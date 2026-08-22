from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from claim_store import ClaimStore  # noqa: E402
from evidence_matrix import build_evidence_matrix, evidence_indexes  # noqa: E402
from question_evidence_retrieval import (  # noqa: E402
    ControlledQuestionEvidenceProvider,
    PaperQA2SubprocessBackend,
    QuestionEvidenceRequest,
    UnconfiguredQuestionEvidenceProvider,
)
from research_skills.adapters import build_default_registry  # noqa: E402
from research_skills.contracts import ResearchSkillContext, SkillRunStatus  # noqa: E402


def fixture_matrix():
    return build_evidence_matrix([
        {
            "paper_id": "P1",
            "abstract": (
                "Explanations improve calibrated trust when users understand system limits. "
                "A factorial experiment compared explanation formats across expertise levels."
            ),
        },
        {
            "paper_id": "P2",
            "abstract": (
                "Interface colors affect perceived usability in routine tasks. "
                "Prior familiarity offers an alternative explanation for trust calibration."
            ),
        },
    ])


class FirstSpanBackend:
    def __init__(self, result_ids=None):
        self.result_ids = result_ids
        self.calls = 0

    def retrieve(self, query, spans, top_k):
        self.calls += 1
        self.query = query
        self.spans = spans
        results = self.result_ids if self.result_ids is not None else [item["span_id"] for item in spans[:top_k]]
        return {"status": "OK", "backend_version": "2026.8.12", "results": results}


class QuestionEvidenceRetrievalTests(unittest.TestCase):
    def test_only_direct_allowlisted_paper_spans_reach_backend(self):
        matrix = fixture_matrix()
        backend = FirstSpanBackend()
        result = ControlledQuestionEvidenceProvider(backend).retrieve(QuestionEvidenceRequest(
            query="When do explanations improve calibrated trust?",
            evidence_matrix=matrix,
            eligible_direct_paper_ids=("P1",),
            top_k=2,
        ))
        self.assertEqual("QUESTION_EVIDENCE_READY", result.status)
        self.assertEqual({"P1"}, {item["paper_id"] for item in backend.spans})
        self.assertTrue(all(item["paper_id"] == "P1" for item in result.candidates))
        self.assertTrue(result.audit["p1_direct_allowlist_enforced"])

    def test_unknown_or_nonallowlisted_backend_span_is_rejected(self):
        matrix = fixture_matrix()
        _, spans = evidence_indexes(matrix)
        p2_span = next(item for item in spans.values() if item["paper_id"] == "P2")
        backend = FirstSpanBackend([p2_span["span_id"]])
        result = ControlledQuestionEvidenceProvider(backend).retrieve(QuestionEvidenceRequest(
            query="calibrated trust",
            evidence_matrix=matrix,
            eligible_direct_paper_ids=("P1",),
        ))
        self.assertEqual("PAPERQA2_RETRIEVAL_FAILED", result.status)
        self.assertEqual([], result.candidates)
        self.assertIn("paperqa2_result_rejected", result.limitations)

    def test_title_only_material_cannot_enter_retrieval_corpus(self):
        matrix = build_evidence_matrix([{"paper_id": "P1", "title": "Only a title"}])
        backend = FirstSpanBackend()
        result = ControlledQuestionEvidenceProvider(backend).retrieve(QuestionEvidenceRequest(
            query="What does the paper show?",
            evidence_matrix=matrix,
            eligible_direct_paper_ids=("P1",),
        ))
        self.assertEqual("QUESTION_EVIDENCE_BLOCKED", result.status)
        self.assertEqual(0, backend.calls)

    def test_direct_allowlist_is_mandatory(self):
        backend = FirstSpanBackend()
        result = ControlledQuestionEvidenceProvider(backend).retrieve(QuestionEvidenceRequest(
            query="calibrated trust",
            evidence_matrix=fixture_matrix(),
            eligible_direct_paper_ids=(),
        ))
        self.assertEqual("QUESTION_EVIDENCE_BLOCKED", result.status)
        self.assertIn("eligible_direct_paper_ids_required", result.limitations)
        self.assertEqual(0, backend.calls)

    def test_output_is_candidate_only_and_claim_store_can_bind_it(self):
        matrix = fixture_matrix()
        result = ControlledQuestionEvidenceProvider(FirstSpanBackend()).retrieve(QuestionEvidenceRequest(
            query="calibrated trust",
            evidence_matrix=matrix,
            eligible_direct_paper_ids=("P1",),
            top_k=1,
        ))
        candidate = result.candidates[0]
        serialized = json.dumps(result.__dict__, ensure_ascii=False)
        self.assertEqual("EVIDENCE_CANDIDATE_ONLY", candidate["candidate_status"])
        self.assertTrue(candidate["requires_claim_store_binding"])
        self.assertNotIn('"answer"', serialized)
        self.assertNotIn('"research_gap"', serialized)
        self.assertNotIn('"claim_id"', serialized)
        store = ClaimStore(matrix)
        store.add_formal_claim(
            candidate["evidence_span"]["text"],
            [{"paper_id": candidate["paper_id"], "evidence_span_id": candidate["evidence_span_id"]}],
        )
        self.assertTrue(store.audit()["valid"])

    def test_empty_backend_result_is_partial_not_fabricated(self):
        result = ControlledQuestionEvidenceProvider(FirstSpanBackend([])).retrieve(QuestionEvidenceRequest(
            query="unknown phenomenon",
            evidence_matrix=fixture_matrix(),
            eligible_direct_paper_ids=("P1",),
        ))
        self.assertEqual("QUESTION_EVIDENCE_EMPTY", result.status)
        self.assertEqual([], result.candidates)

    def test_unpinned_backend_version_is_rejected(self):
        backend = FirstSpanBackend()
        backend.retrieve = lambda query, spans, top_k: {
            "status": "OK", "backend_version": "unexpected", "results": [],
        }
        result = ControlledQuestionEvidenceProvider(backend).retrieve(QuestionEvidenceRequest(
            query="calibrated trust",
            evidence_matrix=fixture_matrix(),
            eligible_direct_paper_ids=("P1",),
        ))
        self.assertEqual("PAPERQA2_RETRIEVAL_FAILED", result.status)
        self.assertIn("paperqa2_version_mismatch", result.limitations)

    def test_unconfigured_provider_blocks_without_answer(self):
        result = UnconfiguredQuestionEvidenceProvider().retrieve(QuestionEvidenceRequest(
            query="calibrated trust", evidence_matrix=fixture_matrix(), eligible_direct_paper_ids=("P1",),
        ))
        self.assertEqual("PAPERQA2_NOT_CONFIGURED", result.status)
        self.assertEqual([], result.candidates)
        self.assertFalse(result.audit["claim_generation_allowed"])

    def test_subprocess_environment_drops_api_keys_and_credentials(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "fixture-secret",
            "SEMANTIC_SCHOLAR_API_KEY": "fixture-secret",
            "CROSSREF_API_KEY": "fixture-secret",
        }):
            environment = PaperQA2SubprocessBackend.sanitized_environment()
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("SEMANTIC_SCHOLAR_API_KEY", environment)
        self.assertNotIn("CROSSREF_API_KEY", environment)

    def test_worker_source_excludes_agent_answer_and_external_search_paths(self):
        source = (
            IMPLEMENTATION / "research_skills/sidecars/paperqa2/paperqa2_retrieval_worker.py"
        ).read_text(encoding="utf-8")
        self.assertIn('Settings(embedding="sparse")', source)
        for forbidden in ("aget_evidence", ".aquery", "agent_query", "SearchPapers", "GenerateAnswer"):
            self.assertNotIn(forbidden, source)

    def test_third_party_lock_records_validated_retrieval_only_scope(self):
        lock = (
            IMPLEMENTATION / "research_skills/third_party_skills.lock.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("package: paper-qa==2026.8.12", lock)
        self.assertIn("integration_mode: isolated_subprocess_span_retrieval", lock)
        for forbidden in (
            "external_paper_search", "llm_or_agent", "answer_generation",
            "claim_generation", "claim_store_bypass",
        ):
            self.assertIn(f"      - {forbidden}", lock)

    def test_registry_maps_ready_and_uses_deterministic_cache(self):
        backend = FirstSpanBackend()
        registry = build_default_registry(
            evidence_retrieval_provider=ControlledQuestionEvidenceProvider(backend),
        )
        payload = {
            "query": "calibrated trust",
            "evidence_matrix": fixture_matrix(),
            "eligible_direct_paper_ids": ["P1"],
            "top_k": 1,
        }
        first = registry.run(
            "p3.question_evidence_retrieval", payload,
            ResearchSkillContext(stage="P3", cache_namespace="question-evidence-test"),
        )
        second = registry.run(
            "p3.question_evidence_retrieval", payload,
            ResearchSkillContext(stage="P3", cache_namespace="question-evidence-test"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, first.status)
        self.assertEqual("QUESTION_EVIDENCE_READY", first.upstream_status)
        self.assertEqual(1, backend.calls)
        self.assertTrue(second.audit["cache_hit"])
        self.assertFalse(first.audit["formal_relevance_decision_allowed"])
        self.assertFalse(first.audit["claim_store_bypass_allowed"])

    def test_real_paperqa2_worker_when_isolated_runtime_exists(self):
        python_path = Path(os.environ.get("LOCALAPPDATA", "")) / (
            "is-im-paperqa2/v2026.08.12/.venv/Scripts/python.exe"
        )
        if not python_path.is_file():
            self.skipTest("isolated PaperQA2 runtime is not installed")
        worker = IMPLEMENTATION / "research_skills/sidecars/paperqa2/paperqa2_retrieval_worker.py"
        provider = ControlledQuestionEvidenceProvider(PaperQA2SubprocessBackend(python_path, worker))
        result = provider.retrieve(QuestionEvidenceRequest(
            query="explanations trust users system limits",
            evidence_matrix=fixture_matrix(),
            eligible_direct_paper_ids=("P1",),
            top_k=1,
        ))
        self.assertEqual("QUESTION_EVIDENCE_READY", result.status)
        self.assertEqual("2026.8.12", result.audit["backend_version"])
        self.assertEqual("P1", result.candidates[0]["paper_id"])


if __name__ == "__main__":
    unittest.main()
