import sys
import unittest
from pathlib import Path


KB_ROOT = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3"
PROVIDER_PATH = KB_ROOT / "11_implementation/proposal_generation_provider.py"
sys.path.insert(0, str(PROVIDER_PATH.parent))
import proposal_generation_provider as provider_module


class FakeClient:
    def complete(self, system_prompt, user_prompt):
        sections = [
            {
                "section_id": section_id,
                "content": f"{title}内容",
                "paper_ids": ["P001"],
                "assumptions": ["待全文复核"],
            }
            for section_id, title in provider_module.SECTION_SPECS
        ]
        guidance = [
            {
                "stage_id": stage_id,
                "purpose": f"{title}目的",
                "recommended_moves": ["动作1"],
                "evidence_required": ["证据1"],
                "common_failures": ["失败1"],
                "self_check": ["问题1"],
            }
            for stage_id, title in provider_module.GUIDANCE_STAGES
        ]
        return {
            "working_title": "实验研究暂定题目",
            "research_question": "随机化干预如何影响结果？",
            "proposal_sections": sections,
            "writing_guidance": guidance,
            "limitations": ["测试限制"],
        }, {"model": "fake"}


class ProposalProviderTests(unittest.TestCase):
    def test_generates_all_proposal_sections_and_guidance_from_local_paradigm(self):
        engine = provider_module.DeepSeekProposalGenerationProvider(FakeClient(), KB_ROOT)
        result = engine.generate(provider_module.ProposalRequest(
            research_direction="AI-enabled information systems",
            fine_grained_question=None,
            selected_gap={
                "gap_id": "g1",
                "gap_statement": "缺少随机实验验证",
                "why_it_matters": "需要因果证据",
            },
            selected_innovation_id="g1_innovation_1",
            selected_innovation="通过随机实验检验界面干预",
            papers=({"title": "Paper 1", "journal": "MIS Quarterly", "doi": "10.1/test"},),
        ))
        self.assertEqual(result.status, "PROPOSAL_DRAFT_READY")
        self.assertEqual(len(result.proposal["sections"]), len(provider_module.SECTION_SPECS))
        self.assertEqual(len(result.writing_guidance["stages"]), len(provider_module.GUIDANCE_STAGES))
        self.assertEqual(result.writing_guidance["paradigm_id"], "experiment")
        self.assertTrue(result.proposal_context["gate_passed"])

    def test_unconfigured_provider_stops_without_placeholder_report(self):
        result = provider_module.UnconfiguredProposalGenerationProvider().generate(
            provider_module.ProposalRequest(
                research_direction="AI", fine_grained_question=None,
                selected_gap={"gap_id": "g1"}, selected_innovation_id="i1",
                selected_innovation="innovation", papers=({"title": "Paper"},),
            )
        )
        self.assertEqual(result.status, "PROPOSAL_NOT_CONFIGURED")
        self.assertEqual(result.proposal, {})


if __name__ == "__main__":
    unittest.main()
