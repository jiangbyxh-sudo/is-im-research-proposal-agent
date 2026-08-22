#!/usr/bin/env python3
"""Compile maintainable YAML retrieval rules into 61 DirectionProfiles."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import yaml


KB_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = KB_ROOT / "01_taxonomy"
CATALOG_PATH = TAXONOMY / "generated/research_direction_catalog.json"
BASE_PATH = TAXONOMY / "direction_profile_base.yaml"
OVERRIDE_PATH = TAXONOMY / "direction_profile_overrides.yaml"
TOPIC_REGISTRY_PATH = TAXONOMY / "openalex_topic_registry.json"
SOURCE_REGISTRY_PATH = TAXONOMY / "openalex_source_registry.json"
OUTPUT_PATH = TAXONOMY / "generated/direction_profiles.json"
AUDIT_PATH = TAXONOMY / "generated/direction_profile_audit.json"


def unique(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw or "").strip()
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            result.append(value)
    return result


def merge_dict(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def phrase_queries(zh: str, en: str, aliases: list[str], contexts: list[str]) -> dict:
    en_aliases = [value for value in aliases if value.isascii()]
    zh_aliases = [value for value in aliases if not value.isascii()]
    return {
        "en_precise": unique([en, *en_aliases[:2]]),
        "en_recall": unique([f"{en} {context}" for context in contexts[:2]]),
        "zh_precise": unique([zh, *zh_aliases[:2]]),
        "zh_recall": unique([f"{zh} {context}" for context in ("信息系统", "信息管理")]),
    }


def source_ids_for_pools(source_registry: dict, pool_ids: list[str], language: str | None = None) -> list[str]:
    result = []
    pools = set(pool_ids)
    for source in source_registry.get("sources", []):
        if source.get("review_status") != "approved" or not source.get("openalex_source_id"):
            continue
        if language and source.get("language") != language:
            continue
        if pools.intersection(source.get("pool_ids", [])):
            result.append(source["openalex_source_id"])
    return unique(result)


def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []
    required_paths = (
        ("labels", "zh"), ("labels", "en"),
        ("facets", "core_phenomena"), ("facets", "required_context_any"), ("facets", "negative_contexts"),
        ("queries", "en_precise"), ("queries", "zh_precise"),
        ("source_policy", "tier_a_pool_ids"),
    )
    for parent, child in required_paths:
        if not profile.get(parent, {}).get(child):
            errors.append(f"missing:{parent}.{child}")
    if any("empirical or theoretical research" in value for value in profile.get("facets", {}).get("core_phenomena", [])):
        errors.append("generic_group_context_used_as_core")
    topic_statuses = profile.get("openalex_routes", {}).get("topic_resolution", [])
    if any(item.get("review_status") not in {"approved", "pending_review", "rejected"} for item in topic_statuses):
        errors.append("invalid_topic_review_status")
    return errors


def compile_profiles() -> tuple[dict, dict]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE_PATH.read_text(encoding="utf-8"))
    overrides = yaml.safe_load(OVERRIDE_PATH.read_text(encoding="utf-8")).get("profiles", {})
    topic_registry = json.loads(TOPIC_REGISTRY_PATH.read_text(encoding="utf-8"))
    source_registry = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    version = base["version"]
    defaults = base["defaults"]
    profiles = []
    audit = {"version": version, "generated_on": date.today().isoformat(), "directions": [], "errors": []}
    previous = {}
    if OUTPUT_PATH.is_file():
        previous = {item["direction_id"]: item for item in json.loads(OUTPUT_PATH.read_text(encoding="utf-8")).get("profiles", [])}

    for direction in catalog["directions"]:
        direction_id = direction["direction_id"]
        zh = direction["label"]
        aliases = unique(direction.get("aliases", []))
        en = next((value for value in aliases if value.isascii()), direction_id.removeprefix("topic_").replace("_", " "))
        group_rules = [base["group_defaults"][group_id] for group_id in direction["group_ids"]]
        contexts = unique(value for rules in group_rules for value in rules.get("required_context_any", []))
        tier_a = unique(value for rules in group_rules for value in rules.get("tier_a_pool_ids", []))
        tier_b = unique(value for rules in group_rules for value in rules.get("tier_b_pool_ids", []))
        adjacent = unique(value for rules in group_rules for value in rules.get("adjacent_pool_ids", []))
        zh_pools = unique(value for rules in group_rules for value in rules.get("zh_pool_ids", []))
        all_pools = unique([*tier_a, *tier_b, *adjacent, *zh_pools])
        allow_proceedings = any(rules.get("allow_proceedings") for rules in group_rules)
        topic_evidence = topic_registry.get("directions", {}).get(direction_id, {}).get("candidates", [])
        approved_topics = [item["id"] for item in topic_evidence if item.get("review_status") == "approved"]
        profile = {
            "profile_version": version,
            "direction_id": direction_id,
            "labels": {"zh": zh, "en": en},
            "group_ids": direction["group_ids"],
            "aliases": aliases,
            "facets": {
                "core_phenomena": unique([en, zh, *aliases]),
                "technology_terms": [],
                "required_context_any": contexts,
                "negative_contexts": unique(defaults["generic_negative_contexts"]),
            },
            "boundary_policy": deepcopy(defaults["boundary_policy"]),
            "queries": phrase_queries(zh, en, aliases, contexts),
            "source_policy": {
                "tier_a_pool_ids": tier_a,
                "tier_b_pool_ids": tier_b,
                "adjacent_pool_ids": adjacent,
                "zh_pool_ids": zh_pools,
                "unknown_action": "manual_review",
            },
            "openalex_routes": {
                "approved_topic_ids": approved_topics,
                "approved_primary_topic_ids": [],
                "approved_field_ids": [],
                "approved_subfield_ids": [],
                "tier_a_source_ids": source_ids_for_pools(source_registry, tier_a, "en"),
                "tier_b_source_ids": source_ids_for_pools(source_registry, tier_b, "en"),
                "adjacent_source_ids": source_ids_for_pools(source_registry, adjacent, "en"),
                "zh_source_ids": source_ids_for_pools(source_registry, zh_pools, "zh"),
                "topic_resolution": topic_evidence,
            },
            "source_routes": {
                "required": ["openalex", "crossref"],
                "optional": ["semantic_scholar", *(["dblp"] if allow_proceedings else [])],
                "licensed_optional": ["scopus", "web_of_science", "cnki", "wanfang"],
            },
            "journal_pool_ids": all_pools,
            "document_types": ["journal-article", *(["proceedings-article"] if allow_proceedings else [])],
            "coverage_targets": deepcopy(defaults["coverage_targets"]),
            "source_refs": direction.get("source_refs", []),
        }
        profile = merge_dict(profile, overrides.get(direction_id, {}))
        errors = validate_profile(profile)
        changed = previous.get(direction_id) != profile
        audit["directions"].append({
            "direction_id": direction_id,
            "valid": not errors,
            "errors": errors,
            "changed_from_previous": changed,
            "approved_topic_count": len(approved_topics),
            "approved_source_count": sum(len(profile["openalex_routes"][key]) for key in ("tier_a_source_ids", "tier_b_source_ids", "zh_source_ids")),
        })
        audit["errors"].extend(f"{direction_id}:{error}" for error in errors)
        profiles.append(profile)
    payload = {
        "version": version,
        "generated_on": date.today().isoformat(),
        "generated_from": [str(path.relative_to(KB_ROOT)).replace("\\", "/") for path in (CATALOG_PATH, BASE_PATH, OVERRIDE_PATH, TOPIC_REGISTRY_PATH, SOURCE_REGISTRY_PATH)],
        "direction_count": len(profiles),
        "policy": {
            "local_profile_first": True,
            "generic_group_context_is_not_synonym": True,
            "topic_candidates_require_review": True,
            "fixed_70_threshold_removed": True,
        },
        "profiles": profiles,
    }
    if len(profiles) != 61 or audit["errors"]:
        raise SystemExit(f"profile compilation failed: count={len(profiles)} errors={audit['errors'][:10]}")
    return payload, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload, audit = compile_profiles()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            raise SystemExit("generated direction profiles are stale")
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
        AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"validated {len(payload['profiles'])} direction profiles; errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
