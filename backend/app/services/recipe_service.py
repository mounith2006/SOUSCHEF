from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class Recipe:
    canonical_name: str
    aliases: List[str]
    ingredients: List[str]
    steps: List[str]

class RecipeService:
    """
    Stateless service that provides deterministic recipe lookup and data.
    Active cooking state is maintained by ConversationContext, not here.
    """
    def __init__(self):
        self.recipes: Dict[str, Recipe] = {
            "chicken pasta": Recipe(
                canonical_name="Chicken Pasta",
                aliases=["chicken pasta", "chicken and pasta"],
                ingredients=[
                    "pasta",
                    "chicken",
                    "olive oil",
                    "garlic",
                    "cream",
                    "parmesan",
                    "salt",
                    "pepper"
                ],
                steps=[
                    "Bring a pot of salted water to a boil.",
                    "Cook the pasta according to package instructions, then drain.",
                    "Season the chicken with salt and pepper, then cook it in a pan with olive oil until browned.",
                    "Add minced garlic to the pan and cook for 1 minute.",
                    "Stir in the cream and parmesan cheese, simmering until thickened.",
                    "Toss the cooked pasta with the chicken and sauce. Serve hot."
                ]
            ),
            "carbonara": Recipe(
                canonical_name="Carbonara",
                aliases=["carbonara", "spaghetti carbonara", "pasta carbonara"],
                ingredients=[
                    "spaghetti",
                    "guanciale or pancetta",
                    "eggs",
                    "pecorino romano",
                    "black pepper"
                ],
                steps=[
                    "Boil the spaghetti in salted water until al dente.",
                    "In a bowl, whisk together the eggs and grated pecorino cheese.",
                    "Crisp the guanciale in a large skillet over medium heat.",
                    "Transfer the pasta to the skillet with the guanciale, off the heat.",
                    "Quickly stir in the egg mixture, adding a splash of pasta water to create a creamy sauce.",
                    "Top with plenty of freshly cracked black pepper and serve."
                ]
            ),
            "pancakes": Recipe(
                canonical_name="Pancakes",
                aliases=["pancakes", "flapjacks", "hotcakes", "pancake"],
                ingredients=[
                    "flour",
                    "milk",
                    "eggs",
                    "baking powder",
                    "sugar",
                    "butter",
                    "salt"
                ],
                steps=[
                    "In a large bowl, whisk together the flour, sugar, baking powder, and a pinch of salt.",
                    "In a separate bowl, mix the milk, eggs, and melted butter.",
                    "Pour the wet ingredients into the dry ingredients and stir until just combined.",
                    "Heat a lightly oiled griddle or pan over medium-high heat.",
                    "Pour a quarter cup of batter for each pancake onto the griddle.",
                    "Brown on both sides and serve hot with syrup."
                ]
            )
        }

    def get_recipe(self, canonical_name: str) -> Optional[Recipe]:
        """Fetch a recipe exactly by its canonical key."""
        return self.recipes.get(canonical_name.lower())

    def find_recipe(self, user_text: str) -> Optional[Recipe]:
        """Find a recipe if its canonical name or alias appears in the text."""
        text = user_text.lower()
        for recipe in self.recipes.values():
            if recipe.canonical_name.lower() in text:
                return recipe
            for alias in recipe.aliases:
                if alias in text:
                    return recipe
        return None

    def get_step(self, canonical_name: str, step_index: int) -> Optional[str]:
        """Get a specific step string for a recipe by index."""
        recipe = self.get_recipe(canonical_name)
        if not recipe:
            return None
        if step_index < 0 or step_index >= len(recipe.steps):
            return None
        return recipe.steps[step_index]

    def get_total_steps(self, canonical_name: str) -> int:
        """Get the total number of steps for a recipe."""
        recipe = self.get_recipe(canonical_name)
        if not recipe:
            return 0
        return len(recipe.steps)
