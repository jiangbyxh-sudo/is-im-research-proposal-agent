"""P4 controlled proposal workflow: blueprint, confirmation, then claim-bound sections."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol

from proposal_arena_review import PROPOSAL_ARENA_VERSION, ProposalArenaReviewer
from proposal_workflow_controls import (
    MIN_CHECKABLE_TARGET_WORDS,
    MIN_SECTION_WORD_RATIO,
    audit_constraint_alignment,
    build_execution_task_cards,
    build_proposal_outline,
    cross_section_repetition,
    evaluate_user_constraints,
    proposal_outline_matches,
)
from research_synthesis_provider import DeepSeekJsonClient


SECTION_SPECS = (
    ("working_title", "暂定题目"),
    ("background", "研究背景与问题重要性"),
    ("concepts", "概念界定"),
    ("literature_status", "国内外研究现状"),
    ("selected_gap", "已选研究空白及证据"),
    ("research_questions", "研究问题、假设或命题"),
    ("theoretical_framework", "理论框架与作用机制"),
    ("research_design", "研究设计、数据、测量与分析"),
    ("contributions", "预期理论、方法与实践贡献"),
    ("feasibility_ethics", "可行性、伦理、风险与替代方案"),
    ("timeline", "研究计划"),
)
GUIDANCE_STAGES = (
    ("topic", "选题"), ("introduction", "引言"), ("theory", "理论"),
    ("method", "方法"), ("results", "结果"), ("discussion", "讨论"), ("submission", "投稿"),
)
PARADIGM_LABELS = {
    "quantitative_archival_causal": "档案/面板数据与因果推断", "survey_sem": "问卷、测量与CFA/SEM",
    "experiment": "实验、在线实验与A/B测试", "qualitative_case_process": "定性案例、归纳理论与过程研究",
    "systematic_review_bibliometric": "系统综述、元分析与科学计量", "mixed_methods": "混合方法",
    "computational_text_network": "计算文本、机器学习与网络分析", "analytical_modeling": "分析建模、博弈论与机制设计",
    "design_science": "设计科学",
}
PROPOSAL_CONTROL_VERSION = "p4-controlled-proposal-1.3.0"


@dataclass(frozen=True)
class ResearchDesignBlueprint:
    blueprint_id: str
    research_direction: str
    gap_id: str
    research_question: str
    claim_ids: tuple[str, ...]
    paradigm_id: str
    unit_of_analysis: str
    context: str
    design: str
    data: str
    analysis: str
    section_ids: tuple[str, ...]
    constraint_hash: str
    degree_level: str
    institution_template: str
    output_language: str
    target_word_count: int
    deadline: str
    data_access: str
    method_constraints: str
    ethics_privacy: str
    tool_capabilities: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalRequest:
    research_direction: str
    fine_grained_question: str | None
    selected_gap: dict
    selected_innovation_id: str
    selected_innovation: str
    papers: tuple[dict, ...]
    claim_store: dict = field(default_factory=dict)
    user_constraints: dict = field(default_factory=dict)
    constraints_confirmed: bool = False
    research_design_blueprint: dict | None = None
    blueprint_confirmed: bool = False
    proposal_outline: dict | None = None
    outline_confirmed: bool = False


@dataclass
class ProposalResult:
    status: str
    proposal: dict = field(default_factory=dict)
    writing_guidance: dict = field(default_factory=dict)
    proposal_context: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    message_to_user: str = ""


class ProposalGenerationProvider(Protocol):
    def generate(self, request: ProposalRequest) -> ProposalResult: ...


class UnconfiguredProposalGenerationProvider:
    def generate(self, request: ProposalRequest) -> ProposalResult:
        return ProposalResult(
            status="PROPOSAL_NOT_CONFIGURED",
            limitations=["逐节生成模型密钥未在当前服务进程中配置。"],
            message_to_user="ResearchDesignBlueprint可本地构建，但逐节生成需要配置DEEPSEEK_API_KEY。",
        )


def _frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*([^\n]+)$", text)
    return match.group(1).strip() if match else ""


def _frontmatter_list(text: str, key: str) -> list[str]:
    raw = _frontmatter_value(text, key).strip("[]")
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def load_paradigm_cards(kb_root: Path) -> dict[str, dict]:
    cards = {}
    for path in sorted((kb_root / "04_paradigms").glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        paradigm_id, status = _frontmatter_value(text, "paradigm_id"), _frontmatter_value(text, "status")
        if paradigm_id and status in {"seeded", "complete"}:
            cards[paradigm_id] = {
                "paradigm_id": paradigm_id, "label": PARADIGM_LABELS.get(paradigm_id, paradigm_id),
                "status": status, "minimum_sources": _frontmatter_list(text, "minimum_sources"),
                "local_path": str(path.relative_to(kb_root)).replace("\\", "/"),
            }
    return cards


def recommend_paradigm(request: ProposalRequest, cards: dict[str, dict]) -> str:
    method = request.selected_gap.get("feasible_method") or {}
    text = " ".join([
        request.research_direction, request.fine_grained_question or "", request.selected_innovation,
        str(method.get("design") or ""), str(method.get("analysis") or ""),
    ]).lower()
    routes = (
        ("experiment", ("实验", "随机", "factorial", "a/b", "manipulation")),
        ("survey_sem", ("问卷", "量表", "sem", "cfa", "survey")),
        ("qualitative_case_process", ("访谈", "案例", "qualitative", "gioia")),
        ("systematic_review_bibliometric", ("系统综述", "元分析", "bibliometric")),
        ("computational_text_network", ("文本分析", "机器学习", "network", "nlp")),
        ("analytical_modeling", ("博弈", "机制设计", "analytical model")),
        ("design_science", ("设计科学", "artifact", "原型")),
        ("mixed_methods", ("混合方法", "mixed method")),
        ("quantitative_archival_causal", ("面板", "档案", "did", "因果", "event study")),
    )
    for paradigm_id, keywords in routes:
        if paradigm_id in cards and any(keyword in text for keyword in keywords):
            return paradigm_id
    return next((value for value in ("quantitative_archival_causal", "survey_sem", "experiment") if value in cards), next(iter(cards), ""))


def _claim_index(claim_store: dict) -> dict[str, dict]:
    return {claim["claim_id"]: claim for claim in claim_store.get("claims", []) if claim.get("claim_id")}


def audit_claim_store(claim_store: dict) -> dict:
    errors = []
    claims = _claim_index(claim_store)
    for claim_id, claim in claims.items():
        if not claim.get("formal") or not claim.get("bindings"):
            errors.append(f"{claim_id}:not_formal_or_unbound")
            continue
        for binding in claim["bindings"]:
            span = binding.get("evidence_span") or {}
            if not binding.get("paper_id") or not binding.get("evidence_span_id"):
                errors.append(f"{claim_id}:missing_paper_or_span_id")
            if span.get("evidence_level") not in {"abstract", "fulltext"} or not span.get("text"):
                errors.append(f"{claim_id}:invalid_evidence_span")
    return {"valid": bool(claims) and not errors, "claim_count": len(claims), "errors": errors}


def _title_level_dominates(papers: tuple[dict, ...]) -> bool:
    if not papers:
        return True
    title_only = 0
    for paper in papers:
        level = str(paper.get("evidence_level") or "").lower()
        if not level:
            level = "fulltext" if paper.get("fulltext") or paper.get("full_text") else "abstract" if paper.get("abstract") else "title_only"
        title_only += level == "title_only"
    return title_only > len(papers) / 2


def build_research_design_blueprint(
    request: ProposalRequest,
    paradigm_id: str,
    normalized_constraints: dict,
    constraint_hash: str,
) -> ResearchDesignBlueprint:
    method = request.selected_gap.get("feasible_method") or {}
    claim_ids = [request.selected_gap.get("support_claim_id"), *request.selected_gap.get("counterevidence_claim_ids", [])]
    claim_ids = tuple(dict.fromkeys(str(value) for value in claim_ids if value))
    payload = {
        "research_direction": request.research_direction,
        "gap_id": str(request.selected_gap.get("gap_id") or ""),
        "research_question": str(request.selected_gap.get("research_question") or request.fine_grained_question or "").strip(),
        "claim_ids": claim_ids,
        "paradigm_id": paradigm_id,
        "unit_of_analysis": str(method.get("unit_of_analysis") or normalized_constraints["research_context"]).strip(),
        "context": str(method.get("context") or normalized_constraints["research_context"]).strip(),
        "design": str(method.get("design") or "").strip(),
        "data": str(method.get("data") or "").strip(),
        "analysis": str(method.get("analysis") or "").strip(),
        "section_ids": tuple(section_id for section_id, _ in SECTION_SPECS),
        "constraint_hash": constraint_hash,
        "degree_level": normalized_constraints["degree_level"],
        "institution_template": normalized_constraints["institution_template"],
        "output_language": normalized_constraints["output_language"],
        "target_word_count": normalized_constraints["target_word_count"],
        "deadline": normalized_constraints["deadline"],
        "data_access": normalized_constraints["data_access"],
        "method_constraints": normalized_constraints["method_constraints"],
        "ethics_privacy": normalized_constraints["ethics_privacy"],
        "tool_capabilities": normalized_constraints["tool_capabilities"],
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    return ResearchDesignBlueprint(blueprint_id=f"blueprint_{digest}", **payload)


def _blueprint_matches(expected: ResearchDesignBlueprint, supplied: dict | None) -> bool:
    if not supplied:
        return False
    normalized = dict(supplied)
    normalized["claim_ids"] = tuple(normalized.get("claim_ids") or [])
    normalized["section_ids"] = tuple(normalized.get("section_ids") or [])
    return normalized == expected.as_dict()


class DeepSeekProposalGenerationProvider:
    def __init__(self, client: DeepSeekJsonClient, kb_root: Path, arena_reviewer=None):
        self.client = client
        self.kb_root = kb_root
        self.arena_reviewer = arena_reviewer or ProposalArenaReviewer(client)

    @staticmethod
    def _section_system_prompt() -> str:
        return """你是受控开题报告逐节生成器。只输出JSON对象：
{"section":{"section_id":"background","content":"...","claim_ids":["claim_x"],"assumptions":[],"blueprint_refs":{"blueprint_id":"...","research_question":"...","design":"...","outline_id":"...","constraint_hash":"..."}}}
本节唯一事实来源是用户消息中的Claim Store；不得使用外部知识、原始论文列表或自造引用。
所有事实性论断必须由claim_ids支持。不得改变ResearchDesignBlueprint、已确认用户约束或提纲。
硬性规则（违反即拒）：
1. 字数：本节content长度必须达到length_rule给出的硬性下限，并以target_words为目标；若收到length_feedback，说明上一版字数不足，必须扩写达标；
2. 约束：一切时间计划必须落在已确认截止时间之前；数据与伦理表述必须与用户约束原文一致，不得出现与约束冲突的口径（如约束为纯公开/二手数据时不得写访谈、被试或问卷发放），可行性/伦理表述不得比约束原文更强（如不得写"伦理风险极低"）；
3. 外推：超出claim_ids直接支持范围的命题、假设或机制推演，必须在assumptions中列出或显式标注为"理论推演（待验证）"；同一claim不得被用于支撑方向相反的结论；
4. 方法：凡声称DID、实验或任何因果识别，content必须明确处理组与对照组、处理时点、结果变量和识别假设关注点；数据结构不支持时降低其核心地位；
5. 重复：不得复用其他节已有的成段表述或句式，各节信息应有分工。"""

    @staticmethod
    def _section_length_floor(section_spec: dict) -> int:
        target = int(section_spec.get("target_words") or 0)
        if target < MIN_CHECKABLE_TARGET_WORDS:
            return 0
        return int(target * MIN_SECTION_WORD_RATIO)

    def _generate_section(
        self,
        section_spec: dict,
        blueprint: ResearchDesignBlueprint,
        outline: dict,
        claims: dict[str, dict],
        user_constraints: dict | None = None,
        length_feedback: str = "",
    ) -> tuple[dict, dict]:
        section_id = section_spec["section_id"]
        title = section_spec["title"]
        allowed_claim_ids = [claim_id for claim_id in section_spec["allowed_claim_ids"] if claim_id in claims]
        constraints_digest = {
            key: (user_constraints or {}).get(key)
            for key in ("deadline", "target_word_count", "data_access", "ethics_privacy", "method_constraints")
            if (user_constraints or {}).get(key)
        }
        timeline_rule = (
            f"本节是研究计划：今天是{date.today().isoformat()}；所有阶段必须从今天之后开始，"
            "严禁把启动日期回溯到过去的任何年月（如自2025年启动属于违规）；"
            "全部阶段必须落在截止时间之前完成并写出具体月份区间；字数按target_words执行。"
            if section_id == "timeline" else ""
        )
        floor = self._section_length_floor(section_spec)
        length_rule = (
            f"字数硬性要求：本节content长度不得低于{floor}字符，目标{section_spec.get('target_words')}字符；"
            f"低于{floor}字符即拒。"
            if floor else ""
        )
        payload = {
            "task": "仅生成一个开题报告章节",
            "confirmed_user_constraints": constraints_digest,
            "timeline_rule": timeline_rule,
            "length_rule": length_rule,
            "length_feedback": length_feedback,
            "section_spec": section_spec,
            "research_design_blueprint": blueprint.as_dict(),
            "proposal_outline": {
                "outline_id": outline["outline_id"],
                "constraint_hash": outline["constraint_hash"],
            },
            "claim_store": {"claims": [claims[claim_id] for claim_id in allowed_claim_ids]},
            "allowed_claim_ids": allowed_claim_ids,
        }
        raw, model_audit = self.client.complete(self._section_system_prompt(), json.dumps(payload, ensure_ascii=False))
        item = raw.get("section", {}) if isinstance(raw, dict) else {}
        if item.get("section_id") != section_id:
            raise ValueError("section_id_mismatch")
        content = str(item.get("content") or "").strip()
        claim_ids = list(dict.fromkeys(str(value) for value in item.get("claim_ids", []) if value))
        if not content or not claim_ids or not set(claim_ids).issubset(set(allowed_claim_ids)):
            raise ValueError("section_requires_content_and_allowed_claims")
        refs = item.get("blueprint_refs") or {}
        expected_refs = {
            "blueprint_id": blueprint.blueprint_id,
            "research_question": blueprint.research_question,
            "design": blueprint.design,
            "outline_id": outline["outline_id"],
            "constraint_hash": blueprint.constraint_hash,
        }
        if refs != expected_refs:
            raise ValueError("section_blueprint_inconsistency")
        citations = [citation for claim_id in claim_ids for citation in claims[claim_id].get("citations", [])]
        if not citations:
            raise ValueError("section_citations_missing")
        return {
            "section_id": section_id, "title": title, "content": content, "claim_ids": claim_ids,
            "citations": citations, "assumptions": [str(value) for value in item.get("assumptions", [])[:5]],
            "blueprint_refs": refs,
        }, model_audit

    @staticmethod
    def _controlled_guidance(paradigm: dict) -> dict:
        return {
            "paradigm_id": paradigm["paradigm_id"], "paradigm_label": paradigm["label"],
            "paradigm_status": paradigm["status"], "source_ids": paradigm["minimum_sources"],
            "local_path": paradigm["local_path"],
            "stages": [
                {
                    "stage_id": stage_id, "title": title, "purpose": f"按已确认蓝图完成{title}阶段",
                    "recommended_moves": ["先引用Claim Store，再写本阶段判断"],
                    "evidence_required": ["claim_id、paper_id与evidence_span三联绑定"],
                    "common_failures": ["引入Claim Store之外的事实"],
                    "self_check": ["所有正式论断是否均有Claim Store绑定？"],
                }
                for stage_id, title in GUIDANCE_STAGES
            ],
            "target_journal_status": "not_selected",
        }

    def generate(self, request: ProposalRequest) -> ProposalResult:
        claim_audit = audit_claim_store(request.claim_store)
        title_level_dominates = _title_level_dominates(request.papers)
        if title_level_dominates or not claim_audit["valid"]:
            return ProposalResult(
                status="RESEARCH_SKETCH_ONLY",
                proposal={
                    "research_direction": request.research_direction,
                    "selected_gap": request.selected_gap,
                    "sketch_status": "formal_generation_blocked_by_evidence",
                },
                limitations=["题名级证据占主导或Claim Store无有效L1/L2绑定，不能生成正式开题。"],
                audit={"claim_audit": claim_audit, "title_level_evidence_dominates": title_level_dominates},
                message_to_user="当前只能生成研究构想草图；补足摘要/全文证据后再进入正式开题。",
            )
        constraint_gate = evaluate_user_constraints(request.user_constraints)
        if not constraint_gate.complete:
            return ProposalResult(
                status="PROPOSAL_NEEDS_USER_INPUT",
                proposal={"user_constraints": constraint_gate.normalized, "sections": []},
                proposal_context={
                    "checkpoint": "USER_CONSTRAINTS",
                    "missing_field": constraint_gate.missing_field,
                    "next_question": constraint_gate.next_question,
                    "gate_passed": False,
                },
                limitations=[constraint_gate.error or f"missing_user_constraint:{constraint_gate.missing_field}"],
                audit={"claim_audit": claim_audit, "model_calls": 0, "constraint_gate_passed": False},
                message_to_user=constraint_gate.next_question or "需要补充会改变研究设计的用户约束。",
            )
        if not request.constraints_confirmed:
            return ProposalResult(
                status="USER_CONSTRAINT_CONFIRMATION_REQUIRED",
                proposal={"user_constraints": constraint_gate.normalized, "sections": []},
                proposal_context={
                    "checkpoint": "USER_CONSTRAINT_CONFIRMATION",
                    "constraint_hash": constraint_gate.constraint_hash,
                    "gate_passed": False,
                },
                audit={"claim_audit": claim_audit, "model_calls": 0, "constraint_gate_passed": True},
                message_to_user="用户约束已完整记录；确认后才会生成研究设计蓝图与提纲。",
            )
        cards = load_paradigm_cards(self.kb_root)
        paradigm_id = recommend_paradigm(request, cards)
        paradigm = cards.get(paradigm_id)
        if not paradigm:
            return ProposalResult(status="PROPOSAL_PARADIGM_MISSING", limitations=["缺少可用研究范式卡。"])
        blueprint = build_research_design_blueprint(
            request,
            paradigm_id,
            constraint_gate.normalized,
            constraint_gate.constraint_hash,
        )
        claims = _claim_index(request.claim_store)
        if not blueprint.claim_ids or not set(blueprint.claim_ids).issubset(claims):
            return ProposalResult(status="RESEARCH_SKETCH_ONLY", limitations=["研究空白没有绑定完整Claim Store论断。"])
        outline = build_proposal_outline(blueprint.as_dict(), SECTION_SPECS)
        task_cards = build_execution_task_cards(blueprint.as_dict(), outline, request.claim_store)
        plan_payload = {
            "user_constraints": constraint_gate.normalized,
            "research_design_blueprint": blueprint.as_dict(),
            "proposal_outline": outline,
            "execution_task_cards": task_cards,
            "sections": [],
        }
        if not request.blueprint_confirmed or not request.outline_confirmed:
            return ProposalResult(
                status="PROPOSAL_PLAN_CONFIRMATION_REQUIRED",
                proposal=plan_payload,
                writing_guidance=self._controlled_guidance(paradigm),
                proposal_context={
                    "checkpoint": "BLUEPRINT_AND_OUTLINE_CONFIRMATION",
                    "constraint_hash": constraint_gate.constraint_hash,
                    "blueprint_id": blueprint.blueprint_id,
                    "outline_id": outline["outline_id"],
                    "gate_passed": False,
                },
                audit={
                    "claim_audit": claim_audit,
                    "constraint_gate_passed": True,
                    "task_card_audit": task_cards["audit"],
                    "model_calls": 0,
                },
                message_to_user="研究设计蓝图、逐节提纲和执行任务卡已生成；确认计划后才会逐节生成。",
            )
        if (
            not _blueprint_matches(blueprint, request.research_design_blueprint)
            or not proposal_outline_matches(outline, request.proposal_outline)
        ):
            return ProposalResult(
                status="PROPOSAL_PLAN_INVALID",
                proposal=plan_payload,
                limitations=["已确认蓝图或提纲与当前证据、用户约束、研究问题或方法不一致。"],
                audit={
                    "claim_audit": claim_audit,
                    "constraint_gate_passed": True,
                    "task_card_audit": task_cards["audit"],
                    "model_calls": 0,
                },
            )

        sections, model_audits, generation_errors = [], [], []
        started = time.monotonic()
        task_card_by_section = {item["section_id"]: item for item in task_cards["cards"]}
        for section_spec in outline["sections"]:
            section_id = section_spec["section_id"]
            try:
                section, model_audit = self._generate_section(section_spec, blueprint, outline, claims, request.user_constraints)
                floor = self._section_length_floor(section_spec)
                if floor and len(section["content"]) < floor:
                    feedback = (
                        f"你上一版content长度为{len(section['content'])}字符，低于硬性下限{floor}字符，被审计拒绝。"
                        f"请扩写本节至至少{floor}字符（目标{section_spec.get('target_words')}字符），"
                        "只补充与claim_ids相关的内容，不得改变蓝图、约束与引用结构。"
                    )
                    retried, retry_audit = self._generate_section(
                        section_spec, blueprint, outline, claims, request.user_constraints, length_feedback=feedback,
                    )
                    model_audit["length_retry"] = {
                        "first_length": len(section["content"]),
                        "floor": floor,
                        "retried_length": len(retried["content"]),
                        "passed": len(retried["content"]) >= floor,
                        "retry_attempts": retry_audit.get("attempts"),
                        "retry_duration_ms": retry_audit.get("duration_ms"),
                    }
                    section = retried if len(retried["content"]) > len(section["content"]) else section
                section["task_card_id"] = task_card_by_section[section_id]["task_card_id"]
                sections.append(section)
                model_audits.append({"section_id": section_id, **model_audit})
            except Exception as exc:
                generation_errors.append(f"{section_id}:{type(exc).__name__}:{exc}")

        citation_errors = []
        for section in sections:
            if not section["citations"]:
                citation_errors.append(f"{section['section_id']}:no_citations")
            for citation in section["citations"]:
                if not citation.get("claim_id") or not citation.get("paper_id") or not citation.get("evidence_span"):
                    citation_errors.append(f"{section['section_id']}:invalid_citation_binding")
                elif citation["claim_id"] not in section["claim_ids"]:
                    citation_errors.append(f"{section['section_id']}:citation_claim_not_declared")
        consistency_rows = []
        expected_refs = {
            "blueprint_id": blueprint.blueprint_id,
            "research_question": blueprint.research_question,
            "design": blueprint.design,
            "outline_id": outline["outline_id"],
            "constraint_hash": blueprint.constraint_hash,
        }
        for section in sections:
            consistency_rows.append({
                "section_id": section["section_id"], "expected": expected_refs,
                "actual": section["blueprint_refs"], "consistent": section["blueprint_refs"] == expected_refs,
            })
        consistency_valid = len(consistency_rows) == len(SECTION_SPECS) and all(row["consistent"] for row in consistency_rows)
        citation_audit = {"valid": not citation_errors and len(sections) == len(SECTION_SPECS), "errors": citation_errors}
        consistency_matrix = {"valid": consistency_valid, "rows": consistency_rows}
        constraint_alignment = audit_constraint_alignment(request.user_constraints, outline, sections)
        repetition = cross_section_repetition(sections)
        all_gates = (
            claim_audit["valid"]
            and citation_audit["valid"]
            and consistency_matrix["valid"]
            and task_cards["audit"]["valid"]
            and constraint_alignment["valid"]
            and not generation_errors
        )
        status = "READY_FOR_HUMAN_REVIEW" if all_gates else "PROPOSAL_CONTROLLED_PARTIAL"
        arena_review: dict = {}
        arena_note = ""
        if sections:
            try:
                arena_review = self.arena_reviewer.review(blueprint.research_question, sections)
            except Exception as exc:
                arena_review = {"version": PROPOSAL_ARENA_VERSION, "error": f"{type(exc).__name__}: {exc}"}
                arena_note = "高风险章节竞技场评审失败，不影响既定审计结论；建议人工复核时补评。"
            if arena_review.get("revise_section_ids"):
                arena_note = "竞技场评审建议修订以下章节：" + "、".join(arena_review["revise_section_ids"]) + "；裁决供人工复核参考，不自动改稿。"
        limitations = ["本状态仅表示通过自动门禁，仍须人工审阅，不能视为最终开题。"]
        if not constraint_alignment["valid"]:
            limitations.append("约束对齐审计未通过：" + "；".join(constraint_alignment["errors"][:5]))
        if repetition.get("flagged"):
            limitations.append(f"跨节重复度偏高（{repetition.get('rate')}），建议人工压缩复用表述。")
        if arena_note:
            limitations.append(arena_note)
        return ProposalResult(
            status=status,
            proposal={
                **plan_payload,
                "sections": sections,
                "selected_gap": request.selected_gap, "selected_innovation_id": request.selected_innovation_id,
                "selected_innovation": request.selected_innovation, "draft_status": "human_review_required",
            },
            writing_guidance=self._controlled_guidance(paradigm),
            proposal_context={
                "scope_label": "IS_IM", "claim_ids": list(blueprint.claim_ids), "blueprint_id": blueprint.blueprint_id,
                "outline_id": outline["outline_id"], "constraint_hash": blueprint.constraint_hash,
                "checkpoint": "HUMAN_REVIEW", "gate_passed": all_gates,
                "release_ceiling": "READY_FOR_HUMAN_REVIEW",
                "arena_overall_verdict": arena_review.get("overall_verdict", ""),
            },
            limitations=limitations,
            audit={
                "version": PROPOSAL_CONTROL_VERSION, "claim_audit": claim_audit, "citation_audit": citation_audit,
                "cross_section_consistency_matrix": consistency_matrix, "generation_errors": generation_errors,
                "constraint_gate_passed": True, "constraints_confirmed": True,
                "blueprint_confirmed": True, "outline_confirmed": True,
                "task_card_audit": task_cards["audit"],
                "constraint_alignment_audit": constraint_alignment,
                "cross_section_repetition": repetition,
                "arena_review": arena_review,
                "model_calls": len(model_audits), "models": model_audits,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
            message_to_user="已按确认蓝图逐节生成并完成Claim、引用与跨节一致性审计；请进入人工审阅。" if all_gates else "逐节生成未通过全部控制门禁。",
        )


def build_proposal_generation_provider(kb_root: Path) -> ProposalGenerationProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        return UnconfiguredProposalGenerationProvider()
    client = DeepSeekJsonClient(
        api_key=api_key, base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"), timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "90")),
    )
    return DeepSeekProposalGenerationProvider(client, kb_root)
