"""Structured cooking data produced by an LLM and validated by the application."""

from dataclasses import dataclass, field, replace


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


@dataclass(frozen=True, slots=True)
class Recipe:
    id: str
    name: str
    servings: int
    ingredients: tuple[Ingredient, ...] = field(default_factory=tuple)
    steps: tuple[RecipeStep, ...] = field(default_factory=tuple)
    version: int = 1

    @property
    def ordered_steps(self) -> tuple[RecipeStep, ...]:
        return tuple(sorted(self.steps, key=lambda step: step.order))

    def step(self, step_id: str) -> RecipeStep:
        try:
            return next(step for step in self.steps if step.id == step_id)
        except StopIteration as error:
            raise KeyError(f"unknown recipe step: {step_id}") from error

    def with_version(self, version: int) -> "Recipe":
        return replace(self, version=version)
