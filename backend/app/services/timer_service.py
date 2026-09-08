"""Non-blocking, multiple-timer service."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.timer import CookingTimer, TimerStatus

TimerEventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class TimerService:
    def __init__(self, event_handler: TimerEventHandler | None = None) -> None:
        self._timers: dict[str, CookingTimer] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._event_handler = event_handler

    async def start_timer(
        self,
        *,
        session_id: str,
        duration_seconds: float,
        label: str,
        action_id: str,
        timer_id: str | None = None,
    ) -> CookingTimer:
        loop = asyncio.get_running_loop()
        timer = CookingTimer.running(
            timer_id=timer_id or str(uuid4()),
            session_id=session_id,
            label=label,
            duration_seconds=duration_seconds,
            action_id=action_id,
            deadline=loop.time() + duration_seconds,
        )
        self._timers[timer.id] = timer
        self._tasks[timer.id] = asyncio.create_task(self._run(timer.id))
        await self._emit("timer.started", timer)
        return timer

    def get_timer(self, timer_id: str) -> CookingTimer:
        try:
            timer = self._timers[timer_id]
        except KeyError as error:
            raise KeyError(f"unknown timer: {timer_id}") from error
        self._refresh_remaining(timer)
        return timer

    def list_timers(self, session_id: str) -> list[CookingTimer]:
        timers = [timer for timer in self._timers.values() if timer.session_id == session_id]
        for timer in timers:
            self._refresh_remaining(timer)
        return timers

    async def pause_timer(self, timer_id: str, *, action_id: str | None = None) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status is not TimerStatus.RUNNING:
            raise ValueError("only a running timer can be paused")
        self._refresh_remaining(timer)
        self._cancel_task(timer_id)
        timer.deadline = None
        timer.status = TimerStatus.PAUSED
        timer.action_id = action_id or timer.action_id
        await self._emit("timer.paused", timer)
        return timer

    async def resume_timer(self, timer_id: str, *, action_id: str | None = None) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status is not TimerStatus.PAUSED:
            raise ValueError("only a paused timer can be resumed")
        timer.status = TimerStatus.RUNNING
        timer.action_id = action_id or timer.action_id
        timer.deadline = asyncio.get_running_loop().time() + timer.remaining_seconds
        self._tasks[timer.id] = asyncio.create_task(self._run(timer.id))
        await self._emit("timer.resumed", timer)
        return timer

    async def cancel_timer(self, timer_id: str, *, action_id: str | None = None) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status in {TimerStatus.CANCELLED, TimerStatus.COMPLETED}:
            return timer
        self._refresh_remaining(timer)
        self._cancel_task(timer_id)
        timer.deadline = None
        timer.status = TimerStatus.CANCELLED
        timer.action_id = action_id or timer.action_id
        timer.completed_at = datetime.now(UTC)
        await self._emit("timer.cancelled", timer)
        return timer

    async def cancel_session_timers(
        self, session_id: str, *, action_id: str
    ) -> list[CookingTimer]:
        cancelled: list[CookingTimer] = []
        for timer in self.list_timers(session_id):
            if timer.status in {TimerStatus.RUNNING, TimerStatus.PAUSED}:
                cancelled.append(await self.cancel_timer(timer.id, action_id=action_id))
        return cancelled

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run(self, timer_id: str) -> None:
        timer = self._timers[timer_id]
        try:
            await asyncio.sleep(timer.remaining_seconds)
        except asyncio.CancelledError:
            return
        timer.remaining_seconds = 0
        timer.deadline = None
        timer.status = TimerStatus.COMPLETED
        timer.completed_at = datetime.now(UTC)
        self._tasks.pop(timer_id, None)
        await self._emit("timer.completed", timer)

    def _refresh_remaining(self, timer: CookingTimer) -> None:
        if timer.status is TimerStatus.RUNNING and timer.deadline is not None:
            timer.remaining_seconds = max(0.0, timer.deadline - asyncio.get_running_loop().time())

    def _cancel_task(self, timer_id: str) -> None:
        task = self._tasks.pop(timer_id, None)
        if task is not None:
            task.cancel()

    async def _emit(self, event_type: str, timer: CookingTimer) -> None:
        if self._event_handler is None:
            return
        result = self._event_handler(
            {
                "type": event_type,
                "action_id": timer.action_id,
                "session_id": timer.session_id,
                "timer_id": timer.id,
                "status": timer.status.value,
            }
        )
        if result is not None:
            await result
