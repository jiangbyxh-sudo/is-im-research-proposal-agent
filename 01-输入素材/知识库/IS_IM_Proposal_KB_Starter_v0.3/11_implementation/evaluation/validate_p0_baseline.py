"""Fail-closed validator for the P0 baseline deliverable."""
from __future__ import annotations

import json
from pathlib import Path


IMPLEMENTATION_DIR = Path(__file__).resolve().parent.parent
KB_ROOT = IMPLEMENTATION_DIR.parent
WORKSPACE = KB_ROOT.parents[2]
REPORT_ROOT = WORKSPACE / "02-任务/99-done/T02-V0实现与结果报告/验收证据/P0-质量基线"


def _json(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _require_fields(payload: dict, fields: tuple[str, ...], label: str, failures: list[str]) -> None:
    for field in fields:
        if field not in payload:
            failures.append(f"{label}:missing_{field}")


def validate(report_root: Path = REPORT_ROOT) -> dict:
    failures = []
    coverage = _json(report_root / "direction_coverage_baseline.json")
    records = coverage.get("records", [])
    if len(records) != 61:
        failures.append(f"coverage_count={len(records)} expected=61")
    coverage_traces = list((report_root / "traces/coverage").glob("FIX-COVERAGE-*.json"))
    if len(coverage_traces) != 61:
        failures.append(f"coverage_trace_count={len(coverage_traces)} expected=61")
    for path in coverage_traces:
        payload = _json(path)
        _require_fields(
            payload,
            ("input", "versions", "query_plan", "provider_runs", "candidate_counts", "filters", "duration_ms", "errors"),
            path.name,
            failures,
        )

    challenges = _json(report_root / "challenge_baseline.json")
    if len(challenges.get("outcomes", [])) < 7:
        failures.append("challenge_cases_incomplete")
    challenge_traces = list((report_root / "traces/challenges").glob("CHALLENGE-*.json"))
    if len(challenge_traces) != 7:
        failures.append(f"challenge_trace_count={len(challenge_traces)} expected=7")
    for path in challenge_traces:
        payload = _json(path)
        _require_fields(payload, ("input", "status", "checkpoint"), path.name, failures)
    rate_trace = report_root / "traces/challenges/CHALLENGE-CROSSREF-429.json"
    if rate_trace.is_file():
        payload = _json(rate_trace)
        _require_fields(payload, ("versions", "provider_runs", "errors", "cost"), rate_trace.name, failures)

    model_path = report_root / "model_baseline_raw.json"
    if not model_path.is_file():
        failures.append("five_run_model_baseline_missing")
    else:
        model = _json(model_path)
        stability = model.get("stability", {})
        if stability.get("completed_runs") != 5:
            failures.append("stability_runs_not_five")
        traces = list((report_root / "traces/stability").glob("FIX-STABILITY-001-RUN-*.json"))
        if len(traces) != 5:
            failures.append(f"stability_trace_count={len(traces)} expected=5")
        for path in traces:
            payload = _json(path)
            _require_fields(
                payload,
                ("input", "versions", "candidate_counts", "clustering", "model", "duration_ms", "status", "errors"),
                path.name,
                failures,
            )
            model_trace = payload.get("model", {})
            _require_fields(model_trace, ("athlete_a", "usage", "cost"), f"{path.name}:model", failures)
        if not model.get("proposal_generated"):
            failures.append("proposal_baseline_missing")
        proposal_trace = report_root / "traces/proposal/FIX-PROPOSAL-001.json"
        if not proposal_trace.is_file():
            failures.append("proposal_trace_missing")
        else:
            payload = _json(proposal_trace)
            _require_fields(
                payload,
                ("input", "versions", "model", "human_rubric", "status", "errors", "missing_trace_fields"),
                proposal_trace.name,
                failures,
            )
            model_trace = payload.get("model", {})
            _require_fields(model_trace, ("output", "usage", "cost"), f"{proposal_trace.name}:model", failures)

    for name in ("开题人工Rubric评分.json", "写作指导项目针对性Rubric评分.json"):
        path = report_root / name
        if not path.is_file():
            failures.append(f"missing:{name}")
            continue
        scorecard = _json(path)
        if scorecard.get("weighted_total_0_100") is None:
            failures.append(f"manual_score_pending:{name}")
        if scorecard.get("checkpoint_passed") is None:
            failures.append(f"checkpoint_pending:{name}")
        for dimension in scorecard.get("dimensions", []):
            if dimension.get("score_0_100") is None:
                failures.append(f"dimension_score_pending:{name}:{dimension.get('dimension_id')}")

    for name in ("61方向覆盖基线报告.md", "五次稳定性基线报告.md", "开题人工评测报告.md", "完整Trace索引.md", "P0基线总报告.md"):
        if not (report_root / name).is_file():
            failures.append(f"missing_report:{name}")

    all_traces = list((report_root / "traces").glob("**/*.json"))
    if len(all_traces) != 74:
        failures.append(f"trace_count={len(all_traces)} expected=74")

    result = {
        "status": "P0_BASELINE_COMPLETE" if not failures else "P0_BASELINE_INCOMPLETE",
        "failures": failures,
        "coverage_records": len(records),
        "coverage_traces": len(coverage_traces),
        "stability_traces": len(list((report_root / "traces/stability").glob("*.json"))),
        "challenge_traces": len(challenge_traces),
        "total_traces": len(all_traces),
    }
    return result


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "P0_BASELINE_COMPLETE" else 1)
