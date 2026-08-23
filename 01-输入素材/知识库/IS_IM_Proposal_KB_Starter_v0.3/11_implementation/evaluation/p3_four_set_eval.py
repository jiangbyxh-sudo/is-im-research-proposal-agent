#!/usr/bin/env python3
"""T05 four-set evaluation for the P3 gap-candidate main chain.

Fixed / holdout-similar / regression / challenge sets run offline against the
real synthesis provider with a controlled model stub. Every set writes a
trace JSON into the T05 evidence folder; gates map to the T05 acceptance
thresholds that can be checked offline (title-only blocking, forged-span
rejection, anchor completeness, no-fabrication invariants).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from research_synthesis_provider import DeepSeekResearchSynthesisProvider, SynthesisRequest  # noqa: E402

KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
OUT_DIR = WORKSPACE / "02-任务/01-current/T05-P3证据矩阵与研究空白/验收证据/P3-证据矩阵与空白"

GROUPS = [
    "platform governance regulation openness",
    "algorithm recommendation personalization consumer",
    "trust artificial intelligence transparency human",
    "knowledge sharing community collaboration wiki",
    "privacy disclosure concern personal data",
]


def paper(index: int, abstract: bool = True, count: int = 35) -> dict:
    terms = GROUPS[min(len(GROUPS) - 1, (index - 1) // max(1, count // 5))]
    return {
        "paper_id": f"P{index:03d}",
        "title": f"{terms.split()[0]} study {index}",
        "abstract": f"We examine {terms} in context {index} with measurable findings." if abstract else "",
        "journal": "Test Journal",
        "year": 2025,
        "doi": f"10.0/t{index}",
        "relevance_tier": "direct",
        "terminal_status": "eligible",
    }


class ControlledGapClient:
    """Naming arena + span-honest gap candidates; optional adversarial modes."""

    def __init__(self, mode: str = "honest"):
        self.mode = mode
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        payload = json.loads(user)
        if "命名选手" in system:
            names = [{"cluster_id": c["cluster_id"], "name_zh": f"受控簇{c['cluster_id'][-1]}", "name_en": f"C{c['cluster_id']}", "description": "受控"} for c in payload["clusters"]]
            return json.loads(json.dumps({"names": names}, ensure_ascii=False)), {"model": "controlled"}
        if "命名裁判" in system:
            sels = [{"cluster_id": c["cluster_id"], "winner": "candidate_1", "reason": "受控"} for c in payload["clusters"]]
            return json.loads(json.dumps({"selections": sels}, ensure_ascii=False)), {"model": "controlled"}
        if "空白候选选手" in system:
            spans = payload.get("evidence_spans") or []
            papers = sorted({s["paper_id"] for s in spans})
            if len(papers) < 2:
                return {"candidates": []}, {"model": "controlled"}
            support = [spans[0]["span_id"], next(s["span_id"] for s in spans if s["paper_id"] != papers[0])]
            counter = [next(s["span_id"] for s in spans if s["paper_id"] == papers[-1])]
            if self.mode == "forge_span":
                support = support + ["span_forged_offpool"]
            candidate = {
                "gap_statement": f"受控空白：{payload['cluster']['name']}",
                "why_it_matters": "受控评测，不构成研究结论。",
                "evidence_span_ids": support,
                "alternative_explanations": ["受控替代解释"],
                "research_question": "受控研究问题？",
                "feasible_method": {"design": "受控设计", "data": "受控数据", "analysis": "受控分析", "unit_of_analysis": "用户", "context": "受控情境"},
                "counterevidence": [{"statement": "受控反证", "evidence_span_ids": counter}],
                "innovation_candidates": ["受控创新点"],
            }
            if self.mode == "single_paper_support":
                candidate["evidence_span_ids"] = support[:1]
            if self.mode == "fabricated_paper":
                candidate["evidence_span_ids"] = support
                candidate["counterevidence"] = [{"statement": "受控反证", "evidence_span_ids": counter + ["span_nonexistent"]}]
            return json.loads(json.dumps({"candidates": [candidate]}, ensure_ascii=False)), {"model": "controlled"}
        if "空白候选裁判" in system:
            if self.mode == "judge_none":
                return {"selections": []}, {"model": "controlled"}
            ids = [c["selection_id"] for c in payload["candidates"][:1]]
            return json.loads(json.dumps({"selections": [{"selection_id": i, "reason": "受控"} for i in ids]}, ensure_ascii=False)), {"model": "controlled"}
        return {}, {"model": "controlled"}


def run_case(name: str, papers, mode: str = "honest", p1: bool = True) -> dict:
    client = ControlledGapClient(mode)
    provider = DeepSeekResearchSynthesisProvider(client)
    result = provider.synthesize(SynthesisRequest(
        research_direction="platform governance", fine_grained_question=None,
        derived_path="top_five_subdirections", papers=tuple(papers), p1_precision_gate_passed=p1,
    ))
    formal = result.formal_gaps
    trace = {
        "case": name,
        "mode": mode,
        "status": result.status,
        "paper_count": len(papers),
        "subdirection_count": len(result.top_subdirections),
        "formal_gap_count": len(formal),
        "claim_count": len(result.claim_store.get("claims", [])),
        "anchor_violations": sum(
            1 for gap in formal
            if len(gap.get("supporting_paper_ids", [])) < 2 or not gap.get("counterevidence_claim_ids")
        ),
        "fabrication_signals": sum(1 for gap in formal if not gap.get("formal")),
        "limitations": result.limitations,
        "gap_audit": result.audit.get("gap_candidates", {}).get("formalization", {}),
        "matrix": result.audit.get("gap_candidates", {}).get("evidence_matrix", {}),
        "model_calls": client.calls,
    }
    return trace


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fixed = run_case("fixed_qualified_35", [paper(i) for i in range(1, 36)])
    holdout = run_case("heldout_every_4th_removed", [paper(i) for i in range(1, 36) if i % 4 != 0])
    regression_p0 = run_case("regression_title_only_27", [paper(i, abstract=False, count=27) for i in range(1, 28)])
    regression_gate = run_case("regression_p1_blocked", [paper(i) for i in range(1, 36)], p1=False)
    challenge_forge = run_case("challenge_forged_support_span", [paper(i) for i in range(1, 36)], mode="forge_span")
    challenge_single = run_case("challenge_single_paper_support", [paper(i) for i in range(1, 36)], mode="single_paper_support")
    challenge_none = run_case("challenge_judge_selects_none", [paper(i) for i in range(1, 36)], mode="judge_none")
    challenge_fab = run_case("challenge_fabricated_counterevidence_span", [paper(i) for i in range(1, 36)], mode="fabricated_paper")

    sets = {
        "fixed": [fixed],
        "heldout_similar": [holdout],
        "regression": [regression_p0, regression_gate],
        "challenge": [challenge_forge, challenge_single, challenge_none, challenge_fab],
    }
    for set_name, traces in sets.items():
        (OUT_DIR / f"p3_{set_name}_traces.json").write_text(
            json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gates = {
        "fixed_produces_formal_gaps_with_full_anchors": fixed["formal_gap_count"] >= 1 and fixed["anchor_violations"] == 0,
        "holdout_still_formal": holdout["formal_gap_count"] >= 1 and holdout["anchor_violations"] == 0,
        "title_only_blocked": regression_p0["formal_gap_count"] == 0 and "SYNTHESIS" in regression_p0["status"],
        "p1_gate_blocks": regression_gate["status"] == "P2_BLOCKED_BY_P1_PRECISION",
        "forged_span_rejected": challenge_forge["formal_gap_count"] == 0,
        "single_paper_rejected": challenge_single["formal_gap_count"] == 0,
        "judge_none_yields_no_gaps": challenge_none["formal_gap_count"] == 0,
        "fabricated_counter_rejected": challenge_fab["formal_gap_count"] == 0,
        "no_fabrication_anywhere": all(t["fabrication_signals"] == 0 for traces in sets.values() for t in traces),
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "p3-athlete-judge-gap-candidates-1.0.0",
        "offline_note": "受控模型桩离线评测；真实模型验收另行执行（8766实例）。",
        "sets": {k: [t["case"] for t in v] for k, v in sets.items()},
        "summary": {t["case"]: {"formal_gaps": t["formal_gap_count"], "status": t["status"]} for v in sets.values() for t in v},
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }
    (OUT_DIR / "p3_four_set_eval.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=1))
    print("all_gates_passed:", report["all_gates_passed"])
    return 0 if report["all_gates_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
