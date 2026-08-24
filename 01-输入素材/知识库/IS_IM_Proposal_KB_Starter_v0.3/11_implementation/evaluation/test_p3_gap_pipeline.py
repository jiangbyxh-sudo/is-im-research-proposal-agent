"""Deterministic tests for the P3 gap-candidate pipeline (T05 main chain)."""
import json
import sys
import unittest
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from gap_candidate_provider import (  # noqa: E402
    GapCandidateRequest,
    LLMGapCandidateProvider,
    _validate_candidate,
    select_prompt_spans,
)
from research_synthesis_provider import (  # noqa: E402
    DeepSeekResearchSynthesisProvider,
    SynthesisRequest,
)


def fixture_papers(count: int = 35) -> list[dict]:
    groups = [
        "platform governance regulation openness",
        "algorithm recommendation personalization consumer",
        "trust artificial intelligence transparency human",
        "knowledge sharing community collaboration wiki",
        "privacy disclosure concern personal data",
    ]
    papers = []
    for index in range(1, count + 1):
        terms = groups[(index - 1) // (count // 5 or 1)] if count >= 5 else groups[0]
        papers.append({
            "paper_id": f"P{index:03d}",
            "title": f"{terms.split()[0]} study {index}",
            "abstract": f"We examine {terms} in context {index} with measurable findings.",
            "journal": "Test Journal",
            "year": 2025,
            "doi": f"10.0/t{index}",
            "relevance_tier": "direct",
            "terminal_status": "eligible",
        })
    return papers


class FakeClient:
    def __init__(self, candidate_mutator=None, judge_selector=None):
        self.calls = []
        self.candidate_mutator = candidate_mutator
        self.judge_selector = judge_selector

    def complete(self, system, user):
        self.calls.append(system)
        payload = json.loads(user)
        if "命名选手" in system:
            names = [{"cluster_id": c["cluster_id"], "name_zh": f"受控方向{c['cluster_id'][-1]}", "name_en": f"Test {c['cluster_id']}", "description": "受控"} for c in payload["clusters"]]
            return json.loads(json.dumps({"names": names}, ensure_ascii=False)), {"model": "fake"}
        if "命名裁判" in system:
            sels = [{"cluster_id": c["cluster_id"], "winner": "candidate_1", "reason": "受控"} for c in payload["clusters"]]
            return json.loads(json.dumps({"selections": sels}, ensure_ascii=False)), {"model": "fake"}
        if "空白候选选手" in system:
            spans = payload.get("evidence_spans") or []
            papers = sorted({s["paper_id"] for s in spans})
            if len(papers) < 2:
                return {"candidates": []}, {"model": "fake"}
            support = [spans[0]["span_id"], next(s["span_id"] for s in spans if s["paper_id"] != papers[0])]
            counter = [next(s["span_id"] for s in spans if s["paper_id"] == papers[-1])]
            candidate = {
                "gap_statement": f"受控空白：{payload['cluster']['name']}",
                "why_it_matters": "受控说明",
                "evidence_span_ids": support,
                "alternative_explanations": ["替代解释A"],
                "research_question": "受控研究问题？",
                "feasible_method": {"design": "实验", "data": "样本", "analysis": "方差分析", "unit_of_analysis": "用户", "context": "受控情境"},
                "counterevidence": [{"statement": "受控反证", "evidence_span_ids": counter}],
                "innovation_candidates": ["受控创新点"],
            }
            if self.candidate_mutator:
                candidate = self.candidate_mutator(candidate)
            return json.loads(json.dumps({"candidates": [candidate]}, ensure_ascii=False)), {"model": "fake"}
        if "空白候选裁判" in system:
            if self.judge_selector:
                return self.judge_selector(payload), {"model": "fake"}
            ids = [c["selection_id"] for c in payload["candidates"][:1]]
            return json.loads(json.dumps({"selections": [{"selection_id": i, "reason": "受控"} for i in ids]}, ensure_ascii=False)), {"model": "fake"}
        return {}, {"model": "fake"}


class SpanPoolValidationTests(unittest.TestCase):
    def test_invented_span_id_rejects_candidate(self):
        allowed = {"span_real_1", "span_real_2"}
        raw = {
            "gap_statement": "x", "research_question": "q?", "alternative_explanations": ["a"],
            "innovation_candidates": ["i"],
            "feasible_method": {"design": "d", "data": "da", "analysis": "an"},
            "evidence_span_ids": ["span_real_1", "span_forged_9"],
            "counterevidence": [{"statement": "c", "evidence_span_ids": ["span_real_2"]}],
        }
        self.assertIsNone(_validate_candidate(raw, allowed))

    def test_counterevidence_with_forged_span_rejects(self):
        allowed = {"span_real_1", "span_real_2"}
        raw = {
            "gap_statement": "x", "research_question": "q?", "alternative_explanations": ["a"],
            "innovation_candidates": ["i"],
            "feasible_method": {"design": "d", "data": "da", "analysis": "an"},
            "evidence_span_ids": ["span_real_1"],
            "counterevidence": [{"statement": "c", "evidence_span_ids": ["span_forged"]}],
        }
        self.assertIsNone(_validate_candidate(raw, allowed))

    def test_complete_candidate_passes(self):
        allowed = {"span_real_1", "span_real_2"}
        raw = {
            "gap_statement": "x", "research_question": "q?", "alternative_explanations": ["a"],
            "innovation_candidates": ["i"],
            "feasible_method": {"design": "d", "data": "da", "analysis": "an"},
            "evidence_span_ids": ["span_real_1"],
            "counterevidence": [{"statement": "c", "evidence_span_ids": ["span_real_2"]}],
        }
        self.assertIsNotNone(_validate_candidate(raw, allowed))

    def test_span_selection_is_deterministic_and_bounded(self):
        spans = [{"span_id": f"s{p}_{i}", "paper_id": f"P{p:03d}", "text": "t", "evidence_level": "abstract"} for p in range(1, 11) for i in range(5)]
        first = select_prompt_spans(spans)
        second = select_prompt_spans(list(reversed(spans)))
        self.assertEqual([s["span_id"] for s in first], [s["span_id"] for s in second])
        papers = {s["paper_id"] for s in first}
        self.assertEqual(10, len(papers), "round-robin must cover every paper before deepening")


class GapPipelineIntegrationTests(unittest.TestCase):
    def synthesize_with(self, client):
        provider = DeepSeekResearchSynthesisProvider(client)
        return provider.synthesize(SynthesisRequest(
            research_direction="platform governance", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=tuple(fixture_papers()),
            p1_precision_gate_passed=True,
        ))

    def test_formal_gaps_flow_through_main_chain(self):
        result = self.synthesize_with(FakeClient())
        self.assertEqual("SYNTHESIS_COMPLETE", result.status)
        self.assertTrue(result.formal_gaps)
        self.assertEqual(result.gap_candidates, result.formal_gaps)
        for gap in result.formal_gaps:
            self.assertIs(True, gap.get("formal"))
            self.assertGreaterEqual(len(gap.get("supporting_paper_ids", [])), 2)
            self.assertTrue(gap.get("alternative_explanations"))
            self.assertTrue(gap.get("research_question"))
            self.assertTrue(all(gap["feasible_method"][key] for key in ("design", "data", "analysis")))
            self.assertTrue(gap.get("counterevidence_claim_ids"))
            self.assertIn("falsification_plan", gap)
        self.assertGreaterEqual(len(result.claim_store.get("claims", [])), 2 * len(result.formal_gaps))
        subdirection_ids = {s["subdirection_id"] for s in result.top_subdirections}
        self.assertEqual(subdirection_ids, {g["subdirection_id"] for g in result.formal_gaps})

    def test_forged_span_never_becomes_formal_gap(self):
        def mutate(candidate):
            candidate["evidence_span_ids"] = ["span_forged_zzz"]
            return candidate
        result = self.synthesize_with(FakeClient(candidate_mutator=mutate))
        self.assertEqual([], result.formal_gaps)
        self.assertIn("不硬凑空白", "".join(result.limitations))

    def test_single_paper_support_is_rejected_by_formalizer(self):
        def mutate(candidate):
            candidate["evidence_span_ids"] = candidate["evidence_span_ids"][:1]
            return candidate
        result = self.synthesize_with(FakeClient(candidate_mutator=mutate))
        self.assertEqual([], result.formal_gaps)
        audit = result.audit.get("gap_candidates", {}).get("formalization", {})
        self.assertGreaterEqual(audit.get("rejected_count", 0), 1)

    def test_judge_selecting_none_leaves_gaps_empty_honestly(self):
        def judge(payload):
            return {"selections": []}, {"model": "fake"}
        result = self.synthesize_with(FakeClient(judge_selector=judge))
        self.assertEqual([], result.formal_gaps)
        self.assertIn("不硬凑空白", "".join(result.limitations))

    def test_title_only_corpus_yields_no_formal_evidence_and_no_gaps(self):
        papers = [{**paper, "abstract": ""} for paper in fixture_papers()]
        provider = DeepSeekResearchSynthesisProvider(FakeClient())
        result = provider.synthesize(SynthesisRequest(
            research_direction="platform governance", fine_grained_question=None,
            derived_path="top_five_subdirections", papers=tuple(papers),
            p1_precision_gate_passed=True,
        ))
        # 全部论文无摘要 → P2 语料门禁阻断（题名级证据不得进入正式链路）。
        self.assertIn(result.status, {"SYNTHESIS_INSUFFICIENT_EVIDENCE", "P2_BLOCKED_BY_P1_PRECISION"})
        self.assertEqual([], result.formal_gaps)


if __name__ == "__main__":
    unittest.main()
