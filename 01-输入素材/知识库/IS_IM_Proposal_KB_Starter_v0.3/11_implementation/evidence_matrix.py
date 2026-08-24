"""Build sentence-level L1/L2 evidence matrices from abstracts and full text."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass


EVIDENCE_MATRIX_VERSION = "p3-evidence-matrix-1.0.0"
FORMAL_EVIDENCE_LEVELS = {"abstract", "fulltext"}


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    paper_id: str
    evidence_level: str
    source_field: str
    start_char: int
    end_char: int
    text: str

    def as_dict(self) -> dict:
        return asdict(self)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sentence_offsets(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in re.finditer(r"[^.!?。！？\n]+(?:[.!?。！？]+|$)", text):
        raw = match.group(0)
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        start = match.start() + leading
        end = match.start() + trailing
        sentence = text[start:end]
        if len(_clean(sentence)) >= 20:
            spans.append((start, end, sentence))
    return spans


def _paper_id(paper: dict) -> str:
    existing = _clean(paper.get("paper_id"))
    if existing:
        return existing
    seed = "|".join([_clean(paper.get("doi")).casefold(), _clean(paper.get("title")).casefold(), str(paper.get("year") or "")])
    return "paper_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def _source_text(paper: dict) -> tuple[str, str, str]:
    fulltext = next(
        (_clean(paper.get(key)) for key in ("fulltext", "full_text", "extracted_fulltext") if _clean(paper.get(key))),
        "",
    )
    if fulltext:
        return "fulltext", "fulltext", fulltext
    abstract = _clean(paper.get("abstract"))
    if abstract:
        return "abstract", "abstract", abstract
    return "title_only", "title", _clean(paper.get("title"))


def build_evidence_matrix(papers: list[dict] | tuple[dict, ...]) -> dict:
    """Persist only abstract/fulltext sentences as formal evidence spans."""
    paper_rows = []
    spans = []
    for paper in sorted(papers, key=lambda item: (_paper_id(item), _clean(item.get("title")).casefold())):
        paper_id = _paper_id(paper)
        level, source_field, source_text = _source_text(paper)
        span_ids = []
        if level in FORMAL_EVIDENCE_LEVELS:
            for start, end, sentence in _sentence_offsets(source_text):
                seed = f"{paper_id}|{source_field}|{start}|{end}|{sentence}"
                span_id = "span_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
                span = EvidenceSpan(span_id, paper_id, level, source_field, start, end, sentence)
                spans.append(span.as_dict())
                span_ids.append(span_id)
        paper_rows.append({
            "paper_id": paper_id,
            "title": _clean(paper.get("title")),
            "evidence_level": level,
            "formal_evidence_eligible": level in FORMAL_EVIDENCE_LEVELS and bool(span_ids),
            "span_ids": span_ids,
            "source_text_hash": hashlib.sha256(source_text.encode("utf-8")).hexdigest() if source_text else None,
        })
    matrix_hash = hashlib.sha256(
        "|".join(f"{span['span_id']}:{span['paper_id']}" for span in spans).encode("utf-8")
    ).hexdigest()
    return {
        "version": EVIDENCE_MATRIX_VERSION,
        "paper_count": len(paper_rows),
        "formal_evidence_paper_count": sum(row["formal_evidence_eligible"] for row in paper_rows),
        "span_count": len(spans),
        "matrix_hash": matrix_hash,
        "papers": paper_rows,
        "spans": spans,
    }


def evidence_indexes(matrix: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    papers = {row["paper_id"]: row for row in matrix.get("papers", [])}
    spans = {row["span_id"]: row for row in matrix.get("spans", [])}
    return papers, spans


def validate_formal_span(matrix: dict, span_id: str, paper_id: str | None = None) -> dict:
    """Resolve one formal span and reject L0/title-only or cross-paper bindings."""
    papers, spans = evidence_indexes(matrix)
    span = spans.get(span_id)
    if not span:
        raise ValueError("evidence_span_not_found")
    if span.get("evidence_level") not in FORMAL_EVIDENCE_LEVELS:
        raise ValueError("title_level_evidence_not_formal")
    if paper_id and span.get("paper_id") != paper_id:
        raise ValueError("evidence_span_paper_mismatch")
    paper = papers.get(span["paper_id"])
    if not paper or not paper.get("formal_evidence_eligible"):
        raise ValueError("paper_not_formal_evidence_eligible")
    return span
