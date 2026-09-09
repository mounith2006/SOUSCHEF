from typing import Any, Dict
from ..conversation.interfaces import ToolInterface
from ..services.recipe_service import RecipeService

class RecipeToolRunner(ToolInterface):
    """
    Tool runner that executes structured recipe operations using RecipeService.
    Returns structured dictionaries containing the tool execution results.
    """
    def __init__(self, recipe_service: RecipeService = None):
        self.recipe_service = recipe_service or RecipeService()

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute the specified recipe tool.
        Returns a structured dict with a "status" and relevant fields.
        """
        if tool_name == "find_recipe":
            query = tool_args.get("query", "")
            recipe = self.recipe_service.find_recipe(query)
            if recipe:
                return {
                    "status": "success",
                    "action": "found_recipe",
                    "recipe_name": recipe.canonical_name,
                    "ingredients": recipe.ingredients,
                    "first_step": recipe.steps[0] if recipe.steps else ""
                }
            return {
                "status": "error",
                "message": f"Could not find recipe for '{query}'"
            }

        elif tool_name == "get_step":
            recipe_name = tool_args.get("recipe_name")
            step_idx = tool_args.get("step_index", 0)
            step_text = self.recipe_service.get_step(recipe_name, step_idx)
            
            if step_text:
                return {
                    "status": "success",
                    "action": "step_retrieved",
                    "recipe_name": recipe_name,
                    "step_index": step_idx,
                    "step_text": step_text
                }
            
            total_steps = self.recipe_service.get_total_steps(recipe_name)
            if step_idx >= total_steps and total_steps > 0:
                return {
                    "status": "success",
                    "action": "recipe_complete",
                    "recipe_name": recipe_name,
                    "message": "You have completed all the steps for this recipe!"
                }
                
            return {
                "status": "error",
                "message": f"Could not get step {step_idx} for {recipe_name}"
            }

        elif tool_name == "no_recipe_active":
            return {
                "status": "error",
                "action": "no_recipe_active",
                "message": "No recipe is currently active."
            }

        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }
