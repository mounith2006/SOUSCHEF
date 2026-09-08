"""Concurrent, non-blocking timer management for cooking sessions."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.models.timer import CookingTimer, TimerStatus

TimerEventHandler = Callable[[CookingTimer], Awaitable[None]]


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
    ) -> CookingTimer:
        loop = asyncio.get_running_loop()
        timer_id = str(uuid4())
        timer = CookingTimer.running(
            timer_id=timer_id,
            session_id=session_id,
            label=label,
            duration_seconds=duration_seconds,
            action_id=action_id,
            deadline=loop.time() + duration_seconds,
        )
        self._timers[timer_id] = timer
        self._schedule(timer)
        return timer

    def get_timer(self, timer_id: str) -> CookingTimer:
        try:
            timer = self._timers[timer_id]
        except KeyError as error:
            raise KeyError(f"unknown timer: {timer_id}") from error
        self._refresh(timer)
        return timer

    def list_timers(self, session_id: str) -> list[CookingTimer]:
        timers = [timer for timer in self._timers.values() if timer.session_id == session_id]
        for timer in timers:
            self._refresh(timer)
        return timers

    async def pause_timer(self, timer_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status != TimerStatus.RUNNING:
            raise ValueError("only a running timer can be paused")
        self._cancel_task(timer.id)
        timer.status = TimerStatus.PAUSED
        timer.deadline = None
        return timer

    async def resume_timer(self, timer_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status != TimerStatus.PAUSED:
            raise ValueError("only a paused timer can be resumed")
        timer.status = TimerStatus.RUNNING
        timer.deadline = asyncio.get_running_loop().time() + timer.remaining_seconds
        self._schedule(timer)
        return timer

    async def cancel_timer(self, timer_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id)
        if timer.status in (TimerStatus.COMPLETED, TimerStatus.CANCELLED):
            return timer
        self._cancel_task(timer.id)
        timer.status = TimerStatus.CANCELLED
        timer.deadline = None
        timer.completed_at = datetime.now(UTC)
        await self._emit(timer)
        return timer

    async def cancel_session_timers(self, session_id: str) -> None:
        for timer in self.list_timers(session_id):
            if timer.status in (TimerStatus.RUNNING, TimerStatus.PAUSED):
                await self.cancel_timer(timer.id)

    async def close(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    def _refresh(self, timer: CookingTimer) -> None:
        if timer.status == TimerStatus.RUNNING and timer.deadline is not None:
            timer.remaining_seconds = max(0.0, timer.deadline - asyncio.get_running_loop().time())

    def _schedule(self, timer: CookingTimer) -> None:
        self._tasks[timer.id] = asyncio.create_task(self._complete_after_delay(timer.id))

    def _cancel_task(self, timer_id: str) -> None:
        task = self._tasks.pop(timer_id, None)
        if task:
            task.cancel()

    async def _complete_after_delay(self, timer_id: str) -> None:
        timer = self._timers[timer_id]
        try:
            await asyncio.sleep(timer.remaining_seconds)
            if timer.status == TimerStatus.RUNNING:
                timer.remaining_seconds = 0.0
                timer.deadline = None
                timer.status = TimerStatus.COMPLETED
                timer.completed_at = datetime.now(UTC)
                await self._emit(timer)
        except asyncio.CancelledError:
            raise
        finally:
            if self._tasks.get(timer_id) is asyncio.current_task():
                self._tasks.pop(timer_id, None)

    async def _emit(self, timer: CookingTimer) -> None:
        if self._event_handler:
            await self._event_handler(timer)
