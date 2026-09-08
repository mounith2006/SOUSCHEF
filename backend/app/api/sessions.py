"""Cooking-session endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_recipe_service, get_session_service, get_timer_service
from app.schemas.recipe import RecipeStepSchema
from app.schemas.session import (
    CancelSessionRequest,
    CancelSessionResponse,
    SessionSchema,
    SessionWithStepSchema,
    StartSessionRequest,
)
from app.schemas.timer import TimerSchema
from app.services.recipe_service import RecipeProviderError, RecipeService
from app.services.session_service import SessionService
from app.services.timer_service import TimerService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionWithStepSchema, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartSessionRequest,
    recipes: Annotated[RecipeService, Depends(get_recipe_service)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionWithStepSchema:
    try:
        recipe = await recipes.get_recipe(request.provider_recipe_id)
    except RecipeProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External recipe provider is temporarily unavailable.",
        ) from error
    session = sessions.start_session(recipe, request.session_id)
    return _with_step(sessions, session.id, action_id=request.action_id)


@router.get("/{session_id}", response_model=SessionWithStepSchema)
async def get_session(
    session_id: str,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionWithStepSchema:
    return _with_step_or_404(sessions, session_id)


@router.post("/{session_id}/complete-step", response_model=SessionWithStepSchema)
async def complete_step(
    session_id: str,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionWithStepSchema:
    return _transition(sessions, session_id, sessions.complete_current_step)


@router.post("/{session_id}/skip-step", response_model=SessionWithStepSchema)
async def skip_step(
    session_id: str,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionWithStepSchema:
    return _transition(sessions, session_id, sessions.skip_current_step)


@router.post("/{session_id}/previous-step", response_model=SessionWithStepSchema)
async def previous_step(
    session_id: str,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionWithStepSchema:
    return _transition(sessions, session_id, sessions.previous_step)


@router.post("/{session_id}/cancel", response_model=CancelSessionResponse)
async def cancel_session(
    session_id: str,
    request: CancelSessionRequest,
    sessions: Annotated[SessionService, Depends(get_session_service)],
    timers: Annotated[TimerService, Depends(get_timer_service)],
) -> CancelSessionResponse:
    try:
        sessions.cancel_session(session_id)
    except KeyError as error:
        raise _session_not_found() from error
    cancelled = await timers.cancel_session_timers(session_id, action_id=request.action_id)
    state = _with_step(sessions, session_id, action_id=request.action_id)
    return CancelSessionResponse(
        **state.model_dump(),
        cancelled_timers=[TimerSchema.model_validate(timer) for timer in cancelled],
    )


def _transition(sessions: SessionService, session_id: str, operation: object) -> SessionWithStepSchema:
    try:
        operation(session_id)  # type: ignore[operator]
    except KeyError as error:
        raise _session_not_found() from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _with_step(sessions, session_id)


def _with_step_or_404(sessions: SessionService, session_id: str) -> SessionWithStepSchema:
    try:
        return _with_step(sessions, session_id)
    except KeyError as error:
        raise _session_not_found() from error


def _with_step(
    sessions: SessionService, session_id: str, action_id: str | None = None
) -> SessionWithStepSchema:
    session = sessions.get_session(session_id)
    step = sessions.current_step(session_id)
    return SessionWithStepSchema(
        action_id=action_id,
        session=SessionSchema.model_validate(session),
        current_step=None if step is None else RecipeStepSchema.model_validate(step),
    )


def _session_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cooking session not found.")
