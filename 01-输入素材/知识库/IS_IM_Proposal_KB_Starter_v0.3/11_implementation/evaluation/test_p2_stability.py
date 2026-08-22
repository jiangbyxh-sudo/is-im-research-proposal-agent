from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from cluster_naming_provider import ClusterNamingRequest, LLMClusterNamingProvider, membership_hash  # noqa: E402
from research_synthesis_provider import DeepSeekResearchSynthesisProvider, SynthesisRequest  # noqa: E402
from stable_subdirection_clustering import (  # noqa: E402
    P2ClusterConfig,
    assess_corpus_sufficiency,
    build_corpus_snapshot,
    deterministic_average_linkage,
)


TOPICS = ["trust", "governance", "adoption", "collaboration", "decision"]


def paper(index: int, with_abstract: bool = True, relevance_tier: str = "direct") -> dict:
    topic = TOPICS[(index - 1) % len(TOPICS)]
    return {
        "paper_id": f"P{index:03d}",
        "title": f"{topic.title()} in AI-enabled information systems {index}",
        "abstract": f"{topic} {topic} evidence in organizations and digital work {index}" if with_abstract else "",
        "year": 2026,
        "journal": "Information Systems Research",
        "doi": f"10.1000/stable.{index}",
        "topics": [{"id": f"T-{topic}", "name": topic}],
        "keywords": [{"name": f"AI {topic}"}],
        "relevance_tier": relevance_tier,
    }


def snapshot(rows: list[dict], p1_passed: bool = True) -> dict:
    return build_corpus_snapshot(
        direction_id="topic_ai_enabled_information_systems",
        papers=rows,
        data_cutoff_date="2026-08-22",
        direction_profile_version="1.1.6-p1-retrieval",
        retrieval_version="p1-query-plan-2.0.0",
        score_version="p1-directness-reranker-2.0.0",
        p1_precision_gate_passed=p1_passed,
        p1_precision_summary={"overall_precision_at_10": 0.80 if p1_passed else 0.7667},
    )


class P2SnapshotTests(unittest.TestCase):
    def test_hash_is_invariant_to_input_order(self):
        rows = [paper(index) for index in range(1, 31)]
        self.assertEqual(snapshot(rows)["corpus_hash"], snapshot(list(reversed(rows)))["corpus_hash"])

    def test_content_change_changes_hash(self):
        rows = [paper(index) for index in range(1, 31)]
        changed = [dict(item) for item in rows]
        changed[0]["title"] = "Changed evidence"
        self.assertNotEqual(snapshot(rows)["corpus_hash"], snapshot(changed)["corpus_hash"])

    def test_p0_27_paper_snapshot_cannot_output_five_directions(self):
        result = assess_corpus_sufficiency(snapshot([paper(index) for index in range(1, 28)]))
        self.assertEqual(result["status"], "SYNTHESIS_INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["can_output_five_directions"])
        self.assertIn("paper_count_below_30", result["reasons"])

    def test_30_papers_and_20_abstracts_pass_snapshot_gate(self):
        rows = [paper(index, with_abstract=index <= 20) for index in range(1, 31)]
        result = assess_corpus_sufficiency(snapshot(rows), P2ClusterConfig())
        self.assertEqual(result["status"], "P2_CORPUS_READY")
        self.assertTrue(result["can_output_five_directions"])

    def test_p1_precision_false_blocks_by_default(self):
        value = snapshot([paper(index) for index in range(1, 31)], p1_passed=False)
        result = assess_corpus_sufficiency(value)
        self.assertEqual("P2_BLOCKED_BY_P1_PRECISION", result["status"])
        self.assertFalse(result["can_output_five_directions"])
        self.assertIn("p1_precision_gate_not_passed", result["reasons"])

    def test_p2_snapshot_excludes_adjacent_papers(self):
        rows = [paper(index) for index in range(1, 31)] + [paper(31, relevance_tier="adjacent")]
        value = snapshot(rows)
        self.assertEqual(30, value["paper_count"])
        self.assertEqual(1, value["excluded_non_direct_count"])
        self.assertTrue(all(item["relevance_tier"] == "direct" for item in value["papers"]))

    def test_average_linkage_is_deterministic_and_has_five_minimum_size_clusters(self):
        rows = [paper(index) for index in range(1, 31)]
        first = deterministic_average_linkage(snapshot(rows))
        second = deterministic_average_linkage(snapshot(list(reversed(rows))))
        self.assertEqual("P2_CLUSTERING_COMPLETE", first["status"])
        self.assertEqual(first["clusters"], second["clusters"])
        self.assertEqual(5, len(first["clusters"]))
        self.assertTrue(all(item["paper_count"] >= 3 for item in first["clusters"]))
        self.assertEqual("average", first["linkage"])
        self.assertEqual("tfidf_text_plus_topic_keyword", first["feature_method"])

    def test_cache_key_includes_corpus_hash_and_config_version(self):
        value = snapshot([paper(index) for index in range(1, 31)])
        first = deterministic_average_linkage(value, P2ClusterConfig())
        changed = deterministic_average_linkage(value, replace(P2ClusterConfig(), version="p2-config-test-change"))
        self.assertNotEqual(first["cache_key"], changed["cache_key"])
        self.assertEqual(value["corpus_hash"], first["corpus_hash"])


class NamingClient:
    def __init__(self, return_paper_ids: bool = False):
        self.return_paper_ids = return_paper_ids
        self.prompts = []

    def complete(self, system_prompt, user_prompt):
        self.prompts.append((system_prompt, user_prompt))
        clusters = json.loads(user_prompt)["clusters"]
        names = [
            {"cluster_id": item["cluster_id"], "name_zh": f"名称{index}", "name_en": f"Name {index}", "description": "固定簇"}
            for index, item in enumerate(clusters, start=1)
        ]
        payload = {"names": names}
        if self.return_paper_ids:
            payload["paper_ids"] = ["P999"]
        return payload, {"model": "test"}


class P2NamingTests(unittest.TestCase):
    def setUp(self):
        self.clustering = deterministic_average_linkage(snapshot([paper(index) for index in range(1, 31)]))
        self.request = ClusterNamingRequest(
            research_direction="AI-enabled information systems",
            clusters=tuple(self.clustering["clusters"]),
            corpus_hash=self.clustering["corpus_hash"],
            cluster_config_version=self.clustering["cluster_config_version"],
        )

    def test_llm_can_only_name_fixed_membership(self):
        before = membership_hash(self.request.clusters)
        named, _ = LLMClusterNamingProvider(NamingClient()).name_clusters(self.request)
        self.assertEqual(before, membership_hash(named))
        self.assertTrue(all(item["name_zh"] for item in named))

    def test_llm_output_with_paper_ids_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must_not_return_paper_ids"):
            LLMClusterNamingProvider(NamingClient(return_paper_ids=True)).name_clusters(self.request)

    def test_synthesis_blocks_before_model_when_p1_gate_is_false(self):
        client = NamingClient()
        provider = DeepSeekResearchSynthesisProvider(client)
        result = provider.synthesize(SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=tuple(paper(index) for index in range(1, 31)),
        ))
        self.assertEqual("P2_BLOCKED_BY_P1_PRECISION", result.status)
        self.assertEqual([], client.prompts)

    def test_synthesis_names_fixed_clusters_without_gap_generation_and_uses_cache(self):
        client = NamingClient()
        provider = DeepSeekResearchSynthesisProvider(client)
        request = SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=tuple(paper(index) for index in range(1, 31)),
            p1_precision_gate_passed=True,
        )
        first = provider.synthesize(request)
        second = provider.synthesize(request)
        self.assertEqual("SYNTHESIS_COMPLETE", first.status)
        self.assertEqual(5, len(first.top_subdirections))
        self.assertEqual([], first.gap_candidates)
        self.assertFalse(first.audit["research_gap_generation_in_p2"])
        self.assertTrue(second.audit["cache_hit"])
        self.assertEqual(1, len(client.prompts))
        prompt = " ".join(client.prompts[0])
        self.assertNotIn("gap_statement", prompt)
        self.assertNotIn("研究空白", prompt)


if __name__ == "__main__":
    unittest.main()
