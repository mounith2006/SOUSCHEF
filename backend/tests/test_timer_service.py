import asyncio

from app.models.timer import TimerStatus
from app.services.timer_service import TimerService


def test_multiple_timers_complete_without_blocking() -> None:
    asyncio.run(_multiple_timers_complete_without_blocking())


async def _multiple_timers_complete_without_blocking() -> None:
    events: list[dict] = []
    service = TimerService(events.append)

    first = await service.start_timer(
        session_id="session-1", duration_seconds=0.02, label="Pasta", action_id="a1"
    )
    second = await service.start_timer(
        session_id="session-1", duration_seconds=0.04, label="Sauce", action_id="a2"
    )

    assert {timer.id for timer in service.list_timers("session-1")} == {first.id, second.id}
    await asyncio.sleep(0.06)
    assert service.get_timer(first.id).status is TimerStatus.COMPLETED
    assert service.get_timer(second.id).status is TimerStatus.COMPLETED
    assert [event["type"] for event in events].count("timer.completed") == 2


def test_timer_can_pause_resume_and_cancel() -> None:
    asyncio.run(_timer_can_pause_resume_and_cancel())


async def _timer_can_pause_resume_and_cancel() -> None:
    service = TimerService()
    timer = await service.start_timer(
        session_id="session-1", duration_seconds=1, label="Rest", action_id="start"
    )

    await service.pause_timer(timer.id, action_id="pause")
    assert timer.status is TimerStatus.PAUSED
    assert 0 < timer.remaining_seconds < 1

    await service.resume_timer(timer.id, action_id="resume")
    assert timer.status is TimerStatus.RUNNING
    await service.cancel_timer(timer.id, action_id="cancel")
    assert timer.status is TimerStatus.CANCELLED
    assert timer.action_id == "cancel"
    await service.close()


def test_cancels_only_active_timers_for_session() -> None:
    asyncio.run(_cancels_only_active_timers_for_session())


async def _cancels_only_active_timers_for_session() -> None:
    service = TimerService()
    first = await service.start_timer(
        session_id="session-1", duration_seconds=10, label="One", action_id="start-1"
    )
    second = await service.start_timer(
        session_id="session-2", duration_seconds=10, label="Two", action_id="start-2"
    )

    cancelled = await service.cancel_session_timers("session-1", action_id="end-session")

    assert [timer.id for timer in cancelled] == [first.id]
    assert first.status is TimerStatus.CANCELLED
    assert first.action_id == "end-session"
    assert second.status is TimerStatus.RUNNING
    await service.close()
