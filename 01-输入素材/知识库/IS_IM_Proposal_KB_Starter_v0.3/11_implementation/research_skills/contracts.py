"""Versioned contracts shared by all internal research-skill adapters."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import uuid4


CONTRACT_VERSION = "research-skill-contract-1.0.0"
SECRET_MARKERS = (
    "api_key", "apikey", "authorization", "password", "secret",
    "access_token", "refresh_token", "private_key", "credential",
)
SECRET_VALUE_PATTERN = re.compile(r"(?i)(?:bearer\s+|sk-)[a-z0-9._-]{8,}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_secret_key(key: object) -> bool:
    normalized = str(key).strip().casefold().replace("-", "_")
    return any(marker in normalized for marker in SECRET_MARKERS)


def redact(value: Any) -> Any:
    """Return a JSON-safe, recursively redacted value."""
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_secret_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return SECRET_VALUE_PATTERN.sub("[REDACTED]", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def secret_field_paths(value: Any, prefix: str = "$") -> list[str]:
    """Find secret-bearing field names; payloads must configure secrets out of band."""
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if _is_secret_key(key):
                paths.append(path)
            else:
                paths.extend(secret_field_paths(item, path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            paths.extend(secret_field_paths(item, f"{prefix}[{index}]"))
    return paths


def canonical_json(value: Any) -> str:
    return json.dumps(redact(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SkillRunStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class SkillInputError(ValueError):
    """Raised when a skill payload cannot be safely converted upstream."""


@dataclass(frozen=True)
class ResearchSkillContext:
    stage: str
    project_id: str = "is-im-proposal-platform"
    run_id: str = field(default_factory=lambda: f"run_{uuid4().hex}")
    trace_dir: Path | None = None
    cache_namespace: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)

    def cache_identity(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "stage": self.stage,
            "cache_namespace": self.cache_namespace,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ResearchSkillDescriptor:
    skill_id: str
    version: str
    stage: str
    description: str
    deterministic: bool = False
    input_schema_version: str = "1.0.0"
    output_schema_version: str = "1.0.0"
    external_network: bool = False


@dataclass
class AdapterExecution:
    result_status: SkillRunStatus
    upstream_status: str
    output: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    cacheable: bool = True


@dataclass
class ResearchSkillResult:
    skill_id: str
    skill_version: str
    stage: str
    run_id: str
    status: SkillRunStatus
    upstream_status: str
    cache_key: str
    started_at: str
    finished_at: str
    output: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    contract_version: str = CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return redact(asdict(self))


def build_cache_key(
    descriptor: ResearchSkillDescriptor,
    payload: Mapping[str, Any],
    context: ResearchSkillContext,
) -> str:
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "skill_id": descriptor.skill_id,
        "skill_version": descriptor.version,
        "input_schema_version": descriptor.input_schema_version,
        "payload": payload,
        "context": context.cache_identity(),
    }
    digest = hashlib.sha256(canonical_json(envelope).encode("utf-8")).hexdigest()
    return f"rskill:{descriptor.skill_id}:{digest}"


class ResearchSkillAdapter(Protocol):
    descriptor: ResearchSkillDescriptor

    def execute(self, payload: Mapping[str, Any], context: ResearchSkillContext) -> AdapterExecution: ...
