"""Question-specific retrieval over already admitted Evidence Matrix spans."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from evidence_matrix import validate_formal_span


QUESTION_EVIDENCE_VERSION = "p3-question-evidence-retrieval-1.0.0"
PAPERQA2_RELEASE = "2026.8.12"
MAX_QUERY_CHARACTERS = 2_000
MAX_SPAN_CHARACTERS = 20_000
MAX_CORPUS_CHARACTERS = 8_000_000
MAX_SPANS = 5_000
MAX_TOP_K = 50


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class EvidenceRetrievalBackend(Protocol):
    def retrieve(self, query: str, spans: list[dict], top_k: int) -> dict: ...


@dataclass(frozen=True)
class QuestionEvidenceRequest:
    query: str
    evidence_matrix: dict
    eligible_direct_paper_ids: tuple[str, ...]
    top_k: int = 10


@dataclass
class QuestionEvidenceResult:
    status: str
    candidates: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    message_to_user: str = ""


class UnconfiguredQuestionEvidenceProvider:
    def retrieve(self, request: QuestionEvidenceRequest) -> QuestionEvidenceResult:
        return QuestionEvidenceResult(
            status="PAPERQA2_NOT_CONFIGURED",
            limitations=["PaperQA2隔离检索运行时未配置。"],
            audit={
                "formal_evidence_only": True,
                "p1_direct_allowlist_enforced": True,
                "claim_generation_allowed": False,
                "research_gap_decision_allowed": False,
            },
            message_to_user="问题相关证据检索未配置；未生成答案、Claim或研究空白。",
        )


class PaperQA2SubprocessBackend:
    """Invoke a pinned PaperQA2 worker with a secret-free environment."""

    def __init__(self, python_executable: Path, worker_path: Path, timeout: int = 120) -> None:
        self.python_executable = python_executable.resolve()
        self.worker_path = worker_path.resolve()
        self.timeout = max(1, int(timeout))

    @staticmethod
    def sanitized_environment() -> dict[str, str]:
        keep = (
            "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC",
            "USERPROFILE", "LOCALAPPDATA", "APPDATA",
        )
        environment = {key: os.environ[key] for key in keep if os.environ.get(key)}
        environment.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        runtime_root = Path(environment.get("LOCALAPPDATA") or environment.get("TEMP") or ".")
        environment["PQA_HOME"] = str(runtime_root / "is-im-paperqa2" / "runtime-home")
        return environment

    def retrieve(self, query: str, spans: list[dict], top_k: int) -> dict:
        if not self.python_executable.is_file() or not self.worker_path.is_file():
            raise RuntimeError("paperqa2_runtime_not_found")
        payload = json.dumps(
            {"query": query, "spans": spans, "top_k": top_k},
            ensure_ascii=False,
            sort_keys=True,
        )
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            [str(self.python_executable), str(self.worker_path)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.timeout,
            env=self.sanitized_environment(),
            creationflags=creation_flags,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError("paperqa2_worker_failed")
        if len(completed.stdout) > 1_000_000:
            raise RuntimeError("paperqa2_worker_output_too_large")
        response = json.loads(completed.stdout)
        if not isinstance(response, dict):
            raise RuntimeError("paperqa2_worker_invalid_response")
        return response


class ControlledQuestionEvidenceProvider:
    def __init__(self, backend: EvidenceRetrievalBackend) -> None:
        self.backend = backend

    @staticmethod
    def _validate_request(request: QuestionEvidenceRequest) -> tuple[str, set[str], int]:
        query = _clean(request.query)
        if not query or len(query) > MAX_QUERY_CHARACTERS:
            raise ValueError("valid_question_required")
        allowed = {_clean(item) for item in request.eligible_direct_paper_ids if _clean(item)}
        if not allowed:
            raise ValueError("eligible_direct_paper_ids_required")
        if isinstance(request.top_k, bool) or not 1 <= int(request.top_k) <= MAX_TOP_K:
            raise ValueError("top_k_out_of_bounds")
        return query, allowed, int(request.top_k)

    @staticmethod
    def _curated_spans(matrix: dict, allowed: set[str]) -> tuple[list[dict], dict[str, dict]]:
        curated = []
        index = {}
        corpus_characters = 0
        rows = sorted(
            matrix.get("spans", []),
            key=lambda item: (_clean(item.get("paper_id")), _clean(item.get("span_id"))),
        )
        for row in rows:
            paper_id = _clean(row.get("paper_id"))
            span_id = _clean(row.get("span_id"))
            if paper_id not in allowed or not span_id:
                continue
            span = validate_formal_span(matrix, span_id, paper_id)
            text = _clean(span.get("text"))
            if not text or len(text) > MAX_SPAN_CHARACTERS:
                continue
            corpus_characters += len(text)
            if corpus_characters > MAX_CORPUS_CHARACTERS or len(curated) >= MAX_SPANS:
                raise ValueError("evidence_corpus_out_of_bounds")
            backend_row = {"span_id": span_id, "paper_id": paper_id, "text": text}
            curated.append(backend_row)
            index[span_id] = span
        if not curated:
            raise ValueError("no_formal_evidence_for_eligible_direct_papers")
        return curated, index

    def retrieve(self, request: QuestionEvidenceRequest) -> QuestionEvidenceResult:
        try:
            query, allowed, top_k = self._validate_request(request)
            curated, span_index = self._curated_spans(request.evidence_matrix, allowed)
            backend = self.backend.retrieve(query, curated, min(top_k, len(curated)))
            if backend.get("status") != "OK" or not isinstance(backend.get("results"), list):
                raise RuntimeError("paperqa2_result_rejected")
            if _clean(backend.get("backend_version")) != PAPERQA2_RELEASE:
                raise RuntimeError("paperqa2_version_mismatch")
            result_ids = [_clean(item) for item in backend["results"]]
            if any(not item or item not in span_index for item in result_ids):
                raise RuntimeError("paperqa2_result_rejected")
            if len(result_ids) != len(set(result_ids)) or len(result_ids) > top_k:
                raise RuntimeError("paperqa2_result_rejected")

            candidates = []
            for rank, span_id in enumerate(result_ids, start=1):
                span = span_index[span_id]
                candidates.append({
                    "candidate_id": f"evidence_candidate_{_sha256_text(query + '|' + span_id)[:20]}",
                    "rank": rank,
                    "rank_score": round(1.0 / rank, 6),
                    "paper_id": span["paper_id"],
                    "evidence_span_id": span_id,
                    "evidence_span": {
                        "evidence_level": span["evidence_level"],
                        "source_field": span["source_field"],
                        "start_char": span["start_char"],
                        "end_char": span["end_char"],
                        "text": span["text"],
                        "section": span.get("section"),
                        "page": span.get("page"),
                    },
                    "candidate_status": "EVIDENCE_CANDIDATE_ONLY",
                    "requires_claim_store_binding": True,
                })
            status = "QUESTION_EVIDENCE_READY" if candidates else "QUESTION_EVIDENCE_EMPTY"
            return QuestionEvidenceResult(
                status=status,
                candidates=candidates,
                limitations=[] if candidates else ["PaperQA2未返回匹配的正式证据span。"],
                audit={
                    "version": QUESTION_EVIDENCE_VERSION,
                    "backend": "paperqa2_sparse_retrieval",
                    "backend_version": PAPERQA2_RELEASE,
                    "query_hash": _sha256_text(query),
                    "matrix_hash": request.evidence_matrix.get("matrix_hash"),
                    "eligible_direct_paper_count": len(allowed),
                    "curated_formal_span_count": len(curated),
                    "returned_candidate_count": len(candidates),
                    "formal_evidence_only": True,
                    "p1_direct_allowlist_enforced": True,
                    "external_paper_search_allowed": False,
                    "pdf_parsing_allowed": False,
                    "llm_or_agent_allowed": False,
                    "answer_generation_allowed": False,
                    "claim_generation_allowed": False,
                    "research_gap_decision_allowed": False,
                },
                message_to_user=(
                    f"已检索{len(candidates)}条问题相关全文/摘要证据候选；正式使用前仍须绑定Claim Store。"
                    if candidates else "未找到问题相关正式证据；未生成答案、Claim或研究空白。"
                ),
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            return QuestionEvidenceResult(
                status="PAPERQA2_RETRIEVAL_FAILED",
                limitations=[str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__],
                audit={
                    "error_type": type(exc).__name__,
                    "formal_evidence_only": True,
                    "p1_direct_allowlist_enforced": True,
                    "claim_generation_allowed": False,
                    "research_gap_decision_allowed": False,
                },
                message_to_user="PaperQA2证据检索失败；未生成答案、Claim或研究空白。",
            )
        except (ValueError, TypeError) as exc:
            return QuestionEvidenceResult(
                status="QUESTION_EVIDENCE_BLOCKED",
                limitations=[str(exc)],
                audit={
                    "formal_evidence_only": True,
                    "p1_direct_allowlist_enforced": True,
                    "claim_generation_allowed": False,
                },
            )


def build_question_evidence_provider():
    enabled = os.getenv("PROPOSAL_ENABLE_PAPERQA2", "0").strip().casefold() in {"1", "true", "yes", "on"}
    if not enabled:
        return UnconfiguredQuestionEvidenceProvider()
    local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    default_python = local_app_data / "is-im-paperqa2" / "v2026.08.12" / ".venv" / "Scripts" / "python.exe"
    python_executable = Path(os.getenv("PAPERQA2_PYTHON", str(default_python)))
    worker_path = Path(__file__).parent / "research_skills" / "sidecars" / "paperqa2" / "paperqa2_retrieval_worker.py"
    backend = PaperQA2SubprocessBackend(
        python_executable=python_executable,
        worker_path=worker_path,
        timeout=int(os.getenv("PAPERQA2_TIMEOUT", "120")),
    )
    return ControlledQuestionEvidenceProvider(backend)
