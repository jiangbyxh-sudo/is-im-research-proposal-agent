"""Five-run synthesis stability and proposal/guidance baseline on one fixed corpus."""
from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from evaluation.rubrics import (
    GUIDANCE_RUBRIC,
    GUIDANCE_RUBRIC_VERSION,
    PROPOSAL_RUBRIC,
    PROPOSAL_RUBRIC_VERSION,
    blank_human_scorecard,
)
from observability.trace import utc_now, write_trace
from proposal_generation_provider import ProposalRequest
from research_synthesis_provider import SynthesisRequest


IMPLEMENTATION_DIR = Path(__file__).resolve().parent.parent
KB_ROOT = IMPLEMENTATION_DIR.parent
WORKSPACE = KB_ROOT.parents[2]
DEFAULT_REPORT_ROOT = WORKSPACE / "02-任务/01-current/T02-V0实现与结果报告/验收证据/P0-质量基线"


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _comb2(value: int) -> float:
    return (value * (value - 1)) / 2


def adjusted_rand_index(first: dict[str, str], second: dict[str, str]) -> float | None:
    paper_ids = sorted(set(first) & set(second))
    if len(paper_ids) < 2:
        return None
    contingency = Counter((first[paper_id], second[paper_id]) for paper_id in paper_ids)
    first_counts = Counter(first[paper_id] for paper_id in paper_ids)
    second_counts = Counter(second[paper_id] for paper_id in paper_ids)
    pair_count = _comb2(len(paper_ids))
    if not pair_count:
        return None
    sum_comb = sum(_comb2(value) for value in contingency.values())
    first_comb = sum(_comb2(value) for value in first_counts.values())
    second_comb = sum(_comb2(value) for value in second_counts.values())
    expected = (first_comb * second_comb) / pair_count
    maximum = 0.5 * (first_comb + second_comb)
    denominator = maximum - expected
    if denominator == 0:
        return 1.0
    return round((sum_comb - expected) / denominator, 4)


def _assignments(result: dict) -> dict[str, str]:
    assignments = {}
    for direction in result.get("top_subdirections", []):
        cluster_id = str(direction.get("subdirection_id"))
        for paper_id in direction.get("paper_ids", []):
            assignments[str(paper_id)] = cluster_id
    return assignments


def _clusters(result: dict) -> list[set[str]]:
    return [set(map(str, item.get("paper_ids", []))) for item in result.get("top_subdirections", [])]


def representative_jaccard(first: dict, second: dict) -> float | None:
    left = _clusters(first)
    right = _clusters(second)
    if not left or not right:
        return None
    candidates = []
    for left_index, left_set in enumerate(left):
        for right_index, right_set in enumerate(right):
            union = left_set | right_set
            score = len(left_set & right_set) / len(union) if union else 1.0
            candidates.append((score, left_index, right_index))
    used_left = set()
    used_right = set()
    matched = []
    for score, left_index, right_index in sorted(candidates, reverse=True):
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        matched.append(score)
    denominator = max(len(left), len(right))
    matched.extend([0.0] * (denominator - len(matched)))
    return round(statistics.mean(matched), 4) if matched else None


def _serialize_synthesis(result) -> dict:
    return {
        "status": result.status,
        "top_subdirections": result.top_subdirections,
        "gap_candidates": result.gap_candidates,
        "limitations": result.limitations,
        "audit": result.audit,
        "message_to_user": result.message_to_user,
    }


def _serialize_proposal(result) -> dict:
    return {
        "status": result.status,
        "proposal": result.proposal,
        "writing_guidance": result.writing_guidance,
        "proposal_context": result.proposal_context,
        "limitations": result.limitations,
        "audit": result.audit,
        "message_to_user": result.message_to_user,
    }


def run_model_baseline(synthesis_provider, proposal_provider, report_root: Path = DEFAULT_REPORT_ROOT) -> dict:
    report_root = report_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = report_root / "fixed_corpus_snapshot.json"
    if not snapshot_path.is_file():
        raise FileNotFoundError("P0 fixed corpus snapshot is missing; run 61-direction coverage first")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    papers = tuple(snapshot.get("papers", []))
    if len(papers) < 5:
        raise ValueError("P0 fixed corpus contains fewer than five papers")
    request = SynthesisRequest(
        research_direction=snapshot["research_direction"],
        fine_grained_question=None,
        derived_path="top_five_subdirections",
        papers=papers,
    )
    run_outputs = []
    trace_ids = []
    for run_index in range(1, 6):
        started_at = utc_now()
        started = time.monotonic()
        result = synthesis_provider.synthesize(request)
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        serialized = _serialize_synthesis(result)
        output_hash = _hash({
            "directions": serialized["top_subdirections"],
            "gaps": serialized["gap_candidates"],
        })
        run_output = {
            "run_index": run_index,
            "status": result.status,
            "duration_ms": duration_ms,
            "output_hash": output_hash,
            **serialized,
        }
        run_outputs.append(run_output)
        trace_id, _ = write_trace(report_root / "traces/stability", f"FIX-STABILITY-001-RUN-{run_index}", {
            "stage": "P0_BASELINE_NOT_A_FIX",
            "started_at": started_at,
            "completed_at": utc_now(),
            "duration_ms": duration_ms,
            "input": {
                "direction_id": snapshot["direction_id"],
                "research_direction": snapshot["research_direction"],
                "corpus_hash": snapshot["corpus_hash"],
                "paper_count": len(papers),
            },
            "versions": {
                "synthesis_prompt": result.audit.get("prompt_version"),
                "model": result.audit.get("model", {}).get("model"),
                "rubric": None,
                "clustering": "not_implemented_model_free_grouping",
            },
            "query_plan": None,
            "candidate_counts": {"fixed_corpus": len(papers)},
            "corpus_hash": snapshot["corpus_hash"],
            "clustering": {
                "algorithm": "single_llm_free_grouping",
                "random_seed": None,
                "output_assignments": _assignments(serialized),
            },
            "model": {
                "single_provider_degraded": True,
                "athlete_a": serialized,
                "athlete_b": None,
                "judge": None,
                "usage": result.audit.get("model", {}).get("usage", {}),
                "cost": None,
            },
            "status": result.status,
            "errors": result.limitations if result.status == "SYNTHESIS_FAILED" else [],
            "missing_trace_fields": [
                "second_independent_athlete_not_implemented",
                "judge_not_implemented",
                "deterministic_clustering_not_implemented",
                "provider_cost_not_configured",
            ],
        })
        trace_ids.append(trace_id)

    valid = [item for item in run_outputs if item["status"] in {"SYNTHESIS_COMPLETE", "SYNTHESIS_PARTIAL"}]
    hashes = Counter(item["output_hash"] for item in valid)
    baseline = valid[0] if valid else None
    ari_values = []
    jaccard_values = []
    if baseline:
        base_assignments = _assignments(baseline)
        for item in valid[1:]:
            ari = adjusted_rand_index(base_assignments, _assignments(item))
            jaccard = representative_jaccard(baseline, item)
            if ari is not None:
                ari_values.append(ari)
            if jaccard is not None:
                jaccard_values.append(jaccard)
    stability = {
        "case_id": "FIX-STABILITY-001",
        "requested_runs": 5,
        "completed_runs": len(run_outputs),
        "valid_runs": len(valid),
        "exact_output_consistency": round(max(hashes.values()) / len(valid), 4) if valid else 0.0,
        "ari_against_first": ari_values,
        "mean_ari": round(statistics.mean(ari_values), 4) if ari_values else None,
        "representative_jaccard_against_first": jaccard_values,
        "mean_representative_jaccard": round(statistics.mean(jaccard_values), 4) if jaccard_values else None,
        "direction_counts": [len(item["top_subdirections"]) for item in run_outputs],
        "gap_counts": [len(item["gap_candidates"]) for item in run_outputs],
        "trace_ids": trace_ids,
        "assessment": "BASELINE_ONLY_NOT_FIXED",
    }

    proposal_output = None
    proposal_trace_id = None
    if baseline and baseline.get("gap_candidates"):
        selected_gap = baseline["gap_candidates"][0]
        innovations = selected_gap.get("innovation_candidates", [])
        if innovations:
            proposal_request = ProposalRequest(
                research_direction=snapshot["research_direction"],
                fine_grained_question=None,
                selected_gap=selected_gap,
                selected_innovation_id=f"{selected_gap['gap_id']}_innovation_1",
                selected_innovation=str(innovations[0]),
                papers=papers,
            )
            started_at = utc_now()
            started = time.monotonic()
            proposal_result = proposal_provider.generate(proposal_request)
            duration_ms = round((time.monotonic() - started) * 1000, 2)
            proposal_output = {"duration_ms": duration_ms, **_serialize_proposal(proposal_result)}
            proposal_trace_id, _ = write_trace(report_root / "traces/proposal", "FIX-PROPOSAL-001", {
                "stage": "P0_BASELINE_NOT_A_FIX",
                "started_at": started_at,
                "completed_at": utc_now(),
                "duration_ms": duration_ms,
                "input": {
                    "direction_id": snapshot["direction_id"],
                    "research_direction": snapshot["research_direction"],
                    "corpus_hash": snapshot["corpus_hash"],
                    "selected_gap": selected_gap,
                    "selected_innovation": innovations[0],
                },
                "versions": {
                    "proposal_prompt": proposal_result.audit.get("prompt_version"),
                    "proposal_rubric": PROPOSAL_RUBRIC_VERSION,
                    "guidance_rubric": GUIDANCE_RUBRIC_VERSION,
                    "model": proposal_result.audit.get("model", {}).get("model"),
                },
                "model": {
                    "single_provider_degraded": True,
                    "output": proposal_output,
                    "usage": proposal_result.audit.get("model", {}).get("usage", {}),
                    "cost": None,
                },
                "human_rubric": "pending_manual_scoring",
                "status": proposal_result.status,
                "errors": proposal_result.limitations if proposal_result.status == "PROPOSAL_GENERATION_FAILED" else [],
                "missing_trace_fields": [
                    "sentence_level_claim_audit_not_implemented",
                    "cross_section_consistency_matrix_not_implemented",
                    "human_scores_pending",
                    "provider_cost_not_configured",
                ],
            })

    proposal_scorecard = blank_human_scorecard(PROPOSAL_RUBRIC, evaluator="Coding Agent manual review pending")
    proposal_scorecard.update({
        "rubric_version": PROPOSAL_RUBRIC_VERSION,
        "case_id": "FIX-PROPOSAL-001",
        "trace_id": proposal_trace_id,
    })
    guidance_scorecard = blank_human_scorecard(GUIDANCE_RUBRIC, evaluator="Coding Agent manual review pending")
    guidance_scorecard.update({
        "rubric_version": GUIDANCE_RUBRIC_VERSION,
        "case_id": "FIX-GUIDANCE-001",
        "trace_id": proposal_trace_id,
    })
    (report_root / "开题人工Rubric评分.json").write_text(
        json.dumps(proposal_scorecard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (report_root / "写作指导项目针对性Rubric评分.json").write_text(
        json.dumps(guidance_scorecard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    output = {
        "baseline_version": "p0-model-baseline-1.0.0",
        "stage": "P0_BASELINE_NOT_A_FIX",
        "snapshot": {
            "path": str(snapshot_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "corpus_hash": snapshot["corpus_hash"],
            "paper_count": len(papers),
        },
        "stability": stability,
        "proposal_trace_id": proposal_trace_id,
        "proposal_generated": proposal_output is not None,
        "proposal_output": proposal_output,
        "rubric_status": "PENDING_MANUAL_SCORING",
    }
    (report_root / "model_baseline_raw.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "status": "P0_MODEL_BASELINE_RECORDED",
        "stability": stability,
        "proposal_generated": proposal_output is not None,
        "rubric_status": "PENDING_MANUAL_SCORING",
    }
