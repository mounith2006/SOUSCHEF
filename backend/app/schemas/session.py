"""Serializable cooking-session state."""

from pydantic import BaseModel, ConfigDict

from app.models.session import CookingStatus
from app.schemas.recipe import RecipeSchema, RecipeStepSchema


class CookingSessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recipe: RecipeSchema
    current_step_id: str | None
    completed_step_ids: list[str]
    skipped_step_ids: list[str]
    active_timer_ids: list[str]
    status: CookingStatus


class CookingStateSchema(BaseModel):
    session: CookingSessionSchema
    current_step: RecipeStepSchema | None
