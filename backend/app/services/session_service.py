"""Cooking-session state transitions."""

from uuid import uuid4

from app.models.recipe import Recipe, RecipeStep
from app.models.session import CookingSession, SessionStatus


class SessionService:
    def __init__(self) -> None:
        self._sessions: dict[str, CookingSession] = {}
        self._recipes: dict[str, Recipe] = {}

    def start_session(self, recipe: Recipe, session_id: str | None = None) -> CookingSession:
        steps = recipe.ordered_steps
        session = CookingSession(
            id=session_id or str(uuid4()),
            recipe_id=recipe.id,
            current_step_id=steps[0].id if steps else None,
            status=SessionStatus.ACTIVE if steps else SessionStatus.COMPLETED,
        )
        self._sessions[session.id] = session
        self._recipes[session.id] = recipe
        return session

    def get_session(self, session_id: str) -> CookingSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise KeyError(f"unknown session: {session_id}") from error

    def current_step(self, session_id: str) -> RecipeStep | None:
        session = self.get_session(session_id)
        if session.current_step_id is None:
            return None
        return self._session_recipe(session_id).step(session.current_step_id)

    def complete_current_step(self, session_id: str) -> CookingSession:
        return self._finish_current_step(session_id, skipped=False)

    def skip_current_step(self, session_id: str) -> CookingSession:
        return self._finish_current_step(session_id, skipped=True)

    def previous_step(self, session_id: str) -> CookingSession:
        session = self.get_session(session_id)
        if session.status is SessionStatus.CANCELLED:
            raise ValueError("cancelled cooking session cannot change steps")
        recipe = self._session_recipe(session_id)
        steps = recipe.ordered_steps
        if not steps:
            return session
        if session.current_step_id is None:
            previous = steps[-1]
        else:
            index = self._step_index(recipe, session.current_step_id)
            if index == 0:
                return session
            previous = steps[index - 1]
        if previous.id in session.completed_step_ids:
            session.completed_step_ids.remove(previous.id)
        if previous.id in session.skipped_step_ids:
            session.skipped_step_ids.remove(previous.id)
        session.current_step_id = previous.id
        session.status = SessionStatus.ACTIVE
        return session

    def cancel_session(self, session_id: str) -> CookingSession:
        session = self.get_session(session_id)
        if session.status is SessionStatus.ACTIVE:
            session.status = SessionStatus.CANCELLED
        return session

    def _finish_current_step(self, session_id: str, *, skipped: bool) -> CookingSession:
        session = self.get_session(session_id)
        if session.status is SessionStatus.CANCELLED:
            raise ValueError("cancelled cooking session cannot change steps")
        if session.status is not SessionStatus.ACTIVE or session.current_step_id is None:
            return session
        target = session.skipped_step_ids if skipped else session.completed_step_ids
        if session.current_step_id not in target:
            target.append(session.current_step_id)
        recipe = self._session_recipe(session_id)
        index = self._step_index(recipe, session.current_step_id)
        steps = recipe.ordered_steps
        if index + 1 < len(steps):
            session.current_step_id = steps[index + 1].id
        else:
            session.current_step_id = None
            session.status = SessionStatus.COMPLETED
        return session

    @staticmethod
    def _step_index(recipe: Recipe, step_id: str) -> int:
        for index, step in enumerate(recipe.ordered_steps):
            if step.id == step_id:
                return index
        raise KeyError(f"unknown step: {step_id}")

    def _session_recipe(self, session_id: str) -> Recipe:
        self.get_session(session_id)
        return self._recipes[session_id]
