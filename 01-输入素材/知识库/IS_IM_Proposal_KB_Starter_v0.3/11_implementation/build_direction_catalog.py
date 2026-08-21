#!/usr/bin/env python3
"""Compile the complete user-selectable research-direction catalog.

The journal Markdown remains the human-maintained source. This compiler extracts
only semantic topic lists (典型主题/适用研究/适用主题/研究模块), merges configured
aliases, preserves every source group, and deliberately ignores section 7's quick
routes as a complete catalog.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import yaml


GROUPS = {
    "1": ("is", "IS"),
    "2": ("is_cs_hci", "IS × Computer Science / HCI"),
    "3": ("is_psychology", "IS × Psychology"),
    "4": ("is_communication_media", "IS × Journalism / Communication / Media"),
    "5": ("im", "IM"),
    "6": ("im_data_ai_knowledge", "IM × 数据 / AI / 知识管理"),
}


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def fallback_id(value: str) -> str:
    slug = re.sub(r"[^\w]+", "_", norm(value), flags=re.UNICODE).strip("_")
    return f"topic_{slug}"


def extract(markdown: str) -> list[dict]:
    rows: list[dict] = []
    current_group: tuple[str, str] | None = None
    capture_bullets = False
    captured_any_bullet = False
    in_module_table = False
    for line_no, line in enumerate(markdown.splitlines(), 1):
        top = re.match(r"^#\s+(\d+)\.", line)
        if top:
            current_group = GROUPS.get(top.group(1))
            capture_bullets = False
            captured_any_bullet = False
            in_module_table = False
            continue
        if not current_group:
            continue
        if re.match(r"^##\s+7\.", line):
            current_group = None
            continue
        if line.strip() == "典型主题：" or re.match(r"^##\s+\d+\.\d+\s+适用主题", line):
            capture_bullets = True
            captured_any_bullet = False
            in_module_table = False
            continue
        inline = re.match(r"^适用研究：(.+?)[。.]?$", line.strip())
        if inline:
            for value in re.split(r"[、,，]", inline.group(1)):
                if value.strip():
                    rows.append({"label": value.strip(), "group_id": current_group[0], "group_label": current_group[1], "source_line": line_no})
            continue
        if "按研究模块快速路由" in line:
            in_module_table = True
            capture_bullets = False
            continue
        if capture_bullets:
            bullet = re.match(r"^-\s+(.+)$", line.strip())
            if bullet:
                captured_any_bullet = True
                rows.append({"label": bullet.group(1).strip(), "group_id": current_group[0], "group_label": current_group[1], "source_line": line_no})
                continue
            if captured_any_bullet and line.strip() and not line.startswith("##"):
                capture_bullets = False
        if in_module_table:
            cell = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|", line)
            if cell:
                rows.append({"label": cell.group(1).strip(), "group_id": current_group[0], "group_label": current_group[1], "source_line": line_no})
            elif line.startswith("---") or (line.startswith("#") and "按研究模块" not in line):
                in_module_table = False
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    router_path = root / "01_taxonomy/research_direction_router.yaml"
    router = yaml.safe_load(router_path.read_text(encoding="utf-8"))
    policy = router["catalog_policy"]
    source_path = root / policy["source"]
    rows = extract(source_path.read_text(encoding="utf-8"))

    alias_lookup: dict[str, dict] = {}
    for group in router.get("catalog_alias_groups", []):
        for alias in group["aliases"]:
            alias_lookup[norm(alias)] = group

    directions: dict[str, dict] = {}
    groups: dict[str, dict] = {}
    for row in rows:
        alias_group = alias_lookup.get(norm(row["label"]))
        direction_id = alias_group["direction_id"] if alias_group else fallback_id(row["label"])
        item = directions.setdefault(direction_id, {
            "direction_id": direction_id,
            "label": alias_group["label_zh"] if alias_group else row["label"],
            "aliases": [],
            "group_ids": [],
            "source_refs": [],
        })
        if row["label"] not in item["aliases"]:
            item["aliases"].append(row["label"])
        if row["group_id"] not in item["group_ids"]:
            item["group_ids"].append(row["group_id"])
        item["source_refs"].append(f"{policy['source']}:{row['source_line']}")
        group = groups.setdefault(row["group_id"], {"group_id": row["group_id"], "label": row["group_label"], "direction_ids": []})
        if direction_id not in group["direction_ids"]:
            group["direction_ids"].append(direction_id)

    payload = {
        "version": "0.4.1",
        "generated_on": dt.date.today().isoformat(),
        "generated_from": policy["source"],
        "policy": {
            "group_by_source_section": True,
            "merge_aliases": True,
            "quick_topic_mapping_is_complete_catalog": False,
        },
        "raw_topic_count": len(rows),
        "direction_count": len(directions),
        "groups": list(groups.values()),
        "directions": list(directions.values()),
    }
    output = root / policy["generated_catalog"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "raw_topics": len(rows), "directions": len(directions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
