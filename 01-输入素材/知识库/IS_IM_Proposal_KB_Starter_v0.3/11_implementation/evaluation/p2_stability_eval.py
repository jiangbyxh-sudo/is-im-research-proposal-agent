#!/usr/bin/env python3
"""P2 five-run stability evaluation over a frozen corpus snapshot.

Runs the deterministic clustering five times on the same snapshot and reports
exact-output consistency, pairwise ARI on paper-to-cluster assignments, and
representative-paper Jaccard. Determinism makes passing an engineering
property, not a statistical hope: any run-to-run difference is a defect.

On insufficient corpora this tool must report the honest blocked status and
never fabricate cluster assignments.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from stable_subdirection_clustering import P2ClusterConfig, deterministic_average_linkage  # noqa: E402

KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
DEFAULT_OUTPUT = WORKSPACE / "02-任务/01-current/T04-P2稳定五方向/验收证据/P2-稳定五方向"


def adjusted_rand_index(left: dict[str, str], right: dict[str, str]) -> float:
    """Pairwise-count ARI over the shared paper set; identical input space required."""
    keys = sorted(set(left) & set(right))
    if len(keys) < 2:
        return 0.0
    from collections import Counter

    left_labels = [left[key] for key in keys]
    right_labels = [right[key] for key in keys]
    contingency = Counter(zip(left_labels, right_labels))
    left_counts = Counter(left_labels)
    right_counts = Counter(right_labels)
    n = len(keys)

    def comb2(value: int) -> int:
        return value * (value - 1) // 2

    sum_cells = sum(comb2(count) for count in contingency.values())
    sum_left = sum(comb2(count) for count in left_counts.values())
    sum_right = sum(comb2(count) for count in right_counts.values())
    expected = sum_left * sum_right / comb2(n)
    maximum = (sum_left + sum_right) / 2
    if maximum == expected:
        return 1.0 if sum_left == sum_right else 0.0
    return (sum_cells - expected) / (maximum - expected)


def representative_papers(clusters: list[dict]) -> set[str]:
    """Centroid-nearest members are not stored per-run, so use fixed top-N by cluster order."""
    representatives: set[str] = set()
    for cluster in clusters:
        for paper_id in cluster["paper_ids"][:3]:
            representatives.add(paper_id)
    return representatives


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def evaluate_stability(snapshot: dict, runs: int = 5) -> dict:
    assignments: list[dict[str, str]] = []
    representatives: list[set[str]] = []
    statuses: list[str] = []
    for _ in range(runs):
        result = deterministic_average_linkage(snapshot)
        statuses.append(result["status"])
        if result.get("clusters"):
            assignment = {
                paper_id: cluster["cluster_id"]
                for cluster in result["clusters"]
                for paper_id in cluster["paper_ids"]
            }
            assignments.append(assignment)
            representatives.append(representative_papers(result["clusters"]))

    blocked = not statuses or not all(
        status in {"P2_CLUSTERING_COMPLETE", "P2_CLUSTERING_DEGRADED"} for status in statuses
    )
    if blocked:
        return {
            "snapshot_corpus_hash": snapshot.get("corpus_hash"),
            "paper_count": snapshot.get("paper_count"),
            "abstract_count": snapshot.get("abstract_count"),
            "statuses": statuses,
            "blocked": True,
            "note": "语料不足，未生成任何聚类；本结果不得作为五方向样例。",
        }

    canonical = [
        json.dumps(
            {paper: assignment[paper] for paper in sorted(assignment)}, ensure_ascii=False, sort_keys=True,
        )
        for assignment in assignments
    ]
    exact_consistency = len(set(canonical)) == 1
    pair_ari = [
        adjusted_rand_index(a, b)
        for a, b in combinations(assignments, 2)
    ]
    pair_jaccard = [
        jaccard(a, b)
        for a, b in combinations(representatives, 2)
    ]
    return {
        "snapshot_corpus_hash": snapshot.get("corpus_hash"),
        "paper_count": snapshot.get("paper_count"),
        "abstract_count": snapshot.get("abstract_count"),
        "statuses": statuses,
        "blocked": False,
        "degraded": any(status == "P2_CLUSTERING_DEGRADED" for status in statuses),
        "runs": len(assignments),
        "exact_output_consistency": exact_consistency,
        "mean_ari": round(sum(pair_ari) / max(1, len(pair_ari)), 4),
        "mean_representative_jaccard": round(sum(pair_jaccard) / max(1, len(pair_jaccard)), 4),
        "cluster_counts": [len({a[paper] for paper in a}) for a in assignments[:1]],
        "gates": {
            "consistency_100pct": exact_consistency,
            "ari_ge_0_85": all(value >= 0.85 for value in pair_ari),
            "jaccard_ge_0_80": all(value >= 0.80 for value in pair_jaccard),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--name", default="p2_stability")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_path": str(args.snapshot),
        "cluster_config_version": P2ClusterConfig().version,
        **evaluate_stability(snapshot, runs=args.runs),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / f"{args.name}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    gates = report.get("gates")
    return 0 if (report.get("blocked") or (gates and all(gates.values()))) else 2


if __name__ == "__main__":
    raise SystemExit(main())
