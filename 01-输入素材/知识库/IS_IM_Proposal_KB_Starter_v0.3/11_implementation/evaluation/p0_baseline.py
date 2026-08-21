"""Reproducible P0 coverage baseline for the current Crossref-only pipeline."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parent
IMPLEMENTATION_DIR = EVALUATION_DIR.parent
KB_ROOT = IMPLEMENTATION_DIR.parent
WORKSPACE = KB_ROOT.parents[2]
APP_ROOT = WORKSPACE / "03-交付物/01-Demo/01-current"
DEFAULT_REPORT_ROOT = WORKSPACE / "02-任务/99-done/T02-V0实现与结果报告/验收证据/P0-质量基线"
CATALOG_PATH = KB_ROOT / "01_taxonomy/generated/research_direction_catalog.json"
REGISTRY_PATH = KB_ROOT / "02_journals/generated/journal_registry.json"

for path in (str(IMPLEMENTATION_DIR), str(APP_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from observability.trace import utc_now, write_trace  # noqa: E402
from paper_discovery_provider import CrossrefPaperDiscoveryProvider, DiscoveryRequest  # noqa: E402


def _load_server_module():
    spec = importlib.util.spec_from_file_location("p0_proposal_server", APP_ROOT / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _hash_json(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((len(ordered) * percentile) - 1)))
    return round(ordered[index], 2)


def _zero_reason(result) -> str | None:
    if result.analysis_papers:
        return None
    if result.status == "JOURNAL_ROUTE_UNAVAILABLE":
        return "route_missing"
    failures = [item for item in result.exclusion_log if item.get("reason") == "provider_request_failed"]
    if any(item.get("http_status") == 429 for item in failures):
        return "rate_limited"
    if failures and not result.search_log:
        return "provider_failed"
    if result.shortages.get("zh") and not result.shortages.get("en"):
        return "language_coverage_gap"
    if result.search_log and not sum(int(item.get("returned_rows", 0)) for item in result.search_log):
        return "provider_empty"
    if result.exclusion_log:
        return "quality_or_relevance_gate"
    return "query_or_metadata_gap"


def run_coverage(report_root: Path, max_journals: int, rows: int, limit: int | None = None) -> dict:
    report_root = report_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    trace_dir = report_root / "traces/coverage"
    server = _load_server_module()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    directions = catalog["directions"][:limit] if limit else catalog["directions"]
    provider = CrossrefPaperDiscoveryProvider(
        REGISTRY_PATH,
        max_journals_per_language=max_journals,
        rows_per_journal=rows,
    )
    records = []
    fixed_snapshot = None
    run_started = utc_now()
    for index, direction in enumerate(directions, start=1):
        case_id = f"FIX-COVERAGE-{index:03d}"
        pools = server.journal_pools_for(direction)
        request = DiscoveryRequest(
            selected_direction_id=direction["direction_id"],
            research_direction=direction["label"],
            fine_grained_question=None,
            chinese_count=10,
            english_count=20,
            journal_pool_ids=pools,
        )
        started_at = utc_now()
        started = time.monotonic()
        result = provider.discover(request)
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        exclusion_counts = Counter(item.get("reason", "unknown") for item in result.exclusion_log)
        final_language_counts = Counter(item.get("language", "unknown") for item in result.papers)
        raw_returned = sum(int(item.get("returned_rows", 0)) for item in result.search_log)
        accepted_before_dedupe = sum(int(item.get("accepted_before_dedupe", 0)) for item in result.search_log)
        corpus = result.analysis_papers
        corpus_hash = _hash_json([
            {"doi": item.get("doi"), "title": item.get("title"), "year": item.get("year")}
            for item in corpus
        ])
        trace_payload = {
            "stage": "P0_BASELINE_NOT_A_FIX",
            "started_at": started_at,
            "completed_at": utc_now(),
            "duration_ms": duration_ms,
            "input": {
                "selected_direction_id": direction["direction_id"],
                "research_direction": direction["label"],
                "fine_grained_question": None,
                "chinese_count": 10,
                "english_count": 20,
            },
            "versions": {
                "catalog": catalog.get("version"),
                "journal_registry": json.loads(REGISTRY_PATH.read_text(encoding="utf-8")).get("version"),
                "retrieval_provider": "crossref-current-baseline",
                "trace_schema": "1.0.0",
            },
            "query_plan": {
                "query": direction["label"],
                "journal_pool_ids": list(pools),
                "max_journals_per_language": max_journals,
                "rows_per_journal": rows,
                "popularity_window_years": 5,
                "concurrency": provider.max_workers,
                "concurrency_policy": provider.concurrency_policy,
            },
            "provider_runs": result.search_log,
            "candidate_counts": {
                "raw_returned": raw_returned,
                "accepted_before_dedupe": accepted_before_dedupe,
                "deduped_corpus": len(corpus),
                "final_selected": len(result.papers),
                "final_by_language": dict(final_language_counts),
            },
            "filters": dict(exclusion_counts),
            "status": result.status,
            "shortages": result.shortages,
            "zero_reason": _zero_reason(result),
            "errors": [item for item in result.exclusion_log if item.get("reason") == "provider_request_failed"],
            "final_papers": result.papers,
            "corpus_hash": corpus_hash,
            "model": {"called": False, "outputs": [], "token_usage": 0, "cost": 0},
            "missing_trace_fields": [
                "provider_raw_response_not_persisted",
                "paper_score_breakdown_not_implemented",
                "abstract_not_exposed_in_final_paper_record",
            ],
        }
        trace_id, trace_path = write_trace(trace_dir, case_id, trace_payload)
        record = {
            "case_id": case_id,
            "trace_id": trace_id,
            "trace_path": str(trace_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "direction_id": direction["direction_id"],
            "label": direction["label"],
            "query": direction["label"],
            "status": result.status,
            "raw_returned": raw_returned,
            "accepted_before_dedupe": accepted_before_dedupe,
            "deduped_corpus": len(corpus),
            "final_zh": final_language_counts.get("zh", 0),
            "final_en": final_language_counts.get("en", 0),
            "zero_reason": _zero_reason(result),
            "duration_ms": duration_ms,
            "provider_failures": exclusion_counts.get("provider_request_failed", 0),
        }
        records.append(record)
        if direction["direction_id"] == "topic_ai_enabled_information_systems" and corpus:
            fixed_snapshot = {
                "snapshot_version": "p0-fixed-corpus-1.0.0",
                "created_at": utc_now(),
                "source_case_id": case_id,
                "direction_id": direction["direction_id"],
                "research_direction": direction["label"],
                "corpus_hash": corpus_hash,
                "papers": corpus,
            }
            (report_root / "fixed_corpus_snapshot.json").write_text(
                json.dumps(fixed_snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        print(f"[{index:02d}/{len(directions):02d}] {direction['direction_id']}: corpus={len(corpus)} status={result.status}", flush=True)

    durations = [item["duration_ms"] for item in records]
    summary = {
        "baseline_version": "p0-coverage-baseline-1.0.0",
        "stage": "P0_BASELINE_NOT_A_FIX",
        "started_at": run_started,
        "completed_at": utc_now(),
        "direction_count": len(records),
        "zero_result_count": sum(item["deduped_corpus"] == 0 for item in records),
        "directions_with_20_raw_candidates": sum(item["raw_returned"] >= 20 for item in records),
        "directions_with_10_deduped_candidates": sum(item["deduped_corpus"] >= 10 for item in records),
        "directions_meeting_requested_zh_10": sum(item["final_zh"] >= 10 for item in records),
        "directions_meeting_requested_en_20": sum(item["final_en"] >= 20 for item in records),
        "provider_failure_count": sum(item["provider_failures"] for item in records),
        "latency_ms": {
            "mean": round(statistics.mean(durations), 2) if durations else None,
            "p50": round(statistics.median(durations), 2) if durations else None,
            "p95": _percentile(durations, 0.95),
        },
        "fixed_snapshot_created": bool(fixed_snapshot),
        "records": records,
    }
    (report_root / "direction_coverage_baseline.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# P0 · 61方向实网覆盖基线",
        "",
        "> 本报告描述当前Crossref单信源管线的实测基线，不代表覆盖问题已经修复。",
        "",
        f"- 运行方向：{summary['direction_count']}",
        f"- 零结果方向：{summary['zero_result_count']}",
        f"- 原始返回量≥20：{summary['directions_with_20_raw_candidates']}",
        f"- 去重语料≥10：{summary['directions_with_10_deduped_candidates']}",
        f"- 满足中文10篇：{summary['directions_meeting_requested_zh_10']}",
        f"- 满足英文20篇：{summary['directions_meeting_requested_en_20']}",
        f"- Provider请求失败：{summary['provider_failure_count']}",
        f"- 延迟p50/p95：{summary['latency_ms']['p50']} / {summary['latency_ms']['p95']} ms",
        "",
        "| Case | 方向 | 状态 | 原始 | 去重语料 | 中文 | 英文 | 零结果原因 | 耗时ms |",
        "|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for item in records:
        lines.append(
            f"| {item['case_id']} | {item['label']} | {item['status']} | {item['raw_returned']} | "
            f"{item['deduped_corpus']} | {item['final_zh']} | {item['final_en']} | {item['zero_reason'] or ''} | {item['duration_ms']} |"
        )
    (report_root / "61方向覆盖基线报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--max-journals-per-language", type=int, default=10)
    parser.add_argument("--rows-per-journal", type=int, default=20)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    summary = run_coverage(
        args.report_root,
        max_journals=max(1, args.max_journals_per_language),
        rows=max(1, args.rows_per_journal),
        limit=args.limit,
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
