from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_recipe_service
from app.main import app
from app.models.recipe import Ingredient, Recipe, RecipeSearchResult, RecipeStep


class FakeRecipeService:
    async def search_recipes(
        self, query: str, *, diet: str | None = None, number: int = 5
    ) -> list[RecipeSearchResult]:
        assert query == "pasta"
        assert diet == "vegetarian"
        return [RecipeSearchResult(provider_recipe_id="123", name="Provider Pasta")]

    async def get_recipe(self, provider_recipe_id: str) -> Recipe:
        assert provider_recipe_id == "123"
        return Recipe(
            id="spoonacular:123",
            name="Provider Pasta",
            servings=2,
            ingredients=(Ingredient(id="pasta", name="pasta", quantity=250, unit="g"),),
            steps=(
                RecipeStep(id="step-1", order=1, instruction="Boil water."),
                RecipeStep(
                    id="step-2",
                    order=2,
                    instruction="Cook pasta.",
                    ingredient_ids=("pasta",),
                    duration_seconds=480,
                ),
            ),
            source="spoonacular",
            source_recipe_id="123",
        )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_recipe_service] = lambda: FakeRecipeService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_external_recipe_to_session_and_timer_flow(client: TestClient) -> None:
    search = client.get(
        "/api/recipes/search",
        params={"query": "pasta", "diet": "vegetarian", "number": 3},
    )
    assert search.status_code == 200
    assert search.json()[0]["provider_recipe_id"] == "123"

    started = client.post(
        "/api/sessions",
        json={
            "provider_recipe_id": "123",
            "action_id": "turn-1",
            "session_id": "session-1",
        },
    )
    assert started.status_code == 201
    assert started.json()["action_id"] == "turn-1"
    assert started.json()["current_step"]["id"] == "step-1"

    advanced = client.post("/api/sessions/session-1/complete-step")
    assert advanced.status_code == 200
    assert advanced.json()["current_step"]["id"] == "step-2"

    timer = client.post(
        "/api/timers",
        json={
            "session_id": "session-1",
            "duration_seconds": 60,
            "label": "Pasta",
            "action_id": "turn-2",
        },
    )
    assert timer.status_code == 201
    assert timer.json()["status"] == "running"
    assert timer.json()["action_id"] == "turn-2"

    cancelled = client.post(
        "/api/sessions/session-1/cancel", json={"action_id": "turn-3"}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["action_id"] == "turn-3"
    assert cancelled.json()["session"]["status"] == "cancelled"
    assert cancelled.json()["cancelled_timers"][0]["status"] == "cancelled"
    assert cancelled.json()["cancelled_timers"][0]["action_id"] == "turn-3"

    rejected = client.post("/api/sessions/session-1/complete-step")
    assert rejected.status_code == 409
    assert "cancelled" in rejected.json()["detail"]


def test_unknown_session_returns_404(client: TestClient) -> None:
    response = client.get("/api/sessions/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cooking session not found."
