import pytest
import asyncio
import sys
from unittest.mock import AsyncMock, patch, MagicMock

sys.modules['whisper'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

from app.conversation.engine import ConversationEngine
from app.conversation.state import ConversationState
from app.services.stt_service import STTService
from app.services.voice_orchestrator import VoiceOrchestrator
from app.services.wake_word_listener import WakeWordListener

@pytest.fixture
def mock_tts():
    tts = AsyncMock()
    return tts

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate_response.return_value = "This is a test response."
    return llm

@pytest.fixture
def mock_stt():
    stt = AsyncMock(spec=STTService)
    # Don't mock the methods that get explicitly set
    return stt

@pytest.fixture
def engine(mock_tts, mock_llm, mock_stt):
    eng = ConversationEngine(
        tts=mock_tts,
        llm=mock_llm,
        stt=mock_stt
    )
    return eng

@pytest.fixture
def orchestrator(engine, mock_stt, mock_tts):
    orch = VoiceOrchestrator(
        engine=engine,
        stt=mock_stt,
        tts=mock_tts
    )
    orch.wake_listener = AsyncMock(spec=WakeWordListener)
    orch.active_listening_timeout = 0.1
    return orch

@pytest.mark.asyncio
async def test_wake_word_interrupts_active_tts(orchestrator, engine, mock_tts):
    """
    1. Wake-word interrupts active TTS.
    """
    # Create a turn that hangs in SPEAKING state
    async def slow_speak(*args, **kwargs):
        await asyncio.sleep(0.5)

    mock_tts.speak.side_effect = slow_speak
    task = asyncio.create_task(engine.handle_user_input("initial turn"))

    # Wait for it to reach SPEAKING
    await asyncio.sleep(0.05)
    assert engine.state == ConversationState.SPEAKING

    # Process "wait!"
    await orchestrator.process_wake_command("wait!")

    # TTS should be stopped
    mock_tts.stop.assert_awaited_once()
    # Engine state will be IDLE after processing finishes
    assert engine.state == ConversationState.IDLE
    assert engine.current_turn.user_input == "wait!"

    task.cancel()

@pytest.mark.asyncio
async def test_stale_turns_cannot_speak_after_interruption(engine, mock_tts, mock_llm):
    """
    2. Old turn finishes after interruption -> old response is discarded.
    """
    async def slow_llm(*args, **kwargs):
        await asyncio.sleep(0.2)
        return "Slow response"

    mock_llm.generate_response.side_effect = slow_llm

    task_1 = asyncio.create_task(engine.handle_user_input("Turn 1"))
    await asyncio.sleep(0.05)

    old_turn = engine.current_turn

    # Interruption happens
    await engine.on_user_speech_started()
    assert old_turn.is_cancelled

    await task_1

    # The slow response should NOT have triggered speak
    mock_tts.speak.assert_not_called()

@pytest.mark.asyncio
async def test_wake_text_parsing(orchestrator):
    """
    3. Wake text parsing ("Sofi, wait!" -> "wait!").
    5. "Sofi, wait!" -> "wait!"
    """
    cleaned = orchestrator.wake_word_service.strip_wake_word("Sofi, wait!")
    assert cleaned == "wait!"

@pytest.mark.asyncio
async def test_sophie_variant_handling(orchestrator):
    """
    4. "Sophie" variant handling.
    6. "Sophie, wait!" -> "wait!"
    """
    cleaned = orchestrator.wake_word_service.strip_wake_word("Sophie, wait!")
    assert cleaned == "wait!"

@pytest.mark.asyncio
async def test_sophia_variant_handling(orchestrator):
    """
    7. "Sophia" variant handling.
    """
    cleaned = orchestrator.wake_word_service.strip_wake_word("Sophia, wait!")
    assert cleaned == "wait!"

@pytest.mark.asyncio
async def test_speaker_echo_ignored_during_speaking(orchestrator, engine, mock_tts):
    """
    6. Speaker echo ignored during `SPEAKING`.
    """
    async def slow_speak(*args, **kwargs):
        await asyncio.sleep(0.5)

    mock_tts.speak.side_effect = slow_speak
    task = asyncio.create_task(engine.handle_user_input("fake"))
    await asyncio.sleep(0.05)

    assert engine.state == ConversationState.SPEAKING

    # Send a garbage transcript through _handle_transcript
    turn = await orchestrator._handle_transcript("You are transcribing a cooking assistant conversation.")

    assert turn is None
    assert engine.current_turn.user_input == "fake"

    task.cancel()

@pytest.mark.asyncio
async def test_wake_listener_concurrency(orchestrator, engine, mock_llm):
    """
    4. Wake listener remains alive while LLM/TTS processing is still running.
    """
    async def slow_llm(*args, **kwargs):
        await asyncio.sleep(0.5)
        return "Slow"

    mock_llm.generate_response.side_effect = slow_llm

    task = asyncio.create_task(engine.handle_user_input("Turn A"))
    await asyncio.sleep(0.05)

    assert engine.state == ConversationState.THINKING

    # Process "wait!" in the background
    orchestrator._start_background_processing("wait!")

    await asyncio.sleep(0.1)

    # The old turn should be cancelled, the new turn should be "wait!"
    assert engine.current_turn.user_input == "wait!"
    assert engine.state == ConversationState.THINKING

    assert not orchestrator.wake_listener.stop.called

    task.cancel()
    for t in list(orchestrator._background_tasks):
        t.cancel()

@pytest.mark.asyncio
async def test_local_cooking_command_tts_is_interruptible(orchestrator, engine, mock_tts):
    """
    Regression test: Local cooking command creates an interruptible turn in SPEAKING state,
    and 'Sofi, wait!' stops local TTS and becomes the new authoritative turn.
    """
    mock_runner = AsyncMock()
    mock_runner.execute_tool.return_value = {
        "ok": True,
        "tool": "get_current_step",
        "data": {"instruction": "Simmer sauce on low heat for 10 minutes"},
    }
    engine.tool_runner = mock_runner

    # Simulate slow TTS playback
    async def slow_speak(*args, **kwargs):
        await asyncio.sleep(0.5)

    mock_tts.speak.side_effect = slow_speak

    # Launch local cooking command
    local_task = asyncio.create_task(
        orchestrator.process_user_utterance("current step")
    )

    # Allow it to process tool locally and reach SPEAKING state
    await asyncio.sleep(0.05)
    assert engine.state == ConversationState.SPEAKING
    assert engine.current_turn is not None
    assert "Simmer sauce" in (engine.current_turn.response_text or "")

    # Interruption with "Sofi, wait!"
    await orchestrator.process_wake_command("wait!")

    # Local TTS must be stopped
    mock_tts.stop.assert_awaited()

    # "wait!" becomes the new authoritative turn
    assert engine.current_turn.user_input == "wait!"
    assert engine.state == ConversationState.IDLE

    local_task.cancel()
    try:
        await local_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_stale_local_cooking_feedback_cannot_speak_after_newer_turn(orchestrator, engine, mock_tts):
    """
    Regression test: Stale local cooking command feedback cannot speak
    after an interruption and a newer turn has become authoritative.
    """
    tool_started = asyncio.Event()
    tool_can_finish = asyncio.Event()

    mock_runner = AsyncMock()
    async def slow_execute(name, args):
        tool_started.set()
        await tool_can_finish.wait()
        return {
            "ok": True,
            "tool": name,
            "data": {"instruction": "Add minced garlic to pan"},
        }

    mock_runner.execute_tool.side_effect = slow_execute
    engine.tool_runner = mock_runner

    # Start local command A
    task_a = asyncio.create_task(
        orchestrator._try_local_cooking_command("what is next")
    )
    await tool_started.wait()

    # Interruption occurs and Turn B starts
    await orchestrator.process_wake_command("wait!")
    assert engine.current_turn.user_input == "wait!"
    turn_b_id = engine.current_turn_id

    # Allow local tool A to finish
    tool_can_finish.set()
    turn_a = await task_a

    # Turn A was discarded as stale
    assert turn_a is None

    # Stale local feedback from A must not have spoken
    for call in mock_tts.speak.call_args_list:
        spoken_text = call[0][0]
        assert "Add minced garlic" not in spoken_text

    assert engine.current_turn_id == turn_b_id


@pytest.mark.asyncio
async def test_chicken_pasta_physical_interruption_flow(orchestrator, engine, mock_tts, mock_llm):
    """
    Simulates the exact physical demo flow:
    1. User: "Let's cook chicken pasta"
    2. Rime TTS begins speaking Chicken Pasta response
    3. User barge-in: "Sofi, wait!"
    4. Wake word detected, active turn cancelled, Rime TTS stopped
    5. "wait!" processed as new authoritative turn
    6. Old Chicken Pasta response does not resume
    """
    mock_llm.generate_response.side_effect = lambda query, history: (
        "Here is the recipe for chicken pasta. Step one: boil water."
        if "pasta" in query
        else "I am paused and waiting."
    )

    speaking_event = asyncio.Event()
    tts_stopped = asyncio.Event()

    async def slow_speak(text, *args, **kwargs):
        if "pasta" in text:
            speaking_event.set()
            try:
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                raise
        else:
            await asyncio.sleep(0.01)

    async def mock_stop():
        tts_stopped.set()

    mock_tts.speak.side_effect = slow_speak
    mock_tts.stop.side_effect = mock_stop

    # 1. Start "Let's cook chicken pasta"
    pasta_task = asyncio.create_task(
        orchestrator.process_user_utterance("Let's cook chicken pasta")
    )
    await speaking_event.wait()

    # Rime is currently speaking
    assert engine.state == ConversationState.SPEAKING
    pasta_turn = engine.current_turn
    assert "chicken pasta" in pasta_turn.user_input

    # 2. While speaking, user interrupts with "Sofi, wait!"
    cleaned = orchestrator.wake_word_service.strip_wake_word("Sofi, wait!")
    assert cleaned == "wait!"

    # Process wake command
    wait_turn = await orchestrator.process_wake_command(cleaned)

    # 3. Verify Rime stopped
    assert tts_stopped.is_set()
    assert pasta_turn.is_cancelled

    # 4. "wait!" processed as new authoritative turn
    assert engine.current_turn.user_input == "wait!"
    assert engine.current_turn.response_text == "I am paused and waiting."

    # 5. Old Chicken Pasta turn does not resume
    await pasta_task
    assert engine.current_turn.user_input == "wait!"


@pytest.mark.asyncio
async def test_cooking_rollback_semantics_and_step_commands(orchestrator, engine, mock_tts):
    """
    Verify active cooking session tools:
    - Starting a recipe routes through authoritative CookingRecipeToolRunner
    - Advancing steps moves current step forward
    - 'Sofi, wait!' does NOT rollback step
    - 'what is the current step?' returns current step
    - 'repeat the step' returns current step
    - 'go back' rolls back step
    - 'start a timer for 30 seconds' starts the timer tool
    """
    from app.services.conversation_service import CookingRecipeToolRunner
    from app.services.llm_service import LocalTestLLM

    tool_runner = CookingRecipeToolRunner("test_rollback_session")
    engine.tool_runner = tool_runner
    engine.llm = LocalTestLLM()

    # 1. Start chicken pasta recipe
    turn = await orchestrator.process_user_utterance("Let's cook chicken pasta")
    assert engine.context.active_recipe == "Chicken Pasta"
    state = await tool_runner.execute_tool("get_current_step", {})
    assert "Bring a pot" in state["data"]["instruction"]

    # 2. Advance to next step
    next_turn = await orchestrator.process_user_utterance("finished this step")
    assert "Cook the pasta" in next_turn.response_text
    state = await tool_runner.execute_tool("get_current_step", {})
    assert "Cook the pasta" in state["data"]["instruction"]

    # 3. Interruption "Sofi, wait!" must NOT roll back step
    await orchestrator.process_wake_command("wait!")
    state = await tool_runner.execute_tool("get_current_step", {})
    assert "Cook the pasta" in state["data"]["instruction"]

    # 4. "what is the current step?"
    cur_turn = await orchestrator.process_user_utterance("what is the current step?")
    assert "Cook the pasta" in cur_turn.response_text

    # 5. "repeat the step"
    rep_turn = await orchestrator.process_user_utterance("repeat the step")
    assert "Cook the pasta" in rep_turn.response_text

    # 6. "go back" MUST call previous_step and rollback to step 0
    back_turn = await orchestrator.process_user_utterance("go back")
    assert "Bring a pot" in back_turn.response_text
    state = await tool_runner.execute_tool("get_current_step", {})
    assert "Bring a pot" in state["data"]["instruction"]

    # 7. "start a timer for 30 seconds"
    timer_turn = await orchestrator.process_user_utterance("start a timer for 30 seconds")
    assert "30 seconds" in timer_turn.response_text

    await tool_runner.close()
