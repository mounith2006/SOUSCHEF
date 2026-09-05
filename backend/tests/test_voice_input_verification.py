import unittest
import asyncio
from typing import List
from app.conversation.engine import ConversationEngine
from app.conversation.state import ConversationState
from app.conversation.turn import Turn
from app.conversation.interfaces import TTSInterface
from app.services.voice_orchestrator import VoiceOrchestrator
from app.services.stt_service import DefaultSTTService
from app.services.rime_tts_service import RimeTTSService
from app.services.llm_service import LocalTestLLM

class DummyMockSTT(DefaultSTTService):
    """Mock STT service for testing real voice orchestrator interaction without mic hardware."""

    def __init__(self):
        super().__init__()
        self.transcription_queue: List[str] = []

    def queue_transcription(self, text: str):
        self.transcription_queue.append(text)

    async def listen_and_transcribe(self) -> str:
        if self.transcription_queue:
            text = self.transcription_queue.pop(0)
            clean_text = text.strip() if text else ""
            if clean_text:
                await self.notify_transcript(clean_text)
            return clean_text
        return ""


class SlowMockTTS(TTSInterface):
    """TTS with playback delay to test interruption while speaking."""

    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.spoken_texts = []
        self.stop_count = 0

    async def speak(self, text: str) -> None:
        self.spoken_texts.append(text)
        await asyncio.sleep(self.delay)

    async def stop(self) -> None:
        self.stop_count += 1


class TestVoiceInputVerification(unittest.IsolatedAsyncioTestCase):
    """Suite verifying input path purity, single delivery, and turn management."""

    async def test_A_demo_voice_path_does_not_use_hardcoded_user_input(self):
        """Verify VoiceOrchestrator does not generate turns without STT input."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = RimeTTSService()
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        turn = await orchestrator.listen_cycle()
        assert turn is None
        assert engine.current_turn is None
        assert engine.state == ConversationState.IDLE

    async def test_B_transcript_delivered_exactly_once(self):
        """Verify a single utterance delivers transcript exactly once and creates one turn."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = RimeTTSService()
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        stt.queue_transcription("Tell me the cooking time for two hundred grams of spaghetti.")
        turn = await orchestrator.listen_cycle()

        assert turn is not None
        assert turn.user_input == "Tell me the cooking time for two hundred grams of spaghetti."
        assert engine.context.get_messages() != []
        assert len(engine.context.get_messages()) >= 2  # user + assistant

    async def test_C_empty_transcript_does_not_start_turn(self):
        """Verify empty transcripts or silence yield no turn, no LLM call, and no state change."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = RimeTTSService()
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        stt.queue_transcription("   ")
        turn = await orchestrator.listen_cycle()

        assert turn is None
        assert engine.current_turn is None
        assert engine.state == ConversationState.IDLE
        assert engine.context.get_messages() == []

    async def test_D_speech_start_event_does_not_create_turn(self):
        """Verify speech-start barge-in event does not create a turn on its own."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = RimeTTSService()
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        await stt.notify_speech_started()

        assert engine.current_turn is None
        assert engine.state == ConversationState.IDLE

    async def test_E_actual_transcript_creates_exactly_one_turn(self):
        """Verify actual STT transcript creates exactly one turn matching input."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = RimeTTSService()
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        input_text = "How much salt should I add?"
        stt.queue_transcription(input_text)
        turn = await orchestrator.listen_cycle()

        assert turn is not None
        assert turn.user_input == input_text
        assert turn.turn_id == engine.current_turn_id

    async def test_F_interruption_cancels_current_turn(self):
        """Verify speech start during active turn interrupts and cancels previous turn."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = SlowMockTTS(delay=0.3)
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        stt.queue_transcription("How long should I cook pasta?")
        turn1_task = asyncio.create_task(orchestrator.listen_cycle())
        await asyncio.sleep(0.05)

        # User interrupts while TTS is speaking
        await stt.notify_speech_started()
        turn1 = await turn1_task

        assert turn1.is_cancelled is True
        assert tts.stop_count > 0

    async def test_G_stale_response_cannot_be_spoken(self):
        """Verify cancelled turn's response is marked cancelled and discarded."""
        stt = DummyMockSTT()
        llm = LocalTestLLM()
        tts = SlowMockTTS(delay=0.3)
        engine = ConversationEngine(tts=tts, llm=llm, stt=stt)
        orchestrator = VoiceOrchestrator(engine=engine, stt=stt, tts=tts, display_mode=False)

        stt.queue_transcription("First question")
        task1 = asyncio.create_task(orchestrator.listen_cycle())
        await asyncio.sleep(0.05)

        # Cancel turn 1 manually while running
        await engine.cancel_current_turn("Interrupted")
        turn1 = await task1

        assert turn1.is_cancelled is True
        assert turn1.state == ConversationState.CANCELLED
