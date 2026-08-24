#!/usr/bin/env python3
"""Local-only DeepSeek-compatible fixture for browser acceptance tests."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        envelope = json.loads(self.rfile.read(length).decode("utf-8"))
        messages = envelope.get("messages", [])
        system_prompt = str(messages[0].get("content", "")) if messages else ""
        if "研究簇命名选手A" in system_prompt:
            content = self.athlete_a_content(messages)
        elif "研究簇命名选手B" in system_prompt:
            content = self.athlete_b_content(messages)
        elif "研究簇命名裁判" in system_prompt:
            content = self.judge_content(messages)
        elif "研究空白候选选手A" in system_prompt:
            content = self.gap_candidate_content(messages)
        elif "研究空白候选选手B" in system_prompt:
            content = self.gap_candidate_content(messages)
        elif "研究空白候选裁判" in system_prompt:
            content = self.gap_judge_content(messages)
        elif "开题报告评审员A" in system_prompt or "开题报告评审员B" in system_prompt:
            content = self.arena_reviewer_content(messages)
        elif "开题报告评审裁判" in system_prompt:
            content = self.arena_judge_content(messages)
        elif "受控开题报告逐节生成器" in system_prompt:
            content = self.controlled_section_content(messages)
        elif "开题报告与写作指导生成器" in system_prompt:
            content = self.proposal_content()
        else:
            content = self.synthesis_content()
        body = json.dumps({
            "model": "controlled-browser-fixture",
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _cluster_ids(messages):
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        return [str(item.get("cluster_id")) for item in payload.get("clusters", [])]

    @classmethod
    def athlete_a_content(cls, messages):
        # 受控命名选手A：简洁学术化风格，全部标注受控测试，不构成研究结论。
        names = [{
            "cluster_id": cluster_id,
            "name_zh": f"受控测试簇名A{index + 1}（界面验收）",
            "name_en": f"Controlled fixture name A{index + 1}",
            "description": "受控选手A命名：仅用于界面验收，不代表真实研究方向命名。",
        } for index, cluster_id in enumerate(cls._cluster_ids(messages))]
        return json.dumps({"names": names}, ensure_ascii=False)

    @classmethod
    def athlete_b_content(cls, messages):
        # 受控命名选手B：具体组合风格，全部标注受控测试，不构成研究结论。
        names = [{
            "cluster_id": cluster_id,
            "name_zh": f"受控测试簇名B{index + 1}：机制×情境组合（界面验收）",
            "name_en": f"Controlled fixture name B{index + 1}: mechanism x context",
            "description": "受控选手B命名：仅用于界面验收，不代表真实研究方向命名。",
        } for index, cluster_id in enumerate(cls._cluster_ids(messages))]
        return json.dumps({"names": names}, ensure_ascii=False)

    @classmethod
    def judge_content(cls, messages):
        # 受控裁判：交替选择两个匿名候选，验证两种胜出路径都能渲染。
        selections = [{
            "cluster_id": cluster_id,
            "winner": "candidate_1" if index % 2 == 0 else "candidate_2",
            "reason": "受控裁判理由：仅用于界面验收。",
        } for index, cluster_id in enumerate(cls._cluster_ids(messages))]
        return json.dumps({"selections": selections}, ensure_ascii=False)

    @staticmethod
    def controlled_section_content(messages):
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        spec = payload.get("section_spec") or {}
        blueprint = payload.get("research_design_blueprint") or {}
        outline = payload.get("proposal_outline") or {}
        allowed = list(payload.get("allowed_claim_ids") or [])
        target = int(spec.get("target_words") or 0)
        base = f"{spec.get('title')}的受控测试内容，仅用于界面验收，不构成研究结论。"
        content = base if target < 100 else "".join(f"{base}（第{index}段）" for index in range(max(1, int(target * 0.62) // len(base) + 1)))
        return json.dumps({"section": {
            "section_id": spec.get("section_id"),
            "content": content,
            "claim_ids": allowed[:2],
            "assumptions": ["受控夹具内容，须人工复核"],
            "blueprint_refs": {
                "blueprint_id": blueprint.get("blueprint_id"),
                "research_question": blueprint.get("research_question"),
                "design": blueprint.get("design"),
                "outline_id": outline.get("outline_id"),
                "constraint_hash": blueprint.get("constraint_hash"),
            },
        }}, ensure_ascii=False)

    @staticmethod
    def gap_candidate_content(messages):
        # 受控空白候选选手：回显输入中的真实span_id，模型侧不得编造锚点。
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        spans = payload.get("evidence_spans") or []
        papers = sorted({span.get("paper_id") for span in spans})
        if len(papers) < 2:
            return json.dumps({"candidates": []}, ensure_ascii=False)
        support = [spans[0]["span_id"], next(s["span_id"] for s in spans if s["paper_id"] != papers[0])]
        counter = [next(s["span_id"] for s in spans if s["paper_id"] == papers[-1])]
        return json.dumps({"candidates": [{
            "gap_statement": f"受控空白：{payload.get('cluster', {}).get('name', '')}中的未解释差异（仅供界面验收）",
            "why_it_matters": "受控夹具说明，不构成研究结论。",
            "evidence_span_ids": support,
            "alternative_explanations": ["受控替代解释"],
            "research_question": "受控研究问题：夹具关系如何成立？",
            "feasible_method": {
                "design": "受控实验设计", "data": "夹具样本", "analysis": "方差分析",
                "unit_of_analysis": "夹具用户", "context": "受控情境",
            },
            "counterevidence": [{"statement": "受控反证：夹具存在不一致结果", "evidence_span_ids": counter}],
            "innovation_candidates": ["受控创新点A", "受控创新点B"],
        }]}, ensure_ascii=False)

    @staticmethod
    def gap_judge_content(messages):
        # 受控空白裁判：盲选第一个匿名候选，仅用于界面验收。
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        candidates = payload.get("candidates") or []
        return json.dumps({"selections": [
            {"selection_id": item["selection_id"], "reason": "受控裁判理由，仅供界面验收"}
            for item in candidates[:1]
        ]}, ensure_ascii=False)

    @staticmethod
    def arena_reviewer_content(messages):
        # 受控评审员：对给出章节打分，不改写内容。
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        scope = [row["section_id"] for row in payload.get("sections", [])]
        return json.dumps({
            "reviews": [{"section_id": sid, "score": 8, "issues": []} for sid in scope],
            "overall": {"score": 8, "summary": "受控评审，仅供界面验收。"},
        }, ensure_ascii=False)

    @staticmethod
    def arena_judge_content(messages):
        # 受控评审裁判：全部pass，仅用于界面验收。
        payload = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
        scope = [row["section_id"] for row in payload.get("sections", [])]
        return json.dumps({
            "verdicts": [{"section_id": sid, "verdict": "pass", "final_score": 8, "reason": "受控裁决"} for sid in scope],
            "overall": {"verdict": "pass", "score": 8, "reason": "受控裁决，仅供界面验收。"},
        }, ensure_ascii=False)

    @staticmethod
    def synthesis_content():
        subdirections = []
        for index in range(5):
            first = (index * 2) + 1
            paper_ids = [f"P{first:03d}", f"P{first + 1:03d}"]
            subdirections.append({
                "name_zh": f"受控测试方向{index + 1}",
                "name_en": f"Controlled test direction {index + 1}",
                "description": "仅用于前端成功态验收，不是研究结论。",
                "paper_ids": paper_ids,
                "gaps": [{
                    "gap_type": "empirical",
                    "gap_statement": f"受控测试空白候选{index + 1}",
                    "why_it_matters": "验证证据锚点和选择交互。",
                    "evidence_basis": paper_ids,
                    "alternative_explanations": ["这是测试夹具"],
                    "innovation_candidates": ["通过受控实验验证界面交互", "使用多源数据做稳健性检验"],
                    "confidence": "emerging",
                }],
            })
        return json.dumps({
            "subdirections": subdirections,
            "unclassified_paper_ids": [],
            "contradictions": [],
            "limitations": ["受控测试数据，不得作为研究结果。"],
        }, ensure_ascii=False)

    @staticmethod
    def proposal_content():
        section_ids = [
            "working_title", "background", "concepts", "literature_status",
            "selected_gap", "research_questions", "theoretical_framework",
            "research_design", "contributions", "feasibility_ethics", "timeline",
        ]
        stage_ids = ["topic", "introduction", "theory", "method", "results", "discussion", "submission"]
        return json.dumps({
            "working_title": "受控测试：AI界面干预与用户决策",
            "research_question": "AI界面干预如何影响用户决策质量？",
            "proposal_sections": [{
                "section_id": section_id,
                "content": f"{section_id}的受控测试内容，仅用于界面验收。",
                "paper_ids": ["P001", "P002"],
                "assumptions": ["需要全文复核"],
            } for section_id in section_ids],
            "writing_guidance": [{
                "stage_id": stage_id,
                "purpose": f"{stage_id}阶段的写作目的",
                "recommended_moves": ["先呈现证据，再提出判断"],
                "evidence_required": ["可核验论文与方法依据"],
                "common_failures": ["把待验证判断写成事实"],
                "self_check": ["本段是否保留证据边界？"],
            } for stage_id in stage_ids],
            "limitations": ["受控测试内容，不得作为真实开题结论。"],
        }, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
