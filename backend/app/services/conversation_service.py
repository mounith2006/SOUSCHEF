from typing import Optional, Dict, Any
from ..conversation.engine import ConversationEngine
from ..conversation.interfaces import LLMInterface, TTSInterface, STTInterface
from .rime_tts_service import RimeTTSService
from .stt_service import DefaultSTTService
from .llm_service import get_llm_service, LocalTestLLM
from ..tools.cooking_tool_runner import CookingToolRunner
from ..models.recipe import Recipe, RecipeStep, Ingredient
from ..tools.recipe_tools import RecipeToolRunner

class CookingRecipeToolRunner(CookingToolRunner):
    """Bridge runner combining cooking session tools and recipe tools."""

    def __init__(self, conversation_session_id: str) -> None:
        super().__init__(conversation_session_id)
        self.recipe_runner = RecipeToolRunner(self.recipes)

    async def execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "find_recipe":
            query = tool_args.get("query", "")
            static_recipe = self.recipes.find_recipe(query)
            if static_recipe:
                recipe_id = static_recipe.canonical_name.lower().replace(" ", "-")
                if recipe_id not in self.recipes._recipes:
                    ingredients_models = tuple(
                        Ingredient(id=f"ing-{i}", name=ing, quantity=1, unit="unit")
                        for i, ing in enumerate(static_recipe.ingredients)
                    )
                    steps_models = tuple(
                        RecipeStep(id=f"step-{i}", order=i + 1, instruction=step)
                        for i, step in enumerate(static_recipe.steps)
                    )
                    full_recipe = Recipe(
                        id=recipe_id,
                        name=static_recipe.canonical_name,
                        servings=2,
                        ingredients=ingredients_models,
                        steps=steps_models,
                        version=1,
                    )
                    self.recipes._recipes[recipe_id] = full_recipe
                else:
                    full_recipe = self.recipes._recipes[recipe_id]

                # Start session in SessionService so CookingToolRunner state is active
                self.sessions.start_session(full_recipe, self.conversation_session_id)

                return {
                    "ok": True,
                    "status": "success",
                    "action": "found_recipe",
                    "recipe_name": static_recipe.canonical_name,
                    "ingredients": static_recipe.ingredients,
                    "first_step": static_recipe.steps[0] if static_recipe.steps else "",
                    "data": {"instruction": static_recipe.steps[0] if static_recipe.steps else ""},
                }
            return {
                "ok": False,
                "status": "error",
                "message": f"Could not find recipe for '{query}'",
            }

        if tool_name == "get_step":
            res = await self.recipe_runner.execute_tool(tool_name, tool_args)
            if isinstance(res, dict):
                res["ok"] = res.get("status") == "success"
                res["data"] = {"instruction": res.get("step_text", "")}
            return res

        if tool_name == "no_recipe_active":
            return {
                "ok": False,
                "status": "error",
                "action": "no_recipe_active",
                "message": "No recipe is currently active.",
            }

        return await super().execute_tool(tool_name, tool_args)

class SessionConversationManager:
    """Registry managing session-scoped ConversationEngine instances for multi-session safety."""

    def __init__(self):
        self._engines: Dict[str, ConversationEngine] = {}

    def get_engine_for_session(
        self,
        session_id: str = "default_session",
        tts: Optional[TTSInterface] = None,
        llm: Optional[LLMInterface] = None,
        stt: Optional[STTInterface] = None,
    ) -> ConversationEngine:
        if session_id not in self._engines:
            tts_inst = tts or RimeTTSService()
            llm_inst = llm or get_llm_service()
            stt_inst = stt or DefaultSTTService()
            self._engines[session_id] = ConversationEngine(
                tts=tts_inst,
                llm=llm_inst,
                stt=stt_inst,
                session_id=session_id,
                tool_runner=CookingRecipeToolRunner(session_id),
            )
        return self._engines[session_id]

    def clear_session(self, session_id: str) -> None:
        if session_id in self._engines:
            del self._engines[session_id]

_manager = SessionConversationManager()

def get_conversation_engine(
    session_id: str = "default_session",
    tts: Optional[TTSInterface] = None,
    llm: Optional[LLMInterface] = None,
    stt: Optional[STTInterface] = None,
) -> ConversationEngine:
    """Helper to retrieve or create session-scoped ConversationEngine instance."""
    return _manager.get_engine_for_session(session_id=session_id, tts=tts, llm=llm, stt=stt)
