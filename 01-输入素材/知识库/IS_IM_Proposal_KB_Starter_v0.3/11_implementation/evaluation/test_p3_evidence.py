from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from claim_store import ClaimStore  # noqa: E402
from evidence_matrix import build_evidence_matrix, evidence_indexes  # noqa: E402
from research_gap_provider import EvidenceBoundResearchGapProvider, ResearchGapRequest  # noqa: E402


class P3EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.matrix = build_evidence_matrix([
            {
                "paper_id": "P001", "title": "AI trust evidence", "evidence_level": "abstract",
                "abstract": "Transparent explanations improve calibrated user trust under some organizational conditions. Boundary effects remain across different task risks.",
            },
            {
                "paper_id": "P002", "title": "AI trust field study", "evidence_level": "fulltext",
                "abstract": "An abstract is available but full text is preferred.",
                "fulltext": "A field study found that explanation effects vary with decision stakes and prior expertise. The observed association weakens after accounting for task familiarity.",
            },
            {"paper_id": "P003", "title": "Title-only claim about universal AI trust"},
        ])
        papers, spans = evidence_indexes(self.matrix)
        self.papers = papers
        self.spans = spans
        self.p1_span = papers["P001"]["span_ids"][0]
        self.p2_span = papers["P002"]["span_ids"][0]
        self.p2_counter = papers["P002"]["span_ids"][1]
        self.valid_candidate = {
            "candidate_id": "G001",
            "gap_statement": "Explanation effects on calibrated AI trust remain insufficiently bounded across task-risk contexts.",
            "evidence_span_ids": [self.p1_span, self.p2_span],
            "counterevidence": [{
                "statement": "Task familiarity may explain part of the observed relationship.",
                "evidence_span_ids": [self.p2_counter],
            }],
            "alternative_explanations": ["Prior expertise rather than explanation design may drive the effect."],
            "research_question": "How does task risk condition the effect of explanations on calibrated AI trust?",
            "feasible_method": {
                "design": "Preregistered online factorial experiment",
                "data": "Adult technology users recruited from a panel",
                "analysis": "Interaction model with robustness and equivalence checks",
                "feasibility_constraints": ["Use validated trust measures", "Pilot task-risk manipulation"],
            },
        }

    def test_matrix_saves_abstract_and_fulltext_sentences_but_not_title_spans(self):
        self.assertEqual("abstract", self.spans[self.p1_span]["evidence_level"])
        self.assertEqual("fulltext", self.spans[self.p2_span]["evidence_level"])
        self.assertFalse(self.papers["P003"]["formal_evidence_eligible"])
        self.assertEqual([], self.papers["P003"]["span_ids"])

    def test_formal_gap_requires_two_distinct_l1_or_l2_papers(self):
        candidate = deepcopy(self.valid_candidate)
        candidate["evidence_span_ids"] = [self.p1_span]
        result = EvidenceBoundResearchGapProvider().formalize(ResearchGapRequest("cluster_001", (candidate,), self.matrix))
        self.assertEqual("RESEARCH_GAPS_INSUFFICIENT_EVIDENCE", result.status)
        self.assertIn("requires_two", result.rejected_candidates[0]["reason"])

    def test_valid_gap_contains_counterevidence_alternative_rq_and_method(self):
        result = EvidenceBoundResearchGapProvider().formalize(
            ResearchGapRequest("cluster_001", (self.valid_candidate,), self.matrix)
        )
        self.assertEqual("RESEARCH_GAPS_READY", result.status)
        gap = result.formal_gaps[0]
        self.assertEqual(["P001", "P002"], gap["supporting_paper_ids"])
        self.assertTrue(gap["counterevidence_claim_ids"])
        self.assertTrue(gap["alternative_explanations"])
        self.assertTrue(gap["research_question"])
        self.assertEqual("Preregistered online factorial experiment", gap["feasible_method"]["design"])
        self.assertTrue(result.audit["claim_store_valid"])

    def test_every_formal_claim_binds_claim_paper_and_evidence_span(self):
        result = EvidenceBoundResearchGapProvider().formalize(
            ResearchGapRequest("cluster_001", (self.valid_candidate,), self.matrix)
        )
        for claim in result.claim_store["claims"]:
            self.assertTrue(claim["claim_id"])
            self.assertTrue(claim["citations"])
            for citation in claim["citations"]:
                self.assertEqual(claim["claim_id"], citation["claim_id"])
                self.assertTrue(citation["paper_id"])
                self.assertIn(citation["evidence_span"]["evidence_level"], {"abstract", "fulltext"})
                self.assertTrue(citation["evidence_span"]["text"])

    def test_missing_required_gap_fields_are_rejected(self):
        mutations = {
            "counterevidence": [],
            "alternative_explanations": [],
            "research_question": "",
            "feasible_method": {},
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                candidate = deepcopy(self.valid_candidate)
                candidate[field] = value
                result = EvidenceBoundResearchGapProvider().formalize(
                    ResearchGapRequest("cluster_001", (candidate,), self.matrix)
                )
                self.assertEqual([], result.formal_gaps)

    def test_claim_store_rejects_unbound_or_cross_paper_span(self):
        store = ClaimStore(self.matrix)
        with self.assertRaisesRegex(ValueError, "requires_evidence_binding"):
            store.add_formal_claim("Unsupported formal assertion", [])
        with self.assertRaisesRegex(ValueError, "paper_mismatch"):
            store.add_formal_claim(
                "Cross-paper binding",
                [{"paper_id": "P001", "evidence_span_id": self.p2_span}],
            )


if __name__ == "__main__":
    unittest.main()
