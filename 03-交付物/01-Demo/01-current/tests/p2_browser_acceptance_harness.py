#!/usr/bin/env python3
"""Controlled browser-acceptance harness for the T04/P2 synthesis quality panel.

Runs the real Demo server on an isolated port with a controlled discovery
fixture, while the synthesis chain stays REAL end to end:

- corpus snapshot, deterministic TF-IDF average-linkage clustering, honest
  degradation gates and heat all execute the production P2 code;
- cluster naming runs the real Athlete A/B + blind Judge provider against the
  local fake_deepseek_server (all naming content is labeled 受控测试).

Three fixture corpora exercise three UI paths:

- platform_governance  -> 36 direct papers, all abstracts  -> 5 directions (complete);
- topic_data_governance -> 24 direct papers, all abstracts  -> honest 4 directions (degraded);
- topic_it_governance   -> 14 direct papers                 -> honest stop, no directions.

No fixture content may be quoted as a research conclusion.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SERVER_PATH = TESTS_DIR.parent / "server.py"
FIXTURE_PORT = int(os.getenv("P2_ACCEPTANCE_FIXTURE_PORT", "18767"))
APP_PORT = int(os.getenv("P2_ACCEPTANCE_APP_PORT", "8793"))

# 三个夹具主题池：仅用于驱动确定性聚类产生稳定分簇，内容均声明为受控测试。
THEME_POOLS = {
    "ecosystem": {
        "topic": "Platform ecosystems and complementors",
        "keywords": ["platform governance", "complementors", "ecosystem"],
        "sentences": [
            "Platform governance shapes complementor participation in digital ecosystems.",
            "Complementor strategies depend on platform rules and ecosystem boundaries.",
            "Ecosystem orchestration moderates value creation among platform complementors.",
        ],
    },
    "data_exchange": {
        "topic": "Data exchange and interoperability",
        "keywords": ["data exchange", "interoperability", "data sharing"],
        "sentences": [
            "Data exchange between organizations requires interoperability standards.",
            "Design principles for data sharing platforms balance openness and control.",
            "Interoperability governance explains variation in data exchange outcomes.",
        ],
    },
    "regulation": {
        "topic": "Government regulation of digital platforms",
        "keywords": ["government regulation", "digital government", "policy"],
        "sentences": [
            "Government regulation addresses market power of digital platforms.",
            "Policy instruments for platform oversight differ across jurisdictions.",
            "Digital government initiatives reshape regulatory capacity for platforms.",
        ],
    },
    "algorithmic": {
        "topic": "Algorithmic transparency and accountability",
        "keywords": ["algorithmic transparency", "accountability", "stakeholder"],
        "sentences": [
            "Algorithmic transparency requirements create accountability obligations.",
            "Stakeholder pressure drives algorithm disclosure on platforms.",
            "Accountability mechanisms for algorithmic decisions remain fragmented.",
        ],
    },
    "orchestration": {
        "topic": "Platform orchestration and regulatory externalities",
        "keywords": ["orchestration", "externalities", "coordination"],
        "sentences": [
            "Platform orchestration strategies generate regulatory externalities.",
            "Coordination failures among platforms produce spillover effects.",
            "The evolution of orchestration practices tracks regulatory shifts.",
        ],
    },
}


def _fixture_paper(index: int, theme: str, year: int) -> dict:
    pool = THEME_POOLS[theme]
    return {
        "paper_id": f"P2F{index:03d}",
        "title": f"Controlled fixture paper {index} on {pool['topic']} (UI acceptance only)",
        "abstract": (
            "This abstract is controlled fixture text for P2 interface acceptance; "
            f"it is not a research finding. {pool['sentences'][index % len(pool['sentences'])]} "
            "Fixture sentence for deterministic clustering vocabulary."
        ),
        "year": year,
        "source_title": "Controlled Fixture Journal",
        "doi": f"10.0000/p2fixture.{index}",
        "language": "en",
        "citation_count": (index * 7) % 41,
        "topics": [{"id": f"fixture/{theme}", "display_name": pool["topic"]}],
        "keywords": list(pool["keywords"]),
        "relevance_tier": "direct",
        "p1_match_score": 70 + (index % 26),
        "source_quality": 60 + (index % 36),
    }


def _fixture_corpus(direction_id: str) -> list[dict]:
    """Per-direction controlled corpora: complete / degraded / honest stop."""
    if direction_id == "platform_governance":
        plan = [("ecosystem", 8), ("data_exchange", 7), ("regulation", 7), ("algorithmic", 7), ("orchestration", 7)]
    elif direction_id == "topic_data_governance":
        plan = [("data_exchange", 8), ("ecosystem", 6), ("regulation", 5), ("algorithmic", 5)]
    elif direction_id == "topic_it_governance":
        plan = [("ecosystem", 5), ("data_exchange", 5), ("regulation", 4)]
    else:
        plan = []
    papers: list[dict] = []
    index = 1
    for theme, count in plan:
        for _ in range(count):
            papers.append(_fixture_paper(index, theme, 2023 + (index % 4)))
            index += 1
    return papers


class P2FixtureDiscoveryProvider:
    def discover(self, request):
        from paper_discovery_provider import DiscoveryResult
        from paper_quality import SCORE_CONFIG_VERSION

        papers = _fixture_corpus(request.selected_direction_id)
        return DiscoveryResult(
            status="RETRIEVAL_COMPLETE",
            papers=list(papers),
            analysis_papers=list(papers),
            search_log=[{"provider": "controlled_p2_fixture", "status": "ok", "returned_rows": len(papers)}],
            message_to_user="受控P2界面验收：论文来自本地夹具，聚类与命名链路为真实代码，内容不代表任何真实检索结果。",
            provider_statuses=[{"provider": "controlled_p2_fixture", "status": "ok", "returned_rows": len(papers)}],
            coverage_audit={"fixture": True, "direction_id": request.selected_direction_id},
            score_config_version=SCORE_CONFIG_VERSION,
        )


def main() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "controlled-fixture-key"
    os.environ["DEEPSEEK_BASE_URL"] = f"http://127.0.0.1:{FIXTURE_PORT}"
    os.environ["DEEPSEEK_MODEL"] = "controlled-browser-fixture"

    spec = importlib.util.spec_from_file_location("proposal_server", SERVER_PATH)
    server = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(server)
    server.build_dynamic_provider = lambda: P2FixtureDiscoveryProvider()

    fake_spec = importlib.util.spec_from_file_location("fake_deepseek_server", TESTS_DIR / "fake_deepseek_server.py")
    fake_server = importlib.util.module_from_spec(fake_spec)
    assert fake_spec.loader
    fake_spec.loader.exec_module(fake_server)
    fixture_httpd = ThreadingHTTPServer(("127.0.0.1", FIXTURE_PORT), fake_server.Handler)
    threading.Thread(target=fixture_httpd.serve_forever, daemon=True, name="fixture-deepseek").start()

    app_httpd = ThreadingHTTPServer(("127.0.0.1", APP_PORT), server.AppHandler)
    print(f"[harness] fixture deepseek: http://127.0.0.1:{FIXTURE_PORT}")
    print(f"[harness] acceptance app:   http://127.0.0.1:{APP_PORT}")
    print("[harness] P2 snapshot/clustering/heat/naming run REAL code; papers are controlled fixtures")
    sys.stdout.flush()
    app_httpd.serve_forever()


if __name__ == "__main__":
    main()
