"""Bounded OpenAlex citation expansion that emits discovery candidates only."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Protocol

from openalex_provider import OpenAlexPaperProvider, OpenAlexTransport
from paper_quality import clean_doi, normalize_record, title_key


CITATION_GRAPH_VERSION = "citation-graph-discovery-1.0.0"
WORK_SELECT = ",".join((
    "id", "display_name", "abstract_inverted_index", "authorships",
    "publication_year", "publication_date", "language", "doi",
    "primary_location", "best_oa_location", "type", "cited_by_count",
    "citation_normalized_percentile", "fwci", "primary_topic",
    "topics", "keywords", "is_retracted",
))


def _openalex_short_id(value: object) -> str | None:
    text = str(value or "").strip()
    match = re.search(r"(?:^|/)(W\d+)$", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def stable_identifiers(record: dict) -> dict[str, str]:
    identifiers: dict[str, str] = {}
    doi = clean_doi(record.get("doi"))
    if doi:
        identifiers["doi"] = doi
    external = record.get("external_ids") or {}
    for provider, value in external.items():
        if value in (None, ""):
            continue
        if str(provider).casefold() == "doi":
            cleaned = clean_doi(str(value))
            if cleaned:
                identifiers["doi"] = cleaned
        openalex_id = _openalex_short_id(value) if str(provider).casefold() == "openalex" else None
        if openalex_id:
            identifiers["openalex"] = openalex_id
        elif str(provider).casefold() in {"semantic_scholar", "dblp", "arxiv"}:
            identifiers[str(provider).casefold()] = str(value).strip()
    for value in [record.get("external_id"), *(record.get("provider_payload_refs") or [])]:
        openalex_id = _openalex_short_id(value)
        if openalex_id:
            identifiers["openalex"] = openalex_id
    return identifiers


def canonical_stable_id(record: dict) -> str:
    identifiers = stable_identifiers(record)
    for provider in ("doi", "openalex", "semantic_scholar", "dblp", "arxiv"):
        if identifiers.get(provider):
            return f"{provider}:{identifiers[provider]}"
    title = title_key(record.get("title"))
    year = str(record.get("year") or "")
    if title:
        return "title_year:" + hashlib.sha256(f"{title}|{year}".encode("utf-8")).hexdigest()[:24]
    return "unresolved:" + hashlib.sha256(str(sorted(record.items())).encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class CitationExpansionRequest:
    seed_papers: tuple[dict, ...]
    direction: str = "both"
    max_seeds: int = 5
    max_neighbors_per_seed: int = 25


@dataclass
class CitationExpansionResult:
    status: str
    discovery_candidates: list[dict] = field(default_factory=list)
    seed_audit: list[dict] = field(default_factory=list)
    provider_log: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)


class CitationGraphProvider(Protocol):
    def expand(self, request: CitationExpansionRequest) -> CitationExpansionResult: ...


class OpenAlexCitationGraphProvider:
    endpoint = "https://api.openalex.org/works"

    def __init__(self, transport: OpenAlexTransport | None = None) -> None:
        self.transport = transport or OpenAlexTransport()

    def _list(self, params: dict) -> tuple[list[dict], dict]:
        payload, transport_meta = self.transport.get(self.endpoint, params)
        return list(payload.get("results") or []), transport_meta

    def _references(self, openalex_id: str, limit: int) -> tuple[list[dict], list[dict]]:
        seed_payload, seed_meta = self.transport.get(
            f"{self.endpoint}/{openalex_id}", {"select": "id,referenced_works"},
        )
        references = [_openalex_short_id(value) for value in seed_payload.get("referenced_works", [])]
        references = [value for value in references if value][:100]
        logs = [{"edge": "references", "operation": "seed_lookup", "transport": seed_meta, "id_count": len(references)}]
        if not references:
            return [], logs
        results, list_meta = self._list({
            "filter": f"openalex:{'|'.join(references)}",
            "per_page": len(references),
            "sort": "cited_by_count:desc",
            "select": WORK_SELECT,
        })
        logs.append({"edge": "references", "operation": "neighbor_fetch", "transport": list_meta, "returned_rows": len(results)})
        return results[: max(1, limit)], logs

    def _citations(self, openalex_id: str, limit: int) -> tuple[list[dict], list[dict]]:
        results, transport_meta = self._list({
            "filter": f"cites:{openalex_id}",
            "sort": "cited_by_count:desc",
            "per_page": min(100, max(1, limit)),
            "select": WORK_SELECT,
        })
        return results, [{"edge": "cited_by", "operation": "neighbor_fetch", "transport": transport_meta, "returned_rows": len(results)}]

    def expand(self, request: CitationExpansionRequest) -> CitationExpansionResult:
        if request.direction not in {"references", "cited_by", "both"}:
            return CitationExpansionResult(status="CITATION_EXPANSION_UNAVAILABLE", limitations=["invalid_direction"])
        seeds = []
        for record in request.seed_papers:
            identifiers = stable_identifiers(record)
            seeds.append({
                "record": record,
                "stable_id": canonical_stable_id(record),
                "openalex_id": identifiers.get("openalex"),
            })
        seeds = seeds[: max(1, request.max_seeds)]
        usable = [item for item in seeds if item["openalex_id"]]
        if not usable:
            return CitationExpansionResult(
                status="CITATION_EXPANSION_UNAVAILABLE",
                seed_audit=[{"seed_id": item["stable_id"], "status": "missing_openalex_id"} for item in seeds],
                limitations=["citation_expansion_requires_openalex_seed_id"],
                audit={"version": CITATION_GRAPH_VERSION, "discovery_only": True},
            )

        seed_stable_ids = {item["stable_id"] for item in seeds}
        seed_openalex_ids = {item["openalex_id"] for item in usable}
        candidates: dict[str, dict] = {}
        provider_log: list[dict] = []
        seed_audit: list[dict] = []
        failures = 0
        for seed in usable:
            edges = []
            directions = ("references", "cited_by") if request.direction == "both" else (request.direction,)
            for edge_direction in directions:
                try:
                    works, logs = (
                        self._references(seed["openalex_id"], request.max_neighbors_per_seed)
                        if edge_direction == "references"
                        else self._citations(seed["openalex_id"], request.max_neighbors_per_seed)
                    )
                    for log in logs:
                        provider_log.append({"provider": "openalex", "seed_id": seed["stable_id"], "status": "ok", **log})
                    for work in works:
                        raw = OpenAlexPaperProvider._record(work, f"citation_{edge_direction}")
                        normalized = normalize_record(raw, "openalex")
                        candidate_id = canonical_stable_id(normalized)
                        candidate_openalex = stable_identifiers(normalized).get("openalex")
                        if candidate_id in seed_stable_ids or candidate_openalex in seed_openalex_ids:
                            continue
                        edge = {
                            "seed_id": seed["stable_id"],
                            "seed_openalex_id": seed["openalex_id"],
                            "direction": edge_direction,
                        }
                        current = candidates.get(candidate_id)
                        if current is None:
                            current = {
                                **normalized,
                                "stable_id": candidate_id,
                                "citation_edges": [],
                                "selection_status": "P1_REEVALUATION_REQUIRED",
                                "p1_relevance_tier": "not_evaluated",
                                "discovery_only": True,
                            }
                            candidates[candidate_id] = current
                        if edge not in current["citation_edges"]:
                            current["citation_edges"].append(edge)
                        edges.append(edge)
                except Exception as exc:
                    failures += 1
                    provider_log.append({
                        "provider": "openalex", "seed_id": seed["stable_id"],
                        "edge": edge_direction, "status": "failed", "error_type": type(exc).__name__,
                    })
            seed_audit.append({
                "seed_id": seed["stable_id"], "openalex_id": seed["openalex_id"],
                "status": "expanded" if edges else "no_neighbors", "edge_count": len(edges),
            })

        ranked = []
        for candidate in candidates.values():
            seed_degree = len({edge["seed_id"] for edge in candidate["citation_edges"]})
            candidate["seed_degree"] = seed_degree
            candidate["edge_count"] = len(candidate["citation_edges"])
            candidate["discovery_reason"] = "citation_graph_neighbor"
            ranked.append(candidate)
        ranked.sort(key=lambda item: (-item["seed_degree"], -int(item.get("citation_count") or 0), item["stable_id"]))
        if failures and ranked:
            status = "CITATION_EXPANSION_PARTIAL"
        elif failures:
            status = "CITATION_EXPANSION_UNAVAILABLE"
        else:
            status = "CITATION_EXPANSION_COMPLETE"
        return CitationExpansionResult(
            status=status,
            discovery_candidates=ranked,
            seed_audit=seed_audit,
            provider_log=provider_log,
            limitations=["one_or_more_citation_graph_legs_failed"] if failures else [],
            audit={
                "version": CITATION_GRAPH_VERSION,
                "seed_count": len(seeds),
                "usable_seed_count": len(usable),
                "candidate_count": len(ranked),
                "failed_leg_count": failures,
                "discovery_only": True,
                "formal_papers_emitted": False,
                "selection_policy": "P1_REEVALUATION_REQUIRED",
            },
        )
