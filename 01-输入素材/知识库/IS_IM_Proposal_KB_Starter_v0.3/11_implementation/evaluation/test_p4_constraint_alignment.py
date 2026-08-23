"""Deterministic tests for the P4 constraint alignment audit and repetition metric."""
import sys
import unittest
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from proposal_workflow_controls import (  # noqa: E402
    audit_constraint_alignment,
    cross_section_repetition,
)

CONSTRAINTS = {
    "deadline": "2026-12-31", "target_word_count": 12000,
    "data_access": "公开平台数据与二手数据", "ethics_privacy": "不涉及人类被试敏感数据",
}


def outline_for(*pairs) -> dict:
    return {"sections": [{"section_id": sid, "target_words": words} for sid, words in pairs]}


class ConstraintAlignmentTests(unittest.TestCase):
    def test_deadline_year_violation_is_caught(self):
        sections = [{"section_id": "timeline", "content": "计划分四阶段，2027年6月完成全部研究。" * 40}]
        audit = audit_constraint_alignment(CONSTRAINTS, outline_for(("timeline", 480)), sections, today="2026-08-23")
        self.assertFalse(audit["valid"])
        self.assertTrue(any("beyond_deadline" in e for e in audit["errors"]))

    def test_duration_beyond_deadline_is_caught(self):
        sections = [{"section_id": "timeline", "content": "研究计划共24个月，分四阶段推进执行。" * 40}]
        audit = audit_constraint_alignment(CONSTRAINTS, outline_for(("timeline", 480)), sections, today="2026-08-23")
        self.assertTrue(any("duration" in e for e in audit["errors"]))

    def test_human_subject_term_contradicts_public_only_scope(self):
        sections = [{"section_id": "research_design", "content": "我们将开展互补者访谈并发放问卷。" * 60}]
        audit = audit_constraint_alignment(CONSTRAINTS, outline_for(("research_design", 2040)), sections, today="2026-08-23")
        self.assertTrue(any("human_subject_term" in e for e in audit["errors"]))

    def test_interview_allowed_when_constraints_permit(self):
        constraints = {**CONSTRAINTS, "data_access": "公开数据与半结构化访谈", "ethics_privacy": "访谈已获知情同意"}
        sections = [{"section_id": "research_design", "content": "我们将开展互补者访谈并做主题分析。" * 60}]
        audit = audit_constraint_alignment(constraints, outline_for(("research_design", 2040)), sections, today="2026-08-23")
        self.assertFalse(any("human_subject_term" in e for e in audit["errors"]))

    def test_word_shortfall_is_caught_and_adequate_passes(self):
        short = [{"section_id": "background", "content": "太短。" * 10}]
        audit = audit_constraint_alignment(CONSTRAINTS, outline_for(("background", 1560)), short, today="2026-08-23")
        self.assertTrue(any("words_" in e for e in audit["errors"]))
        adequate = [{"section_id": "background", "content": "足够长的研究背景内容。" * 120}]
        audit2 = audit_constraint_alignment(CONSTRAINTS, outline_for(("background", 1560)), adequate, today="2026-08-23")
        self.assertFalse(any("background" in e for e in audit2["errors"]))

    def test_clean_flow_is_valid(self):
        sections = [
            {"section_id": "timeline", "content": "研究计划分三阶段于2026年11月前完成。" * 40},
            {"section_id": "background", "content": "基于公开数据的背景论述，逐句展开证据与情境。" * 60},
        ]
        audit = audit_constraint_alignment(
            CONSTRAINTS, outline_for(("timeline", 480), ("background", 1560)), sections, today="2026-08-23",
        )
        self.assertTrue(audit["valid"], audit["errors"])


class RepetitionTests(unittest.TestCase):
    def test_distinct_sections_have_low_rate(self):
        sections = [
            {"section_id": "a", "content": "平台治理研究的第一组独特论述，围绕监管冲击与生态演化展开分析。" * 5},
            {"section_id": "b", "content": "理论框架部分引入不同的构念体系，讨论权力依赖与编排机制的差异。" * 5},
        ]
        metric = cross_section_repetition(sections)
        self.assertFalse(metric["flagged"])

    def test_duplicated_sections_are_flagged(self):
        text = "平台治理研究存在明显分歧，需要进一步识别边界条件与作用机制。" * 5
        sections = [{"section_id": "a", "content": text}, {"section_id": "b", "content": text}]
        metric = cross_section_repetition(sections)
        self.assertTrue(metric["flagged"])


if __name__ == "__main__":
    unittest.main()
