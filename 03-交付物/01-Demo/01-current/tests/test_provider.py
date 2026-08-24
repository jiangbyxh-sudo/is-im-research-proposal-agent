import sys
import json
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from pathlib import Path


KB_PROVIDER_DIR = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3/11_implementation"
sys.path.insert(0, str(KB_PROVIDER_DIR))

from paper_discovery_provider import CrossrefPaperDiscoveryProvider, CrossrefTransport  # noqa: E402


class StaticTransport:
    def get(self, url, params):
        return {
            "message": {
                "items": [
                    {"title": ["AI-enabled organizational decision support"], "DOI": "10.1/good", "published": {"date-parts": [[2026]]}},
                    {"title": ["Blockchain enabled traffic optimization"], "DOI": "10.1/irrelevant", "published": {"date-parts": [[2025]]}},
                    {"title": ["RETRACTED: AI-enabled personalisation"], "DOI": "10.1/retracted", "published": {"date-parts": [[2025]]}},
                ]
            }
        }


class ProviderTests(unittest.TestCase):
    def test_crossref_concurrency_obeys_public_and_polite_pool_caps(self):
        public_provider = CrossrefPaperDiscoveryProvider(Path("unused"), transport=CrossrefTransport())
        polite_provider = CrossrefPaperDiscoveryProvider(
            Path("unused"), transport=CrossrefTransport(mailto="researcher@example.edu"), max_workers=99
        )
        self.assertEqual(public_provider.max_workers, 1)
        self.assertEqual(public_provider.concurrency_policy, "crossref_public_pool")
        self.assertEqual(polite_provider.max_workers, 3)
        self.assertEqual(polite_provider.concurrency_policy, "crossref_polite_pool")

    def test_crossref_429_honors_retry_after_and_records_rate_headers(self):
        class FakeResponse:
            headers = {"X-Rate-Limit-Limit": "50", "X-Rate-Limit-Interval": "1s"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, *args):
                return json.dumps({"message": {"items": []}}).encode("utf-8")

        rate_error = HTTPError(
            "https://api.crossref.org/works", 429, "rate limited",
            {"Retry-After": "2", "X-Rate-Limit-Limit": "1", "X-Rate-Limit-Interval": "1s"},
            io.BytesIO(b""),
        )
        transport = CrossrefTransport(retries=1)
        with patch("paper_discovery_provider.urlopen", side_effect=[rate_error, FakeResponse()]), patch(
            "paper_discovery_provider.time.sleep"
        ) as sleeper:
            payload = transport.get("https://api.crossref.org/works", {"rows": 1})
        self.assertEqual(payload["_transport_meta"]["attempts"], 2)
        self.assertEqual(payload["_transport_meta"]["rate_limit"], 50.0)
        self.assertTrue(any(call.args and call.args[0] == 2.0 for call in sleeper.call_args_list))

    def test_crossref_returns_raw_records_for_unified_candidate_ledger(self):
        provider = CrossrefPaperDiscoveryProvider(Path("unused"), transport=StaticTransport())
        journal = {
            "canonical_title": "MIS Quarterly",
            "language": "en",
            "issns": ["0276-7783"],
            "ranking_levels": ["UTD24", "FMS_INT_A"],
            "pool_ids": ["IS_CORE"],
        }
        papers, audit, exclusions = provider._fetch_journal(
            journal, "AI-enabled information systems", "2022-01-01", "2026-08-21"
        )
        self.assertEqual([paper["doi"] for paper in papers], ["10.1/good", "10.1/irrelevant", "10.1/retracted"])
        self.assertFalse(papers[0]["is_correction"])
        self.assertTrue(papers[2]["is_correction"])
        self.assertEqual([], exclusions)
        self.assertEqual(audit["language"], "en")
        self.assertEqual(audit["ranking_levels"], ["UTD24", "FMS_INT_A"])

    def test_cn_cas_supplement_is_merged_without_rank_inflation(self):
        registry_path = KB_PROVIDER_DIR.parents[0] / "02_journals/generated/journal_registry.json"
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        journals = {item["canonical_title"]: item for item in payload["journals"]}
        self.assertEqual(payload["version"], "0.4.0")
        self.assertEqual(payload["journal_count"], 179)
        self.assertIn("CSSCI_2025_2026_SOURCE", journals["中国图书馆学报"]["ranking_levels"])
        self.assertIn("PKU_CORE_2023", journals["中国图书馆学报"]["ranking_levels"])
        self.assertFalse(journals["科技情报研究"]["default_eligible"])
        self.assertFalse(journals["Social Media + Society"]["default_eligible"])
        self.assertIn("CAS_SSCI_2025_ZONE1", journals["Social Media + Society"]["ranking_levels"])


if __name__ == "__main__":
    unittest.main()
