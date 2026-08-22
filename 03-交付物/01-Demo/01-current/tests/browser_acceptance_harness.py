#!/usr/bin/env python3
"""Controlled browser-acceptance harness for the Phase E proposal workflow.

Runs the real Demo server on an isolated port with two fixture providers
injected at process level:

- discovery returns controlled fixture papers only (never mistaken for real
  retrieval output);
- synthesis builds the evidence matrix and formal gaps through the REAL
  deterministic EvidenceBoundResearchGapProvider / ClaimStore code, then
  bridges the formal gaps into gap_candidates so the existing UI can render
  them (wiring P3 into the server chain is planned task T05 and must not be
  faked in production code).

The proposal provider stays real: it calls the local fake_deepseek_server
over HTTP for every per-section generation request, so all checkpoints
(user constraints → blueprint & outline confirmation → per-section
generation → human review) execute production code end to end.

All fixture content is explicitly labeled 受控测试/界面验收 and must never be
quoted as a research conclusion.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

TESTS_DIR = Path(__file__).resolve().parent
SERVER_PATH = TESTS_DIR.parent / "server.py"
FIXTURE_PORT = int(os.getenv("ACCEPTANCE_FIXTURE_PORT", "18765"))
APP_PORT = int(os.getenv("ACCEPTANCE_APP_PORT", "8791"))

# 受控夹具论文：标题与摘要均声明为界面验收数据，不得作为真实检索结果引用。
FIXTURE_PAPERS = [
    {
        "paper_id": f"P{index:03d}",
        "title": f"Controlled fixture paper {index} for browser acceptance only",
        "abstract": (
            "This abstract is controlled fixture text for interface acceptance. "
            f"Fixture sentence {index}a describes an observed pattern in fixture data. "
            f"Fixture sentence {index}b reports a measured effect in fixture data. "
            "No claim here may be cited as a research finding."
        ),
        "journal": "Controlled Fixture Journal",
        "year": 2025,
        "doi": f"10.0000/fixture.{index}",
        "language": "en",
        "relevance_tier": "direct",
        "terminal_status": "eligible",
        "relevance_score": 80,
    }
    for index in range(1, 7)
]


class FixtureDiscoveryProvider:
    def discover(self, request):
        from paper_discovery_provider import DiscoveryResult

        return DiscoveryResult(
            status="RETRIEVAL_COMPLETE",
            papers=list(FIXTURE_PAPERS),
            analysis_papers=list(FIXTURE_PAPERS),
            search_log=[{"provider": "controlled_fixture", "status": "ok", "returned_rows": len(FIXTURE_PAPERS)}],
            message_to_user="受控浏览器验收：论文来自本地夹具，不代表任何真实检索结果。",
            provider_statuses=[{"provider": "controlled_fixture", "status": "ok", "returned_rows": len(FIXTURE_PAPERS)}],
            coverage_audit={"fixture": True},
        )


class FixtureSynthesisProvider:
    """Real deterministic P3 formalization over fixture papers, P2 bridged."""

    def synthesize(self, request):
        from evidence_matrix import build_evidence_matrix, evidence_indexes
        from research_gap_provider import (
            EvidenceBoundResearchGapProvider,
            ResearchGapRequest,
        )

        matrix = build_evidence_matrix(list(request.papers))
        _, span_index = evidence_indexes(matrix)
        by_paper: dict[str, list[str]] = {}
        for span_id, span in span_index.items():
            by_paper.setdefault(span["paper_id"], []).append(span_id)
        paper_ids = sorted(by_paper)
        support_spans = [by_paper[paper_ids[0]][0], by_paper[paper_ids[1]][0]]
        counter_spans = [by_paper[paper_ids[2]][0]]
        candidates = [{
            "candidate_id": "fixture_candidate_001",
            "subdirection_id": "fixture_subdirection_1",
            "gap_statement": "受控测试空白：夹具数据中的未解释差异（仅供界面验收）。",
            "evidence_span_ids": support_spans,
            "alternative_explanations": ["夹具内的替代解释A", "夹具内的替代解释B"],
            "research_question": "受控测试研究问题：夹具关系如何成立？（仅供界面验收）",
            "why_it_matters": "受控夹具说明：该空白仅用于验证界面与门禁。",
            "innovation_candidates": ["受控创新点A：界面验收用", "受控创新点B：界面验收用"],
            "feasible_method": {
                "design": "受控测试设计：实验室实验（夹具）",
                "data": "受控测试数据：夹具样本",
                "analysis": "受控测试分析：方差分析",
                "unit_of_analysis": "夹具用户",
                "context": "受控测试情境",
            },
            "counterevidence": [{
                "statement": "受控反证：夹具数据中存在不一致结果（仅供界面验收）。",
                "evidence_span_ids": counter_spans,
            }],
        }]
        gap_result = EvidenceBoundResearchGapProvider().formalize(
            ResearchGapRequest(
                cluster_id="fixture_subdirection_1",
                gap_candidates=tuple(candidates),
                evidence_matrix=matrix,
            )
        )
        if gap_result.status != "RESEARCH_GAPS_READY":
            raise RuntimeError(f"fixture formal gaps failed: {gap_result.rejected_candidates}")
        top_subdirections = [{
            "subdirection_id": "fixture_subdirection_1",
            "name_zh": "受控测试方向1（界面验收夹具）",
            "name_en": "Controlled fixture direction 1",
            "description": "受控夹具说明：聚类结果由夹具桥接，不代表P2真实结论。",
            "paper_ids": paper_ids,
        }]
        return SimpleNamespace(
            status="SYNTHESIS_COMPLETE",
            top_subdirections=top_subdirections,
            gap_candidates=list(gap_result.formal_gaps),
            formal_gaps=list(gap_result.formal_gaps),
            claim_store=gap_result.claim_store,
            limitations=["受控浏览器验收：synthesis由夹具提供，P2/P3服务端整合属T05，不因本验收视为通过。"],
            audit={
                "claim_audit": {"valid": True, "claim_count": len(gap_result.claim_store.get("claims", []))},
                "saturation": {"status": "ADVISORY_ONLY_FIXTURE", "advisory_only": True},
                "fixture": True,
            },
            message_to_user="受控夹具：正式空白与Claim Store由真实确定性代码在夹具论文上生成，仅供界面验收。",
        )


def main() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "controlled-fixture-key"
    os.environ["DEEPSEEK_BASE_URL"] = f"http://127.0.0.1:{FIXTURE_PORT}"
    os.environ["DEEPSEEK_MODEL"] = "controlled-browser-fixture"

    spec = importlib.util.spec_from_file_location("proposal_server", SERVER_PATH)
    server = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(server)
    server.build_dynamic_provider = lambda: FixtureDiscoveryProvider()
    server.build_research_synthesis_provider = lambda: FixtureSynthesisProvider()

    fake_spec = importlib.util.spec_from_file_location("fake_deepseek_server", TESTS_DIR / "fake_deepseek_server.py")
    fake_server = importlib.util.module_from_spec(fake_spec)
    assert fake_spec.loader
    fake_spec.loader.exec_module(fake_server)
    fixture_httpd = ThreadingHTTPServer(("127.0.0.1", FIXTURE_PORT), fake_server.Handler)
    threading.Thread(target=fixture_httpd.serve_forever, daemon=True, name="fixture-deepseek").start()

    app_httpd = ThreadingHTTPServer(("127.0.0.1", APP_PORT), server.AppHandler)
    print(f"[harness] fixture deepseek: http://127.0.0.1:{FIXTURE_PORT}")
    print(f"[harness] acceptance app:   http://127.0.0.1:{APP_PORT}")
    print("[harness] all paper/gap content is controlled fixture data for UI acceptance only")
    sys.stdout.flush()
    app_httpd.serve_forever()


if __name__ == "__main__":
    main()
