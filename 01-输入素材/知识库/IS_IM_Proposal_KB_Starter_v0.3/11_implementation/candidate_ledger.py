"""Single-path candidate decisions and count-conserving P1 traces."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from paper_quality import evaluate_boundary, qualify_source, quality_gate, score_record


RELEVANCE_TIERS = {"direct", "adjacent", "reject", "manual"}
TERMINAL_STATUSES = {"gate_reject", "rank_reject", "boundary", "eligible", "adjacent", "manual_review"}


@dataclass(frozen=True)
class CandidateDecision:
    paper_id: str
    terminal_status: str
    reasons: tuple[str, ...]
    checkpoint: dict
    retrieval_score: dict | None
    boundary_evidence: dict
    source_tier: str
    relevance_tier: str

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        return payload


def evaluate_candidate(
    record: dict,
    profile: dict,
    journal_index: dict,
    from_year: int,
    to_year: int,
    query_context: dict,
) -> CandidateDecision:
    """Give one deduplicated paper exactly one terminal decision."""
    qualify_source(record, journal_index, set(profile.get("journal_pool_ids", [])), profile)
    passed, gate_reasons = quality_gate(record, profile, from_year, to_year)
    checkpoint = {"passed": passed, "reasons": gate_reasons, "version": "p1-hard-gate-2.0.0"}
    boundary = evaluate_boundary(record, profile)
    score = None
    reasons = list(gate_reasons)
    relevance_tier = boundary.relevance_tier
    if not passed:
        terminal = "gate_reject"
        relevance_tier = "reject"
    elif record.get("source_tier") == "UNKNOWN":
        terminal = "manual_review"
        relevance_tier = "manual"
        reasons.append("unknown_source_requires_review")
    elif boundary.relevance_tier == "manual":
        terminal = "manual_review"
        reasons.extend(boundary.missing_required_facets)
    elif boundary.relevance_tier == "reject":
        terminal = "boundary"
        reasons.extend(boundary.missing_required_facets or ("excluded_context",))
    else:
        score = score_record(
            record,
            profile,
            query_context.get("query") or profile["labels"]["en"],
            from_year,
            to_year,
        )
        if boundary.relevance_tier == "direct":
            terminal = "eligible"
        else:
            terminal = "adjacent"
            reasons.append("adjacent_not_formal_paper")
    if relevance_tier not in RELEVANCE_TIERS:
        raise AssertionError(f"unknown relevance tier: {relevance_tier}")
    if terminal not in TERMINAL_STATUSES:
        raise AssertionError(f"unknown terminal status: {terminal}")
    record["checkpoint"] = checkpoint
    record["boundary_evidence"] = boundary.as_dict()
    record["retrieval_score"] = score
    record["score"] = score
    record["relevance_score"] = score["total"] if score else 0.0
    record["focality_score"] = boundary.focality_score
    record["relevance_tier"] = relevance_tier
    record["terminal_status"] = terminal
    record["terminal_reasons"] = list(dict.fromkeys(reasons))
    return CandidateDecision(
        paper_id=record["paper_id"],
        terminal_status=terminal,
        reasons=tuple(record["terminal_reasons"]),
        checkpoint=checkpoint,
        retrieval_score=score,
        boundary_evidence=boundary.as_dict(),
        source_tier=record.get("source_tier", "UNKNOWN"),
        relevance_tier=relevance_tier,
    )


def build_candidate_trace(record: dict, decision: CandidateDecision) -> dict:
    return {
        "paper_id": record["paper_id"],
        "title": record.get("title"),
        "providers": record.get("providers", []),
        "query_lane_ids": record.get("query_lane_ids", []),
        "source_identity": {
            "source_id": record.get("source_id"),
            "journal_id": record.get("journal_id"),
            "source_title": record.get("source_title"),
            "issns": record.get("source_issns", []),
        },
        "normalization": {
            "language": record.get("language"),
            "document_type": record.get("document_type"),
            "doi": record.get("doi"),
        },
        "dedupe": {"canonical_paper_id": record["paper_id"]},
        "topic_evidence": {
            "primary_topic": record.get("primary_topic", {}),
            "topics": record.get("topics", []),
            "keywords": record.get("keywords", []),
        },
        "boundary_evidence": decision.boundary_evidence,
        "source_tier": decision.source_tier,
        "source_quality": record.get("source_quality"),
        "source_direction_fit": record.get("source_direction_fit"),
        "content_relevance": (decision.retrieval_score or {}).get("total"),
        "focality_score": record.get("focality_score"),
        "relevance_tier": decision.relevance_tier,
        "checkpoint": decision.checkpoint,
        "retrieval_score": decision.retrieval_score,
        "rerank": decision.retrieval_score,
        "evidence": {
            "oa_pdf_url": record.get("oa_pdf_url"),
            "oa_landing_page_url": record.get("oa_landing_page_url"),
            "doi_landing_url": record.get("doi_landing_url"),
            "verified_fulltext_available": record.get("verified_fulltext_available", False),
        },
        "terminal_status": decision.terminal_status,
        "terminal_reasons": list(decision.reasons),
    }


def ledger_summary(records: list[dict], selected: list[dict]) -> dict:
    counts = {status: 0 for status in sorted(TERMINAL_STATUSES)}
    for record in records:
        status = record.get("terminal_status")
        if status not in counts:
            raise AssertionError(f"candidate missing unique terminal status: {record.get('paper_id')}")
        counts[status] += 1
    terminal_total = sum(counts.values())
    selected_ids = {record["paper_id"] for record in selected}
    eligible_ids = {record["paper_id"] for record in records if record.get("terminal_status") == "eligible"}
    summary = {
        "deduplicated_count": len(records),
        **{f"{status}_count": count for status, count in counts.items()},
        "selected_count": len(selected_ids),
        "candidate_trace_count": len(records),
        "terminal_count": terminal_total,
        "count_conserved": terminal_total == len(records),
        "selected_is_eligible_subset": selected_ids.issubset(eligible_ids),
        "retracted_in_selected": sum(record.get("integrity_status") == "retracted" for record in selected),
        "direct_count": sum(record.get("relevance_tier") == "direct" for record in records),
        "adjacent_relevance_count": sum(record.get("relevance_tier") == "adjacent" for record in records),
        "manual_relevance_count": sum(record.get("relevance_tier") == "manual" for record in records),
        "reject_relevance_count": sum(record.get("relevance_tier") == "reject" for record in records),
    }
    if not summary["count_conserved"] or not summary["selected_is_eligible_subset"]:
        raise AssertionError(f"candidate ledger conservation failed: {summary}")
    return summary
