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

from multi_source_discovery_provider import MultiSourcePaperDiscoveryProvider
from paper_discovery_provider import DiscoveryRequest, DiscoveryResult
from paper_quality import SCORE_WEIGHTS, build_journal_index, dedupe_records, normalize_record, qualify_source, quality_gate, score_record


class EmptyCrossref:
    def discover(self, request):
        return DiscoveryResult(status="DYNAMIC_RETRIEVAL_UNAVAILABLE")


class FakeOpenAlex:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def search(self, query, from_date, to_date, document_types):
        self.calls.append(query)
        return list(self.records), {"provider": "openalex", "status": "ok", "query": query, "returned_rows": len(self.records)}


class RateLimitedOpenAlex:
    def __init__(self):
        self.calls = 0

    def search(self, *args):
        self.calls += 1
        raise HTTPError("https://api.openalex.org/works", 429, "rate limited", {}, None)


class P1RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles_payload = json.loads((KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((KB_ROOT / "02_journals/generated/journal_registry.json").read_text(encoding="utf-8"))
        cls.profiles = {item["direction_id"]: item for item in cls.profiles_payload["profiles"]}

    def test_all_61_profiles_have_p1_routes(self):
        self.assertEqual(61, self.profiles_payload["direction_count"])
        self.assertEqual(61, len(self.profiles))
        for profile in self.profiles.values():
            self.assertTrue(profile["labels"]["zh"])
            self.assertTrue(profile["labels"]["en"])
            self.assertGreaterEqual(len(profile["synonyms"]), 3)
            self.assertTrue(profile["boundaries"]["include"])
            self.assertTrue(profile["boundaries"]["exclude"])
            self.assertEqual({"openalex", "semantic_scholar", "crossref", "dblp"}, set(profile["provider_queries"]))
            self.assertGreaterEqual(len(profile["fallback_queries"]), 2)
            self.assertIn("openalex", profile["source_routes"]["required"])
            self.assertIn("crossref", profile["source_routes"]["required"])
            self.assertTrue(profile["journal_pool_ids"])

    def test_dedupe_priority_and_provenance(self):
        first = normalize_record({"title": "Trust in AI", "authors": ["A Li"], "year": 2025, "doi": "https://doi.org/10.1/X", "abstract": "one"}, "openalex")
        second = normalize_record({"title": "Trust in AI", "authors": ["A Li"], "year": 2025, "doi": "10.1/x", "abstract": "a longer abstract", "citation_count": 9}, "crossref")
        records, log = dedupe_records([first, second])
        self.assertEqual(1, len(records))
        self.assertEqual(["openalex", "crossref"], records[0]["providers"])
        self.assertEqual("a longer abstract", records[0]["abstract"])
        self.assertEqual("doi", log[0]["reason"])

    def test_hard_gate_excludes_retraction_and_wrong_source(self):
        profile = self.profiles["platform_governance"]
        record = normalize_record({"title": "Retracted platform study", "authors": ["A"], "year": date.today().year, "source_title": "Unknown", "document_type": "journal-article", "is_retracted": True}, "openalex")
        qualify_source(record, build_journal_index(self.registry), set(profile["journal_pool_ids"]))
        passed, reasons = quality_gate(record, profile, date.today().year - 4, date.today().year)
        self.assertFalse(passed)
        self.assertIn("retraction_or_correction", reasons)
        self.assertIn("source_not_qualified", reasons)
        self.assertTrue(record["untrusted_text_isolated"])

    def test_score_formula_is_exact_and_marked_uncalibrated(self):
        profile = self.profiles["platform_governance"]
        record = {"title": "Platform governance in information systems", "abstract": "Platform governance research in digital organizations", "journal_ranking": ["UTD24"], "citation_count": 20, "year": date.today().year, "evidence_level": "abstract", "providers": ["openalex", "crossref"]}
        score = score_record(record, profile, "platform governance", date.today().year - 4, date.today().year)
        expected = round(sum(score["components"][key] * SCORE_WEIGHTS[key] for key in SCORE_WEIGHTS), 2)
        self.assertEqual(expected, score["total"])
        self.assertEqual("uncalibrated", score["threshold_calibration_status"])

    def test_orchestrator_preserves_eligible_records_and_audit(self):
        profile = self.profiles["platform_governance"]
        pools = set(profile["journal_pool_ids"])
        journal = next(item for item in self.registry["journals"] if pools.intersection(item["pool_ids"]) and item.get("issns") and item["language"] == "en")
        year = date.today().year
        records = [{
            "external_id": f"W{index}", "title": f"Platform governance in digital organizations study {index}",
            "abstract": "platform governance information systems digital organizations empirical research " * 4,
            "authors": [f"Author {index}"], "year": year, "publication_date": f"{year}-01-01",
            "language": "en", "doi": f"10.5555/{index}", "source_title": journal["canonical_title"],
            "source_issns": journal["issns"], "document_type": "journal-article", "citation_count": 25,
        } for index in range(24)]
        provider = MultiSourcePaperDiscoveryProvider(
            KB_ROOT / "01_taxonomy/generated/direction_profiles.json",
            KB_ROOT / "02_journals/generated/journal_registry.json",
            openalex=FakeOpenAlex(records), crossref=EmptyCrossref(), enable_optional=False,
        )
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 5, 5, tuple(profile["journal_pool_ids"])))
        self.assertEqual("RETRIEVAL_PARTIAL", result.status)
        self.assertEqual(5, len(result.papers))
        self.assertEqual(24, result.coverage_audit["eligible_count"])
        self.assertEqual(0, result.coverage_audit["retracted_in_final"])
        self.assertEqual("p1-metadata-score-1.0.0", result.score_config_version)
        self.assertIn("language_coverage_gap", result.zero_result_diagnosis["causes"])
        cached = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 5, 5, tuple(profile["journal_pool_ids"])))
        self.assertEqual("hit", cached.provider_statuses[0]["status"])
        self.assertEqual(1, len(provider.openalex.calls))

    def test_rate_limit_is_not_misreported_as_provider_empty(self):
        profile = self.profiles["platform_governance"]
        openalex = RateLimitedOpenAlex()
        provider = MultiSourcePaperDiscoveryProvider(
            KB_ROOT / "01_taxonomy/generated/direction_profiles.json",
            KB_ROOT / "02_journals/generated/journal_registry.json",
            openalex=openalex, crossref=EmptyCrossref(), enable_optional=False,
        )
        result = provider.discover(DiscoveryRequest("platform_governance", "平台治理", None, 1, 1, 5, tuple(profile["journal_pool_ids"])))
        self.assertIn("rate_limited", result.zero_result_diagnosis["causes"])
        self.assertNotIn("provider_empty", result.zero_result_diagnosis["causes"])
        self.assertEqual(1, openalex.calls)


if __name__ == "__main__":
    unittest.main()
