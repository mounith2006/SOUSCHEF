"""Validated API representations for cooking timers."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.timer import TimerStatus


class StartTimerRequest(BaseModel):
    session_id: str
    duration_seconds: float = Field(gt=0)
    label: str
    action_id: str


class TimerActionRequest(BaseModel):
    action_id: str


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
