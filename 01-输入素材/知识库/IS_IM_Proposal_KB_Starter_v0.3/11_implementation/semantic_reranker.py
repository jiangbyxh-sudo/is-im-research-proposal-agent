"""Deterministic multilingual hybrid reranker for P1.

This implementation is deliberately dependency-light.  It exposes the same
component boundaries as a future embedding/cross-encoder backend, while never
claiming that lexical overlap is an embedding score.
"""
from __future__ import annotations

import math
import re
from collections import Counter


RERANK_VERSION = "p1-hybrid-reranker-1.0.1"
RERANK_WEIGHTS = {
    "topic_route_match": 0.30,
    "multilingual_semantic_similarity": 0.30,
    "facet_coverage": 0.15,
    "source_direction_fit": 0.12,
    "evidence_completeness": 0.05,
    "recency": 0.04,
    "normalized_impact": 0.04,
}
GENERIC_EN = {
    "a", "an", "and", "ai", "computer", "data", "digital", "for", "human",
    "in", "information", "of", "on", "research", "system", "systems", "the",
    "to", "using", "with",
}
GENERIC_ZH = {"人工智能", "信息", "系统", "研究", "数据", "数字", "用户", "影响", "分析"}


def _latin_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.casefold()) if len(token) > 1 and token not in GENERIC_EN]


def _cjk_ngrams(text: str) -> list[str]:
    runs = re.findall(r"[\u4e00-\u9fff]+", text)
    grams: list[str] = []
    for run in runs:
        if run in GENERIC_ZH:
            continue
        grams.extend(run[index:index + 2] for index in range(max(0, len(run) - 1)))
        grams.extend(run[index:index + 3] for index in range(max(0, len(run) - 2)))
    return [gram for gram in grams if gram not in GENERIC_ZH]


def multilingual_tokens(text: str) -> Counter:
    tokens = _latin_tokens(text) + _cjk_ngrams(text)
    return Counter(tokens)


def weighted_overlap(query: str, document: str) -> float:
    query_tokens = multilingual_tokens(query)
    document_tokens = multilingual_tokens(document)
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = sum(min(count, document_tokens.get(token, 0)) for token, count in query_tokens.items())
    return min(100.0, 100.0 * overlap / max(1, sum(query_tokens.values())))


def _facet_match(facet: str, text: str) -> bool:
    facet = str(facet or "").strip().casefold()
    if not facet:
        return False
    if facet in text:
        return True
    score = weighted_overlap(facet, text)
    meaningful = len(_latin_tokens(facet)) + len(_cjk_ngrams(facet))
    return meaningful >= 1 and score >= 67.0


def _facets_for_document(facets: list[str], text: str) -> list[str]:
    """Use one script's aliases without penalizing bilingual profiles twice."""
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_tokens = len(re.findall(r"[a-z]{2,}", text.casefold()))
    prefer_cjk = cjk_chars >= 4 and cjk_chars >= latin_tokens
    if prefer_cjk:
        selected = [facet for facet in facets if re.search(r"[\u4e00-\u9fff]", str(facet))]
    else:
        selected = [facet for facet in facets if re.search(r"[a-z]", str(facet).casefold())]
    return selected or list(facets)


def _topic_route_score(record: dict, profile: dict) -> float:
    routes = profile.get("openalex_routes", {})
    approved = {
        str(value).rstrip("/").rsplit("/", 1)[-1]
        for key in ("approved_topic_ids", "approved_primary_topic_ids")
        for value in routes.get(key, [])
    }
    observed = {
        str(topic.get("id") or "").rstrip("/").rsplit("/", 1)[-1]
        for topic in [record.get("primary_topic") or {}, *(record.get("topics") or [])]
        if topic.get("id")
    }
    if approved:
        return 100.0 if approved.intersection(observed) else 0.0
    topic_text = " ".join(
        str(topic.get("name") or "") for topic in [record.get("primary_topic") or {}, *(record.get("topics") or [])]
    )
    core = profile.get("facets", {}).get("core_phenomena", [])
    structured_score = max((weighted_overlap(facet, topic_text) for facet in core), default=0.0)
    if structured_score:
        return structured_score
    # Metadata-only providers may omit OpenAlex topics.  Preserve explicit core
    # phrase evidence without pretending it is a reviewed Topic-ID hit.
    text = " ".join(filter(None, [record.get("title"), record.get("abstract")]))
    return 80.0 if any(_facet_match(facet, text.casefold()) for facet in core) else 0.0


def _normalized_impact(record: dict) -> tuple[float, str]:
    percentile = record.get("citation_normalized_percentile")
    try:
        if percentile is not None:
            value = float(percentile)
            return max(0.0, min(100.0, value * 100.0 if value <= 1 else value)), "citation_normalized_percentile"
    except (TypeError, ValueError):
        pass
    fwci = record.get("fwci")
    try:
        if fwci is not None:
            return min(100.0, 50.0 + 25.0 * math.log(max(0.01, float(fwci)), 2)), "fwci_log_transform"
    except (TypeError, ValueError):
        pass
    return 0.0, "unavailable_not_raw_citation_substitute"


def hybrid_rerank_score(record: dict, profile: dict, query: str, from_year: int, to_year: int) -> dict:
    text = " ".join(filter(None, [record.get("title"), record.get("abstract")])).casefold()
    facets = profile.get("facets", {})
    core = _facets_for_document(facets.get("core_phenomena", []), text)
    contexts = _facets_for_document(facets.get("required_context_any", []), text)
    facet_values = [*core, *contexts]
    facet_hits = [facet for facet in facet_values if _facet_match(facet, text)]
    facet_coverage = 100.0 * len(facet_hits) / max(1, len(facet_values))
    query_text = " ".join([query, *core, *contexts])
    semantic = weighted_overlap(query_text, text)
    source_fit = {"A": 100.0, "B": 82.0, "ADJACENT": 45.0, "UNKNOWN": 0.0}.get(record.get("source_tier"), 0.0)
    evidence = 100.0 if record.get("verified_fulltext_available") else 78.0 if record.get("abstract") else 35.0
    age = max(0, to_year - int(record.get("year") or from_year))
    recency = max(0.0, 100.0 - age * (100.0 / max(1, to_year - from_year + 1)))
    impact, impact_method = _normalized_impact(record)
    components = {
        "topic_route_match": round(_topic_route_score(record, profile), 2),
        "multilingual_semantic_similarity": round(semantic, 2),
        "facet_coverage": round(facet_coverage, 2),
        "source_direction_fit": round(source_fit, 2),
        "evidence_completeness": round(evidence, 2),
        "recency": round(recency, 2),
        "normalized_impact": round(impact, 2),
    }
    total = round(sum(components[key] * RERANK_WEIGHTS[key] for key in RERANK_WEIGHTS), 2)
    return {
        "config_version": RERANK_VERSION,
        "total": total,
        "components": components,
        "weights": RERANK_WEIGHTS,
        "semantic_method": "deterministic_multilingual_weighted_overlap_not_embedding",
        "normalized_impact_method": impact_method,
        "matched_facets": facet_hits,
        "confidence": "high" if record.get("abstract") and len(facet_hits) >= 2 else "medium" if facet_hits else "low",
        "label": "core" if total >= 72 else "relevant" if total >= 52 else "peripheral" if total >= 35 else "irrelevant",
    }
