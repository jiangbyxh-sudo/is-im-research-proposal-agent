"""Evidence-bounded proposal drafting and paradigm-specific writing guidance."""
from __future__ import annotations

import json
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
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
    ("topic", "选题"),
    ("introduction", "引言"),
    ("theory", "理论"),
    ("method", "方法"),
    ("results", "结果"),
    ("discussion", "讨论"),
    ("submission", "投稿"),
)
PARADIGM_LABELS = {
    "quantitative_archival_causal": "档案/面板数据与因果推断",
    "survey_sem": "问卷、测量与CFA/SEM",
    "experiment": "实验、在线实验与A/B测试",
    "qualitative_case_process": "定性案例、归纳理论与过程研究",
    "systematic_review_bibliometric": "系统综述、元分析与科学计量",
    "mixed_methods": "混合方法",
    "computational_text_network": "计算文本、机器学习与网络分析",
    "analytical_modeling": "分析建模、博弈论与机制设计",
    "design_science": "设计科学",
}


@dataclass(frozen=True)
class ProposalRequest:
    research_direction: str
    fine_grained_question: str | None
    selected_gap: dict
    selected_innovation_id: str
    selected_innovation: str
    papers: tuple[dict, ...]


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
            limitations=["DeepSeek密钥未在当前服务进程中配置。"],
            message_to_user="空白与创新点已记录；生成开题报告和写作指导需要先在“检索设置”中启用DeepSeek。",
        )


def _frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*([^\n]+)$", text)
    return match.group(1).strip() if match else ""


def _frontmatter_list(text: str, key: str) -> list[str]:
    raw = _frontmatter_value(text, key).strip("[]")
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def load_paradigm_cards(kb_root: Path) -> dict[str, dict]:
    cards: dict[str, dict] = {}
    for path in sorted((kb_root / "04_paradigms").glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        paradigm_id = _frontmatter_value(text, "paradigm_id")
        status = _frontmatter_value(text, "status")
        if not paradigm_id or status not in {"seeded", "complete"}:
            continue
        cards[paradigm_id] = {
            "paradigm_id": paradigm_id,
            "label": PARADIGM_LABELS.get(paradigm_id, paradigm_id),
            "status": status,
            "minimum_sources": _frontmatter_list(text, "minimum_sources"),
            "local_path": str(path.relative_to(kb_root)).replace("\\", "/"),
            "content": text.split("---", 2)[-1].strip()[:7000],
        }
    return cards


def recommend_paradigm(request: ProposalRequest, cards: dict[str, dict]) -> str:
    text = " ".join([
        request.research_direction,
        request.fine_grained_question or "",
        request.selected_gap.get("gap_statement", ""),
        request.selected_gap.get("why_it_matters", ""),
        request.selected_innovation,
    ]).lower()
    routes = (
        ("experiment", ("实验", "随机", "a/b", "ab test", "操纵", "causal experiment")),
        ("survey_sem", ("问卷", "量表", "构念", "信任", "态度", "意愿", "感知", "sem", "cfa")),
        ("qualitative_case_process", ("访谈", "案例", "质化", "过程机制", "扎根", "gioia")),
        ("systematic_review_bibliometric", ("系统综述", "元分析", "科学计量", "bibliometric", "meta-analysis")),
        ("computational_text_network", ("文本分析", "自然语言", "机器学习", "知识图谱", "网络分析", "nlp")),
        ("analytical_modeling", ("博弈", "机制设计", "定价", "信息不对称", "analytical model")),
        ("design_science", ("设计科学", "制品", "artifact", "原型评价")),
        ("mixed_methods", ("混合方法", "mixed method")),
        ("quantitative_archival_causal", ("面板", "档案", "政策冲击", "平台规则", "事件研究", "did", "因果")),
    )
    for paradigm_id, keywords in routes:
        if paradigm_id in cards and any(keyword in text for keyword in keywords):
            return paradigm_id
    for fallback in ("quantitative_archival_causal", "survey_sem", "experiment"):
        if fallback in cards:
            return fallback
    return next(iter(cards), "")


class DeepSeekProposalGenerationProvider:
    def __init__(self, client: DeepSeekJsonClient, kb_root: Path):
        self.client = client
        self.kb_root = kb_root

    @staticmethod
    def _system_prompt() -> str:
        return """你是面向IS/IM社科研究者的开题报告与写作指导生成器。必须只输出JSON对象。
只能使用用户消息提供的论文元数据、已选研究空白、创新点和本地研究范式卡，不得虚构论文、DOI、作者、数据、结果、理论出处或目标期刊要求。
现有论文主要是题名级元数据，因此研究现状、空白与机制均必须使用“提示、候选、拟验证”等审慎措辞。
方法部分必须严格遵循selected_paradigm，不得混入未提供的方法要求。
开题报告必须覆盖用户消息中的required_sections；每节包含content、paper_ids、assumptions。paper_ids只能来自allowed_paper_ids。
写作指导必须覆盖required_guidance_stages；每阶段包含purpose、recommended_moves、evidence_required、common_failures、self_check。
未指定目标期刊时，不得编造格式要求，只能说明“选择目标期刊后核对官方作者指南”。
JSON格式：
{
  "working_title": "题目",
  "research_question": "核心RQ",
  "proposal_sections": [{"section_id":"background","content":"...","paper_ids":["P001"],"assumptions":["..."]}],
  "writing_guidance": [{"stage_id":"introduction","purpose":"...","recommended_moves":["..."],"evidence_required":["..."],"common_failures":["..."],"self_check":["..."]}],
  "limitations": ["..."]
}"""

    @staticmethod
    def _paper_view(paper: dict, paper_id: str) -> dict:
        return {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "authors": paper.get("authors", [])[:6],
            "year": paper.get("year"),
            "journal": paper.get("journal"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
            "journal_ranking": paper.get("journal_ranking", []),
        }

    def _validate(self, raw: dict, request: ProposalRequest, paradigm: dict, paper_map: dict[str, dict], model_audit: dict) -> ProposalResult:
        allowed = set(paper_map)
        invalid_refs = 0
        raw_sections = {
            str(item.get("section_id")): item
            for item in raw.get("proposal_sections", [])
            if isinstance(item, dict)
        }
        sections = []
        for section_id, title in SECTION_SPECS:
            item = raw_sections.get(section_id, {})
            content = str(item.get("content") or "").strip()
            raw_ids = item.get("paper_ids", [])
            raw_ids = raw_ids if isinstance(raw_ids, list) else []
            paper_ids = [value for value in raw_ids if value in allowed]
            invalid_refs += len(raw_ids) - len(paper_ids)
            assumptions = item.get("assumptions", [])
            assumptions = [str(value) for value in assumptions[:5]] if isinstance(assumptions, list) else []
            sections.append({
                "section_id": section_id,
                "title": title,
                "content": content,
                "paper_ids": paper_ids,
                "evidence_papers": [paper_map[value] for value in paper_ids],
                "assumptions": assumptions,
            })

        raw_guidance = {
            str(item.get("stage_id")): item
            for item in raw.get("writing_guidance", [])
            if isinstance(item, dict)
        }
        guidance_stages = []
        for stage_id, title in GUIDANCE_STAGES:
            item = raw_guidance.get(stage_id, {})
            guidance_stages.append({
                "stage_id": stage_id,
                "title": title,
                "purpose": str(item.get("purpose") or "").strip(),
                "recommended_moves": [str(value) for value in item.get("recommended_moves", [])[:6]],
                "evidence_required": [str(value) for value in item.get("evidence_required", [])[:5]],
                "common_failures": [str(value) for value in item.get("common_failures", [])[:5]],
                "self_check": [str(value) for value in item.get("self_check", [])[:6]],
            })

        known_dois = {str(item.get("doi")).lower() for item in paper_map.values() if item.get("doi")}
        raw_text = json.dumps(raw, ensure_ascii=False)
        mentioned_dois = {value.lower() for value in re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", raw_text, re.I)}
        invalid_refs += len(mentioned_dois - known_dois)
        complete_sections = sum(bool(item["content"]) for item in sections)
        complete_guidance = sum(bool(item["purpose"] and item["recommended_moves"]) for item in guidance_stages)
        status = "PROPOSAL_DRAFT_READY" if complete_sections == len(SECTION_SPECS) and complete_guidance == len(GUIDANCE_STAGES) and invalid_refs == 0 else "PROPOSAL_DRAFT_PARTIAL"

        limitations = [str(value) for value in raw.get("limitations", [])[:8]]
        limitations.extend([
            "研究空白目前主要依据题名级元数据，正式开题前必须获取核心论文全文复核。",
            "当前未指定目标期刊；投稿格式与特殊要求需在选刊后查询官方作者指南。",
        ])
        return ProposalResult(
            status=status,
            proposal={
                "working_title": str(raw.get("working_title") or "").strip(),
                "research_question": str(raw.get("research_question") or "").strip(),
                "selected_gap": request.selected_gap,
                "selected_innovation_id": request.selected_innovation_id,
                "selected_innovation": request.selected_innovation,
                "sections": sections,
                "references": list(paper_map.values()),
                "draft_status": "pending_fulltext_verification",
            },
            writing_guidance={
                "paradigm_id": paradigm["paradigm_id"],
                "paradigm_label": paradigm["label"],
                "paradigm_status": paradigm["status"],
                "source_ids": paradigm["minimum_sources"],
                "local_path": paradigm["local_path"],
                "stages": guidance_stages,
                "target_journal_status": "not_selected",
            },
            proposal_context={
                "scope_label": "IS_IM",
                "paper_ids": list(paper_map),
                "claim_ids": [request.selected_gap.get("gap_id", "")],
                "selected_gap_ids": [request.selected_gap.get("gap_id", "")],
                "selected_innovation_ids": [request.selected_innovation_id],
                "paradigm_ids": [paradigm["paradigm_id"]],
                "gate_passed": True,
            },
            limitations=limitations,
            audit={
                "invalid_reference_count": invalid_refs,
                "proposal_section_count": complete_sections,
                "guidance_stage_count": complete_guidance,
                "model": model_audit,
                "local_paradigm_path": paradigm["local_path"],
            },
            message_to_user=(
                f"已基于“{paradigm['label']}”范式生成开题报告草案和7阶段写作指导；"
                "当前草案保留全文复核门禁。"
            ),
        )

    def generate(self, request: ProposalRequest) -> ProposalResult:
        cards = load_paradigm_cards(self.kb_root)
        paradigm_id = recommend_paradigm(request, cards)
        paradigm = cards.get(paradigm_id)
        if not paradigm:
            return ProposalResult(
                status="PROPOSAL_PARADIGM_MISSING",
                limitations=["本地知识库中没有状态为seeded/complete的适用研究范式卡。"],
                message_to_user="本地研究范式覆盖不足，已停止生成；需要检索并补入权威方法来源。",
            )
        paper_map = {
            f"P{index + 1:03d}": self._paper_view(paper, f"P{index + 1:03d}")
            for index, paper in enumerate(list(request.papers)[:40])
        }
        if not paper_map:
            return ProposalResult(
                status="PROPOSAL_EVIDENCE_MISSING",
                limitations=["没有可验证论文记录。"],
                message_to_user="缺少可核验论文证据，已停止生成开题报告。",
            )
        payload = {
            "task": "依据已选空白、创新点和本地范式，生成通用开题报告草案与分阶段写作指导。",
            "research_direction": request.research_direction,
            "fine_grained_question": request.fine_grained_question,
            "selected_gap": request.selected_gap,
            "selected_innovation": {
                "innovation_id": request.selected_innovation_id,
                "text": request.selected_innovation,
            },
            "selected_paradigm": paradigm,
            "required_sections": [{"section_id": key, "title": title} for key, title in SECTION_SPECS],
            "required_guidance_stages": [{"stage_id": key, "title": title} for key, title in GUIDANCE_STAGES],
            "allowed_paper_ids": list(paper_map),
            "papers": list(paper_map.values()),
        }
        try:
            started = time.monotonic()
            raw, model_audit = self.client.complete(self._system_prompt(), json.dumps(payload, ensure_ascii=False))
            result = self._validate(raw, request, paradigm, paper_map, model_audit)
            result.audit["prompt_version"] = "proposal-current-baseline-0.5"
            result.audit["input_hash"] = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            result.audit["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
            result.audit["raw_model_output"] = raw
            return result
        except Exception as exc:
            return ProposalResult(
                status="PROPOSAL_GENERATION_FAILED",
                limitations=[f"模型调用或JSON校验失败：{type(exc).__name__}"],
                message_to_user="空白与创新点已记录，但开题报告生成失败；系统没有用模拟内容补写。",
            )


def build_proposal_generation_provider(kb_root: Path) -> ProposalGenerationProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY") or ""
    if not api_key:
        return UnconfiguredProposalGenerationProvider()
    client = DeepSeekJsonClient(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
        timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "90")),
    )
    return DeepSeekProposalGenerationProvider(client, kb_root)
