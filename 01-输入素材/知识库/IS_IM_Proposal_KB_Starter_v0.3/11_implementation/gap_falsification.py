"""Deterministic gap-falsification queries and evidence-bound verdicts."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from claim_store import ClaimStore
from evidence_matrix import validate_formal_span


GAP_FALSIFICATION_VERSION = "gap-falsification-1.0.0"
FALSIFICATION_ROLES = (
    "direct_solution", "contradictory_finding", "alternative_explanation", "boundary_condition",
)
CLAIM_ROLE_MAP = {
    "direct_solution": "falsification",
    "contradictory_finding": "counterevidence",
    "alternative_explanation": "alternative_explanation",
    "boundary_condition": "boundary",
}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _is_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def build_gap_falsification_query_plan(gap: dict, direction_profile: dict | None = None) -> dict:
    gap_id = _clean(gap.get("gap_id"))
    statement = _clean(gap.get("gap_statement"))
    research_question = _clean(gap.get("research_question"))
    if not gap_id or not statement or not research_question:
        raise ValueError("gap_id_statement_and_research_question_required")
    profile = direction_profile or {}
    core = next((_clean(item) for item in (profile.get("facets") or {}).get("core_phenomena", []) if _clean(item)), "")
    base = research_question or statement
    if _is_chinese(base):
        suffixes = {
            "direct_solution": "已有解决方案 已验证方法",
            "contradictory_finding": "无效应 相反结果 不一致证据",
            "alternative_explanation": "替代解释 混杂机制",
            "boundary_condition": "边界条件 调节效应 情境限制",
        }
        language = "zh"
    else:
        suffixes = {
            "direct_solution": "existing solution validated approach",
            "contradictory_finding": "null effect contradictory inconsistent evidence",
            "alternative_explanation": "alternative explanation confounding mechanism",
            "boundary_condition": "boundary condition moderator contextual limitation",
        }
        language = "en"
    queries = [
        {
            "query_id": f"falsify_{index:02d}_{role}",
            "role": role,
            "language": language,
            "query": _clean(f"{core} {base} {suffixes[role]}"),
            "selection_requirement": "existing_P1_direct_only",
        }
        for index, role in enumerate(FALSIFICATION_ROLES, start=1)
    ]
    payload = {
        "version": GAP_FALSIFICATION_VERSION,
        "gap_id": gap_id,
        "queries": queries,
        "required_roles": list(FALSIFICATION_ROLES),
        "discovery_only": True,
        "selection_policy": "results_must_pass_existing_P1_as_direct_before_evidence_assessment",
        "title_level_evidence_allowed": False,
        "changes_p1_thresholds": False,
    }
    payload["plan_hash"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


@dataclass(frozen=True)
class GapFalsificationRequest:
    gap: dict
    findings: tuple[dict, ...]
    evidence_matrix: dict
    search_status: str = "COMPLETE"
    search_audit: dict = field(default_factory=dict)


@dataclass
class GapFalsificationResult:
    status: str
    gap_id: str
    accepted_findings: list[dict] = field(default_factory=list)
    rejected_findings: list[dict] = field(default_factory=list)
    falsification_claim_store: dict = field(default_factory=dict)
    recommendation: str = ""
    limitations: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)


class EvidenceBoundGapFalsificationProvider:
    """Evaluate only already-screened direct findings with L1/L2 span bindings."""

    def evaluate(self, request: GapFalsificationRequest) -> GapFalsificationResult:
        gap_id = _clean(request.gap.get("gap_id"))
        if not gap_id:
            return GapFalsificationResult(status="GAP_FALSIFICATION_BLOCKED", gap_id="", limitations=["gap_id_required"])
        if request.search_status not in {"COMPLETE", "PARTIAL"}:
            return GapFalsificationResult(
                status="GAP_FALSIFICATION_BLOCKED", gap_id=gap_id,
                limitations=["search_status_must_be_COMPLETE_or_PARTIAL"],
            )
        store = ClaimStore(request.evidence_matrix)
        accepted, rejected = [], []
        for index, finding in enumerate(request.findings, start=1):
            finding_id = _clean(finding.get("finding_id")) or f"finding_{index:03d}"
            try:
                role = _clean(finding.get("role"))
                if role not in FALSIFICATION_ROLES:
                    raise ValueError("invalid_falsification_role")
                if finding.get("relevance_tier") != "direct":
                    raise ValueError("falsification_finding_requires_existing_p1_direct")
                statement = _clean(finding.get("statement"))
                paper_id = _clean(finding.get("paper_id"))
                span_id = _clean(finding.get("evidence_span_id"))
                if not statement or not paper_id or not span_id:
                    raise ValueError("finding_requires_statement_paper_and_evidence_span")
                citation_verdict = _clean(finding.get("citation_verdict"))
                if citation_verdict in {"MISMATCH", "RETRACTED", "UNRESOLVED"}:
                    raise ValueError(f"citation_{citation_verdict.casefold()}")
                validate_formal_span(request.evidence_matrix, span_id, paper_id)
                claim = store.add_formal_claim(
                    statement,
                    [{"paper_id": paper_id, "evidence_span_id": span_id}],
                    role=CLAIM_ROLE_MAP[role],
                )
                accepted.append({
                    "finding_id": finding_id,
                    "role": role,
                    "statement": statement,
                    "claim_id": claim["claim_id"],
                    "paper_id": paper_id,
                    "evidence_span_id": span_id,
                })
            except (TypeError, ValueError, KeyError) as exc:
                rejected.append({"finding_id": finding_id, "reason": str(exc)})

        roles = {item["role"] for item in accepted}
        limitations = []
        if "direct_solution" in roles:
            status, recommendation = "GAP_FALSIFIED", "DOWNGRADE_FORMAL_GAP"
        elif request.search_status == "PARTIAL":
            status, recommendation = "GAP_FALSIFICATION_PARTIAL", "RETRY_FAILED_SEARCH_LEGS"
            limitations.append("partial_search_cannot_confirm_gap_survival")
        elif "contradictory_finding" in roles:
            status, recommendation = "GAP_CHALLENGED", "REVISE_SCOPE_AND_REPEAT_SEARCH"
        elif roles.intersection({"alternative_explanation", "boundary_condition"}):
            status, recommendation = "GAP_NARROWED", "REVISE_GAP_SCOPE"
        else:
            status, recommendation = "GAP_SURVIVES_FALSIFICATION", "RETAIN_WITH_ABSENCE_OF_EVIDENCE_CAVEAT"
            limitations.append("absence_of_falsifying_evidence_is_not_proof_of_novelty")
        claim_payload = store.as_dict()
        claim_audit = store.audit()
        return GapFalsificationResult(
            status=status,
            gap_id=gap_id,
            accepted_findings=accepted,
            rejected_findings=rejected,
            falsification_claim_store=claim_payload,
            recommendation=recommendation,
            limitations=limitations,
            audit={
                "version": GAP_FALSIFICATION_VERSION,
                "search_status": request.search_status,
                "search_audit": request.search_audit,
                "finding_count": len(request.findings),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "accepted_roles": sorted(roles),
                "claim_store_valid": claim_audit["valid"],
                "title_level_evidence_allowed": False,
                "p1_direct_required": True,
                "formal_gap_minimum_changed": False,
                "gap_mutated_automatically": False,
            },
        )
