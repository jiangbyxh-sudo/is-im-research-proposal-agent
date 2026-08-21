#!/usr/bin/env python3
"""Build the runtime journal whitelist and resolve English ISSNs with Crossref."""
from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:  # Generated supplement remains usable in zero-dependency runtime environments.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
POOL_PATH = ROOT / "02_journals/journal_pools.yaml"
EN_RANK_PATH = ROOT / "02_journals/IS_IM_Journal_Knowledge_Base.md"
ZH_RANK_PATH = ROOT / "02_journals/FMS_Chinese_2025_T1_T2.md"
OUTPUT_PATH = ROOT / "02_journals/generated/journal_registry.json"
SUPPLEMENT_SOURCE_DIR = ROOT.parents[1] / "supplement_cn_cas"
SUPPLEMENT_OUTPUT_PATH = ROOT / "02_journals/supplements/supplement_cn_cas_merged.json"

TITLE_ALIASES = {
    "现代传播": "现代传播（中国传媒大学学报）",
}


def clean_title(value: str) -> str:
    value = value.replace("**", "").strip()
    return re.sub(r"\s+\((?:[A-Z][A-Z&]*|IP&M)\)$", "", value).strip()


def normalize_title(value: str) -> str:
    value = TITLE_ALIASES.get(value.strip(), value)
    value = unicodedata.normalize("NFKC", clean_title(value)).casefold()
    value = value.replace("&", " and ")
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value)


def parse_pools(supplement: dict | None = None) -> dict[str, list[str]]:
    pools: dict[str, list[str]] = {}
    current: str | None = None
    in_journals = False
    for line in POOL_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("conference_discovery_pools:"):
            break
        match = re.match(r"^- pool_id:\s*(\S+)", line)
        if match:
            current = match.group(1)
            pools[current] = []
            in_journals = False
            continue
        if current and line.strip() == "journals:":
            in_journals = True
            continue
        if current and in_journals:
            match = re.match(r"^\s{2}-\s+(.+?)\s*$", line)
            if match:
                pools[current].append(match.group(1).strip("'\""))
            elif line and not line.startswith("  "):
                in_journals = False
    for pool_id, titles in (supplement or {}).get("pools", {}).items():
        pools.setdefault(pool_id, [])
        for title in titles:
            if title not in pools[pool_id]:
                pools[pool_id].append(title)
    return pools


def parse_english_ranks() -> dict[str, dict]:
    records: dict[str, dict] = {}
    for line in EN_RANK_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"Journal", "期刊"}:
            continue
        title = clean_title(cells[0])
        rank_blob = " ".join(cells[1:3])
        grade_match = re.search(r"(?:FMS\s*)?\b([AB])\b", rank_blob, re.I)
        utd = "UTD24" in rank_blob or "✓" in rank_blob
        if not grade_match and not utd:
            continue
        levels = []
        if grade_match:
            levels.append(f"FMS_INT_{grade_match.group(1).upper()}")
        if utd:
            levels.append("UTD24")
        records[normalize_title(title)] = {
            "canonical_title": title,
            "language": "en",
            "ranking_levels": levels,
            "source_refs": ["02_journals/IS_IM_Journal_Knowledge_Base.md"],
        }
    return records


def parse_chinese_ranks() -> dict[str, dict]:
    records: dict[str, dict] = {}
    pattern = re.compile(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(T[12])\s*\|")
    for line in ZH_RANK_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        title, issn, level = (part.strip() for part in match.groups())
        valid_issn = issn if re.fullmatch(r"\d{4}-[\dXx]{4}", issn) else None
        records[normalize_title(title)] = {
            "canonical_title": title,
            "language": "zh",
            "ranking_levels": [f"FMS_CN_{level}"],
            "issns": [valid_issn] if valid_issn else [],
            "source_refs": ["02_journals/FMS_Chinese_2025_T1_T2.md"],
        }
    return records


def merge_supplement() -> dict:
    """Normalize creator-supplied CAS/CSSCI/PKU lists into one auditable KB artifact."""
    required = {
        "CAS_SSCI_2025_Z1_Z2_IS_IM.yaml",
        "CSSCI_2025_2026_IS_IM.yaml",
        "PKU_CORE_2023_IS_IM.yaml",
        "journal_source_provenance.yaml",
        "journal_routing_extension.yaml",
    }
    missing = sorted(name for name in required if not (SUPPLEMENT_SOURCE_DIR / name).is_file())
    if missing:
        if SUPPLEMENT_OUTPUT_PATH.is_file():
            return json.loads(SUPPLEMENT_OUTPUT_PATH.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Missing supplement files: {', '.join(missing)}")
    if yaml is None:
        if SUPPLEMENT_OUTPUT_PATH.is_file():
            return json.loads(SUPPLEMENT_OUTPUT_PATH.read_text(encoding="utf-8"))
        raise RuntimeError("PyYAML is required for the first supplement merge")

    def read_yaml(name: str) -> dict:
        return yaml.safe_load((SUPPLEMENT_SOURCE_DIR / name).read_text(encoding="utf-8")) or {}

    cas = read_yaml("CAS_SSCI_2025_Z1_Z2_IS_IM.yaml")
    cssci = read_yaml("CSSCI_2025_2026_IS_IM.yaml")
    pku = read_yaml("PKU_CORE_2023_IS_IM.yaml")
    provenance = read_yaml("journal_source_provenance.yaml")
    routing = read_yaml("journal_routing_extension.yaml")
    records: dict[str, dict] = {}
    pools: dict[str, list[str]] = {}

    def add_record(
        title: str,
        language: str,
        ranking_level: str,
        pool_id: str,
        default_eligible: bool,
        source_file: str,
        verification_status: str | None = None,
        runtime_rule: str | None = None,
    ) -> None:
        title = TITLE_ALIASES.get(title, title)
        key = normalize_title(title)
        record = records.setdefault(key, {
            "canonical_title": title,
            "language": language,
            "ranking_levels": [],
            "pool_ids": [],
            "default_eligible": False,
            "source_refs": [],
            "verification_notes": [],
        })
        if ranking_level not in record["ranking_levels"]:
            record["ranking_levels"].append(ranking_level)
        if pool_id not in record["pool_ids"]:
            record["pool_ids"].append(pool_id)
        record["default_eligible"] = record["default_eligible"] or default_eligible
        source_ref = f"01-输入素材/supplement_cn_cas/{source_file}"
        if source_ref not in record["source_refs"]:
            record["source_refs"].append(source_ref)
        note = {"system": ranking_level, "verification_status": verification_status, "runtime_rule": runtime_rule}
        if note not in record["verification_notes"]:
            record["verification_notes"].append(note)
        pools.setdefault(pool_id, [])
        if title not in pools[pool_id]:
            pools[pool_id].append(title)

    for zone_name, zone_number in (("zone_1", 1), ("zone_2", 2)):
        pool_id = f"CAS_SSCI_2025_ZONE{zone_number}"
        for item in cas.get(zone_name, []):
            add_record(
                item["title"], "en", pool_id, pool_id, False,
                "CAS_SSCI_2025_Z1_Z2_IS_IM.yaml",
                item.get("verification_status"), item.get("runtime_rule"),
            )

    for pool in cssci.get("pools", []):
        status = pool.get("status")
        level = "CSSCI_2025_2026_EXTENDED" if status == "extended" else "CSSCI_2025_2026_SOURCE"
        eligible = status in {"source", "source_subset"}
        for title in pool.get("journals", []):
            add_record(
                title, "zh", level, pool["pool_id"], eligible,
                "CSSCI_2025_2026_IS_IM.yaml", status,
                "CSSCI扩展版不得与来源期刊等价" if status == "extended" else None,
            )

    for pool in pku.get("pools", []):
        for title in pool.get("journals", []):
            add_record(
                title, "zh", "PKU_CORE_2023", pool["pool_id"], True,
                "PKU_CORE_2023_IS_IM.yaml", pku.get("status"), pku.get("warning"),
            )

    merged = {
        "version": "0.4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_directory": "01-输入素材/supplement_cn_cas",
        "source_files": sorted(required | {"IS_IM_Journal_Supplement_CAS_CSSCI_PKU.md"}),
        "policy": routing.get("policy", {}),
        "eligibility_profiles": routing.get("eligibility_profiles", []),
        "direction_routes": routing.get("direction_routes", []),
        "provenance": provenance.get("systems", {}),
        "important_exclusions": cas.get("important_exclusions", []),
        "source_warnings": {
            "pku": pku.get("warning"),
            "cssci": cssci.get("policy", {}),
        },
        "pools": pools,
        "journal_count": len(records),
        "records": sorted(records.values(), key=lambda item: item["canonical_title"]),
    }
    SUPPLEMENT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUPPLEMENT_OUTPUT_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return merged


def merge_rank_maps(base: dict[str, dict], extra: dict) -> dict[str, dict]:
    merged = {key: {**value, "default_eligible": True} for key, value in base.items()}
    for record in extra.get("records", []):
        key = normalize_title(record["canonical_title"])
        target = merged.setdefault(key, {
            "canonical_title": record["canonical_title"],
            "language": record["language"],
            "ranking_levels": [],
            "source_refs": [],
            "default_eligible": False,
        })
        target["ranking_levels"] = sorted(set(target.get("ranking_levels", [])) | set(record["ranking_levels"]))
        target["source_refs"] = sorted(set(target.get("source_refs", [])) | set(record["source_refs"]) | {"02_journals/supplements/supplement_cn_cas_merged.json"})
        target["default_eligible"] = target.get("default_eligible", False) or record.get("default_eligible", False)
        target["verification_notes"] = record.get("verification_notes", [])
    return merged


def crossref_json(path: str, params: dict, mailto: str | None, timeout: int = 25) -> dict:
    if mailto:
        params = {**params, "mailto": mailto}
    url = f"https://api.crossref.org{path}?{urlencode(params)}"
    agent = "ProposalCompass-JournalRegistry/0.1"
    if mailto:
        agent += f" (mailto:{mailto})"
    request = Request(url, headers={"User-Agent": agent, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def resolve_crossref(title: str, mailto: str | None) -> dict:
    try:
        payload = crossref_json("/journals", {"query": title, "rows": 10}, mailto)
        wanted = normalize_title(title)
        for item in payload.get("message", {}).get("items", []):
            if normalize_title(item.get("title", "")) == wanted:
                issns = sorted({value.upper() for value in item.get("ISSN", []) if value})
                return {"issns": issns, "crossref_title": item.get("title"), "status": "resolved"}
        return {"issns": [], "status": "title_not_exact"}
    except Exception as exc:
        return {"issns": [], "status": "request_failed", "error": type(exc).__name__}


def verify_crossref_issn(issn: str, mailto: str | None) -> dict:
    try:
        payload = crossref_json(f"/journals/{issn}", {}, mailto)
        message = payload.get("message", {})
        return {
            "status": "resolved",
            "crossref_title": message.get("title"),
            "issns": sorted({value.upper() for value in message.get("ISSN", []) if value} | {issn.upper()}),
        }
    except Exception as exc:
        return {"status": "issn_not_in_crossref", "error": type(exc).__name__, "issns": [issn.upper()]}


def build_registry(mailto: str | None, workers: int) -> dict:
    supplement = merge_supplement()
    pools = parse_pools(supplement)
    english = merge_rank_maps(parse_english_ranks(), {
        "records": [item for item in supplement["records"] if item["language"] == "en"]
    })
    chinese = merge_rank_maps(parse_chinese_ranks(), {
        "records": [item for item in supplement["records"] if item["language"] == "zh"]
    })
    membership: dict[str, set[str]] = {}
    for pool_id, titles in pools.items():
        for title in titles:
            membership.setdefault(normalize_title(title), set()).add(pool_id)

    selected_en = {key: value for key, value in english.items() if key in membership}
    selected_zh = {key: value for key, value in chinese.items() if key in membership}
    resolved: dict[str, dict] = {}
    previous = {}
    if OUTPUT_PATH.is_file():
        try:
            previous_payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            previous = {normalize_title(item["canonical_title"]): item for item in previous_payload.get("journals", [])}
        except (OSError, json.JSONDecodeError):
            previous = {}
    for key, item in previous.items():
        if key in selected_en or key in selected_zh:
            resolved[key] = {
                "status": item.get("metadata_resolution", "missing_local_issn"),
                "issns": item.get("issns", []),
            }
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as executor:
        futures = {
            executor.submit(resolve_crossref, record["canonical_title"], mailto): key
            for key, record in selected_en.items() if key not in resolved
        }
        for future in as_completed(futures):
            resolved[futures[future]] = future.result()
            time.sleep(0.03)
        zh_futures = {
            executor.submit(
                verify_crossref_issn if record.get("issns") else resolve_crossref,
                record["issns"][0] if record.get("issns") else record["canonical_title"],
                mailto,
            ): key
            for key, record in selected_zh.items() if key not in resolved
        }
        for future in as_completed(zh_futures):
            resolved[zh_futures[future]] = future.result()
            time.sleep(0.03)

    journals = []
    for key, record in sorted({**selected_en, **selected_zh}.items(), key=lambda item: item[1]["canonical_title"]):
        resolution = resolved.get(key, {})
        issns = record.get("issns") or resolution.get("issns", [])
        journals.append({
            "journal_id": f"journal_{len(journals) + 1:03d}",
            "canonical_title": record["canonical_title"],
            "language": record["language"],
            "issns": issns,
            "ranking_levels": record["ranking_levels"],
            "pool_ids": sorted(membership[key]),
            "source_refs": record["source_refs"],
            "default_eligible": record.get("default_eligible", False),
            "verification_notes": record.get("verification_notes", []),
            "metadata_resolution": resolution.get("status", "missing_local_issn"),
            "crossref_available": resolution.get("status") == "resolved",
        })

    return {
        "version": "0.4.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eligibility_policy": "English default UTD24/FMS 2025 A/B; Chinese default FMS T1/T2, CSSCI 2025-2026 source, or PKU Core 2023; CAS 2025 Z1/Z2 stored as opt-in English extension",
        "supplement_version": supplement["version"],
        "journal_count": len(journals),
        "issn_ready_count": sum(bool(item["issns"]) for item in journals),
        "journals": journals,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailto", default=None, help="Crossref contact email; not stored in output")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    registry = build_registry(args.mailto, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "journal_count": registry["journal_count"],
        "issn_ready_count": registry["issn_ready_count"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
