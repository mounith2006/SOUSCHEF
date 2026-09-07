"""Conversation-facing external recipe operations."""

from typing import Any

from app.schemas.recipe import RecipeSchema, RecipeSearchResultSchema
from app.services.recipe_service import RecipeService


async def search_recipes(
    service: RecipeService,
    *,
    query: str,
    action_id: str,
    diet: str | None = None,
    number: int = 5,
) -> dict[str, Any]:
    matches = await service.search_recipes(query, diet=diet, number=number)
    data = [
        RecipeSearchResultSchema.model_validate(match).model_dump(mode="json")
        for match in matches
    ]
    return _result(action_id, "search_recipes", {"recipes": data})


async def get_recipe(
    service: RecipeService, *, provider_recipe_id: str, action_id: str
) -> dict[str, Any]:
    recipe = await service.get_recipe(provider_recipe_id)
    data = RecipeSchema.model_validate(recipe).model_dump(mode="json")
    return _result(action_id, "get_recipe", {"recipe": data})


def _result(action_id: str, operation: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "action_id": action_id, "operation": operation, "data": data, "error": None}
