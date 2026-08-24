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


CONSTRAINT_ALIGNMENT_VERSION = "phase-e-constraint-alignment-1.2.0"
MIN_SECTION_WORD_RATIO = 0.4
MIN_CHECKABLE_TARGET_WORDS = 100
REPETITION_NGRAM = 8
REPETITION_FLAG_THRESHOLD = 0.10

_HUMAN_SUBJECT_TERMS = ("访谈", "采访", "被试", "interview", "焦点小组", "问卷发放")
_NEGATION_MARKERS = ("不", "未", "无", "没有", "无需", "并非", "不得", "排除", "避免")
_SECONDARY_SCOPE_QUALIFIERS = ("二手", "已发表", "公开报道", "secondary")
_SENTENCE_SPLIT = "。！？\n"


def _sentence_has_affirmative_human_subject_term(sentence: str) -> bool:
    """True when a human-subject term appears outside negation/secondary scope.

    否定句（如"不涉及人类被试"）与同句明确限定为二手来源的表述（如"访谈仅
    作为二手资料的可能来源"）不构成口径矛盾；只有未被否定且无二手限定的
    肯定式提及才算违约。
    """
    qualified = any(marker in sentence for marker in _SECONDARY_SCOPE_QUALIFIERS)
    for term in _HUMAN_SUBJECT_TERMS:
        start = 0
        while True:
            index = sentence.find(term, start)
            if index < 0:
                break
            window = sentence[max(0, index - 8):index]
            if not any(marker in window for marker in _NEGATION_MARKERS) and not qualified:
                return True
            start = index + len(term)
    return False


def audit_constraint_alignment(
    user_constraints: dict,
    outline: dict,
    sections: list[dict],
    today: str = "",
) -> dict:
    """Deterministic post-generation check of the rubric's hard findings.

    Catches what structural audits cannot: timeline beyond the confirmed
    deadline or backdated before today, ignored per-section word budgets, and
    data-scope statements that contradict the confirmed ethics/data constraints.
    """
    from datetime import date as _date
    import re as _re

    errors: list[str] = []
    section_map = {str(s.get("section_id") or ""): s for s in sections}
    deadline = str(user_constraints.get("deadline") or "")
    today_value = _date.fromisoformat(today) if today else _date.today()

    # 1a) timeline 终点不得晚于确认截止日：显式年份与时长双查。
    timeline_text = str(section_map.get("timeline", {}).get("content") or "")
    if deadline:
        try:
            deadline_year = int(deadline[:4])
        except ValueError:
            deadline_year = None
        if deadline_year is not None:
            for year in {int(v) for v in _re.findall(r"(20\d{2})", timeline_text)}:
                if year > deadline_year:
                    errors.append(f"timeline_year_{year}_beyond_deadline_{deadline_year}")
            months_left = max(0, (_date.fromisoformat(deadline) - today_value).days // 30)
            for months in (int(v) for v in _re.findall(r"(?<!年)(\d{1,2})\s*个月", timeline_text)):
                if months_left <= 24 and months > months_left:
                    errors.append(f"timeline_duration_{months}m_exceeds_{months_left}m_to_deadline")

    # 1a-2) timeline 起点不得回溯到今天之前：防止模型把启动日期写进过去来
    # 拉长总周期（如"自2025年1月启动"绕过剩余时长检查）。
    for match in _re.finditer(r"(20\d{2})年(\d{1,2})月", timeline_text):
        start_year, start_month = int(match.group(1)), int(match.group(2))
        if (start_year, start_month) < (today_value.year, today_value.month):
            errors.append(
                f"timeline_start_{start_year}-{start_month:02d}_before_today_"
                f"{today_value.year}-{today_value.month:02d}"
            )
            break

    # 1b) 各节字数不低于提纲分配的 MIN_SECTION_WORD_RATIO。
    for spec in outline.get("sections", []):
        target = int(spec.get("target_words") or 0)
        if target < MIN_CHECKABLE_TARGET_WORDS:
            continue
        content = str(section_map.get(spec.get("section_id"), {}).get("content") or "")
        if len(content) < target * MIN_SECTION_WORD_RATIO:
            errors.append(f"{spec.get('section_id')}:words_{len(content)}_below_{int(target * MIN_SECTION_WORD_RATIO)}")

    # 1c) 数据口径：约束声明纯公开/二手且不含人类被试时，正文不得出现未被
    # 否定且无二手限定的访谈类肯定式表述（否定句不计入违约）。
    data_scope = f"{user_constraints.get('data_access', '')}{user_constraints.get('ethics_privacy', '')}"
    scope_declares_public_only = ("公开" in data_scope or "二手" in data_scope) and ("不涉及人类被试" in data_scope or "不涉及" in data_scope)
    scope_allows_interview = "访谈" in data_scope or "interview" in data_scope.lower()
    if scope_declares_public_only and not scope_allows_interview:
        for section_id, section in section_map.items():
            content = str(section.get("content") or "")
            sentences = [s for s in _re.split(f"[{_re.escape(_SENTENCE_SPLIT)}]", content) if s]
            if any(_sentence_has_affirmative_human_subject_term(s) for s in sentences):
                errors.append(f"{section_id}:human_subject_term_contradicts_public_only_scope")

    return {
        "version": CONSTRAINT_ALIGNMENT_VERSION,
        "valid": not errors,
        "errors": errors,
        "checks": ["timeline_vs_deadline", "timeline_start_not_before_today", "section_words_vs_outline", "data_scope_consistency"],
    }


def cross_section_repetition(sections: list[dict]) -> dict:
    """Advisory duplication metric: shared 8-gram occurrence rate across sections."""
    import re as _re

    from collections import Counter

    section_grams: dict[str, Counter] = {}
    total = 0
    for section in sections:
        text = str(section.get("content") or "")
        grams = ["".join(tokens) for tokens in _re.findall(r"([\u4e00-\u9fff]|[a-z0-9]+)", text.casefold())]
        ngrams = Counter(tuple(grams[i:i + REPETITION_NGRAM]) for i in range(max(0, len(grams) - REPETITION_NGRAM + 1)))
        section_grams[str(section.get("section_id") or "")] = ngrams
        total += sum(ngrams.values())
    if total == 0:
        return {"rate": 0.0, "flagged": False, "threshold": REPETITION_FLAG_THRESHOLD}
    owner: dict[tuple, set] = {}
    for section_id, ngrams in section_grams.items():
        for gram in ngrams:
            owner.setdefault(gram, set()).add(section_id)
    shared = {gram for gram, ids in owner.items() if len(ids) > 1}
    shared_occurrences = sum(ngrams[gram] for ngrams in section_grams.values() for gram in shared if gram in ngrams)
    rate = round(shared_occurrences / total, 4)
    return {
        "rate": rate,
        "flagged": rate > REPETITION_FLAG_THRESHOLD,
        "threshold": REPETITION_FLAG_THRESHOLD,
        "method": f"shared_{REPETITION_NGRAM}gram_occurrence_rate",
    }
