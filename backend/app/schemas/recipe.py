"""Validation schemas for LLM-generated recipe data."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IngredientSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    note: str | None = None


class RecipeStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(min_length=1)
    order: int = Field(ge=1)
    instruction: str = Field(min_length=1)
    ingredient_ids: tuple[str, ...] = ()
    duration_seconds: int | None = Field(default=None, ge=0)
    heat_level: str | None = None


class RecipeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str | None = None
    name: str = Field(min_length=1)
    servings: int = Field(ge=1, le=100)
    ingredients: tuple[IngredientSchema, ...] = ()
    steps: tuple[RecipeStepSchema, ...] = Field(min_length=1)
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_references(self) -> "RecipeSchema":
        ingredient_ids = [item.id for item in self.ingredients]
        step_ids = [step.id for step in self.steps]
        orders = [step.order for step in self.steps]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise ValueError("ingredient ids must be unique")
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("step ids must be unique")
        if len(set(orders)) != len(orders):
            raise ValueError("step order values must be unique")
        known = set(ingredient_ids)
        unknown = {item_id for step in self.steps for item_id in step.ingredient_ids if item_id not in known}
        if unknown:
            raise ValueError(f"steps reference unknown ingredients: {sorted(unknown)}")
        return self
