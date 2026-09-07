from app.models.recipe import Ingredient, Recipe, RecipeStep
from app.models.session import SessionStatus
from app.services.session_service import SessionService


def make_recipe() -> Recipe:
    return Recipe(
        id="spoonacular:123",
        name="Provider Pasta",
        servings=2,
        ingredients=(Ingredient(id="pasta", name="pasta", quantity=250, unit="g"),),
        steps=(
            RecipeStep(id="boil", order=1, instruction="Boil water."),
            RecipeStep(id="salt", order=2, instruction="Add salt."),
            RecipeStep(id="cook", order=3, instruction="Cook pasta.", ingredient_ids=("pasta",)),
        ),
        source="spoonacular",
        source_recipe_id="123",
    )


def test_session_progresses_through_completed_and_skipped_steps() -> None:
    service = SessionService()
    session = service.start_session(make_recipe(), "session-1")

    assert service.current_step(session.id).id == "boil"
    service.complete_current_step(session.id)
    assert service.current_step(session.id).id == "salt"
    service.skip_current_step(session.id)
    assert service.current_step(session.id).id == "cook"
    service.complete_current_step(session.id)

    assert session.status is SessionStatus.COMPLETED
    assert session.current_step_id is None
    assert session.completed_step_ids == ["boil", "cook"]
    assert session.skipped_step_ids == ["salt"]


def test_previous_step_reopens_completed_session() -> None:
    service = SessionService()
    session = service.start_session(make_recipe(), "session-1")
    for _ in range(3):
        service.complete_current_step(session.id)

    service.previous_step(session.id)

    assert session.status is SessionStatus.ACTIVE
    assert session.current_step_id == "cook"
    assert "cook" not in session.completed_step_ids


def test_cancelled_session_rejects_step_changes() -> None:
    service = SessionService()
    session = service.start_session(make_recipe(), "session-1")

    service.cancel_session(session.id)

    assert session.status is SessionStatus.CANCELLED
    assert session.current_step_id == "boil"
    for change in (
        service.complete_current_step,
        service.skip_current_step,
        service.previous_step,
    ):
        try:
            change(session.id)
        except ValueError as error:
            assert "cancelled" in str(error)
        else:
            raise AssertionError("cancelled session accepted a step change")
