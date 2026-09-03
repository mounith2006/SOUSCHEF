# Spoonacular-to-SOUSCHEF recipe mapping

Use Spoonacular only through the FastAPI backend. The frontend never receives the Spoonacular API key.

## Recommended flow

1. Search with `GET /recipes/complexSearch` using `addRecipeInformation=true` and `instructionsRequired=true`.
2. When a user chooses a result, retrieve the full recipe with `GET /recipes/{id}/information` using `includeNutrition=false`.
3. Normalize the response to the SOUSCHEF recipe shape below.
4. Store the normalized object in the active cooking session. Cache it in PostgreSQL when database persistence is added.

## Field map

| SOUSCHEF field             | Spoonacular response field                      | Rule                                                                                                                                 |
| -------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `source`                   | —                                               | Set to `"spoonacular"`.                                                                                                              |
| `source_recipe_id`         | `id`                                            | Keep the original numeric recipe ID.                                                                                                 |
| `id`                       | `id`                                            | Use `spoonacular-{id}`.                                                                                                              |
| `title`                    | `title`                                         | Copy as supplied.                                                                                                                    |
| `servings`                 | `servings`                                      | Copy as supplied.                                                                                                                    |
| `prep_time_minutes`        | `readyInMinutes`                                | Use as an estimated total time for Phase 1; Spoonacular does not reliably separate preparation and cooking time.                     |
| `cook_time_minutes`        | `readyInMinutes`                                | Use as the same estimated total time for Phase 1, or set to `null` if you want to avoid duplication.                                 |
| `ingredients[]`            | `extendedIngredients[]`                         | Map `nameClean` (fallback `name`), `amount`, `unit`, and `original` as the note.                                                     |
| `steps[]`                  | `analyzedInstructions[0].steps[]`               | Map `number` to `step_number`, and `step` to `instruction`.                                                                          |
| `steps[].duration_seconds` | `length.number` + `length.unit`                 | Convert minutes to seconds. Set `null` when there is no length.                                                                      |
| `steps[].ingredients_used` | `ingredients[].name` within an instruction step | Map to an array of ingredient names.                                                                                                 |
| `steps[].temperature`      | —                                               | Set to `null` initially. Temperature is often written only inside the instruction text, not supplied as a reliable structured field. |

## Required safeguards

- If `analyzedInstructions` is empty, call Spoonacular's instruction-analysis endpoint or show the original instruction only after it has been reviewed.
- Do not invent a duration or temperature when the source does not supply one.
- Preserve the original source recipe ID so a recipe can be refreshed or traced later.
- The assistant should answer a quantity, time, or temperature only when that field is present; otherwise it should say that the recipe does not specify it.

## Normalized recipe shape

```json
{
  "id": "spoonacular-12345",
  "source": "spoonacular",
  "source_recipe_id": 12345,
  "title": "Example recipe",
  "servings": 2,
  "prep_time_minutes": 30,
  "cook_time_minutes": 30,
  "ingredients": [
    { "name": "Pasta", "quantity": 200, "unit": "g", "note": "200 g pasta" }
  ],
  "steps": [
    {
      "step_number": 1,
      "instruction": "Cook the pasta.",
      "duration_seconds": 600,
      "temperature": null,
      "ingredients_used": ["Pasta"]
    }
  ]
}
```

Source documentation: https://spoonacular.com/food-api/docs
