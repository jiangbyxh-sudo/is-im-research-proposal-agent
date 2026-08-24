from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from evidence_matrix import build_evidence_matrix, evidence_indexes  # noqa: E402
from gap_falsification import (  # noqa: E402
    EvidenceBoundGapFalsificationProvider,
    GapFalsificationRequest,
    build_gap_falsification_query_plan,
)
from research_skills.adapters import build_default_registry  # noqa: E402
from research_skills.contracts import ResearchSkillContext, SkillRunStatus  # noqa: E402


class GapFalsificationTests(unittest.TestCase):
    def setUp(self):
        self.gap = {
            "gap_id": "gap_test",
            "gap_statement": "The boundary conditions of explanation effects on calibrated trust remain unresolved.",
            "research_question": "When do explanations improve calibrated trust in high-risk decisions?",
        }
        self.profile = {
            "facets": {"core_phenomena": ["explainable AI trust"]},
        }
        self.matrix = build_evidence_matrix([
            {
                "paper_id": "P1", "title": "Existing solution", "evidence_level": "abstract",
                "abstract": "A preregistered experiment already identifies the boundary conditions and validates a calibrated explanation method.",
            },
            {
                "paper_id": "P2", "title": "Boundary evidence", "evidence_level": "fulltext",
                "fulltext": "The explanation effect disappears for expert users when decision stakes are high. Task familiarity offers an alternative account.",
            },
            {"paper_id": "P3", "title": "Title-only alleged solution"},
        ])
        papers, _ = evidence_indexes(self.matrix)
        self.p1_span = papers["P1"]["span_ids"][0]
        self.p2_span = papers["P2"]["span_ids"][0]

    def finding(self, role: str, paper_id: str, span_id: str, **extra) -> dict:
        return {
            "finding_id": f"F_{role}",
            "role": role,
            "statement": "This evidence directly bears on the claimed unresolved boundary condition.",
            "paper_id": paper_id,
            "evidence_span_id": span_id,
            "relevance_tier": "direct",
            "citation_verdict": "VERIFIED",
            **extra,
        }

    def evaluate(self, findings, search_status="COMPLETE"):
        return EvidenceBoundGapFalsificationProvider().evaluate(GapFalsificationRequest(
            gap=self.gap,
            findings=tuple(findings),
            evidence_matrix=self.matrix,
            search_status=search_status,
        ))

    def test_plan_has_four_falsification_roles_and_is_deterministic(self):
        first = build_gap_falsification_query_plan(self.gap, self.profile)
        second = build_gap_falsification_query_plan(self.gap, self.profile)
        self.assertEqual(4, len(first["queries"]))
        self.assertEqual(
            {"direct_solution", "contradictory_finding", "alternative_explanation", "boundary_condition"},
            {item["role"] for item in first["queries"]},
        )
        self.assertEqual(first["plan_hash"], second["plan_hash"])
        self.assertTrue(all(item["selection_requirement"] == "existing_P1_direct_only" for item in first["queries"]))
        self.assertFalse(first["title_level_evidence_allowed"])
        self.assertFalse(first["changes_p1_thresholds"])

    def test_direct_solution_falsifies_gap_with_bound_claim(self):
        original = deepcopy(self.gap)
        result = self.evaluate([self.finding("direct_solution", "P1", self.p1_span)])
        self.assertEqual("GAP_FALSIFIED", result.status)
        self.assertEqual("DOWNGRADE_FORMAL_GAP", result.recommendation)
        self.assertEqual(original, self.gap)
        self.assertFalse(result.audit["gap_mutated_automatically"])
        self.assertTrue(result.audit["claim_store_valid"])
        claim = result.falsification_claim_store["claims"][0]
        self.assertEqual("P1", claim["bindings"][0]["paper_id"])
        self.assertEqual(self.p1_span, claim["bindings"][0]["evidence_span_id"])

    def test_adjacent_finding_cannot_falsify_gap(self):
        finding = self.finding("direct_solution", "P1", self.p1_span, relevance_tier="adjacent")
        result = self.evaluate([finding])
        self.assertEqual("GAP_SURVIVES_FALSIFICATION", result.status)
        self.assertEqual([], result.accepted_findings)
        self.assertIn("requires_existing_p1_direct", result.rejected_findings[0]["reason"])

    def test_title_only_paper_cannot_enter_falsification_claim(self):
        finding = self.finding("direct_solution", "P3", "missing_title_span")
        result = self.evaluate([finding])
        self.assertEqual([], result.accepted_findings)
        self.assertIn("evidence_span_not_found", result.rejected_findings[0]["reason"])
        self.assertFalse(result.audit["title_level_evidence_allowed"])

    def test_retracted_or_mismatched_citation_is_rejected(self):
        for verdict in ("RETRACTED", "MISMATCH", "UNRESOLVED"):
            with self.subTest(verdict=verdict):
                result = self.evaluate([
                    self.finding("direct_solution", "P1", self.p1_span, citation_verdict=verdict)
                ])
                self.assertEqual([], result.accepted_findings)
                self.assertIn(verdict.casefold(), result.rejected_findings[0]["reason"])

    def test_boundary_evidence_narrows_instead_of_destroying_gap(self):
        result = self.evaluate([self.finding("boundary_condition", "P2", self.p2_span)])
        self.assertEqual("GAP_NARROWED", result.status)
        self.assertEqual("REVISE_GAP_SCOPE", result.recommendation)

    def test_partial_search_cannot_confirm_survival(self):
        result = self.evaluate([], search_status="PARTIAL")
        self.assertEqual("GAP_FALSIFICATION_PARTIAL", result.status)
        self.assertEqual("RETRY_FAILED_SEARCH_LEGS", result.recommendation)
        self.assertIn("partial_search_cannot_confirm_gap_survival", result.limitations)

    def test_complete_search_without_finding_keeps_absence_caveat(self):
        result = self.evaluate([])
        self.assertEqual("GAP_SURVIVES_FALSIFICATION", result.status)
        self.assertIn("absence_of_falsifying_evidence_is_not_proof_of_novelty", result.limitations)

    def test_registry_exposes_plan_and_evaluation(self):
        registry = build_default_registry()
        ids = {item["skill_id"] for item in registry.descriptors()}
        self.assertIn("p3.gap_falsification_plan", ids)
        self.assertIn("p3.gap_falsification_evaluation", ids)
        result = registry.run(
            "p3.gap_falsification_evaluation",
            {
                "gap": self.gap,
                "findings": [self.finding("direct_solution", "P1", self.p1_span)],
                "evidence_matrix": self.matrix,
                "search_status": "COMPLETE",
            },
            ResearchSkillContext(stage="P3"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, result.status)
        self.assertEqual("GAP_FALSIFIED", result.upstream_status)
        self.assertFalse(result.audit["formal_gap_minimum_changed"])


if __name__ == "__main__":
    unittest.main()
