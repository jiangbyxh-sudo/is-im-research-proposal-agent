"""Evidence-bounded five-direction clustering and research-gap synthesis."""
from __future__ import annotations

import json
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GAP_TYPES = {"empirical", "theoretical", "methodological", "contextual", "temporal", "contradiction"}


@dataclass(frozen=True)
class SynthesisRequest:
    research_direction: str
    fine_grained_question: str | None
    derived_path: str
    papers: tuple[dict, ...]


@dataclass
class SynthesisResult:
    status: str
    top_subdirections: list[dict] = field(default_factory=list)
    gap_candidates: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    message_to_user: str = ""


class ResearchSynthesisProvider(Protocol):
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...


class UnconfiguredResearchSynthesisProvider:
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        return SynthesisResult(
            status="SYNTHESIS_NOT_CONFIGURED",
            limitations=["DeepSeek密钥未通过环境变量配置。"],
            message_to_user="论文发现已完成；五方向与研究空白综合需要配置DEEPSEEK_API_KEY后运行。",
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
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.1,
            "max_tokens": 8000,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        target = f"{self.base_url}/chat/completions"
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(self.retries + 1):
            try:
                request = Request(
                    target,
                    data=body,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "ProposalCompass/0.3",
                    },
                )
                with urlopen(request, timeout=self.timeout) as response:
                    envelope = json.load(response)
                content = envelope.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    raise ValueError("empty_model_content")
                return json.loads(content), {
                    "model": envelope.get("model", self.model),
                    "usage": envelope.get("usage", {}),
                    "finish_reason": envelope.get("choices", [{}])[0].get("finish_reason"),
                    "attempts": attempt + 1,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
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
    def __init__(self, client: DeepSeekJsonClient, max_corpus_size: int = 120):
        self.client = client
        self.max_corpus_size = max(10, max_corpus_size)

    @staticmethod
    def _paper_view(paper: dict, paper_id: str) -> dict:
        return {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "authors": paper.get("authors", [])[:6],
            "year": paper.get("year"),
            "journal": paper.get("journal"),
            "doi": paper.get("doi"),
            "citation_count": paper.get("citation_count", 0),
            "journal_ranking": paper.get("journal_ranking", []),
        }

    @staticmethod
    def _system_prompt() -> str:
        return """你是IS/IM领域的证据综合器。必须输出一个JSON对象，不得输出JSON以外的文字。
只允许使用用户消息中提供的论文元数据；不得虚构论文、DOI、作者、方法、结论、理论或因果关系。
论文只有题名级元数据时，只能形成“待全文验证的研究空白候选”，不能宣称已证实空白。
每篇论文最多归入一个小方向。小方向按论文数量排序，但数量由下游代码重新计算。
研究空白必须属于empirical/theoretical/methodological/contextual/temporal/contradiction之一，且至少引用2个输入paper_id。
需要显式报告矛盾、证据不足和替代解释；不要把期刊等级等同于结论正确性。
JSON格式示例：
{
  "subdirections": [{
    "name_zh": "小方向中文名", "name_en": "English name", "description": "边界描述",
    "paper_ids": ["P001", "P002"],
    "gaps": [{
      "gap_type": "empirical", "gap_statement": "待验证的空白陈述",
      "why_it_matters": "意义", "evidence_basis": ["P001", "P002"],
      "alternative_explanations": ["替代解释"],
      "innovation_candidates": ["可检验创新点"], "confidence": "emerging"
    }]
  }],
  "unclassified_paper_ids": [],
  "contradictions": [],
  "limitations": ["限制"]
}"""

    def _validate(self, raw: dict, paper_map: dict[str, dict], derived_path: str) -> SynthesisResult:
        allowed = set(paper_map)
        assigned: set[str] = set()
        directions = []
        gaps = []
        invalid_refs = 0
        for index, item in enumerate(raw.get("subdirections", [])):
            if not isinstance(item, dict):
                continue
            name_zh = str(item.get("name_zh") or "").strip()
            name_en = str(item.get("name_en") or "").strip()
            if not name_zh or not name_en:
                continue
            paper_ids = []
            raw_paper_ids = item.get("paper_ids", [])
            if not isinstance(raw_paper_ids, list):
                raw_paper_ids = []
            for paper_id in raw_paper_ids:
                if paper_id in allowed and paper_id not in assigned:
                    assigned.add(paper_id)
                    paper_ids.append(paper_id)
                elif paper_id not in allowed:
                    invalid_refs += 1
            if not paper_ids:
                continue
            direction_id = f"subdirection_{index + 1}"
            direction = {
                "subdirection_id": direction_id,
                "name_zh": name_zh,
                "name_en": name_en,
                "description": str(item.get("description") or "").strip(),
                "paper_count": len(paper_ids),
                "paper_ids": paper_ids,
                "evidence_papers": [paper_map[value] for value in paper_ids[:6]],
            }
            raw_gaps = item.get("gaps", [])
            if not isinstance(raw_gaps, list):
                raw_gaps = []
            for gap_index, gap in enumerate(raw_gaps[:3]):
                if not isinstance(gap, dict) or gap.get("gap_type") not in GAP_TYPES:
                    continue
                raw_evidence = gap.get("evidence_basis", [])
                if not isinstance(raw_evidence, list):
                    raw_evidence = []
                evidence_ids = [value for value in raw_evidence if value in paper_ids]
                invalid_refs += len(raw_evidence) - len(evidence_ids)
                statement = str(gap.get("gap_statement") or "").strip()
                if len(evidence_ids) < 2 or not statement:
                    continue
                known_dois = {str(paper_map[value].get("doi")).lower() for value in evidence_ids if paper_map[value].get("doi")}
                gap_text = json.dumps(gap, ensure_ascii=False)
                mentioned_dois = {value.lower() for value in re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", gap_text, re.I)}
                if mentioned_dois - known_dois:
                    invalid_refs += len(mentioned_dois - known_dois)
                    continue
                gap_id = f"{direction_id}_gap_{gap_index + 1}"
                gaps.append({
                    "gap_id": gap_id,
                    "subdirection_id": direction_id,
                    "gap_type": gap["gap_type"],
                    "gap_statement": statement,
                    "why_it_matters": str(gap.get("why_it_matters") or "").strip(),
                    "evidence_basis": evidence_ids,
                    "evidence_papers": [paper_map[value] for value in evidence_ids],
                    "alternative_explanations": [str(value) for value in gap.get("alternative_explanations", [])[:3]],
                    "innovation_candidates": [str(value) for value in gap.get("innovation_candidates", [])[:3]],
                    "confidence": str(gap.get("confidence") or "emerging"),
                    "verification_status": "title_metadata_only_pending_fulltext",
                })
            directions.append(direction)

        directions.sort(key=lambda item: (item["paper_count"], item["name_zh"]), reverse=True)
        if derived_path == "top_five_subdirections":
            directions = directions[:5]
            kept_ids = {item["subdirection_id"] for item in directions}
            gaps = [item for item in gaps if item["subdirection_id"] in kept_ids]
        else:
            directions = directions[:1]
            kept_ids = {item["subdirection_id"] for item in directions}
            gaps = [item for item in gaps if item["subdirection_id"] in kept_ids]
        limitations = [str(value) for value in raw.get("limitations", [])[:8]]
        limitations.append("当前综合主要依据题名级元数据；所有空白均需在全文获取后复核。")
        if len(directions) < (5 if derived_path == "top_five_subdirections" else 1) or not gaps:
            status = "SYNTHESIS_PARTIAL"
        else:
            status = "SYNTHESIS_COMPLETE"
        return SynthesisResult(
            status=status,
            top_subdirections=directions,
            gap_candidates=gaps,
            limitations=limitations,
            audit={
                "input_paper_count": len(paper_map),
                "assigned_paper_count": len(assigned),
                "unclassified_paper_count": len(allowed - assigned),
                "invalid_reference_count": invalid_refs,
                "counts_recomputed_by_code": True,
            },
            message_to_user=(
                f"已生成{len(directions)}个研究小方向和{len(gaps)}个可追溯研究空白候选；"
                "空白依据题名级元数据，选择前仍需全文复核。"
            ),
        )

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        corpus = list(request.papers)[: self.max_corpus_size]
        if len(corpus) < 5:
            return SynthesisResult(
                status="SYNTHESIS_INSUFFICIENT_EVIDENCE",
                limitations=["合格论文少于5篇，不能稳定形成五方向与研究空白。"],
                message_to_user="论文证据不足，已停止五方向与研究空白综合。",
            )
        paper_map = {f"P{index + 1:03d}": self._paper_view(paper, f"P{index + 1:03d}") for index, paper in enumerate(corpus)}
        user_payload = {
            "task": "输出json：对最近五年论文做互斥主题归类，并提出有证据锚点的研究空白候选。",
            "research_direction": request.research_direction,
            "fine_grained_question": request.fine_grained_question,
            "derived_path": request.derived_path,
            "required_subdirection_count": 5 if request.derived_path == "top_five_subdirections" else 1,
            "papers": list(paper_map.values()),
        }
        try:
            raw, model_audit = self.client.complete(self._system_prompt(), json.dumps(user_payload, ensure_ascii=False))
            result = self._validate(raw, paper_map, request.derived_path)
            result.audit["model"] = model_audit
            result.audit["prompt_version"] = "synthesis-current-baseline-0.3"
            result.audit["input_hash"] = hashlib.sha256(
                json.dumps(user_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            result.audit["raw_model_output"] = raw
            return result
        except Exception as exc:
            return SynthesisResult(
                status="SYNTHESIS_FAILED",
                limitations=[f"模型调用或JSON校验失败：{type(exc).__name__}"],
                message_to_user="论文发现已完成，但五方向与研究空白综合失败；未生成无证据结果。",
            )


def build_research_synthesis_provider() -> ResearchSynthesisProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        return UnconfiguredResearchSynthesisProvider()
    client = DeepSeekJsonClient(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "90")),
    )
    return DeepSeekResearchSynthesisProvider(client)
