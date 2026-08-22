"""OpenAlex discovery connector with bounded retries and redacted telemetry."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from http.client import IncompleteRead, RemoteDisconnected
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from retrieval_query_plan import OpenAlexQueryPlan, compile_openalex_filter


class OpenAlexTransport:
    def __init__(self, timeout: int = 45, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self._lock = Lock()
        self._next_request_at = 0.0

    def _pace(self) -> None:
        with self._lock:
            wait = max(0.0, self._next_request_at - time.monotonic())
            if wait:
                time.sleep(wait)
            self._next_request_at = time.monotonic() + 0.20

    def get(self, endpoint: str, params: dict) -> tuple[dict, dict]:
        request_params = dict(params)
        headers = {"Accept": "application/json", "User-Agent": "ProposalCompass/0.6"}
        api_key = os.getenv("OPENALEX_API_KEY", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.monotonic()
        last_error: Exception | None = None
        retry_errors: list[str] = []
        for attempt in range(self.retries + 1):
            try:
                self._pace()
                target = f"{endpoint}?{urlencode(request_params)}"
                with urlopen(Request(target, headers=headers), timeout=self.timeout) as response:
                    payload = json.load(response)
                return payload, {
                    "attempts": attempt + 1,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "authenticated": bool(api_key),
                    "http_status": 200,
                    "effective_per_page": request_params.get("per_page"),
                    "retry_errors": retry_errors,
                }
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    break
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else (2.0 if exc.code == 429 else 0.5) * (2 ** attempt)
                except ValueError:
                    delay = (2.0 if exc.code == 429 else 0.5) * (2 ** attempt)
                time.sleep(min(max(delay, 0.1), 60.0))
            except Exception as exc:
                last_error = exc
                retry_errors.append(type(exc).__name__)
                if attempt < self.retries:
                    if isinstance(exc, (IncompleteRead, RemoteDisconnected, TimeoutError, ConnectionResetError, URLError, json.JSONDecodeError)):
                        current_page_size = int(request_params.get("per_page") or 0)
                        if current_page_size > 10:
                            request_params["per_page"] = max(10, current_page_size // 2)
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
        self.transport = transport or OpenAlexTransport(
            timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "45")),
            retries=int(os.getenv("PROPOSAL_RETRIEVAL_RETRIES", "3")),
        )
        self.per_page = max(1, min(per_page, 100))

    @staticmethod
    def _record(work: dict, lane_id: str) -> dict:
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        best_oa = work.get("best_oa_location") or {}
        authors = []
        for authorship in work.get("authorships", [])[:30]:
            name = ((authorship.get("author") or {}).get("display_name") or "").strip()
            if name:
                authors.append(name)
        source_issns = list(source.get("issn") or [])
        if source.get("issn_l") and source["issn_l"] not in source_issns:
            source_issns.append(source["issn_l"])
        primary_topic = work.get("primary_topic") or {}
        keywords = work.get("keywords") or []
        normalized = work.get("citation_normalized_percentile") or {}
        return {
            "external_id": work.get("id"),
            "title": work.get("display_name") or work.get("title"),
            "abstract": _abstract(work.get("abstract_inverted_index")),
            "authors": authors,
            "year": work.get("publication_year"),
            "publication_date": work.get("publication_date"),
            "language": work.get("language"),
            "doi": _doi(work.get("doi")),
            "url": primary.get("landing_page_url") or work.get("doi") or work.get("id"),
            "source_title": source.get("display_name"),
            "source_id": source.get("id"),
            "source_issns": source_issns,
            "document_type": _document_type(work.get("type")),
            "citation_count": work.get("cited_by_count") or 0,
            "citation_normalized_percentile": normalized.get("value") if isinstance(normalized, dict) else normalized,
            "fwci": work.get("fwci"),
            "primary_topic": {
                "id": primary_topic.get("id"),
                "name": primary_topic.get("display_name"),
                "field": primary_topic.get("field"),
                "subfield": primary_topic.get("subfield"),
            } if primary_topic else {},
            "topics": [
                {
                    "id": topic.get("id"), "name": topic.get("display_name"),
                    "score": topic.get("score"), "field": topic.get("field"),
                    "subfield": topic.get("subfield"),
                }
                for topic in work.get("topics", [])[:10]
            ],
            "keywords": [
                {"id": keyword.get("id"), "name": keyword.get("display_name"), "score": keyword.get("score")}
                for keyword in keywords[:20]
            ],
            "is_retracted": bool(work.get("is_retracted")),
            "oa_pdf_url": best_oa.get("pdf_url"),
            "oa_landing_page_url": best_oa.get("landing_page_url"),
            "doi_landing_url": work.get("doi"),
            "verified_fulltext_available": bool(best_oa.get("pdf_url")),
            "query_lane_ids": [lane_id],
            "provider_payload_refs": [work.get("id")],
        }

    def search(self, plan: OpenAlexQueryPlan) -> tuple[list[dict], dict]:
        if not isinstance(plan, OpenAlexQueryPlan):
            raise TypeError("OpenAlexPaperProvider.search requires OpenAlexQueryPlan")
        per_page = max(1, min(int(plan.per_page or self.per_page), 100))
        params = {
            "per_page": per_page,
            "cursor": "*",
            # Avoid multi-megabyte work payloads that caused repeated
            # IncompleteRead failures.  Every selected field is consumed by
            # normalization, source qualification, boundary checks or rerank.
            "select": ",".join((
                "id", "display_name", "abstract_inverted_index", "authorships",
                "publication_year", "publication_date", "language", "doi",
                "primary_location", "best_oa_location", "type", "cited_by_count",
                "citation_normalized_percentile", "fwci", "primary_topic",
                "topics", "keywords", "is_retracted",
            )),
        }
        if plan.search:
            params["search"] = plan.search
        compiled_filter = compile_openalex_filter(plan.filters)
        if compiled_filter:
            params["filter"] = compiled_filter
        if plan.sort:
            params["sort"] = plan.sort
        started_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        pages: list[dict] = []
        provider_count = None
        next_cursor = "*"
        stop_reason = "max_pages"
        for page_number in range(1, max(1, plan.max_pages) + 1):
            params["cursor"] = next_cursor
            payload, transport_meta = self.transport.get(self.endpoint, params)
            meta = payload.get("meta") or {}
            provider_count = meta.get("count", provider_count)
            page_records = [self._record(work, plan.lane_id) for work in payload.get("results", [])]
            records.extend(page_records)
            next_cursor = meta.get("next_cursor")
            pages.append({
                "page": page_number,
                "returned_rows": len(page_records),
                "next_cursor_present": bool(next_cursor),
                "transport": transport_meta,
            })
            if not next_cursor or not page_records:
                stop_reason = "provider_exhausted"
                break
        return records, {
            "provider": "openalex",
            "status": "ok",
            "lane_id": plan.lane_id,
            "query_plan": plan.as_dict(),
            "compiled_filter": compiled_filter,
            "requested_rows_per_page": per_page,
            "provider_match_count": provider_count,
            "returned_rows": len(records),
            "queried_at": started_at,
            "pages": pages,
            "stop_reason": stop_reason,
        }
