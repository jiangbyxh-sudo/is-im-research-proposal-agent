from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from evidence_matrix import build_evidence_matrix, evidence_indexes  # noqa: E402
from paper_discovery_provider import DiscoveryResult  # noqa: E402
from proposal_generation_provider import ProposalResult  # noqa: E402
from research_skills.adapters import (  # noqa: E402
    P1DiscoverySkillAdapter,
    P2ClusteringSkillAdapter,
    P3EvidenceGapSkillAdapter,
    P4ControlledProposalSkillAdapter,
)
from research_skills.contracts import (  # noqa: E402
    AdapterExecution,
    ResearchSkillContext,
    ResearchSkillDescriptor,
    SkillRunStatus,
    build_cache_key,
)
from research_skills.registry import ResearchSkillRegistry  # noqa: E402
from research_synthesis_provider import UnconfiguredResearchSynthesisProvider  # noqa: E402


class FakeP1Provider:
    def discover(self, request):
        return DiscoveryResult(
            status="RETRIEVAL_PARTIAL",
            papers=[{"paper_id": "D1", "relevance_tier": "direct"}],
            adjacent_papers=[{"paper_id": "A1", "relevance_tier": "adjacent"}],
            shortages={"en": 9},
            message_to_user="direct论文不足，未使用adjacent补足。",
            coverage_audit={"selected_count": 1},
            provider_statuses=[{"provider": "fake", "status": "ok"}],
            score_config_version="test-score",
        )


class EchoAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p3.echo", version="1.0.0", stage="P3", description="test", deterministic=True,
    )

    def __init__(self):
        self.calls = 0

    def execute(self, payload, context):
        self.calls += 1
        return AdapterExecution(
            result_status=SkillRunStatus.COMPLETE,
            upstream_status="ECHO_COMPLETE",
            output={"payload": dict(payload), "api_key": "fixture-provider-secret"},
        )


class BlueprintRequiredProvider:
    def generate(self, request):
        return ProposalResult(
            status="BLUEPRINT_CONFIRMATION_REQUIRED",
            proposal_context={"research_design_blueprint": {"blueprint_id": "blueprint_test"}},
            limitations=["请先确认研究设计蓝图。"],
        )


class ResearchSkillLayerTests(unittest.TestCase):
    def test_p1_partial_is_preserved_and_adjacent_is_separate(self):
        registry = ResearchSkillRegistry()
        registry.register(P1DiscoverySkillAdapter(FakeP1Provider()))
        result = registry.run(
            "p1.paper_discovery",
            {"selected_direction_id": "topic_x", "research_direction": "X", "chinese_count": 0, "english_count": 10},
            ResearchSkillContext(stage="P1"),
        )
        self.assertEqual(SkillRunStatus.PARTIAL, result.status)
        self.assertEqual("RETRIEVAL_PARTIAL", result.upstream_status)
        self.assertEqual(["D1"], [item["paper_id"] for item in result.output["papers"]])
        self.assertEqual(["A1"], [item["paper_id"] for item in result.output["adjacent_papers"]])
        self.assertTrue(result.audit["formal_papers_only_direct"])

    def test_stage_mismatch_blocks_without_executing(self):
        adapter = EchoAdapter()
        registry = ResearchSkillRegistry()
        registry.register(adapter)
        result = registry.run("p3.echo", {"value": 1}, ResearchSkillContext(stage="P2"))
        self.assertEqual(SkillRunStatus.BLOCKED, result.status)
        self.assertEqual("STAGE_MISMATCH", result.upstream_status)
        self.assertEqual(0, adapter.calls)

    def test_p2_upstream_gate_cannot_be_promoted_to_success(self):
        registry = ResearchSkillRegistry()
        registry.register(P2ClusteringSkillAdapter(UnconfiguredResearchSynthesisProvider()))
        result = registry.run(
            "p2.deterministic_clustering",
            {
                "research_direction": "AI-enabled information systems",
                "derived_path": "popular",
                "papers": [],
                "p1_precision_gate_passed": False,
            },
            ResearchSkillContext(stage="P2"),
        )
        self.assertEqual(SkillRunStatus.BLOCKED, result.status)
        self.assertEqual("P2_BLOCKED_BY_P1_PRECISION", result.upstream_status)
        self.assertFalse(result.audit["paper_membership_owned_by_llm"])

    def test_string_false_cannot_bypass_p2_boolean_gate(self):
        registry = ResearchSkillRegistry()
        registry.register(P2ClusteringSkillAdapter(UnconfiguredResearchSynthesisProvider()))
        result = registry.run(
            "p2.deterministic_clustering",
            {
                "research_direction": "AI-enabled information systems",
                "papers": [],
                "p1_precision_gate_passed": "false",
            },
            ResearchSkillContext(stage="P2"),
        )
        self.assertEqual(SkillRunStatus.BLOCKED, result.status)
        self.assertEqual("INVALID_SKILL_INPUT", result.upstream_status)

    def test_p4_blueprint_confirmation_remains_partial(self):
        registry = ResearchSkillRegistry()
        registry.register(P4ControlledProposalSkillAdapter(BlueprintRequiredProvider()))
        result = registry.run(
            "p4.controlled_proposal",
            {
                "research_direction": "AI-enabled information systems",
                "selected_gap": {},
                "selected_innovation_id": "I1",
                "selected_innovation": "Test",
                "papers": [],
                "blueprint_confirmed": False,
            },
            ResearchSkillContext(stage="P4"),
        )
        self.assertEqual(SkillRunStatus.PARTIAL, result.status)
        self.assertEqual("BLUEPRINT_CONFIRMATION_REQUIRED", result.upstream_status)
        self.assertEqual("READY_FOR_HUMAN_REVIEW", result.audit["ready_state_ceiling"])

    def test_secret_fields_are_rejected_and_not_written_to_trace(self):
        adapter = EchoAdapter()
        registry = ResearchSkillRegistry()
        registry.register(adapter)
        with tempfile.TemporaryDirectory() as directory:
            result = registry.run(
                "p3.echo", {"api_key": "fixture-user-secret", "value": 1},
                ResearchSkillContext(stage="P3", trace_dir=Path(directory)),
            )
            self.assertEqual(SkillRunStatus.BLOCKED, result.status)
            self.assertEqual(0, adapter.calls)
            trace_text = next(Path(directory).glob("*.json")).read_text(encoding="utf-8")
            self.assertNotIn("fixture-user-secret", trace_text)

    def test_provider_output_is_redacted_and_deterministic_cache_is_used(self):
        adapter = EchoAdapter()
        registry = ResearchSkillRegistry()
        registry.register(adapter)
        context = ResearchSkillContext(stage="P3", cache_namespace="test")
        first = registry.run("p3.echo", {"value": 1}, context)
        second = registry.run("p3.echo", {"value": 1}, ResearchSkillContext(stage="P3", cache_namespace="test"))
        self.assertEqual(1, adapter.calls)
        self.assertEqual("[REDACTED]", first.output["api_key"])
        self.assertTrue(second.audit["cache_hit"])
        self.assertEqual(first.cache_key, second.cache_key)

    def test_cache_key_changes_with_skill_version_and_not_run_id(self):
        descriptor = EchoAdapter.descriptor
        payload = {"value": 1}
        first = build_cache_key(descriptor, payload, ResearchSkillContext(stage="P3"))
        second = build_cache_key(descriptor, payload, ResearchSkillContext(stage="P3"))
        changed = build_cache_key(
            ResearchSkillDescriptor(skill_id="p3.echo", version="2.0.0", stage="P3", description="test"),
            payload,
            ResearchSkillContext(stage="P3"),
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_p3_adapter_keeps_two_paper_formal_evidence_gate(self):
        matrix = build_evidence_matrix([
            {"paper_id": "P1", "abstract": "Explanations improve calibrated trust in high-risk tasks."},
            {"paper_id": "P2", "abstract": "Effects vary by expertise. Familiarity may explain the association."},
        ])
        papers, _ = evidence_indexes(matrix)
        candidate = {
            "candidate_id": "G1",
            "gap_statement": "The boundary conditions remain unresolved.",
            "evidence_span_ids": [papers["P1"]["span_ids"][0], papers["P2"]["span_ids"][0]],
            "counterevidence": [{
                "statement": "Familiarity may explain the association.",
                "evidence_span_ids": [papers["P2"]["span_ids"][1]],
            }],
            "alternative_explanations": ["Prior expertise may drive the effect."],
            "research_question": "When do explanations improve calibrated trust?",
            "feasible_method": {"design": "factorial experiment", "data": "panel users", "analysis": "interaction model"},
        }
        registry = ResearchSkillRegistry()
        registry.register(P3EvidenceGapSkillAdapter())
        result = registry.run(
            "p3.evidence_bound_gaps",
            {"cluster_id": "C1", "gap_candidates": [candidate], "evidence_matrix": matrix},
            ResearchSkillContext(stage="P3"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, result.status)
        self.assertEqual(2, len(result.output["formal_gaps"][0]["supporting_paper_ids"]))
        self.assertFalse(result.audit["formal_gap_minimum_changed"])

    def test_lock_file_has_no_unreviewed_enabled_external_project(self):
        text = (IMPLEMENTATION / "research_skills/third_party_skills.lock.yaml").read_text(encoding="utf-8")
        self.assertNotIn("status: enabled", text)
        self.assertEqual(6, text.count("    repository: https://github.com/"))


if __name__ == "__main__":
    unittest.main()
