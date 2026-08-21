"""Safe JSON trace persistence for P0 evaluation runs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


TRACE_SCHEMA_VERSION = "1.0.0"
SECRET_KEYS = {"api_key", "authorization", "password", "secret", "access_token", "refresh_token"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).casefold() in SECRET_KEYS else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    return value


def write_trace(directory: Path, case_id: str, payload: dict) -> tuple[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    trace_id = f"trace_{uuid4().hex}"
    envelope = {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "trace_id": trace_id,
        "case_id": case_id,
        "recorded_at": utc_now(),
        **sanitize(payload),
    }
    target = directory / f"{case_id}.json"
    temporary = directory / f".{case_id}.{uuid4().hex}.tmp"
    temporary.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    return trace_id, target
