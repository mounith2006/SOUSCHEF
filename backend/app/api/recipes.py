"""External recipe search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_recipe_service
from app.schemas.recipe import RecipeSchema, RecipeSearchResultSchema
from app.services.recipe_service import RecipeProviderError, RecipeService

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("/search", response_model=list[RecipeSearchResultSchema])
async def search_recipes(
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    query: Annotated[str, Query(min_length=1)],
    diet: str | None = None,
    number: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[RecipeSearchResultSchema]:
    try:
        results = await service.search_recipes(query, diet=diet, number=number)
    except RecipeProviderError as error:
        raise _provider_unavailable() from error
    return [RecipeSearchResultSchema.model_validate(result) for result in results]


@router.get("/{provider_recipe_id}", response_model=RecipeSchema)
async def get_recipe(
    provider_recipe_id: str,
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeSchema:
    try:
        recipe = await service.get_recipe(provider_recipe_id)
    except RecipeProviderError as error:
        raise _provider_unavailable() from error
    return RecipeSchema.model_validate(recipe)


def _provider_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="External recipe provider is temporarily unavailable.",
    )
