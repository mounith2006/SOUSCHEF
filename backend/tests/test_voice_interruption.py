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
