"""Deterministic five-perspective discovery queries; never a selection policy."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


SEARCH_PLAN_VERSION = "multi-perspective-search-plan-1.0.0"
PERSPECTIVES = ("phenomenon", "theory", "mechanism", "context", "method")


@dataclass(frozen=True)
class PerspectiveQuery:
    query_id: str
    perspective: str
    language: str
    query: str
    origin: str

    def as_dict(self) -> dict:
        return asdict(self)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in (_clean(item) for item in values) if value))


def _first(values: object, fallback: str = "") -> str:
    if isinstance(values, (list, tuple)):
        return next((_clean(item) for item in values if _clean(item)), fallback)
    return _clean(values) or fallback


def build_multi_perspective_search_plan(profile: dict, fine_grained_question: str | None = None) -> dict:
    direction_id = _clean(profile.get("direction_id"))
    if not direction_id:
        raise ValueError("direction_id_required")
    labels = profile.get("labels") or {}
    queries = profile.get("queries") or {}
    facets = profile.get("facets") or {}
    en_core = _first(facets.get("core_phenomena"), _clean(labels.get("en")))
    zh_core = next((item for item in facets.get("core_phenomena", []) if any("\u4e00" <= char <= "\u9fff" for char in str(item))), _clean(labels.get("zh")))
    context = _first(facets.get("required_context_any"), "information systems")
    technology = _first(facets.get("technology_terms"), "")
    question = _clean(fine_grained_question)

    rows: list[tuple[str, str, str, str]] = []
    phenomenon_en = _unique(([question] if question else []) + list(queries.get("en_precise") or []) + [en_core])[:2]
    phenomenon_zh = _unique(list(queries.get("zh_precise") or []) + ([zh_core] if zh_core else []))[:1]
    rows.extend(("phenomenon", "en", value, "profile_or_user_question") for value in phenomenon_en)
    rows.extend(("phenomenon", "zh", value, "profile") for value in phenomenon_zh)

    if en_core:
        rows.extend((
            ("theory", "en", f"{en_core} theory conceptual framework", "deterministic_template"),
            ("mechanism", "en", f"{en_core} {technology or 'mechanism process mediator'}", "deterministic_template"),
            ("context", "en", f"{en_core} {context}", "deterministic_template"),
            ("method", "en", f"{en_core} empirical study measurement research design", "deterministic_template"),
        ))
    if zh_core:
        rows.extend((
            ("theory", "zh", f"{zh_core} 理论 概念框架", "deterministic_template"),
            ("mechanism", "zh", f"{zh_core} 机制 中介 过程", "deterministic_template"),
            ("context", "zh", f"{zh_core} {context}", "deterministic_template"),
            ("method", "zh", f"{zh_core} 实证研究 测量 研究设计", "deterministic_template"),
        ))

    built: list[PerspectiveQuery] = []
    seen: set[tuple[str, str]] = set()
    counters = {perspective: 0 for perspective in PERSPECTIVES}
    for perspective, language, query, origin in rows:
        normalized = _clean(query)
        key = (language, normalized.casefold())
        if not normalized or key in seen:
            continue
        seen.add(key)
        counters[perspective] += 1
        built.append(PerspectiveQuery(
            query_id=f"{perspective}_{language}_{counters[perspective]:02d}",
            perspective=perspective,
            language=language,
            query=normalized,
            origin=origin,
        ))

    covered = sorted({item.perspective for item in built})
    payload = {
        "version": SEARCH_PLAN_VERSION,
        "profile_version": profile.get("profile_version", "unknown"),
        "direction_id": direction_id,
        "fine_grained_question": question or None,
        "queries": [item.as_dict() for item in built],
        "perspective_coverage": covered,
        "missing_perspectives": [item for item in PERSPECTIVES if item not in covered],
        "discovery_only": True,
        "selection_policy": "all_results_must_reenter_existing_p1_selection_space",
        "llm_generated_queries": False,
    }
    payload["plan_hash"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload
