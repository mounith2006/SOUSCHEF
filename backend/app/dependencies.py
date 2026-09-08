"""FastAPI dependencies for cooking services."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.recipe_service import RecipeService
from app.services.session_service import SessionService
from app.services.timer_service import TimerService


async def get_recipe_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[RecipeService]:
    if not settings.spoonacular_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External recipe provider is not configured.",
        )
    service = RecipeService(
        api_key=settings.spoonacular_api_key,
        base_url=settings.spoonacular_api_url,
        timeout_seconds=settings.spoonacular_timeout_seconds,
    )
    try:
        yield service
    finally:
        await service.close()


def get_session_service(request: Request) -> SessionService:
    return request.app.state.session_service


def get_timer_service(request: Request) -> TimerService:
    return request.app.state.timer_service
