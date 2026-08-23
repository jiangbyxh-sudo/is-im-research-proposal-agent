import importlib.util
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SPEC = importlib.util.spec_from_file_location("proposal_server", SERVER_PATH)
server = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(server)


class ServerTests(unittest.TestCase):
    def test_openalex_transport_uses_stability_defaults(self):
        keys = ("PROPOSAL_RETRIEVAL_TIMEOUT", "PROPOSAL_RETRIEVAL_RETRIES")
        previous = {key: os.environ.pop(key, None) for key in keys}
        try:
            self.assertEqual({"timeout": 45, "retries": 5}, server.openalex_transport_settings())
        finally:
            for key, value in previous.items():
                if value is not None:
                    os.environ[key] = value

    def test_dynamic_provider_signature_tracks_local_knowledge_files(self):
        signature = server.dynamic_provider_signature()
        self.assertEqual(2, len(signature))
        self.assertTrue(all(isinstance(value, int) and value > 0 for value in signature))

    def test_catalog_is_complete(self):
        catalog = server.load_catalog()
        self.assertEqual(catalog["raw_topic_count"], 75)
        self.assertEqual(catalog["direction_count"], 61)
        ids = {item["direction_id"] for item in catalog["directions"]}
        self.assertIn("topic_ai_enabled_information_systems", ids)

    def test_broad_direction_uses_top_five_path_and_stops_when_disabled(self):
        result = server.build_research_response({
            "selected_direction_id": "topic_ai_enabled_information_systems",
            "chinese_count": 10,
            "english_count": 20,
        }, provider=server.UnconfiguredPaperDiscoveryProvider())
        self.assertEqual(result["request"]["derived_path"], "top_five_subdirections")
        self.assertEqual(result["status_code"], "DYNAMIC_RETRIEVAL_UNAVAILABLE")
        self.assertEqual(result["papers"], [])

    def test_question_uses_focused_path(self):
        result = server.build_research_response({
            "selected_direction_id": "topic_ai_enabled_information_systems",
            "fine_grained_question": "生成式AI如何改变组织知识检索？",
            "chinese_count": 12,
            "english_count": 24,
        }, provider=server.UnconfiguredPaperDiscoveryProvider())
        self.assertEqual(result["request"]["derived_path"], "focused_question")

    def test_configured_provider_returns_papers_and_audit_fields(self):
        class FakeProvider:
            def discover(self, request):
                return SimpleNamespace(
                    status="RETRIEVAL_PARTIAL",
                    message_to_user="partial",
                    papers=[{"title": "Verified paper"}],
                    search_log=[{"provider": "test"}],
                    exclusion_log=[],
                    shortages={"zh": 10, "en": 19},
                )

        result = server.build_research_response({
            "selected_direction_id": "topic_ai_enabled_information_systems",
            "chinese_count": 10,
            "english_count": 20,
        }, provider=FakeProvider())
        self.assertEqual(result["state"], "PAPERS_DISCOVERED")
        self.assertEqual(result["stages"][3]["status"], "complete")
        self.assertTrue(result["request"]["journal_pool_ids"])
        self.assertEqual(result["papers"][0]["title"], "Verified paper")

    def test_broad_path_returns_five_directions_and_selectable_gaps(self):
        papers = [{"title": f"Paper {index}"} for index in range(12)]

        class FakeProvider:
            def discover(self, request):
                return SimpleNamespace(
                    status="RETRIEVAL_PARTIAL", message_to_user="partial",
                    papers=papers[:5], analysis_papers=papers,
                    search_log=[], exclusion_log=[], shortages={"zh": 10, "en": 15},
                )

        class FakeSynthesis:
            def synthesize(self, request):
                directions = [
                    {"subdirection_id": f"d{index}", "name_zh": f"方向{index}", "name_en": f"Direction {index}", "paper_count": 2}
                    for index in range(1, 6)
                ]
                return SimpleNamespace(
                    status="SYNTHESIS_COMPLETE", top_subdirections=directions,
                    gap_candidates=[{"gap_id": "g1", "subdirection_id": "d1"}],
                    limitations=["pending fulltext"], audit={"input_paper_count": len(request.papers)},
                    message_to_user="ready",
                )

        result = server.build_research_response({
            "selected_direction_id": "topic_ai_enabled_information_systems",
            "chinese_count": 10, "english_count": 20,
        }, provider=FakeProvider(), synthesis_provider=FakeSynthesis())
        self.assertEqual(result["state"], "GAP_CANDIDATES_READY")
        self.assertEqual(len(result["top_subdirections"]), 5)
        self.assertEqual(result["next_allowed_actions"][0], "select_gap")
        self.assertEqual(result["synthesis_audit"]["input_paper_count"], 12)

    def test_discovery_can_return_before_synthesis_and_resume_by_job_id(self):
        papers = [{"title": f"Paper {index}"} for index in range(8)]

        class FakeProvider:
            def discover(self, request):
                return SimpleNamespace(
                    status="RETRIEVAL_COMPLETE", message_to_user="ready",
                    papers=papers[:4], analysis_papers=papers,
                    search_log=[], exclusion_log=[], shortages={"zh": 0, "en": 0},
                )

        class FakeSynthesis:
            def synthesize(self, request):
                return SimpleNamespace(
                    status="SYNTHESIS_COMPLETE",
                    top_subdirections=[{"subdirection_id": "d1"}],
                    gap_candidates=[{"gap_id": "g1", "subdirection_id": "d1"}],
                    limitations=[], audit={"input_paper_count": len(request.papers)},
                    message_to_user="ready",
                )

        discovery = server.build_research_response({
            "selected_direction_id": "topic_ai_enabled_information_systems",
            "chinese_count": 2, "english_count": 2, "run_synthesis": False,
        }, provider=FakeProvider())
        self.assertEqual(discovery["state"], "PAPERS_DISCOVERED")
        self.assertEqual(discovery["synthesis_status"], "SYNTHESIS_QUEUED")
        self.assertTrue(discovery["synthesis_job_id"])

        synthesis = server.run_synthesis_job(discovery["synthesis_job_id"], FakeSynthesis())
        self.assertEqual(synthesis["state"], "GAP_CANDIDATES_READY")
        self.assertEqual(synthesis["synthesis_audit"]["input_paper_count"], 8)
        self.assertTrue(synthesis["proposal_context_id"])

    def test_proposal_requires_verified_gap_and_innovation_selection(self):
        request = server.SynthesisRequest(
            research_direction="AI-enabled information systems",
            fine_grained_question=None,
            derived_path="top_five_subdirections",
            papers=({"title": "Paper 1"}, {"title": "Paper 2"}),
        )
        synthesis = SimpleNamespace(gap_candidates=[{
            "gap_id": "g1",
            "gap_statement": "待验证空白",
            "innovation_candidates": ["创新点A"],
            "formal": True,
        }], claim_store={"claims": []}, status="RESEARCH_GAPS_READY", audit={})
        context_id = server.store_proposal_context(request, synthesis)

        class FakeProposal:
            received = None

            def generate(self, proposal_request):
                self.received = proposal_request
                return SimpleNamespace(
                    status="READY_FOR_HUMAN_REVIEW",
                    proposal={"working_title": "Title"},
                    writing_guidance={"paradigm_id": "experiment"},
                    proposal_context={"gate_passed": True},
                    limitations=[],
                    audit={},
                    message_to_user="ready",
                )

        fake = FakeProposal()
        result = server.generate_proposal({
            "proposal_context_id": context_id,
            "selected_gap_id": "g1",
            "selected_innovation_id": "g1_innovation_1",
            "user_constraints": {"degree_level": "硕士"},
        }, fake)
        self.assertEqual(result["state"], "PROPOSAL_READY")
        self.assertEqual(result["proposal_context"]["session_id"], context_id)
        self.assertEqual({"claims": []}, fake.received.claim_store)
        self.assertEqual("硕士", fake.received.user_constraints["degree_level"])
        self.assertIn("skill", result["workflow_panels"])
        self.assertIn("audit", result["workflow_panels"])
        with self.assertRaises(server.RequestError):
            server.generate_proposal({
                "proposal_context_id": context_id,
                "selected_gap_id": "g1",
                "selected_innovation_id": "g1_innovation_99",
            }, FakeProposal())

    def test_nonformal_gap_cannot_enter_proposal(self):
        request = server.SynthesisRequest(
            research_direction="AI", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=({"title": "Paper"},),
        )
        synthesis = SimpleNamespace(gap_candidates=[{
            "gap_id": "g1", "innovation_candidates": ["i1"], "formal": False,
        }])
        context_id = server.store_proposal_context(request, synthesis)
        with self.assertRaisesRegex(server.RequestError, "P3正式证据门禁"):
            server.generate_proposal({
                "proposal_context_id": context_id,
                "selected_gap_id": "g1",
                "selected_innovation_id": "g1_innovation_1",
            }, SimpleNamespace())

    def test_p1_gate_unlock_references_real_v3_evidence(self):
        gate = server.P1_PRECISION_GATE
        self.assertTrue(gate["passed"])
        summary = gate["summary"]
        # 解锁必须锚定D039与v3盲审实测值；证据文件必须真实存在。
        self.assertEqual("D039", summary["decision"])
        self.assertGreaterEqual(summary["overall_precision_at_10"], 0.80)
        self.assertGreaterEqual(summary["weakest_group_precision"], 0.70)
        self.assertLessEqual(summary["obvious_false_positive_rate"], 0.10)
        self.assertEqual(60, summary["labeled_rows"])
        evidence = server.WORKSPACE / summary["evidence"]
        self.assertTrue(evidence.exists(), f"missing evidence file: {evidence}")
        result = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(summary["overall_precision_at_10"], result["overall_precision_at_10"], places=4)

    def test_phase_e_ui_exposes_all_confirmations_and_audit_panels(self):
        static = SERVER_PATH.parent / "static"
        html = (static / "index.html").read_text(encoding="utf-8")
        script = (static / "app.js").read_text(encoding="utf-8")
        for element_id in (
            "proposal-constraints-form", "confirm-proposal-constraints",
            "proposal-plan-review", "confirm-proposal-plan",
            "skill-panel", "evidence-panel", "saturation-panel", "audit-panel",
            "proposal-task-cards",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("USER_CONSTRAINT_CONFIRMATION_REQUIRED", script)
        self.assertIn("PROPOSAL_PLAN_CONFIRMATION_REQUIRED", script)
        self.assertIn("READY_FOR_HUMAN_REVIEW", script)

    def test_invalid_count_stops(self):
        with self.assertRaises(server.RequestError):
            server.build_research_response({
                "selected_direction_id": "topic_ai_enabled_information_systems",
                "chinese_count": 0,
                "english_count": 20,
            })

    def test_synthesis_key_is_process_only_and_never_echoed(self):
        keys = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")
        previous = {key: os.environ.get(key) for key in keys}
        try:
            result = server.configure_synthesis({
                "api_key": "sk-" + ("x" * 32),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-pro",
            })
            self.assertTrue(result["configured"])
            self.assertNotIn("api_key", result)
            self.assertEqual(result["persistence"], "process_memory_only")
            self.assertEqual(server.synthesis_provider_name(), "deepseek")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_openalex_key_is_process_only_and_never_echoed(self):
        previous = os.environ.get("OPENALEX_API_KEY")
        try:
            result = server.configure_retrieval({"openalex_api_key": "oa-test-key-123456"})
            self.assertTrue(result["configured"])
            self.assertNotIn("api_key", result)
            self.assertNotIn("openalex_api_key", result)
            self.assertEqual("process_memory_only", result["persistence"])
        finally:
            if previous is None:
                os.environ.pop("OPENALEX_API_KEY", None)
            else:
                os.environ["OPENALEX_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
