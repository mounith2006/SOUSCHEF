"""Allow-listed bridge between conversation orchestration and cooking services."""

from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.conversation.interfaces import ToolInterface
from app.models.session import CookingStatus
from app.schemas.recipe import RecipeSchema
from app.schemas.session import CookingStateSchema
from app.schemas.timer import TimerSchema
from app.services.recipe_service import RecipeService
from app.services.session_service import SessionService
from app.services.timer_service import TimerService


class CookingToolRunner(ToolInterface):
    """Executes only known cooking tools and always returns a structured envelope."""

    def __init__(self, conversation_session_id: str) -> None:
        self.conversation_session_id = conversation_session_id
        self.recipes = RecipeService()
        self.sessions = SessionService()
        self.timers = TimerService(event_handler=self._handle_timer_event)
        self._handlers = {
            "create_recipe": self._create_recipe,
            "start_cooking": self._start_cooking,
            "get_cooking_state": self._get_cooking_state,
            "get_current_step": self._get_current_step,
            "complete_step": self._complete_step,
            "skip_step": self._skip_step,
            "previous_step": self._previous_step,
            "cancel_session": self._cancel_session,
            "start_timer": self._start_timer,
            "get_timer_status": self._get_timer_status,
            "list_timers": self._list_timers,
            "pause_timer": self._pause_timer,
            "resume_timer": self._resume_timer,
            "cancel_timer": self._cancel_timer,
        }

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    async def execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        action_id = str(tool_args.get("action_id") or uuid4())
        handler = self._handlers.get(tool_name)
        if handler is None:
            return self._error(tool_name, action_id, "UNKNOWN_TOOL", f"unknown tool: {tool_name}")
        try:
            data = await handler(dict(tool_args), action_id)
            return {"ok": True, "tool": tool_name, "action_id": action_id, "data": data, "error": None}
        except (KeyError, ValueError, TypeError, ValidationError) as error:
            return self._error(tool_name, action_id, "INVALID_TOOL_ARGUMENTS", str(error))

    async def close(self) -> None:
        await self.timers.close()

    async def _create_recipe(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        # OpenAI-compatible providers sometimes flatten a single object
        # argument. Accept both shapes here; RecipeSchema still validates it.
        payload = args.get("recipe")
        if payload is None:
            payload = {key: value for key, value in args.items() if key != "action_id"}
        if not isinstance(payload, dict):
            raise ValueError("recipe must be a JSON object")
        recipe = self.recipes.create_recipe(payload)
        return RecipeSchema.model_validate(recipe).model_dump(mode="json")

    async def _start_cooking(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        recipe = self.recipes.get_recipe(args["recipe_id"])
        session = self.sessions.start_session(recipe, args.get("session_id", self.conversation_session_id))
        return self._state(session.id)

    async def _get_cooking_state(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        return self._state(self._session_id(args))

    async def _get_current_step(self, args: dict[str, Any], _: str) -> dict[str, Any] | None:
        state = self._state(self._session_id(args))
        return state["current_step"]

    async def _complete_step(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        session_id = self._session_id(args)
        self.sessions.complete_current_step(session_id)
        return self._state(session_id)

    async def _skip_step(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        self._require_confirmation(args, "skip the current step")
        session_id = self._session_id(args)
        self.sessions.skip_current_step(session_id)
        return self._state(session_id)

    async def _previous_step(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        session_id = self._session_id(args)
        self.sessions.previous_step(session_id)
        return self._state(session_id)

    async def _cancel_session(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        self._require_confirmation(args, "cancel the cooking session")
        session_id = self._session_id(args)
        self.sessions.cancel_session(session_id)
        await self.timers.cancel_session_timers(session_id)
        return self._state(session_id)

    async def _start_timer(self, args: dict[str, Any], action_id: str) -> dict[str, Any]:
        session_id = self._session_id(args)
        session = self.sessions.get_session(session_id)
        if session.status != CookingStatus.ACTIVE:
            raise ValueError(f"cooking session is {session.status.value}")
        timer = await self.timers.start_timer(
            session_id=session_id,
            duration_seconds=float(args["duration_seconds"]),
            label=str(args.get("label") or "Cooking timer"),
            action_id=action_id,
        )
        self.sessions.add_timer(session_id, timer.id)
        return self._timer(timer)

    async def _get_timer_status(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        return self._timer(self.timers.get_timer(args["timer_id"]))

    async def _list_timers(self, args: dict[str, Any], _: str) -> list[dict[str, Any]]:
        return [self._timer(timer) for timer in self.timers.list_timers(self._session_id(args))]

    async def _pause_timer(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        return self._timer(await self.timers.pause_timer(args["timer_id"]))

    async def _resume_timer(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        return self._timer(await self.timers.resume_timer(args["timer_id"]))

    async def _cancel_timer(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        return self._timer(await self.timers.cancel_timer(args["timer_id"]))

    async def _handle_timer_event(self, timer: Any) -> None:
        self.sessions.remove_timer(timer.session_id, timer.id)

    def _state(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get_session(session_id)
        state = CookingStateSchema(session=session, current_step=self.sessions.current_step(session_id))
        return state.model_dump(mode="json")

    @staticmethod
    def _timer(timer: Any) -> dict[str, Any]:
        return TimerSchema.model_validate(timer).model_dump(mode="json")

    def _session_id(self, args: dict[str, Any]) -> str:
        return str(args.get("session_id", self.conversation_session_id))

    @staticmethod
    def _require_confirmation(args: dict[str, Any], action: str) -> None:
        if args.get("confirmed") is not True:
            raise ValueError(f"explicit user confirmation is required to {action}")

    @staticmethod
    def _error(tool: str, action_id: str, code: str, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "tool": tool,
            "action_id": action_id,
            "data": None,
            "error": {"code": code, "message": message},
        }
