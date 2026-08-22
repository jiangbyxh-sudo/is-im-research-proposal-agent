"""Validated Claim Store: every formal assertion is bound to paper evidence."""
from __future__ import annotations

import hashlib
import json

from evidence_matrix import validate_formal_span


CLAIM_STORE_VERSION = "p3-claim-store-1.0.0"
FORMAL_CLAIM_ROLES = {
    "support", "counterevidence", "boundary", "method_basis",
    "alternative_explanation", "falsification",
}


class ClaimStore:
    def __init__(self, evidence_matrix: dict):
        self.evidence_matrix = evidence_matrix
        self._claims: dict[str, dict] = {}

    def add_formal_claim(self, statement: str, bindings: list[dict], role: str = "support") -> dict:
        statement = str(statement or "").strip()
        if not statement:
            raise ValueError("formal_claim_statement_missing")
        if role not in FORMAL_CLAIM_ROLES:
            raise ValueError("invalid_formal_claim_role")
        if not bindings:
            raise ValueError("formal_claim_requires_evidence_binding")
        resolved = []
        seen = set()
        for binding in bindings:
            paper_id = str(binding.get("paper_id") or "").strip()
            span_id = str(binding.get("evidence_span_id") or binding.get("span_id") or "").strip()
            if not paper_id or not span_id:
                raise ValueError("formal_binding_requires_paper_and_span")
            span = validate_formal_span(self.evidence_matrix, span_id, paper_id)
            key = (paper_id, span_id)
            if key in seen:
                continue
            seen.add(key)
            resolved.append({
                "paper_id": paper_id,
                "evidence_span_id": span_id,
                "evidence_span": {
                    "evidence_level": span["evidence_level"],
                    "source_field": span["source_field"],
                    "start_char": span["start_char"],
                    "end_char": span["end_char"],
                    "text": span["text"],
                },
            })
        seed = json.dumps({"statement": statement, "role": role, "bindings": resolved}, ensure_ascii=False, sort_keys=True)
        claim_id = "claim_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        citations = [
            {"claim_id": claim_id, "paper_id": binding["paper_id"], "evidence_span": binding["evidence_span"]}
            for binding in resolved
        ]
        claim = {
            "claim_id": claim_id,
            "statement": statement,
            "role": role,
            "formal": True,
            "bindings": resolved,
            "citations": citations,
        }
        self._claims[claim_id] = claim
        return claim

    def get(self, claim_id: str) -> dict | None:
        return self._claims.get(claim_id)

    def as_dict(self) -> dict:
        claims = [self._claims[key] for key in sorted(self._claims)]
        return {
            "version": CLAIM_STORE_VERSION,
            "evidence_matrix_hash": self.evidence_matrix.get("matrix_hash"),
            "claim_count": len(claims),
            "claims": claims,
        }

    def audit(self) -> dict:
        errors = []
        for claim in self._claims.values():
            if claim.get("formal") and not claim.get("bindings"):
                errors.append(f"{claim['claim_id']}:missing_bindings")
            for binding in claim.get("bindings", []):
                try:
                    validate_formal_span(self.evidence_matrix, binding["evidence_span_id"], binding["paper_id"])
                except ValueError as exc:
                    errors.append(f"{claim['claim_id']}:{exc}")
        return {"valid": not errors, "errors": errors, "formal_claim_count": len(self._claims)}
