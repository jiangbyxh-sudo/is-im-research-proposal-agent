from __future__ import annotations

import sys
import unittest
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from stable_subdirection_clustering import (  # noqa: E402
    P2ClusterConfig,
    assess_corpus_sufficiency,
    build_corpus_snapshot,
)


def paper(index: int, with_abstract: bool = True) -> dict:
    return {
        "paper_id": f"P{index:03d}",
        "title": f"Stable paper {index}",
        "abstract": f"Abstract evidence {index}" if with_abstract else "",
        "year": 2026,
        "journal": "Information Systems Research",
        "doi": f"10.1000/stable.{index}",
    }


def snapshot(rows: list[dict], p1_passed: bool = False) -> dict:
    return build_corpus_snapshot(
        direction_id="topic_ai_enabled_information_systems",
        papers=rows,
        data_cutoff_date="2026-08-22",
        direction_profile_version="1.1.6-p1-retrieval",
        retrieval_version="p1-query-plan-1.0.0",
        score_version="p1-hybrid-reranker-1.0.1",
        p1_precision_gate_passed=p1_passed,
        p1_precision_summary={"overall_precision_at_10": 0.7667},
    )


class P2SnapshotTests(unittest.TestCase):
    def test_hash_is_invariant_to_input_order(self):
        rows = [paper(index) for index in range(1, 31)]
        self.assertEqual(snapshot(rows)["corpus_hash"], snapshot(list(reversed(rows)))["corpus_hash"])

    def test_content_change_changes_hash(self):
        rows = [paper(index) for index in range(1, 31)]
        changed = [dict(item) for item in rows]
        changed[0]["title"] = "Changed evidence"
        self.assertNotEqual(snapshot(rows)["corpus_hash"], snapshot(changed)["corpus_hash"])

    def test_p0_27_paper_snapshot_cannot_output_five_directions(self):
        result = assess_corpus_sufficiency(snapshot([paper(index) for index in range(1, 28)]))
        self.assertEqual(result["status"], "SYNTHESIS_INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["can_output_five_directions"])
        self.assertIn("paper_count_below_30", result["reasons"])

    def test_30_papers_and_20_abstracts_pass_snapshot_gate(self):
        rows = [paper(index, with_abstract=index <= 20) for index in range(1, 31)]
        result = assess_corpus_sufficiency(snapshot(rows), P2ClusterConfig())
        self.assertEqual(result["status"], "P2_CORPUS_READY")
        self.assertTrue(result["can_output_five_directions"])

    def test_p1_precision_risk_is_preserved(self):
        value = snapshot([paper(index) for index in range(1, 31)], p1_passed=False)
        self.assertFalse(value["p1_precision_gate_passed"])
        self.assertEqual(value["p1_precision_summary"]["overall_precision_at_10"], 0.7667)


if __name__ == "__main__":
    unittest.main()
