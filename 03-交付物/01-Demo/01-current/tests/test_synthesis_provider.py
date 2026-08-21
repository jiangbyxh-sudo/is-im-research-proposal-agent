import sys
import unittest
from pathlib import Path


KB_PROVIDER_DIR = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3/11_implementation"
sys.path.insert(0, str(KB_PROVIDER_DIR))

from research_synthesis_provider import (  # noqa: E402
    DeepSeekResearchSynthesisProvider,
    SynthesisRequest,
    UnconfiguredResearchSynthesisProvider,
)


class StaticClient:
    def complete(self, system_prompt, user_prompt):
        directions = []
        for index in range(5):
            first = (index * 2) + 1
            ids = [f"P{first:03d}", f"P{first + 1:03d}"]
            evidence = ids + (["P999"] if index == 0 else [])
            gaps = [{
                "gap_type": "empirical",
                "gap_statement": f"方向{index + 1}在跨情境稳健性方面仍是待验证候选。",
                "why_it_matters": "可界定适用边界。",
                "evidence_basis": evidence,
                "alternative_explanations": ["题名无法呈现全文边界"],
                "innovation_candidates": ["开展跨情境比较"],
                "confidence": "emerging",
            }]
            if index == 0:
                gaps.append({
                    "gap_type": "theoretical",
                    "gap_statement": "未知DOI 10.9999/fabricated 暗示理论空白。",
                    "why_it_matters": "invalid",
                    "evidence_basis": ids,
                })
            directions.append({
                "name_zh": f"方向{index + 1}", "name_en": f"Direction {index + 1}",
                "description": "互斥主题", "paper_ids": ids, "gaps": gaps,
            })
        return {"subdirections": directions, "limitations": ["仅有元数据"]}, {"model": "test-model"}


class SynthesisProviderTests(unittest.TestCase):
    def setUp(self):
        self.papers = tuple({
            "title": f"Verified paper {index}", "authors": ["A"], "year": 2026,
            "journal": "MIS Quarterly", "doi": f"10.1000/{index}",
            "citation_count": index, "journal_ranking": ["UTD24"],
        } for index in range(1, 13))

    def test_five_directions_are_counted_and_references_are_validated(self):
        provider = DeepSeekResearchSynthesisProvider(StaticClient())
        result = provider.synthesize(SynthesisRequest(
            research_direction="AI-enabled information systems",
            fine_grained_question=None,
            derived_path="top_five_subdirections",
            papers=self.papers,
        ))
        self.assertEqual(result.status, "SYNTHESIS_COMPLETE")
        self.assertEqual(len(result.top_subdirections), 5)
        self.assertTrue(all(item["paper_count"] == 2 for item in result.top_subdirections))
        self.assertEqual(len(result.gap_candidates), 5)
        self.assertGreaterEqual(result.audit["invalid_reference_count"], 2)
        self.assertTrue(all(gap["verification_status"].endswith("pending_fulltext") for gap in result.gap_candidates))
        known = {f"P{index:03d}" for index in range(1, 13)}
        self.assertTrue(all(set(gap["evidence_basis"]).issubset(known) for gap in result.gap_candidates))

    def test_unconfigured_provider_never_generates_gaps(self):
        result = UnconfiguredResearchSynthesisProvider().synthesize(SynthesisRequest(
            research_direction="AI", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers,
        ))
        self.assertEqual(result.status, "SYNTHESIS_NOT_CONFIGURED")
        self.assertEqual(result.gap_candidates, [])


if __name__ == "__main__":
    unittest.main()
