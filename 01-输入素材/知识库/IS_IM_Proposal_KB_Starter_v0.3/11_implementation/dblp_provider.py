"""Optional DBLP publication-search connector for IS×CS/HCI/AI profiles."""
from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class DblpPaperProvider:
    endpoint = "https://dblp.org/search/publ/api"

    def search(self, query: str, limit: int = 100) -> tuple[list[dict], dict]:
        params = {"q": query, "format": "json", "h": min(max(limit, 1), 100)}
        with urlopen(Request(f"{self.endpoint}?{urlencode(params)}", headers={"Accept": "application/json", "User-Agent": "ProposalCompass/0.6"}), timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "18"))) as response:
            payload = json.load(response)
        hit = (((payload.get("result") or {}).get("hits") or {}).get("hit") or [])
        records = []
        for item in hit:
            info = item.get("info") or {}
            authors_raw = (info.get("authors") or {}).get("author") or []
            if isinstance(authors_raw, dict):
                authors_raw = [authors_raw]
            authors = [(a.get("text") if isinstance(a, dict) else str(a)) for a in authors_raw]
            records.append({
                "external_id": info.get("key"), "title": info.get("title"), "authors": authors,
                "year": info.get("year"), "doi": info.get("doi"), "url": info.get("url"),
                "source_title": info.get("venue"), "document_type": "proceedings-article" if info.get("type") in {"Conference and Workshop Papers", "Informal and Other Publications"} else "journal-article",
                "provider_payload_refs": [info.get("key")],
            })
        return records, {"provider": "dblp", "status": "ok", "query": query, "returned_rows": len(records)}
