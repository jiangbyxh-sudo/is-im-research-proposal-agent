"""Replayable P1 retrieval plans and OpenAlex filter compilation.

The plan is provider-neutral at the orchestration boundary.  OpenAlex-specific
filter names are kept here so query construction is testable without making a
network request.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


OPENALEX_TYPE_MAP = {
    "journal-article": "article|review",
    "proceedings-article": "proceedings-article",
}


@dataclass(frozen=True)
class OpenAlexQueryPlan:
    lane_id: str
    search: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    sort: str | None = None
    per_page: int = 100
    max_pages: int = 1
    language_target: str | None = None
    evidence_mode: str = "abstract_preferred"
    stop_target: int = 10

    def as_dict(self) -> dict:
        return asdict(self)


def _short_id(value: str) -> str:
    return str(value or "").rstrip("/").rsplit("/", 1)[-1]


def _join(values: list[str] | tuple[str, ...] | str) -> str:
    if isinstance(values, str):
        values = [values]
    return "|".join(dict.fromkeys(_short_id(value) for value in values if value))


def compile_openalex_filter(filters: dict[str, Any]) -> str:
    """Compile reviewed plan fields into the OpenAlex works filter syntax."""
    parts: list[str] = []
    direct = {
        "from_publication_date": "from_publication_date",
        "to_publication_date": "to_publication_date",
        "language": "language",
        "has_abstract": "has_abstract",
    }
    for key, api_key in direct.items():
        value = filters.get(key)
        if value not in (None, "", [], ()):
            parts.append(f"{api_key}:{str(value).lower() if isinstance(value, bool) else value}")

    document_types = filters.get("document_types") or []
    mapped_types: list[str] = []
    for document_type in document_types:
        mapped_types.extend(OPENALEX_TYPE_MAP.get(document_type, document_type).split("|"))
    if mapped_types:
        parts.append(f"type:{_join(mapped_types)}")

    mappings = (
        ("approved_topic_ids", "topics.id"),
        ("approved_primary_topic_ids", "primary_topic.id"),
        ("approved_field_ids", "topics.field.id"),
        ("approved_subfield_ids", "topics.subfield.id"),
        ("approved_source_ids", "primary_location.source.id"),
    )
    for key, api_key in mappings:
        value = filters.get(key) or []
        if value:
            parts.append(f"{api_key}:{_join(value)}")
    return ",".join(parts)


def build_direction_query_plans(
    profile: dict,
    from_date: str,
    to_date: str,
    fine_grained_question: str | None = None,
    per_page: int = 100,
) -> list[OpenAlexQueryPlan]:
    """Build ordered precision-to-recall lanes from one compiled profile."""
    routes = profile.get("openalex_routes", {})
    queries = profile.get("queries", {})
    source_policy = profile.get("source_policy", {})
    types = profile.get("document_types", ["journal-article"])
    common = {
        "from_publication_date": from_date,
        "to_publication_date": to_date,
        "document_types": types,
    }
    topic_filters = {
        key: routes.get(key, [])
        for key in ("approved_topic_ids", "approved_primary_topic_ids", "approved_field_ids", "approved_subfield_ids")
    }
    tier_a_sources = routes.get("tier_a_source_ids") or source_policy.get("tier_a_source_ids") or []
    tier_b_sources = routes.get("tier_b_source_ids") or source_policy.get("tier_b_source_ids") or []
    en_precise = list(queries.get("en_precise") or [profile["labels"]["en"]])
    en_recall = list(queries.get("en_recall") or en_precise)
    if fine_grained_question:
        en_precise.insert(0, fine_grained_question)

    plans: list[OpenAlexQueryPlan] = []
    approved_topics = any(topic_filters.values())
    if approved_topics and tier_a_sources:
        plans.append(OpenAlexQueryPlan(
            lane_id="A_topic_tier_a",
            filters={**common, **topic_filters, "approved_source_ids": tier_a_sources, "has_abstract": True},
            sort="relevance_score:desc",
            per_page=per_page,
            max_pages=2,
            language_target="en",
            evidence_mode="abstract_required",
        ))
    for index, query in enumerate(en_precise[:2]):
        plans.append(OpenAlexQueryPlan(
            lane_id=f"B_precise_{index + 1}",
            search=query,
            filters={**common, "approved_source_ids": list(dict.fromkeys([*tier_a_sources, *tier_b_sources]))},
            sort="relevance_score:desc",
            per_page=per_page,
            max_pages=2,
            language_target="en",
        ))
    if approved_topics:
        plans.append(OpenAlexQueryPlan(
            lane_id="C_topic_recall",
            search=en_recall[0] if en_recall else None,
            filters={**common, **topic_filters},
            sort="relevance_score:desc",
            per_page=per_page,
            max_pages=2,
            language_target="en",
        ))
    else:
        plans.append(OpenAlexQueryPlan(
            lane_id="C_facet_recall",
            search=en_recall[0],
            filters=common,
            sort="relevance_score:desc",
            per_page=per_page,
            max_pages=2,
            language_target="en",
        ))

    for index, query in enumerate((queries.get("zh_precise") or [])[:1]):
        zh_sources = routes.get("zh_source_ids") or source_policy.get("zh_source_ids") or []
        plans.append(OpenAlexQueryPlan(
            lane_id=f"E_zh_precise_{index + 1}",
            search=query,
            filters={**common, "approved_source_ids": zh_sources},
            sort="relevance_score:desc",
            per_page=per_page,
            max_pages=2,
            language_target="zh",
        ))
    return plans
