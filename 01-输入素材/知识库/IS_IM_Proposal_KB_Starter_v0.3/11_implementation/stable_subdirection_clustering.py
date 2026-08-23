"""Deterministic P2 corpus snapshots and evidence sufficiency gates.

This module deliberately contains no model calls.  It establishes the stable
input contract that clustering, naming athletes, and judges must consume.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable


SNAPSHOT_VERSION = "p2-direct-corpus-snapshot-2.0.0"

DEGRADATION_REASON_TEXT = {
    "p1_precision_gate_not_passed": "P1人工Precision门禁未通过，P2默认阻断",
    "paper_count_below_30": "direct论文不足30篇，无法支撑五个方向",
    "abstract_count_below_20": "带摘要论文不足20篇，文本特征不足",
    "insufficient_rows_for_minimum_cluster_sizes": "论文数不足以保证每簇至少3篇",
    "evidence_supports_fewer_than_three_directions": "证据仅支撑少于3个方向，已诚实停止",
}


def degradation_reasons_text(reasons: list[str]) -> list[str]:
    return [DEGRADATION_REASON_TEXT.get(reason, reason) for reason in reasons]


@dataclass(frozen=True)
class P2ClusterConfig:
    version: str = "p2-tfidf-average-linkage-2.1.0"
    requested_clusters: int = 5
    min_papers: int = 30
    min_abstracts: int = 20
    min_cluster_size: int = 3
    # 五方向门槛按比例换算：30篇/5方向=6篇每方向，20摘要/5方向=4摘要每方向。
    papers_per_direction: int = 6
    abstracts_per_direction: int = 4
    min_degraded_directions: int = 3
    text_weight: float = 1.0
    topic_weight: float = 1.35
    keyword_weight: float = 1.15
    recent_window_years: int = 3
    # 热度权重：论文占比/近期增长/引文速度/匹配分/来源质量。
    heat_weights: tuple[float, float, float, float, float] = (0.30, 0.25, 0.20, 0.15, 0.10)
    max_citations_per_year_for_heat: float = 10.0


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _canonical_paper(paper: dict) -> dict:
    title = _clean_text(paper.get("title"))
    doi = _clean_text(paper.get("doi")).lower()
    source = _clean_text(paper.get("source_title") or paper.get("journal"))
    year = int(paper.get("year") or 0)
    identity_seed = doi or f"{title.casefold()}|{source.casefold()}|{year}"
    paper_id = _clean_text(paper.get("paper_id")) or (
        "p2paper_" + hashlib.sha256(identity_seed.encode("utf-8")).hexdigest()[:20]
    )
    topics = paper.get("topics") or paper.get("openalex_topics") or []
    keywords = paper.get("keywords") or []
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": _clean_text(paper.get("abstract")),
        "year": year,
        "source_title": source,
        "doi": doi,
        "language": _clean_text(paper.get("language")).lower(),
        "citation_count": int(paper.get("citation_count") or 0),
        "topics": topics,
        "keywords": keywords,
        "relevance_tier": _clean_text(paper.get("relevance_tier")).lower(),
        "p1_match_score": paper.get("paper_match_score", paper.get("retrieval_score")),
        "source_quality": paper.get("source_quality"),
    }

def build_corpus_snapshot(
    *,
    direction_id: str,
    papers: Iterable[dict],
    data_cutoff_date: str,
    direction_profile_version: str,
    retrieval_version: str,
    score_version: str,
    p1_precision_gate_passed: bool,
    p1_precision_summary: dict | None = None,
) -> dict:
    canonical_by_id = {}
    input_count = 0
    excluded_non_direct_count = 0
    for paper in papers:
        input_count += 1
        canonical = _canonical_paper(paper)
        if canonical["relevance_tier"] != "direct":
            excluded_non_direct_count += 1
            continue
        if canonical["title"]:
            canonical_by_id.setdefault(canonical["paper_id"], canonical)
    canonical_papers = sorted(
        canonical_by_id.values(),
        key=lambda item: (item["paper_id"], item["doi"], item["title"].casefold()),
    )
    corpus_bytes = json.dumps(
        canonical_papers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "direction_id": direction_id,
        "data_cutoff_date": data_cutoff_date,
        "direction_profile_version": direction_profile_version,
        "retrieval_version": retrieval_version,
        "score_version": score_version,
        "p1_precision_gate_passed": bool(p1_precision_gate_passed),
        "p1_precision_summary": p1_precision_summary or {},
        "paper_count": len(canonical_papers),
        "input_paper_count": input_count,
        "excluded_non_direct_count": excluded_non_direct_count,
        "abstract_count": sum(bool(item["abstract"]) for item in canonical_papers),
        "corpus_hash": hashlib.sha256(corpus_bytes).hexdigest(),
        "papers": canonical_papers,
    }


def assess_corpus_sufficiency(snapshot: dict, config: P2ClusterConfig | None = None) -> dict:
    config = config or P2ClusterConfig()
    paper_count = int(snapshot.get("paper_count") or 0)
    abstract_count = int(snapshot.get("abstract_count") or 0)
    reasons = []
    if not snapshot.get("p1_precision_gate_passed"):
        reasons.append("p1_precision_gate_not_passed")
    if paper_count < config.min_papers:
        reasons.append("paper_count_below_30")
    if abstract_count < config.min_abstracts:
        reasons.append("abstract_count_below_20")
    if paper_count < config.requested_clusters * config.min_cluster_size:
        reasons.append("insufficient_rows_for_minimum_cluster_sizes")
    # 诚实目标簇数：按五方向门槛的每方向论文/摘要密度等比换算，只降不升。
    honest_target = min(
        config.requested_clusters,
        paper_count // config.papers_per_direction,
        abstract_count // config.abstracts_per_direction,
    )
    if honest_target < config.min_degraded_directions:
        reasons.append("evidence_supports_fewer_than_three_directions")
    if "p1_precision_gate_not_passed" in reasons:
        status = "P2_BLOCKED_BY_P1_PRECISION"
    elif honest_target >= config.requested_clusters:
        status = "P2_CORPUS_READY"
    elif honest_target >= config.min_degraded_directions:
        status = "P2_CORPUS_DEGRADED"
    else:
        status = "SYNTHESIS_INSUFFICIENT_EVIDENCE"
    return {
        "status": status,
        "can_output_five_directions": status == "P2_CORPUS_READY",
        "honest_target": honest_target,
        "degraded": status == "P2_CORPUS_DEGRADED",
        "paper_count": paper_count,
        "abstract_count": abstract_count,
        "max_clusters_by_size": paper_count // config.min_cluster_size,
        "reasons": reasons,
        "reasons_text": degradation_reasons_text(reasons),
        "config": asdict(config),
        "corpus_hash": snapshot.get("corpus_hash"),
        "p1_precision_gate_passed": bool(snapshot.get("p1_precision_gate_passed")),
    }


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "of", "on", "or", "our", "paper", "research", "study", "system", "systems", "the",
    "this", "to", "using", "we", "with",
}


def _text_tokens(text: str) -> list[str]:
    latin = [value for value in re.findall(r"[a-z0-9]+", text.casefold()) if len(value) > 1 and value not in _STOPWORDS]
    cjk = []
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        cjk.extend(run[index:index + 2] for index in range(max(0, len(run) - 1)))
    return latin + cjk


def _metadata_values(values: object) -> list[str]:
    result = []
    for value in values or []:
        if isinstance(value, dict):
            raw = value.get("name") or value.get("display_name") or value.get("id")
        else:
            raw = value
        cleaned = _clean_text(raw).casefold()
        if cleaned:
            result.append(cleaned)
    return result


def build_tfidf_features(papers: list[dict], config: P2ClusterConfig | None = None) -> dict[str, dict[str, float]]:
    """Build deterministic TF-IDF vectors with reviewed Topic/keyword features."""
    config = config or P2ClusterConfig()
    documents: dict[str, Counter] = {}
    for paper in papers:
        counts = Counter(_text_tokens(" ".join([paper.get("title", ""), paper.get("abstract", "")])))
        weighted = Counter({term: value * config.text_weight for term, value in counts.items()})
        for topic in _metadata_values(paper.get("topics")):
            weighted[f"topic::{topic}"] += config.topic_weight
        for keyword in _metadata_values(paper.get("keywords")):
            weighted[f"keyword::{keyword}"] += config.keyword_weight
        documents[paper["paper_id"]] = weighted
    document_frequency = Counter(term for counts in documents.values() for term in counts)
    total_documents = len(documents)
    vectors: dict[str, dict[str, float]] = {}
    for paper_id, counts in documents.items():
        vector = {}
        for term, count in counts.items():
            tf = 1.0 + math.log(max(float(count), 1e-12))
            idf = math.log((1.0 + total_documents) / (1.0 + document_frequency[term])) + 1.0
            vector[term] = tf * idf
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vectors[paper_id] = {term: value / norm for term, value in vector.items()}
    return vectors


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


def _average_linkage(left: tuple[str, ...], right: tuple[str, ...], vectors: dict[str, dict[str, float]]) -> float:
    scores = [_cosine(vectors[left_id], vectors[right_id]) for left_id in left for right_id in right]
    return sum(scores) / len(scores)


def _best_pair(clusters: list[tuple[str, ...]], vectors: dict[str, dict[str, float]], candidates: list[tuple[int, int]]) -> tuple[int, int]:
    ranked = []
    for left_index, right_index in candidates:
        left, right = clusters[left_index], clusters[right_index]
        ranked.append((-_average_linkage(left, right, vectors), left, right, left_index, right_index))
    return min(ranked)[-2:]


def _merge(clusters: list[tuple[str, ...]], left_index: int, right_index: int) -> list[tuple[str, ...]]:
    merged = tuple(sorted([*clusters[left_index], *clusters[right_index]]))
    return sorted(
        [cluster for index, cluster in enumerate(clusters) if index not in {left_index, right_index}] + [merged]
    )


def _percentage(value: object) -> float:
    if isinstance(value, dict):
        value = value.get("total")
    try:
        return max(0.0, min(100.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def compute_cluster_heat(
    clusters: list[dict], papers: list[dict], config: P2ClusterConfig, data_cutoff_date: str
) -> list[dict]:
    """Deterministic heat score: share / recent growth / citation velocity / match / source."""
    cutoff_year = int(str(data_cutoff_date or "0000")[:4] or 0)
    paper_map = {paper["paper_id"]: paper for paper in papers}
    total_papers = max(1, len(papers))
    weights = config.heat_weights
    for cluster in clusters:
        members = [paper_map[paper_id] for paper_id in cluster["paper_ids"]]
        count = max(1, len(members))
        share = len(members) / total_papers
        recent = sum(
            1 for item in members
            if cutoff_year and item["year"] and 0 <= cutoff_year - item["year"] < config.recent_window_years
        ) / count
        velocities = []
        for item in members:
            age = (cutoff_year - item["year"] + 1) if (cutoff_year and item["year"]) else 1
            velocities.append(item["citation_count"] / max(1, age))
        citation = min(1.0, (sum(velocities) / count) / config.max_citations_per_year_for_heat)
        match = sum(_percentage(item.get("p1_match_score")) for item in members) / count / 100.0
        source = sum(_percentage(item.get("source_quality")) for item in members) / count / 100.0
        heat = (
            weights[0] * share + weights[1] * recent + weights[2] * citation
            + weights[3] * match + weights[4] * source
        )
        cluster["heat"] = round(heat, 4)
        cluster["heat_components"] = {
            "paper_share": round(share, 4),
            "recent_growth": round(recent, 4),
            "citation_velocity": round(citation, 4),
            "match_score": round(match, 4),
            "source_quality": round(source, 4),
        }
    return clusters


def _language_counts(papers: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for paper in papers:
        language = paper.get("language") or "unknown"
        counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items()))


def deterministic_average_linkage(snapshot: dict, config: P2ClusterConfig | None = None) -> dict:
    """Create fixed-membership clusters; model calls are intentionally absent."""
    config = config or P2ClusterConfig()
    gate = assess_corpus_sufficiency(snapshot, config)
    cache_key = hashlib.sha256(
        "|".join([
            str(snapshot.get("corpus_hash")),
            config.version,
            str(snapshot.get("direction_profile_version")),
            str(snapshot.get("retrieval_version")),
            str(snapshot.get("score_version")),
            str(snapshot.get("data_cutoff_date")),
        ]).encode("utf-8")
    ).hexdigest()
    if gate["status"] not in {"P2_CORPUS_READY", "P2_CORPUS_DEGRADED"}:
        return {
            **gate, "clusters": [], "cache_key": cache_key, "cluster_config_version": config.version,
            "language_counts": _language_counts(list(snapshot.get("papers") or [])),
        }
    target = int(gate["honest_target"])
    papers = list(snapshot.get("papers") or [])
    if any(paper.get("relevance_tier") != "direct" for paper in papers):
        raise AssertionError("P2 corpus contains non-direct paper")
    vectors = build_tfidf_features(papers, config)
    clusters = [(paper_id,) for paper_id in sorted(vectors)]

    # Build deterministic minimum-size micro-clusters first, always using
    # average-linkage similarity and a lexical cluster-id tie-break.
    while any(len(cluster) < config.min_cluster_size for cluster in clusters):
        candidates = [
            (left, right)
            for left in range(len(clusters))
            for right in range(left + 1, len(clusters))
            if len(clusters[left]) < config.min_cluster_size
            and len(clusters[right]) < config.min_cluster_size
            and len(clusters[left]) + len(clusters[right]) <= config.min_cluster_size
        ]
        if not candidates:
            small_index = next(index for index, cluster in enumerate(clusters) if len(cluster) < config.min_cluster_size)
            candidates = [(min(small_index, other), max(small_index, other)) for other in range(len(clusters)) if other != small_index]
        left, right = _best_pair(clusters, vectors, candidates)
        clusters = _merge(clusters, left, right)

    if len(clusters) < target:
        return {
            **gate,
            "status": "SYNTHESIS_INSUFFICIENT_EVIDENCE",
            "can_output_five_directions": False,
            "reasons": [*gate["reasons"], "minimum_size_partition_has_too_few_clusters"],
            "reasons_text": degradation_reasons_text([*gate["reasons"], "minimum_size_partition_has_too_few_clusters"]),
            "clusters": [],
            "cache_key": cache_key,
            "cluster_config_version": config.version,
            "language_counts": _language_counts(papers),
        }
    while len(clusters) > target:
        candidates = [(left, right) for left in range(len(clusters)) for right in range(left + 1, len(clusters))]
        left, right = _best_pair(clusters, vectors, candidates)
        clusters = _merge(clusters, left, right)

    paper_map = {paper["paper_id"]: paper for paper in papers}
    output_clusters = []
    for index, cluster in enumerate(sorted(clusters, key=lambda value: (-len(value), value)), start=1):
        centroid = Counter()
        for paper_id in cluster:
            centroid.update(vectors[paper_id])
        feature_terms = [term for term, _ in sorted(centroid.items(), key=lambda item: (-item[1], item[0]))[:10]]
        output_clusters.append({
            "cluster_id": f"cluster_{index:03d}",
            "paper_ids": list(cluster),
            "paper_count": len(cluster),
            "feature_terms": feature_terms,
            "sample_titles": [paper_map[paper_id]["title"] for paper_id in cluster[:5]],
        })
    output_clusters = compute_cluster_heat(output_clusters, papers, config, str(snapshot.get("data_cutoff_date") or ""))
    status = "P2_CLUSTERING_COMPLETE" if target >= config.requested_clusters else "P2_CLUSTERING_DEGRADED"
    return {
        "status": status,
        "can_output_five_directions": target >= config.requested_clusters,
        "honest_target": target,
        "requested_clusters": config.requested_clusters,
        "degradation_reasons": gate["reasons"],
        "degradation_reasons_text": gate["reasons_text"],
        "corpus_hash": snapshot["corpus_hash"],
        "cluster_config_version": config.version,
        "cache_key": cache_key,
        "linkage": "average",
        "tie_break": "lexicographic_paper_ids",
        "feature_method": "tfidf_text_plus_topic_keyword",
        "heat_method": "weighted_share_recent_citation_match_source",
        "language_counts": _language_counts(papers),
        "clusters": output_clusters,
    }
