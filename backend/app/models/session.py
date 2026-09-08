"""Cooking-session state, kept separate from conversation history."""

from dataclasses import dataclass, field
from enum import StrEnum

from app.models.recipe import Recipe


class CookingStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class CookingSession:
    id: str
    recipe: Recipe
    current_step_id: str | None
    completed_step_ids: list[str] = field(default_factory=list)
    skipped_step_ids: list[str] = field(default_factory=list)
    active_timer_ids: list[str] = field(default_factory=list)
    status: CookingStatus = CookingStatus.ACTIVE
