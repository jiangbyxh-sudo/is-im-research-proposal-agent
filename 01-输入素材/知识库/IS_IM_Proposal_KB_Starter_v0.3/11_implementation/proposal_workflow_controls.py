"""Deterministic Phase E controls for user constraints, outlines, and task cards."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


PROPOSAL_WORKFLOW_CONTROL_VERSION = "phase-e-workflow-controls-1.0.0"
MIN_TARGET_WORDS = 2_000
MAX_TARGET_WORDS = 100_000

CONSTRAINT_FIELDS = (
    ("degree_level", "学位与培养层次", "请先说明学位与培养层次，例如本科、硕士或博士。"),
    ("institution_template", "学校模板要求", "请说明学校模板要求；如无指定模板，请明确填写“无指定模板”。"),
    ("output_language", "写作语言", "请确认开题报告使用中文、英文或双语。"),
    ("target_word_count", "目标篇幅", "请给出开题报告目标字数。"),
    ("deadline", "截止时间", "请确认开题报告截止时间。"),
    ("data_access", "数据权限", "请说明当前可合法获得的数据、样本或访问权限。"),
    ("method_constraints", "方法限制", "请说明必须采用或不能采用的方法；如无，请明确填写“无”。"),
    ("research_context", "研究情境", "请确认研究发生的组织、平台、行业或用户情境。"),
    ("ethics_privacy", "伦理与隐私", "请说明伦理审批、知情同意、隐私或敏感数据约束。"),
    ("tool_capabilities", "工具能力", "请说明当前可使用的软件、编程、统计或实验工具。"),
)


@dataclass(frozen=True)
class ConstraintEvaluation:
    complete: bool
    normalized: dict
    constraint_hash: str
    missing_field: str | None = None
    next_question: str | None = None
    error: str | None = None


def _clean(value: object, limit: int = 2_000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:limit]


def evaluate_user_constraints(raw: object) -> ConstraintEvaluation:
    payload = raw if isinstance(raw, dict) else {}
    normalized = {}
    for field_id, _, question in CONSTRAINT_FIELDS:
        value = payload.get(field_id)
        if field_id == "target_word_count":
            if value in (None, ""):
                return ConstraintEvaluation(False, normalized, "", field_id, question)
            if isinstance(value, bool):
                return ConstraintEvaluation(False, normalized, "", field_id, question, "target_word_count_invalid")
            try:
                word_count = int(value)
            except (TypeError, ValueError):
                return ConstraintEvaluation(False, normalized, "", field_id, question, "target_word_count_invalid")
            if not MIN_TARGET_WORDS <= word_count <= MAX_TARGET_WORDS:
                return ConstraintEvaluation(
                    False, normalized, "", field_id,
                    f"目标字数须在{MIN_TARGET_WORDS}至{MAX_TARGET_WORDS}之间，请重新确认。",
                    "target_word_count_out_of_bounds",
                )
            normalized[field_id] = word_count
            continue
        cleaned = _clean(value)
        if not cleaned:
            return ConstraintEvaluation(False, normalized, "", field_id, question)
        normalized[field_id] = cleaned
    serialized = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    constraint_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return ConstraintEvaluation(True, normalized, constraint_hash)


SECTION_WEIGHTS = {
    "working_title": 0,
    "background": 13,
    "concepts": 8,
    "literature_status": 16,
    "selected_gap": 9,
    "research_questions": 7,
    "theoretical_framework": 11,
    "research_design": 17,
    "contributions": 8,
    "feasibility_ethics": 7,
    "timeline": 4,
}


def build_proposal_outline(blueprint: dict, section_specs: tuple[tuple[str, str], ...]) -> dict:
    target_words = int(blueprint["target_word_count"])
    sections = []
    allocated = 0
    for index, (section_id, title) in enumerate(section_specs):
        section_words = round(target_words * SECTION_WEIGHTS[section_id] / 100)
        allocated += section_words
        sections.append({
            "sequence": index + 1,
            "section_id": section_id,
            "title": title,
            "purpose": f"在已确认研究设计与Claim Store边界内完成“{title}”",
            "target_words": section_words,
            "allowed_claim_ids": list(blueprint["claim_ids"]),
            "required_blueprint_refs": [
                "blueprint_id", "research_question", "design", "outline_id", "constraint_hash",
            ],
        })
    if sections:
        sections[-1]["target_words"] += target_words - allocated
    seed = json.dumps(
        {"blueprint_id": blueprint["blueprint_id"], "sections": sections},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    outline_id = "outline_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
    return {
        "version": PROPOSAL_WORKFLOW_CONTROL_VERSION,
        "outline_id": outline_id,
        "blueprint_id": blueprint["blueprint_id"],
        "constraint_hash": blueprint["constraint_hash"],
        "target_word_count": target_words,
        "sections": sections,
    }


def proposal_outline_matches(expected: dict, supplied: object) -> bool:
    return isinstance(supplied, dict) and supplied == expected


def build_execution_task_cards(blueprint: dict, outline: dict, claim_store: dict) -> dict:
    known_claims = {
        str(item.get("claim_id")) for item in claim_store.get("claims", []) if item.get("claim_id")
    }
    cards = []
    previous_card_id = None
    for section in outline["sections"]:
        seed = f"{outline['outline_id']}|{section['sequence']}|{section['section_id']}"
        card_id = "task_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        allowed = [claim_id for claim_id in section["allowed_claim_ids"] if claim_id in known_claims]
        cards.append({
            "task_card_id": card_id,
            "sequence": section["sequence"],
            "section_id": section["section_id"],
            "title": section["title"],
            "status": "PENDING_HUMAN_EXECUTION",
            "objective": section["purpose"],
            "prerequisite_task_card_ids": [previous_card_id] if previous_card_id else [],
            "controlled_inputs": {
                "blueprint_id": blueprint["blueprint_id"],
                "outline_id": outline["outline_id"],
                "constraint_hash": blueprint["constraint_hash"],
                "allowed_claim_ids": allowed,
            },
            "target_words": section["target_words"],
            "done_when": [
                "所有事实性论断均绑定允许的claim_id",
                "引用包含claim_id、paper_id与evidence_span",
                "内容与已确认蓝图和用户约束一致",
                "人工完成本节审阅",
            ],
        })
        previous_card_id = card_id
    errors = []
    if len(cards) != len(outline["sections"]):
        errors.append("task_card_count_mismatch")
    if len({item["task_card_id"] for item in cards}) != len(cards):
        errors.append("duplicate_task_card_id")
    for card in cards:
        unknown = set(card["controlled_inputs"]["allowed_claim_ids"]) - known_claims
        if unknown:
            errors.append(f"{card['task_card_id']}:unknown_claim_ids")
    return {
        "version": PROPOSAL_WORKFLOW_CONTROL_VERSION,
        "blueprint_id": blueprint["blueprint_id"],
        "outline_id": outline["outline_id"],
        "cards": cards,
        "audit": {
            "valid": not errors,
            "task_card_count": len(cards),
            "errors": errors,
            "claim_store_only": True,
        },
    }
