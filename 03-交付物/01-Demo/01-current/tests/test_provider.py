import sys
import json
import unittest
from pathlib import Path


KB_PROVIDER_DIR = Path(__file__).resolve().parents[4] / "01-输入素材/知识库/IS_IM_Proposal_KB_Starter_v0.3/11_implementation"
sys.path.insert(0, str(KB_PROVIDER_DIR))

from paper_discovery_provider import CrossrefPaperDiscoveryProvider  # noqa: E402


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
    def test_fetch_excludes_irrelevant_and_retracted_records(self):
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
        self.assertEqual([paper["doi"] for paper in papers], ["10.1/good"])
        self.assertEqual({item["reason"] for item in exclusions}, {"relevance_below_threshold", "retraction_or_correction"})
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
