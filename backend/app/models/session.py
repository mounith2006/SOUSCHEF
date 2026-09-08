"""Mutable state for one active cooking session."""

from dataclasses import dataclass, field
from enum import StrEnum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class CookingSession:
    id: str
    recipe_id: str
    current_step_id: str | None
    completed_step_ids: list[str] = field(default_factory=list)
    skipped_step_ids: list[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    recipe_version: int = 1
