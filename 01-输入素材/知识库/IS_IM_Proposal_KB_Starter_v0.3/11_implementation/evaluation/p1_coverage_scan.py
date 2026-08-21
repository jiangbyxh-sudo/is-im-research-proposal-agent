#!/usr/bin/env python3
"""Run the P1 primary-route live coverage preflight across all 61 profiles."""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
if str(IMPLEMENTATION) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION))

from openalex_provider import OpenAlexPaperProvider, OpenAlexTransport
from paper_quality import build_journal_index, dedupe_records, normalize_record, qualify_source, quality_gate, score_record


def evaluate(profile: dict, registry_index: dict, provider: OpenAlexPaperProvider) -> dict:
    today = date.today()
    from_year = today.year - 4
    query = profile["provider_queries"]["openalex"][0]
    try:
        raw, provider_meta = provider.search(query, f"{from_year}-01-01", today.isoformat(), profile["document_types"])
    except Exception as exc:
        return {
            "direction_id": profile["direction_id"], "labels": profile["labels"], "query": query,
            "status": "provider_failed", "error_type": type(exc).__name__, "http_status": getattr(exc, "code", None),
            "raw_count": 0, "hard_gate_pass_count": 0, "eligible_count": 0, "boundary_count": 0,
        }
    records, dedupe_log = dedupe_records([normalize_record(item, "openalex") for item in raw])
    gate_pass = []
    exclusion_counts: dict[str, int] = {}
    allowed_pools = set(profile["journal_pool_ids"])
    for record in records:
        qualify_source(record, registry_index, allowed_pools)
        passed, reasons = quality_gate(record, profile, from_year, today.year)
        if not passed:
            for reason in reasons:
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
            continue
        record["score"] = score_record(record, profile, profile["labels"]["en"], from_year, today.year)
        gate_pass.append(record)
    eligible = sorted(
        (item for item in gate_pass if item["score"]["total"] >= 70),
        key=lambda item: item["score"]["total"], reverse=True,
    )
    boundary = [item for item in gate_pass if 55 <= item["score"]["total"] < 70]
    return {
        "direction_id": profile["direction_id"], "labels": profile["labels"], "query": query, "status": "ok",
        "raw_count": len(raw), "deduplicated_count": len(records), "hard_gate_pass_count": len(gate_pass),
        "eligible_count": len(eligible), "boundary_count": len(boundary),
        "raw_target_met": len(raw) >= profile["coverage_targets"]["raw_min"],
        "eligible_target_met": len(eligible) >= profile["coverage_targets"]["eligible_min"],
        "provider_meta": provider_meta, "exclusion_counts": exclusion_counts,
        "dedupe_event_count": len(dedupe_log),
        "top_candidates": [
            {"paper_id": item["paper_id"], "title": item["title"], "year": item["year"], "journal": item["journal"], "doi": item["doi"], "score": item["score"]}
            for item in eligible[:5]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=WORKSPACE / "02-任务/01-current/T02-V0实现与结果报告/验收证据/P1-检索质量工程")
    args = parser.parse_args()
    profiles_payload = json.loads((KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8"))
    registry = json.loads((KB_ROOT / "02_journals/generated/journal_registry.json").read_text(encoding="utf-8"))
    registry_index = build_journal_index(registry)
    provider = OpenAlexPaperProvider(OpenAlexTransport(timeout=22, retries=2), per_page=100)
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as executor:
        futures = {executor.submit(evaluate, profile, registry_index, provider): profile for profile in profiles_payload["profiles"]}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{len(results):02d}/61 {result['direction_id']} raw={result['raw_count']} eligible={result['eligible_count']}", flush=True)
    results.sort(key=lambda item: item["direction_id"])
    raw_met = sum(item.get("raw_target_met", False) for item in results)
    eligible_met = sum(item.get("eligible_target_met", False) for item in results)
    failed = sum(item["status"] != "ok" for item in results)
    summary = {
        "evaluation": "P1 primary-route live coverage preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_version": profiles_payload["version"],
        "directions": len(results),
        "raw_ge_20": raw_met,
        "raw_ge_20_rate": round(raw_met / len(results), 4),
        "eligible_ge_10": eligible_met,
        "eligible_ge_10_rate": round(eligible_met / len(results), 4),
        "provider_failures": failed,
        "precision_at_20": None,
        "precision_status": "not_measured_requires_blind_human_labels",
        "p1_acceptance_status": "NOT_EVALUATED_FULL_PIPELINE",
        "scope_note": "Primary OpenAlex query only; fallback expansion, Crossref verification, optional providers and human Precision@20 are evaluated separately.",
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p1_primary_route_coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    trace_dir = args.output_dir / "traces/coverage"
    trace_dir.mkdir(parents=True, exist_ok=True)
    for item in results:
        (trace_dir / f"{item['direction_id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# P1 主路由 61 方向真实覆盖预检", "",
        f"- 运行时间（UTC）：{summary['generated_at']}",
        f"- DirectionProfile：{summary['profile_version']}",
        f"- 原始候选 ≥20：{raw_met}/61（{summary['raw_ge_20_rate']:.1%}）",
        f"- ≥70 分候选 ≥10：{eligible_met}/61（{summary['eligible_ge_10_rate']:.1%}）",
        f"- Provider 失败：{failed}/61",
        "- Precision@20：未测；必须完成人工盲标后才能填写。",
        "- 结论：这是 OpenAlex 主查询预检，不是完整 P1 验收，不能据此声称 P1 达标。", "",
        "| Direction | Raw | Hard gate | Eligible | Boundary | Status |", "|---|---:|---:|---:|---:|---|",
    ]
    for item in results:
        lines.append(f"| {item['direction_id']} | {item['raw_count']} | {item['hard_gate_pass_count']} | {item['eligible_count']} | {item['boundary_count']} | {item['status']} |")
    (args.output_dir / "P1主路由61方向覆盖预检.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("directions", "raw_ge_20", "eligible_ge_10", "provider_failures", "p1_acceptance_status")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
