from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path
from urllib.error import HTTPError


IMPLEMENTATION = Path(__file__).resolve().parents[1]
KB_ROOT = IMPLEMENTATION.parent
if str(IMPLEMENTATION) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION))

from candidate_ledger import build_candidate_trace, evaluate_candidate, ledger_summary
from multi_source_discovery_provider import MultiSourcePaperDiscoveryProvider
from openalex_provider import OpenAlexPaperProvider
from paper_discovery_provider import DiscoveryRequest, DiscoveryResult
from paper_quality import build_journal_index, evaluate_boundary, normalize_record, qualify_source, score_record
from retrieval_query_plan import OpenAlexQueryPlan, build_direction_query_plans, compile_openalex_filter
from semantic_reranker import multilingual_tokens


class EmptyCrossref:
    def discover(self, request):
        return DiscoveryResult(status="DYNAMIC_RETRIEVAL_UNAVAILABLE")


class FakeOpenAlex:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def search(self, plan):
        self.calls.append(plan)
        records = [{**item, "query_lane_ids": [plan.lane_id]} for item in self.records]
        return records, {"provider": "openalex", "status": "ok", "lane_id": plan.lane_id, "returned_rows": len(records)}


class RateLimitedOpenAlex:
    def __init__(self):
        self.calls = 0

    def search(self, plan):
        self.calls += 1
        raise HTTPError("https://api.openalex.org/works", 429, "rate limited", {}, None)


class PagingTransport:
    def __init__(self):
        self.params = []

    def get(self, endpoint, params):
        self.params.append(dict(params))
        page = len(self.params)
        return {
            "meta": {"count": 2, "next_cursor": "next" if page == 1 else None},
            "results": [{"id": f"https://openalex.org/W{page}", "display_name": f"Paper {page}", "type": "article"}],
        }, {"http_status": 200}


class RawCrossref:
    def __init__(self, records):
        self.records = records

    def discover(self, request):
        return DiscoveryResult(status="RETRIEVAL_PARTIAL", analysis_papers=self.records)


class P1RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles_payload = json.loads((KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((KB_ROOT / "02_journals/generated/journal_registry.json").read_text(encoding="utf-8"))
        cls.profiles = {item["direction_id"]: item for item in cls.profiles_payload["profiles"]}
        cls.journal_index = build_journal_index(cls.registry)

    def _journal(self, profile, language="en"):
        pools = set(profile["source_policy"]["tier_a_pool_ids"])
        return next(item for item in self.registry["journals"] if pools.intersection(item["pool_ids"]) and item.get("issns") and item["language"] == language)

    def _record(self, profile, title, abstract, language="en", **extra):
        journal = self._journal(profile, language)
        raw = {
            "title": title, "abstract": abstract, "authors": ["A"], "year": date.today().year,
            "language": language, "source_title": journal["canonical_title"], "source_issns": journal["issns"],
            "document_type": "journal-article", **extra,
        }
        return normalize_record(raw, "openalex")

    def test_all_61_profiles_have_new_schema(self):
        self.assertEqual(61, self.profiles_payload["direction_count"])
        for profile in self.profiles.values():
            self.assertTrue(profile["facets"]["core_phenomena"])
            self.assertTrue(profile["facets"]["required_context_any"])
            self.assertTrue(profile["facets"]["negative_contexts"])
            self.assertTrue(profile["source_policy"]["tier_a_pool_ids"])
            self.assertTrue(profile["queries"]["zh_precise"])

    def test_group_context_is_not_a_core_synonym(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        self.assertNotIn("human-computer interaction", profile["facets"]["core_phenomena"])
        self.assertNotIn("synonyms", profile)

    def test_openalex_document_type_filter_is_applied(self):
        value = compile_openalex_filter({"document_types": ["journal-article", "proceedings-article"]})
        self.assertIn("type:article|review|proceedings-article", value)

    def test_openalex_approved_topic_filter_is_applied(self):
        self.assertIn("topics.id:T1|T2", compile_openalex_filter({"approved_topic_ids": ["T1", "https://openalex.org/T2"]}))

    def test_openalex_approved_source_filter_is_applied(self):
        self.assertIn("primary_location.source.id:S1", compile_openalex_filter({"approved_source_ids": ["S1"]}))

    def test_openalex_cursor_pagination(self):
        transport = PagingTransport()
        records, log = OpenAlexPaperProvider(transport=transport).search(OpenAlexQueryPlan("lane", "test", max_pages=3))
        self.assertEqual(2, len(records))
        self.assertEqual("*", transport.params[0]["cursor"])
        self.assertEqual("next", transport.params[1]["cursor"])
        self.assertEqual("provider_exhausted", log["stop_reason"])

    def test_stop_condition_uses_post_boundary_count(self):
        profile = self.profiles["platform_governance"]
        plans = build_direction_query_plans(profile, "2022-01-01", "2026-12-31")
        self.assertTrue(all(plan.stop_target == 10 for plan in plans))

    def test_profile_boundaries_are_executed(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        record = self._record(profile, "AI for radiology diagnosis", "Artificial intelligence clinical diagnosis medical imaging only")
        self.assertEqual("reject", evaluate_boundary(record, profile).decision)

    def test_clinical_ai_only_is_not_ai_enabled_is(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        record = self._record(profile, "Measurements, Algorithms, and Presentations of Reality: Framing Interactions with AI-Enabled Decision Support", "Clinical medical diagnosis and colonoscopy practice using AI systems")
        decision = evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": profile["labels"]["en"]})
        self.assertNotEqual("eligible", decision.terminal_status)

    def test_genai_is_research_agenda_is_retained(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        record = self._record(profile, "Generative Artificial Intelligence: Opportunities for Information Systems Research", "Generative artificial intelligence creates opportunities for information systems research in organizations and digital work")
        decision = evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": profile["labels"]["en"]})
        self.assertEqual("eligible", decision.terminal_status)

    def test_hci_only_paper_is_downranked_for_ai_enabled_is(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        record = self._record(profile, "Post-growth Human-Computer Interaction", "Human-computer interaction design for sustainability and users")
        decision = evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": profile["labels"]["en"]})
        self.assertNotEqual("eligible", decision.terminal_status)

    def test_unknown_source_does_not_enter_final_automatically(self):
        profile = self.profiles["platform_governance"]
        record = normalize_record({"title": "Platform governance", "abstract": "platform governance digital platform", "authors": ["A"], "year": date.today().year, "source_title": "Unknown", "document_type": "journal-article"}, "openalex")
        decision = evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": "platform governance"})
        self.assertEqual("manual_review", decision.terminal_status)

    def test_source_quality_does_not_replace_content_relevance(self):
        profile = self.profiles["topic_ai_enabled_information_systems"]
        record = self._record(profile, "Post-growth Human-Computer Interaction", "interaction design sustainability")
        qualify_source(record, self.journal_index, set(profile["journal_pool_ids"]), profile)
        self.assertGreater(record["source_quality"], 0)
        self.assertEqual("reject", evaluate_boundary(record, profile).decision)

    def test_generic_terms_are_downweighted(self):
        self.assertEqual({}, multilingual_tokens("AI information systems research human computer"))

    def test_cjk_query_is_tokenized_or_embedded_correctly(self):
        tokens = multilingual_tokens("平台治理与算法机制")
        self.assertIn("平台", tokens)
        self.assertIn("治理", tokens)

    def test_doi_landing_page_is_not_fulltext(self):
        record = normalize_record({"title": "X", "doi": "10.1/x", "fulltext_url": "https://doi.org/10.1/x"}, "crossref")
        self.assertFalse(record["verified_fulltext_available"])
        self.assertIsNone(record["fulltext_url"])

    def test_oa_landing_page_is_not_fulltext(self):
        record = normalize_record({"title": "X", "oa_url": "https://publisher.example/article"}, "openalex")
        self.assertFalse(record["verified_fulltext_available"])
        self.assertEqual("title_only", record["evidence_level"])

    def test_normalized_impact_used_when_available(self):
        profile = self.profiles["platform_governance"]
        record = self._record(profile, "Platform governance", "platform governance digital platform", citation_normalized_percentile=0.9)
        qualify_source(record, self.journal_index, set(profile["journal_pool_ids"]), profile)
        score = score_record(record, profile, "platform governance", date.today().year - 4, date.today().year)
        self.assertEqual("citation_normalized_percentile", score["normalized_impact_method"])

    def test_candidate_count_conservation(self):
        profile = self.profiles["platform_governance"]
        records = [self._record(profile, f"Platform governance {i}", "platform governance digital platform ecosystem") for i in range(3)]
        decisions = [evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": "platform governance"}) for record in records]
        selected = [record for record in records if record["terminal_status"] == "eligible"][:1]
        summary = ledger_summary(records, selected)
        self.assertTrue(summary["count_conserved"])
        self.assertEqual(3, summary["candidate_trace_count"])
        self.assertEqual(3, len([build_candidate_trace(record, decision) for record, decision in zip(records, decisions)]))

    def test_crossref_merge_keeps_all_candidate_decisions(self):
        profile = self.profiles["platform_governance"]
        journal = self._journal(profile)
        weak = {"title": "Unrelated chemistry", "authors": ["B"], "year": date.today().year, "source_title": journal["canonical_title"], "source_issns": journal["issns"], "document_type": "journal-article"}
        provider = MultiSourcePaperDiscoveryProvider(KB_ROOT / "01_taxonomy/generated/direction_profiles.json", KB_ROOT / "02_journals/generated/journal_registry.json", openalex=FakeOpenAlex([]), crossref=RawCrossref([weak]), enable_optional=False)
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 1, 5))
        self.assertEqual(result.coverage_audit["deduplicated_count"], len(result.candidate_traces))
        self.assertEqual(1, len(result.candidate_traces))

    def test_english_papers_do_not_fill_chinese_quota(self):
        profile = self.profiles["platform_governance"]
        journal = self._journal(profile)
        records = [{"external_id": f"W{i}", "title": f"Platform governance {i}", "abstract": "platform governance digital platform ecosystem", "authors": ["A"], "year": date.today().year, "language": "en", "source_title": journal["canonical_title"], "source_issns": journal["issns"], "document_type": "journal-article"} for i in range(3)]
        provider = MultiSourcePaperDiscoveryProvider(KB_ROOT / "01_taxonomy/generated/direction_profiles.json", KB_ROOT / "02_journals/generated/journal_registry.json", openalex=FakeOpenAlex(records), crossref=EmptyCrossref(), enable_optional=False)
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 2, 1, 5))
        self.assertEqual(0, result.chinese_coverage["english_substitution_count"])
        self.assertEqual(2, result.shortages["zh"])

    def test_retracted_record_never_enters_selected(self):
        profile = self.profiles["platform_governance"]
        record = self._record(profile, "Platform governance", "platform governance digital platform", is_retracted=True)
        decision = evaluate_candidate(record, profile, self.journal_index, date.today().year - 4, date.today().year, {"query": "platform governance"})
        self.assertEqual("gate_reject", decision.terminal_status)

    def test_unconfigured_provider_is_not_reported_as_queried(self):
        profile = self.profiles["platform_governance"]
        provider = MultiSourcePaperDiscoveryProvider(KB_ROOT / "01_taxonomy/generated/direction_profiles.json", KB_ROOT / "02_journals/generated/journal_registry.json", openalex=FakeOpenAlex([]), crossref=EmptyCrossref(), enable_optional=False)
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 1, 5))
        optional = [item for item in result.provider_statuses if item["provider"] in profile["source_routes"]["optional"]]
        self.assertTrue(optional)
        self.assertTrue(all(item["status"] == "not_configured" for item in optional))

    def test_rate_limit_is_not_misreported_as_provider_empty(self):
        provider = MultiSourcePaperDiscoveryProvider(KB_ROOT / "01_taxonomy/generated/direction_profiles.json", KB_ROOT / "02_journals/generated/journal_registry.json", openalex=RateLimitedOpenAlex(), crossref=EmptyCrossref(), enable_optional=False)
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 1, 5))
        self.assertIn("rate_limited", result.zero_result_diagnosis["causes"])
        self.assertNotIn("provider_empty", result.zero_result_diagnosis["causes"])


if __name__ == "__main__":
    unittest.main()
