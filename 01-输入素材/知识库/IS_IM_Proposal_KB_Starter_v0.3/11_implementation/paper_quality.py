"""P1 paper normalization, conservative deduplication, hard gates and scoring."""
from __future__ import annotations

import hashlib
import html
import math
import re
import unicodedata
from copy import deepcopy
from dataclasses import asdict, dataclass

from semantic_reranker import RERANK_VERSION, RERANK_WEIGHTS, hybrid_rerank_score


SCORE_CONFIG_VERSION = RERANK_VERSION
SCORE_WEIGHTS = RERANK_WEIGHTS
ZERO_RESULT_CAUSES = {
    "route_missing", "provider_empty", "rate_limited", "quality_gate_too_strict",
    "language_coverage_gap", "query_too_narrow",
}


def clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value).strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value).strip().rstrip(".,;)")
    return value or None


def clean_text(value: str | None) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def title_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", clean_text(value).casefold())


def infer_language(title: str, declared: str | None) -> str:
    if declared in {"zh", "en"}:
        return declared
    cjk = len(re.findall(r"[\u4e00-\u9fff]", title))
    return "zh" if cjk >= max(2, len(title) // 5) else "en"


def normalize_record(raw: dict, provider: str) -> dict:
    title = clean_text(raw.get("title"))
    abstract = clean_text(raw.get("abstract")) or None
    authors = [clean_text(value) for value in raw.get("authors", []) if clean_text(value)]
    year = raw.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    doi = clean_doi(raw.get("doi"))
    external_ids = dict(raw.get("external_ids") or {})
    if raw.get("external_id"):
        external_ids[provider] = str(raw["external_id"])
    seed = doi or f"{title_key(title)}|{year}|{title_key(authors[0] if authors else '')}"
    paper_id = "paper_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
    oa_pdf_url = raw.get("oa_pdf_url")
    verified_fulltext = bool(raw.get("verified_fulltext_available") and (oa_pdf_url or raw.get("fulltext_url")))
    evidence_level = "fulltext" if verified_fulltext else "abstract" if abstract else "title_only"
    source_title = clean_text(raw.get("source_title") or raw.get("journal")) or None
    publication_date = raw.get("publication_date") or raw.get("published_date")
    sources = [provider]
    field_sources = {
        key: [provider]
        for key, value in {
            "title": title, "abstract": abstract, "authors": authors, "year": year,
            "doi": doi, "source_title": source_title, "citation_count": raw.get("citation_count"),
        }.items() if value not in (None, "", [])
    }
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "publication_date": publication_date,
        "published_date": publication_date,
        "language": infer_language(title, raw.get("language")),
        "doi": doi,
        "url": raw.get("url") or (f"https://doi.org/{doi}" if doi else None),
        "official_url": raw.get("url") or (f"https://doi.org/{doi}" if doi else None),
        "source_title": source_title,
        "journal": source_title,
        "source_issns": sorted(set(raw.get("source_issns") or [])),
        "source_id": raw.get("source_id"),
        "document_type": raw.get("document_type") or "unknown",
        "citation_count": int(raw.get("citation_count") or 0),
        "citation_normalized_percentile": raw.get("citation_normalized_percentile"),
        "fwci": raw.get("fwci"),
        "primary_topic": raw.get("primary_topic") or {},
        "topics": raw.get("topics") or [],
        "keywords": raw.get("keywords") or [],
        "external_ids": external_ids,
        "providers": sources,
        "metadata_source": provider,
        "field_sources": field_sources,
        "integrity_status": "retracted" if raw.get("is_retracted") else raw.get("integrity_status", "unknown"),
        "is_correction": bool(raw.get("is_correction")),
        "evidence_level": evidence_level,
        "oa_pdf_url": oa_pdf_url,
        "oa_landing_page_url": raw.get("oa_landing_page_url") or raw.get("oa_url"),
        "doi_landing_url": raw.get("doi_landing_url") or (f"https://doi.org/{doi}" if doi else None),
        "verified_fulltext_available": verified_fulltext,
        "fulltext_url": (oa_pdf_url or raw.get("fulltext_url")) if verified_fulltext else None,
        "query_lane_ids": list(dict.fromkeys(raw.get("query_lane_ids") or [])),
        "provider_payload_refs": raw.get("provider_payload_refs") or [],
    }


def _merge(target: dict, incoming: dict) -> None:
    provider = incoming["providers"][0]
    for item in incoming["providers"]:
        if item not in target["providers"]:
            target["providers"].append(item)
    target["external_ids"].update(incoming.get("external_ids", {}))
    target["source_issns"] = sorted(set(target.get("source_issns", []) + incoming.get("source_issns", [])))
    if incoming.get("integrity_status") in {"retracted", "expression_of_concern"}:
        target["integrity_status"] = incoming["integrity_status"]
    for field in ("title", "abstract", "authors", "year", "publication_date", "published_date", "doi", "url", "official_url", "source_title", "journal", "source_id", "document_type", "oa_pdf_url", "oa_landing_page_url", "doi_landing_url", "fulltext_url", "primary_topic", "topics", "keywords", "citation_normalized_percentile", "fwci"):
        current = target.get(field)
        candidate = incoming.get(field)
        if candidate not in (None, "", []) and (current in (None, "", []) or field == "abstract" and len(candidate) > len(current or "")):
            target[field] = deepcopy(candidate)
        if candidate not in (None, "", []):
            target.setdefault("field_sources", {}).setdefault(field, [])
            if provider not in target["field_sources"][field]:
                target["field_sources"][field].append(provider)
    target["citation_count"] = max(int(target.get("citation_count") or 0), int(incoming.get("citation_count") or 0))
    target["query_lane_ids"] = list(dict.fromkeys([*target.get("query_lane_ids", []), *incoming.get("query_lane_ids", [])]))
    target["provider_payload_refs"] = list(dict.fromkeys([*target.get("provider_payload_refs", []), *incoming.get("provider_payload_refs", [])]))
    target["verified_fulltext_available"] = bool(target.get("verified_fulltext_available") or incoming.get("verified_fulltext_available"))
    if target.get("verified_fulltext_available") and target.get("fulltext_url"):
        target["evidence_level"] = "fulltext"
    elif target.get("abstract"):
        target["evidence_level"] = "abstract"


def dedupe_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    by_doi: dict[str, dict] = {}
    by_external: dict[tuple[str, str], dict] = {}
    by_exact: dict[tuple[str, int | None, str], dict] = {}
    log: list[dict] = []
    for record in records:
        match = by_doi.get(record.get("doi")) if record.get("doi") else None
        reason = "doi" if match else ""
        if not match:
            for provider, external_id in record.get("external_ids", {}).items():
                match = by_external.get((provider, external_id))
                if match:
                    reason = "external_id"
                    break
        first_author = title_key(record.get("authors", [""])[0] if record.get("authors") else "")
        exact = (title_key(record.get("title")), record.get("year"), first_author)
        if not match and exact[0] and exact[1] and exact[2]:
            match = by_exact.get(exact)
            reason = "normalized_title_year_first_author" if match else ""
        if match:
            log.append({"action": "merged", "reason": reason, "kept_paper_id": match["paper_id"], "incoming_paper_id": record["paper_id"]})
            _merge(match, record)
            continue
        # Similar titles are deliberately only candidates; P1 forbids silent fuzzy merges.
        compact = title_key(record.get("title"))
        for previous in kept[-100:]:
            other = title_key(previous.get("title"))
            if record.get("year") == previous.get("year") and compact and other and (compact in other or other in compact) and compact != other:
                log.append({"action": "review_candidate", "reason": "fuzzy_title_not_auto_merged", "paper_ids": [previous["paper_id"], record["paper_id"]]})
                break
        kept.append(record)
        if record.get("doi"):
            by_doi[record["doi"]] = record
        for provider, external_id in record.get("external_ids", {}).items():
            by_external[(provider, external_id)] = record
        if exact[0] and exact[1] and exact[2]:
            by_exact[exact] = record
    return kept, log


def build_journal_index(registry: dict) -> dict:
    by_issn: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    for journal in registry.get("journals", []):
        if not journal.get("default_eligible", True):
            continue
        by_title[title_key(journal.get("canonical_title"))] = journal
        for issn in journal.get("issns", []):
            by_issn[issn.upper()] = journal
    return {"by_issn": by_issn, "by_title": by_title}


def qualify_source(record: dict, journal_index: dict, allowed_pools: set[str], profile: dict | None = None) -> None:
    journal = None
    for issn in record.get("source_issns", []):
        journal = journal_index["by_issn"].get(str(issn).upper())
        if journal:
            break
    if not journal:
        journal = journal_index["by_title"].get(title_key(record.get("source_title")))
    matched_pools = allowed_pools.intersection(journal.get("pool_ids", [])) if journal else set()
    policy = (profile or {}).get("source_policy", {})
    tier_a = set(policy.get("tier_a_pool_ids", []))
    tier_b = set(policy.get("tier_b_pool_ids", []))
    adjacent = set(policy.get("adjacent_pool_ids", []))
    zh_pools = set(policy.get("zh_pool_ids", []))
    if journal and matched_pools:
        record["journal_id"] = journal["journal_id"]
        record["source_title"] = journal["canonical_title"]
        record["journal"] = journal["canonical_title"]
        record["journal_ranking"] = journal["ranking_levels"]
        record["journal_pool_ids"] = journal["pool_ids"]
        if matched_pools.intersection(tier_a):
            source_tier = "A"
        elif matched_pools.intersection(tier_b):
            source_tier = "B"
        # The Chinese lane has its own reviewed high-quality journal pools.
        # Treat those pools as direction-qualified Tier B instead of UNKNOWN;
        # content relevance and language quota remain independent checks.
        elif matched_pools.intersection(zh_pools):
            source_tier = "B"
        elif matched_pools.intersection(adjacent) or not policy:
            source_tier = "ADJACENT"
        else:
            source_tier = "UNKNOWN"
        record["source_tier"] = source_tier
        record["source_quality"] = _source_quality(journal["ranking_levels"])
        record["source_direction_fit"] = {"A": 100.0, "B": 82.0, "ADJACENT": 45.0, "UNKNOWN": 0.0}[source_tier]
        record["source_qualified"] = source_tier in {"A", "B", "ADJACENT"}
        record["verified_by"] = ["local_journal_whitelist", *record["providers"]]
    else:
        record["source_tier"] = "UNKNOWN"
        record["source_quality"] = 0.0
        record["source_direction_fit"] = 0.0
        record["source_qualified"] = False


def quality_gate(record: dict, profile: dict, from_year: int, to_year: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if record.get("integrity_status") in {"retracted", "expression_of_concern"} or record.get("is_correction"):
        reasons.append("retraction_or_correction")
    for field in ("title", "year", "source_title"):
        if record.get(field) in (None, ""):
            reasons.append(f"missing_{field}")
    if record.get("year") and not (from_year <= record["year"] <= to_year):
        reasons.append("outside_time_window")
    allowed_types = set(profile.get("document_types", []))
    if record.get("document_type") not in allowed_types:
        reasons.append("wrong_document_type")
    # Unknown sources are routed to manual_review later; the integrity/type/date
    # checkpoint remains separate from source direction fit.
    # External metadata is data, never an instruction.  Store it without executing it.
    record["untrusted_text_isolated"] = True
    return not reasons, reasons


@dataclass(frozen=True)
class BoundaryResult:
    decision: str
    matched_core_facets: tuple[str, ...]
    matched_context_facets: tuple[str, ...]
    matched_negative_facets: tuple[str, ...]
    topic_matches: tuple[str, ...]
    missing_required_facets: tuple[str, ...]
    evidence: tuple[str, ...]

    def as_dict(self) -> dict:
        payload = asdict(self)
        return {key: list(value) if isinstance(value, tuple) else value for key, value in payload.items()}


def _facet_match(facet: str, text: str) -> bool:
    facet = clean_text(facet).casefold()
    if not facet:
        return False
    if facet in text:
        return True
    tokens = [token for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", facet) if token not in {"and", "or", "the", "of", "in", "only"}]
    hits = sum(token in text for token in tokens)
    return bool(tokens) and hits / len(tokens) >= 0.67


def evaluate_boundary(record: dict, profile: dict) -> BoundaryResult:
    facets = profile.get("facets", {})
    core = tuple(facets.get("core_phenomena", []))
    contexts = tuple(facets.get("required_context_any", []))
    negatives = tuple(facets.get("negative_contexts", []))
    topic_names = tuple(
        clean_text(topic.get("name"))
        for topic in [record.get("primary_topic") or {}, *(record.get("topics") or [])]
        if topic.get("name")
    )
    keyword_names = [clean_text(item.get("name")) for item in record.get("keywords", []) if item.get("name")]
    text = " ".join(filter(None, [record.get("title"), record.get("abstract"), *topic_names, *keyword_names])).casefold()
    matched_core = tuple(facet for facet in core if _facet_match(facet, text))
    matched_context = tuple(facet for facet in contexts if _facet_match(facet, text))
    matched_negative = tuple(facet for facet in negatives if _facet_match(facet, text))
    approved = {
        str(value).rstrip("/").rsplit("/", 1)[-1]
        for key in ("approved_topic_ids", "approved_primary_topic_ids")
        for value in profile.get("openalex_routes", {}).get(key, [])
    }
    topic_matches = tuple(
        str(topic.get("id")).rstrip("/").rsplit("/", 1)[-1]
        for topic in [record.get("primary_topic") or {}, *(record.get("topics") or [])]
        if topic.get("id") and str(topic.get("id")).rstrip("/").rsplit("/", 1)[-1] in approved
    )
    policy = profile.get("boundary_policy", {})
    missing: list[str] = []
    if policy.get("require_core_phenomenon", True) and not (matched_core or topic_matches):
        missing.append("core_phenomenon")
    if policy.get("require_context_any", True) and not matched_context:
        missing.append("required_context")
    evidence = tuple(filter(None, [
        "title+abstract" if record.get("abstract") else "title_only",
        "approved_topic" if topic_matches else "",
        "negative_context" if matched_negative else "",
    ]))
    if matched_negative and not (len(matched_core) >= 1 and len(matched_context) >= 1):
        decision = "reject"
    elif missing:
        decision = "manual_review" if not record.get("abstract") and policy.get("insufficient_metadata_action", "manual_review") == "manual_review" else "reject"
    else:
        decision = "pass"
    return BoundaryResult(decision, matched_core, matched_context, matched_negative, topic_matches, tuple(missing), evidence)


def _tokens(profile: dict, query: str) -> set[str]:
    text = " ".join([query, *profile.get("synonyms", [])]).casefold()
    return {token for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", text) if token not in {"and", "or", "the", "of", "in", "for", "with", "research", "systems", "system"}}


def _source_quality(rankings: list[str]) -> float:
    text = " ".join(rankings).upper()
    if "UTD24" in text or "FMS_INT_A" in text or "FMS_CN_A" in text:
        return 100.0
    if "FMS_INT_B" in text or "FMS_CN_B" in text or "CSSCI" in text:
        return 85.0
    if "FMS_INT_C" in text or "FMS_CN_C" in text or "PKU" in text:
        return 72.0
    return 60.0


def score_record(record: dict, profile: dict, query: str, from_year: int, to_year: int) -> dict:
    score = hybrid_rerank_score(record, profile, query, from_year, to_year)
    score["threshold_calibration_status"] = "ranking_not_fixed_eligibility_threshold"
    score["band"] = score["label"]
    return score
