"""P1 paper normalization, conservative deduplication, hard gates and scoring."""
from __future__ import annotations

import hashlib
import html
import math
import re
import unicodedata
from copy import deepcopy
from datetime import date


SCORE_CONFIG_VERSION = "p1-metadata-score-1.0.0"
SCORE_WEIGHTS = {
    "semantic_relevance": 0.35,
    "lexical_coverage": 0.15,
    "source_quality": 0.15,
    "field_year_normalized_impact": 0.10,
    "recency": 0.10,
    "evidence_completeness": 0.10,
    "cross_source_agreement": 0.05,
}
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
    evidence_level = raw.get("evidence_level") or ("abstract" if abstract else "title_only")
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
        "document_type": raw.get("document_type") or "unknown",
        "citation_count": int(raw.get("citation_count") or 0),
        "topics": raw.get("topics") or [],
        "external_ids": external_ids,
        "providers": sources,
        "metadata_source": provider,
        "field_sources": field_sources,
        "integrity_status": "retracted" if raw.get("is_retracted") else raw.get("integrity_status", "unknown"),
        "is_correction": bool(raw.get("is_correction")),
        "evidence_level": evidence_level,
        "fulltext_url": raw.get("fulltext_url") or raw.get("oa_url"),
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
    for field in ("title", "abstract", "authors", "year", "publication_date", "published_date", "doi", "url", "official_url", "source_title", "journal", "document_type", "fulltext_url"):
        current = target.get(field)
        candidate = incoming.get(field)
        if candidate not in (None, "", []) and (current in (None, "", []) or field == "abstract" and len(candidate) > len(current or "")):
            target[field] = deepcopy(candidate)
        if candidate not in (None, "", []):
            target.setdefault("field_sources", {}).setdefault(field, [])
            if provider not in target["field_sources"][field]:
                target["field_sources"][field].append(provider)
    target["citation_count"] = max(int(target.get("citation_count") or 0), int(incoming.get("citation_count") or 0))
    if target.get("fulltext_url"):
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


def qualify_source(record: dict, journal_index: dict, allowed_pools: set[str]) -> None:
    journal = None
    for issn in record.get("source_issns", []):
        journal = journal_index["by_issn"].get(str(issn).upper())
        if journal:
            break
    if not journal:
        journal = journal_index["by_title"].get(title_key(record.get("source_title")))
    if journal and allowed_pools.intersection(journal.get("pool_ids", [])):
        record["journal_id"] = journal["journal_id"]
        record["source_title"] = journal["canonical_title"]
        record["journal"] = journal["canonical_title"]
        record["journal_ranking"] = journal["ranking_levels"]
        record["journal_pool_ids"] = journal["pool_ids"]
        record["source_qualified"] = True
        record["verified_by"] = ["local_journal_whitelist", *record["providers"]]
    else:
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
    if not record.get("source_qualified"):
        reasons.append("source_not_qualified")
    # External metadata is data, never an instruction.  Store it without executing it.
    record["untrusted_text_isolated"] = True
    return not reasons, reasons


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
    tokens = _tokens(profile, query)
    title = (record.get("title") or "").casefold()
    body = f"{title} {(record.get('abstract') or '').casefold()}"
    hits = {token for token in tokens if token in body}
    title_hits = {token for token in tokens if token in title}
    lexical = min(100.0, 100.0 * len(hits) / max(1, min(len(tokens), 8)))
    semantic_proxy = min(100.0, 18.0 + lexical * 0.65 + min(25.0, len(title_hits) * 8.0))
    source = _source_quality(record.get("journal_ranking", []))
    citations = int(record.get("citation_count") or 0)
    age = max(0, to_year - int(record.get("year") or from_year))
    impact = min(100.0, 100.0 * math.log1p(citations) / math.log(101))
    recency = max(20.0, 100.0 - age * (80.0 / max(1, to_year - from_year)))
    evidence = {"fulltext": 100.0, "abstract": 72.0, "title_only": 25.0}.get(record.get("evidence_level"), 10.0)
    agreement = min(100.0, 35.0 + 32.5 * (len(record.get("providers", [])) - 1))
    components = {
        "semantic_relevance": round(semantic_proxy, 2),
        "lexical_coverage": round(lexical, 2),
        "source_quality": round(source, 2),
        "field_year_normalized_impact": round(impact, 2),
        "recency": round(recency, 2),
        "evidence_completeness": round(evidence, 2),
        "cross_source_agreement": round(agreement, 2),
    }
    total = round(sum(components[key] * SCORE_WEIGHTS[key] for key in SCORE_WEIGHTS), 2)
    band = "high" if total >= 85 else "eligible" if total >= 70 else "boundary" if total >= 55 else "reject"
    return {
        "config_version": SCORE_CONFIG_VERSION,
        "total": total,
        "band": band,
        "components": components,
        "weights": SCORE_WEIGHTS,
        "semantic_method": "deterministic_lexical_proxy_pending_embedding_calibration",
        "impact_method": "bounded_raw_citation_proxy_pending_field_year_calibration",
        "threshold_calibration_status": "uncalibrated",
    }
