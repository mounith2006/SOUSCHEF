import asyncio

import httpx
import pytest

from app.services.recipe_service import RecipeProviderError, RecipeService


def provider_recipe() -> dict:
    return {
        "id": 123,
        "title": "Provider Pasta",
        "servings": 2,
        "extendedIngredients": [
            {"id": 1, "name": "pasta", "amount": 250, "unit": "g", "original": "250 g pasta"},
            {"id": 2, "name": "salt", "amount": 2, "unit": "tsp", "original": "2 tsp salt"},
        ],
        "analyzedInstructions": [
            {"steps": [{
                "number": 1,
                "step": "<b>Cook</b> the pasta.",
                "ingredients": [{"id": 1}],
                "length": {"number": 8, "unit": "minutes"},
            }]}
        ],
    }


def test_searches_provider_and_normalizes_recipe() -> None:
    asyncio.run(_searches_provider_and_normalizes_recipe())


async def _searches_provider_and_normalizes_recipe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["apiKey"] == "test-key"
        if request.url.path == "/recipes/complexSearch":
            assert request.url.params["query"] == "pasta"
            assert request.url.params["diet"] == "vegetarian"
            return httpx.Response(200, json={"results": [{"id": 123, "title": "Provider Pasta"}]})
        return httpx.Response(200, json=provider_recipe())

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    )
    service = RecipeService(api_key="test-key", client=client)
    matches = await service.search_recipes("pasta", diet="vegetarian")
    recipe = await service.get_recipe(matches[0].provider_recipe_id)

    assert matches[0].provider_recipe_id == "123"
    assert recipe.id == "spoonacular:123"
    assert recipe.source == "spoonacular"
    assert recipe.step("step-1").instruction == "Cook the pasta."
    assert recipe.step("step-1").duration_seconds == 480
    assert recipe.step("step-1").ingredient_ids == ("ingredient-1",)
    await client.aclose()


def test_rejects_provider_recipe_without_structured_steps() -> None:
    asyncio.run(_rejects_provider_recipe_without_structured_steps())


async def _rejects_provider_recipe_without_structured_steps() -> None:
    payload = provider_recipe()
    payload["analyzedInstructions"] = []
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        base_url="https://provider.test",
    )
    service = RecipeService(api_key="test-key", client=client)

    with pytest.raises(RecipeProviderError, match="no structured instructions"):
        await service.get_recipe("123")
    await client.aclose()
