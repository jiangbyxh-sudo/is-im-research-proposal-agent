import json
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


class StaticNamingClient:
    """Answers athlete A/B prompts and the blind judge prompt."""

    def __init__(self):
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        clusters = json.loads(user_prompt)["clusters"]
        if "命名裁判" in system_prompt:
            return {
                "selections": [
                    {"cluster_id": cluster["cluster_id"], "winner": "candidate_1", "reason": "更贴近簇内容"}
                    for cluster in clusters
                ]
            }, {"model": "test-judge"}
        athlete = "B" if "选手B" in system_prompt else "A"
        return {
            "names": [
                {
                    "cluster_id": cluster["cluster_id"],
                    "name_zh": f"选手{athlete}方向{index}",
                    "name_en": f"Athlete {athlete} Direction {index}",
                    "description": "固定聚类的边界描述",
                }
                for index, cluster in enumerate(clusters, start=1)
            ]
        }, {"model": "test-model"}


class FailingNamingClient:
    def complete(self, system_prompt, user_prompt):
        raise RuntimeError("naming model unavailable")


class SynthesisProviderTests(unittest.TestCase):
    def setUp(self):
        topics = ["trust", "governance", "adoption", "collaboration", "decision"]
        self.papers = tuple({
            "paper_id": f"P{index:03d}",
            "title": f"{topics[(index - 1) % 5]} in AI-enabled information systems {index}",
            "abstract": f"{topics[(index - 1) % 5]} evidence in organizations and digital work",
            "authors": ["A"], "year": 2026, "journal": "MIS Quarterly", "doi": f"10.1000/{index}",
            "topics": [{"name": topics[(index - 1) % 5]}], "keywords": [{"name": "AI organization"}],
            "relevance_tier": "direct",
        } for index in range(1, 31))

    def test_five_fixed_directions_are_named_without_gap_generation(self):
        class StubGapProvider:
            def propose(self, request):
                return [], {"provider": "stub"}

        client = StaticNamingClient()
        provider = DeepSeekResearchSynthesisProvider(client, gap_candidate_provider=StubGapProvider())
        result = provider.synthesize(SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers, p1_precision_gate_passed=True,
        ))
        self.assertEqual("SYNTHESIS_COMPLETE", result.status)
        self.assertEqual(5, len(result.top_subdirections))
        self.assertTrue(all(item["paper_count"] >= 3 for item in result.top_subdirections))
        self.assertEqual([], result.gap_candidates)
        self.assertEqual("p3-athlete-judge-gap-candidates-1.0.0", result.audit["gap_generation_pipeline"])
        self.assertEqual("athlete_judge_arena", result.audit["naming"]["provider"])
        self.assertTrue(all("heat" in item for item in result.top_subdirections))
        self.assertTrue(result.audit["stability_self_check"]["exact_match"])
        self.assertEqual(3, len(client.calls))
        prompt = " ".join(client.calls[0])
        self.assertNotIn("gap_statement", prompt)
        self.assertNotIn("研究空白", prompt)

    def test_arena_failure_falls_back_to_deterministic_naming(self):
        provider = DeepSeekResearchSynthesisProvider(FailingNamingClient())
        result = provider.synthesize(SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers, p1_precision_gate_passed=True,
        ))
        self.assertEqual("SYNTHESIS_COMPLETE", result.status)
        self.assertEqual(5, len(result.top_subdirections))
        self.assertEqual("deterministic_feature_terms", result.audit["naming"]["provider"])
        self.assertTrue(result.audit["naming_fallback_reason"])

    def test_insufficient_corpus_degrades_honestly_instead_of_five(self):
        provider = DeepSeekResearchSynthesisProvider(StaticNamingClient())
        result = provider.synthesize(SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers[:21], p1_precision_gate_passed=True,
        ))
        self.assertEqual("SYNTHESIS_PARTIAL", result.status)
        self.assertEqual(3, len(result.top_subdirections))
        self.assertEqual(3, result.audit["honest_target"])
        self.assertIn("未硬凑五方向", result.message_to_user)

    def test_p1_gate_blocks_by_default(self):
        result = DeepSeekResearchSynthesisProvider(StaticNamingClient()).synthesize(SynthesisRequest(
            research_direction="AI", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers,
        ))
        self.assertEqual("P2_BLOCKED_BY_P1_PRECISION", result.status)

    def test_unconfigured_provider_never_generates_directions(self):
        result = UnconfiguredResearchSynthesisProvider().synthesize(SynthesisRequest(
            research_direction="AI", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=self.papers, p1_precision_gate_passed=True,
        ))
        self.assertEqual("SYNTHESIS_NOT_CONFIGURED", result.status)
        self.assertEqual([], result.top_subdirections)


if __name__ == "__main__":
    unittest.main()
