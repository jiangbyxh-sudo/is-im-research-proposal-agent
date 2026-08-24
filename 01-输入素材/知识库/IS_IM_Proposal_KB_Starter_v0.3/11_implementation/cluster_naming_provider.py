"""Name fixed P2 clusters without allowing a model to change membership."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol


NAMING_PROMPT_VERSION = "p2-athlete-judge-naming-2.0.0"

ATHLETE_A_SYSTEM = """你是研究簇命名选手A。你只负责为已经固定的研究簇命名，风格要求：名称简洁、学术化，使用信息系统与管理学（IS/MIM）领域的通用构念。
输出JSON对象，格式为：
{"names":[{"cluster_id":"cluster_001","name_zh":"中文名","name_en":"English name","description":"边界描述"}]}
不得输出paper_ids，不得增删、合并、拆分研究簇，不得生成簇命名以外的任何内容。"""

ATHLETE_B_SYSTEM = """你是研究簇命名选手B。你只负责为已经固定的研究簇命名，风格要求：名称具体，体现研究对象、机制与情境的组合，便于研究者快速定位文献簇。
输出JSON对象，格式为：
{"names":[{"cluster_id":"cluster_001","name_zh":"中文名","name_en":"English name","description":"边界描述"}]}
不得输出paper_ids，不得增删、合并、拆分研究簇，不得生成簇命名以外的任何内容。"""

JUDGE_SYSTEM = """你是研究簇命名裁判。你只依据固定簇的证据信息，盲评两个匿名候选命名（候选一/候选二）；你不知道也无法判断候选来源。
对每个簇，选择更能准确概括簇内论文内容、边界更清晰的候选。输出JSON对象，格式为：
{"selections":[{"cluster_id":"cluster_001","winner":"candidate_1","reason":"一句话理由"}]}
winner只能是candidate_1或candidate_2。不得改写、合并候选名称，不得输出paper_ids，不得增删研究簇，不得输出裁决以外的任何内容。"""


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


def _athlete_payload(request: ClusterNamingRequest) -> dict:
    return {
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


def _validated_athlete_names(raw: object, request: ClusterNamingRequest) -> dict[str, dict]:
    if "paper_ids" in json.dumps(raw, ensure_ascii=False):
        raise ValueError("cluster_namer_must_not_return_paper_ids")
    names = raw.get("names", []) if isinstance(raw, dict) else []
    by_id = {item.get("cluster_id"): item for item in names if isinstance(item, dict)}
    allowed = {cluster["cluster_id"] for cluster in request.clusters}
    if set(by_id) != allowed:
        raise ValueError("cluster_namer_must_name_every_fixed_cluster_exactly_once")
    validated = {}
    for cluster_id in allowed:
        value = by_id[cluster_id]
        if not str(value.get("name_zh") or "").strip() or not str(value.get("name_en") or "").strip():
            raise ValueError("cluster_name_missing")
        validated[cluster_id] = {
            "name_zh": str(value["name_zh"]).strip(),
            "name_en": str(value["name_en"]).strip(),
            "description": str(value.get("description") or "").strip(),
        }
    return validated


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

    def name_clusters(self, request: ClusterNamingRequest) -> tuple[list[dict], dict]:
        before = membership_hash(request.clusters)
        raw, audit = self.client.complete(ATHLETE_A_SYSTEM, json.dumps(_athlete_payload(request), ensure_ascii=False))
        validated = _validated_athlete_names(raw, request)
        named = [{**deepcopy(cluster), **validated[cluster["cluster_id"]]} for cluster in request.clusters]
        if membership_hash(named) != before:
            raise AssertionError("cluster membership changed during naming")
        return named, {**audit, "provider": "llm_single_call", "prompt_version": NAMING_PROMPT_VERSION, "membership_hash": before}


class AthleteJudgeClusterNamingProvider:
    """Athlete A/B independently name fixed clusters; a blind judge picks per cluster."""

    def __init__(self, client):
        self.client = client

    def name_clusters(self, request: ClusterNamingRequest) -> tuple[list[dict], dict]:
        before = membership_hash(request.clusters)
        payload = json.dumps(_athlete_payload(request), ensure_ascii=False)
        raw_a, audit_a = self.client.complete(ATHLETE_A_SYSTEM, payload)
        names_a = _validated_athlete_names(raw_a, request)
        raw_b, audit_b = self.client.complete(ATHLETE_B_SYSTEM, payload)
        names_b = _validated_athlete_names(raw_b, request)

        judge_payload = {
            "task": "盲评固定研究簇的候选命名",
            "research_direction": request.research_direction,
            "clusters": [
                {
                    "cluster_id": cluster["cluster_id"],
                    "paper_count": cluster["paper_count"],
                    "feature_terms": cluster.get("feature_terms", []),
                    "sample_titles": cluster.get("sample_titles", []),
                    "candidate_1": names_a[cluster["cluster_id"]],
                    "candidate_2": names_b[cluster["cluster_id"]],
                }
                for cluster in request.clusters
            ],
        }
        raw_judge, audit_judge = self.client.complete(
            JUDGE_SYSTEM, json.dumps(judge_payload, ensure_ascii=False)
        )
        if "paper_ids" in json.dumps(raw_judge, ensure_ascii=False):
            raise ValueError("judge_must_not_return_paper_ids")
        selections = raw_judge.get("selections", []) if isinstance(raw_judge, dict) else []
        by_id = {item.get("cluster_id"): item for item in selections if isinstance(item, dict)}
        allowed = {cluster["cluster_id"] for cluster in request.clusters}
        if set(by_id) != allowed:
            raise ValueError("judge_must_select_for_every_fixed_cluster_exactly_once")
        named = []
        winners: dict[str, str] = {}
        for cluster in request.clusters:
            selection = by_id[cluster["cluster_id"]]
            winner = str(selection.get("winner") or "").strip()
            if winner not in {"candidate_1", "candidate_2"}:
                raise ValueError("judge_winner_must_be_candidate_1_or_candidate_2")
            source = names_a if winner == "candidate_1" else names_b
            athlete = "athlete_a" if winner == "candidate_1" else "athlete_b"
            winners[cluster["cluster_id"]] = athlete
            named.append({
                **deepcopy(cluster), **source[cluster["cluster_id"]],
                "selected_from": athlete,
                "judge_reason": str(selection.get("reason") or "").strip(),
            })
        if membership_hash(named) != before:
            raise AssertionError("cluster membership changed during naming")
        return named, {
            "provider": "athlete_judge_arena",
            "prompt_version": NAMING_PROMPT_VERSION,
            "membership_hash": before,
            "athlete_a": audit_a,
            "athlete_b": audit_b,
            "judge": audit_judge,
            "winners": winners,
            "athlete_win_counts": {
                "athlete_a": sum(1 for value in winners.values() if value == "athlete_a"),
                "athlete_b": sum(1 for value in winners.values() if value == "athlete_b"),
            },
            "membership_invariant": True,
        }
