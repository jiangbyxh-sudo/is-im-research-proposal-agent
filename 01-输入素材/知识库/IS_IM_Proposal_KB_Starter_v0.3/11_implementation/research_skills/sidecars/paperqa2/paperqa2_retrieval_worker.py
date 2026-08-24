"""Isolated PaperQA2 sparse retriever; JSON stdin/stdout, no LLM or paper search."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
import sys
from collections import defaultdict

from paperqa import Docs, Settings
from paperqa.types import Doc, Text


MAX_INPUT_BYTES = 12_000_000
MAX_SPANS = 5_000


async def retrieve(payload: dict) -> dict:
    query = str(payload.get("query") or "").strip()
    spans = payload.get("spans")
    top_k = int(payload.get("top_k") or 0)
    if not query or not isinstance(spans, list) or not spans or len(spans) > MAX_SPANS:
        raise ValueError("invalid_worker_input")
    if not 1 <= top_k <= min(50, len(spans)):
        raise ValueError("invalid_worker_top_k")

    settings = Settings(embedding="sparse")
    embedding_model = settings.get_embedding_model()
    docs = Docs(name="controlled-evidence-spans")
    grouped = defaultdict(list)
    for item in spans:
        if not isinstance(item, dict):
            raise ValueError("invalid_worker_span")
        span_id = str(item.get("span_id") or "").strip()
        paper_id = str(item.get("paper_id") or "").strip()
        text = str(item.get("text") or "").strip()
        if not span_id or not paper_id or not text:
            raise ValueError("invalid_worker_span")
        grouped[paper_id].append((span_id, text))

    for paper_id in sorted(grouped):
        rows = sorted(grouped[paper_id])
        content_hash = hashlib.sha256("\n".join(text for _, text in rows).encode("utf-8")).hexdigest()
        doc = Doc(docname=paper_id, dockey=paper_id, citation=paper_id, content_hash=content_hash)
        texts = [Text(text=text, name=span_id, doc=doc) for span_id, text in rows]
        await docs.aadd_texts(texts, doc, settings=settings, embedding_model=embedding_model)

    matches = await docs.retrieve_texts(
        query,
        k=top_k,
        settings=settings,
        embedding_model=embedding_model,
    )
    return {
        "status": "OK",
        "backend_version": importlib.metadata.version("paper-qa"),
        "results": [item.name for item in matches],
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        return 2
    try:
        payload = json.loads(raw.decode("utf-8"))
        result = asyncio.run(retrieve(payload))
    except (ValueError, TypeError, json.JSONDecodeError):
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
