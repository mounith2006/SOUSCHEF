"""Conversation-facing cooking-session operations."""

from typing import Any

from app.schemas.recipe import RecipeStepSchema
from app.schemas.session import SessionSchema
from app.services.recipe_service import RecipeService
from app.services.session_service import SessionService
from app.services.timer_service import TimerService


async def start_session(
    service: SessionService,
    recipes: RecipeService,
    *,
    provider_recipe_id: str,
    action_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    recipe = await recipes.get_recipe(provider_recipe_id)
    return _session_result(action_id, "start_session", service.start_session(recipe, session_id))


def get_session_state(service: SessionService, *, session_id: str, action_id: str) -> dict[str, Any]:
    return _session_result(action_id, "get_session_state", service.get_session(session_id))


def get_current_step(service: SessionService, *, session_id: str, action_id: str) -> dict[str, Any]:
    step = service.current_step(session_id)
    data = None if step is None else RecipeStepSchema.model_validate(step).model_dump(mode="json")
    return _result(action_id, session_id, "get_current_step", {"step": data})


def complete_current_step(service: SessionService, *, session_id: str, action_id: str) -> dict[str, Any]:
    return _session_result(action_id, "complete_current_step", service.complete_current_step(session_id))


def skip_current_step(service: SessionService, *, session_id: str, action_id: str) -> dict[str, Any]:
    return _session_result(action_id, "skip_current_step", service.skip_current_step(session_id))


def previous_step(service: SessionService, *, session_id: str, action_id: str) -> dict[str, Any]:
    return _session_result(action_id, "previous_step", service.previous_step(session_id))


async def cancel_session(
    service: SessionService,
    timers: TimerService,
    *,
    session_id: str,
    action_id: str,
) -> dict[str, Any]:
    session = service.cancel_session(session_id)
    cancelled = await timers.cancel_session_timers(session_id, action_id=action_id)
    result = _session_result(action_id, "cancel_session", session)
    result["data"]["cancelled_timer_ids"] = [timer.id for timer in cancelled]
    return result


def _session_result(action_id: str, operation: str, session: Any) -> dict[str, Any]:
    data = SessionSchema.model_validate(session).model_dump(mode="json")
    return _result(action_id, session.id, operation, {"session": data})


def _result(action_id: str, session_id: str, operation: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "action_id": action_id,
        "session_id": session_id,
        "operation": operation,
        "data": data,
        "error": None,
    }
