#!/usr/bin/env python3
"""Build the first P2 snapshot and sufficiency evidence from a fixed corpus."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from stable_subdirection_clustering import assess_corpus_sufficiency, build_corpus_snapshot  # noqa: E402


KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
DEFAULT_P0 = WORKSPACE / (
    "02-任务/99-done/T02-V0实现与结果报告/验收证据/"
    "P0-质量基线/fixed_corpus_snapshot.json"
)
DEFAULT_P1 = WORKSPACE / (
    "02-任务/99-done/T03-P1检索质量工程/验收证据/P1-检索质量工程/"
    "certification/profile-1.1.3-high-confidence/p1_sampled_precision_result.json"
)
DEFAULT_OUTPUT = WORKSPACE / "02-任务/01-current/T04-P2稳定五方向/验收证据/P2-稳定五方向"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p0-snapshot", type=Path, default=DEFAULT_P0)
    parser.add_argument("--p1-precision", type=Path, default=DEFAULT_P1)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    p0 = json.loads(args.p0_snapshot.read_text(encoding="utf-8"))
    p1 = json.loads(args.p1_precision.read_text(encoding="utf-8"))
    snapshot = build_corpus_snapshot(
        direction_id=p0.get("direction_id") or "topic_ai_enabled_information_systems",
        papers=p0.get("papers") or [],
        data_cutoff_date="2026-08-22",
        direction_profile_version="1.1.6-p1-retrieval",
        retrieval_version="p1-query-plan-1.0.0",
        score_version="p1-hybrid-reranker-1.0.1",
        p1_precision_gate_passed=bool(p1.get("passed")),
        p1_precision_summary={
            "overall_precision_at_10": p1.get("overall_precision_at_10"),
            "obvious_false_positive_rate": p1.get("obvious_false_positive_rate"),
            "gates": p1.get("gates") or {},
        },
    )
    sufficiency = assess_corpus_sufficiency(snapshot)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "p2_p0_corpus_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "p2_p0_sufficiency.json").write_text(
        json.dumps(sufficiency, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(sufficiency, ensure_ascii=False))
    return 0 if sufficiency["can_output_five_directions"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
