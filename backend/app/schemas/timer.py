"""Serializable timer state."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.timer import TimerStatus


class TimerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    label: str
    duration_seconds: float
    remaining_seconds: float
    status: TimerStatus
    action_id: str
    started_at: datetime
    completed_at: datetime | None
