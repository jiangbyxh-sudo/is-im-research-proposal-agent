"""Replaceable boundary and Crossref implementation for live paper discovery."""
from __future__ import annotations

import html
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DiscoveryRequest:
    selected_direction_id: str
    research_direction: str
    fine_grained_question: str | None
    chinese_count: int = 10
    english_count: int = 20
    popularity_window_years: int = 5
    journal_pool_ids: tuple[str, ...] = ()
    query_by_language: dict[str, str] = field(default_factory=dict)
    source_tier_pool_ids: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    status: str
    papers: list[dict] = field(default_factory=list)
    analysis_papers: list[dict] = field(default_factory=list)
    search_log: list[dict] = field(default_factory=list)
    exclusion_log: list[dict] = field(default_factory=list)
    shortages: dict[str, int] = field(default_factory=dict)
    message_to_user: str = ""
    coverage_audit: dict = field(default_factory=dict)
    provider_statuses: list[dict] = field(default_factory=list)
    expansion_log: list[dict] = field(default_factory=list)
    dedupe_log: list[dict] = field(default_factory=list)
    zero_result_diagnosis: dict = field(default_factory=dict)
    score_config_version: str = ""
    candidate_traces: list[dict] = field(default_factory=list)
    lane_funnels: list[dict] = field(default_factory=list)
    chinese_coverage: dict = field(default_factory=dict)


class PaperDiscoveryProvider(Protocol):
    def discover(self, request: DiscoveryRequest) -> DiscoveryResult: ...


class JsonTransport(Protocol):
    def get(self, url: str, params: dict) -> dict: ...


class UnconfiguredPaperDiscoveryProvider:
    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        return DiscoveryResult(
            status="DYNAMIC_RETRIEVAL_UNAVAILABLE",
            message_to_user="动态论文检索接口尚未配置，已停止；未生成或填充任何论文记录。",
        )


class CrossrefTransport:
    def __init__(self, mailto: str | None = None, timeout: int = 18, retries: int = 1):
        self.mailto = mailto
        self.timeout = timeout
        self.retries = retries
        self._rate_lock = Lock()
        self._next_request_at = 0.0
        self._minimum_interval = 0.0

    @staticmethod
    def _seconds(value: str | None) -> float | None:
        if not value:
            return None
        text = value.strip().lower()
        try:
            return max(0.0, float(text))
        except ValueError:
            pass
        match = re.fullmatch(r"([0-9.]+)\s*(ms|s|m|h)", text)
        if not match:
            return None
        amount = float(match.group(1))
        return amount * {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[match.group(2)]

    def _reserve_request_slot(self) -> None:
        with self._rate_lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self._next_request_at - now)
            if wait_seconds:
                time.sleep(wait_seconds)
            self._next_request_at = time.monotonic() + self._minimum_interval

    def _apply_rate_headers(self, headers) -> dict:
        limit_raw = headers.get("X-Rate-Limit-Limit")
        interval_raw = headers.get("X-Rate-Limit-Interval")
        retry_after_raw = headers.get("Retry-After")
        try:
            limit = float(limit_raw) if limit_raw else None
        except ValueError:
            limit = None
        interval_seconds = self._seconds(interval_raw)
        retry_after_seconds = self._seconds(retry_after_raw)
        if limit and interval_seconds:
            with self._rate_lock:
                self._minimum_interval = max(self._minimum_interval, interval_seconds / limit)
        return {
            "rate_limit": limit,
            "rate_interval_seconds": interval_seconds,
            "retry_after_seconds": retry_after_seconds,
        }

    def get(self, url: str, params: dict) -> dict:
        params = dict(params)
        if self.mailto:
            params["mailto"] = self.mailto
        target = f"{url}?{urlencode(params)}"
        agent = "ProposalCompass/0.2"
        if self.mailto:
            agent += f" (mailto:{self.mailto})"
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(self.retries + 1):
            try:
                self._reserve_request_slot()
                request = Request(target, headers={"User-Agent": agent, "Accept": "application/json"})
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                    rate_meta = self._apply_rate_headers(response.headers)
                payload["_transport_meta"] = {
                    "attempts": attempt + 1,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "polite_pool": bool(self.mailto),
                    **rate_meta,
                }
                return payload
            except HTTPError as exc:
                last_error = exc
                rate_meta = self._apply_rate_headers(exc.headers)
                if exc.code != 429 or attempt >= self.retries:
                    break
                delay = rate_meta.get("retry_after_seconds")
                if delay is None:
                    delay = 0.5 * (2 ** attempt)
                time.sleep(min(max(delay, 0.1), 60.0))
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (2 ** attempt))
        assert last_error
        raise last_error


class CrossrefPaperDiscoveryProvider:
    """Discover recent papers inside the locally verified journal whitelist."""

    def __init__(
        self,
        registry_path: Path,
        transport: JsonTransport | None = None,
        max_workers: int | None = None,
        max_journals_per_language: int = 10,
        rows_per_journal: int = 20,
        enable_chinese: bool = True,
    ):
        self.registry_path = registry_path
        self.transport = transport or CrossrefTransport(
            mailto=os.getenv("PROPOSAL_CROSSREF_MAILTO") or None,
            timeout=int(os.getenv("PROPOSAL_RETRIEVAL_TIMEOUT", "18")),
        )
        policy_cap = 3 if getattr(self.transport, "mailto", None) else 1
        requested_workers = policy_cap if max_workers is None else max_workers
        self.max_workers = max(1, min(requested_workers, policy_cap))
        self.concurrency_policy = "crossref_polite_pool" if policy_cap == 3 else "crossref_public_pool"
        self.max_journals_per_language = max(1, max_journals_per_language)
        self.rows_per_journal = max(1, min(rows_per_journal, 100))
        self.enable_chinese = enable_chinese

    def _load_registry(self) -> dict:
        if not self.registry_path.is_file():
            raise FileNotFoundError(f"Journal registry missing: {self.registry_path}")
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    @staticmethod
    def _published_parts(item: dict) -> tuple[int | None, str | None]:
        for key in ("published-print", "published-online", "published", "issued", "created"):
            parts = item.get(key, {}).get("date-parts", [])
            if parts and parts[0]:
                values = parts[0]
                year = int(values[0])
                month = int(values[1]) if len(values) > 1 else 1
                day = int(values[2]) if len(values) > 2 else 1
                try:
                    return year, date(year, month, day).isoformat()
                except ValueError:
                    return year, f"{year:04d}"
        return None, None

    @staticmethod
    def _first(value, default=""):
        return value[0] if isinstance(value, list) and value else (value or default)

    @staticmethod
    def _authors(item: dict) -> list[str]:
        names = []
        for author in item.get("author", [])[:20]:
            name = " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
            if name:
                names.append(name)
        return names

    @staticmethod
    def _strip_markup(value: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()

    @staticmethod
    def _dedupe_key(paper: dict) -> str:
        if paper.get("doi"):
            return f"doi:{paper['doi'].lower()}"
        title = re.sub(r"\W+", "", paper.get("title", "").casefold())
        return f"title:{title}:{paper.get('year')}"

    @staticmethod
    def _relevance_score(query: str, title: str, abstract: str) -> float:
        text = f"{title} {abstract}".casefold()
        normalized_query = query.casefold().strip()
        if normalized_query and normalized_query in text:
            return 10.0
        tokens = {
            token for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized_query)
            if token not in {"the", "and", "for", "with", "information", "system", "systems", "research", "enabled"}
        }
        if not tokens:
            return 1.0
        def contains_token(haystack: str, token: str) -> bool:
            if token.isascii():
                return bool(re.search(rf"\b{re.escape(token)}\b", haystack))
            return token in haystack
        hits = sum(contains_token(text, token) for token in tokens)
        title_hits = sum(contains_token(title.casefold(), token) for token in tokens)
        return hits + (1.5 * title_hits)

    def _fetch_journal(self, journal: dict, query: str, from_date: str, until_date: str) -> tuple[list[dict], dict, list[dict]]:
        issn = journal["issns"][0]
        endpoint = f"https://api.crossref.org/journals/{quote(issn)}/works"
        params = {
            "query.bibliographic": query,
            "filter": f"from-pub-date:{from_date},until-pub-date:{until_date},type:journal-article",
            "rows": self.rows_per_journal,
            "select": "DOI,title,container-title,published,published-print,published-online,issued,created,author,ISSN,URL,type,is-referenced-by-count,abstract,relation,update-to",
        }
        started = datetime.now(timezone.utc).isoformat()
        started_monotonic = time.monotonic()
        payload = self.transport.get(endpoint, params)
        transport_meta = payload.pop("_transport_meta", {})
        items = payload.get("message", {}).get("items", [])
        papers = []
        exclusions = []
        for item in items:
            title = str(self._first(item.get("title"))).strip()
            if not title:
                continue
            lower_title = title.casefold()
            is_correction = bool(item.get("update-to") or re.match(r"^(retracted\b|retraction\b|retraction notice\b|correction\b|corrigendum\b|erratum\b)", lower_title))
            year, published_date = self._published_parts(item)
            abstract = self._strip_markup(item.get("abstract", ""))
            doi = str(item.get("DOI") or "").strip().lower() or None
            relevance = self._relevance_score(query, title, abstract)
            papers.append({
                "title": title,
                "abstract": abstract or None,
                "authors": self._authors(item),
                "year": year,
                "published_date": published_date,
                "journal": journal["canonical_title"],
                "source_title": journal["canonical_title"],
                "source_issns": item.get("ISSN") or journal["issns"],
                "language": journal["language"],
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else item.get("URL"),
                "citation_count": int(item.get("is-referenced-by-count") or 0),
                "journal_ranking": journal["ranking_levels"],
                "journal_pool_ids": journal["pool_ids"],
                "verified_by": ["local_journal_whitelist", "crossref_journal_endpoint"],
                "relevance_score": relevance,
                "metadata_source": "Crossref",
                "provider": "crossref",
                "document_type": "journal-article",
                "integrity_status": "clear",
                "is_correction": is_correction,
                "evidence_level": "abstract" if abstract else "title_only",
            })
        return papers, {
            "provider": "Crossref",
            "journal": journal["canonical_title"],
            "language": journal["language"],
            "ranking_levels": journal["ranking_levels"],
            "issn": issn,
            "query": query,
            "from_date": from_date,
            "until_date": until_date,
            "requested_rows": self.rows_per_journal,
            "returned_rows": len(items),
            "accepted_before_dedupe": len(papers),
            "queried_at": started,
            "duration_ms": round((time.monotonic() - started_monotonic) * 1000, 2),
            "concurrency_policy": self.concurrency_policy,
            "transport": transport_meta,
        }, exclusions

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        try:
            registry = self._load_registry()
        except (OSError, json.JSONDecodeError) as exc:
            return DiscoveryResult(
                status="DYNAMIC_RETRIEVAL_UNAVAILABLE",
                message_to_user=f"动态检索已启用，但本地期刊注册表不可用（{type(exc).__name__}），已停止。",
            )

        pools = set(request.journal_pool_ids)
        journals = [
            item for item in registry.get("journals", [])
            if item.get("default_eligible", True)
            and item.get("issns")
            and item.get("crossref_available")
            and pools.intersection(item.get("pool_ids", []))
        ]
        if not journals:
            return DiscoveryResult(
                status="JOURNAL_ROUTE_UNAVAILABLE",
                message_to_user="研究方向尚未映射到带ISSN的合格期刊，已停止动态检索。",
            )

        current_year = date.today().year
        from_date = f"{current_year - request.popularity_window_years + 1}-01-01"
        until_date = date.today().isoformat()
        selected = []
        enabled_languages = ("zh", "en") if self.enable_chinese else ("en",)
        tier_order = {tier: index for index, tier in enumerate(("A", "B", "ADJACENT"))}
        pool_tiers = {
            pool_id: tier
            for tier, pool_ids in request.source_tier_pool_ids.items()
            for pool_id in pool_ids
        }
        for language in enabled_languages:
            candidates = [item for item in journals if item["language"] == language]
            candidates.sort(key=lambda item: (
                min((tier_order.get(pool_tiers.get(pool), 99) for pool in item.get("pool_ids", [])), default=99),
                item["canonical_title"].casefold(),
            ))
            selected.extend(candidates[: self.max_journals_per_language])

        papers: list[dict] = []
        logs: list[dict] = []
        exclusions: list[dict] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._fetch_journal,
                    journal,
                    request.query_by_language.get(journal["language"]) or request.fine_grained_question or request.research_direction,
                    from_date,
                    until_date,
                ): journal
                for journal in selected
            }
            for future in as_completed(futures):
                journal = futures[future]
                try:
                    found, log, filtered = future.result()
                    papers.extend(found)
                    logs.append(log)
                    exclusions.extend(filtered)
                except Exception as exc:
                    exclusions.append({
                        "reason": "provider_request_failed",
                        "journal": journal["canonical_title"],
                        "error_type": type(exc).__name__,
                        "http_status": getattr(exc, "code", None),
                    })

        best: dict[str, dict] = {}
        for paper in papers:
            key = self._dedupe_key(paper)
            previous = best.get(key)
            if previous is None or paper["relevance_score"] > previous["relevance_score"]:
                best[key] = paper
        deduped = list(best.values())
        deduped.sort(key=lambda item: (
            item["relevance_score"], item.get("year") or 0, item["citation_count"]
        ), reverse=True)

        zh = [item for item in deduped if item["language"] == "zh"][: request.chinese_count]
        en = [item for item in deduped if item["language"] == "en"][: request.english_count]
        selected_papers = zh + en
        shortages = {"zh": max(0, request.chinese_count - len(zh)), "en": max(0, request.english_count - len(en))}
        chinese_note = "" if self.enable_chinese else "中文连接器暂未启用；"
        if not selected_papers:
            status = "DYNAMIC_RETRIEVAL_UNAVAILABLE"
            message = f"{chinese_note}已查询合格期刊，但当前查询未返回可核验论文；未使用非白名单来源补数。"
        elif any(shortages.values()):
            status = "RETRIEVAL_PARTIAL"
            message = (
                f"{chinese_note}动态检索完成：中文{len(zh)}/{request.chinese_count}篇，"
                f"英文{len(en)}/{request.english_count}篇。结果不足部分保持缺口，未降级补数。"
            )
        else:
            status = "RETRIEVAL_COMPLETE"
            message = f"动态检索完成：中文{len(zh)}篇、英文{len(en)}篇，均已通过本地期刊白名单路由。"
        return DiscoveryResult(
            status=status,
            papers=selected_papers,
            # Crossref returns raw normalized metadata only.  The multi-source
            # orchestrator owns boundary, source-tier and final qualification.
            analysis_papers=deduped[:120],
            search_log=sorted(logs, key=lambda item: (item["journal"], item["issn"])),
            exclusion_log=exclusions,
            shortages=shortages,
            message_to_user=message,
        )
