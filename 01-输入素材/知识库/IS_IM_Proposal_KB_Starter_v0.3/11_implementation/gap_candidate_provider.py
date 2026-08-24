"""Athlete A/B gap-candidate proposals with a blind judge, span-anchored.

The model only PROPOSES: every evidence_span_ids value must come from the
exact span pool supplied for the cluster, and the deterministic formalizer
(research_gap_provider) re-validates everything before a gap becomes formal.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol


GAP_CANDIDATE_VERSION = "p3-athlete-judge-gap-candidates-1.0.0"
MAX_CANDIDATES_PER_ATHLETE = 2
MAX_SELECTED_PER_CLUSTER = 2
MAX_SPANS_PER_CLUSTER_PROMPT = 40

ATHLETE_A_SYSTEM = """你是研究空白候选选手A（机会导向）。基于给出的句级证据（span_id与原文句子），为该研究方向提出最有价值的研究空白候选。
风格要求：识别证据中反复出现但未被解释的机会、未覆盖的情境或未检验的机制。
输出JSON对象，格式为：
{"candidates":[{
  "gap_statement":"空白陈述",
  "why_it_matters":"重要性",
  "evidence_span_ids":["span_xxx"],
  "alternative_explanations":["替代解释"],
  "research_question":"可检验研究问题",
  "feasible_method":{"design":"研究设计","data":"数据","analysis":"分析方法","unit_of_analysis":"分析单位","context":"研究情境"},
  "counterevidence":[{"statement":"相反或边界证据陈述","evidence_span_ids":["span_xxx"]}],
  "innovation_candidates":["创新点1","创新点2"]
}]}
硬性规则：evidence_span_ids只能使用输入中给出的span_id，不得编造；支持证据至少来自两篇不同论文；counterevidence至少一行且其span真实存在；最多提出2个候选。"""

ATHLETE_B_SYSTEM = """你是研究空白候选选手B（矛盾与边界导向）。基于给出的句级证据（span_id与原文句子），为该研究方向提出最有价值的研究空白候选。
风格要求：识别证据之间的矛盾、结果不一致、边界条件不明或理论冲突之处。
输出JSON对象，格式为：
{"candidates":[{
  "gap_statement":"空白陈述",
  "why_it_matters":"重要性",
  "evidence_span_ids":["span_xxx"],
  "alternative_explanations":["替代解释"],
  "research_question":"可检验研究问题",
  "feasible_method":{"design":"研究设计","data":"数据","analysis":"分析方法","unit_of_analysis":"分析单位","context":"研究情境"},
  "counterevidence":[{"statement":"相反或边界证据陈述","evidence_span_ids":["span_xxx"]}],
  "innovation_candidates":["创新点1","创新点2"]
}]}
硬性规则：evidence_span_ids只能使用输入中给出的span_id，不得编造；支持证据至少来自两篇不同论文；counterevidence至少一行且其span真实存在；最多提出2个候选。"""

JUDGE_SYSTEM = """你是研究空白候选裁判。依据给出的句级证据与匿名候选（candidate_1..candidate_N，来源未知），选出最多2个最值得进入确定性证据核验的候选：证据锚定真实、空白表述可检验、方法可行。
输出JSON对象，格式为：
{"selections":[{"selection_id":"candidate_2","reason":"一句话理由"}]}
硬性规则：selection_id必须是给出的候选编号；最多选择2个；不得改写候选内容；若所有候选质量都不足，返回空selections。"""


@dataclass(frozen=True)
class GapCandidateRequest:
    research_direction: str
    cluster_id: str
    cluster_name: str
    feature_terms: tuple[str, ...]
    papers: tuple[dict, ...]
    spans: tuple[dict, ...]  # [{"span_id", "paper_id", "text", "evidence_level"}]


class GapCandidateProvider(Protocol):
    def propose(self, request: GapCandidateRequest) -> tuple[list[dict], dict]: ...


def select_prompt_spans(spans: list[dict] | tuple[dict, ...], limit: int = MAX_SPANS_PER_CLUSTER_PROMPT) -> list[dict]:
    """Deterministic bounded span selection: round-robin across papers by paper_id."""
    by_paper: dict[str, list[dict]] = {}
    for span in sorted(spans, key=lambda item: (item["paper_id"], item["span_id"])):
        by_paper.setdefault(span["paper_id"], []).append(span)
    selected: list[dict] = []
    round_index = 0
    while len(selected) < limit:
        added = False
        for paper_id in sorted(by_paper):
            if round_index < len(by_paper[paper_id]):
                selected.append(by_paper[paper_id][round_index])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        round_index += 1
    return selected


def _anon_label(candidate: dict) -> str:
    digest = hashlib.sha256(str(candidate.get("gap_statement") or "").encode("utf-8")).hexdigest()[:12]
    return digest


def _validate_candidate(raw: object, allowed_span_ids: set[str]) -> dict | None:
    """Return a normalized candidate or None; span ids outside the pool are fatal."""
    if not isinstance(raw, dict):
        return None
    statement = str(raw.get("gap_statement") or "").strip()
    question = str(raw.get("research_question") or "").strip()
    alternatives = [str(v).strip() for v in raw.get("alternative_explanations", []) if str(v).strip()]
    method = raw.get("feasible_method") if isinstance(raw.get("feasible_method"), dict) else {}
    innovations = [str(v).strip() for v in raw.get("innovation_candidates", []) if str(v).strip()]
    span_ids = [str(v).strip() for v in raw.get("evidence_span_ids", []) if str(v).strip()]
    if not statement or not question or not alternatives or not innovations:
        return None
    if not all(str(method.get(key) or "").strip() for key in ("design", "data", "analysis")):
        return None
    if not span_ids or not set(span_ids).issubset(allowed_span_ids):
        return None
    counters = []
    for row in raw.get("counterevidence", []) if isinstance(raw.get("counterevidence"), list) else []:
        if not isinstance(row, dict):
            continue
        counter_statement = str(row.get("statement") or "").strip()
        counter_ids = [str(v).strip() for v in row.get("evidence_span_ids", []) if str(v).strip()]
        if counter_statement and counter_ids and set(counter_ids).issubset(allowed_span_ids):
            counters.append({"statement": counter_statement, "evidence_span_ids": counter_ids})
    if not counters:
        return None
    return {
        "gap_statement": statement,
        "why_it_matters": str(raw.get("why_it_matters") or "").strip(),
        "evidence_span_ids": sorted(set(span_ids)),
        "alternative_explanations": alternatives,
        "research_question": question,
        "feasible_method": {
            "design": str(method.get("design") or "").strip(),
            "data": str(method.get("data") or "").strip(),
            "analysis": str(method.get("analysis") or "").strip(),
            "unit_of_analysis": str(method.get("unit_of_analysis") or "").strip(),
            "context": str(method.get("context") or "").strip(),
        },
        "counterevidence": counters,
        "innovation_candidates": innovations,
    }


class LLMGapCandidateProvider:
    def __init__(self, client):
        self.client = client

    def propose(self, request: GapCandidateRequest) -> tuple[list[dict], dict]:
        spans = select_prompt_spans(request.spans)
        allowed = {span["span_id"] for span in spans}
        paper_titles = {paper.get("paper_id"): paper.get("title") for paper in request.papers}
        payload = {
            "task": "为固定研究簇提出空白候选（只提议，不裁决）",
            "research_direction": request.research_direction,
            "cluster": {
                "cluster_id": request.cluster_id,
                "name": request.cluster_name,
                "feature_terms": list(request.feature_terms),
                "paper_count": len(request.papers),
            },
            "evidence_spans": [
                {
                    "span_id": span["span_id"],
                    "paper_id": span["paper_id"],
                    "paper_title": paper_titles.get(span["paper_id"]),
                    "text": span["text"],
                }
                for span in spans
            ],
        }
        user_payload = json.dumps(payload, ensure_ascii=False)
        pool: list[dict] = []
        audits: dict[str, object] = {}
        for athlete, system in (("athlete_a", ATHLETE_A_SYSTEM), ("athlete_b", ATHLETE_B_SYSTEM)):
            raw, audit = self.client.complete(system, user_payload)
            audits[athlete] = audit
            candidates = raw.get("candidates", []) if isinstance(raw, dict) else []
            for item in candidates[:MAX_CANDIDATES_PER_ATHLETE]:
                validated = _validate_candidate(item, allowed)
                if validated is not None:
                    pool.append(validated)
        if not pool:
            return [], {"provider": "athlete_judge_gap_candidates", "version": GAP_CANDIDATE_VERSION,
                        "pool_size": 0, "athletes": audits, "note": "no_valid_candidate"}

        # Deterministic anonymization: order by content hash, not by athlete.
        ordered = sorted(pool, key=_anon_label)
        judge_payload = {
            "task": "盲评研究空白候选",
            "research_direction": request.research_direction,
            "cluster_name": request.cluster_name,
            "evidence_spans": payload["evidence_spans"],
            "candidates": [
                {"selection_id": f"candidate_{index + 1}", **candidate}
                for index, candidate in enumerate(ordered)
            ],
        }
        raw_judge, judge_audit = self.client.complete(JUDGE_SYSTEM, json.dumps(judge_payload, ensure_ascii=False))
        audits["judge"] = judge_audit
        selections = raw_judge.get("selections", []) if isinstance(raw_judge, dict) else []
        chosen_ids: list[str] = []
        reasons: dict[str, str] = {}
        for row in selections[:MAX_SELECTED_PER_CLUSTER]:
            if not isinstance(row, dict):
                continue
            selection_id = str(row.get("selection_id") or "").strip()
            if selection_id in {f"candidate_{index + 1}" for index in range(len(ordered))} and selection_id not in chosen_ids:
                chosen_ids.append(selection_id)
                reasons[selection_id] = str(row.get("reason") or "").strip()
        if not chosen_ids:
            return [], {"provider": "athlete_judge_gap_candidates", "version": GAP_CANDIDATE_VERSION,
                        "pool_size": len(pool), "athletes": audits, "judge_selections": [],
                        "note": "judge_selected_none"}
        index_by_id = {f"candidate_{index + 1}": index for index in range(len(ordered))}
        selected = [dict(ordered[index_by_id[selection_id]]) for selection_id in chosen_ids]
        for selection_id, candidate in zip(chosen_ids, selected):
            candidate["judge_reason"] = reasons.get(selection_id, "")
        return selected, {
            "provider": "athlete_judge_gap_candidates",
            "version": GAP_CANDIDATE_VERSION,
            "pool_size": len(pool),
            "selected_count": len(selected),
            "judge_selections": chosen_ids,
            "athletes": audits,
            "span_pool_size": len(allowed),
        }
