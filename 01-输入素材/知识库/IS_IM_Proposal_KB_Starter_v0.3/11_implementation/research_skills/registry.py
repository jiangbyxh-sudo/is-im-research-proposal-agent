"""In-process registry enforcing research-skill stage, secrecy and trace contracts."""
from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import replace
from threading import Lock
from typing import Any, Mapping

from observability.trace import write_trace

from .contracts import (
    AdapterExecution,
    ResearchSkillAdapter,
    ResearchSkillContext,
    ResearchSkillResult,
    SkillInputError,
    SkillRunStatus,
    build_cache_key,
    redact,
    secret_field_paths,
    utc_now,
)


class ResearchSkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, ResearchSkillAdapter] = {}
        self._cache: dict[str, ResearchSkillResult] = {}
        self._lock = Lock()

    def register(self, adapter: ResearchSkillAdapter, *, replace_existing: bool = False) -> None:
        skill_id = adapter.descriptor.skill_id
        with self._lock:
            if skill_id in self._skills and not replace_existing:
                raise ValueError(f"research_skill_already_registered:{skill_id}")
            self._skills[skill_id] = adapter

    def descriptors(self) -> list[dict[str, Any]]:
        with self._lock:
            adapters = list(self._skills.values())
        return [redact(adapter.descriptor.__dict__) for adapter in sorted(adapters, key=lambda item: item.descriptor.skill_id)]

    @staticmethod
    def _failure(
        adapter: ResearchSkillAdapter,
        context: ResearchSkillContext,
        cache_key: str,
        started_at: str,
        status: SkillRunStatus,
        upstream_status: str,
        message: str,
        error_type: str | None = None,
    ) -> ResearchSkillResult:
        return ResearchSkillResult(
            skill_id=adapter.descriptor.skill_id,
            skill_version=adapter.descriptor.version,
            stage=adapter.descriptor.stage,
            run_id=context.run_id,
            status=status,
            upstream_status=upstream_status,
            cache_key=cache_key,
            started_at=started_at,
            finished_at=utc_now(),
            limitations=[message],
            error={"type": error_type, "message": message} if error_type else None,
            audit={"cache_hit": False},
        )

    def run(
        self,
        skill_id: str,
        payload: Mapping[str, Any],
        context: ResearchSkillContext,
    ) -> ResearchSkillResult:
        with self._lock:
            adapter = self._skills.get(skill_id)
        if adapter is None:
            raise KeyError(f"research_skill_not_registered:{skill_id}")
        if not isinstance(payload, Mapping):
            raise TypeError("research_skill_payload_must_be_mapping")

        started_at = utc_now()
        cache_key = build_cache_key(adapter.descriptor, payload, context)
        secret_paths = secret_field_paths(payload)
        if secret_paths:
            result = self._failure(
                adapter, context, cache_key, started_at, SkillRunStatus.BLOCKED,
                "SECRET_INPUT_REJECTED",
                "API credentials must be configured out of band; secret fields were rejected.",
                "SecretInputRejected",
            )
            result.audit["secret_field_count"] = len(secret_paths)
            self._write_trace(context, result)
            return result

        if context.stage.casefold() != adapter.descriptor.stage.casefold():
            result = self._failure(
                adapter, context, cache_key, started_at, SkillRunStatus.BLOCKED,
                "STAGE_MISMATCH",
                f"Skill {skill_id} belongs to {adapter.descriptor.stage}, not {context.stage}.",
            )
            self._write_trace(context, result)
            return result

        if adapter.descriptor.deterministic:
            with self._lock:
                cached = deepcopy(self._cache.get(cache_key))
            if cached is not None:
                cached = replace(cached, run_id=context.run_id, started_at=started_at, finished_at=utc_now())
                cached.audit = {**cached.audit, "cache_hit": True}
                self._write_trace(context, cached)
                return cached

        try:
            execution = adapter.execute(payload, context)
            if not isinstance(execution, AdapterExecution):
                raise TypeError("adapter_must_return_AdapterExecution")
            result = ResearchSkillResult(
                skill_id=adapter.descriptor.skill_id,
                skill_version=adapter.descriptor.version,
                stage=adapter.descriptor.stage,
                run_id=context.run_id,
                status=execution.result_status,
                upstream_status=execution.upstream_status,
                cache_key=cache_key,
                started_at=started_at,
                finished_at=utc_now(),
                output=redact(execution.output),
                limitations=redact(execution.limitations),
                provenance=redact(execution.provenance),
                audit={**redact(execution.audit), "cache_hit": False},
            )
            if adapter.descriptor.deterministic and execution.cacheable and result.status in {SkillRunStatus.COMPLETE, SkillRunStatus.PARTIAL}:
                with self._lock:
                    self._cache[cache_key] = deepcopy(result)
        except SkillInputError as exc:
            result = self._failure(
                adapter, context, cache_key, started_at, SkillRunStatus.BLOCKED,
                "INVALID_SKILL_INPUT",
                str(exc),
                type(exc).__name__,
            )
        except Exception as exc:  # adapter failures must not escape as false completion
            result = self._failure(
                adapter, context, cache_key, started_at, SkillRunStatus.FAILED,
                "SKILL_EXECUTION_FAILED",
                f"{adapter.descriptor.skill_id} execution failed.",
                type(exc).__name__,
            )
        self._write_trace(context, result)
        return result

    @staticmethod
    def _write_trace(context: ResearchSkillContext, result: ResearchSkillResult) -> None:
        if context.trace_dir is None:
            return
        case_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{context.run_id}_{result.skill_id}")
        write_trace(context.trace_dir, case_id, {"research_skill_result": result.as_dict()})
