"""Conversation-facing asynchronous timer operations."""

from typing import Any

from app.schemas.timer import TimerSchema
from app.services.timer_service import TimerService


async def start_timer(
    service: TimerService,
    *,
    session_id: str,
    duration_seconds: float,
    label: str,
    action_id: str,
) -> dict[str, Any]:
    timer = await service.start_timer(
        session_id=session_id,
        duration_seconds=duration_seconds,
        label=label,
        action_id=action_id,
    )
    return _timer_result("start_timer", timer)


async def pause_timer(service: TimerService, *, timer_id: str, action_id: str) -> dict[str, Any]:
    return _timer_result("pause_timer", await service.pause_timer(timer_id, action_id=action_id))


async def resume_timer(service: TimerService, *, timer_id: str, action_id: str) -> dict[str, Any]:
    return _timer_result("resume_timer", await service.resume_timer(timer_id, action_id=action_id))


async def cancel_timer(service: TimerService, *, timer_id: str, action_id: str) -> dict[str, Any]:
    return _timer_result("cancel_timer", await service.cancel_timer(timer_id, action_id=action_id))


def get_timer_status(service: TimerService, *, timer_id: str, action_id: str) -> dict[str, Any]:
    return _timer_result("get_timer_status", service.get_timer(timer_id), action_id)


def list_timers(service: TimerService, *, session_id: str, action_id: str) -> dict[str, Any]:
    timers = [TimerSchema.model_validate(timer).model_dump(mode="json") for timer in service.list_timers(session_id)]
    return {
        "ok": True,
        "action_id": action_id,
        "session_id": session_id,
        "operation": "list_timers",
        "data": {"timers": timers},
        "error": None,
    }


def _timer_result(operation: str, timer: Any, action_id: str | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "action_id": action_id or timer.action_id,
        "session_id": timer.session_id,
        "operation": operation,
        "data": {"timer": TimerSchema.model_validate(timer).model_dump(mode="json")},
        "error": None,
    }
