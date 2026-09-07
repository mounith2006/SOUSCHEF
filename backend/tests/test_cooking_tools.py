import asyncio

from app.models.recipe import Ingredient, Recipe, RecipeStep
from app.services.session_service import SessionService
from app.services.timer_service import TimerService
from app.tools.session_tools import get_current_step, start_session
from app.tools.timer_tools import start_timer


class FakeRecipeService:
    async def get_recipe(self, provider_recipe_id: str) -> Recipe:
        assert provider_recipe_id == "123"
        return Recipe(
            id="spoonacular:123",
            name="Provider Pasta",
            servings=2,
            ingredients=(Ingredient(id="pasta", name="pasta"),),
            steps=(
                RecipeStep(
                    id="step-1",
                    order=1,
                    instruction="Cook pasta.",
                    ingredient_ids=("pasta",),
                ),
            ),
            source="spoonacular",
            source_recipe_id="123",
        )


def test_session_tools_return_correlated_structured_results() -> None:
    asyncio.run(_session_tools_return_correlated_structured_results())


async def _session_tools_return_correlated_structured_results() -> None:
    sessions = SessionService()

    started = await start_session(
        sessions,
        FakeRecipeService(),
        provider_recipe_id="123",
        session_id="session-1",
        action_id="turn-1",
    )
    current = get_current_step(sessions, session_id="session-1", action_id="turn-2")

    assert started["action_id"] == "turn-1"
    assert started["session_id"] == "session-1"
    assert started["data"]["session"]["recipe_id"] == "spoonacular:123"
    assert current["data"]["step"]["id"] == "step-1"


def test_timer_tool_preserves_orchestration_action_id() -> None:
    asyncio.run(_timer_tool_preserves_orchestration_action_id())


async def _timer_tool_preserves_orchestration_action_id() -> None:
    service = TimerService()
    result = await start_timer(
        service,
        session_id="session-1",
        duration_seconds=1,
        label="Pasta",
        action_id="turn-3",
    )

    assert result["action_id"] == "turn-3"
    assert result["operation"] == "start_timer"
    assert result["data"]["timer"]["status"] == "running"
    await service.close()
