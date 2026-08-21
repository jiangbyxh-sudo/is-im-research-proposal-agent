"""Deterministic P0 challenge cases for current retrieval and evidence gates."""
from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


EVALUATION_DIR = Path(__file__).resolve().parent
IMPLEMENTATION_DIR = EVALUATION_DIR.parent
KB_ROOT = IMPLEMENTATION_DIR.parent
WORKSPACE = KB_ROOT.parents[2]
REPORT_ROOT = WORKSPACE / "02-任务/01-current/T02-V0实现与结果报告/验收证据/P0-质量基线"

if str(IMPLEMENTATION_DIR) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION_DIR))

from observability.trace import write_trace  # noqa: E402
from paper_discovery_provider import (  # noqa: E402
    CrossrefPaperDiscoveryProvider,
    CrossrefTransport,
    DiscoveryRequest,
)
from research_synthesis_provider import DeepSeekResearchSynthesisProvider, SynthesisRequest  # noqa: E402


def _registry(path: Path, journals: list[dict]) -> None:
    path.write_text(json.dumps({"version": "challenge-1.0.0", "journals": journals}, ensure_ascii=False), encoding="utf-8")


def _journal(title: str, language: str, issn: str) -> dict:
    return {
        "canonical_title": title,
        "language": language,
        "issns": [issn],
        "ranking_levels": ["P0_TEST_ELIGIBLE"],
        "pool_ids": ["P0_TEST"],
        "default_eligible": True,
        "crossref_available": True,
    }


def _request(zh: int = 1, en: int = 1) -> DiscoveryRequest:
    return DiscoveryRequest(
        selected_direction_id="p0_challenge",
        research_direction="AI",
        fine_grained_question=None,
        chinese_count=zh,
        english_count=en,
        journal_pool_ids=("P0_TEST",),
    )


def run_challenges(report_root: Path = REPORT_ROOT) -> dict:
    report_root = report_root.resolve()
    trace_dir = report_root / "traces/challenges"
    outcomes = []

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
    rate_passed = payload["_transport_meta"]["attempts"] == 2 and any(
        call.args and call.args[0] == 2.0 for call in sleeper.call_args_list
    )
    trace_id, _ = write_trace(trace_dir, "CHALLENGE-CROSSREF-429", {
        "stage": "P0_RATE_LIMIT_SAFETY_FIX_NOT_QUALITY_FIX",
        "input": {"http_status": 429, "retry_after_seconds": 2},
        "versions": {"transport": "crossref-rate-policy-1.0.0"},
        "provider_runs": [payload["_transport_meta"]],
        "errors": [{"http_status": 429, "recovered": rate_passed}],
        "cost": 0,
        "status": "RATE_LIMIT_RECOVERED" if rate_passed else "RATE_LIMIT_RECOVERY_FAILED",
        "checkpoint": {"passed": rate_passed},
    })
    outcomes.append({"case_id": "CHALLENGE-CROSSREF-429", "passed": rate_passed, "trace_id": trace_id})

    with tempfile.TemporaryDirectory() as directory:
        registry_path = Path(directory) / "registry.json"
        _registry(registry_path, [_journal("Test Journal", "en", "0000-0001")])

        class TimeoutTransport:
            def get(self, url, params):
                raise TimeoutError("controlled timeout")

        timeout_result = CrossrefPaperDiscoveryProvider(
            registry_path, transport=TimeoutTransport(), max_journals_per_language=1, rows_per_journal=5
        ).discover(_request(zh=1, en=1))
        timeout_passed = not timeout_result.papers and any(
            item.get("error_type") == "TimeoutError" for item in timeout_result.exclusion_log
        )
        trace_id, _ = write_trace(trace_dir, "CHALLENGE-PROVIDER-TIMEOUT", {
            "stage": "P0_BASELINE_NOT_A_FIX",
            "input": {"provider": "Crossref", "failure": "controlled_timeout"},
            "provider_runs": timeout_result.search_log,
            "candidate_counts": {"final": len(timeout_result.papers)},
            "filters": timeout_result.exclusion_log,
            "status": timeout_result.status,
            "errors": timeout_result.exclusion_log,
            "checkpoint": {"passed": timeout_passed, "fabricated_results": 0},
            "missing_trace_fields": ["retry_count_not_exposed_for_terminal_exception"],
        })
        outcomes.append({"case_id": "CHALLENGE-PROVIDER-TIMEOUT", "passed": timeout_passed, "trace_id": trace_id})

    with tempfile.TemporaryDirectory() as directory:
        registry_path = Path(directory) / "registry.json"
        _registry(registry_path, [
            _journal("Chinese Test Journal", "zh", "ZH-0001"),
            _journal("English Test Journal", "en", "EN-0001"),
        ])

        class LanguageGapTransport:
            def get(self, url, params):
                if "ZH-0001" in url:
                    return {"message": {"items": []}}
                return {"message": {"items": [{
                    "title": ["AI organizational decision support"],
                    "DOI": "10.1000/language-gap",
                    "published": {"date-parts": [[2026]]},
                }]}}

        gap_result = CrossrefPaperDiscoveryProvider(
            registry_path, transport=LanguageGapTransport(), max_journals_per_language=1, rows_per_journal=5
        ).discover(_request())
        language_passed = gap_result.shortages == {"zh": 1, "en": 0} and all(
            item.get("language") == "en" for item in gap_result.papers
        )
        trace_id, _ = write_trace(trace_dir, "CHALLENGE-CHINESE-GAP", {
            "stage": "P0_BASELINE_NOT_A_FIX",
            "input": {"requested": {"zh": 1, "en": 1}},
            "provider_runs": gap_result.search_log,
            "candidate_counts": {"final": len(gap_result.papers)},
            "shortages": gap_result.shortages,
            "final_papers": gap_result.papers,
            "status": gap_result.status,
            "checkpoint": {"passed": language_passed, "cross_language_padding": 0},
        })
        outcomes.append({"case_id": "CHALLENGE-CHINESE-GAP", "passed": language_passed, "trace_id": trace_id})

    with tempfile.TemporaryDirectory() as directory:
        registry_path = Path(directory) / "registry.json"
        _registry(registry_path, [_journal("English Test Journal", "en", "EN-0002")])

        class QualityTransport:
            def get(self, url, params):
                return {"message": {"items": [
                    {"title": ["AI decision systems"], "DOI": "10.1000/duplicate", "published": {"date-parts": [[2026]]}},
                    {"title": ["AI decision systems duplicate"], "DOI": "10.1000/duplicate", "published": {"date-parts": [[2026]]}},
                    {"title": ["RETRACTED: AI decision systems"], "DOI": "10.1000/retracted", "published": {"date-parts": [[2026]]}},
                    {"title": ["AI systems without abstract"], "DOI": "10.1000/no-abstract", "published": {"date-parts": [[2026]]}},
                ]}}

        quality_result = CrossrefPaperDiscoveryProvider(
            registry_path, transport=QualityTransport(), max_journals_per_language=1, rows_per_journal=10
        ).discover(_request(zh=1, en=10))
        dois = [item.get("doi") for item in quality_result.analysis_papers]
        duplicate_passed = dois.count("10.1000/duplicate") == 1
        retraction_passed = "10.1000/retracted" not in dois and any(
            item.get("reason") == "retraction_or_correction" for item in quality_result.exclusion_log
        )
        no_abstract_paper = next(item for item in quality_result.analysis_papers if item.get("doi") == "10.1000/no-abstract")
        no_abstract_passed = no_abstract_paper.get("evidence_level") == "title_only"
        for case_id, passed, detail in (
            ("CHALLENGE-DUPLICATE", duplicate_passed, {"deduped_dois": dois}),
            ("CHALLENGE-RETRACTION", retraction_passed, {"exclusions": quality_result.exclusion_log}),
            ("CHALLENGE-NO-ABSTRACT", no_abstract_passed, {
                "paper": no_abstract_paper,
                "expected": "evidence_level=title_only and formal proposal blocked",
                "observed_gap": "current PaperRecord does not expose evidence_level",
            }),
        ):
            trace_id, _ = write_trace(trace_dir, case_id, {
                "stage": "P0_BASELINE_NOT_A_FIX",
                "input": {"fixture": "verified metadata challenge"},
                "candidate_counts": {"final_corpus": len(quality_result.analysis_papers)},
                "status": quality_result.status,
                "checkpoint": {"passed": passed},
                "actual_output": detail,
            })
            outcomes.append({"case_id": case_id, "passed": passed, "trace_id": trace_id})

    class MustNotRunClient:
        def complete(self, system_prompt, user_prompt):
            raise AssertionError("model must not run below evidence threshold")

    insufficient = DeepSeekResearchSynthesisProvider(MustNotRunClient()).synthesize(SynthesisRequest(
        research_direction="AI",
        fine_grained_question=None,
        derived_path="top_five_subdirections",
        papers=tuple({"title": f"Paper {index}"} for index in range(4)),
    ))
    insufficient_passed = insufficient.status == "SYNTHESIS_INSUFFICIENT_EVIDENCE" and not insufficient.top_subdirections
    trace_id, _ = write_trace(trace_dir, "CHALLENGE-INSUFFICIENT-EVIDENCE", {
        "stage": "P0_BASELINE_NOT_A_FIX",
        "input": {"paper_count": 4},
        "model": {"called": False, "cost": 0},
        "status": insufficient.status,
        "actual_output": {"directions": insufficient.top_subdirections, "gaps": insufficient.gap_candidates},
        "checkpoint": {"passed": insufficient_passed},
    })
    outcomes.append({"case_id": "CHALLENGE-INSUFFICIENT-EVIDENCE", "passed": insufficient_passed, "trace_id": trace_id})

    summary = {
        "baseline_version": "p0-challenges-1.0.0",
        "stage": "P0_BASELINE_NOT_A_FIX",
        "passed": sum(item["passed"] for item in outcomes),
        "failed": sum(not item["passed"] for item in outcomes),
        "outcomes": outcomes,
    }
    (report_root / "challenge_baseline.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# P0 · 挑战题基线",
        "",
        "> 通过表示当前实现满足该条最小护栏；不表示三个用户Bad Case已经修复。",
        "",
        "| Case | 结果 | Trace |",
        "|---|---|---|",
    ]
    for item in outcomes:
        lines.append(f"| {item['case_id']} | {'PASS' if item['passed'] else 'FAIL'} | {item['trace_id']} |")
    (report_root / "挑战题基线报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run_challenges(), ensure_ascii=False, indent=2))
