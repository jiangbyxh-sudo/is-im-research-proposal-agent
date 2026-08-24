"""P3 research-gap formalization over an evidence matrix and Claim Store."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from claim_store import ClaimStore
from evidence_matrix import evidence_indexes, validate_formal_span


RESEARCH_GAP_VERSION = "p3-evidence-bound-gap-1.0.0"


@dataclass(frozen=True)
class ResearchGapRequest:
    cluster_id: str
    gap_candidates: tuple[dict, ...]
    evidence_matrix: dict


@dataclass
class ResearchGapResult:
    status: str
    formal_gaps: list[dict] = field(default_factory=list)
    rejected_candidates: list[dict] = field(default_factory=list)
    claim_store: dict = field(default_factory=dict)
    audit: dict = field(default_factory=dict)


def _bindings(matrix: dict, span_ids: list[str]) -> list[dict]:
    _, span_index = evidence_indexes(matrix)
    bindings = []
    for span_id in span_ids:
        span = span_index.get(str(span_id))
        if not span:
            raise ValueError("evidence_span_not_found")
        validate_formal_span(matrix, span["span_id"], span["paper_id"])
        bindings.append({"paper_id": span["paper_id"], "evidence_span_id": span["span_id"]})
    return bindings


def _method_is_feasible(method: object) -> bool:
    return isinstance(method, dict) and all(str(method.get(key) or "").strip() for key in ("design", "data", "analysis"))


class EvidenceBoundResearchGapProvider:
    """Accept candidate wording only after deterministic evidence gates pass."""

    def formalize(self, request: ResearchGapRequest) -> ResearchGapResult:
        store = ClaimStore(request.evidence_matrix)
        formal_gaps = []
        rejected = []
        for index, candidate in enumerate(request.gap_candidates, start=1):
            candidate_id = str(candidate.get("candidate_id") or f"candidate_{index:03d}")
            try:
                statement = str(candidate.get("gap_statement") or "").strip()
                if not statement:
                    raise ValueError("gap_statement_missing")
                support_bindings = _bindings(request.evidence_matrix, list(candidate.get("evidence_span_ids") or []))
                if len({item["paper_id"] for item in support_bindings}) < 2:
                    raise ValueError("formal_gap_requires_two_abstract_or_fulltext_papers")
                alternatives = [str(value).strip() for value in candidate.get("alternative_explanations", []) if str(value).strip()]
                if not alternatives:
                    raise ValueError("alternative_explanation_missing")
                research_question = str(candidate.get("research_question") or "").strip()
                if not research_question:
                    raise ValueError("research_question_missing")
                method = candidate.get("feasible_method")
                if not _method_is_feasible(method):
                    raise ValueError("feasible_method_requires_design_data_analysis")
                counter_rows = candidate.get("counterevidence") or []
                if not isinstance(counter_rows, list) or not counter_rows:
                    raise ValueError("counterevidence_missing")

                prepared_counters = []
                for counter in counter_rows:
                    counter_statement = str(counter.get("statement") or "").strip()
                    if not counter_statement:
                        raise ValueError("counterevidence_statement_missing")
                    counter_bindings = _bindings(request.evidence_matrix, list(counter.get("evidence_span_ids") or []))
                    if not counter_bindings:
                        raise ValueError("counterevidence_requires_formal_span")
                    prepared_counters.append((counter_statement, counter_bindings))
                support_claim = store.add_formal_claim(statement, support_bindings, role="support")
                counter_claims = [
                    store.add_formal_claim(counter_statement, counter_bindings, role="counterevidence")
                    for counter_statement, counter_bindings in prepared_counters
                ]
                gap_seed = f"{request.cluster_id}|{statement}|{support_claim['claim_id']}"
                gap_id = "gap_" + hashlib.sha256(gap_seed.encode("utf-8")).hexdigest()[:20]
                formal_gaps.append({
                    "gap_id": gap_id,
                    "cluster_id": request.cluster_id,
                    "subdirection_id": str(candidate.get("subdirection_id") or request.cluster_id),
                    "gap_statement": statement,
                    "support_claim_id": support_claim["claim_id"],
                    "supporting_paper_ids": sorted({item["paper_id"] for item in support_bindings}),
                    "counterevidence_claim_ids": [claim["claim_id"] for claim in counter_claims],
                    "alternative_explanations": alternatives,
                    "research_question": research_question,
                    "why_it_matters": str(candidate.get("why_it_matters") or "").strip(),
                    "innovation_candidates": [
                        str(value).strip() for value in candidate.get("innovation_candidates", [])
                        if str(value).strip()
                    ],
                    "feasible_method": {
                        "design": str(method["design"]).strip(),
                        "data": str(method["data"]).strip(),
                        "analysis": str(method["analysis"]).strip(),
                        "unit_of_analysis": str(method.get("unit_of_analysis") or "").strip(),
                        "context": str(method.get("context") or "").strip(),
                        "feasibility_constraints": [
                            str(value).strip() for value in method.get("feasibility_constraints", []) if str(value).strip()
                        ],
                    },
                    "formal": True,
                    "evidence_gate": "minimum_two_L1_or_L2_papers",
                })
            except (TypeError, ValueError, KeyError) as exc:
                rejected.append({"candidate_id": candidate_id, "reason": str(exc)})
        claim_payload = store.as_dict()
        claim_audit = store.audit()
        status = "RESEARCH_GAPS_READY" if formal_gaps else "RESEARCH_GAPS_INSUFFICIENT_EVIDENCE"
        return ResearchGapResult(
            status=status,
            formal_gaps=formal_gaps,
            rejected_candidates=rejected,
            claim_store=claim_payload,
            audit={
                "version": RESEARCH_GAP_VERSION,
                "candidate_count": len(request.gap_candidates),
                "formal_gap_count": len(formal_gaps),
                "rejected_count": len(rejected),
                "claim_store_valid": claim_audit["valid"],
                "title_level_evidence_allowed": False,
            },
        )
