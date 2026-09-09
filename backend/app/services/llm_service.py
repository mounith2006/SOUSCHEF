import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from ..conversation.interfaces import LLMInterface
from ..conversation.llm_protocol import COOKING_SYSTEM_PROMPT
from ..config import get_settings

logger = logging.getLogger("souschef.llm")

class LLMUnavailableError(Exception):
    """Raised when LLM API service is unconfigured or unreachable."""
    pass


class LocalTestLLM(LLMInterface):
    """
    Deterministic Local LLM implementation for development and testing.
    Does not require OpenAI API key or internet access.
    """

    async def generate_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> str:
        text = user_input.lower()

        # Check if there is a TOOL RESULT in the history
        tool_result_str = None
        for msg in reversed(conversation_history):
            if msg["role"] == "system" and "[TOOL RESULT:" in msg["content"]:
                tool_result_str = msg["content"]
                break

        if tool_result_str:
            import ast
            try:
                dict_str = tool_result_str.split("[TOOL RESULT: ")[1].rstrip("]")
                tool_data = ast.literal_eval(dict_str)
                status = tool_data.get("status")
                action = tool_data.get("action")

                if status == "success":
                    if action == "found_recipe":
                        name = tool_data.get("recipe_name")
                        ingredients = tool_data.get("ingredients", [])
                        first_step = tool_data.get("first_step", "")
                        response = f"Let's make {name}! Here are the ingredients: {', '.join(ingredients)}. First, {first_step}"
                        return response
                    elif action == "step_retrieved":
                        step_text = tool_data.get("step_text")
                        response = f"Next, {step_text}"
                        return response
                    elif action == "recipe_complete":
                        response = "You have completed all the steps for this recipe! Enjoy your meal!"
                        return response
                elif status == "error":
                    if action == "no_recipe_active":
                        return "No recipe is currently active. Please tell me what you'd like to cook first."
                    return tool_data.get("message", "Something went wrong.")
            except Exception:
                pass

        if "how long" in text and "pasta" in text:
            response = "For most pasta, cook it for about eight to twelve minutes."
        elif "how long" in text:
            response = "Cook until tender, usually about eight to ten minutes."
        elif "how much" in text and "pasta" in text:
            response = "Use about 100 grams of pasta per person."
        elif "salt" in text:
            response = "Start with about one teaspoon of salt and adjust to taste."
        elif "recipe" in text or "carbonara" in text:
            response = "To make carbonara, combine eggs, guanciale, pecorino cheese, and pasta."
        elif "timer" in text:
            response = "Timer set for the requested duration."
        else:
            response = f"I heard '{user_input}'. This is a local test response."

        logger.info(f"[LOCAL LLM RESPONSE] '{response}'")
        return response


class OpenAILLMService(LLMInterface):
    """
    Real LLM Service using OpenAI Chat Completions API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or self.settings.llm_model

    async def generate_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> str:
        """Generate LLM response given user input and recent conversation history."""
        if not self.api_key:
            raise LLMUnavailableError(
                "OPENAI_API_KEY environment variable is not configured. "
                "Please set OPENAI_API_KEY in your .env file or environment."
            )

        messages = [
            {
                "role": "system",
                "content": COOKING_SYSTEM_PROMPT,
            }
        ]

        # Append formatted conversation history
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Append latest user input if not already present
        if not conversation_history or conversation_history[-1].get("content") != user_input:
            messages.append({"role": "user", "content": user_input})

        logger.info(f"[LLM REQUEST] Model: {self.model} | User Input: '{user_input}'")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                logger.info(f"[LLM RESPONSE] Response: '{content}'")
                return content
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API status error: {e.response.status_code} - {e.response.text}")
            raise LLMUnavailableError(f"OpenAI API returned error status {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenAI API connection error: {e}")
            raise LLMUnavailableError(f"Failed to communicate with LLM provider: {e}") from e



class NvidiaLLMService(LLMInterface):
    """
    Real LLM Service using NVIDIA NIM Chat Completions API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.nvidia_api_key or os.getenv("NVIDIA_API_KEY")
        self.model = model or self.settings.llm_model
        self.api_url = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

    async def generate_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> str:
        """Generate LLM response using NVIDIA NIM API."""
        if not self.api_key or "your_" in self.api_key.lower():
            raise LLMUnavailableError("NVIDIA_API_KEY environment variable is not configured.")

        system_prompt = COOKING_SYSTEM_PROMPT

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        # Append formatted conversation history
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Append latest user input if not already present
        if not conversation_history or conversation_history[-1].get("content") != user_input:
            messages.append({"role": "user", "content": user_input})

        logger.info(f"[NVIDIA LLM REQUEST] Model: {self.model} | User Input: '{user_input}'")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.nvidia_timeout_seconds) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict) or "choices" not in data or not data["choices"]:
                    raise LLMUnavailableError("Invalid NVIDIA API response: missing choices")

                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content")

                if content is None:
                    raise LLMUnavailableError("Invalid NVIDIA API response: missing content")

                content_str = str(content).strip()
                logger.info(f"[NVIDIA LLM RESPONSE] Response: '{content_str}'")
                return content_str
        except httpx.HTTPStatusError as e:
            logger.error(f"NVIDIA API status error: {e.response.status_code}")
            raise LLMUnavailableError(f"NVIDIA API returned error status {e.response.status_code}") from e
        except httpx.TimeoutException as e:
            logger.error(f"NVIDIA API timeout: {e}")
            raise LLMUnavailableError("NVIDIA API request timed out") from e
        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"NVIDIA API connection error: {e}")
            raise LLMUnavailableError(f"Failed to communicate with NVIDIA LLM provider: {e}") from e


def get_llm_service(provider: Optional[str] = None) -> LLMInterface:
    """Factory helper returning appropriate LLMInterface provider."""
    settings = get_settings()
    selected = provider or settings.llm_provider or os.getenv("LLM_PROVIDER", "local")
    selected = selected.lower()

    if selected == "local":
        return LocalTestLLM()
    elif selected == "openai":
        return OpenAILLMService()
    elif selected == "nvidia":
        return NvidiaLLMService()
    else:
        raise LLMUnavailableError(
            f"Unsupported LLM provider: '{selected}'. Supported providers are: local, openai, nvidia."
        )
