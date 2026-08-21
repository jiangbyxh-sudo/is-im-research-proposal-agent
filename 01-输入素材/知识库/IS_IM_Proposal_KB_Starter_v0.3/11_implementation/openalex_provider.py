"""OpenAlex discovery connector with bounded retries and redacted telemetry."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OpenAlexTransport:
    def __init__(self, timeout: int = 18, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self._lock = Lock()
        self._next_request_at = 0.0

    def _pace(self) -> None:
        with self._lock:
            wait = max(0.0, self._next_request_at - time.monotonic())
            if wait:
                time.sleep(wait)
            self._next_request_at = time.monotonic() + 0.12

    def get(self, endpoint: str, params: dict) -> tuple[dict, dict]:
        target = f"{endpoint}?{urlencode(params)}"
        headers = {"Accept": "application/json", "User-Agent": "ProposalCompass/0.6"}
        api_key = os.getenv("OPENALEX_API_KEY", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                self._pace()
                with urlopen(Request(target, headers=headers), timeout=self.timeout) as response:
                    payload = json.load(response)
                return payload, {
                    "attempts": attempt + 1,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "authenticated": bool(api_key),
                    "http_status": 200,
                }
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    break
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 0.5 * (2 ** attempt)
                except ValueError:
                    delay = 0.5 * (2 ** attempt)
                time.sleep(min(max(delay, 0.1), 30.0))
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (2 ** attempt))
        assert last_error
        raise last_error


def _abstract(index: dict | None) -> str | None:
    if not index:
        return None
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((int(offset), word))
    positions.sort()
    return " ".join(word for _, word in positions) or None


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.rsplit("doi.org/", 1)[-1].lower()


def _document_type(value: str | None) -> str:
    return {
        "article": "journal-article",
        "review": "journal-article",
        "proceedings-article": "proceedings-article",
    }.get(value or "", value or "unknown")


class OpenAlexPaperProvider:
    endpoint = "https://api.openalex.org/works"

    def __init__(self, transport: OpenAlexTransport | None = None, per_page: int = 100):
        self.transport = transport or OpenAlexTransport(timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "18")))
        self.per_page = max(1, min(per_page, 100))

    def search(self, query: str, from_date: str, to_date: str, document_types: list[str]) -> tuple[list[dict], dict]:
        params = {
            "search": query,
            "filter": f"from_publication_date:{from_date},to_publication_date:{to_date}",
            "per_page": self.per_page,
        }
        started_at = datetime.now(timezone.utc).isoformat()
        payload, transport_meta = self.transport.get(self.endpoint, params)
        records: list[dict] = []
        for work in payload.get("results", []):
            primary = work.get("primary_location") or {}
            source = primary.get("source") or {}
            authors = []
            for authorship in work.get("authorships", [])[:30]:
                name = ((authorship.get("author") or {}).get("display_name") or "").strip()
                if name:
                    authors.append(name)
            source_issns = source.get("issn") or []
            if source.get("issn_l") and source["issn_l"] not in source_issns:
                source_issns.append(source["issn_l"])
            records.append({
                "external_id": work.get("id"),
                "title": work.get("display_name") or work.get("title"),
                "abstract": _abstract(work.get("abstract_inverted_index")),
                "authors": authors,
                "year": work.get("publication_year"),
                "publication_date": work.get("publication_date"),
                "language": work.get("language"),
                "doi": _doi(work.get("doi")),
                "url": (primary.get("landing_page_url") or work.get("doi") or work.get("id")),
                "source_title": source.get("display_name"),
                "source_issns": source_issns,
                "document_type": _document_type(work.get("type")),
                "citation_count": work.get("cited_by_count") or 0,
                "topics": [
                    {"id": topic.get("id"), "name": topic.get("display_name"), "score": topic.get("score")}
                    for topic in work.get("topics", [])[:10]
                ],
                "is_retracted": bool(work.get("is_retracted")),
                "oa_url": ((work.get("best_oa_location") or {}).get("pdf_url") or (work.get("best_oa_location") or {}).get("landing_page_url")),
                "provider_payload_refs": [work.get("id")],
            })
        meta = payload.get("meta") or {}
        return records, {
            "provider": "openalex",
            "status": "ok",
            "query": query,
            "from_date": from_date,
            "to_date": to_date,
            "requested_rows": self.per_page,
            "provider_match_count": meta.get("count"),
            "returned_rows": len(records),
            "queried_at": started_at,
            "transport": transport_meta,
            "cost_usd": meta.get("cost_usd"),
        }
