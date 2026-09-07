"""Validated API representations for cooking sessions."""

from pydantic import BaseModel, ConfigDict

from app.models.session import SessionStatus
from app.schemas.recipe import RecipeStepSchema
from app.schemas.timer import TimerSchema


class StartSessionRequest(BaseModel):
    provider_recipe_id: str
    action_id: str
    session_id: str | None = None


class SessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recipe_id: str
    current_step_id: str | None
    completed_step_ids: list[str]
    skipped_step_ids: list[str]
    status: SessionStatus
    recipe_version: int


class SessionWithStepSchema(BaseModel):
    action_id: str | None = None
    session: SessionSchema
    current_step: RecipeStepSchema | None


class CancelSessionRequest(BaseModel):
    action_id: str


class CancelSessionResponse(SessionWithStepSchema):
    cancelled_timers: list[TimerSchema]
