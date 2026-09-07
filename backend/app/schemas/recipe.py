"""Validated API representations for recipes."""

from pydantic import BaseModel, ConfigDict, Field


class IngredientSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None


class RecipeStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order: int = Field(ge=1)
    instruction: str
    ingredient_ids: tuple[str, ...] = ()
    duration_seconds: int | None = Field(default=None, ge=0)
    heat_level: str | None = None


class RecipeSearchResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    provider_recipe_id: str
    name: str
    image_url: str | None = None


class RecipeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    servings: int = Field(ge=1)
    ingredients: tuple[IngredientSchema, ...] = ()
    steps: tuple[RecipeStepSchema, ...] = ()
    source: str
    source_recipe_id: str | None = None
