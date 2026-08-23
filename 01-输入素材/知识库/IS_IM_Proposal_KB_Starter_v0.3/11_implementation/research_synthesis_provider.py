"""P2 deterministic clustering followed by fixed-membership cluster naming."""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cluster_naming_provider import (
    AthleteJudgeClusterNamingProvider,
    ClusterNamingRequest,
    DeterministicClusterNamingProvider,
)
from evidence_matrix import build_evidence_matrix, evidence_indexes
from gap_candidate_provider import (
    GAP_CANDIDATE_VERSION,
    GapCandidateRequest,
    LLMGapCandidateProvider,
)
from gap_falsification import build_gap_falsification_query_plan
from research_gap_provider import (
    EvidenceBoundResearchGapProvider,
    ResearchGapRequest,
)
from stable_subdirection_clustering import (
    P2ClusterConfig,
    build_corpus_snapshot,
    deterministic_average_linkage,
)


@dataclass(frozen=True)
class SynthesisRequest:
    research_direction: str
    fine_grained_question: str | None
    derived_path: str
    papers: tuple[dict, ...]
    p1_precision_gate_passed: bool = False
    p1_precision_summary: dict = field(default_factory=dict)
    data_cutoff_date: str = ""
    direction_profile_version: str = "unknown"
    retrieval_version: str = "unknown"
    score_version: str = "unknown"


@dataclass
class SynthesisResult:
    status: str
    top_subdirections: list[dict] = field(default_factory=list)
    gap_candidates: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    message_to_user: str = ""
    formal_gaps: list[dict] = field(default_factory=list)
    claim_store: dict = field(default_factory=dict)


class ResearchSynthesisProvider(Protocol):
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...


class UnconfiguredResearchSynthesisProvider:
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        if not request.p1_precision_gate_passed:
            return SynthesisResult(
                status="P2_BLOCKED_BY_P1_PRECISION",
                limitations=["P1人工Precision@10门禁未通过。"],
                message_to_user="P1精度门禁未通过，P2默认阻断。",
            )
        return SynthesisResult(
            status="SYNTHESIS_NOT_CONFIGURED",
            limitations=["聚类命名模型密钥未通过环境变量配置。"],
            message_to_user="确定性聚类可运行，但固定簇命名需要配置DEEPSEEK_API_KEY。",
        )


class DeepSeekJsonClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 90, retries: int = 1):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def complete(self, system_prompt: str, user_prompt: str) -> tuple[dict, dict]:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.0,
            "max_tokens": 4000,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        target = f"{self.base_url}/chat/completions"
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(self.retries + 1):
            try:
                request = Request(
                    target, data=body, method="POST",
                    headers={
                        "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                        "Accept": "application/json", "User-Agent": "ProposalCompass/0.3",
                    },
                )
                with urlopen(request, timeout=self.timeout) as response:
                    envelope = json.load(response)
                content = envelope.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    raise ValueError("empty_model_content")
                return json.loads(content), {
                    "model": envelope.get("model", self.model), "usage": envelope.get("usage", {}),
                    "finish_reason": envelope.get("choices", [{}])[0].get("finish_reason"),
                    "attempts": attempt + 1, "duration_ms": round((time.monotonic() - started) * 1000, 2),
                }
            except HTTPError as exc:
                last_error = RuntimeError(f"deepseek_http_{exc.code}")
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
            if attempt < self.retries:
                time.sleep(1.0 * (2 ** attempt))
        assert last_error
        raise last_error


class DeepSeekResearchSynthesisProvider:
    def __init__(
        self,
        client: DeepSeekJsonClient,
        max_corpus_size: int = 120,
        config: P2ClusterConfig | None = None,
        naming_provider=None,
        fallback_naming_provider=None,
        stability_self_check_runs: int = 2,
        gap_candidate_provider=None,
        gap_formalization_provider=None,
    ):
        self.client = client
        self.max_corpus_size = max(10, max_corpus_size)
        self.config = config or P2ClusterConfig()
        self.naming_provider = naming_provider or AthleteJudgeClusterNamingProvider(client)
        self.fallback_naming_provider = fallback_naming_provider or DeterministicClusterNamingProvider()
        self.stability_self_check_runs = max(1, stability_self_check_runs)
        self.gap_candidate_provider = gap_candidate_provider or LLMGapCandidateProvider(client)
        self.gap_formalization_provider = gap_formalization_provider or EvidenceBoundResearchGapProvider()
        self._cache: dict[str, SynthesisResult] = {}

    def _generate_formal_gaps(self, request: SynthesisRequest, snapshot: dict, named: list[dict]) -> tuple[list[dict], dict, dict]:
        """Athlete/Judge proposals per cluster, then one deterministic formalization."""
        papers = list(snapshot.get("papers") or [])
        paper_map = {paper["paper_id"]: paper for paper in papers}
        matrix = build_evidence_matrix(papers)
        _, span_index = evidence_indexes(matrix)
        spans_by_paper: dict[str, list[dict]] = {}
        for span in span_index.values():
            spans_by_paper.setdefault(span["paper_id"], []).append(span)
        selected_candidates: list[dict] = []
        gap_audit: dict = {"version": GAP_CANDIDATE_VERSION, "clusters": {}}
        for cluster in named:
            cluster_id = cluster["cluster_id"]
            cluster_papers = [paper_map[paper_id] for paper_id in cluster.get("paper_ids", []) if paper_id in paper_map]
            cluster_spans = [span for paper_id in cluster.get("paper_ids", []) for span in spans_by_paper.get(paper_id, [])]
            if not cluster_papers or not cluster_spans:
                gap_audit["clusters"][cluster_id] = {"selected": 0, "note": "no_formal_evidence_spans"}
                continue
            try:
                selected, audit = self.gap_candidate_provider.propose(GapCandidateRequest(
                    research_direction=request.research_direction,
                    cluster_id=cluster_id,
                    cluster_name=str(cluster.get("name_zh") or cluster_id),
                    feature_terms=tuple(cluster.get("feature_terms", [])),
                    papers=tuple(cluster_papers),
                    spans=tuple(cluster_spans),
                ))
            except Exception as exc:
                gap_audit["clusters"][cluster_id] = {"selected": 0, "note": f"proposal_failed:{type(exc).__name__}"}
                continue
            gap_audit["clusters"][cluster_id] = audit
            for candidate in selected:
                candidate["subdirection_id"] = cluster_id
                selected_candidates.append(candidate)
        claim_store: dict = {}
        formal_gaps: list[dict] = []
        rejected: list[dict] = []
        if selected_candidates:
            gap_result = self.gap_formalization_provider.formalize(ResearchGapRequest(
                cluster_id="multi_cluster",
                gap_candidates=tuple(selected_candidates),
                evidence_matrix=matrix,
            ))
            formal_gaps = list(gap_result.formal_gaps)
            claim_store = dict(gap_result.claim_store)
            rejected = list(gap_result.rejected_candidates)
            for gap in formal_gaps:
                gap["falsification_plan"] = build_gap_falsification_query_plan(gap)
        gap_audit["formalization"] = {
            "candidate_count": len(selected_candidates),
            "formal_gap_count": len(formal_gaps),
            "rejected_count": len(rejected),
            "rejected": rejected,
        }
        gap_audit["evidence_matrix"] = {
            "matrix_hash": matrix.get("matrix_hash"),
            "paper_count": matrix.get("paper_count"),
            "formal_evidence_paper_count": matrix.get("formal_evidence_paper_count"),
            "span_count": matrix.get("span_count"),
        }
        return formal_gaps, claim_store, gap_audit

    def _snapshot_audit(self, snapshot: dict, clustering: dict) -> dict:
        return {
            "corpus_hash": snapshot["corpus_hash"],
            "cluster_config_version": self.config.version,
            "cache_key": clustering.get("cache_key"),
            "input_paper_count": snapshot["input_paper_count"],
            "direct_paper_count": snapshot["paper_count"],
            "abstract_count": snapshot["abstract_count"],
            "data_cutoff_date": snapshot.get("data_cutoff_date"),
            "direction_profile_version": snapshot.get("direction_profile_version"),
            "retrieval_version": snapshot.get("retrieval_version"),
            "score_version": snapshot.get("score_version"),
            "language_counts": clustering.get("language_counts", {}),
            "honest_target": clustering.get("honest_target"),
            "requested_clusters": self.config.requested_clusters,
            "degradation_reasons": list(clustering.get("degradation_reasons") or clustering.get("reasons") or []),
            "degradation_reasons_text": list(clustering.get("degradation_reasons_text") or clustering.get("reasons_text") or []),
            "p1_precision_gate_passed": bool(snapshot.get("p1_precision_gate_passed")),
            "p1_precision_summary": snapshot.get("p1_precision_summary") or {},
        }

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        snapshot = build_corpus_snapshot(
            direction_id=request.research_direction,
            papers=list(request.papers)[: self.max_corpus_size],
            data_cutoff_date=request.data_cutoff_date or date.today().isoformat(),
            direction_profile_version=request.direction_profile_version,
            retrieval_version=request.retrieval_version,
            score_version=request.score_version,
            p1_precision_gate_passed=request.p1_precision_gate_passed,
            p1_precision_summary=request.p1_precision_summary,
        )
        clustering = deterministic_average_linkage(snapshot, self.config)
        if clustering["status"] not in {"P2_CLUSTERING_COMPLETE", "P2_CLUSTERING_DEGRADED"}:
            return SynthesisResult(
                status=clustering["status"],
                limitations=list(clustering.get("reasons_text") or clustering.get("reasons", [])),
                audit=self._snapshot_audit(snapshot, clustering),
                message_to_user="P2门禁或语料充分性未满足，未生成方向；系统不会硬凑五方向。",
            )
        cache_key = clustering["cache_key"]
        if cache_key in self._cache:
            result = deepcopy(self._cache[cache_key])
            result.audit["cache_hit"] = True
            return result

        canonical = json.dumps(clustering, ensure_ascii=False, sort_keys=True)
        stability_self_check = {"runs": self.stability_self_check_runs, "exact_match": True, "method": "byte_identical_full_output"}
        for _ in range(self.stability_self_check_runs - 1):
            repeat = deterministic_average_linkage(snapshot, self.config)
            if json.dumps(repeat, ensure_ascii=False, sort_keys=True) != canonical:
                stability_self_check["exact_match"] = False

        naming_fallback_reason = ""
        try:
            named, naming_audit = self.naming_provider.name_clusters(ClusterNamingRequest(
                research_direction=request.research_direction, clusters=tuple(clustering["clusters"]),
                corpus_hash=snapshot["corpus_hash"], cluster_config_version=self.config.version,
            ))
        except Exception as exc:
            named, naming_audit = self.fallback_naming_provider.name_clusters(ClusterNamingRequest(
                research_direction=request.research_direction, clusters=tuple(clustering["clusters"]),
                corpus_hash=snapshot["corpus_hash"], cluster_config_version=self.config.version,
            ))
            naming_fallback_reason = f"{type(exc).__name__}: {exc}"

        degraded = clustering["status"] == "P2_CLUSTERING_DEGRADED"
        target = int(clustering["honest_target"])
        limitations = list(clustering.get("degradation_reasons_text") or [])
        if naming_fallback_reason:
            limitations.append("固定簇命名模型调用失败，已回退确定性特征命名；论文归属未被修改。")
        status = "SYNTHESIS_PARTIAL" if degraded else "SYNTHESIS_COMPLETE"
        message = (
            f"语料仅支撑{target}个方向，已按证据诚实输出{target}个方向，未硬凑五方向。"
            if degraded else
            "已对 direct 论文完成确定性五方向聚类；模型仅命名固定簇。"
        )
        audit = {
            **self._snapshot_audit(snapshot, clustering),
            "cache_hit": False,
            "feature_method": clustering["feature_method"],
            "linkage": clustering["linkage"],
            "tie_break": clustering["tie_break"],
            "heat_method": clustering.get("heat_method"),
            "stability_self_check": stability_self_check,
            "naming": naming_audit,
            "naming_prompt_version": naming_audit.get("prompt_version"),
            "naming_fallback_reason": naming_fallback_reason,
            "gap_generation_pipeline": GAP_CANDIDATE_VERSION,
        }
        formal_gaps: list[dict] = []
        claim_store: dict = {}
        gap_failure = ""
        try:
            formal_gaps, claim_store, gap_audit_detail = self._generate_formal_gaps(request, snapshot, named)
            audit["gap_candidates"] = gap_audit_detail
        except Exception as exc:
            gap_failure = f"{type(exc).__name__}: {exc}"
            audit["gap_candidates"] = {"version": GAP_CANDIDATE_VERSION, "error": gap_failure}
        if gap_failure:
            limitations.append("研究空白候选流水线执行失败，本次未产出正式空白；论文归属与方向命名不受影响。")
        elif not formal_gaps:
            limitations.append("本次证据未产生通过确定性核验的正式研究空白；系统不硬凑空白。")
        named = [{**cluster, "subdirection_id": cluster["cluster_id"]} for cluster in named]
        result = SynthesisResult(
            status=status, top_subdirections=named, gap_candidates=formal_gaps, limitations=limitations,
            audit=audit, message_to_user=message,
            formal_gaps=formal_gaps, claim_store=claim_store,
        )
        self._cache[cache_key] = deepcopy(result)
        return result


def build_research_synthesis_provider() -> ResearchSynthesisProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        return UnconfiguredResearchSynthesisProvider()
    client = DeepSeekJsonClient(
        api_key=api_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"), timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "90")),
    )
    return DeepSeekResearchSynthesisProvider(client)
