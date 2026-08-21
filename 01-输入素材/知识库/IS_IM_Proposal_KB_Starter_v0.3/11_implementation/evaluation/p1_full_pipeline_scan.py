#!/usr/bin/env python3
"""Run the complete P1 discovery pipeline through an already configured Demo process.

The OpenAlex key remains inside the Demo process. This runner only calls the
public localhost API and never reads, accepts, stores, or prints the key.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


IMPLEMENTATION = Path(__file__).resolve().parents[1]
KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
DEFAULT_OUTPUT = WORKSPACE / "02-任务/01-current/T03-P1检索质量工程/验收证据/P1-检索质量工程"


def request_json(url: str, payload: dict | None = None, timeout: int = 240) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Demo API unavailable: {exc.reason}") from exc


def evaluate_direction(base_url: str, profile: dict, timeout: int) -> dict:
    payload = {
        "selected_direction_id": profile["direction_id"],
        "fine_grained_question": "",
        "chinese_count": 10,
        "english_count": 20,
        "run_synthesis": False,
    }
    started = time.monotonic()
    try:
        response = request_json(f"{base_url}/api/research", payload, timeout=timeout)
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        coverage = response.get("coverage_audit") or {}
        providers = response.get("provider_statuses") or []
        raw_count = int(coverage.get("raw_count") or 0)
        eligible_count = int(coverage.get("eligible_count") or 0)
        return {
            "direction_id": profile["direction_id"],
            "labels": profile["labels"],
            "input": payload,
            "duration_ms": elapsed_ms,
            "status": "ok" if response.get("status_code") not in {"INTERNAL_ERROR", "INVALID_REQUEST"} else "api_failed",
            "status_code": response.get("status_code"),
            "state": response.get("state"),
            "raw_count": raw_count,
            "hard_gate_pass_count": int(coverage.get("hard_gate_pass_count") or 0),
            "eligible_count": eligible_count,
            "boundary_count": int(coverage.get("boundary_count") or 0),
            "selected_count": int(coverage.get("selected_count") or len(response.get("papers") or [])),
            "raw_target_met": raw_count >= int(profile["coverage_targets"]["raw_min"]),
            "eligible_target_met": eligible_count >= int(profile["coverage_targets"]["eligible_min"]),
            "retracted_in_final": int(coverage.get("retracted_in_final") or 0),
            "shortages": response.get("shortages") or {},
            "provider_statuses": providers,
            "provider_rate_limited": any(item.get("status") == "rate_limited" for item in providers),
            "cache_hit": any(item.get("provider") == "local_memory_cache" and item.get("status") == "hit" for item in providers),
            "zero_result_diagnosis": response.get("zero_result_diagnosis") or {},
            "score_config_version": response.get("score_config_version"),
            "api_response": response,
        }
    except Exception as exc:
        return {
            "direction_id": profile["direction_id"],
            "labels": profile["labels"],
            "input": payload,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "status": "runner_failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_count": 0,
            "hard_gate_pass_count": 0,
            "eligible_count": 0,
            "boundary_count": 0,
            "selected_count": 0,
            "raw_target_met": False,
            "eligible_target_met": False,
            "retracted_in_final": 0,
            "provider_rate_limited": False,
            "cache_hit": False,
        }


def write_trace(trace_dir: Path, result: dict) -> None:
    trace_dir.mkdir(parents=True, exist_ok=True)
    target = trace_dir / f"{result['direction_id']}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = request_json(f"{base_url}/api/health", timeout=15)
    if health.get("status") != "ok":
        raise SystemExit("Demo health check failed")
    if not health.get("openalex_authenticated"):
        raise SystemExit("OpenAlex is not authenticated in the target Demo process")
    if not health.get("direction_profiles_ready"):
        raise SystemExit("Direction profiles are not available in the target Demo process")

    profiles_payload = json.loads(
        (KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8")
    )
    profiles = profiles_payload["profiles"]
    if len(profiles) != 61:
        raise SystemExit(f"Expected 61 profiles, got {len(profiles)}")

    trace_dir = args.output_dir / "traces/full_pipeline"
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as executor:
        futures = {
            executor.submit(evaluate_direction, base_url, profile, args.timeout): profile
            for profile in profiles
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            write_trace(trace_dir, result)
            print(
                f"{len(results):02d}/61 {result['direction_id']} "
                f"raw={result['raw_count']} eligible={result['eligible_count']} "
                f"status={result['status_code'] if result.get('status_code') else result['status']}",
                flush=True,
            )

    results.sort(key=lambda item: item["direction_id"])
    total = len(results)
    raw_met = sum(item["raw_target_met"] for item in results)
    eligible_met = sum(item["eligible_target_met"] for item in results)
    failures = sum(item["status"] != "ok" for item in results)
    rate_limited = sum(item["provider_rate_limited"] for item in results)
    retracted = sum(item["retracted_in_final"] for item in results)
    raw_required = math.ceil(total * 0.95)
    eligible_required = math.ceil(total * 0.90)
    reason_counts = Counter(
        reason
        for item in results
        for reason in (item.get("zero_result_diagnosis") or {}).get("causes", [])
    )
    coverage_gates_pass = (
        total == 61
        and failures == 0
        and raw_met >= raw_required
        and eligible_met >= eligible_required
        and retracted == 0
    )
    acceptance = "BLOCKED_PENDING_PRECISION_AT_20" if coverage_gates_pass else "NOT_ACCEPTED"
    summary = {
        "evaluation": "P1 complete discovery pipeline coverage",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "health": health,
        "profile_version": profiles_payload["version"],
        "directions": total,
        "raw_ge_20": raw_met,
        "raw_ge_20_rate": round(raw_met / total, 4),
        "raw_gate_required": raw_required,
        "eligible_ge_10": eligible_met,
        "eligible_ge_10_rate": round(eligible_met / total, 4),
        "eligible_gate_required": eligible_required,
        "provider_or_runner_failures": failures,
        "rate_limited_directions": rate_limited,
        "retracted_in_final": retracted,
        "cache_hit_directions": sum(item["cache_hit"] for item in results),
        "zero_diagnosis_counts": dict(reason_counts),
        "precision_at_20": None,
        "precision_status": "not_measured_requires_blind_human_labels",
        "coverage_gates_passed": coverage_gates_pass,
        "p1_acceptance_status": acceptance,
        "acceptance_note": "P1 cannot pass until blind human Precision@20 is measured at or above 0.80.",
        "results": [{key: value for key, value in item.items() if key != "api_response"} for item in results],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p1_full_pipeline_coverage.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# P1完整流水线61方向覆盖报告", "",
        f"- 运行时间（UTC）：{summary['generated_at']}",
        f"- 目标实例：{base_url}（OpenAlex认证状态：已确认；密钥未读取或写入Trace）",
        f"- DirectionProfile：{summary['profile_version']}",
        f"- 原始候选≥20：{raw_met}/61（门槛至少{raw_required}/61）",
        f"- 合格候选≥10：{eligible_met}/61（门槛至少{eligible_required}/61）",
        f"- Provider/Runner失败：{failures}/61；发生限流的方向：{rate_limited}/61",
        f"- 正式结果中的撤稿记录：{retracted}",
        "- Precision@20：未测，仍需人工盲标。",
        f"- 当前结论：{acceptance}。", "",
        "| Direction | Raw | Hard gate | Eligible | Selected | Retracted | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['direction_id']} | {item['raw_count']} | {item['hard_gate_pass_count']} | "
            f"{item['eligible_count']} | {item['selected_count']} | {item['retracted_in_final']} | "
            f"{item.get('status_code') or item['status']} |"
        )
    (args.output_dir / "P1完整流水线61方向覆盖报告.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "directions": total,
        "raw_ge_20": raw_met,
        "eligible_ge_10": eligible_met,
        "provider_or_runner_failures": failures,
        "rate_limited_directions": rate_limited,
        "retracted_in_final": retracted,
        "p1_acceptance_status": acceptance,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
