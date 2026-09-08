"""Domain models for structured cooking recipes."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Ingredient:
    id: str
    name: str
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RecipeStep:
    id: str
    order: int
    instruction: str
    ingredient_ids: tuple[str, ...] = ()
    duration_seconds: int | None = None
    heat_level: str | None = None

    def __post_init__(self) -> None:
        if self.order < 1:
            raise ValueError("step order must be at least 1")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("step duration cannot be negative")


@dataclass(frozen=True, slots=True)
class RecipeSearchResult:
    provider_recipe_id: str
    name: str
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class Recipe:
    id: str
    name: str
    servings: int
    ingredients: tuple[Ingredient, ...] = field(default_factory=tuple)
    steps: tuple[RecipeStep, ...] = field(default_factory=tuple)
    source: str = "external"
    source_recipe_id: str | None = None

    def __post_init__(self) -> None:
        if self.servings < 1:
            raise ValueError("servings must be at least 1")
        if len({item.id for item in self.ingredients}) != len(self.ingredients):
            raise ValueError("ingredient ids must be unique")
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("step ids must be unique")
        if len({step.order for step in self.steps}) != len(self.steps):
            raise ValueError("step order values must be unique")
        ingredient_ids = {item.id for item in self.ingredients}
        unknown_ids = {
            item_id
            for step in self.steps
            for item_id in step.ingredient_ids
            if item_id not in ingredient_ids
        }
        if unknown_ids:
            raise ValueError(f"steps reference unknown ingredients: {sorted(unknown_ids)}")

    @property
    def ordered_steps(self) -> tuple[RecipeStep, ...]:
        return tuple(sorted(self.steps, key=lambda step: step.order))

    def step(self, step_id: str) -> RecipeStep:
        try:
            return next(step for step in self.steps if step.id == step_id)
        except StopIteration as error:
            raise KeyError(f"unknown step: {step_id}") from error
