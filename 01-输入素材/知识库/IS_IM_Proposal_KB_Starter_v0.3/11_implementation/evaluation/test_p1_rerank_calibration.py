"""Deterministic tests for the P1 rerank calibration (reranker 2.1.0 / profiles 1.2.0)."""
import json
import sys
import unittest
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from paper_quality import evaluate_boundary  # noqa: E402
from semantic_reranker import RERANK_VERSION, review_title_signal  # noqa: E402

PROFILES_PATH = IMPLEMENTATION.parent / "01_taxonomy/generated/direction_profiles.json"


def profile(direction_id: str) -> dict:
    payload = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {item["direction_id"]: item for item in payload["profiles"]}[direction_id]


def record(title: str, abstract: str) -> dict:
    return {"paper_id": "p", "title": title, "abstract": abstract, "language": "en", "document_type": "journal-article"}


class ReviewTitleSignalTests(unittest.TestCase):
    def test_version_bumped(self):
        self.assertEqual("p1-directness-reranker-2.1.0", RERANK_VERSION)

    def test_meta_science_titles_are_flagged(self):
        for title in (
            "Generative artificial intelligence for literature reviews",
            "IT's a matter of trust: Literature reviews and analyses of human trust in information technology",
            "Inventing with Machines: Generative AI and the Evolving Landscape of IS Research",
        ):
            self.assertTrue(review_title_signal(record(title, "")), title)

    def test_empirical_and_bibliometric_titles_stay_unflagged(self):
        # "bibliometric" is deliberately absent from the pattern list: a
        # human-labeled relevant bibliometric study must not be demoted by type.
        for title in (
            "The Present and Future of Accountability for AI Systems: A Bibliometric Analysis",
            "Trust in Artificial Intelligence: Comparing Trust Processes Between Humans and Machines",
            "Effects of enterprise social media use on employee improvisation ability",
        ):
            self.assertFalse(review_title_signal(record(title, "")), title)

    def test_review_titled_direct_candidate_is_demoted(self):
        prof = profile("topic_generative_ai")
        rec = record(
            "A literature review of generative AI in organizations",
            "This literature review examines generative AI use in an organization and the workplace.",
        )
        result = evaluate_boundary(rec, prof)
        self.assertNotEqual("direct", result.relevance_tier)
        self.assertIn("review_title_demoted", result.evidence)

    def test_reviews_in_scope_opt_in_keeps_direct(self):
        prof = json.loads(json.dumps(profile("topic_generative_ai")))
        prof.setdefault("precision_policy", {}).setdefault("direct", {})["reviews_in_scope"] = True
        rec = record(
            "A literature review of generative AI in organizations",
            "This literature review examines generative AI use in an organization and the workplace.",
        )
        self.assertEqual("direct", evaluate_boundary(rec, prof).relevance_tier)


class TitleScopeExclusionTests(unittest.TestCase):
    def test_abstract_mention_does_not_demote_title_scoped_exclusion(self):
        prof = profile("topic_ai_trust")
        rec = record(
            "Trust in Artificial Intelligence: Comparing Trust Processes Between Humans and Machines",
            "Unlike prior work on trust in information technology, we study trust in AI.",
        )
        self.assertEqual("direct", evaluate_boundary(rec, prof).relevance_tier)

    def test_title_scoped_exclusion_demotes_adjacent_construct(self):
        prof = profile("topic_ai_trust")
        rec = record(
            "Human trust in information technology: a quantitative study",
            "We survey users about their trust in information technology and AI systems.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, rec and prof).relevance_tier)


class CalibratedFacetTests(unittest.TestCase):
    def test_natural_order_trust_phrase_now_matches_core(self):
        prof = profile("topic_ai_trust")
        rec = record(
            "Trust in Artificial Intelligence: Comparing Trust Processes Between Humans and Machines",
            "We compare trust in artificial intelligence with interpersonal trust processes.",
        )
        result = evaluate_boundary(rec, prof)
        self.assertEqual("direct", result.relevance_tier)
        self.assertTrue(any("artificial intelligence" in facet for facet in result.matched_core_facets))

    def test_trust_without_ai_object_stays_out(self):
        prof = profile("topic_ai_trust")
        rec = record(
            "Human trust in information technology: a quantitative study",
            "We survey users about their trust in information technology.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, prof).relevance_tier)

    def test_generative_ai_short_form_matches_core_with_context(self):
        prof = profile("topic_ai_enabled_information_systems")
        rec = record(
            "Shifting Dynamics: How Generative AI as a Boundary Resource Reshapes Digital Platforms",
            "Digital platforms are increasingly integrating Generative AI (GenAI) tools as a boundary resource.",
        )
        self.assertEqual("direct", evaluate_boundary(rec, prof).relevance_tier)

    def test_metaverse_title_excluded_from_ai_enabled_is(self):
        prof = profile("topic_ai_enabled_information_systems")
        rec = record(
            "Long Live the Metaverse: Identifying the Potential for Market Disruption",
            "The metaverse leverages generative AI and attracts organizations and users to digital platforms.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, prof).relevance_tier)

    def test_ai_trust_required_any_anchor_blocks_non_ai_trust(self):
        prof = profile("topic_ai_trust")
        rec = record(
            "User trust in websites: an empirical study",
            "We survey users about their trust in websites.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, prof).relevance_tier)


class RegressionGuardTests(unittest.TestCase):
    def test_existing_exclusions_still_demote_known_adjacent(self):
        prof = profile("information_behavior")
        rec = record(
            "Does Techno-invasion Lead to Employees' Deviant Behaviors?",
            "Techno-invasion increases employees' deviant behaviors in organizations.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, prof).relevance_tier)

    def test_decision_support_bibliometric_history_still_demoted(self):
        prof = profile("topic_decision_support")
        rec = record(
            "40 years of Decision Support Systems: A bibliometric analysis",
            "We analyze decision support systems research with bibliometric analysis.",
        )
        self.assertNotEqual("direct", evaluate_boundary(rec, prof).relevance_tier)


if __name__ == "__main__":
    unittest.main()
