"""Deterministic multilingual hybrid reranker for P1.

This implementation is deliberately dependency-light.  It exposes the same
component boundaries as a future embedding/cross-encoder backend, while never
claiming that lexical overlap is an embedding score.
"""
from __future__ import annotations

import math
import re
from collections import Counter


RERANK_VERSION = "p1-directness-reranker-2.1.0"
# Conservative, label-safe title patterns for review/meta-science demotion.
# Deliberately excludes "bibliometric": a human-labeled relevant paper uses it
# in its title, so type alone cannot demote a bibliometric study of the
# direction's own phenomenon.
REVIEW_TITLE_PATTERNS = (
    "literature review",
    "systematic review",
    "meta-analysis",
    "review of the literature",
    "evolving landscape",
    "research landscape",
    "research agenda",
)
RERANK_WEIGHTS = {
    "focality": 0.30,
    "multilingual_semantic_similarity": 0.22,
    "facet_coverage": 0.18,
    "topic_route_match": 0.10,
    "evidence_completeness": 0.07,
    "source_direction_fit": 0.03,
    "source_quality_prior": 0.02,
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


def _ordered_latin_match(phrase: str, text: str, max_gap: int = 3) -> tuple[bool, str, int | None]:
    """Match every phrase token in order and within a bounded word window."""
    phrase_tokens = re.findall(r"[a-z0-9]+", phrase.casefold())
    document_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    if not phrase_tokens or not document_tokens:
        return False, "none", None
    width = len(phrase_tokens)
    for start in range(0, len(document_tokens) - width + 1):
        if document_tokens[start:start + width] == phrase_tokens:
            return True, "exact_phrase", 0
    if width == 1:
        return False, "none", None
    for start, token in enumerate(document_tokens):
        if token != phrase_tokens[0]:
            continue
        positions = [start]
        cursor = start
        matched = True
        for expected in phrase_tokens[1:]:
            found = next(
                (index for index in range(cursor + 1, min(len(document_tokens), cursor + max_gap + 2))
                 if document_tokens[index] == expected),
                None,
            )
            if found is None:
                matched = False
                break
            positions.append(found)
            cursor = found
        if matched:
            return True, "ordered_proximity", positions[-1] - positions[0] - width + 1
    return False, "none", None


def phrase_match_detail(phrase: str, text: str, max_gap: int = 3) -> dict:
    """Return positional phrase evidence; unordered token overlap is never a match."""
    normalized_phrase = str(phrase or "").strip().casefold()
    normalized_text = str(text or "").casefold()
    if not normalized_phrase or not normalized_text:
        return {"matched": False, "method": "none", "gap": None}
    if re.search(r"[\u4e00-\u9fff]", normalized_phrase):
        compact_phrase = re.sub(r"\s+", "", normalized_phrase)
        compact_text = re.sub(r"\s+", "", normalized_text)
        matched = compact_phrase in compact_text
        return {"matched": matched, "method": "exact_cjk_phrase" if matched else "none", "gap": 0 if matched else None}
    matched, method, gap = _ordered_latin_match(normalized_phrase, normalized_text, max_gap=max_gap)
    return {"matched": matched, "method": method, "gap": gap}


def review_title_signal(record: dict) -> bool:
    """Title-only meta-science signal; false for empirical studies by construction."""
    title = str(record.get("title") or "").casefold()
    return any(pattern in title for pattern in REVIEW_TITLE_PATTERNS)


def _facet_match(facet: str, text: str) -> bool:
    return bool(phrase_match_detail(facet, text)["matched"])


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
    return structured_score


def focality_score(record: dict, profile: dict) -> tuple[float, dict]:
    """Measure whether the direction is the paper's focus, independent of source prestige."""
    facets = profile.get("facets", {})
    title = str(record.get("title") or "")
    abstract = str(record.get("abstract") or "")
    document = " ".join(filter(None, [title, abstract]))
    core = _facets_for_document(facets.get("core_phenomena", []), document)
    contexts = _facets_for_document(facets.get("required_context_any", []), document)
    title_core = [facet for facet in core if _facet_match(facet, title)]
    abstract_core = [facet for facet in core if _facet_match(facet, abstract)]
    context_hits = [facet for facet in contexts if _facet_match(facet, document)]
    occurrences = sum(document.casefold().count(str(facet).casefold()) for facet in set([*title_core, *abstract_core]))
    score = 0.0
    if title_core:
        score += 45.0
    if abstract_core:
        score += 30.0
    if context_hits:
        score += 15.0
    score += min(10.0, max(0, occurrences - 1) * 2.5)
    evidence = {
        "title_core_matches": title_core,
        "abstract_core_matches": abstract_core,
        "context_matches": context_hits,
        "core_occurrences": occurrences,
    }
    return min(100.0, score), evidence


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
    focality, focality_evidence = focality_score(record, profile)
    components = {
        "focality": round(focality, 2),
        "topic_route_match": round(_topic_route_score(record, profile), 2),
        "multilingual_semantic_similarity": round(semantic, 2),
        "facet_coverage": round(facet_coverage, 2),
        "source_direction_fit": round(source_fit, 2),
        "source_quality_prior": round(float(record.get("source_quality") or 0.0), 2),
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
        "focality_evidence": focality_evidence,
        "matched_facets": facet_hits,
        "confidence": "high" if record.get("abstract") and len(facet_hits) >= 2 else "medium" if facet_hits else "low",
        "label": "high" if total >= 72 else "medium" if total >= 52 else "low",
    }
