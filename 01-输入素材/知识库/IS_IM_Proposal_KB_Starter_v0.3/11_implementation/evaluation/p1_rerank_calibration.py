#!/usr/bin/env python3
"""P1 rerank calibration evaluation and v2 blind package generator.

Runs the calibrated pipeline (reranker 2.1.0 + profiles 1.2.0) offline over the
certification snapshot pools, reports in-sample movement of the 60 human-labeled
papers, and emits a fresh six-group blind package for independent labeling.

All pools come from T03 certification traces; no network access is performed.
The in-sample numbers are optimistic by construction (facets were enriched after
reading these labels); the gate verdict may only come from the new blind labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IMPLEMENTATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION))

from paper_quality import SCORE_CONFIG_VERSION, evaluate_boundary, score_record  # noqa: E402

KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
CERT_DIR = WORKSPACE / "02-任务/99-done/T03-P1检索质量工程/验收证据/P1-检索质量工程/certification/profile-1.1.3-high-confidence"
OUT_DIR = WORKSPACE / "04-分析/01-current/P1精排校准返修"
REPRESENTATIVES = {
    "is": "platform_governance",
    "is_cs_hci": "topic_ai_enabled_information_systems",
    "is_psychology": "topic_ai_trust",
    "is_communication_media": "social_media",
    "im": "information_behavior",
    "im_data_ai_knowledge": "topic_decision_support",
}
FROM_YEAR, TO_YEAR = 2022, 2026


def blind_id(direction_id: str, paper_id: str) -> str:
    return "sample_" + hashlib.sha256(f"{direction_id}:{paper_id}".encode("utf-8")).hexdigest()[:12]


def load_labels() -> dict[str, dict]:
    reviewed = json.loads((CERT_DIR / "p1_sampled_precision_package_reviewed.json").read_text(encoding="utf-8"))
    return {s["title"][:60]: s for s in reviewed["samples"]}


def load_profiles() -> dict[str, dict]:
    payload = json.loads((KB_ROOT / "01_taxonomy/generated/direction_profiles.json").read_text(encoding="utf-8"))
    return {item["direction_id"]: item for item in payload["profiles"]}


def rerank_group(direction_id: str, profile: dict) -> list[dict]:
    trace = json.loads((CERT_DIR / "traces/full_pipeline" / f"{direction_id}.json").read_text(encoding="utf-8"))
    papers = trace["api_response"]["papers"]
    query = profile["labels"]["en"]
    rows = []
    for paper in papers:
        record = dict(paper)
        boundary = evaluate_boundary(record, profile)
        score = None
        if boundary.relevance_tier in {"direct", "adjacent"}:
            score = score_record(record, profile, query, FROM_YEAR, TO_YEAR)
        rows.append({
            "paper": paper,
            "tier": boundary.relevance_tier,
            "focality": boundary.focality_score,
            "total": score["total"] if score else 0.0,
            "evidence": list(boundary.as_dict().get("evidence", [])),
        })
    direct = [row for row in rows if row["tier"] == "direct"]
    direct.sort(key=lambda r: (-r["focality"], -r["total"], -(r["paper"].get("year") or 0), r["paper"]["paper_id"]))
    return direct


def build_report(labels: dict[str, dict], profiles: dict[str, dict]) -> dict:
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "score_config_version": SCORE_CONFIG_VERSION,
              "groups": {}, "in_sample_caveat": "facets were enriched after reading these labels; optimistic"}
    totals = defaultdict(int)
    for group, direction_id in REPRESENTATIVES.items():
        direct = rerank_group(direction_id, profiles[direction_id])
        top10 = direct[:10]
        labeled_in_direct = {lbl: sum(1 for r in direct if labels.get(r["paper"]["title"][:60], {}).get("label") == lbl) for lbl in ("相关", "邻近", "无关")}
        old_top10 = {s["title"][:60] for s in labels.values() if s["group_id"] == group}
        new_top10_titles = {r["paper"]["title"][:60] for r in top10}
        overlap = len(old_top10 & new_top10_titles)
        review_demoted = sum(1 for r in direct if "review_title_demoted" in r["evidence"])
        group_row = {
            "pool_size": len(direct) and len(direct),
            "direct_count": len(direct),
            "top10_size": len(top10),
            "labeled_relevant_in_direct": labeled_in_direct["相关"],
            "labeled_adjacent_or_off_in_direct": labeled_in_direct["邻近"] + labeled_in_direct["无关"],
            "unlabeled_in_top10": sum(1 for r in top10 if r["paper"]["title"][:60] not in labels),
            "overlap_with_old_top10": overlap,
        }
        report["groups"][group] = group_row
        totals["relevant_direct"] += labeled_in_direct["相关"]
        totals["failures_direct"] += labeled_in_direct["邻近"] + labeled_in_direct["无关"]
    report["totals"] = dict(totals)
    report["labeled_direct_precision"] = round(
        totals["relevant_direct"] / max(1, totals["relevant_direct"] + totals["failures_direct"]), 4)
    return report


def build_package(labels: dict[str, dict], profiles: dict[str, dict]) -> dict:
    rows = []
    overlap_notes = {}
    for group, direction_id in REPRESENTATIVES.items():
        top10 = rerank_group(direction_id, profiles[direction_id])[:10]
        old_titles = {s["title"][:60] for s in labels.values() if s["group_id"] == group}
        overlap_notes[group] = sum(1 for r in top10 if r["paper"]["title"][:60] in old_titles)
        for rank, row in enumerate(top10, 1):
            paper = row["paper"]
            rows.append({
                "sample_id": blind_id(direction_id, paper["paper_id"]),
                "group_id": group,
                "direction_id": direction_id,
                "rank": rank,
                "title": paper.get("title"),
                "abstract": paper.get("abstract"),
                "source_title": paper.get("source_title"),
                "year": paper.get("year"),
                "label": "",
                "note": "",
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instructions": "每篇只填写：相关 / 邻近 / 无关 / 不确定。相关与邻近计入宽口径，只有相关计入严格Precision@10。请独立判断，不要参考上一次标注。",
        "representatives": REPRESENTATIVES,
        "expected_rows": len(rows),
        "actual_rows": len(rows),
        "pool_depth_note": "离线包仅含认证快照已选池；direct不足10篇的组按实际数量提供并在此披露。",
        "overlap_with_v1_top10": overlap_notes,
        "samples": rows,
        "scoring": "评分复用 evaluation/p1_sampled_precision.py 的门槛：总体≥0.80、任一分组≥0.70、明显假阳性≤0.10。",
    }


def package_markdown(package: dict) -> str:
    lines = ["# P1 精排校准 · 第二轮盲审标注表", "",
             f"生成时间：{package['generated_at']}", "",
             f"共 {package['actual_rows']} 篇。{package['instructions']}", "",
             f"与上一轮Top10重叠（按组）：{json.dumps(package['overlap_with_v1_top10'], ensure_ascii=False)}", ""]
    current_group = None
    for row in package["samples"]:
        if row["group_id"] != current_group:
            current_group = row["group_id"]
            lines += [f"## {current_group} · {row['direction_id']}", ""]
        lines.append(f"### {row['rank']}. {row['title']}")
        lines.append(f"- 期刊：{row.get('source_title') or '—'} | 年份：{row.get('year') or '—'}")
        abstract = (row.get("abstract") or "（无摘要）").replace("\n", " ")
        lines.append(f"- 摘要：{abstract[:600]}{'…' if len(abstract) > 600 else ''}")
        lines.append(f"- **标注（相关/邻近/无关/不确定）**：＿＿＿＿")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    labels = load_labels()
    profiles = load_profiles()
    report = build_report(labels, profiles)
    package = build_package(labels, profiles)
    (args.out_dir / "calibration_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "p1_sampled_precision_package_v2.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "盲审标注表v2.md").write_text(package_markdown(package), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\npackage rows: {package['actual_rows']} | overlap: {json.dumps(package['overlap_with_v1_top10'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
