"""Deterministic tests for the P2 five-run stability evaluator."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

_spec = importlib.util.spec_from_file_location(
    "p2_stability_eval", IMPLEMENTATION / "evaluation/p2_stability_eval.py"
)
p2_stability_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p2_stability_eval)
adjusted_rand_index = p2_stability_eval.adjusted_rand_index
evaluate_stability = p2_stability_eval.evaluate_stability

from stable_subdirection_clustering import build_corpus_snapshot  # noqa: E402


def synthetic_papers(count_per_group: int = 6, groups: int = 5, abstract_every: int = 4) -> list[dict]:
    vocab = [
        "platform governance regulation openness",
        "algorithm recommendation personalization consumer",
        "trust artificial intelligence transparency human",
        "knowledge sharing community collaboration wiki",
        "privacy disclosure concern personal data",
    ]
    papers = []
    pid = 0
    for terms in vocab[:groups]:
        for index in range(count_per_group):
            pid += 1
            papers.append({
                "paper_id": f"P{pid:03d}",
                "title": f"{terms.split()[0]} study {index} on {terms}",
                "abstract": f"We examine {terms} in organizational context {index}." if pid % abstract_every != 0 else "",
                "journal": "Test Journal",
                "year": 2024,
                "doi": f"10.0/synth.{pid}",
                "relevance_tier": "direct",
                "terminal_status": "eligible",
            })
    return papers


def snapshot_for(papers: list[dict], gate_passed: bool = True) -> dict:
    return build_corpus_snapshot(
        direction_id="topic_ai_enabled_information_systems",
        papers=papers,
        data_cutoff_date="2026-08-23",
        direction_profile_version="1.2.0-p1-retrieval",
        retrieval_version="p1-query-plan-1.0.0",
        score_version="p1-directness-reranker-2.1.0",
        p1_precision_gate_passed=gate_passed,
    )


class AdjustedRandIndexTests(unittest.TestCase):
    def test_identical_partitions_score_one(self):
        left = {"a": "c1", "b": "c1", "c": "c2", "d": "c2"}
        self.assertEqual(1.0, adjusted_rand_index(left, dict(left)))

    def test_disjoint_partitions_score_zero_or_negative(self):
        left = {"a": "1", "b": "1", "c": "2", "d": "2"}
        right = {"a": "1", "c": "1", "b": "2", "d": "2"}
        self.assertLessEqual(adjusted_rand_index(left, right), 0.0)

    def test_partial_agreement_between_zero_and_one(self):
        left = {"a": "1", "b": "1", "c": "2", "d": "2", "e": "3"}
        right = {"a": "1", "b": "1", "c": "2", "d": "3", "e": "3"}
        value = adjusted_rand_index(left, right)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)


class StabilityEvaluationTests(unittest.TestCase):
    def test_deterministic_pipeline_is_perfectly_stable(self):
        report = evaluate_stability(snapshot_for(synthetic_papers()), runs=5)
        self.assertFalse(report["blocked"])
        self.assertTrue(report["exact_output_consistency"])
        self.assertEqual(1.0, report["mean_ari"])
        self.assertEqual(1.0, report["mean_representative_jaccard"])
        self.assertTrue(all(report["gates"].values()))

    def test_insufficient_corpus_reports_blocked_without_clusters(self):
        report = evaluate_stability(snapshot_for(synthetic_papers(count_per_group=2)), runs=5)
        self.assertTrue(report["blocked"])
        self.assertNotIn("mean_ari", report)
        self.assertTrue(any("below_30" in status or status == "SYNTHESIS_INSUFFICIENT_EVIDENCE" for status in report["statuses"]))

    def test_p1_gate_blocked_snapshot_never_clusters(self):
        report = evaluate_stability(snapshot_for(synthetic_papers(), gate_passed=False), runs=5)
        self.assertTrue(report["blocked"])
        self.assertTrue(all(status == "P2_BLOCKED_BY_P1_PRECISION" for status in report["statuses"]))


if __name__ == "__main__":
    unittest.main()
