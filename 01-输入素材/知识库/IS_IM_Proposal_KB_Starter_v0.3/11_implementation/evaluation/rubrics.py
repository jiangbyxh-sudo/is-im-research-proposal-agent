"""Human scoring rubrics used by the P0 quality baseline."""
from __future__ import annotations


PROPOSAL_RUBRIC_VERSION = "proposal-human-rubric-1.0.0"
PROPOSAL_RUBRIC = (
    ("evidence_and_citations", "证据忠实与引用完整", 20),
    ("problem_gap_rq", "问题、空白与RQ质量", 15),
    ("theory_and_mechanism", "理论框架与机制一致性", 15),
    ("method_alignment", "方法与RQ对齐及严谨性", 20),
    ("feasibility_ethics", "可行性、伦理和风险", 10),
    ("innovation_contribution", "创新与贡献清晰度", 10),
    ("cross_section_consistency", "跨节结构一致性", 5),
    ("academic_expression", "学术表达与格式", 5),
)

GUIDANCE_RUBRIC_VERSION = "guidance-project-specificity-rubric-1.0.0"
GUIDANCE_RUBRIC = (
    ("deliverable", "本阶段交付物明确", 10),
    ("confirmed_project_content", "引用当前项目已确认内容", 15),
    ("blockers", "阻塞项具体可见", 10),
    ("concrete_steps", "步骤可执行且项目专属", 15),
    ("evidence", "指定应使用的证据", 15),
    ("skeleton", "给出段落或表格骨架", 10),
    ("common_failures", "列出当前项目的常见失败", 10),
    ("self_check", "自检可操作", 10),
    ("next_gate", "下一阶段门槛明确", 5),
)


def blank_human_scorecard(rubric, evaluator: str = "pending_assignment") -> dict:
    return {
        "evaluator": evaluator,
        "scoring_scale": "每项按0–100评分，再按weight加权",
        "dimensions": [
            {
                "dimension_id": dimension_id,
                "label": label,
                "weight": weight,
                "score_0_100": None,
                "evidence": [],
                "notes": "",
            }
            for dimension_id, label, weight in rubric
        ],
        "weighted_total_0_100": None,
        "checkpoint_passed": None,
        "release_status": "NOT_SCORED",
    }


def calculate_weighted_total(scorecard: dict) -> float | None:
    dimensions = scorecard.get("dimensions", [])
    if not dimensions or any(item.get("score_0_100") is None for item in dimensions):
        return None
    total_weight = sum(float(item["weight"]) for item in dimensions)
    if not total_weight:
        return None
    return round(sum(float(item["score_0_100"]) * float(item["weight"]) for item in dimensions) / total_weight, 2)
