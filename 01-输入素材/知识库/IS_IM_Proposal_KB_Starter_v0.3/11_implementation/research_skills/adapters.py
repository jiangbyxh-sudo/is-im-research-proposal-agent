"""Thin adapters: translate contracts without changing P1-P4 product decisions."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from citation_graph_provider import CitationExpansionRequest
from gap_falsification import (
    EvidenceBoundGapFalsificationProvider,
    GapFalsificationRequest,
    build_gap_falsification_query_plan,
)
from fulltext_evidence_provider import FulltextExtractionRequest
from multi_perspective_search_plan import build_multi_perspective_search_plan
from paper_discovery_provider import DiscoveryRequest
from proposal_generation_provider import ProposalRequest
from research_gap_provider import EvidenceBoundResearchGapProvider, ResearchGapRequest
from research_synthesis_provider import SynthesisRequest
from retrieval_saturation import SaturationConfig, evaluate_retrieval_saturation

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


def _positive_int(payload: Mapping[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool):
        raise SkillInputError(f"{key}_must_be_positive_integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SkillInputError(f"{key}_must_be_positive_integer") from exc
    if parsed < 1:
        raise SkillInputError(f"{key}_must_be_positive_integer")
    return parsed


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


class P1MultiPerspectiveSearchPlanAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p1.multi_perspective_search_plan",
        version="1.0.0",
        stage="P1",
        description="Build deterministic phenomenon/theory/mechanism/context/method discovery queries.",
        deterministic=True,
        external_network=False,
    )

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        profile = payload.get("profile")
        if not isinstance(profile, dict):
            raise SkillInputError("profile_must_be_object")
        plan = build_multi_perspective_search_plan(profile, payload.get("fine_grained_question"))
        status = SkillRunStatus.COMPLETE if not plan["missing_perspectives"] else SkillRunStatus.PARTIAL
        return AdapterExecution(
            result_status=status,
            upstream_status="SEARCH_PLAN_READY" if status == SkillRunStatus.COMPLETE else "SEARCH_PLAN_PARTIAL",
            output=plan,
            limitations=[f"missing_perspective:{item}" for item in plan["missing_perspectives"]],
            provenance={"profile_version": plan["profile_version"], "plan_hash": plan["plan_hash"]},
            audit={"discovery_only": True, "changes_p1_thresholds": False},
        )


class P1CitationExpansionSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p1.citation_graph_expansion",
        version="1.0.0",
        stage="P1",
        description="Expand bounded citation neighbors as P1 re-evaluation candidates.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, provider) -> None:
        self.provider = provider

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        result = self.provider.expand(CitationExpansionRequest(
            seed_papers=_tuple_dicts(payload.get("seed_papers")),
            direction=str(payload.get("direction") or "both"),
            max_seeds=_positive_int(payload, "max_seeds", 5),
            max_neighbors_per_seed=_positive_int(payload, "max_neighbors_per_seed", 25),
        ))
        if result.status == "CITATION_EXPANSION_COMPLETE":
            status = SkillRunStatus.COMPLETE
        elif result.status == "CITATION_EXPANSION_PARTIAL":
            status = SkillRunStatus.PARTIAL
        else:
            status = SkillRunStatus.BLOCKED
        return AdapterExecution(
            result_status=status,
            upstream_status=result.status,
            output=asdict(result),
            limitations=list(result.limitations),
            provenance={"provider_log": result.provider_log},
            audit=result.audit,
            cacheable=False,
        )


class P1CitationVerificationSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p1.citation_verification",
        version="1.0.0",
        stage="P1",
        description="Verify candidate identifiers and canonical metadata without deciding relevance.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, verifier) -> None:
        self.verifier = verifier

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        result = self.verifier.verify(list(_tuple_dicts(payload.get("candidates"))))
        status = SkillRunStatus.PARTIAL if result.status == "CITATION_VERIFICATION_PARTIAL" else SkillRunStatus.COMPLETE
        return AdapterExecution(
            result_status=status,
            upstream_status=result.status,
            output=asdict(result),
            provenance={"provider_log": result.provider_log},
            audit=result.audit,
            cacheable=False,
        )


class P1RetrievalSaturationSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p1.retrieval_saturation",
        version="1.0.0",
        stage="P1",
        description="Compute advisory repeat and new-direct yield across discovery rounds.",
        deterministic=True,
        external_network=False,
    )

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        rounds = payload.get("rounds")
        if not isinstance(rounds, list) or not all(isinstance(item, dict) for item in rounds):
            raise SkillInputError("rounds_must_be_list_of_objects")
        config_payload = payload.get("config") or {}
        if not isinstance(config_payload, dict):
            raise SkillInputError("config_must_be_object")
        try:
            config = SaturationConfig(**config_payload)
        except TypeError as exc:
            raise SkillInputError("invalid_saturation_config") from exc
        if config.window_rounds < 1 or config.max_new_direct_per_round < 0 or not 0.0 <= config.min_repeat_ratio <= 1.0:
            raise SkillInputError("invalid_saturation_config")
        result = evaluate_retrieval_saturation(rounds, config)
        status = SkillRunStatus.PARTIAL if result["status"] == "SATURATION_INSUFFICIENT_ROUNDS" else SkillRunStatus.COMPLETE
        return AdapterExecution(
            result_status=status,
            upstream_status=result["status"],
            output=result,
            audit={"advisory_only": True, "changes_p1_thresholds": False},
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


class P3FulltextEvidenceExtractionSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p3.fulltext_evidence_extraction",
        version="1.0.0",
        stage="P3",
        description="Extract sentence-level full-text evidence through an optional GROBID sidecar.",
        deterministic=False,
        external_network=True,
    )

    def __init__(self, provider) -> None:
        self.provider = provider

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        pdf_path = payload.get("pdf_path")
        paper_id = str(payload.get("paper_id") or "").strip()
        if not isinstance(pdf_path, str) or not pdf_path.strip():
            raise SkillInputError("pdf_path_must_be_nonempty_string")
        if not paper_id:
            raise SkillInputError("paper_id_required")
        result = self.provider.extract(FulltextExtractionRequest(
            pdf_path=Path(pdf_path),
            paper_id=paper_id,
            title=str(payload.get("title") or ""),
            max_pdf_bytes=_positive_int(payload, "max_pdf_bytes", 50 * 1024 * 1024),
        ))
        if result.status == "FULLTEXT_EVIDENCE_READY":
            status = SkillRunStatus.COMPLETE
        elif result.status in {
            "FULLTEXT_SERVICE_NOT_CONFIGURED",
            "FULLTEXT_SERVICE_UNAVAILABLE",
            "FULLTEXT_EXTRACTION_EMPTY",
        }:
            status = SkillRunStatus.BLOCKED
        else:
            status = SkillRunStatus.FAILED
        return AdapterExecution(
            result_status=status,
            upstream_status=result.status,
            output=asdict(result),
            limitations=list(result.limitations),
            provenance={
                "provider": "grobid",
                "matrix_hash": result.evidence_matrix.get("matrix_hash"),
            },
            audit={
                **result.audit,
                "title_level_fallback_used": False,
                "source_path_emitted": False,
            },
            cacheable=False,
        )


class P3GapFalsificationPlanSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p3.gap_falsification_plan",
        version="1.0.0",
        stage="P3",
        description="Build deterministic direct-solution, contradiction, alternative and boundary searches.",
        deterministic=True,
        external_network=False,
    )

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        gap = payload.get("gap")
        profile = payload.get("direction_profile") or {}
        if not isinstance(gap, dict) or not isinstance(profile, dict):
            raise SkillInputError("gap_and_direction_profile_must_be_objects")
        plan = build_gap_falsification_query_plan(gap, profile)
        return AdapterExecution(
            result_status=SkillRunStatus.COMPLETE,
            upstream_status="GAP_FALSIFICATION_PLAN_READY",
            output=plan,
            provenance={"gap_id": plan["gap_id"], "plan_hash": plan["plan_hash"]},
            audit={"discovery_only": True, "p1_direct_required": True, "changes_p1_thresholds": False},
        )


class P3GapFalsificationEvaluationSkillAdapter:
    descriptor = ResearchSkillDescriptor(
        skill_id="p3.gap_falsification_evaluation",
        version="1.0.0",
        stage="P3",
        description="Evaluate P1-direct falsification findings bound to abstract/fulltext spans.",
        deterministic=True,
        external_network=False,
    )

    def __init__(self, provider=None) -> None:
        self.provider = provider or EvidenceBoundGapFalsificationProvider()

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution:
        gap = payload.get("gap")
        matrix = payload.get("evidence_matrix")
        if not isinstance(gap, dict) or not isinstance(matrix, dict):
            raise SkillInputError("gap_and_evidence_matrix_must_be_objects")
        result = self.provider.evaluate(GapFalsificationRequest(
            gap=gap,
            findings=_tuple_dicts(payload.get("findings")),
            evidence_matrix=matrix,
            search_status=str(payload.get("search_status") or "COMPLETE"),
            search_audit=dict(payload.get("search_audit") or {}),
        ))
        if result.status == "GAP_FALSIFICATION_BLOCKED":
            status = SkillRunStatus.BLOCKED
        elif result.status == "GAP_FALSIFICATION_PARTIAL":
            status = SkillRunStatus.PARTIAL
        else:
            status = SkillRunStatus.COMPLETE
        return AdapterExecution(
            result_status=status,
            upstream_status=result.status,
            output=asdict(result),
            limitations=list(result.limitations),
            provenance={"gap_id": result.gap_id},
            audit=result.audit,
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
    citation_graph_provider=None,
    citation_verifier=None,
    fulltext_provider=None,
) -> ResearchSkillRegistry:
    registry = ResearchSkillRegistry()
    registry.register(P1MultiPerspectiveSearchPlanAdapter())
    registry.register(P1RetrievalSaturationSkillAdapter())
    if p1_provider is not None:
        registry.register(P1DiscoverySkillAdapter(p1_provider))
    if citation_graph_provider is not None:
        registry.register(P1CitationExpansionSkillAdapter(citation_graph_provider))
    if citation_verifier is not None:
        registry.register(P1CitationVerificationSkillAdapter(citation_verifier))
    if p2_provider is not None:
        registry.register(P2ClusteringSkillAdapter(p2_provider))
    if fulltext_provider is not None:
        registry.register(P3FulltextEvidenceExtractionSkillAdapter(fulltext_provider))
    registry.register(P3EvidenceGapSkillAdapter(p3_provider))
    registry.register(P3GapFalsificationPlanSkillAdapter())
    registry.register(P3GapFalsificationEvaluationSkillAdapter())
    if p4_provider is not None:
        registry.register(P4ControlledProposalSkillAdapter(p4_provider))
    return registry
