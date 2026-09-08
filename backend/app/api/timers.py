"""Asynchronous cooking-timer endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_session_service, get_timer_service
from app.schemas.timer import StartTimerRequest, TimerActionRequest, TimerSchema
from app.services.session_service import SessionService
from app.services.timer_service import TimerService

router = APIRouter(prefix="/api/timers", tags=["timers"])


@router.post("", response_model=TimerSchema, status_code=status.HTTP_201_CREATED)
async def start_timer(
    request: StartTimerRequest,
    timers: Annotated[TimerService, Depends(get_timer_service)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> TimerSchema:
    try:
        sessions.get_session(request.session_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cooking session not found."
        ) from error
    timer = await timers.start_timer(
        session_id=request.session_id,
        duration_seconds=request.duration_seconds,
        label=request.label,
        action_id=request.action_id,
    )
    return TimerSchema.model_validate(timer)


@router.get("/{timer_id}", response_model=TimerSchema)
async def get_timer(
    timer_id: str, timers: Annotated[TimerService, Depends(get_timer_service)]
) -> TimerSchema:
    try:
        return TimerSchema.model_validate(timers.get_timer(timer_id))
    except KeyError as error:
        raise _timer_not_found() from error


@router.get("/session/{session_id}", response_model=list[TimerSchema])
async def list_timers(
    session_id: str,
    timers: Annotated[TimerService, Depends(get_timer_service)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> list[TimerSchema]:
    try:
        sessions.get_session(session_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cooking session not found."
        ) from error
    return [TimerSchema.model_validate(timer) for timer in timers.list_timers(session_id)]


@router.post("/{timer_id}/pause", response_model=TimerSchema)
async def pause_timer(
    timer_id: str,
    request: TimerActionRequest,
    timers: Annotated[TimerService, Depends(get_timer_service)],
) -> TimerSchema:
    return await _timer_action(timers.pause_timer, timer_id, request.action_id)


@router.post("/{timer_id}/resume", response_model=TimerSchema)
async def resume_timer(
    timer_id: str,
    request: TimerActionRequest,
    timers: Annotated[TimerService, Depends(get_timer_service)],
) -> TimerSchema:
    return await _timer_action(timers.resume_timer, timer_id, request.action_id)


@router.post("/{timer_id}/cancel", response_model=TimerSchema)
async def cancel_timer(
    timer_id: str,
    request: TimerActionRequest,
    timers: Annotated[TimerService, Depends(get_timer_service)],
) -> TimerSchema:
    return await _timer_action(timers.cancel_timer, timer_id, request.action_id)


async def _timer_action(action: object, timer_id: str, action_id: str) -> TimerSchema:
    try:
        timer = await action(timer_id, action_id=action_id)  # type: ignore[operator]
    except KeyError as error:
        raise _timer_not_found() from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return TimerSchema.model_validate(timer)


def _timer_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timer not found.")
