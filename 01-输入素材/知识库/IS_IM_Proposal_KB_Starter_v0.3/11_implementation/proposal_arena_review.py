"""Athlete A/B + blind-judge quality review for high-risk proposal sections.

Reviewers only SCORE and FLAG; they must never rewrite content. Any attempt to
smuggle replacement text ("suggested_text"/"content") invalidates the review.
High-risk section selection is deterministic; the model never chooses scope.
"""
from __future__ import annotations

import json

PROPOSAL_ARENA_VERSION = "p4-athlete-judge-review-1.0.0"
BASE_HIGH_RISK_SECTIONS = ("literature_status", "theoretical_framework", "research_design")
MIN_CITATIONS_BEFORE_RISK = 2
SCORE_MIN, SCORE_MAX = 0, 10

REVIEWER_A_SYSTEM = """你是开题报告评审员A（证据锚定视角）。针对给出的章节内容与引用信息，只评估：
1) 事实性论断是否都有Claim支持（evidence_grounding）；
2) 是否引入了证据边界之外的断言（overreach）。
输出JSON对象，格式为：
{"reviews":[{"section_id":"research_design","score":0到10整数,"issues":["具体问题"]}],"overall":{"score":0到10整数,"summary":"一句话总评"}}
硬性规则：只评审给出的章节；不得输出改写文本、建议正文或paper_ids；score必须是0到10的整数。"""

REVIEWER_B_SYSTEM = """你是开题报告评审员B（逻辑与设计视角）。针对给出的章节内容与研究设计蓝图，只评估：
1) 章节之间与蓝图的一致性（coherence）；
2) 研究问题—理论—方法—数据链条是否闭合（design_soundness）。
输出JSON对象，格式为：
{"reviews":[{"section_id":"research_design","score":0到10整数,"issues":["具体问题"]}],"overall":{"score":0到10整数,"summary":"一句话总评"}}
硬性规则：只评审给出的章节；不得输出改写文本、建议正文或paper_ids；score必须是0到10的整数。"""

JUDGE_SYSTEM = """你是开题报告评审裁判。依据章节内容与两份匿名评审（candidate_1与candidate_2，来源未知），对每个高风险章节和总体给出最终裁决。
输出JSON对象，格式为：
{"verdicts":[{"section_id":"research_design","verdict":"pass或revise","final_score":0到10整数,"reason":"一句话理由"}],"overall":{"verdict":"pass或revise","score":0到10整数,"reason":"一句话理由"}}
硬性规则：verdict只能是pass或revise；不得改写评审或正文；不得输出paper_ids；final_score必须是0到10的整数。"""


def select_high_risk_sections(sections: list[dict]) -> list[str]:
    """Deterministic scope: fixed high-stakes sections + assumption/citation risk."""
    selected: list[str] = []
    for section in sections:
        section_id = str(section.get("section_id") or "")
        citations = section.get("citations") or []
        assumptions = section.get("assumptions") or []
        risky = (
            section_id in BASE_HIGH_RISK_SECTIONS
            or bool(assumptions)
            or len(citations) < MIN_CITATIONS_BEFORE_RISK
        )
        if section_id and risky:
            selected.append(section_id)
    return list(dict.fromkeys(selected))


def _valid_score(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and SCORE_MIN <= float(value) <= SCORE_MAX


def _no_smuggling(raw: object) -> bool:
    return not any(key in json.dumps(raw, ensure_ascii=False) for key in ("suggested_text", "rewritten", "replacement"))


def _validated_reviews(raw: object, scope: set[str]) -> dict[str, dict]:
    if not _no_smuggling(raw):
        raise ValueError("reviewer_must_not_rewrite_content")
    reviews = raw.get("reviews", []) if isinstance(raw, dict) else []
    by_id: dict[str, dict] = {}
    for row in reviews:
        if not isinstance(row, dict):
            continue
        section_id = str(row.get("section_id") or "")
        if section_id not in scope or section_id in by_id:
            continue
        if not _valid_score(row.get("score")):
            continue
        issues = [str(v).strip() for v in row.get("issues", []) if str(v).strip()][:5]
        by_id[section_id] = {"score": int(float(row["score"])), "issues": issues}
    if set(by_id) != scope:
        raise ValueError("reviewer_must_score_every_scoped_section_exactly_once")
    overall = raw.get("overall") if isinstance(raw.get("overall"), dict) else {}
    if not _valid_score(overall.get("score")):
        raise ValueError("reviewer_overall_score_invalid")
    return {**by_id, "__overall__": {"score": int(float(overall["score"])), "summary": str(overall.get("summary") or "").strip()}}


class ProposalArenaReviewer:
    def __init__(self, client):
        self.client = client

    def review(self, blueprint_rq: str, sections: list[dict]) -> dict:
        scope_ids = select_high_risk_sections(sections)
        if not scope_ids:
            return {"version": PROPOSAL_ARENA_VERSION, "scope": [], "note": "no_high_risk_sections"}
        scope = set(scope_ids)
        payload_rows = [
            {
                "section_id": section.get("section_id"),
                "title": section.get("title"),
                "content": str(section.get("content") or "")[:2000],
                "citation_count": len(section.get("citations") or []),
                "assumption_count": len(section.get("assumptions") or []),
            }
            for section in sections
            if section.get("section_id") in scope
        ]
        payload = json.dumps({
            "task": "只评审，不改写",
            "research_question": blueprint_rq,
            "sections": payload_rows,
        }, ensure_ascii=False)
        reviews_a = _validated_reviews(self.client.complete(REVIEWER_A_SYSTEM, payload)[0], scope)
        reviews_b = _validated_reviews(self.client.complete(REVIEWER_B_SYSTEM, payload)[0], scope)

        judge_payload = json.dumps({
            "task": "盲评仲裁",
            "research_question": blueprint_rq,
            "sections": payload_rows,
            "candidate_1": {key: value for key, value in reviews_a.items()},
            "candidate_2": {key: value for key, value in reviews_b.items()},
        }, ensure_ascii=False)
        raw_judge = self.client.complete(JUDGE_SYSTEM, judge_payload)[0]
        if not _no_smuggling(raw_judge):
            raise ValueError("judge_must_not_rewrite_content")
        verdict_rows = raw_judge.get("verdicts", []) if isinstance(raw_judge, dict) else []
        verdicts: dict[str, dict] = {}
        for row in verdict_rows:
            if not isinstance(row, dict):
                continue
            section_id = str(row.get("section_id") or "")
            if section_id not in scope or section_id in verdicts:
                continue
            if str(row.get("verdict") or "") not in {"pass", "revise"} or not _valid_score(row.get("final_score")):
                continue
            verdicts[section_id] = {
                "verdict": str(row["verdict"]), "final_score": int(float(row["final_score"])),
                "reason": str(row.get("reason") or "").strip(),
            }
        if set(verdicts) != scope:
            raise ValueError("judge_must_verdict_every_scoped_section_exactly_once")
        overall = raw_judge.get("overall") if isinstance(raw_judge.get("overall"), dict) else {}
        if str(overall.get("verdict") or "") not in {"pass", "revise"} or not _valid_score(overall.get("score")):
            raise ValueError("judge_overall_verdict_invalid")
        return {
            "version": PROPOSAL_ARENA_VERSION,
            "scope": scope_ids,
            "reviewer_a": reviews_a,
            "reviewer_b": reviews_b,
            "judge": {
                **verdicts,
                "__overall__": {
                    "verdict": str(overall["verdict"]), "score": int(float(overall["score"])),
                    "reason": str(overall.get("reason") or "").strip(),
                },
            },
            "revise_section_ids": [sid for sid in scope_ids if verdicts[sid]["verdict"] == "revise"],
            "overall_verdict": str(overall["verdict"]),
        }
