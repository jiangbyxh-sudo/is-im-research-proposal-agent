#!/usr/bin/env python3
"""P2 four-set evaluation: fixed / held-out similar / regression / challenge.

Gate 6 of T04 requires that the fixed set, a held-out similar corpus, the
regression corpus, and adversarial challenge corpora all run through the real
deterministic clustering pipeline with a complete Trace and honest behaviour:
no corpus may ever output five directions unless the evidence supports five.

Naming (Athlete A/B + blind judge) is model-facing and is covered by unit
tests with stub clients, including failure fallback; this offline evaluation
covers the deterministic clustering, heat, degradation, and Trace contract.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from stable_subdirection_clustering import (  # noqa: E402
    P2ClusterConfig,
    build_corpus_snapshot,
    deterministic_average_linkage,
)

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "p2_stability_eval", IMPLEMENTATION / "evaluation/p2_stability_eval.py"
)
p2_stability_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p2_stability_eval)
evaluate_stability = p2_stability_eval.evaluate_stability

KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
EVIDENCE_DIR = WORKSPACE / "02-任务/01-current/T04-P2稳定五方向/验收证据/P2-稳定五方向"

FIXED_SNAPSHOT = EVIDENCE_DIR / "p2_qualified_corpus_snapshot.json"
REGRESSION_SNAPSHOT = EVIDENCE_DIR / "p2_p0_corpus_snapshot.json"

TOPICS = ["platform", "governance", "algorithm", "data", "regulation"]


def synthetic_paper(index: int, with_abstract: bool = True, relevance_tier: str = "direct") -> dict:
    topic = TOPICS[index % len(TOPICS)]
    return {
        "paper_id": f"C{index:03d}",
        "title": f"{topic.title()} challenge corpus paper {index}",
        "abstract": f"{topic} {topic} evidence in platform governance challenge {index}" if with_abstract else "",
        "year": 2026,
        "journal": "Information Systems Research",
        "doi": f"10.1000/challenge.{index}",
        "language": "en",
        "citation_count": index % 7,
        "topics": [{"id": f"T-{topic}", "name": topic}],
        "keywords": [{"name": f"platform {topic}"}],
        "relevance_tier": relevance_tier,
        "p1_match_score": {"total": 40.0 + (index % 30)},
        "source_quality": 85.0,
    }


def synthetic_snapshot(rows: list[dict], p1_passed: bool = True) -> dict:
    return build_corpus_snapshot(
        direction_id="platform_governance",
        papers=rows,
        data_cutoff_date="2026-08-23",
        direction_profile_version="1.2.0-p1-retrieval",
        retrieval_version="p1-query-plan-1.0.0",
        score_version="p1-directness-reranker-2.1.0",
        p1_precision_gate_passed=p1_passed,
    )


def trace_for(label: str, snapshot: dict, expected_status: str, expected_clusters: int | None = None) -> dict:
    result = deterministic_average_linkage(snapshot)
    clusters = result.get("clusters") or []
    honest_target = result.get("honest_target")
    return {
        "case": label,
        "direction_id": snapshot.get("direction_id"),
        "corpus_hash": snapshot.get("corpus_hash"),
        "paper_count": snapshot.get("paper_count"),
        "abstract_count": snapshot.get("abstract_count"),
        "p1_precision_gate_passed": bool(snapshot.get("p1_precision_gate_passed")),
        "status": result["status"],
        "expected_status": expected_status,
        "status_matches": result["status"] == expected_status,
        "honest_target": honest_target,
        "cluster_count": len(clusters),
        "expected_cluster_count": expected_clusters,
        "cluster_count_matches": expected_clusters is None or len(clusters) == expected_clusters,
        "cluster_sizes": [cluster["paper_count"] for cluster in clusters],
        "cluster_heat": [cluster.get("heat") for cluster in clusters],
        "language_counts": result.get("language_counts"),
        "cache_key": result.get("cache_key"),
        "hardcoded_five_violation": len(clusters) == 5 and (honest_target or 0) < 5,
    }


def build_heldout_snapshot(qualified: dict) -> dict:
    """Deterministic hold-out: drop every 4th paper by sorted paper_id (36 -> 27)."""
    papers = sorted(qualified["papers"], key=lambda item: item["paper_id"])
    kept = [paper for index, paper in enumerate(papers) if index % 4 != 0]
    return build_corpus_snapshot(
        direction_id=qualified["direction_id"],
        papers=kept,
        data_cutoff_date=qualified["data_cutoff_date"],
        direction_profile_version=qualified["direction_profile_version"],
        retrieval_version=qualified["retrieval_version"],
        score_version=qualified["score_version"],
        p1_precision_gate_passed=True,
        p1_precision_summary=qualified.get("p1_precision_summary") or {},
    )


def evaluate() -> dict:
    config = P2ClusterConfig()
    qualified = json.loads(FIXED_SNAPSHOT.read_text(encoding="utf-8"))
    p0 = json.loads(REGRESSION_SNAPSHOT.read_text(encoding="utf-8"))
    p0_gate_passed_variant = {**p0, "p1_precision_gate_passed": True}

    traces = {
        "fixed": [
            trace_for("fixed_qualified_36", qualified, "P2_CLUSTERING_COMPLETE", 5),
        ],
        "heldout_similar": [
            trace_for("heldout_every_4th_removed", build_heldout_snapshot(qualified), "P2_CLUSTERING_DEGRADED", 4),
        ],
        "regression": [
            trace_for("p0_snapshot_as_archived", p0, "P2_BLOCKED_BY_P1_PRECISION", 0),
            trace_for("p0_snapshot_gate_passed_variant", p0_gate_passed_variant, "SYNTHESIS_INSUFFICIENT_EVIDENCE", 0),
        ],
        "challenge": [
            trace_for(
                "challenge_missing_abstracts_40p_10a",
                synthetic_snapshot([synthetic_paper(i, with_abstract=i < 10) for i in range(40)]),
                "SYNTHESIS_INSUFFICIENT_EVIDENCE", 0,
            ),
            trace_for(
                "challenge_small_corpus_14_papers",
                synthetic_snapshot([synthetic_paper(i) for i in range(14)]),
                "SYNTHESIS_INSUFFICIENT_EVIDENCE", 0,
            ),
            trace_for(
                "challenge_p1_gate_off_qualified",
                {**qualified, "p1_precision_gate_passed": False},
                "P2_BLOCKED_BY_P1_PRECISION", 0,
            ),
            trace_for(
                "challenge_adjacent_only_no_direct",
                synthetic_snapshot([synthetic_paper(i, relevance_tier="adjacent") for i in range(30)]),
                "SYNTHESIS_INSUFFICIENT_EVIDENCE", 0,
            ),
        ],
    }

    fixed_stability = evaluate_stability(qualified, runs=5)
    heldout_stability = evaluate_stability(build_heldout_snapshot(qualified), runs=5)

    all_traces = [trace for group in traces.values() for trace in group]
    gates = {
        "all_expected_statuses_match": all(trace["status_matches"] for trace in all_traces),
        "all_expected_cluster_counts_match": all(trace["cluster_count_matches"] for trace in all_traces),
        "hardcoded_five_direction_count_zero": not any(trace["hardcoded_five_violation"] for trace in all_traces),
        "fixed_set_stability_gates": bool(fixed_stability.get("gates")) and all(fixed_stability["gates"].values()),
        "fixed_set_exact_consistency": bool(fixed_stability.get("exact_output_consistency")),
        "heldout_never_outputs_five": all(
            trace["cluster_count"] < 5 for trace in traces["heldout_similar"]
        ),
        "heldout_stability_gates": bool(heldout_stability.get("gates")) and all(heldout_stability["gates"].values()),
        "trace_complete": all(
            trace.get("corpus_hash") and trace.get("cache_key") and trace.get("language_counts") is not None
            for trace in all_traces
        ),
        "regression_blocks_without_clusters": all(
            trace["cluster_count"] == 0 for trace in traces["regression"]
        ),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cluster_config_version": config.version,
        "snapshot_version_used": qualified.get("snapshot_version"),
        "sets": traces,
        "fixed_set_five_run_stability": fixed_stability,
        "heldout_five_run_stability": heldout_stability,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EVIDENCE_DIR / "p2_four_set_eval.json")
    args = parser.parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "all_gates_passed": report["all_gates_passed"],
        "gates": report["gates"],
        "fixed_stability": {
            key: report["fixed_set_five_run_stability"].get(key)
            for key in ["exact_output_consistency", "mean_ari", "mean_representative_jaccard"]
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["all_gates_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
