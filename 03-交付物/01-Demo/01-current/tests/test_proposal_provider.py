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
                    "outline_id": payload["proposal_outline"]["outline_id"],
                    "constraint_hash": blueprint["constraint_hash"],
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


def confirmed_constraints():
    return {
        "degree_level": "硕士",
        "institution_template": "无指定模板",
        "output_language": "中文",
        "target_word_count": 12000,
        "deadline": "2026-12-31",
        "data_access": "可招募在线实验参与者，不访问敏感组织数据",
        "method_constraints": "采用可预注册的在线实验",
        "research_context": "AI辅助决策",
        "ethics_privacy": "知情同意、匿名化并在招募前完成伦理审查",
        "tool_capabilities": "Python、R和在线实验平台",
    }


class ProposalProviderTests(unittest.TestCase):
    def test_constraints_and_plan_must_be_confirmed_before_section_generation(self):
        papers, gap, claim_store = controlled_context()
        client = SectionClient()
        engine = provider_module.DeepSeekProposalGenerationProvider(client, KB_ROOT)
        request = provider_module.ProposalRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            selected_gap=gap, selected_innovation_id="innovation_1",
            selected_innovation="通过随机实验检验界面干预", papers=papers, claim_store=claim_store,
        )
        first = engine.generate(request)
        self.assertEqual("PROPOSAL_NEEDS_USER_INPUT", first.status)
        self.assertEqual("degree_level", first.proposal_context["missing_field"])
        self.assertEqual(0, len(client.calls))
        second = engine.generate(replace(request, user_constraints=confirmed_constraints()))
        self.assertEqual("USER_CONSTRAINT_CONFIRMATION_REQUIRED", second.status)
        plan = engine.generate(replace(
            request, user_constraints=confirmed_constraints(), constraints_confirmed=True,
        ))
        self.assertEqual("PROPOSAL_PLAN_CONFIRMATION_REQUIRED", plan.status)
        self.assertTrue(plan.proposal["execution_task_cards"]["audit"]["valid"])
        self.assertEqual(0, len(client.calls))
        final = engine.generate(replace(
            request,
            user_constraints=confirmed_constraints(),
            constraints_confirmed=True,
            research_design_blueprint=plan.proposal["research_design_blueprint"],
            blueprint_confirmed=True,
            proposal_outline=plan.proposal["proposal_outline"],
            outline_confirmed=True,
        ))
        self.assertEqual("READY_FOR_HUMAN_REVIEW", final.status)
        self.assertEqual(len(provider_module.SECTION_SPECS), len(final.proposal["sections"]))
        self.assertEqual(len(provider_module.SECTION_SPECS), len(client.calls))
        self.assertTrue(final.audit["claim_audit"]["valid"])
        self.assertTrue(final.audit["citation_audit"]["valid"])
        self.assertTrue(final.audit["cross_section_consistency_matrix"]["valid"])
        self.assertTrue(final.audit["task_card_audit"]["valid"])
        self.assertTrue(final.proposal_context["gate_passed"])
        self.assertTrue(all(section["task_card_id"] for section in final.proposal["sections"]))
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
                claim_store=claim_store, user_constraints=confirmed_constraints(),
                constraints_confirmed=True, blueprint_confirmed=True, outline_confirmed=True,
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
            selected_innovation_id="i1", selected_innovation="innovation", papers=papers,
            claim_store=claim_store, user_constraints=confirmed_constraints(), constraints_confirmed=True,
        )
        plan = engine.generate(request).proposal
        result = engine.generate(replace(
            request,
            research_design_blueprint=plan["research_design_blueprint"],
            blueprint_confirmed=True,
            proposal_outline=plan["proposal_outline"],
            outline_confirmed=True,
        ))
        self.assertEqual("PROPOSAL_CONTROLLED_PARTIAL", result.status)
        self.assertFalse(result.proposal_context["gate_passed"])

    def test_tampered_outline_is_rejected_without_model_call(self):
        papers, gap, claim_store = controlled_context()
        client = SectionClient()
        engine = provider_module.DeepSeekProposalGenerationProvider(client, KB_ROOT)
        request = provider_module.ProposalRequest(
            research_direction="AI", fine_grained_question=None, selected_gap=gap,
            selected_innovation_id="i1", selected_innovation="innovation", papers=papers,
            claim_store=claim_store, user_constraints=confirmed_constraints(), constraints_confirmed=True,
        )
        plan = engine.generate(request).proposal
        tampered = json.loads(json.dumps(plan["proposal_outline"], ensure_ascii=False))
        tampered["sections"][0]["title"] = "绕过确认的标题"
        result = engine.generate(replace(
            request,
            research_design_blueprint=plan["research_design_blueprint"], blueprint_confirmed=True,
            proposal_outline=tampered, outline_confirmed=True,
        ))
        self.assertEqual("PROPOSAL_PLAN_INVALID", result.status)
        self.assertEqual(0, len(client.calls))

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
