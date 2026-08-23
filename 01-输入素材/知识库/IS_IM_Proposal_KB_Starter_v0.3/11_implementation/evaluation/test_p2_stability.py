from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from cluster_naming_provider import (  # noqa: E402
    AthleteJudgeClusterNamingProvider,
    ClusterNamingRequest,
    DeterministicClusterNamingProvider,
    membership_hash,
)
from research_synthesis_provider import DeepSeekResearchSynthesisProvider, SynthesisRequest  # noqa: E402
from stable_subdirection_clustering import (  # noqa: E402
    P2ClusterConfig,
    assess_corpus_sufficiency,
    build_corpus_snapshot,
    compute_cluster_heat,
    deterministic_average_linkage,
)


TOPICS = ["trust", "governance", "adoption", "collaboration", "decision"]


def paper(index: int, with_abstract: bool = True, relevance_tier: str = "direct", **overrides) -> dict:
    topic = TOPICS[(index - 1) % len(TOPICS)]
    row = {
        "paper_id": f"P{index:03d}",
        "title": f"{topic.title()} in AI-enabled information systems {index}",
        "abstract": f"{topic} {topic} evidence in organizations and digital work {index}" if with_abstract else "",
        "year": 2026,
        "journal": "Information Systems Research",
        "doi": f"10.1000/stable.{index}",
        "language": "en",
        "topics": [{"id": f"T-{topic}", "name": topic}],
        "keywords": [{"name": f"AI {topic}"}],
        "relevance_tier": relevance_tier,
    }
    row.update(overrides)
    return row


def snapshot(rows: list[dict], p1_passed: bool = True) -> dict:
    return build_corpus_snapshot(
        direction_id="topic_ai_enabled_information_systems",
        papers=rows,
        data_cutoff_date="2026-08-23",
        direction_profile_version="1.2.0-p1-retrieval",
        retrieval_version="p1-query-plan-2.0.0",
        score_version="p1-directness-reranker-2.1.0",
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

    def test_p0_style_27_papers_with_abstracts_degrade_instead_of_five(self):
        result = assess_corpus_sufficiency(snapshot([paper(index) for index in range(1, 28)]))
        self.assertEqual(result["status"], "P2_CORPUS_DEGRADED")
        self.assertFalse(result["can_output_five_directions"])
        self.assertEqual(4, result["honest_target"])
        self.assertIn("paper_count_below_30", result["reasons"])

    def test_27_papers_without_abstracts_still_blocked(self):
        rows = [paper(index, with_abstract=False) for index in range(1, 28)]
        result = assess_corpus_sufficiency(snapshot(rows))
        self.assertEqual(result["status"], "SYNTHESIS_INSUFFICIENT_EVIDENCE")
        self.assertIn("abstract_count_below_20", result["reasons"])
        self.assertIn("evidence_supports_fewer_than_three_directions", result["reasons"])

    def test_30_papers_and_20_abstracts_pass_snapshot_gate(self):
        rows = [paper(index, with_abstract=index <= 20) for index in range(1, 31)]
        result = assess_corpus_sufficiency(snapshot(rows), P2ClusterConfig())
        self.assertEqual(result["status"], "P2_CORPUS_READY")
        self.assertTrue(result["can_output_five_directions"])
        self.assertEqual(5, result["honest_target"])

    def test_honest_target_scales_with_abstract_density(self):
        rows = [paper(index, with_abstract=index <= 15) for index in range(1, 31)]
        result = assess_corpus_sufficiency(snapshot(rows))
        self.assertEqual("P2_CORPUS_DEGRADED", result["status"])
        self.assertEqual(3, result["honest_target"])
        self.assertIn("abstract_count_below_20", result["reasons"])

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

    def test_degraded_corpus_clusters_to_honest_target_not_five(self):
        rows = [paper(index) for index in range(1, 22)]
        result = deterministic_average_linkage(snapshot(rows))
        self.assertEqual("P2_CLUSTERING_DEGRADED", result["status"])
        self.assertEqual(3, result["honest_target"])
        self.assertEqual(3, len(result["clusters"]))
        self.assertTrue(all(item["paper_count"] >= 3 for item in result["clusters"]))
        self.assertIn("paper_count_below_30", result["degradation_reasons"])

    def test_heat_is_present_deterministic_and_bounded(self):
        rows = [
            paper(index, year=2026 - (index % 3), citation_count=index * 3,
                  p1_match_score={"total": 40.0 + index}, source_quality=85.0)
            for index in range(1, 31)
        ]
        first = deterministic_average_linkage(snapshot(rows))
        second = deterministic_average_linkage(snapshot(rows))
        self.assertEqual(first["clusters"], second["clusters"])
        for cluster in first["clusters"]:
            self.assertIn("heat", cluster)
            self.assertIn("heat_components", cluster)
            self.assertGreaterEqual(cluster["heat"], 0.0)
            self.assertLessEqual(cluster["heat"], 1.0)
            components = cluster["heat_components"]
            self.assertEqual(
                {"paper_share", "recent_growth", "citation_velocity", "match_score", "source_quality"},
                set(components),
            )
            for value in components.values():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_heat_weights_reflect_config(self):
        rows = [paper(index, p1_match_score={"total": 90.0}, source_quality=100.0) for index in range(1, 31)]
        config = replace(P2ClusterConfig(), heat_weights=(1.0, 0.0, 0.0, 0.0, 0.0))
        result = deterministic_average_linkage(snapshot(rows), config)
        shares = sum(cluster["heat_components"]["paper_share"] for cluster in result["clusters"])
        heats = sum(cluster["heat"] for cluster in result["clusters"])
        self.assertAlmostEqual(shares, heats, places=3)

    def test_language_counts_disclose_missing_chinese_papers(self):
        rows = [paper(index) for index in range(1, 31)]
        result = deterministic_average_linkage(snapshot(rows))
        self.assertEqual({"en": 30}, result["language_counts"])

    def test_cache_key_includes_corpus_hash_and_config_version(self):
        value = snapshot([paper(index) for index in range(1, 31)])
        first = deterministic_average_linkage(value, P2ClusterConfig())
        changed = deterministic_average_linkage(value, replace(P2ClusterConfig(), version="p2-config-test-change"))
        self.assertNotEqual(first["cache_key"], changed["cache_key"])
        self.assertEqual(value["corpus_hash"], first["corpus_hash"])

    def test_cache_key_includes_profile_and_cutoff_metadata(self):
        rows = [paper(index) for index in range(1, 31)]
        base = snapshot(rows)
        bumped_profile = build_corpus_snapshot(
            direction_id="topic_ai_enabled_information_systems", papers=rows,
            data_cutoff_date="2026-08-23", direction_profile_version="1.3.0-p1-retrieval",
            retrieval_version="p1-query-plan-2.0.0", score_version="p1-directness-reranker-2.1.0",
            p1_precision_gate_passed=True,
        )
        later_cutoff = build_corpus_snapshot(
            direction_id="topic_ai_enabled_information_systems", papers=rows,
            data_cutoff_date="2026-08-24", direction_profile_version="1.2.0-p1-retrieval",
            retrieval_version="p1-query-plan-2.0.0", score_version="p1-directness-reranker-2.1.0",
            p1_precision_gate_passed=True,
        )
        base_key = deterministic_average_linkage(base)["cache_key"]
        self.assertNotEqual(base_key, deterministic_average_linkage(bumped_profile)["cache_key"])
        self.assertNotEqual(base_key, deterministic_average_linkage(later_cutoff)["cache_key"])
        self.assertEqual(base["corpus_hash"], bumped_profile["corpus_hash"])


class ArenaClient:
    """Stub DeepSeek client that answers athlete A/B and judge prompts."""

    def __init__(self, judge_winner: str = "candidate_1", judge_error: str | None = None,
                 athlete_error: str | None = None, return_paper_ids: bool = False):
        self.judge_winner = judge_winner
        self.judge_error = judge_error
        self.athlete_error = athlete_error
        self.return_paper_ids = return_paper_ids
        self.prompts: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> tuple[dict, dict]:
        self.prompts.append((system_prompt, user_prompt))
        if "命名裁判" in system_prompt:
            if self.judge_error:
                raise RuntimeError(self.judge_error)
            clusters = json.loads(user_prompt)["clusters"]
            selections = [
                {"cluster_id": item["cluster_id"], "winner": self.judge_winner, "reason": "更贴近簇内容"}
                for item in clusters
            ]
            return {"selections": selections}, {"model": "test-judge"}
        if self.athlete_error:
            raise RuntimeError(self.athlete_error)
        clusters = json.loads(user_prompt)["clusters"]
        athlete = "B" if "选手B" in system_prompt else "A"
        names = [
            {"cluster_id": item["cluster_id"], "name_zh": f"选手{athlete}名称{index}",
             "name_en": f"Athlete {athlete} Name {index}", "description": f"选手{athlete}边界"}
            for index, item in enumerate(clusters, start=1)
        ]
        payload = {"names": names}
        if self.return_paper_ids:
            payload["paper_ids"] = ["P999"]
        return payload, {"model": f"test-athlete-{athlete}"}


class P2NamingTests(unittest.TestCase):
    def setUp(self):
        self.clustering = deterministic_average_linkage(snapshot([paper(index) for index in range(1, 31)]))
        self.request = ClusterNamingRequest(
            research_direction="AI-enabled information systems",
            clusters=tuple(self.clustering["clusters"]),
            corpus_hash=self.clustering["corpus_hash"],
            cluster_config_version=self.clustering["cluster_config_version"],
        )

    def test_arena_runs_two_athletes_and_one_blind_judge(self):
        client = ArenaClient()
        named, audit = AthleteJudgeClusterNamingProvider(client).name_clusters(self.request)
        self.assertEqual(3, len(client.prompts))
        self.assertIn("选手A", client.prompts[0][0])
        self.assertIn("选手B", client.prompts[1][0])
        self.assertIn("命名裁判", client.prompts[2][0])
        judge_payload = json.loads(client.prompts[2][1])
        self.assertNotIn("athlete", judge_payload["clusters"][0]["candidate_1"])
        self.assertEqual(membership_hash(self.request.clusters), membership_hash(named))
        self.assertEqual("athlete_judge_arena", audit["provider"])
        self.assertEqual({"athlete_a": 5, "athlete_b": 0}, audit["athlete_win_counts"])
        self.assertTrue(all(item["selected_from"] == "athlete_a" for item in named))

    def test_arena_judge_can_pick_candidate_2_per_cluster(self):
        client = ArenaClient(judge_winner="candidate_2")
        named, audit = AthleteJudgeClusterNamingProvider(client).name_clusters(self.request)
        self.assertEqual({"athlete_a": 0, "athlete_b": 5}, audit["athlete_win_counts"])
        self.assertTrue(all(item["selected_from"] == "athlete_b" for item in named))
        self.assertTrue(all(item["name_zh"].startswith("选手B") for item in named))

    def test_arena_rejects_athlete_returning_paper_ids(self):
        with self.assertRaisesRegex(ValueError, "must_not_return_paper_ids"):
            AthleteJudgeClusterNamingProvider(ArenaClient(return_paper_ids=True)).name_clusters(self.request)

    def test_arena_rejects_judge_tampering(self):
        client = ArenaClient()
        original = client.complete

        def judge_tampered(system_prompt: str, user_prompt: str):
            if "命名裁判" not in system_prompt:
                return original(system_prompt, user_prompt)
            return {"selections": [], "paper_ids": ["P001"]}, {"model": "bad-judge"}

        client.complete = judge_tampered
        with self.assertRaisesRegex(ValueError, "judge_must_not_return_paper_ids"):
            AthleteJudgeClusterNamingProvider(client).name_clusters(self.request)

    def test_arena_rejects_judge_winner_outside_candidates(self):
        client = ArenaClient(judge_winner="candidate_3")
        with self.assertRaisesRegex(ValueError, "judge_winner_must_be_candidate_1_or_candidate_2"):
            AthleteJudgeClusterNamingProvider(client).name_clusters(self.request)

    def test_arena_rejects_judge_missing_cluster_selection(self):
        client = ArenaClient()
        original = client.complete

        def judge_drops_one(system_prompt: str, user_prompt: str):
            raw, audit = original(system_prompt, user_prompt)
            if "命名裁判" in system_prompt:
                raw = {"selections": raw["selections"][:-1]}
            return raw, audit

        client.complete = judge_drops_one
        with self.assertRaisesRegex(ValueError, "judge_must_select_for_every_fixed_cluster_exactly_once"):
            AthleteJudgeClusterNamingProvider(client).name_clusters(self.request)

    def test_deterministic_fallback_names_fixed_clusters(self):
        named, audit = DeterministicClusterNamingProvider().name_clusters(self.request)
        self.assertEqual(membership_hash(self.request.clusters), membership_hash(named))
        self.assertTrue(all(item["name_zh"] for item in named))
        self.assertEqual("deterministic_feature_terms", audit["provider"])


class P2SynthesisTests(unittest.TestCase):
    def request(self, rows: list[dict], p1_passed: bool = True) -> SynthesisRequest:
        return SynthesisRequest(
            research_direction="AI-enabled information systems", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=tuple(rows), p1_precision_gate_passed=p1_passed,
        )

    def test_synthesis_blocks_before_model_when_p1_gate_is_false(self):
        client = ArenaClient()
        provider = DeepSeekResearchSynthesisProvider(client)
        result = provider.synthesize(self.request([paper(index) for index in range(1, 31)], p1_passed=False))
        self.assertEqual("P2_BLOCKED_BY_P1_PRECISION", result.status)
        self.assertEqual([], client.prompts)

    def test_synthesis_names_fixed_clusters_via_arena_and_uses_cache(self):
        client = ArenaClient()
        provider = DeepSeekResearchSynthesisProvider(client)
        request = self.request([paper(index) for index in range(1, 31)])
        first = provider.synthesize(request)
        second = provider.synthesize(request)
        self.assertEqual("SYNTHESIS_COMPLETE", first.status)
        self.assertEqual(5, len(first.top_subdirections))
        self.assertEqual([], first.gap_candidates)
        self.assertFalse(first.audit["research_gap_generation_in_p2"])
        self.assertTrue(first.audit["stability_self_check"]["exact_match"])
        self.assertEqual(2, first.audit["stability_self_check"]["runs"])
        self.assertEqual("athlete_judge_arena", first.audit["naming"]["provider"])
        self.assertTrue(all("heat" in item for item in first.top_subdirections))
        self.assertTrue(second.audit["cache_hit"])
        self.assertEqual(3, len(client.prompts))
        prompt = " ".join(client.prompts[0])
        self.assertNotIn("gap_statement", prompt)
        self.assertNotIn("研究空白", prompt)

    def test_synthesis_degrades_to_partial_with_explanation(self):
        provider = DeepSeekResearchSynthesisProvider(ArenaClient())
        result = provider.synthesize(self.request([paper(index) for index in range(1, 22)]))
        self.assertEqual("SYNTHESIS_PARTIAL", result.status)
        self.assertEqual(3, len(result.top_subdirections))
        self.assertEqual(3, result.audit["honest_target"])
        self.assertTrue(any("不足30篇" in value for value in result.limitations))
        self.assertIn("未硬凑五方向", result.message_to_user)

    def test_synthesis_falls_back_to_deterministic_naming_on_arena_failure(self):
        provider = DeepSeekResearchSynthesisProvider(ArenaClient(judge_error="judge down"))
        result = provider.synthesize(self.request([paper(index) for index in range(1, 31)]))
        self.assertEqual("SYNTHESIS_COMPLETE", result.status)
        self.assertEqual("deterministic_feature_terms", result.audit["naming"]["provider"])
        self.assertTrue(result.audit["naming_fallback_reason"])
        self.assertTrue(any("回退确定性特征命名" in value for value in result.limitations))

    def test_synthesis_audit_discloses_corpus_quality_fields(self):
        provider = DeepSeekResearchSynthesisProvider(ArenaClient())
        result = provider.synthesize(self.request([paper(index) for index in range(1, 31)]))
        audit = result.audit
        for key in [
            "input_paper_count", "direct_paper_count", "abstract_count", "data_cutoff_date",
            "direction_profile_version", "retrieval_version", "score_version", "cluster_config_version",
            "naming_prompt_version", "language_counts", "honest_target", "heat_method",
            "stability_self_check", "corpus_hash",
        ]:
            self.assertIn(key, audit)
        self.assertEqual({"en": 30}, audit["language_counts"])


class P2HeatTests(unittest.TestCase):
    def test_heat_components_sum_with_weights(self):
        rows = [paper(index, citation_count=10, p1_match_score={"total": 80.0}, source_quality=90.0)
                for index in range(1, 31)]
        result = deterministic_average_linkage(snapshot(rows))
        weights = P2ClusterConfig().heat_weights
        for cluster in result["clusters"]:
            components = cluster["heat_components"]
            expected = sum(weight * components[name] for weight, name in zip(
                weights,
                ["paper_share", "recent_growth", "citation_velocity", "match_score", "source_quality"],
            ))
            self.assertAlmostEqual(expected, cluster["heat"], places=3)

    def test_compute_cluster_heat_handles_missing_scores(self):
        rows = [paper(index, p1_match_score=None, source_quality=None, citation_count=0, year=0)
                for index in range(1, 31)]
        result = deterministic_average_linkage(snapshot(rows))
        for cluster in result["clusters"]:
            self.assertEqual(0.0, cluster["heat_components"]["match_score"])
            self.assertEqual(0.0, cluster["heat_components"]["source_quality"])


if __name__ == "__main__":
    unittest.main()
