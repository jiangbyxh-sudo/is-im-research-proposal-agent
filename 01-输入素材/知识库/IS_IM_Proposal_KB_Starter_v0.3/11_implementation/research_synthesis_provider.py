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

from cluster_naming_provider import ClusterNamingRequest, LLMClusterNamingProvider
from stable_subdirection_clustering import P2ClusterConfig, build_corpus_snapshot, deterministic_average_linkage


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
    def __init__(self, client: DeepSeekJsonClient, max_corpus_size: int = 120, config: P2ClusterConfig | None = None, naming_provider=None):
        self.client = client
        self.max_corpus_size = max(10, max_corpus_size)
        self.config = config or P2ClusterConfig()
        self.naming_provider = naming_provider or LLMClusterNamingProvider(client)
        self._cache: dict[str, SynthesisResult] = {}

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
        if clustering["status"] != "P2_CLUSTERING_COMPLETE":
            return SynthesisResult(
                status=clustering["status"], limitations=list(clustering.get("reasons", [])),
                audit={
                    "corpus_hash": snapshot["corpus_hash"], "cluster_config_version": self.config.version,
                    "cache_key": clustering["cache_key"], "input_paper_count": snapshot["input_paper_count"],
                    "direct_paper_count": snapshot["paper_count"],
                    "excluded_non_direct_count": snapshot["excluded_non_direct_count"],
                },
                message_to_user="P2门禁或语料充分性未满足，未生成五方向。",
            )
        cache_key = clustering["cache_key"]
        if cache_key in self._cache:
            result = deepcopy(self._cache[cache_key])
            result.audit["cache_hit"] = True
            return result
        try:
            named, naming_audit = self.naming_provider.name_clusters(ClusterNamingRequest(
                research_direction=request.research_direction, clusters=tuple(clustering["clusters"]),
                corpus_hash=snapshot["corpus_hash"], cluster_config_version=self.config.version,
            ))
        except Exception as exc:
            return SynthesisResult(
                status="SYNTHESIS_FAILED", limitations=[f"固定簇命名失败：{type(exc).__name__}"],
                audit={"cache_key": cache_key, "corpus_hash": snapshot["corpus_hash"]},
                message_to_user="确定性聚类已完成，但固定簇命名失败；论文归属未被修改。",
            )
        result = SynthesisResult(
            status="SYNTHESIS_COMPLETE", top_subdirections=named, gap_candidates=[], limitations=[],
            audit={
                "corpus_hash": snapshot["corpus_hash"], "cluster_config_version": self.config.version,
                "cache_key": cache_key, "cache_hit": False, "feature_method": clustering["feature_method"],
                "linkage": clustering["linkage"], "tie_break": clustering["tie_break"],
                "naming": naming_audit, "research_gap_generation_in_p2": False,
            },
            message_to_user="已对 direct 论文完成确定性五方向聚类；模型仅命名固定簇。",
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
