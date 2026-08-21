"""Optional Semantic Scholar Graph API connector."""
from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SemanticScholarPaperProvider:
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query: str, from_year: int, to_year: int, limit: int = 100) -> tuple[list[dict], dict]:
        fields = "paperId,title,abstract,authors,year,publicationDate,venue,externalIds,url,citationCount,publicationTypes,isOpenAccess,openAccessPdf"
        params = {"query": query, "year": f"{from_year}-{to_year}", "limit": min(max(limit, 1), 100), "fields": fields}
        headers = {"Accept": "application/json", "User-Agent": "ProposalCompass/0.6"}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        with urlopen(Request(f"{self.endpoint}?{urlencode(params)}", headers=headers), timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "18"))) as response:
            payload = json.load(response)
        records = []
        for paper in payload.get("data", []):
            external = paper.get("externalIds") or {}
            oa = paper.get("openAccessPdf") or {}
            records.append({
                "external_id": paper.get("paperId"), "title": paper.get("title"), "abstract": paper.get("abstract"),
                "authors": [item.get("name") for item in paper.get("authors", []) if item.get("name")],
                "year": paper.get("year"), "publication_date": paper.get("publicationDate"),
                "doi": external.get("DOI"), "url": paper.get("url"), "source_title": paper.get("venue"),
                "document_type": "journal-article", "citation_count": paper.get("citationCount") or 0,
                "oa_url": oa.get("url"), "provider_payload_refs": [paper.get("paperId")],
            })
        return records, {"provider": "semantic_scholar", "status": "ok", "query": query, "returned_rows": len(records), "authenticated": bool(api_key)}
