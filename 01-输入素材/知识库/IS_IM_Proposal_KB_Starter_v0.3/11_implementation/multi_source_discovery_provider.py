"""P1 local-profile-first multi-source discovery orchestrator."""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import date
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError

from dblp_provider import DblpPaperProvider
from openalex_provider import OpenAlexPaperProvider
from paper_discovery_provider import CrossrefPaperDiscoveryProvider, DiscoveryRequest, DiscoveryResult
from paper_quality import (
    SCORE_CONFIG_VERSION, build_journal_index, dedupe_records, normalize_record,
    qualify_source, quality_gate, score_record,
)
from semantic_scholar_provider import SemanticScholarPaperProvider


class MultiSourcePaperDiscoveryProvider:
    def __init__(
        self,
        profile_path: Path,
        registry_path: Path,
        openalex=None,
        crossref=None,
        semantic_scholar=None,
        dblp=None,
        enable_optional: bool | None = None,
    ):
        self.profile_path = profile_path
        self.registry_path = registry_path
        self.openalex = openalex or OpenAlexPaperProvider()
        self.crossref = crossref or CrossrefPaperDiscoveryProvider(registry_path)
        self.semantic_scholar = semantic_scholar or SemanticScholarPaperProvider()
        self.dblp = dblp or DblpPaperProvider()
        if enable_optional is None:
            enable_optional = os.getenv("PROPOSAL_ENABLE_OPTIONAL_PROVIDERS", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_optional = enable_optional
        self.cache_ttl_seconds = max(0, int(os.getenv("PROPOSAL_RETRIEVAL_CACHE_TTL", "900")))
        self._cache: dict[tuple, tuple[float, DiscoveryResult]] = {}
        self._cache_lock = Lock()

    def _load(self) -> tuple[dict[str, dict], dict]:
        profiles_payload = json.loads(self.profile_path.read_text(encoding="utf-8"))
        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {item["direction_id"]: item for item in profiles_payload["profiles"]}, registry

    @staticmethod
    def _provider_error(provider: str, query: str, exc: Exception) -> dict:
        status = getattr(exc, "code", None)
        return {
            "provider": provider,
            "status": "rate_limited" if status == 429 else "failed",
            "query": query,
            "error_type": type(exc).__name__,
            "http_status": status,
        }

    @staticmethod
    def _zero_diagnosis(profile: dict | None, provider_statuses: list[dict], raw_count: int, hard_gate_count: int, eligible_count: int, request: DiscoveryRequest) -> dict:
        causes: list[str] = []
        evidence: list[str] = []
        if not profile:
            causes.append("route_missing")
        if any(item.get("status") == "rate_limited" for item in provider_statuses):
            causes.append("rate_limited")
        successful = [item for item in provider_statuses if item.get("status") == "ok"]
        if successful and all(item.get("returned_rows", 0) == 0 for item in successful):
            causes.append("provider_empty")
        if raw_count and not hard_gate_count:
            causes.append("quality_gate_too_strict")
        if hard_gate_count and not eligible_count:
            causes.append("quality_gate_too_strict")
        if profile and successful and raw_count < profile.get("coverage_targets", {}).get("raw_min", 20):
            causes.append("query_too_narrow")
        return {"causes": list(dict.fromkeys(causes)), "evidence": evidence}

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        try:
            profiles, registry = self._load()
        except (OSError, json.JSONDecodeError) as exc:
            return DiscoveryResult(status="DYNAMIC_RETRIEVAL_UNAVAILABLE", message_to_user=f"P1检索配置不可用（{type(exc).__name__}），已停止。")
        profile = profiles.get(request.selected_direction_id)
        if not profile:
            return DiscoveryResult(
                status="JOURNAL_ROUTE_UNAVAILABLE",
                message_to_user="该方向缺少版本化检索画像，已停止动态检索。",
                zero_result_diagnosis={"causes": ["route_missing"], "evidence": [request.selected_direction_id]},
            )

        cache_key = (
            profile["profile_version"], request.selected_direction_id,
            request.fine_grained_question or "", request.chinese_count, request.english_count,
            request.popularity_window_years, self.enable_optional,
        )
        if self.cache_ttl_seconds:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
            if cached and time.monotonic() - cached[0] <= self.cache_ttl_seconds:
                result = deepcopy(cached[1])
                result.provider_statuses.insert(0, {"provider": "local_memory_cache", "status": "hit", "returned_rows": len(result.analysis_papers)})
                return result

        today = date.today()
        from_year = today.year - request.popularity_window_years + 1
        from_date, to_date = f"{from_year}-01-01", today.isoformat()
        primary_query = request.fine_grained_question or profile["provider_queries"]["openalex"][0]
        query_plan = [primary_query]
        if not request.fine_grained_question:
            query_plan.extend(profile["fallback_queries"])
        else:
            query_plan.extend([f"{request.fine_grained_question} {profile['labels']['en']}", profile["fallback_queries"][0]])
        query_plan = list(dict.fromkeys(query_plan))

        raw_records: list[dict] = []
        search_log: list[dict] = []
        expansion_log: list[dict] = []
        provider_statuses: list[dict] = []
        allowed_pools = set(profile["journal_pool_ids"])
        journal_index = build_journal_index(registry)

        def preview_counts(records: list[dict]) -> tuple[int, int]:
            normalized = [normalize_record(item, "openalex") for item in records]
            for item in normalized:
                qualify_source(item, journal_index, allowed_pools)
            gated = [item for item in normalized if quality_gate(item, profile, from_year, today.year)[0]]
            return len(normalized), len(gated)

        for index, query in enumerate(query_plan):
            try:
                found, log = self.openalex.search(query, from_date, to_date, profile["document_types"])
                raw_records.extend({"_provider": "openalex", **item} for item in found)
                search_log.append(log)
                provider_statuses.append({"provider": "openalex", "attempt": index + 1, "status": "ok", "returned_rows": len(found), "query": query})
            except Exception as exc:
                failure = self._provider_error("openalex", query, exc)
                provider_statuses.append(failure)
                search_log.append(failure)
            raw_count, hard_gate_count = preview_counts([item for item in raw_records if item.get("_provider") == "openalex"])
            expansion_log.append({"attempt": index + 1, "provider": "openalex", "query": query, "raw_count": raw_count, "hard_gate_pass_count": hard_gate_count, "trigger": "initial" if index == 0 else "coverage_below_target"})
            if provider_statuses[-1].get("status") == "rate_limited":
                break
            if raw_count >= profile["coverage_targets"]["raw_min"] and hard_gate_count >= profile["coverage_targets"]["eligible_min"]:
                break

        # Optional sources enrich metadata and cover CS/HCI routes. They are opt-in
        # because public unauthenticated quotas are volatile.
        if self.enable_optional:
            optional_calls = [("semantic_scholar", self.semantic_scholar, profile["provider_queries"]["semantic_scholar"][0])]
            if "dblp" in profile["source_routes"]["optional"]:
                optional_calls.append(("dblp", self.dblp, profile["provider_queries"]["dblp"][0]))
            for name, provider, query in optional_calls:
                try:
                    if name == "semantic_scholar":
                        found, log = provider.search(query, from_year, today.year)
                    else:
                        found, log = provider.search(query)
                    raw_records.extend({"_provider": name, **item} for item in found)
                    search_log.append(log)
                    provider_statuses.append({"provider": name, "status": "ok", "returned_rows": len(found), "query": query})
                except Exception as exc:
                    failure = self._provider_error(name, query, exc)
                    provider_statuses.append(failure)
                    search_log.append(failure)
        else:
            for name in profile["source_routes"]["optional"]:
                provider_statuses.append({"provider": name, "status": "not_configured", "reason": "optional_provider_opt_in_required"})

        normalized = [normalize_record(item, item.pop("_provider")) for item in raw_records]
        deduped, dedupe_log = dedupe_records(normalized)
        hard_gate_pass: list[dict] = []
        exclusions: list[dict] = []
        query_for_score = request.fine_grained_question or profile["labels"]["en"]
        for record in deduped:
            qualify_source(record, journal_index, allowed_pools)
            passed, reasons = quality_gate(record, profile, from_year, today.year)
            record["checkpoint"] = {"passed": passed, "reasons": reasons, "version": "p1-hard-gate-1.0.0"}
            if not passed:
                exclusions.append({"paper_id": record["paper_id"], "title": record["title"], "reasons": reasons})
                continue
            record["score"] = score_record(record, profile, query_for_score, from_year, today.year)
            record["relevance_score"] = record["score"]["total"]
            hard_gate_pass.append(record)

        eligible = [item for item in hard_gate_pass if item["score"]["total"] >= 70]
        boundary = [item for item in hard_gate_pass if 55 <= item["score"]["total"] < 70]
        rejected_by_score = [item for item in hard_gate_pass if item["score"]["total"] < 55]
        exclusions.extend({"paper_id": item["paper_id"], "title": item["title"], "reasons": ["metadata_score_below_55"]} for item in rejected_by_score)
        eligible.sort(key=lambda item: (item["score"]["total"], item.get("year") or 0, item.get("citation_count") or 0), reverse=True)

        zh = [item for item in eligible if item["language"] == "zh"][:request.chinese_count]
        en = [item for item in eligible if item["language"] == "en"][:request.english_count]
        crossref_candidate_count = 0
        final_records = deduped
        final_hard_gate = hard_gate_pass

        # Crossref is the required DOI/journal verifier and a whitelist-constrained
        # fallback. It runs only when the fast OpenAlex route leaves a user-visible gap.
        if len(zh) < request.chinese_count or len(en) < request.english_count:
            crossref_request = DiscoveryRequest(
                selected_direction_id=request.selected_direction_id,
                research_direction=profile["labels"]["en"],
                fine_grained_question=request.fine_grained_question,
                chinese_count=request.chinese_count,
                english_count=request.english_count,
                popularity_window_years=request.popularity_window_years,
                journal_pool_ids=tuple(profile["journal_pool_ids"]),
                query_by_language={"zh": profile["labels"]["zh"], "en": request.fine_grained_question or profile["labels"]["en"]},
            )
            crossref_result = self.crossref.discover(crossref_request)
            crossref_candidate_count = len(crossref_result.analysis_papers)
            provider_statuses.append({"provider": "crossref", "status": crossref_result.status, "returned_rows": len(crossref_result.analysis_papers)})
            search_log.extend(crossref_result.search_log)
            exclusions.extend(crossref_result.exclusion_log)
            crossref_normalized = [normalize_record(item, "crossref") for item in crossref_result.analysis_papers]
            combined, crossref_dedupe = dedupe_records([*hard_gate_pass, *crossref_normalized])
            final_records = combined
            dedupe_log.extend(crossref_dedupe)
            eligible = []
            boundary = []
            final_hard_gate = []
            for record in combined:
                qualify_source(record, journal_index, allowed_pools)
                passed, reasons = quality_gate(record, profile, from_year, today.year)
                record["checkpoint"] = {"passed": passed, "reasons": reasons, "version": "p1-hard-gate-1.0.0"}
                if not passed:
                    continue
                final_hard_gate.append(record)
                record["score"] = score_record(record, profile, query_for_score, from_year, today.year)
                record["relevance_score"] = record["score"]["total"]
                (eligible if record["score"]["total"] >= 70 else boundary if record["score"]["total"] >= 55 else []).append(record)
            eligible.sort(key=lambda item: (item["score"]["total"], item.get("year") or 0, item.get("citation_count") or 0), reverse=True)
            zh = [item for item in eligible if item["language"] == "zh"][:request.chinese_count]
            en = [item for item in eligible if item["language"] == "en"][:request.english_count]
        else:
            provider_statuses.append({"provider": "crossref", "status": "not_queried", "reason": "coverage_target_met_before_fallback"})

        selected = zh + en
        shortages = {"zh": max(0, request.chinese_count - len(zh)), "en": max(0, request.english_count - len(en))}
        raw_count = len(raw_records) + crossref_candidate_count
        zero = self._zero_diagnosis(profile, provider_statuses, raw_count, len(final_hard_gate), len(eligible), request)
        if request.chinese_count and not zh:
            zero["causes"].append("language_coverage_gap")
            zero["evidence"].append("post-gate Chinese result count is zero")
        zero["causes"] = list(dict.fromkeys(zero["causes"]))
        coverage = {
            "direction_id": profile["direction_id"],
            "profile_version": profile["profile_version"],
            "raw_count": raw_count,
            "deduplicated_count": len(final_records),
            "hard_gate_pass_count": len(final_hard_gate),
            "eligible_count": len(eligible),
            "boundary_count": len(boundary),
            "selected_count": len(selected),
            "retracted_in_final": sum(item.get("integrity_status") == "retracted" for item in selected),
            "targets": profile["coverage_targets"],
        }
        if not selected:
            status = "DYNAMIC_RETRIEVAL_UNAVAILABLE"
            message = "多源检索已运行，但没有论文同时通过期刊范围闸门和未校准的70分候选阈值；诊断与扩展记录已保留。"
        elif any(shortages.values()):
            status = "RETRIEVAL_PARTIAL"
            message = f"P1多源检索完成：中文{len(zh)}/{request.chinese_count}篇、英文{len(en)}/{request.english_count}篇；不足部分保持缺口。评分阈值尚未完成人工校准。"
        else:
            status = "RETRIEVAL_COMPLETE"
            message = f"P1多源检索完成：中文{len(zh)}篇、英文{len(en)}篇；均通过本地期刊范围与硬闸门。评分阈值尚未完成人工校准。"
        result = DiscoveryResult(
            status=status, papers=selected, analysis_papers=eligible[:120], search_log=search_log,
            exclusion_log=exclusions, shortages=shortages, message_to_user=message,
            coverage_audit=coverage, provider_statuses=provider_statuses, expansion_log=expansion_log,
            dedupe_log=dedupe_log, zero_result_diagnosis=zero, score_config_version=SCORE_CONFIG_VERSION,
        )
        if self.cache_ttl_seconds:
            with self._cache_lock:
                self._cache[cache_key] = (time.monotonic(), deepcopy(result))
                expired = [key for key, (created_at, _) in self._cache.items() if time.monotonic() - created_at > self.cache_ttl_seconds]
                for key in expired:
                    self._cache.pop(key, None)
        return result
