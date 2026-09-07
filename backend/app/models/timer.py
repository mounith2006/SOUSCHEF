"""Timer domain state."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class TimerStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass(slots=True)
class CookingTimer:
    id: str
    session_id: str
    label: str
    duration_seconds: float
    remaining_seconds: float
    status: TimerStatus
    action_id: str
    started_at: datetime
    deadline: float | None
    completed_at: datetime | None = None

    @classmethod
    def running(
        cls,
        *,
        timer_id: str,
        session_id: str,
        label: str,
        duration_seconds: float,
        action_id: str,
        deadline: float,
    ) -> "CookingTimer":
        if duration_seconds <= 0:
            raise ValueError("timer duration must be greater than zero")
        return cls(
            id=timer_id,
            session_id=session_id,
            label=label,
            duration_seconds=duration_seconds,
            remaining_seconds=duration_seconds,
            status=TimerStatus.RUNNING,
            action_id=action_id,
            started_at=datetime.now(UTC),
            deadline=deadline,
        )
