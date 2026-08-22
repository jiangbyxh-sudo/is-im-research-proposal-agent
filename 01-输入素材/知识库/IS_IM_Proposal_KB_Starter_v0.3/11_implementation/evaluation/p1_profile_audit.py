#!/usr/bin/env python3
"""Resolve OpenAlex source IDs and evidence-backed topic candidates for P1."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


IMPLEMENTATION = Path(__file__).resolve().parents[1]
KB_ROOT = IMPLEMENTATION.parent
CATALOG = KB_ROOT / "01_taxonomy/generated/research_direction_catalog.json"
JOURNALS = KB_ROOT / "02_journals/generated/journal_registry.json"
SOURCE_OUTPUT = KB_ROOT / "01_taxonomy/openalex_source_registry.json"
TOPIC_OUTPUT = KB_ROOT / "01_taxonomy/openalex_topic_registry.json"


def get_json(endpoint: str, params: dict) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "ProposalCompass/0.7"}
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    target = f"{endpoint}?{urlencode(params)}"
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(Request(target, headers=headers), timeout=30) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
    raise last_error


def short_id(value: str | None) -> str | None:
    return str(value).rstrip("/").rsplit("/", 1)[-1] if value else None


def resolve_sources() -> dict:
    registry = json.loads(JOURNALS.read_text(encoding="utf-8"))
    journals = [item for item in registry["journals"] if item.get("issns")]
    by_issn = {issn.upper(): journal for journal in journals for issn in journal["issns"]}
    matches: dict[str, list[dict]] = {journal["journal_id"]: [] for journal in journals}
    issns = sorted(by_issn)
    for offset in range(0, len(issns), 50):
        chunk = issns[offset:offset + 50]
        payload = get_json("https://api.openalex.org/sources", {
            "filter": f"issn:{'|'.join(chunk)}", "per-page": 100,
            "select": "id,display_name,issn,issn_l,works_count",
        })
        for source in payload.get("results", []):
            observed = {str(value).upper() for value in source.get("issn", [])}
            if source.get("issn_l"):
                observed.add(str(source["issn_l"]).upper())
            for issn in observed.intersection(by_issn):
                journal = by_issn[issn]
                source_id = short_id(source.get("id"))
                existing = next((item for item in matches[journal["journal_id"]] if item["openalex_source_id"] == source_id), None)
                if existing:
                    existing["matched_issns"] = sorted(set([*existing["matched_issns"], issn]))
                else:
                    matches[journal["journal_id"]].append({
                        "openalex_source_id": source_id,
                        "openalex_display_name": source.get("display_name"),
                        "matched_issns": [issn],
                        "works_count": source.get("works_count"),
                    })
        time.sleep(0.12)
    sources = []
    for journal in journals:
        candidates = matches[journal["journal_id"]]
        exact_names = [item for item in candidates if str(item.get("openalex_display_name", "")).casefold() == journal["canonical_title"].casefold()]
        chosen = exact_names[0] if len(exact_names) == 1 else candidates[0] if len(candidates) == 1 else {}
        sources.append({
            "journal_id": journal["journal_id"],
            "canonical_title": journal["canonical_title"],
            "language": journal["language"],
            "issns": journal["issns"],
            "pool_ids": journal["pool_ids"],
            "openalex_source_id": chosen.get("openalex_source_id"),
            "review_status": "approved" if chosen else "pending_review",
            "resolution_evidence": candidates,
        })
    return {
        "version": "1.0.0-p1",
        "generated_on": date.today().isoformat(),
        "policy": "Exact ISSN resolution only; ambiguous matches remain pending_review.",
        "sources": sources,
    }


def resolve_topics() -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    existing_directions = {}
    if TOPIC_OUTPUT.is_file():
        existing_directions = json.loads(TOPIC_OUTPUT.read_text(encoding="utf-8")).get("directions", {})
    directions = {}
    for index, direction in enumerate(catalog["directions"]):
        existing = existing_directions.get(direction["direction_id"], {})
        if existing.get("candidates"):
            directions[direction["direction_id"]] = existing
            print(f"topic candidates {index + 1}/61 {direction['direction_id']} (reused)", file=sys.stderr)
            continue
        aliases = direction.get("aliases", [])
        initial_query = next((item for item in aliases if item.isascii()), direction["label"])
        query_variants = list(dict.fromkeys([
            initial_query,
            initial_query.replace("-", " "),
            direction["direction_id"].removeprefix("topic_").replace("_", " "),
            f"{initial_query} information systems",
        ]))
        payload = {"results": []}
        query = initial_query
        resolution_error = None
        for candidate_query in query_variants:
            try:
                candidate_payload = get_json("https://api.openalex.org/topics", {"search": candidate_query, "per-page": 5})
            except HTTPError as exc:
                resolution_error = "provider_rate_limited" if exc.code == 429 else f"provider_http_{exc.code}"
                break
            except Exception as exc:
                resolution_error = f"provider_{type(exc).__name__}"
                break
            if candidate_payload.get("results"):
                payload = candidate_payload
                query = candidate_query
                break
        topic_results = payload.get("results", [])[:5]
        topic_ids = [short_id(topic.get("id")) for topic in topic_results if topic.get("id")]
        try:
            sample_payload = get_json("https://api.openalex.org/works", {
                "filter": f"primary_topic.id:{'|'.join(topic_ids)}",
                "sort": "cited_by_count:desc",
                "per-page": 10,
                "select": "id,display_name,publication_year,primary_topic",
            }) if topic_ids else {"results": []}
        except HTTPError as exc:
            sample_payload = {"results": []}
            resolution_error = "sample_rate_limited" if exc.code == 429 else f"sample_http_{exc.code}"
        except Exception as exc:
            sample_payload = {"results": []}
            resolution_error = f"sample_{type(exc).__name__}"
        samples_by_topic: dict[str, list[dict]] = {topic_id: [] for topic_id in topic_ids}
        for work in sample_payload.get("results", []):
            topic_id = short_id((work.get("primary_topic") or {}).get("id"))
            if topic_id in samples_by_topic and len(samples_by_topic[topic_id]) < 2:
                samples_by_topic[topic_id].append({
                    "id": short_id(work.get("id")), "title": work.get("display_name"), "year": work.get("publication_year")
                })
        candidates = []
        for topic in topic_results:
            topic_id = short_id(topic.get("id"))
            candidates.append({
                "id": topic_id,
                "display_name": topic.get("display_name"),
                "description": topic.get("description"),
                "field": topic.get("field"),
                "subfield": topic.get("subfield"),
                "domain": topic.get("domain"),
                "works_count": topic.get("works_count"),
                "query": query,
                "review_status": "pending_review",
                "sample_papers": samples_by_topic.get(topic_id, []),
                "evidence_source": "OpenAlex topics search and primary-topic sample works",
            })
            time.sleep(0.12)
        directions[direction["direction_id"]] = {
            "query": query,
            "resolution_status": "candidates_pending_review" if candidates else (resolution_error or "no_topic_candidate"),
            "candidates": candidates,
        }
        print(f"topic candidates {index + 1}/61 {direction['direction_id']}", file=sys.stderr)
    return {
        "version": "1.0.0-p1",
        "generated_on": date.today().isoformat(),
        "policy": "Topic candidates require evidence and review; no first-result auto-approval.",
        "directions": directions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--topics-only", action="store_true")
    args = parser.parse_args()
    if not args.topics_only:
        SOURCE_OUTPUT.write_text(json.dumps(resolve_sources(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {SOURCE_OUTPUT}")
    if not args.sources_only:
        TOPIC_OUTPUT.write_text(json.dumps(resolve_topics(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {TOPIC_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
