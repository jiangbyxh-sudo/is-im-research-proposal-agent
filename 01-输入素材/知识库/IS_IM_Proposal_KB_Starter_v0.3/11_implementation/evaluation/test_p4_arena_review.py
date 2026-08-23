"""Deterministic tests for the P4 proposal arena review (T06 item 1)."""
import json
import sys
import unittest
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from proposal_arena_review import (  # noqa: E402
    ProposalArenaReviewer,
    select_high_risk_sections,
)

SECTIONS = [
    {"section_id": "working_title", "title": "暂定题目", "content": "题目", "citations": [], "assumptions": []},
    {"section_id": "concepts", "title": "概念界定", "content": "概念内容", "citations": [{"claim_id": "c1"}, {"claim_id": "c2"}], "assumptions": []},
    {"section_id": "background", "title": "研究背景", "content": "背景内容", "citations": [{"claim_id": "c1"}], "assumptions": []},
    {"section_id": "literature_status", "title": "研究现状", "content": "现状内容", "citations": [{"claim_id": "c1"}, {"claim_id": "c2"}], "assumptions": []},
    {"section_id": "theoretical_framework", "title": "理论框架", "content": "理论内容", "citations": [{"claim_id": "c1"}], "assumptions": ["理论边界待核"]},
    {"section_id": "research_design", "title": "研究设计", "content": "设计内容", "citations": [{"claim_id": "c1"}, {"claim_id": "c2"}], "assumptions": []},
    {"section_id": "timeline", "title": "研究计划", "content": "计划内容", "citations": [{"claim_id": "c1"}], "assumptions": []},
]


class ArenaClient:
    def __init__(self, mode: str = "honest"):
        self.mode = mode
        self.calls = []

    def complete(self, system, user):
        self.calls.append(system[:14])
        payload = json.loads(user)
        scope = [row["section_id"] for row in payload.get("sections", [])] or list(payload.get("candidate_1", {}))[:-1]
        if "评审员" in system:
            reviews = [{"section_id": sid, "score": 8, "issues": []} for sid in scope]
            raw = {"reviews": reviews, "overall": {"score": 8, "summary": "受控评审"}}
            if self.mode == "smuggle" and "评审员A" in system:
                raw["reviews"][0]["suggested_text"] = "改写后的正文"
            if self.mode == "missing_section":
                raw["reviews"] = reviews[:1]
            return json.loads(json.dumps(raw, ensure_ascii=False)), {"model": "controlled"}
        if "评审裁判" in system:
            verdicts = [{"section_id": sid, "verdict": "revise" if self.mode == "revise" and sid == scope[0] else "pass", "final_score": 7, "reason": "受控裁决"} for sid in scope]
            raw = {"verdicts": verdicts, "overall": {"verdict": "revise" if self.mode == "revise" else "pass", "score": 8, "reason": "受控"}}
            if self.mode == "bad_verdict":
                raw["verdicts"][0]["verdict"] = "approve"
            if self.mode == "judge_smuggle":
                raw["verdicts"][0]["rewritten"] = "裁判改写文本"
            return json.loads(json.dumps(raw, ensure_ascii=False)), {"model": "controlled"}
        return {}, {"model": "controlled"}


class HighRiskSelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_and_rule_based(self):
        first = select_high_risk_sections(SECTIONS)
        again = select_high_risk_sections(SECTIONS)
        self.assertEqual(first, again)  # 同输入同序
        reversed_set = set(select_high_risk_sections(list(reversed(SECTIONS))))
        self.assertEqual(set(first), reversed_set)  # 集合与输入顺序无关
        # 固定高风险节 + 带假设的节 + 引用<2的节
        for expected in ("literature_status", "theoretical_framework", "research_design", "working_title", "background", "timeline"):
            self.assertIn(expected, first)
        # 引用≥2、无假设、非固定高风险的节不入选
        self.assertNotEqual(set(first), {s["section_id"] for s in SECTIONS})


class ArenaReviewTests(unittest.TestCase):
    def test_honest_review_passes_and_records_verdicts(self):
        review = ProposalArenaReviewer(ArenaClient()).review("RQ?", SECTIONS)
        self.assertEqual("p4-athlete-judge-review-1.1.0", review["version"])
        self.assertEqual([], review["revise_section_ids"])
        self.assertEqual("pass", review["overall_verdict"])
        self.assertTrue(review["scope"])

    def test_revise_verdict_is_recorded_not_applied(self):
        review = ProposalArenaReviewer(ArenaClient(mode="revise")).review("RQ?", SECTIONS)
        self.assertEqual(1, len(review["revise_section_ids"]))
        self.assertEqual("revise", review["overall_verdict"])

    def test_reviewer_content_smuggling_invalidates_review(self):
        with self.assertRaisesRegex(ValueError, "rewrite"):
            ProposalArenaReviewer(ArenaClient(mode="smuggle")).review("RQ?", SECTIONS)

    def test_judge_smuggling_invalidates_review(self):
        with self.assertRaisesRegex(ValueError, "rewrite"):
            ProposalArenaReviewer(ArenaClient(mode="judge_smuggle")).review("RQ?", SECTIONS)

    def test_missing_section_review_is_rejected(self):
        with self.assertRaises(ValueError):
            ProposalArenaReviewer(ArenaClient(mode="missing_section")).review("RQ?", SECTIONS)

    def test_invalid_verdict_enum_is_rejected(self):
        with self.assertRaises(ValueError):
            ProposalArenaReviewer(ArenaClient(mode="bad_verdict")).review("RQ?", SECTIONS)


if __name__ == "__main__":
    unittest.main()
