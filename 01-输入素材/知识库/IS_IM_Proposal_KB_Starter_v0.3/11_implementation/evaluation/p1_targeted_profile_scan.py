#!/usr/bin/env python3
"""Recheck selected P1 direction profiles through an authenticated local Demo.

The OpenAlex key remains inside the Demo process. This runner only calls the
localhost API and records complete direction traces for profile tuning.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from p1_full_pipeline_scan import KB_ROOT, evaluate_direction, request_json, write_trace


DEFAULT_OUTPUT = KB_ROOT.parents[2] / (
    "02-任务/01-current/T03-P1检索质量工程/验收证据/"
    "P1-检索质量工程/targeted"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--direction-ids", required=True)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = request_json(f"{base_url}/api/health", timeout=15)
    if health.get("status") != "ok" or not health.get("openalex_authenticated"):
        raise SystemExit("Target Demo is not healthy and OpenAlex-authenticated")
    if not health.get("direction_profiles_ready"):
        raise SystemExit("Direction profiles are not available in the target Demo")

    profiles_payload = json.loads(
        (KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8")
    )
    profiles_by_id = {item["direction_id"]: item for item in profiles_payload["profiles"]}
    requested = [item.strip() for item in args.direction_ids.split(",") if item.strip()]
    missing = [item for item in requested if item not in profiles_by_id]
    if missing:
        raise SystemExit(f"Unknown direction ids: {', '.join(missing)}")

    results = []
    trace_dir = args.output_dir / "traces/targeted"
    for index, direction_id in enumerate(requested, start=1):
        result = evaluate_direction(base_url, profiles_by_id[direction_id], args.timeout)
        results.append(result)
        write_trace(trace_dir, result)
        print(
            f"{index:02d}/{len(requested):02d} {direction_id} "
            f"raw={result['raw_count']} eligible={result['eligible_count']} "
            f"status={result.get('status_code') or result['status']}",
            flush=True,
        )

    all_passed = all(
        item["status"] == "ok"
        and item["raw_target_met"]
        and item["eligible_target_met"]
        and not item["provider_rate_limited"]
        and item["provider_lane_failure_count"] == 0
        and item["retracted_in_final"] == 0
        and item["trace_count_conserved"]
        and item["candidate_trace_count"] == item["deduplicated_count"]
        for item in results
    )
    summary = {
        "evaluation": "P1 targeted direction profile check",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "profile_version": profiles_payload["version"],
        "requested_direction_ids": requested,
        "directions": len(results),
        "raw_target_met": sum(item["raw_target_met"] for item in results),
        "eligible_target_met": sum(item["eligible_target_met"] for item in results),
        "fatal_api_or_runner_failures": sum(item["status"] != "ok" for item in results),
        "provider_lane_failure_events": sum(item["provider_lane_failure_count"] for item in results),
        "rate_limited_directions": sum(item["provider_rate_limited"] for item in results),
        "trace_conserved_directions": sum(
            item["trace_count_conserved"] and item["candidate_trace_count"] == item["deduplicated_count"]
            for item in results
        ),
        "all_selected_gates_passed": all_passed,
        "results": [{key: value for key, value in item.items() if key != "api_response"} for item in results],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p1_targeted_profile_scan.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary | {"results": summary["results"]}, ensure_ascii=False))
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
