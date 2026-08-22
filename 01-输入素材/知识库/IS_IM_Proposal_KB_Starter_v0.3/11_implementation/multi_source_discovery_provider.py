"""P1 profile-first, lane-based and count-conserving discovery orchestrator."""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import date
from pathlib import Path
from threading import Lock

from candidate_ledger import build_candidate_trace, evaluate_candidate, ledger_summary
from dblp_provider import DblpPaperProvider
from openalex_provider import OpenAlexPaperProvider
from paper_discovery_provider import CrossrefPaperDiscoveryProvider, DiscoveryRequest, DiscoveryResult
from paper_quality import SCORE_CONFIG_VERSION, build_journal_index, dedupe_records, normalize_record
from retrieval_query_plan import build_direction_query_plans
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
    def _provider_error(provider: str, lane_id: str, exc: Exception) -> dict:
        status = getattr(exc, "code", None)
        return {
            "provider": provider,
            "status": "rate_limited" if status == 429 else "failed",
            "lane_id": lane_id,
            "error_type": type(exc).__name__,
            "http_status": status,
        }

    @staticmethod
    def _diagnosis(profile: dict, provider_statuses: list[dict], coverage: dict, request: DiscoveryRequest) -> dict:
        causes: list[str] = []
        evidence: list[str] = []
        if any(item.get("status") == "rate_limited" for item in provider_statuses):
            causes.append("rate_limited")
        successful = [item for item in provider_statuses if item.get("status") == "ok"]
        if successful and all(item.get("returned_rows", 0) == 0 for item in successful):
            causes.append("provider_empty")
        if coverage.get("deduplicated_count") and not coverage.get("eligible_count"):
            causes.append("direction_boundary_or_relevance_floor")
        if coverage.get("deduplicated_count", 0) < profile.get("coverage_targets", {}).get("raw_min", 20):
            causes.append("query_too_narrow")
        if request.chinese_count and coverage.get("selected_zh_count", 0) < request.chinese_count:
            causes.append("language_coverage_gap")
            evidence.append("Chinese quota is independent; English records were not used to fill it")
        return {"causes": list(dict.fromkeys(causes)), "evidence": evidence}

    @staticmethod
    def _evaluate_all(raw_records: list[dict], profile: dict, registry: dict, from_year: int, to_year: int, query: str):
        normalized = [normalize_record({key: value for key, value in item.items() if key != "_provider"}, item["_provider"]) for item in raw_records]
        deduped, dedupe_log = dedupe_records(normalized)
        journal_index = build_journal_index(registry)
        decisions = [
            evaluate_candidate(record, profile, journal_index, from_year, to_year, {"query": query})
            for record in deduped
        ]
        traces = [build_candidate_trace(record, decision) for record, decision in zip(deduped, decisions)]
        eligible = [record for record in deduped if record["terminal_status"] == "eligible"]
        eligible.sort(key=lambda item: (item["relevance_score"], item.get("year") or 0), reverse=True)
        return deduped, eligible, traces, dedupe_log

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
        score_query = request.fine_grained_question or profile["labels"]["en"]
        plans = build_direction_query_plans(profile, from_date, to_date, request.fine_grained_question)
        raw_records: list[dict] = []
        search_log: list[dict] = []
        expansion_log: list[dict] = []
        provider_statuses: list[dict] = []
        final_records: list[dict] = []
        eligible: list[dict] = []
        candidate_traces: list[dict] = []
        dedupe_log: list[dict] = []

        for index, plan in enumerate(plans):
            try:
                found, log = self.openalex.search(plan)
                raw_records.extend({"_provider": "openalex", **item} for item in found)
                search_log.append(log)
                provider_statuses.append({"provider": "openalex", "lane_id": plan.lane_id, "status": "ok", "returned_rows": len(found)})
            except Exception as exc:
                failure = self._provider_error("openalex", plan.lane_id, exc)
                provider_statuses.append(failure)
                search_log.append(failure)
            final_records, eligible, candidate_traces, dedupe_log = self._evaluate_all(raw_records, profile, registry, from_year, today.year, score_query)
            en_count = sum(record["language"] == "en" for record in eligible)
            zh_count = sum(record["language"] == "zh" for record in eligible)
            expansion_log.append({
                "attempt": index + 1,
                "provider": "openalex",
                "lane_id": plan.lane_id,
                "trigger": "initial" if index == 0 else "post_boundary_target_not_met",
                "raw_count": len(raw_records),
                "deduplicated_count": len(final_records),
                "post_boundary_eligible_count": len(eligible),
                "eligible_en_count": en_count,
                "eligible_zh_count": zh_count,
                "stop_target_met": en_count >= request.english_count and zh_count >= request.chinese_count,
            })
            if provider_statuses[-1].get("status") == "rate_limited":
                break
            if en_count >= request.english_count and zh_count >= request.chinese_count:
                expansion_log[-1]["stop_reason"] = "post_boundary_language_targets_met"
                break

        if self.enable_optional and len(eligible) < request.english_count + request.chinese_count:
            optional_calls = [("semantic_scholar", self.semantic_scholar, profile["queries"]["en_recall"][0])]
            if "dblp" in profile["source_routes"]["optional"]:
                optional_calls.append(("dblp", self.dblp, profile["queries"]["en_recall"][0]))
            for name, provider, query in optional_calls:
                try:
                    found, log = provider.search(query, from_year, today.year) if name == "semantic_scholar" else provider.search(query)
                    raw_records.extend({"_provider": name, "query_lane_ids": [f"D_{name}_seed"], **item} for item in found)
                    search_log.append(log)
                    provider_statuses.append({"provider": name, "status": "ok", "returned_rows": len(found), "lane_id": f"D_{name}_seed"})
                except Exception as exc:
                    provider_statuses.append(self._provider_error(name, f"D_{name}_seed", exc))
        elif not self.enable_optional:
            for name in profile["source_routes"]["optional"]:
                provider_statuses.append({"provider": name, "status": "not_configured", "reason": "optional_provider_opt_in_required"})

        final_records, eligible, candidate_traces, dedupe_log = self._evaluate_all(raw_records, profile, registry, from_year, today.year, score_query)
        zh = [record for record in eligible if record["language"] == "zh"][:request.chinese_count]
        en = [record for record in eligible if record["language"] == "en"][:request.english_count]

        if len(zh) < request.chinese_count or len(en) < request.english_count:
            source_policy = profile["source_policy"]
            crossref_request = DiscoveryRequest(
                selected_direction_id=request.selected_direction_id,
                research_direction=profile["labels"]["en"],
                fine_grained_question=request.fine_grained_question,
                chinese_count=request.chinese_count,
                english_count=request.english_count,
                popularity_window_years=request.popularity_window_years,
                journal_pool_ids=tuple(profile["journal_pool_ids"]),
                query_by_language={"zh": profile["queries"]["zh_precise"][0], "en": score_query},
                source_tier_pool_ids={
                    "A": tuple(source_policy["tier_a_pool_ids"]),
                    "B": tuple(source_policy["tier_b_pool_ids"]),
                    "ADJACENT": tuple(source_policy["adjacent_pool_ids"]),
                },
            )
            crossref_result = self.crossref.discover(crossref_request)
            crossref_raw = crossref_result.analysis_papers or crossref_result.papers
            raw_records.extend({"_provider": "crossref", "query_lane_ids": ["crossref_fallback"], **item} for item in crossref_raw)
            provider_statuses.append({"provider": "crossref", "status": crossref_result.status, "returned_rows": len(crossref_raw), "lane_id": "crossref_fallback"})
            search_log.extend(crossref_result.search_log)
            final_records, eligible, candidate_traces, dedupe_log = self._evaluate_all(raw_records, profile, registry, from_year, today.year, score_query)
            zh = [record for record in eligible if record["language"] == "zh"][:request.chinese_count]
            en = [record for record in eligible if record["language"] == "en"][:request.english_count]
            expansion_log.append({
                "provider": "crossref", "lane_id": "crossref_fallback", "trigger": "language_target_not_met",
                "returned_rows": len(crossref_raw), "post_boundary_eligible_count": len(eligible),
            })
        else:
            provider_statuses.append({"provider": "crossref", "status": "not_queried", "reason": "post_boundary_language_targets_met"})

        selected = [*zh, *en]
        ledger = ledger_summary(final_records, selected)
        shortages = {"zh": max(0, request.chinese_count - len(zh)), "en": max(0, request.english_count - len(en))}
        coverage = {
            "direction_id": profile["direction_id"],
            "profile_version": profile["profile_version"],
            "raw_count": len(raw_records),
            "hard_gate_pass_count": len(final_records) - ledger["gate_reject_count"],
            "eligible_count": ledger["eligible_count"],
            "boundary_count": ledger["boundary_count"],
            "selected_count": len(selected),
            "selected_zh_count": len(zh),
            "selected_en_count": len(en),
            "targets": profile["coverage_targets"],
            **ledger,
        }
        zero = self._diagnosis(profile, provider_statuses, coverage, request)
        if not selected:
            status = "DYNAMIC_RETRIEVAL_UNAVAILABLE"
            message = "多路检索已运行，但没有论文同时通过完整性闸门、方向边界和相关性底线；候选账本与诊断已保留。"
        elif any(shortages.values()):
            status = "RETRIEVAL_PARTIAL"
            message = f"P1多路检索完成：中文{len(zh)}/{request.chinese_count}篇、英文{len(en)}/{request.english_count}篇；不足部分保持缺口，未用其他语言或低相关论文补数。"
        else:
            status = "RETRIEVAL_COMPLETE"
            message = f"P1多路检索完成：中文{len(zh)}篇、英文{len(en)}篇；均通过方向边界并进入混合精排。"
        result = DiscoveryResult(
            status=status,
            papers=selected,
            analysis_papers=eligible[:120],
            search_log=search_log,
            exclusion_log=[
                {"paper_id": trace["paper_id"], "title": trace["title"], "reasons": trace["terminal_reasons"], "terminal_status": trace["terminal_status"]}
                for trace in candidate_traces if trace["terminal_status"] != "eligible"
            ],
            shortages=shortages,
            message_to_user=message,
            coverage_audit=coverage,
            provider_statuses=provider_statuses,
            expansion_log=expansion_log,
            dedupe_log=dedupe_log,
            zero_result_diagnosis=zero,
            score_config_version=SCORE_CONFIG_VERSION,
            candidate_traces=candidate_traces,
            lane_funnels=expansion_log,
            chinese_coverage={
                "requested": request.chinese_count,
                "selected": len(zh),
                "english_substitution_count": 0,
                "metadata_coverage_gap": len(zh) < request.chinese_count,
                "licensed_cnki_or_wanfang_configured": False,
            },
        )
        if self.cache_ttl_seconds:
            with self._cache_lock:
                self._cache[cache_key] = (time.monotonic(), deepcopy(result))
        return result
