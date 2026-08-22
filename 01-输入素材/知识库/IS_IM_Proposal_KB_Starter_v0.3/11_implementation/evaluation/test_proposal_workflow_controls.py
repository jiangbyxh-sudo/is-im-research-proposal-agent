from __future__ import annotations

import sys
import unittest
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from proposal_workflow_controls import (  # noqa: E402
    build_execution_task_cards,
    build_proposal_outline,
    evaluate_user_constraints,
    proposal_outline_matches,
)


def complete_constraints():
    return {
        "degree_level": "硕士", "institution_template": "无指定模板",
        "output_language": "中文", "target_word_count": 12000,
        "deadline": "2026-12-31", "data_access": "可招募在线参与者",
        "method_constraints": "无", "research_context": "AI辅助决策",
        "ethics_privacy": "知情同意并匿名化", "tool_capabilities": "Python和R",
    }


class ProposalWorkflowControlTests(unittest.TestCase):
    def test_missing_constraints_return_one_design_changing_question(self):
        result = evaluate_user_constraints({})
        self.assertFalse(result.complete)
        self.assertEqual("degree_level", result.missing_field)
        self.assertTrue(result.next_question)

    def test_constraint_hash_is_stable_and_word_count_is_bounded(self):
        first = evaluate_user_constraints(complete_constraints())
        reordered = dict(reversed(list(complete_constraints().items())))
        second = evaluate_user_constraints(reordered)
        self.assertTrue(first.complete)
        self.assertEqual(first.constraint_hash, second.constraint_hash)
        invalid = complete_constraints()
        invalid["target_word_count"] = 100
        self.assertEqual("target_word_count_out_of_bounds", evaluate_user_constraints(invalid).error)

    def test_outline_tampering_and_task_card_claim_escape_are_rejected(self):
        constraints = evaluate_user_constraints(complete_constraints())
        blueprint = {
            "blueprint_id": "blueprint_test", "constraint_hash": constraints.constraint_hash,
            "target_word_count": 12000, "claim_ids": ("claim_1",),
        }
        outline = build_proposal_outline(blueprint, (
            ("working_title", "暂定题目"), ("background", "研究背景与问题重要性"),
            ("timeline", "研究计划"),
        ))
        self.assertEqual(12000, sum(item["target_words"] for item in outline["sections"]))
        self.assertTrue(proposal_outline_matches(outline, dict(outline)))
        tampered = {**outline, "target_word_count": 9999}
        self.assertFalse(proposal_outline_matches(outline, tampered))
        cards = build_execution_task_cards(
            blueprint,
            outline,
            {"claims": [{"claim_id": "claim_1"}]},
        )
        self.assertTrue(cards["audit"]["valid"])
        self.assertTrue(cards["audit"]["claim_store_only"])
        self.assertEqual([], cards["cards"][0]["prerequisite_task_card_ids"])
        self.assertEqual(
            [cards["cards"][0]["task_card_id"]],
            cards["cards"][1]["prerequisite_task_card_ids"],
        )


if __name__ == "__main__":
    unittest.main()
