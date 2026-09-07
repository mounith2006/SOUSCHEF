import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

import httpx

from app.config import get_settings
from app.services.llm_service import (
    get_llm_service,
    LocalTestLLM,
    OpenAILLMService,
    NvidiaLLMService,
    LLMUnavailableError,
)
from app.conversation.engine import ConversationEngine
from app.conversation.state import ConversationState


class MockTTS:
    def __init__(self):
        self.spoken_texts = []
        self.stop_called_count = 0

    async def speak(self, text: str) -> None:
        self.spoken_texts.append(text)

    async def stop(self) -> None:
        self.stop_called_count += 1


class TestNvidiaLLMService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_key = "nvapi-test-mock-key-12345"

    # 1. Provider factory tests
    def test_factory_local(self):
        llm = get_llm_service(provider="local")
        self.assertIsInstance(llm, LocalTestLLM)

    def test_factory_openai(self):
        llm = get_llm_service(provider="openai")
        self.assertIsInstance(llm, OpenAILLMService)

    def test_factory_nvidia(self):
        with patch.dict(os.environ, {"NVIDIA_API_KEY": self.mock_key}):
            llm = get_llm_service(provider="nvidia")
            self.assertIsInstance(llm, NvidiaLLMService)

    def test_factory_unsupported_provider(self):
        with self.assertRaises(LLMUnavailableError) as ctx:
            get_llm_service(provider="invalid_provider")
        self.assertIn("Unsupported LLM provider", str(ctx.exception))

    # 2. Missing & placeholder API key validation
    async def test_missing_nvidia_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(get_settings(), "nvidia_api_key", None):
                service = NvidiaLLMService(api_key=None)
                with self.assertRaises(LLMUnavailableError) as ctx:
                    await service.generate_response("hello", [])
                self.assertIn("NVIDIA_API_KEY environment variable is not configured", str(ctx.exception))
                self.assertNotIn(self.mock_key, str(ctx.exception))

    async def test_placeholder_nvidia_api_key(self):
        service = NvidiaLLMService(api_key="your_nvidia_api_key_here")
        with self.assertRaises(LLMUnavailableError) as ctx:
            await service.generate_response("hello", [])
        self.assertIn("NVIDIA_API_KEY environment variable is not configured", str(ctx.exception))

    # 3. Request construction, headers, system prompt, and context passing
    async def test_nvidia_request_construction(self):
        captured_request = {}

        async def mock_post(url, headers=None, json=None):
            captured_request["url"] = url
            captured_request["headers"] = headers
            captured_request["json"] = json

            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Hi! I'm SOUSCHEF. What would you like to cook today?"
                        }
                    }
                ]
            }
            return mock_resp

        service = NvidiaLLMService(api_key=self.mock_key, model="meta/llama-3.1-8b-instruct")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
            response = await service.generate_response("What can I cook?", history)

            self.assertEqual(response, "Hi! I'm SOUSCHEF. What would you like to cook today?")

            # Check Headers
            self.assertEqual(captured_request["headers"]["Authorization"], f"Bearer {self.mock_key}")
            self.assertEqual(captured_request["headers"]["Content-Type"], "application/json")

            # Check Payload
            payload = captured_request["json"]
            self.assertEqual(payload["model"], "meta/llama-3.1-8b-instruct")

            # Check system prompt
            messages = payload["messages"]
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("You are SOUSCHEF, a friendly real-time voice cooking assistant", messages[0]["content"])

            # Check conversation history & no duplicate user input
            self.assertEqual(messages[1], {"role": "user", "content": "Hi"})
            self.assertEqual(messages[2], {"role": "assistant", "content": "Hello!"})
            self.assertEqual(messages[3], {"role": "user", "content": "What can I cook?"})
            self.assertEqual(len(messages), 4)

    # 4. Duplicate input protection
    async def test_latest_input_not_duplicated_when_already_in_history(self):
        captured_request = {}

        async def mock_post(url, headers=None, json=None):
            captured_request["json"] = json
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"role": "assistant", "content": "Sure!"}}]
            }
            return mock_resp

        service = NvidiaLLMService(api_key=self.mock_key)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "Tell me a recipe"}
            ]
            await service.generate_response("Tell me a recipe", history)

            messages = captured_request["json"]["messages"]
            user_messages = [m for m in messages if m["role"] == "user"]
            self.assertEqual(len(user_messages), 2)
            self.assertEqual(user_messages[-1]["content"], "Tell me a recipe")

    # 5. Invalid response format handling
    async def test_invalid_nvidia_response_format(self):
        async def mock_post(url, headers=None, json=None):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"invalid": "payload"}
            return mock_resp

        service = NvidiaLLMService(api_key=self.mock_key)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with self.assertRaises(LLMUnavailableError) as ctx:
                await service.generate_response("Hello", [])
            self.assertIn("missing choices", str(ctx.exception))

    # 6. HTTP Error & Timeout Handling
    async def test_http_status_error_handling(self):
        async def mock_post(url, headers=None, json=None):
            req = httpx.Request("POST", url)
            resp = httpx.Response(status_code=401, json={"error": "Unauthorized"}, request=req)
            raise httpx.HTTPStatusError("Unauthorized", request=req, response=resp)

        service = NvidiaLLMService(api_key=self.mock_key)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with self.assertRaises(LLMUnavailableError) as ctx:
                await service.generate_response("Hello", [])
            self.assertIn("error status 401", str(ctx.exception))
            self.assertNotIn(self.mock_key, str(ctx.exception))

    async def test_timeout_handling(self):
        async def mock_post(url, headers=None, json=None):
            req = httpx.Request("POST", url)
            raise httpx.TimeoutException("Connection timed out", request=req)

        service = NvidiaLLMService(api_key=self.mock_key)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with self.assertRaises(LLMUnavailableError) as ctx:
                await service.generate_response("Hello", [])
            self.assertIn("timed out", str(ctx.exception))

    # 7. Integration with ConversationEngine: Current response reaches TTS
    async def test_conversation_engine_nvidia_success(self):
        async def mock_post(url, headers=None, json=None):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"role": "assistant", "content": "Boil pasta in salted water."}}]
            }
            return mock_resp

        tts = MockTTS()
        nvidia_llm = NvidiaLLMService(api_key=self.mock_key)

        engine = ConversationEngine(tts=tts, llm=nvidia_llm, session_id="test_nvidia_session")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            turn = await engine.handle_user_input("How do I cook pasta?")
            self.assertIsNotNone(turn)
            self.assertEqual(turn.response_text, "Boil pasta in salted water.")
            self.assertEqual(tts.spoken_texts, ["Boil pasta in salted water."])
            self.assertEqual(engine.state, ConversationState.IDLE)

    # 8. Integration with ConversationEngine: Stale response discarded on interruption
    async def test_conversation_engine_nvidia_interruption_discards_stale_response(self):
        async def mock_slow_post(url, headers=None, json=None):
            req_json = json or {}
            msgs = req_json.get("messages", [])
            user_text = msgs[-1]["content"] if msgs else ""
            if "long recipe" in user_text:
                await asyncio.sleep(0.2)
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value={
                        "choices": [{"message": {"role": "assistant", "content": "Long recipe response Turn A"}}]
                    })
                )
            return MagicMock(
                raise_for_status=MagicMock(),
                json=MagicMock(return_value={
                    "choices": [{"message": {"role": "assistant", "content": "Fast response Turn B"}}]
                })
            )

        tts = MockTTS()
        nvidia_llm = NvidiaLLMService(api_key=self.mock_key)

        engine = ConversationEngine(tts=tts, llm=nvidia_llm, session_id="test_nvidia_interruption_session")

        with patch("httpx.AsyncClient.post", side_effect=mock_slow_post):
            task_a = asyncio.create_task(engine.handle_user_input("Tell me a long recipe"))
            await asyncio.sleep(0.05)

            # Interrupt Turn A with new input (Turn B)
            await engine.interrupt()
            task_b = asyncio.create_task(engine.handle_user_input("What is salt?"))

            await asyncio.gather(task_a, task_b)

            # Only Turn B response reaches TTS
            self.assertIn("Fast response Turn B", tts.spoken_texts)
            self.assertNotIn("Long recipe response Turn A", tts.spoken_texts)


if __name__ == "__main__":
    unittest.main()
