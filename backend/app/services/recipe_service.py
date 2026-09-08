"""External recipe search and normalization through Spoonacular."""

from html import unescape
from html.parser import HTMLParser
from typing import Any

import httpx

from app.models.recipe import Ingredient, Recipe, RecipeSearchResult, RecipeStep


class RecipeProviderError(RuntimeError):
    """Raised when the external recipe provider cannot satisfy a request."""


class RecipeService:
    """Fetch recipes directly from Spoonacular; no internal catalogue is used."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.spoonacular.com",
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SPOONACULAR_API_KEY is required")
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )

    async def search_recipes(
        self, query: str, *, diet: str | None = None, number: int = 5
    ) -> list[RecipeSearchResult]:
        if not query.strip():
            raise ValueError("recipe search query cannot be empty")
        if not 1 <= number <= 20:
            raise ValueError("recipe search result count must be between 1 and 20")
        params: dict[str, str | int] = {
            "apiKey": self._api_key,
            "query": query,
            "number": number,
        }
        if diet:
            params["diet"] = diet
        payload = await self._get_json("/recipes/complexSearch", params=params)
        results = payload.get("results")
        if not isinstance(results, list):
            raise RecipeProviderError("provider returned an invalid recipe search response")
        return [
            RecipeSearchResult(
                provider_recipe_id=str(item["id"]),
                name=str(item["title"]),
                image_url=item.get("image"),
            )
            for item in results
            if "id" in item and "title" in item
        ]

    async def get_recipe(self, provider_recipe_id: str) -> Recipe:
        payload = await self._get_json(
            f"/recipes/{provider_recipe_id}/information",
            params={"apiKey": self._api_key, "includeNutrition": "false"},
        )
        return _normalize_recipe(payload)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise RecipeProviderError("recipe provider timed out") from error
        except httpx.HTTPStatusError as error:
            raise RecipeProviderError(
                f"recipe provider returned HTTP {error.response.status_code}"
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise RecipeProviderError("recipe provider request failed") from error
        if not isinstance(payload, dict):
            raise RecipeProviderError("recipe provider returned invalid JSON")
        return payload


def _normalize_recipe(data: dict[str, Any]) -> Recipe:
    try:
        provider_id = str(data["id"])
        name = str(data["title"])
        servings = int(data["servings"])
    except (KeyError, TypeError, ValueError) as error:
        raise RecipeProviderError("provider recipe is missing required metadata") from error

    ingredients: list[Ingredient] = []
    ingredient_ids_by_provider_id: dict[str, str] = {}
    for index, item in enumerate(data.get("extendedIngredients") or [], start=1):
        ingredient_id = f"ingredient-{index}"
        provider_ingredient_id = str(item.get("id", ""))
        if provider_ingredient_id:
            ingredient_ids_by_provider_id.setdefault(provider_ingredient_id, ingredient_id)
        ingredients.append(
            Ingredient(
                id=ingredient_id,
                name=str(item.get("nameClean") or item.get("name") or "ingredient"),
                quantity=_optional_float(item.get("amount")),
                unit=str(item.get("unit") or "") or None,
                note=str(item.get("original") or "") or None,
            )
        )

    steps: list[RecipeStep] = []
    for index, item in enumerate(_instruction_steps(data), start=1):
        referenced_ids = tuple(
            ingredient_ids_by_provider_id[str(reference.get("id"))]
            for reference in item.get("ingredients") or []
            if str(reference.get("id")) in ingredient_ids_by_provider_id
        )
        instruction = _plain_text(str(item.get("step") or ""))
        if not instruction:
            continue
        steps.append(
            RecipeStep(
                id=f"step-{index}",
                order=len(steps) + 1,
                instruction=instruction,
                ingredient_ids=tuple(dict.fromkeys(referenced_ids)),
                duration_seconds=_duration_seconds(item.get("length")),
            )
        )

    if not ingredients:
        raise RecipeProviderError("provider recipe has no ingredients")
    if not steps:
        raise RecipeProviderError("provider recipe has no structured instructions")
    return Recipe(
        id=f"spoonacular:{provider_id}",
        name=name,
        servings=servings,
        ingredients=tuple(ingredients),
        steps=tuple(steps),
        source="spoonacular",
        source_recipe_id=provider_id,
    )


def _instruction_steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    sections = data.get("analyzedInstructions") or []
    return [step for section in sections for step in section.get("steps", [])]


def _duration_seconds(length: Any) -> int | None:
    if not isinstance(length, dict):
        return None
    try:
        number = float(length["number"])
    except (KeyError, TypeError, ValueError):
        return None
    unit = str(length.get("unit", "minutes")).casefold()
    multiplier = 3600 if unit.startswith("hour") else 1 if unit.startswith("second") else 60
    return round(number * multiplier)


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(unescape(value))
    return " ".join("".join(parser.parts).split())
