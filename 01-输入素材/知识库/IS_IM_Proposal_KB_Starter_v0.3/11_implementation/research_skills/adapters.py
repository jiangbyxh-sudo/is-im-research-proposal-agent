"""Thin adapters: translate contracts without changing P1-P4 product decisions."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from paper_discovery_provider import DiscoveryRequest
from proposal_generation_provider import ProposalRequest
from research_gap_provider import EvidenceBoundResearchGapProvider, ResearchGapRequest
from research_synthesis_provider import SynthesisRequest

from .contracts import (
    AdapterExecution,
    ResearchSkillContext,
    ResearchSkillDescriptor,
    SkillInputError,
    SkillRunStatus,
)
from .registry import ResearchSkillRegistry


def _tuple_dicts(value: object) -> tuple[dict, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, dict) for item in value):
        raise SkillInputError("expected_list_of_objects")
    return tuple(value)


def _strict_bool(payload: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise SkillInputError(f"{key}_must_be_boolean")
    return value


class P1DiscoverySkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p1.paper_discovery",
        version="1.0.0",
        stage="P1",
        description="Run existing direct/adjacent discovery without changing selection policy.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, provider) -> None:
        self.provider = provider

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        request = DiscoveryRequest(
            selected_direction_id=str(payload.get("selected_direction_id") or ""),
            research_direction=str(payload.get("research_direction") or ""),
            fine_grained_question=payload.get("fine_grained_question"),
            chinese_count=int(payload.get("chinese_count", 10)),
            english_count=int(payload.get("english_count", 20)),
            popularity_window_years=int(payload.get("popularity_window_years", 5)),
            journal_pool_ids=tuple(payload.get("journal_pool_ids") or ()),
            query_by_language=dict(payload.get("query_by_language") or {}),
            source_tier_pool_ids={key: tuple(value) for key, value in dict(payload.get("source_tier_pool_ids") or {}).items()},
        )
        upstream = self.provider.discover(request)
        data = asdict(upstream)
        status = {
            "RETRIEVAL_COMPLETE": SkillRunStatus.COMPLETE,
            "RETRIEVAL_PARTIAL": SkillRunStatus.PARTIAL,
            "DYNAMIC_RETRIEVAL_UNAVAILABLE": SkillRunStatus.BLOCKED,
            "JOURNAL_ROUTE_UNAVAILABLE": SkillRunStatus.BLOCKED,
        }.get(upstream.status, SkillRunStatus.FAILED)
        return AdapterExecution(
            result_status=status,
            upstream_status=upstream.status,
            output=data,
            limitations=[upstream.message_to_user] if status != SkillRunStatus.COMPLETE and upstream.message_to_user else [],
            provenance={"provider_statuses": upstream.provider_statuses},
            audit={
                "coverage_audit": upstream.coverage_audit,
                "formal_papers_only_direct": all(item.get("relevance_tier") == "direct" for item in upstream.papers),
                "adjacent_returned_separately": True,
                "upstream_score_config_version": upstream.score_config_version,
            },
            cacheable=False,
        )


class P2ClusteringSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p2.deterministic_clustering",
        version="1.0.0",
        stage="P2",
        description="Run direct-only deterministic clustering and fixed-membership naming.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, provider) -> None:
        self.provider = provider

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        request = SynthesisRequest(
            research_direction=str(payload.get("research_direction") or ""),
            fine_grained_question=payload.get("fine_grained_question"),
            derived_path=str(payload.get("derived_path") or "popular"),
            papers=_tuple_dicts(payload.get("papers")),
            p1_precision_gate_passed=_strict_bool(payload, "p1_precision_gate_passed"),
            p1_precision_summary=dict(payload.get("p1_precision_summary") or {}),
            data_cutoff_date=str(payload.get("data_cutoff_date") or ""),
            direction_profile_version=str(payload.get("direction_profile_version") or "unknown"),
            retrieval_version=str(payload.get("retrieval_version") or "unknown"),
            score_version=str(payload.get("score_version") or "unknown"),
        )
        upstream = self.provider.synthesize(request)
        data = asdict(upstream)
        if upstream.status == "SYNTHESIS_COMPLETE":
            status = SkillRunStatus.COMPLETE
        elif upstream.status in {"P2_BLOCKED_BY_P1_PRECISION", "SYNTHESIS_INSUFFICIENT_EVIDENCE", "SYNTHESIS_NOT_CONFIGURED"}:
            status = SkillRunStatus.BLOCKED
        else:
            status = SkillRunStatus.FAILED
        return AdapterExecution(
            result_status=status,
            upstream_status=upstream.status,
            output=data,
            limitations=list(upstream.limitations),
            provenance={"corpus_hash": upstream.audit.get("corpus_hash")},
            audit={**upstream.audit, "paper_membership_owned_by_llm": False},
            cacheable=False,
        )


class P3EvidenceGapSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p3.evidence_bound_gaps",
        version="1.0.0",
        stage="P3",
        description="Formalize gaps only through the existing Evidence Matrix and Claim Store.",
        deterministic=True,
        external_network=False,
    )

    def __init__(self, provider=None) -> None:
        self.provider = provider or EvidenceBoundResearchGapProvider()

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        request = ResearchGapRequest(
            cluster_id=str(payload.get("cluster_id") or ""),
            gap_candidates=_tuple_dicts(payload.get("gap_candidates")),
            evidence_matrix=dict(payload.get("evidence_matrix") or {}),
        )
        upstream = self.provider.formalize(request)
        data = asdict(upstream)
        status = SkillRunStatus.COMPLETE if upstream.status == "RESEARCH_GAPS_READY" else SkillRunStatus.BLOCKED
        return AdapterExecution(
            result_status=status,
            upstream_status=upstream.status,
            output=data,
            limitations=[item.get("reason", "gap_rejected") for item in upstream.rejected_candidates],
            provenance={"evidence_matrix_id": request.evidence_matrix.get("matrix_id")},
            audit={**upstream.audit, "formal_gap_minimum_changed": False},
        )


class P4ControlledProposalSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p4.controlled_proposal",
        version="1.0.0",
        stage="P4",
        description="Run the existing blueprint-confirmed, Claim-Store-only proposal workflow.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, provider) -> None:
        self.provider = provider

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        request = ProposalRequest(
            research_direction=str(payload.get("research_direction") or ""),
            fine_grained_question=payload.get("fine_grained_question"),
            selected_gap=dict(payload.get("selected_gap") or {}),
            selected_innovation_id=str(payload.get("selected_innovation_id") or ""),
            selected_innovation=str(payload.get("selected_innovation") or ""),
            papers=_tuple_dicts(payload.get("papers")),
            claim_store=dict(payload.get("claim_store") or {}),
            research_design_blueprint=payload.get("research_design_blueprint"),
            blueprint_confirmed=_strict_bool(payload, "blueprint_confirmed"),
        )
        upstream = self.provider.generate(request)
        data = asdict(upstream)
        if upstream.status == "READY_FOR_HUMAN_REVIEW":
            status = SkillRunStatus.COMPLETE
        elif upstream.status in {
            "RESEARCH_SKETCH_ONLY", "BLUEPRINT_CONFIRMATION_REQUIRED", "PROPOSAL_CONTROLLED_PARTIAL",
        }:
            status = SkillRunStatus.PARTIAL
        elif upstream.status in {"PROPOSAL_NOT_CONFIGURED", "PROPOSAL_PARADIGM_MISSING", "BLUEPRINT_INVALID"}:
            status = SkillRunStatus.BLOCKED
        else:
            status = SkillRunStatus.FAILED
        return AdapterExecution(
            result_status=status,
            upstream_status=upstream.status,
            output=data,
            limitations=list(upstream.limitations),
            provenance={"blueprint_id": upstream.proposal_context.get("research_design_blueprint", {}).get("blueprint_id")},
            audit={**upstream.audit, "ready_state_ceiling": "READY_FOR_HUMAN_REVIEW"},
            cacheable=False,
        )


def build_default_registry(
    *,
    p1_provider=None,
    p2_provider=None,
    p3_provider=None,
    p4_provider=None,
) -> ResearchSkillRegistry:
    registry = ResearchSkillRegistry()
    if p1_provider is not None:
        registry.register(P1DiscoverySkillAdapter(p1_provider))
    if p2_provider is not None:
        registry.register(P2ClusteringSkillAdapter(p2_provider))
    registry.register(P3EvidenceGapSkillAdapter(p3_provider))
    if p4_provider is not None:
        registry.register(P4ControlledProposalSkillAdapter(p4_provider))
    return registry
