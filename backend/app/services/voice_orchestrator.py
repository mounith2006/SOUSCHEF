import asyncio
import sys
import logging
from typing import Optional
from ..conversation.engine import ConversationEngine
from ..conversation.state import ConversationState
from ..conversation.turn import Turn
from .stt_service import DefaultSTTService
from .rime_tts_service import RimeTTSService
from .conversation_service import get_conversation_engine

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("souschef.orchestrator")

class VoiceOrchestrator:
    """
    Thin Voice Orchestrator connecting STT, ConversationEngine, and Rime TTS.
    Does NOT own conversation state; ConversationEngine is the single source of truth.
    """

    def __init__(
        self,
        engine: Optional[ConversationEngine] = None,
        stt: Optional[DefaultSTTService] = None,
        tts: Optional[RimeTTSService] = None,
        session_id: str = "default_session",
        display_mode: bool = False,
    ):
        self.session_id = session_id
        self.display_mode = display_mode
        self.tts = tts or RimeTTSService()
        self.stt = stt or DefaultSTTService()
        self.engine = engine or get_conversation_engine(
            session_id=session_id,
            tts=self.tts,
            stt=self.stt,
        )

        # Wire up STT callbacks
        self.stt.set_on_speech_started(self._handle_speech_started)
        self.stt.set_on_transcript(self._handle_transcript)

    def _safe_print(self, text: str) -> None:
        """Helper for printing text cleanly across all OS terminal encodings."""
        try:
            print(text, flush=True)
        except UnicodeEncodeError:
            # Fallback for environments with strict legacy encoding
            safe_text = (
                text.replace("🎤 LISTENING...", "LISTENING...")
                .replace("🎤 YOU SAID:", "YOU SAID:")
                .replace("🤖 SOUSCHEF:", "SOUSCHEF:")
                .replace("🔊 SPEAKING...", "SPEAKING...")
                .replace("⚡ BARGE-IN DETECTED", "BARGE-IN DETECTED")
                .replace("⚡ STOPPING CURRENT RESPONSE", "STOPPING CURRENT RESPONSE")
            )
            print(safe_text, flush=True)

    async def _handle_speech_started(self) -> None:
        """Invoked immediately when STT/VAD detects user speech barge-in."""
        logger.info("[VOICE ORCHESTRATOR] Speech onset detected -> triggering engine interruption")
        if self.engine.state in (ConversationState.SPEAKING, ConversationState.THINKING, ConversationState.TOOL_RUNNING):
            if self.display_mode:
                self._safe_print("⚡ BARGE-IN DETECTED\n⚡ STOPPING CURRENT RESPONSE\n")
        await self.engine.on_user_speech_started()

    async def _handle_transcript(self, text: str) -> Optional[Turn]:
        """Invoked when STT yields final transcript text."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            return None

        logger.info(f"[VOICE ORCHESTRATOR] Delivering transcript to engine: '{clean_text}'")
        if self.display_mode:
            self._safe_print(f"🎤 YOU SAID: {clean_text}\n")

        turn = await self.engine.handle_user_input(clean_text)

        if self.display_mode and turn and not turn.is_cancelled and turn.response_text:
            self._safe_print(f"🤖 SOUSCHEF: {turn.response_text}\n\n🔊 SPEAKING...\n\n---\n")

        return turn

    async def process_user_utterance(self, text: str) -> Optional[Turn]:
        """Direct entry point to trigger transcript processing."""
        return await self._handle_transcript(text)

    async def listen_cycle(self) -> Optional[Turn]:
        """
        Single voice interaction cycle: listen via STT.
        Ensures transcript is delivered exactly once per completed utterance.
        """
        if self.display_mode and self.engine.state in (ConversationState.IDLE, ConversationState.COMPLETED):
            self._safe_print("🎤 LISTENING...\n")

        prior_turn_id = self.engine.current_turn_id
        text = await self.stt.listen_and_transcribe()

        # If callback already delivered transcript and created a new turn, return it
        if self.engine.current_turn and self.engine.current_turn_id != prior_turn_id:
            return self.engine.current_turn

        # If callback did not run (e.g. custom mock STT without callback wiring), process once
        clean_text = text.strip() if text else ""
        if clean_text:
            return await self._handle_transcript(clean_text)

        # Ensure engine state does not remain stuck in INTERRUPTED or CANCELLED if no transcript follows
        if self.engine.state in (ConversationState.INTERRUPTED, ConversationState.CANCELLED):
            self.engine.reset_to_idle()

        return None

    async def run_voice_loop(self) -> None:
        """Continuous real voice loop processing microphone audio."""
        logger.info("[VOICE ORCHESTRATOR] Starting continuous voice loop...")
        while True:
            try:
                await self.listen_cycle()
            except asyncio.CancelledError:
                logger.info("[VOICE ORCHESTRATOR] Voice loop stopped.")
                break
            except Exception as e:
                logger.error(f"[VOICE ORCHESTRATOR] Voice loop error: {e}")
                await asyncio.sleep(1.0)

