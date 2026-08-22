"""Name fixed P2 clusters without allowing a model to change membership."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol


NAMING_PROMPT_VERSION = "p2-fixed-cluster-naming-1.0.0"


@dataclass(frozen=True)
class ClusterNamingRequest:
    research_direction: str
    clusters: tuple[dict, ...]
    corpus_hash: str
    cluster_config_version: str


class ClusterNamingProvider(Protocol):
    def name_clusters(self, request: ClusterNamingRequest) -> tuple[list[dict], dict]: ...


def membership_hash(clusters: list[dict] | tuple[dict, ...]) -> str:
    membership = [
        {"cluster_id": item["cluster_id"], "paper_ids": sorted(item.get("paper_ids", []))}
        for item in sorted(clusters, key=lambda value: value["cluster_id"])
    ]
    return hashlib.sha256(
        json.dumps(membership, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class DeterministicClusterNamingProvider:
    """Offline fallback that names clusters from already-fixed feature terms."""

    def name_clusters(self, request: ClusterNamingRequest) -> tuple[list[dict], dict]:
        named = []
        for cluster in request.clusters:
            terms = [str(value).replace("topic::", "").replace("keyword::", "") for value in cluster.get("feature_terms", [])[:3]]
            label = " / ".join(terms) or cluster["cluster_id"]
            named.append({**deepcopy(cluster), "name_zh": label, "name_en": label, "description": "基于固定簇高权重特征的确定性命名。"})
        return named, {"provider": "deterministic_feature_terms", "prompt_version": NAMING_PROMPT_VERSION}


class LLMClusterNamingProvider:
    def __init__(self, client):
        self.client = client

    @staticmethod
    def _system_prompt() -> str:
        return """你只负责为已经固定的研究簇命名。输出JSON对象，格式为：
{"names":[{"cluster_id":"cluster_001","name_zh":"中文名","name_en":"English name","description":"边界描述"}]}
不得输出paper_ids，不得增删、合并、拆分研究簇，不得生成簇命名以外的任何内容。"""

    def name_clusters(self, request: ClusterNamingRequest) -> tuple[list[dict], dict]:
        before = membership_hash(request.clusters)
        payload = {
            "task": "仅命名固定研究簇",
            "research_direction": request.research_direction,
            "clusters": [
                {
                    "cluster_id": cluster["cluster_id"],
                    "paper_count": cluster["paper_count"],
                    "feature_terms": cluster.get("feature_terms", []),
                    "sample_titles": cluster.get("sample_titles", []),
                }
                for cluster in request.clusters
            ],
        }
        raw, audit = self.client.complete(self._system_prompt(), json.dumps(payload, ensure_ascii=False))
        if "paper_ids" in json.dumps(raw, ensure_ascii=False):
            raise ValueError("cluster_namer_must_not_return_paper_ids")
        names = raw.get("names", []) if isinstance(raw, dict) else []
        by_id = {item.get("cluster_id"): item for item in names if isinstance(item, dict)}
        allowed = {cluster["cluster_id"] for cluster in request.clusters}
        if set(by_id) != allowed:
            raise ValueError("cluster_namer_must_name_every_fixed_cluster_exactly_once")
        named = []
        for cluster in request.clusters:
            value = by_id[cluster["cluster_id"]]
            if not str(value.get("name_zh") or "").strip() or not str(value.get("name_en") or "").strip():
                raise ValueError("cluster_name_missing")
            named.append({
                **deepcopy(cluster),
                "name_zh": str(value["name_zh"]).strip(),
                "name_en": str(value["name_en"]).strip(),
                "description": str(value.get("description") or "").strip(),
            })
        if membership_hash(named) != before:
            raise AssertionError("cluster membership changed during naming")
        return named, {**audit, "prompt_version": NAMING_PROMPT_VERSION, "membership_hash": before}
