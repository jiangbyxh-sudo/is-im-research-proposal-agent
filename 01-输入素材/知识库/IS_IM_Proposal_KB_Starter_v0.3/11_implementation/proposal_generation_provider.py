"""P4 controlled proposal workflow: blueprint, confirmation, then claim-bound sections."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

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
PROPOSAL_CONTROL_VERSION = "p4-controlled-proposal-1.0.0"


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
    research_design_blueprint: dict | None = None
    blueprint_confirmed: bool = False


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


def build_research_design_blueprint(request: ProposalRequest, paradigm_id: str) -> ResearchDesignBlueprint:
    method = request.selected_gap.get("feasible_method") or {}
    claim_ids = [request.selected_gap.get("support_claim_id"), *request.selected_gap.get("counterevidence_claim_ids", [])]
    claim_ids = tuple(dict.fromkeys(str(value) for value in claim_ids if value))
    payload = {
        "research_direction": request.research_direction,
        "gap_id": str(request.selected_gap.get("gap_id") or ""),
        "research_question": str(request.selected_gap.get("research_question") or request.fine_grained_question or "").strip(),
        "claim_ids": claim_ids,
        "paradigm_id": paradigm_id,
        "unit_of_analysis": str(method.get("unit_of_analysis") or "to_be_confirmed").strip(),
        "context": str(method.get("context") or request.research_direction).strip(),
        "design": str(method.get("design") or "").strip(),
        "data": str(method.get("data") or "").strip(),
        "analysis": str(method.get("analysis") or "").strip(),
        "section_ids": tuple(section_id for section_id, _ in SECTION_SPECS),
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
    def __init__(self, client: DeepSeekJsonClient, kb_root: Path):
        self.client = client
        self.kb_root = kb_root

    @staticmethod
    def _section_system_prompt() -> str:
        return """你是受控开题报告逐节生成器。只输出JSON对象：
{"section":{"section_id":"background","content":"...","claim_ids":["claim_x"],"assumptions":[],"blueprint_refs":{"blueprint_id":"...","research_question":"...","design":"..."}}}
本节唯一事实来源是用户消息中的Claim Store；不得使用外部知识、原始论文列表或自造引用。
所有事实性论断必须由claim_ids支持。不得改变ResearchDesignBlueprint。"""

    def _generate_section(self, section_id: str, title: str, blueprint: ResearchDesignBlueprint, claims: dict[str, dict]) -> tuple[dict, dict]:
        payload = {
            "task": "仅生成一个开题报告章节",
            "section_spec": {"section_id": section_id, "title": title},
            "research_design_blueprint": blueprint.as_dict(),
            "claim_store": {"claims": [claims[claim_id] for claim_id in blueprint.claim_ids]},
            "allowed_claim_ids": list(blueprint.claim_ids),
        }
        raw, model_audit = self.client.complete(self._section_system_prompt(), json.dumps(payload, ensure_ascii=False))
        item = raw.get("section", {}) if isinstance(raw, dict) else {}
        if item.get("section_id") != section_id:
            raise ValueError("section_id_mismatch")
        content = str(item.get("content") or "").strip()
        claim_ids = list(dict.fromkeys(str(value) for value in item.get("claim_ids", []) if value))
        if not content or not claim_ids or not set(claim_ids).issubset(claims):
            raise ValueError("section_requires_content_and_allowed_claims")
        refs = item.get("blueprint_refs") or {}
        expected_refs = {
            "blueprint_id": blueprint.blueprint_id,
            "research_question": blueprint.research_question,
            "design": blueprint.design,
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
        if _title_level_dominates(request.papers) or not claim_audit["valid"]:
            return ProposalResult(
                status="RESEARCH_SKETCH_ONLY",
                proposal={
                    "research_direction": request.research_direction,
                    "selected_gap": request.selected_gap,
                    "sketch_status": "formal_generation_blocked_by_evidence",
                },
                limitations=["题名级证据占主导或Claim Store无有效L1/L2绑定，不能生成正式开题。"],
                audit={"claim_audit": claim_audit, "title_level_evidence_dominates": _title_level_dominates(request.papers)},
                message_to_user="当前只能生成研究构想草图；补足摘要/全文证据后再进入正式开题。",
            )
        cards = load_paradigm_cards(self.kb_root)
        paradigm_id = recommend_paradigm(request, cards)
        paradigm = cards.get(paradigm_id)
        if not paradigm:
            return ProposalResult(status="PROPOSAL_PARADIGM_MISSING", limitations=["缺少可用研究范式卡。"])
        blueprint = build_research_design_blueprint(request, paradigm_id)
        claims = _claim_index(request.claim_store)
        if not blueprint.claim_ids or not set(blueprint.claim_ids).issubset(claims):
            return ProposalResult(status="RESEARCH_SKETCH_ONLY", limitations=["研究空白没有绑定完整Claim Store论断。"])
        if not request.blueprint_confirmed:
            return ProposalResult(
                status="BLUEPRINT_CONFIRMATION_REQUIRED",
                proposal={"research_design_blueprint": blueprint.as_dict(), "sections": []},
                proposal_context={"blueprint_id": blueprint.blueprint_id, "gate_passed": False},
                audit={"claim_audit": claim_audit, "model_calls": 0},
                message_to_user="ResearchDesignBlueprint已生成；确认蓝图后才会逐节生成。",
            )
        if not _blueprint_matches(blueprint, request.research_design_blueprint):
            return ProposalResult(
                status="BLUEPRINT_INVALID",
                proposal={"research_design_blueprint": blueprint.as_dict(), "sections": []},
                limitations=["已确认蓝图与当前证据、研究问题或方法不一致。"],
                audit={"claim_audit": claim_audit, "model_calls": 0},
            )

        sections, model_audits, generation_errors = [], [], []
        started = time.monotonic()
        for section_id, title in SECTION_SPECS:
            try:
                section, model_audit = self._generate_section(section_id, title, blueprint, claims)
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
        consistency_rows = []
        expected_refs = {"blueprint_id": blueprint.blueprint_id, "research_question": blueprint.research_question, "design": blueprint.design}
        for section in sections:
            consistency_rows.append({
                "section_id": section["section_id"], "expected": expected_refs,
                "actual": section["blueprint_refs"], "consistent": section["blueprint_refs"] == expected_refs,
            })
        consistency_valid = len(consistency_rows) == len(SECTION_SPECS) and all(row["consistent"] for row in consistency_rows)
        citation_audit = {"valid": not citation_errors and len(sections) == len(SECTION_SPECS), "errors": citation_errors}
        consistency_matrix = {"valid": consistency_valid, "rows": consistency_rows}
        all_gates = claim_audit["valid"] and citation_audit["valid"] and consistency_matrix["valid"] and not generation_errors
        status = "READY_FOR_HUMAN_REVIEW" if all_gates else "PROPOSAL_CONTROLLED_PARTIAL"
        return ProposalResult(
            status=status,
            proposal={
                "research_design_blueprint": blueprint.as_dict(), "sections": sections,
                "selected_gap": request.selected_gap, "selected_innovation_id": request.selected_innovation_id,
                "selected_innovation": request.selected_innovation, "draft_status": "human_review_required",
            },
            writing_guidance=self._controlled_guidance(paradigm),
            proposal_context={
                "scope_label": "IS_IM", "claim_ids": list(blueprint.claim_ids), "blueprint_id": blueprint.blueprint_id,
                "gate_passed": all_gates, "release_ceiling": "READY_FOR_HUMAN_REVIEW",
            },
            limitations=["本状态仅表示通过自动门禁，仍须人工审阅，不能视为最终开题。"],
            audit={
                "version": PROPOSAL_CONTROL_VERSION, "claim_audit": claim_audit, "citation_audit": citation_audit,
                "cross_section_consistency_matrix": consistency_matrix, "generation_errors": generation_errors,
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
