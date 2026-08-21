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
        if "开题报告与写作指导生成器" in system_prompt:
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
