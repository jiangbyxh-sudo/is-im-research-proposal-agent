from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from citation_graph_provider import (  # noqa: E402
    CitationExpansionRequest,
    OpenAlexCitationGraphProvider,
    canonical_stable_id,
    stable_identifiers,
)
from citation_verification import (  # noqa: E402
    CitationVerifier,
    CrossrefCitationMetadataProvider,
    OpenAlexCitationMetadataProvider,
)
from multi_perspective_search_plan import PERSPECTIVES, build_multi_perspective_search_plan  # noqa: E402
from research_skills.adapters import (  # noqa: E402
    P1CitationExpansionSkillAdapter,
    build_default_registry,
)
from research_skills.contracts import ResearchSkillContext, SkillRunStatus  # noqa: E402
from research_skills.registry import ResearchSkillRegistry  # noqa: E402
from retrieval_saturation import SaturationConfig, evaluate_retrieval_saturation  # noqa: E402


def work(work_id: str, title: str, doi: str | None = None, cited_by_count: int = 0, retracted: bool = False) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": title,
        "abstract_inverted_index": {"Evidence": [0], "abstract": [1]},
        "authorships": [{"author": {"display_name": "Alice Example"}}],
        "publication_year": 2024,
        "publication_date": "2024-01-01",
        "language": "en",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "primary_location": {
            "landing_page_url": "https://example.test/paper",
            "source": {
                "id": "https://openalex.org/S1",
                "display_name": "MIS Quarterly",
                "issn": ["0276-7783"],
                "issn_l": "0276-7783",
            },
        },
        "best_oa_location": {},
        "type": "article",
        "cited_by_count": cited_by_count,
        "topics": [],
        "keywords": [],
        "is_retracted": retracted,
    }


class FakeGraphTransport:
    def get(self, endpoint: str, params: dict):
        if endpoint.endswith("/W1"):
            return {"id": "https://openalex.org/W1", "referenced_works": ["https://openalex.org/W3", "https://openalex.org/W4"]}, {"fixture": True}
        if endpoint.endswith("/W2"):
            return {"id": "https://openalex.org/W2", "referenced_works": ["https://openalex.org/W3"]}, {"fixture": True}
        filter_value = params.get("filter", "")
        if filter_value == "openalex:W3|W4":
            return {"results": [work("W3", "Shared neighbor", "10.1000/shared", 50), work("W4", "Reference only", "10.1000/ref", 5)]}, {"fixture": True}
        if filter_value == "openalex:W3":
            return {"results": [work("W3", "Shared neighbor", "10.1000/shared", 50)]}, {"fixture": True}
        if filter_value == "cites:W1":
            return {"results": [work("W3", "Shared neighbor", "10.1000/shared", 50), work("W5", "Citing work", "10.1000/citing", 8)]}, {"fixture": True}
        if filter_value == "cites:W2":
            return {"results": [work("W3", "Shared neighbor", "10.1000/shared", 50)]}, {"fixture": True}
        raise AssertionError(f"unexpected_call:{endpoint}:{params}")


class StaticMetadataProvider:
    def __init__(self, name: str, *, fail: bool = False, retracted: bool = False, title: str = "Canonical title"):
        self.provider_name = name
        self.fail = fail
        self.retracted = retracted
        self.title = title

    def lookup(self, candidate: dict) -> dict:
        if self.fail:
            raise TimeoutError("fixture timeout")
        return {
            "provider": self.provider_name,
            "status": "RETRACTED" if self.retracted else "RESOLVED",
            "record": {
                "title": self.title,
                "authors": ["Alice Example"],
                "year": 2024,
                "doi": "10.1000/test",
                "source_title": "MIS Quarterly",
                "integrity_status": "retracted" if self.retracted else "unknown",
            },
        }


class FakeCrossrefTransport:
    def get(self, endpoint: str, params: dict):
        return {
            "message": {
                "title": ["Canonical title"],
                "author": [{"given": "Alice", "family": "Example"}],
                "published-online": {"date-parts": [[2024, 1, 1]]},
                "DOI": "10.1000/test",
                "container-title": ["MIS Quarterly"],
            },
            "_transport_meta": {"fixture": True},
        }


class FakeSingleWorkTransport:
    def get(self, endpoint: str, params: dict):
        return work("W9", "Canonical title", "10.1000/test"), {"fixture": True}


class DiscoveryLoopTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "profile_version": "fixture-1",
            "direction_id": "topic_ai_enabled_information_systems",
            "labels": {"en": "AI-enabled information systems", "zh": "AI赋能信息系统"},
            "queries": {
                "en_precise": ["AI-enabled information systems"],
                "zh_precise": ["AI赋能信息系统"],
            },
            "facets": {
                "core_phenomena": ["AI-enabled information systems", "AI赋能信息系统"],
                "technology_terms": ["generative AI"],
                "required_context_any": ["organization"],
            },
        }

    def test_search_plan_has_all_five_perspectives_and_is_deterministic(self):
        first = build_multi_perspective_search_plan(self.profile, "How does generative AI change digital work?")
        second = build_multi_perspective_search_plan(self.profile, "How does generative AI change digital work?")
        self.assertEqual(set(PERSPECTIVES), set(first["perspective_coverage"]))
        self.assertEqual([], first["missing_perspectives"])
        self.assertEqual(first["plan_hash"], second["plan_hash"])
        self.assertTrue(first["discovery_only"])
        self.assertFalse(first["llm_generated_queries"])
        serialized = json.dumps(first, ensure_ascii=False)
        self.assertNotIn("min_focality_score", serialized)
        self.assertNotIn("directness_threshold", serialized)

    def test_question_changes_plan_hash_without_changing_profile(self):
        first = build_multi_perspective_search_plan(self.profile, "Question A")
        second = build_multi_perspective_search_plan(self.profile, "Question B")
        self.assertNotEqual(first["plan_hash"], second["plan_hash"])

    def test_all_61_profiles_receive_five_perspective_coverage(self):
        payload = json.loads(
            (IMPLEMENTATION.parent / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8")
        )
        self.assertEqual(61, payload["direction_count"])
        for profile in payload["profiles"]:
            with self.subTest(direction_id=profile["direction_id"]):
                plan = build_multi_perspective_search_plan(profile)
                self.assertEqual([], plan["missing_perspectives"])

    def test_stable_identifier_prefers_doi_then_openalex(self):
        record = {
            "title": "Paper", "year": 2024, "doi": "https://doi.org/10.1000/ABC",
            "external_ids": {"openalex": "https://openalex.org/W123"},
        }
        self.assertEqual("doi:10.1000/abc", canonical_stable_id(record))
        self.assertEqual("W123", stable_identifiers(record)["openalex"])

    def test_citation_neighbors_are_candidates_not_formal_papers(self):
        provider = OpenAlexCitationGraphProvider(FakeGraphTransport())
        result = provider.expand(CitationExpansionRequest(seed_papers=(
            {"title": "Seed one", "year": 2024, "external_ids": {"openalex": "W1"}},
            {"title": "Seed two", "year": 2024, "external_ids": {"openalex": "W2"}},
        )))
        self.assertEqual("CITATION_EXPANSION_COMPLETE", result.status)
        shared = next(item for item in result.discovery_candidates if item["doi"] == "10.1000/shared")
        self.assertEqual(2, shared["seed_degree"])
        self.assertEqual("P1_REEVALUATION_REQUIRED", shared["selection_status"])
        self.assertEqual("not_evaluated", shared["p1_relevance_tier"])
        self.assertTrue(shared["discovery_only"])
        self.assertFalse(result.audit["formal_papers_emitted"])
        self.assertNotIn("papers", result.__dict__)

    def test_graph_without_openalex_seed_stops_honestly(self):
        result = OpenAlexCitationGraphProvider(FakeGraphTransport()).expand(CitationExpansionRequest(
            seed_papers=({"title": "DOI only", "doi": "10.1000/no-openalex"},),
        ))
        self.assertEqual("CITATION_EXPANSION_UNAVAILABLE", result.status)
        self.assertEqual([], result.discovery_candidates)

    def test_citation_verification_is_not_relevance(self):
        candidate = {"title": "Canonical title", "year": 2024, "doi": "10.1000/test"}
        result = CitationVerifier([
            StaticMetadataProvider("one"), StaticMetadataProvider("two"),
        ]).verify([candidate])
        checked = result.candidates[0]
        self.assertEqual("VERIFIED", checked["citation_verification"]["verdict"])
        self.assertEqual("not_evaluated", checked["p1_relevance_tier"])
        self.assertTrue(result.audit["citation_verification_is_not_relevance"])
        self.assertFalse(result.audit["formal_papers_emitted"])

    def test_crossref_and_openalex_metadata_connectors_parse_canonical_records(self):
        candidate = {
            "title": "Canonical title", "year": 2024, "doi": "10.1000/test",
            "external_ids": {"openalex": "W9"},
        }
        crossref = CrossrefCitationMetadataProvider(FakeCrossrefTransport()).lookup(candidate)
        openalex = OpenAlexCitationMetadataProvider(FakeSingleWorkTransport()).lookup(candidate)
        self.assertEqual("RESOLVED", crossref["status"])
        self.assertEqual("10.1000/test", crossref["record"]["doi"])
        self.assertEqual("RESOLVED", openalex["status"])
        self.assertEqual("W9", openalex["record"]["openalex_id"])

    def test_provider_failure_yields_partial_not_verified(self):
        candidate = {"title": "Canonical title", "year": 2024, "doi": "10.1000/test"}
        result = CitationVerifier([
            StaticMetadataProvider("one"), StaticMetadataProvider("two", fail=True),
        ]).verify([candidate])
        self.assertEqual("CITATION_VERIFICATION_PARTIAL", result.status)
        self.assertEqual("PARTIAL", result.candidates[0]["citation_verification"]["verdict"])

    def test_retraction_is_preserved(self):
        candidate = {"title": "Canonical title", "year": 2024, "doi": "10.1000/test"}
        result = CitationVerifier([StaticMetadataProvider("one", retracted=True)]).verify([candidate])
        self.assertEqual("RETRACTED", result.candidates[0]["citation_verification"]["verdict"])

    def test_saturation_is_advisory_only(self):
        rounds = [
            {"source": "keyword", "candidate_ids": ["A", "B"], "direct_ids": ["A"]},
            {"source": "citation_1", "candidate_ids": ["A", "B"], "direct_ids": ["A"]},
            {"source": "citation_2", "candidate_ids": ["A", "B"], "direct_ids": ["A"]},
        ]
        result = evaluate_retrieval_saturation(rounds, SaturationConfig(window_rounds=2))
        self.assertEqual("SATURATION_CANDIDATE", result["status"])
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["changes_p1_thresholds"])

    def test_default_registry_exposes_local_plan_and_saturation(self):
        registry = build_default_registry()
        ids = {item["skill_id"] for item in registry.descriptors()}
        self.assertIn("p1.multi_perspective_search_plan", ids)
        self.assertIn("p1.retrieval_saturation", ids)
        plan = registry.run(
            "p1.multi_perspective_search_plan", {"profile": self.profile}, ResearchSkillContext(stage="P1"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, plan.status)

    def test_graph_adapter_preserves_discovery_only_boundary(self):
        registry = ResearchSkillRegistry()
        registry.register(P1CitationExpansionSkillAdapter(OpenAlexCitationGraphProvider(FakeGraphTransport())))
        result = registry.run(
            "p1.citation_graph_expansion",
            {"seed_papers": [{"title": "Seed", "year": 2024, "external_ids": {"openalex": "W1"}}]},
            ResearchSkillContext(stage="P1"),
        )
        self.assertEqual(SkillRunStatus.COMPLETE, result.status)
        self.assertFalse(result.audit["formal_papers_emitted"])
        self.assertNotIn("papers", result.output)


if __name__ == "__main__":
    unittest.main()
