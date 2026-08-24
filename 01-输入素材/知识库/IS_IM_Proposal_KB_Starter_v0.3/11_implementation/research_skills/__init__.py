"""Auditable adapters around the existing P1-P4 research workflow."""

from .contracts import (
    AdapterExecution,
    ResearchSkillContext,
    ResearchSkillDescriptor,
    ResearchSkillResult,
    SkillInputError,
    SkillRunStatus,
)
from .registry import ResearchSkillRegistry

__all__ = [
    "AdapterExecution",
    "ResearchSkillContext",
    "ResearchSkillDescriptor",
    "ResearchSkillRegistry",
    "ResearchSkillResult",
    "SkillInputError",
    "SkillRunStatus",
]
