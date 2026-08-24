#!/usr/bin/env python3
"""T06 真实重跑 v4 驱动脚本。

复刻 v2 真实链路（同一方向、同一数量、同一约束、同一gap选择策略），
在 v3+v4 修复代码（arena截断5节/timeline防回溯/否定句感知/字数下限反馈重试）上重跑全链并落盘证据。

阶段：research -> synthesize -> proposal(约束确认) -> proposal(蓝图提纲) -> proposal(正式生成)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8766"
OUT_DIR = Path(__file__).resolve().parent

USER_CONSTRAINTS = {
    "degree_level": "硕士",
    "institution_template": "无指定模板",
    "output_language": "中文",
    "target_word_count": 12000,
    "deadline": "2026-12-31",
    "data_access": "公开平台数据与二手数据",
    "method_constraints": "无",
    "research_context": "数字平台生态情境",
    "ethics_privacy": "不涉及人类被试敏感数据",
    "tool_capabilities": "Python与统计工具",
}


def post(path: str, payload: dict, timeout: int = 1200) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"})
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - started
    return data, elapsed


def save(name: str, data: dict) -> Path:
    path = OUT_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def main() -> int:
    print("[1/5] research: platform_governance 10zh/45en (run_synthesis=false)")
    research, sec = post("/api/research", {
        "selected_direction_id": "platform_governance",
        "fine_grained_question": None,
        "chinese_count": 10,
        "english_count": 45,
        "run_synthesis": False,
    })
    save("t06_real_research_v4.json", research)
    job_id = research.get("synthesis_job_id")
    print(f"  status={research.get('status_code')} papers={len(research.get('papers') or [])} job_id={job_id} ({sec:.0f}s)")
    if not job_id:
        print("FAILED: no synthesis job id")
        return 1

    print("[2/5] synthesize (real DeepSeek athlete/judge naming)")
    synthesis, sec = post("/api/synthesize", {"job_id": job_id})
    save("t06_real_synthesis_v4.json", synthesis)
    ctx_id = synthesis.get("proposal_context_id")
    gaps = synthesis.get("gap_candidates") or []
    formal = [g for g in gaps if g.get("formal") is True]
    print(f"  status={synthesis.get('synthesis_status')} ctx={ctx_id} gaps={len(gaps)} formal={len(formal)} ({sec:.0f}s)")
    if not ctx_id or not formal:
        print("FAILED: no context or formal gaps")
        return 1

    gap = formal[0]
    gap_id = gap["gap_id"]
    innovation_id = f"{gap_id}_innovation_1"
    print(f"[3/5] proposal stage1: gap={gap_id}")
    print(f"  gap_statement: {str(gap.get('gap_statement'))[:80]}...")
    print(f"  innovation: {gap.get('innovation_candidates', [''])[0]}")

    base_payload = {
        "proposal_context_id": ctx_id,
        "selected_gap_id": gap_id,
        "selected_innovation_id": innovation_id,
        "user_constraints": USER_CONSTRAINTS,
    }
    stage1, sec = post("/api/proposal", base_payload)
    print(f"  status={stage1.get('proposal_status')} checkpoint={stage1.get('proposal_context', {}).get('checkpoint')} ({sec:.0f}s)")
    if stage1.get("proposal_status") != "USER_CONSTRAINT_CONFIRMATION_REQUIRED":
        save("t06_real_proposal_v4_stage1_unexpected.json", stage1)
        print(f"UNEXPECTED stage1 status: {stage1.get('proposal_status')} - {stage1.get('proposal_message')}")
        return 1

    print("[4/5] proposal stage2: constraints_confirmed -> blueprint+outline")
    stage2, sec = post("/api/proposal", {**base_payload, "constraints_confirmed": True})
    print(f"  status={stage2.get('proposal_status')} ({sec:.0f}s)")
    if stage2.get("proposal_status") != "PROPOSAL_PLAN_CONFIRMATION_REQUIRED":
        save("t06_real_proposal_v4_stage2_unexpected.json", stage2)
        print(f"UNEXPECTED stage2 status: {stage2.get('proposal_status')} - {stage2.get('proposal_message')}")
        return 1
    proposal_plan = stage2.get("proposal") or {}
    blueprint = proposal_plan.get("research_design_blueprint")
    outline = proposal_plan.get("proposal_outline")
    save("t06_real_proposal_v4_stage2_plan.json", stage2)
    print(f"  blueprint_id={blueprint.get('blueprint_id')} paradigm={blueprint.get('paradigm_id')}")
    print(f"  outline sections={len(outline.get('sections') or [])}")

    print("[5/5] proposal stage3: blueprint+outline confirmed -> full generation")
    stage3, sec = post("/api/proposal", {
        **base_payload,
        "constraints_confirmed": True,
        "blueprint_confirmed": True,
        "outline_confirmed": True,
        "research_design_blueprint": blueprint,
        "proposal_outline": outline,
    })
    save("t06_real_proposal_v4.json", stage3)
    status = stage3.get("proposal_status")
    audit = stage3.get("proposal_audit") or {}
    arena = audit.get("arena_review") or {}
    ca = audit.get("constraint_alignment_audit") or {}
    print(f"  status={status} ({sec:.0f}s)")
    print(f"  message: {stage3.get('proposal_message')}")
    print(f"  constraint_alignment: valid={ca.get('valid')} errors={ca.get('errors')}")
    print(f"  arena: verdict={arena.get('overall_verdict')} version={arena.get('version')} scope={arena.get('scope')}")
    if arena.get("error"):
        print(f"  arena ERROR: {arena.get('error')}")
    sections = (stage3.get("proposal") or {}).get("sections") or []
    print(f"  sections={len(sections)}")
    for s in sections:
        c = s.get("content") or ""
        joined = c if isinstance(c, str) else "".join(c)
        print(f"    {s.get('section_id')}: {len(joined)} chars, citations={len(s.get('citations') or [])}")
    print("DONE" if status == "READY_FOR_HUMAN_REVIEW" else f"FINAL STATUS: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

