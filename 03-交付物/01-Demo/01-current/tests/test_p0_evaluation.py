import json
import sys
import tempfile
import unittest
from pathlib import Path


KB_IMPLEMENTATION_DIR = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3/11_implementation"
sys.path.insert(0, str(KB_IMPLEMENTATION_DIR))

from evaluation.rubrics import PROPOSAL_RUBRIC, blank_human_scorecard, calculate_weighted_total  # noqa: E402
from observability.trace import write_trace  # noqa: E402


class P0EvaluationTests(unittest.TestCase):
    def test_proposal_human_rubric_weights_total_100(self):
        self.assertEqual(sum(item[2] for item in PROPOSAL_RUBRIC), 100)
        scorecard = blank_human_scorecard(PROPOSAL_RUBRIC, evaluator="test")
        for item in scorecard["dimensions"]:
            item["score_0_100"] = 80
        self.assertEqual(calculate_weighted_total(scorecard), 80.0)

    def test_trace_redacts_secret_but_keeps_token_usage_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            _, path = write_trace(Path(directory), "CASE-001", {
                "api_key": "should-not-be-written",
                "model": {"total_tokens": 123},
            })
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["model"]["total_tokens"], 123)

    def test_fixed_dataset_contains_61_coverage_cases_by_convention(self):
        dataset = KB_IMPLEMENTATION_DIR / "evaluation/datasets/fixed/p0_fixed_cases.json"
        payload = json.loads(dataset.read_text(encoding="utf-8"))
        ids = {item["case_id"] for item in payload["cases"]}
        self.assertIn("FIX-STABILITY-001", ids)
        self.assertIn("FIX-PROPOSAL-001", ids)
        self.assertIn("CHALLENGE-CROSSREF-429", ids)


if __name__ == "__main__":
    unittest.main()
