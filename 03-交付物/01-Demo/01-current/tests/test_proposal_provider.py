import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


KB_ROOT = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3"
PROVIDER_PATH = KB_ROOT / "11_implementation/proposal_generation_provider.py"
sys.path.insert(0, str(PROVIDER_PATH.parent))
import proposal_generation_provider as provider_module
from evidence_matrix import build_evidence_matrix
from research_gap_provider import EvidenceBoundResearchGapProvider, ResearchGapRequest


class SectionClient:
    def __init__(self, invalid_claim=False):
        self.calls = []
        self.invalid_claim = invalid_claim

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        payload = json.loads(user_prompt)
        blueprint = payload["research_design_blueprint"]
        section_id = payload["section_spec"]["section_id"]
        claim_ids = ["claim_unknown"] if self.invalid_claim else payload["allowed_claim_ids"]
        return {
            "section": {
                "section_id": section_id,
                "content": f"{section_id}仅依据Claim Store形成的受控内容。",
                "claim_ids": claim_ids,
                "assumptions": ["仍需人工审阅"],
                "blueprint_refs": {
                    "blueprint_id": blueprint["blueprint_id"],
                    "research_question": blueprint["research_question"],
                    "design": blueprint["design"],
                },
            }
        }, {"model": "fake-section-model"}


def controlled_context():
    papers = (
        {
            "paper_id": "P001", "title": "Explanation and calibrated trust", "evidence_level": "abstract",
            "abstract": "Transparent explanations improve calibrated user trust under some organizational conditions. Boundary effects remain across different task risks.",
        },
        {
            "paper_id": "P002", "title": "Trust boundary conditions", "evidence_level": "fulltext",
            "fulltext": "A field study found that explanation effects vary with decision stakes and prior expertise. The observed association weakens after accounting for task familiarity.",
        },
    )
    matrix = build_evidence_matrix(papers)
    by_paper = {item["paper_id"]: item for item in matrix["papers"]}
    candidate = {
        "gap_statement": "Explanation effects on calibrated trust remain insufficiently bounded across task-risk contexts.",
        "evidence_span_ids": [by_paper["P001"]["span_ids"][0], by_paper["P002"]["span_ids"][0]],
        "counterevidence": [{
            "statement": "Task familiarity may explain part of the relationship.",
            "evidence_span_ids": [by_paper["P002"]["span_ids"][1]],
        }],
        "alternative_explanations": ["Prior expertise may drive the effect."],
        "research_question": "How does task risk condition the effect of explanations on calibrated AI trust?",
        "feasible_method": {
            "design": "Preregistered online factorial experiment",
            "data": "Adult technology users recruited from a panel",
            "analysis": "Interaction model with robustness checks",
            "unit_of_analysis": "individual user",
            "context": "AI-assisted decisions",
        },
    }
    gaps = EvidenceBoundResearchGapProvider().formalize(ResearchGapRequest("cluster_001", (candidate,), matrix))
    return papers, gaps.formal_gaps[0], gaps.claim_store


class ProposalProviderTests(unittest.TestCase):
    def test_blueprint_must_be_confirmed_before_section_generation(self):
        papers, gap, claim_store = controlled_context()
        client = SectionClient()
        engine = provider_module.DeepSeekProposalGenerationProvider(client, KB_ROOT)
        request = provider_module.ProposalRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            selected_gap=gap, selected_innovation_id="innovation_1",
            selected_innovation="通过随机实验检验界面干预", papers=papers, claim_store=claim_store,
        )
        first = engine.generate(request)
        self.assertEqual("BLUEPRINT_CONFIRMATION_REQUIRED", first.status)
        self.assertEqual(0, len(client.calls))
        blueprint = first.proposal["research_design_blueprint"]
        second = engine.generate(replace(request, research_design_blueprint=blueprint, blueprint_confirmed=True))
        self.assertEqual("READY_FOR_HUMAN_REVIEW", second.status)
        self.assertEqual(len(provider_module.SECTION_SPECS), len(second.proposal["sections"]))
        self.assertEqual(len(provider_module.SECTION_SPECS), len(client.calls))
        self.assertTrue(second.audit["claim_audit"]["valid"])
        self.assertTrue(second.audit["citation_audit"]["valid"])
        self.assertTrue(second.audit["cross_section_consistency_matrix"]["valid"])
        self.assertTrue(second.proposal_context["gate_passed"])
        self.assertTrue(all('"papers"' not in prompt for _, prompt in client.calls))

    def test_title_level_evidence_dominance_can_only_return_sketch(self):
        papers, gap, claim_store = controlled_context()
        dominated = (
            {"paper_id": "T1", "title": "Title one", "evidence_level": "title_only"},
            {"paper_id": "T2", "title": "Title two", "evidence_level": "title_only"},
            papers[0],
        )
        client = SectionClient()
        result = provider_module.DeepSeekProposalGenerationProvider(client, KB_ROOT).generate(
            provider_module.ProposalRequest(
                research_direction="AI", fine_grained_question=None, selected_gap=gap,
                selected_innovation_id="i1", selected_innovation="innovation", papers=dominated,
                claim_store=claim_store, blueprint_confirmed=True,
            )
        )
        self.assertEqual("RESEARCH_SKETCH_ONLY", result.status)
        self.assertEqual(0, len(client.calls))

    def test_unknown_claim_prevents_ready_status(self):
        papers, gap, claim_store = controlled_context()
        client = SectionClient(invalid_claim=True)
        engine = provider_module.DeepSeekProposalGenerationProvider(client, KB_ROOT)
        request = provider_module.ProposalRequest(
            research_direction="AI", fine_grained_question=None, selected_gap=gap,
            selected_innovation_id="i1", selected_innovation="innovation", papers=papers, claim_store=claim_store,
        )
        blueprint = engine.generate(request).proposal["research_design_blueprint"]
        result = engine.generate(replace(request, research_design_blueprint=blueprint, blueprint_confirmed=True))
        self.assertEqual("PROPOSAL_CONTROLLED_PARTIAL", result.status)
        self.assertFalse(result.proposal_context["gate_passed"])

    def test_unconfigured_provider_stops_without_placeholder_report(self):
        result = provider_module.UnconfiguredProposalGenerationProvider().generate(
            provider_module.ProposalRequest(
                research_direction="AI", fine_grained_question=None, selected_gap={"gap_id": "g1"},
                selected_innovation_id="i1", selected_innovation="innovation", papers=({"title": "Paper"},),
            )
        )
        self.assertEqual("PROPOSAL_NOT_CONFIGURED", result.status)
        self.assertEqual({}, result.proposal)


if __name__ == "__main__":
    unittest.main()
