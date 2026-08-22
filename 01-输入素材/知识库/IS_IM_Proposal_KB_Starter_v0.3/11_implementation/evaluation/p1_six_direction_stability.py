#!/usr/bin/env python3
"""Recheck six representative P1 directions without exposing API keys."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from p1_full_pipeline_scan import (
    DEFAULT_OUTPUT,
    KB_ROOT,
    evaluate_direction,
    request_json,
    write_trace,
)
from p1_sampled_precision import REPRESENTATIVES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = request_json(f"{base_url}/api/health", timeout=15)
    if health.get("status") != "ok":
        raise SystemExit("Demo health check failed")
    if not health.get("openalex_authenticated"):
        raise SystemExit("OpenAlex is not authenticated in the target Demo process")

    profiles_payload = json.loads(
        (KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8")
    )
    profiles_by_id = {profile["direction_id"]: profile for profile in profiles_payload["profiles"]}
    selected = [(group_id, direction_id, profiles_by_id[direction_id]) for group_id, direction_id in REPRESENTATIVES.items()]

    trace_dir = args.output_dir / "traces/stability_challenge_1_1_2"
    results = []
    for index, (group_id, direction_id, profile) in enumerate(selected, 1):
        result = evaluate_direction(base_url, profile, args.timeout)
        result["group_id"] = group_id
        results.append(result)
        write_trace(trace_dir, result)
        print(
            f"{index:02d}/06 {group_id}:{direction_id} raw={result['raw_count']} "
            f"eligible={result['eligible_count']} lane_failures={result['provider_lane_failure_count']} "
            f"rate_limited={result['provider_rate_limited']}",
            flush=True,
        )

    fatal_failures = sum(result["status"] != "ok" for result in results)
    lane_failure_events = sum(result["provider_lane_failure_count"] for result in results)
    rate_limited = sum(result["provider_rate_limited"] for result in results)
    trace_conserved = sum(
        result["trace_count_conserved"]
        and result["candidate_trace_count"] == result["deduplicated_count"]
        for result in results
    )
    passed = (
        len(results) == 6
        and fatal_failures == 0
        and lane_failure_events == 0
        and rate_limited == 0
        and trace_conserved == 6
    )
    summary = {
        "evaluation": "P1 image 1.1.2 six-direction stability challenge",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "health": health,
        "profile_version": profiles_payload["version"],
        "representatives": REPRESENTATIVES,
        "directions": len(results),
        "fatal_api_or_runner_failures": fatal_failures,
        "provider_lane_failure_events": lane_failure_events,
        "rate_limited_directions": rate_limited,
        "trace_conserved_directions": trace_conserved,
        "passed": passed,
        "acceptance_note": (
            "Six-direction transport/rate-limit stability gate passed; proceed to the 61-direction scan."
            if passed
            else "Six-direction stability gate failed; do not start the 61-direction scan."
        ),
        "results": [{key: value for key, value in result.items() if key != "api_response"} for result in results],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / "p1_six_direction_stability_1_1_2.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
