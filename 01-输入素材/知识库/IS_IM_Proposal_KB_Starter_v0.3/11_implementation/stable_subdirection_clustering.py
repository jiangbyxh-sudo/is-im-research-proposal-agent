"""Deterministic P2 corpus snapshots and evidence sufficiency gates.

This module deliberately contains no model calls.  It establishes the stable
input contract that clustering, naming athletes, and judges must consume.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Iterable


SNAPSHOT_VERSION = "p2-corpus-snapshot-1.0.0"


@dataclass(frozen=True)
class P2ClusterConfig:
    version: str = "p2-cluster-config-1.0.0"
    requested_clusters: int = 5
    min_papers: int = 30
    min_abstracts: int = 20
    min_cluster_size: int = 3
    random_seed: int = 20260822


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _canonical_paper(paper: dict) -> dict:
    title = _clean_text(paper.get("title"))
    doi = _clean_text(paper.get("doi")).lower()
    source = _clean_text(paper.get("source_title") or paper.get("journal"))
    year = int(paper.get("year") or 0)
    identity_seed = doi or f"{title.casefold()}|{source.casefold()}|{year}"
    paper_id = _clean_text(paper.get("paper_id")) or (
        "p2paper_" + hashlib.sha256(identity_seed.encode("utf-8")).hexdigest()[:20]
    )
    topics = paper.get("topics") or paper.get("openalex_topics") or []
    keywords = paper.get("keywords") or []
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": _clean_text(paper.get("abstract")),
        "year": year,
        "source_title": source,
        "doi": doi,
        "language": _clean_text(paper.get("language")).lower(),
        "citation_count": int(paper.get("citation_count") or 0),
        "topics": topics,
        "keywords": keywords,
        "p1_match_score": paper.get("paper_match_score", paper.get("retrieval_score")),
        "source_quality": paper.get("source_quality"),
    }

def build_corpus_snapshot(
    *,
    direction_id: str,
    papers: Iterable[dict],
    data_cutoff_date: str,
    direction_profile_version: str,
    retrieval_version: str,
    score_version: str,
    p1_precision_gate_passed: bool,
    p1_precision_summary: dict | None = None,
) -> dict:
    canonical_by_id = {}
    for paper in papers:
        canonical = _canonical_paper(paper)
        if canonical["title"]:
            canonical_by_id.setdefault(canonical["paper_id"], canonical)
    canonical_papers = sorted(
        canonical_by_id.values(),
        key=lambda item: (item["paper_id"], item["doi"], item["title"].casefold()),
    )
    corpus_bytes = json.dumps(
        canonical_papers, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "direction_id": direction_id,
        "data_cutoff_date": data_cutoff_date,
        "direction_profile_version": direction_profile_version,
        "retrieval_version": retrieval_version,
        "score_version": score_version,
        "p1_precision_gate_passed": bool(p1_precision_gate_passed),
        "p1_precision_summary": p1_precision_summary or {},
        "paper_count": len(canonical_papers),
        "abstract_count": sum(bool(item["abstract"]) for item in canonical_papers),
        "corpus_hash": hashlib.sha256(corpus_bytes).hexdigest(),
        "papers": canonical_papers,
    }


def assess_corpus_sufficiency(snapshot: dict, config: P2ClusterConfig | None = None) -> dict:
    config = config or P2ClusterConfig()
    paper_count = int(snapshot.get("paper_count") or 0)
    abstract_count = int(snapshot.get("abstract_count") or 0)
    reasons = []
    if paper_count < config.min_papers:
        reasons.append("paper_count_below_30")
    if abstract_count < config.min_abstracts:
        reasons.append("abstract_count_below_20")
    if paper_count < config.requested_clusters * config.min_cluster_size:
        reasons.append("insufficient_rows_for_minimum_cluster_sizes")
    return {
        "status": "P2_CORPUS_READY" if not reasons else "SYNTHESIS_INSUFFICIENT_EVIDENCE",
        "can_output_five_directions": not reasons,
        "paper_count": paper_count,
        "abstract_count": abstract_count,
        "max_clusters_by_size": paper_count // config.min_cluster_size,
        "reasons": reasons,
        "config": asdict(config),
        "corpus_hash": snapshot.get("corpus_hash"),
        "p1_precision_gate_passed": bool(snapshot.get("p1_precision_gate_passed")),
    }
