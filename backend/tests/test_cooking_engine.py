import asyncio

import pytest

from app.conversation.engine import ConversationEngine
from app.conversation.interfaces import LLMInterface, TTSInterface
from app.conversation.llm_protocol import parse_llm_response
from app.conversation.llm_protocol import parse_llm_response
from app.tools.cooking_tool_runner import CookingToolRunner


RECIPE = {
    "id": "simple-pasta",
    "name": "Simple Pasta",
    "servings": 2,
    "ingredients": [{"id": "water", "name": "Water", "quantity": 1, "unit": "pot"}],
    "steps": [
        {
            "id": "boil-water",
            "order": 1,
            "instruction": "Bring the water to a boil.",
            "ingredient_ids": ["water"],
        },
        {"id": "serve", "order": 2, "instruction": "Serve the pasta."},
    ],
}


def test_truncated_protocol_json_never_becomes_spoken_raw_json() -> None:
    raw = '{"speech":"What sauce would you like?","tool_calls":[]'
    decision = parse_llm_response(raw)
    assert decision.speech == "What sauce would you like?"
    assert decision.tool_calls == []


@pytest.mark.asyncio
async def test_recipe_to_completed_cooking_session() -> None:
    runner = CookingToolRunner("conversation-a")
    try:
        created = await runner.execute_tool("create_recipe", {"recipe": RECIPE})
        assert created["ok"] is True
        started = await runner.execute_tool("start_cooking", {"recipe_id": "simple-pasta"})
        assert started["data"]["current_step"]["id"] == "boil-water"

        next_step = await runner.execute_tool("complete_step", {})
        assert next_step["data"]["current_step"]["id"] == "serve"
        completed = await runner.execute_tool("complete_step", {})
        assert completed["data"]["session"]["status"] == "completed"
        assert completed["data"]["current_step"] is None
    finally:
        await runner.close()


@pytest.mark.asyncio
async def test_sessions_are_isolated_between_runners() -> None:
    first = CookingToolRunner("conversation-a")
    second = CookingToolRunner("conversation-b")
    try:
        for runner in (first, second):
            await runner.execute_tool("create_recipe", {"recipe": RECIPE})
            await runner.execute_tool("start_cooking", {"recipe_id": "simple-pasta"})
        await first.execute_tool("complete_step", {})
        first_state = await first.execute_tool("get_cooking_state", {})
        second_state = await second.execute_tool("get_cooking_state", {})
        assert first_state["data"]["current_step"]["id"] == "serve"
        assert second_state["data"]["current_step"]["id"] == "boil-water"
    finally:
        await first.close()
        await second.close()


@pytest.mark.asyncio
async def test_timer_completes_without_blocking_and_leaves_session_state() -> None:
    runner = CookingToolRunner("conversation-a")
    try:
        await runner.execute_tool("create_recipe", {"recipe": RECIPE})
        await runner.execute_tool("start_cooking", {"recipe_id": "simple-pasta"})
        started = await runner.execute_tool(
            "start_timer", {"duration_seconds": 0.02, "label": "Test timer", "action_id": "action-1"}
        )
        timer_id = started["data"]["id"]
        assert started["data"]["status"] == "running"
        await asyncio.sleep(0.04)
        finished = await runner.execute_tool("get_timer_status", {"timer_id": timer_id})
        state = await runner.execute_tool("get_cooking_state", {})
        assert finished["data"]["status"] == "completed"
        assert timer_id not in state["data"]["session"]["active_timer_ids"]
    finally:
        await runner.close()


@pytest.mark.asyncio
async def test_invalid_recipe_and_unknown_tool_return_error_envelopes() -> None:
    runner = CookingToolRunner("conversation-a")
    try:
        invalid = await runner.execute_tool(
            "create_recipe",
            {"recipe": {**RECIPE, "steps": [{**RECIPE["steps"][0], "ingredient_ids": ["missing"]}]}},
        )
        unknown = await runner.execute_tool("run_shell_command", {"command": "anything"})
        assert invalid["ok"] is False
        assert invalid["error"]["code"] == "INVALID_TOOL_ARGUMENTS"
        assert unknown["ok"] is False
        assert unknown["error"]["code"] == "UNKNOWN_TOOL"
    finally:
        await runner.close()


@pytest.mark.asyncio
async def test_create_recipe_accepts_provider_flattened_arguments() -> None:
    runner = CookingToolRunner("conversation-a")
    try:
        created = await runner.execute_tool("create_recipe", RECIPE)
        assert created["ok"] is True
        assert created["data"]["id"] == "simple-pasta"
    finally:
        await runner.close()


class QueueLLM(LLMInterface):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.inputs: list[str] = []

    async def generate_response(self, user_input: str, conversation_history: list[dict[str, str]]) -> str:
        self.inputs.append(user_input)
        return self.responses.pop(0)


class CapturingTTS(TTSInterface):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def speak(self, text: str) -> None:
        self.spoken.append(text)

    async def stop(self) -> None:
        pass


@pytest.mark.asyncio
async def test_conversation_engine_executes_llm_tools_then_speaks_result() -> None:
    import json

    llm = QueueLLM(
        [
            json.dumps(
                {
                    "speech": "",
                    "tool_calls": [
                        {"name": "create_recipe", "arguments": {"recipe": RECIPE}},
                        {"name": "start_cooking", "arguments": {"recipe_id": "simple-pasta"}},
                    ],
                }
            ),
            json.dumps({"speech": "Let's begin. Bring the water to a boil.", "tool_calls": []}),
        ]
    )
    tts = CapturingTTS()
    runner = CookingToolRunner("voice-session")
    engine = ConversationEngine(tts=tts, llm=llm, tool_runner=runner, session_id="voice-session")
    try:
        turn = await engine.handle_user_input("Make pasta and start cooking")
        assert turn.response_text == "Let's begin. Bring the water to a boil."
        assert tts.spoken == ["Let's begin. Bring the water to a boil."]
        assert runner.sessions.current_step("voice-session").id == "boil-water"
        assert llm.inputs[1].startswith("Tool results (authoritative JSON):")
    finally:
        await runner.close()


@pytest.mark.asyncio
async def test_skip_and_cancel_require_explicit_confirmation() -> None:
    runner = CookingToolRunner("conversation-a")
    try:
        await runner.execute_tool("create_recipe", {"recipe": RECIPE})
        await runner.execute_tool("start_cooking", {"recipe_id": "simple-pasta"})
        rejected = await runner.execute_tool("skip_step", {})
        accepted = await runner.execute_tool("skip_step", {"confirmed": True})
        assert rejected["ok"] is False
        assert "confirmation" in rejected["error"]["message"]
        assert accepted["ok"] is True
        assert accepted["data"]["current_step"]["id"] == "serve"
    finally:
        await runner.close()


def test_malformed_protocol_never_exposes_tools_as_speech() -> None:
    recoverable = parse_llm_response(
        '{"speech":"What sauce would you like?","tool_calls":[{"name":"create_recipe"}'
    )
    unrecoverable = parse_llm_response('{"tool_calls":[{"name":"create_recipe"}')
    plain = parse_llm_response("A normal plain-text response.")

    assert recoverable.speech == "What sauce would you like?"
    assert "tool_calls" not in recoverable.speech
    assert "tool_calls" not in unrecoverable.speech
    assert plain.speech == "A normal plain-text response."
