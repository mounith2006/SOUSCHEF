"""In-memory lifecycle management for isolated cooking sessions."""

from uuid import uuid4

from app.models.recipe import Recipe, RecipeStep
from app.models.session import CookingSession, CookingStatus


class SessionService:
    def __init__(self) -> None:
        self._sessions: dict[str, CookingSession] = {}

    def start_session(self, recipe: Recipe, session_id: str | None = None) -> CookingSession:
        ordered_steps = recipe.ordered_steps
        session = CookingSession(
            id=session_id or str(uuid4()),
            recipe=recipe,
            current_step_id=ordered_steps[0].id if ordered_steps else None,
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> CookingSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise KeyError(f"unknown cooking session: {session_id}") from error

    def current_step(self, session_id: str) -> RecipeStep | None:
        session = self.get_session(session_id)
        return session.recipe.step(session.current_step_id) if session.current_step_id else None

    def complete_current_step(self, session_id: str) -> CookingSession:
        session = self._active_session(session_id)
        if session.current_step_id is None:
            raise ValueError("cooking session has no current step")
        if session.current_step_id not in session.completed_step_ids:
            session.completed_step_ids.append(session.current_step_id)
        self._advance(session)
        return session

    def skip_current_step(self, session_id: str) -> CookingSession:
        session = self._active_session(session_id)
        if session.current_step_id is None:
            raise ValueError("cooking session has no current step")
        if session.current_step_id not in session.skipped_step_ids:
            session.skipped_step_ids.append(session.current_step_id)
        self._advance(session)
        return session

    def previous_step(self, session_id: str) -> CookingSession:
        session = self.get_session(session_id)
        if session.status == CookingStatus.CANCELLED:
            raise ValueError("cooking session is cancelled")
        ordered = session.recipe.ordered_steps
        if not ordered:
            raise ValueError("recipe has no steps")
        current_index = next(
            (index for index, step in enumerate(ordered) if step.id == session.current_step_id),
            len(ordered),
        )
        session.current_step_id = ordered[max(0, current_index - 1)].id
        session.status = CookingStatus.ACTIVE
        return session

    def cancel_session(self, session_id: str) -> CookingSession:
        session = self.get_session(session_id)
        session.status = CookingStatus.CANCELLED
        return session

    def add_timer(self, session_id: str, timer_id: str) -> None:
        session = self._active_session(session_id)
        if timer_id not in session.active_timer_ids:
            session.active_timer_ids.append(timer_id)

    def remove_timer(self, session_id: str, timer_id: str) -> None:
        session = self.get_session(session_id)
        if timer_id in session.active_timer_ids:
            session.active_timer_ids.remove(timer_id)

    def _active_session(self, session_id: str) -> CookingSession:
        session = self.get_session(session_id)
        if session.status != CookingStatus.ACTIVE:
            raise ValueError(f"cooking session is {session.status.value}")
        return session

    @staticmethod
    def _advance(session: CookingSession) -> None:
        ordered = session.recipe.ordered_steps
        index = next(index for index, step in enumerate(ordered) if step.id == session.current_step_id)
        if index + 1 == len(ordered):
            session.current_step_id = None
            session.status = CookingStatus.COMPLETED
        else:
            session.current_step_id = ordered[index + 1].id
