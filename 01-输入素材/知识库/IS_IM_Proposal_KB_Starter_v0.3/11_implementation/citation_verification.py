"""Live-metadata citation verification without making relevance decisions."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Protocol
from urllib.parse import quote

from citation_graph_provider import canonical_stable_id, stable_identifiers
from openalex_provider import OpenAlexPaperProvider, OpenAlexTransport
from paper_discovery_provider import CrossrefTransport
from paper_quality import clean_doi, clean_text, title_key


CITATION_VERIFICATION_VERSION = "citation-verification-1.0.0"


class CitationMetadataProvider(Protocol):
    provider_name: str

    def lookup(self, candidate: dict) -> dict: ...


def _year(message: dict) -> int | None:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


class CrossrefCitationMetadataProvider:
    provider_name = "crossref"
    endpoint = "https://api.crossref.org/works"

    def __init__(self, transport: CrossrefTransport | None = None) -> None:
        self.transport = transport or CrossrefTransport(
            mailto=os.getenv("PROPOSAL_CROSSREF_MAILTO") or None,
            timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "18")),
        )

    def lookup(self, candidate: dict) -> dict:
        doi = stable_identifiers(candidate).get("doi")
        if not doi:
            return {"provider": self.provider_name, "status": "NOT_APPLICABLE", "reason": "doi_missing"}
        payload = self.transport.get(f"{self.endpoint}/{quote(doi, safe='')}", {})
        message = payload.get("message") or {}
        title = clean_text(_first(message.get("title")))
        authors = []
        for author in message.get("author") or []:
            name = clean_text(" ".join(value for value in (author.get("given"), author.get("family")) if value))
            if name:
                authors.append(name)
        relation_text = json.dumps({
            "update_to": message.get("update-to"),
            "relation": message.get("relation"),
            "subtype": message.get("subtype"),
        }, ensure_ascii=False).casefold()
        retracted = "retract" in relation_text
        return {
            "provider": self.provider_name,
            "status": "RETRACTED" if retracted else "RESOLVED",
            "record": {
                "title": title,
                "authors": authors,
                "year": _year(message),
                "doi": clean_doi(message.get("DOI")) or doi,
                "source_title": clean_text(_first(message.get("container-title"))),
                "integrity_status": "retracted" if retracted else "unknown",
            },
            "transport": payload.get("_transport_meta") or {},
        }


def _first(value: object) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


class OpenAlexCitationMetadataProvider:
    provider_name = "openalex"
    endpoint = "https://api.openalex.org/works"

    def __init__(self, transport: OpenAlexTransport | None = None) -> None:
        self.transport = transport or OpenAlexTransport()

    def lookup(self, candidate: dict) -> dict:
        identifiers = stable_identifiers(candidate)
        identifier = identifiers.get("openalex") or (f"doi:{identifiers['doi']}" if identifiers.get("doi") else None)
        if not identifier:
            return {"provider": self.provider_name, "status": "NOT_APPLICABLE", "reason": "stable_id_missing"}
        payload, transport_meta = self.transport.get(
            f"{self.endpoint}/{quote(identifier, safe=':')}", {"select": "id,display_name,authorships,publication_year,doi,primary_location,is_retracted"},
        )
        raw = OpenAlexPaperProvider._record(payload, "citation_verification")
        record = {
            "title": clean_text(raw.get("title")),
            "authors": list(raw.get("authors") or []),
            "year": raw.get("year"),
            "doi": clean_doi(raw.get("doi")),
            "source_title": clean_text(raw.get("source_title")),
            "openalex_id": stable_identifiers(raw).get("openalex"),
            "integrity_status": "retracted" if raw.get("is_retracted") else "unknown",
        }
        return {
            "provider": self.provider_name,
            "status": "RETRACTED" if record["integrity_status"] == "retracted" else "RESOLVED",
            "record": record,
            "transport": transport_meta,
        }


@dataclass
class CitationVerificationResult:
    status: str
    candidates: list[dict] = field(default_factory=list)
    provider_log: list[dict] = field(default_factory=list)
    audit: dict = field(default_factory=dict)


def _metadata_mismatches(candidate: dict, record: dict) -> list[str]:
    mismatches: list[str] = []
    expected_title = title_key(candidate.get("title"))
    actual_title = title_key(record.get("title"))
    title_similarity = SequenceMatcher(None, expected_title, actual_title).ratio() if expected_title and actual_title else 0.0
    if title_similarity < 0.90:
        mismatches.append("TITLE_MISMATCH")
    expected_doi = clean_doi(candidate.get("doi"))
    actual_doi = clean_doi(record.get("doi"))
    if expected_doi and actual_doi and expected_doi != actual_doi:
        mismatches.append("DOI_MISMATCH")
    expected_year, actual_year = candidate.get("year"), record.get("year")
    if expected_year and actual_year:
        try:
            if abs(int(expected_year) - int(actual_year)) > 1:
                mismatches.append("YEAR_MISMATCH")
        except (TypeError, ValueError):
            mismatches.append("YEAR_MISMATCH")
    return mismatches


class CitationVerifier:
    def __init__(self, providers: list[CitationMetadataProvider]) -> None:
        self.providers = list(providers)
        if not self.providers:
            raise ValueError("citation_verifier_requires_provider")

    def verify(self, candidates: list[dict]) -> CitationVerificationResult:
        verified = []
        provider_log = []
        run_had_failure = False
        for candidate in candidates:
            outcomes = []
            for provider in self.providers:
                try:
                    outcome = provider.lookup(candidate)
                except Exception as exc:
                    outcome = {"provider": provider.provider_name, "status": "FAILED", "error_type": type(exc).__name__}
                    run_had_failure = True
                outcomes.append(outcome)
                provider_log.append({
                    "stable_id": canonical_stable_id(candidate),
                    "provider": outcome.get("provider", provider.provider_name),
                    "status": outcome.get("status"),
                    **({"error_type": outcome["error_type"]} if outcome.get("error_type") else {}),
                })

            applicable = [item for item in outcomes if item.get("status") != "NOT_APPLICABLE"]
            resolved = [item for item in applicable if item.get("status") in {"RESOLVED", "RETRACTED"}]
            failures = [item for item in applicable if item.get("status") == "FAILED"]
            retracted = any(item.get("status") == "RETRACTED" for item in resolved)
            mismatch_by_provider = {
                item["provider"]: _metadata_mismatches(candidate, item.get("record") or {})
                for item in resolved
            }
            mismatches = sorted({reason for reasons in mismatch_by_provider.values() for reason in reasons})
            if retracted:
                verdict = "RETRACTED"
            elif mismatches:
                verdict = "MISMATCH"
            elif resolved and failures:
                verdict = "PARTIAL"
            elif resolved:
                verdict = "VERIFIED"
            elif failures:
                verdict = "PARTIAL"
            else:
                verdict = "UNRESOLVED"
            canonical = next((item.get("record") for item in resolved if item.get("record")), {})
            verified.append({
                **candidate,
                "selection_status": "P1_REEVALUATION_REQUIRED",
                "p1_relevance_tier": "not_evaluated",
                "citation_verification": {
                    "verdict": verdict,
                    "provider_count": len(resolved),
                    "providers": [item.get("provider") for item in resolved],
                    "mismatches": mismatch_by_provider,
                    "canonical_record": canonical,
                },
            })

        verdict_counts: dict[str, int] = {}
        for candidate in verified:
            verdict = candidate["citation_verification"]["verdict"]
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        status = "CITATION_VERIFICATION_PARTIAL" if run_had_failure else "CITATION_VERIFICATION_COMPLETE"
        return CitationVerificationResult(
            status=status,
            candidates=verified,
            provider_log=provider_log,
            audit={
                "version": CITATION_VERIFICATION_VERSION,
                "candidate_count": len(candidates),
                "verdict_counts": verdict_counts,
                "discovery_only": True,
                "citation_verification_is_not_relevance": True,
                "formal_papers_emitted": False,
            },
        )
