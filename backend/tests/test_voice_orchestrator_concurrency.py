import pytest
import asyncio
import threading
import sys
from unittest.mock import AsyncMock, MagicMock

# Bypass PyTorch DLL crash on this environment during collection
sys.modules['whisper'] = MagicMock()
sys.modules['sounddevice'] = MagicMock() # Mock sounddevice too just in case

from app.services.voice_orchestrator import VoiceOrchestrator
from app.conversation.state import ConversationState
from app.conversation.turn import Turn
from app.conversation.engine import ConversationEngine
from app.services.stt_service import STTService
from app.conversation.interfaces import LLMInterface, TTSInterface, ToolInterface
from app.conversation.context import ConversationContext


# TEST 1: Async VAD callback from worker thread
@pytest.mark.asyncio
async def test_async_vad_callback_from_worker_thread():
    class DummyModel:
        pass

    class STTServiceNoWhisper(STTService):
        def __init__(self):
            self.model = DummyModel()
            self.language = "en"
            self._on_speech_started = None
            self._on_transcript = None

    stt = STTServiceNoWhisper()
    callback_event = asyncio.Event()

    async def my_async_callback():
        callback_event.set()

    stt.set_on_speech_started(my_async_callback)

    assert hasattr(stt, "_callback_loop")
    assert stt._callback_loop is asyncio.get_running_loop()

    def worker_thread_func():
        callback_result = stt._on_speech_started()
        import inspect
        if inspect.isawaitable(callback_result):
            loop = getattr(stt, "_callback_loop", None)
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(callback_result, loop)

    thread = threading.Thread(target=worker_thread_func)
    thread.start()
    thread.join()

    await asyncio.wait_for(callback_event.wait(), timeout=2.0)
    assert callback_event.is_set()


# TEST 2: Turn A running while Turn B interrupts + Regression
@pytest.mark.asyncio
async def test_turn_a_running_while_turn_b_interrupts():
    mock_llm = AsyncMock(spec=LLMInterface)
    mock_tts = AsyncMock(spec=TTSInterface)

    engine = ConversationEngine(
        tts=mock_tts,
        llm=mock_llm,
        context=ConversationContext()
    )

    stt_mock = MagicMock()
    orchestrator = VoiceOrchestrator(
        engine=engine,
        stt=stt_mock,
        tts=mock_tts,
        display_mode=False
    )

    turn_a_llm_start = asyncio.Event()
    turn_a_llm_finish = asyncio.Event()
    
    turn_b_llm_start = asyncio.Event()
    turn_b_llm_finish = asyncio.Event()

    async def delayed_llm(user_input, history):
        if "start the timer" in user_input:
            turn_a_llm_start.set()
            await turn_a_llm_finish.wait()
            return "Timer started"
        elif "wait!" in user_input:
            turn_b_llm_start.set()
            await turn_b_llm_finish.wait()
            return "Okay, waiting"
        return "Default"

    mock_llm.generate_response = AsyncMock(side_effect=delayed_llm)

    # 1. User says "Sofi, start the timer"
    orchestrator._start_background_processing("start the timer")

    await asyncio.wait_for(turn_a_llm_start.wait(), timeout=1.0)

    assert engine.state == ConversationState.THINKING
    turn_a_id = engine.current_turn_id

    # 2. While active, user says "Sofi, wait!"
    # Wake word detected during active turn interrupts it
    await engine.on_user_speech_started()
    orchestrator._start_background_processing("wait!")

    # Wait for Turn B to reach LLM
    await asyncio.wait_for(turn_b_llm_start.wait(), timeout=1.0)

    # Engine state is THINKING for the new turn
    assert engine.state == ConversationState.THINKING
    turn_b_id = engine.current_turn_id
    assert turn_a_id != turn_b_id

    # Now let Turn A finish
    turn_a_llm_finish.set()

    # Yield to let Turn A background task complete
    await asyncio.sleep(0.1)

    # 3. Turn A stale result shouldn't emit TTS
    mock_tts.speak.assert_not_called()
    
    # Let Turn B finish
    turn_b_llm_finish.set()
    await asyncio.sleep(0.1)
    
    # Turn B should have called TTS
    mock_tts.speak.assert_called_once_with("Okay, waiting")

    # Clean up
    await orchestrator.stop_voice_loop()


# TEST 3 & 4: Turn A completes late, stale Turn A cannot invoke TTS
@pytest.mark.asyncio
async def test_late_completion_and_stale_tts_prevention():
    mock_llm = AsyncMock(spec=LLMInterface)
    mock_tts = AsyncMock(spec=TTSInterface)

    engine = ConversationEngine(
        tts=mock_tts,
        llm=mock_llm,
        context=ConversationContext()
    )

    turn_a_llm_start = asyncio.Event()
    turn_a_llm_finish = asyncio.Event()

    async def delayed_llm_generate(user_input, history):
        if user_input == "Turn A":
            turn_a_llm_start.set()
            await turn_a_llm_finish.wait()
            return "Response A"
        return "Response B"

    mock_llm.generate_response = AsyncMock(side_effect=delayed_llm_generate)

    task_a = asyncio.create_task(engine.handle_user_input("Turn A"))

    await asyncio.wait_for(turn_a_llm_start.wait(), timeout=1.0)

    assert engine.state == ConversationState.THINKING
    turn_a_id = engine.current_turn_id

    await engine.on_user_speech_started()
    assert engine.state == ConversationState.INTERRUPTED

    task_b = asyncio.create_task(engine.handle_user_input("Turn B"))

    turn_b = await task_b
    assert turn_b.response_text == "Response B"
    assert engine.current_turn_id == turn_b.turn_id

    mock_tts.speak.assert_called_once_with("Response B")
    mock_tts.speak.reset_mock()

    turn_a_llm_finish.set()
    turn_a = await task_a

    assert turn_a.is_cancelled or not engine.is_current_turn(turn_a.turn_id)

    mock_tts.speak.assert_not_called()
    assert engine.current_turn_id == turn_b.turn_id


# TEST 5: Multiple rapid interruptions
@pytest.mark.asyncio
async def test_multiple_rapid_interruptions():
    mock_llm = AsyncMock(spec=LLMInterface)
    mock_tts = AsyncMock(spec=TTSInterface)
    mock_llm.generate_response.return_value = "Response"

    engine = ConversationEngine(
        tts=mock_tts,
        llm=mock_llm,
        context=ConversationContext()
    )

    orchestrator = VoiceOrchestrator(
        engine=engine,
        stt=AsyncMock(),
        tts=mock_tts,
        display_mode=False
    )

    await engine.on_user_speech_started()
    orchestrator._start_background_processing("start the timer")
    await engine.on_user_speech_started()
    orchestrator._start_background_processing("wait!")
    await engine.on_user_speech_started()
    orchestrator._start_background_processing("actually stop it")
    await engine.on_user_speech_started()
    orchestrator._start_background_processing("never mind")

    await asyncio.sleep(0.2)

    await orchestrator.stop_voice_loop()

    assert len(orchestrator._background_tasks) == 0


# TEST 6: Background task cleanup
@pytest.mark.asyncio
async def test_background_task_cleanup():
    engine = AsyncMock(spec=ConversationEngine)
    orchestrator = VoiceOrchestrator(
        engine=engine,
        stt=AsyncMock(),
        tts=AsyncMock(),
        display_mode=False
    )

    task_started = asyncio.Event()

    async def slow_transcript(text):
        task_started.set()
        await asyncio.sleep(5.0)

    orchestrator._handle_transcript = AsyncMock(side_effect=slow_transcript)

    orchestrator._start_background_processing("cmd 1")
    orchestrator._start_background_processing("cmd 2")
    orchestrator._start_background_processing("cmd 3")

    assert len(orchestrator._background_tasks) == 3

    await asyncio.wait_for(task_started.wait(), timeout=1.0)

    await orchestrator.stop_voice_loop()

    assert len(orchestrator._background_tasks) == 0
