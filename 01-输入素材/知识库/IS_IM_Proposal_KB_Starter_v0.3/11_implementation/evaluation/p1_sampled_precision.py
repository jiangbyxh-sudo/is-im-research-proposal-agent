#!/usr/bin/env python3
"""Create and score the six-group, 60-paper P1 human sampling package."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


IMPLEMENTATION = Path(__file__).resolve().parents[1]
KB_ROOT = IMPLEMENTATION.parent
WORKSPACE = KB_ROOT.parents[2]
DEFAULT_EVIDENCE = WORKSPACE / "02-任务/01-current/T03-P1检索质量工程/验收证据/P1-检索质量工程"
REPRESENTATIVES = {
    "is": "platform_governance",
    "is_cs_hci": "topic_ai_enabled_information_systems",
    "is_psychology": "topic_ai_trust",
    "is_communication_media": "social_media",
    "im": "information_behavior",
    "im_data_ai_knowledge": "topic_decision_support",
}
ALLOWED_LABELS = {"相关", "邻近", "无关", "不确定"}


def blind_id(direction_id: str, paper_id: str) -> str:
    return "sample_" + hashlib.sha256(f"{direction_id}:{paper_id}".encode("utf-8")).hexdigest()[:12]


def build_package(trace_dir: Path) -> dict:
    rows = []
    for group_id, direction_id in REPRESENTATIVES.items():
        trace = json.loads((trace_dir / f"{direction_id}.json").read_text(encoding="utf-8"))
        response = trace.get("api_response", trace)
        papers = (response.get("papers") or [])[:10]
        for rank, paper in enumerate(papers, 1):
            rows.append({
                "sample_id": blind_id(direction_id, paper["paper_id"]),
                "group_id": group_id,
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
        "instructions": "每篇只填写：相关 / 邻近 / 无关 / 不确定。相关与邻近计入宽口径，只有相关计入严格Precision@10。",
        "representatives": REPRESENTATIVES,
        "expected_rows": 60,
        "actual_rows": len(rows),
        "samples": rows,
        "fixed_regressions": [
            {"title": "Measurements, Algorithms, and Presentations of Reality: Framing Interactions with AI-Enabled Decision Support", "expected": "无关或不确定", "reason": "clinical AI-only must not automatically enter the formal AI-enabled IS set"},
            {"title": "Generative Artificial Intelligence: Evolving Technology, Growing Societal Impact, and Opportunities for Information Systems Research", "expected": "相关", "reason": "direct IS research agenda"},
            {"title": "Post-growth Human–Computer Interaction", "expected": "邻近或无关", "reason": "high-quality HCI is not automatically AI-enabled IS"},
        ],
    }


def score_labels(package: dict) -> dict:
    by_group = defaultdict(list)
    invalid = []
    for row in package["samples"]:
        label = str(row.get("label") or "").strip()
        if label not in ALLOWED_LABELS:
            invalid.append(row["sample_id"])
            continue
        by_group[row["group_id"]].append(label)
    group_metrics = {}
    for group_id, labels in by_group.items():
        decided = [label for label in labels if label != "不确定"]
        strict = sum(label == "相关" for label in decided) / len(decided) if decided else None
        obvious_false = sum(label == "无关" for label in decided) / len(decided) if decided else None
        group_metrics[group_id] = {"n": len(labels), "decided_n": len(decided), "precision_at_10": strict, "obvious_false_positive_rate": obvious_false}
    all_decided = [label for labels in by_group.values() for label in labels if label != "不确定"]
    precision = sum(label == "相关" for label in all_decided) / len(all_decided) if all_decided else None
    false_rate = sum(label == "无关" for label in all_decided) / len(all_decided) if all_decided else None
    gates = {
        "overall_precision_ge_0_80": precision is not None and precision >= 0.80,
        "every_group_ge_0_70": len(group_metrics) == 6 and all(value["precision_at_10"] is not None and value["precision_at_10"] >= 0.70 for value in group_metrics.values()),
        "obvious_false_positive_rate_le_0_10": false_rate is not None and false_rate <= 0.10,
        "all_60_labeled": not invalid and len(package["samples"]) == 60,
    }
    return {"overall_precision_at_10": precision, "obvious_false_positive_rate": false_rate, "groups": group_metrics, "invalid_or_missing_labels": invalid, "gates": gates, "passed": all(gates.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--labels", type=Path)
    args = parser.parse_args()
    if args.labels:
        package = json.loads(args.labels.read_text(encoding="utf-8"))
        result = score_labels(package)
        target = args.evidence_dir / "p1_sampled_precision_result.json"
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["passed"] else 2
    package = build_package(args.evidence_dir / "traces/full_pipeline")
    target = args.evidence_dir / "p1_sampled_precision_package.json"
    target.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {package['actual_rows']}/60 sampled rows to {target}")
    return 0 if package["actual_rows"] == 60 else 2


if __name__ == "__main__":
    raise SystemExit(main())
