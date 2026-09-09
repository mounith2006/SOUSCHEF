import asyncio
import re
import sys
import logging
from typing import Optional

from ..conversation.engine import ConversationEngine
from ..conversation.state import ConversationState
from ..conversation.turn import Turn
from ..config import get_settings
from .stt_service import DefaultSTTService
from .rime_tts_service import RimeTTSService
from .conversation_service import get_conversation_engine
from .wake_word_service import WakeWordService
from .wake_word_listener import WakeWordListener


# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        pass


logger = logging.getLogger("souschef.orchestrator")


class VoiceOrchestrator:
    """
    Voice Orchestrator connecting:

        microphone
            ↓
        wake word
            ↓
        active listening
            ↓
        STT
            ↓
        ConversationEngine
            ↓
        Rime TTS

    ConversationEngine remains the single source of truth for
    conversation state and interruption handling.
    """

    def __init__(
        self,
        engine: Optional[ConversationEngine] = None,
        stt: Optional[DefaultSTTService] = None,
        tts: Optional[RimeTTSService] = None,
        session_id: str = "default_session",
        display_mode: bool = False,
    ):
        settings = get_settings()

        self.session_id = session_id
        self.display_mode = display_mode
        self._background_tasks = set()

        self.tts = tts or RimeTTSService()
        self.stt = stt or DefaultSTTService()

        self.engine = engine or get_conversation_engine(
            session_id=session_id,
            tts=self.tts,
            stt=self.stt,
        )

        self.wake_word_service = WakeWordService()

        self.wake_listener = WakeWordListener(
            stt=self.stt,
            wake_word_service=self.wake_word_service,
            chunk_duration=settings.wake_chunk_duration,
            overlap_duration=settings.wake_overlap_duration,
            min_energy=settings.wake_min_energy,
        )

        self.active_listening_timeout = (
            settings.active_listening_timeout
        )
        self.sleep_warning_timeout = getattr(
            settings, "sleep_warning_timeout", 8.0
        )

        self._wake_loop_running = False

        # Wire STT callbacks.
        #
        # IMPORTANT:
        # VoiceOrchestrator owns the actual voice interaction path.
        self.stt.set_on_speech_started(
            self._handle_speech_started
        )

        self.stt.set_on_transcript(
            self._handle_transcript
        )

    def _safe_print(self, text: str) -> None:
        """Print safely on Windows terminals."""

        try:
            print(
                text,
                flush=True,
            )
        except UnicodeEncodeError:
            safe_text = (
                text.replace(
                    "🎤 LISTENING...",
                    "LISTENING...",
                )
                .replace(
                    "🎤 YOU:",
                    "YOU:",
                )
                .replace(
                    "🤖 SOUSCHEF:",
                    "SOUSCHEF:",
                )
                .replace(
                    "🔊 SPEAKING...",
                    "SPEAKING...",
                )
                .replace(
                    "⚡ INTERRUPTED",
                    "INTERRUPTED",
                )
            )

            print(
                safe_text,
                flush=True,
            )

    async def _handle_speech_started(self) -> None:
        """
        Existing VAD barge-in path.

        This remains useful for active command capture.

        If SOUSCHEF is currently:
            SPEAKING
            THINKING
            TOOL_RUNNING

        ConversationEngine cancels the active turn and stops TTS.
        """

        logger.info(
            "[VOICE ORCHESTRATOR] "
            "Speech onset detected -> checking interruption"
        )

        if self.engine.state in (
            ConversationState.SPEAKING,
            ConversationState.THINKING,
            ConversationState.TOOL_RUNNING,
        ):
            if self.display_mode:
                self._safe_print(
                    "\n⚡ INTERRUPTED\n"
                )

        await self.engine.on_user_speech_started()

    async def _handle_transcript(
        self,
        text: str,
    ) -> Optional[Turn]:
        """
        Deliver final user transcript to ConversationEngine.
        """

        # State-based echo cancellation:
        # While the engine is SPEAKING, Whisper transcripts caused by Rime speaker audio
        # must NOT be routed as user commands unless they pass the wake-word interruption path.
        if self.engine.state == ConversationState.SPEAKING:
            logger.info(
                "[VOICE ORCHESTRATOR] "
                "Discarding transcript during SPEAKING state (Echo Cancellation)"
            )
            return None

        clean_text = (
            text.strip()
            if text
            else ""
        )

        if not clean_text:
            return None

        logger.info(
            "[VOICE ORCHESTRATOR] "
            "Delivering transcript to engine: '%s'",
            clean_text,
        )

        if self.display_mode:
            self._safe_print(
                f"🎤 YOU: {clean_text}\n"
            )

        if await self._try_local_cooking_command(clean_text):
            return None

        turn = await self.engine.handle_user_input(
            clean_text
        )

        if (
            self.display_mode
            and turn
            and not turn.is_cancelled
            and turn.response_text
        ):
            self._safe_print(
                f"🤖 SOUSCHEF: "
                f"{turn.response_text}\n"
            )

        return turn

    async def _try_local_cooking_command(self, text: str) -> bool:
        """Handle common state commands without a slow remote LLM round trip."""
        runner = self.engine.tool_runner
        if runner is None:
            return False

        normalized = text.lower().strip(" .!?")
        tool_name = ""
        arguments = {}

        if any(phrase in normalized for phrase in ("current step", "what's next", "what is next", "repeat the step")):
            tool_name = "get_current_step"
        elif any(phrase in normalized for phrase in ("finished this step", "done with this step", "completed this step")):
            tool_name = "complete_step"
        elif any(phrase in normalized for phrase in ("list my timers", "what timers", "show my timers")):
            tool_name = "list_timers"
        else:
            timer_match = re.search(
                r"(?:set|start)(?: a)? timer(?: for)? (\d+(?:\.\d+)?)\s*(seconds?|minutes?)",
                normalized,
            )
            if timer_match:
                duration = float(timer_match.group(1))
                if timer_match.group(2).startswith("minute"):
                    duration *= 60
                tool_name = "start_timer"
                arguments = {"duration_seconds": duration, "label": "Cooking timer"}

        if not tool_name:
            return False

        result = await runner.execute_tool(tool_name, arguments)
        if not isinstance(result, dict) or not result.get("ok"):
            return False

        data = result.get("data")
        if tool_name == "get_current_step":
            response = (
                f"Your current step is: {data['instruction']}"
                if data
                else "You have completed all the recipe steps."
            )
        elif tool_name == "complete_step":
            step = data.get("current_step") if data else None
            response = (
                f"Done. Your next step is: {step['instruction']}"
                if step
                else "Great work. You have completed the recipe."
            )
        elif tool_name == "start_timer":
            response = f"Timer started for {data['duration_seconds']:g} seconds."
        else:
            active = [timer for timer in data if timer["status"] in ("running", "paused")]
            response = (
                f"You have {len(active)} active timer{'s' if len(active) != 1 else ''}."
                if active
                else "You have no active timers."
            )

        await self._speak_feedback(response)
        return True

    async def _speak_feedback(self, text: str) -> None:
        """Speak local voice-state feedback without spending an LLM request."""
        if self.display_mode:
            self._safe_print(f"🤖 SOUSCHEF: {text}\n")
        await self.tts.speak(text)

    async def _wake_greeting(self) -> str:
        """Resume the active cooking step when a sleeping session is awakened."""
        runner = self.engine.tool_runner
        if runner is not None:
            result = await runner.execute_tool("get_cooking_state", {})
            if isinstance(result, dict) and result.get("ok"):
                step = result.get("data", {}).get("current_step")
                if step:
                    return f"Welcome back. We were on this step: {step['instruction']} I'm listening."
        return "Yes, I'm listening. What would you like to cook?"

    async def _capture_active_text(self, timeout: float | None = None) -> tuple[str, str]:
        """Return (status, text), distinguishing silence from unclear speech."""
        audio = await asyncio.to_thread(
            self.stt.record_active_command,
            timeout or self.active_listening_timeout,
        )
        if audio.size == 0:
            return "silence", ""
        text = await asyncio.to_thread(self.stt.transcribe, audio)
        clean_text = text.strip() if text else ""
        return ("heard", clean_text) if clean_text else ("unclear", "")

    async def _process_transcript_background(self, text: str) -> None:
        try:
            await self._handle_transcript(text)
        except asyncio.CancelledError:
            pass
        except Exception as error:
            logger.error(
                "[VOICE ORCHESTRATOR] Background processing error: %s",
                error,
                exc_info=True,
            )

    def _start_background_processing(self, text: str) -> asyncio.Task:
        task = asyncio.create_task(self._process_transcript_background(text))
        self._background_tasks.add(task)

        def _on_task_done(t):
            self._background_tasks.discard(t)
            try:
                if not t.cancelled() and t.exception() is not None:
                    logger.error(f"[VOICE ORCHESTRATOR] Background task exception: {t.exception()}")
            except Exception:
                pass

        task.add_done_callback(_on_task_done)
        return task

    async def process_user_utterance(
        self,
        text: str,
    ) -> Optional[Turn]:
        """
        Direct transcript entry point.

        Existing tests and non-microphone callers continue
        to use this method.
        """

        return await self._handle_transcript(
            text
        )

    async def process_wake_command(
        self,
        cleaned_text: str,
    ) -> Optional[Turn]:
        """
        Process text that has already passed the wake-word gate.

        This is the bridge between the new wake detector and
        ConversationEngine.

        IMPORTANT:

        If the engine is currently SPEAKING / THINKING /
        TOOL_RUNNING, detecting the wake word itself is enough
        to trigger the existing interruption machinery.

        Then the actual command becomes the new turn.
        """

        cleaned_text = (
            cleaned_text.strip()
            if cleaned_text
            else ""
        )

        active_state = self.engine.state in (
            ConversationState.SPEAKING,
            ConversationState.THINKING,
            ConversationState.TOOL_RUNNING,
        )

        if active_state:
            logger.info(
                "[WAKE] Wake word detected during active turn. "
                "Interrupting current turn."
            )

            if self.display_mode:
                self._safe_print(
                    "\n⚡ WAKE WORD INTERRUPTION\n"
                )

            # This calls:
            #
            #   Turn.cancel()
            #   context rollback
            #   tts.stop()
            #   state -> INTERRUPTED
            #
            await self.engine.on_user_speech_started()

        # If the wake word was the entire utterance,
        # the caller will open the 6-second command window.
        if not cleaned_text:
            return None

        return await self._handle_transcript(
            cleaned_text
        )

    async def listen_cycle(self) -> Optional[Turn]:
        """
        Existing single STT interaction cycle.

        Kept for compatibility with current tests and
        non-wake-word microphone testing.
        """

        if (
            self.display_mode
            and self.engine.state
            in (
                ConversationState.IDLE,
                ConversationState.COMPLETED,
            )
        ):
            self._safe_print(
                "🎤 LISTENING...\n"
            )

        prior_turn_id = (
            self.engine.current_turn_id
        )

        import inspect
        if inspect.iscoroutinefunction(self.stt.listen_and_transcribe):
            text = await self.stt.listen_and_transcribe()
        else:
            text = await asyncio.to_thread(self.stt.listen_and_transcribe)

        if inspect.isawaitable(text):
            text = await text

        # Callback may already have created the turn.
        if (
            self.engine.current_turn
            and self.engine.current_turn_id
            != prior_turn_id
        ):
            return self.engine.current_turn

        clean_text = (
            text.strip()
            if text
            else ""
        )

        if clean_text:
            return await self._handle_transcript(
                clean_text
            )

        if self.engine.state in (
            ConversationState.INTERRUPTED,
            ConversationState.CANCELLED,
        ):
            self.engine.reset_to_idle()

        return None

    async def run_wake_word_loop(self) -> None:
        """
        Main production voice loop.

        State machine:

            SLEEPING
                ↓
            detect "Sofi"
                ↓
            ACTIVE
                ↓
            listen up to timeout
                ↓
            ConversationEngine (in background)
                ↓
            Rime
                ↓
            SLEEPING

        If "Sofi" is detected while Rime/LLM/tool processing
        is active:

            wake detected
                ↓
            ConversationEngine interruption
                ↓
            tts.stop()
                ↓
            capture new command (in background)
        """

        logger.info(
            "[VOICE ORCHESTRATOR] "
            "Starting wake-word voice loop"
        )

        self._wake_loop_running = True

        try:
            while self._wake_loop_running:

                try:
                    # --------------------------------------------------
                    # 1. SLEEPING / WAKE DETECTION
                    # --------------------------------------------------

                    wake_detected, wake_text = (
                        await self.wake_listener
                        .listen_for_wake_word()
                    )

                    if not wake_detected:
                        continue

                    logger.info(
                        "[VOICE ORCHESTRATOR] "
                        "Wake word detected. "
                        "Inline text='%s'",
                        wake_text,
                    )

                    # --------------------------------------------------
                    # 2. WAKE WORD ITSELF CAN INTERRUPT
                    # --------------------------------------------------

                    if self.engine.state in (
                        ConversationState.SPEAKING,
                        ConversationState.THINKING,
                        ConversationState.TOOL_RUNNING,
                    ):
                        await self.engine.on_user_speech_started()

                        if self.display_mode:
                            self._safe_print(
                                "\n⚡ INTERRUPTED BY 'SOFI'\n"
                            )

                    # --------------------------------------------------
                    # 3. COMMAND WAS SPOKEN IN SAME CHUNK
                    #
                    # Example:
                    #
                    # "Sofi, how much salt?"
                    #
                    # wake_text becomes:
                    #
                    # "how much salt?"
                    # --------------------------------------------------

                    if wake_text:
                        self._start_background_processing(
                            wake_text
                        )

                        # The turn runs inside _process_transcript_background,
                        # so we go back to wake mode immediately.
                        continue

                    # --------------------------------------------------
                    # 4. WAKE WORD ONLY
                    #
                    # Example:
                    #
                    # "Sofi"
                    #
                    # Open a short active listening window.
                    # --------------------------------------------------

                    if self.display_mode:
                        self._safe_print(
                            "\n🟡 SOUSCHEF ACTIVE "
                            f"({self.active_listening_timeout:.1f}s)\n"
                        )

                    audio = await asyncio.to_thread(
                        self.stt.record_active_command,
                        self.active_listening_timeout,
                    )

                    if audio.size == 0:
                        logger.info(
                            "[VOICE ORCHESTRATOR] "
                            "No command after wake word. "
                            "Returning to sleep."
                        )

                        if self.display_mode:
                            self._safe_print(
                                "\n💤 No command. "
                                "Returning to wake mode.\n"
                            )

                        if self.engine.state in (
                            ConversationState.INTERRUPTED,
                            ConversationState.CANCELLED,
                        ):
                            self.engine.reset_to_idle()

                        continue

                    # --------------------------------------------------
                    # 5. WHISPER COMMAND
                    # --------------------------------------------------

                    command_text = await asyncio.to_thread(
                        self.stt.transcribe,
                        audio,
                    )

                    command_text = (
                        command_text.strip()
                        if command_text
                        else ""
                    )

                    if not command_text:
                        logger.info(
                            "[VOICE ORCHESTRATOR] "
                            "No command transcript."
                        )

                        if self.engine.state in (
                            ConversationState.INTERRUPTED,
                            ConversationState.CANCELLED,
                        ):
                            self.engine.reset_to_idle()

                        continue

                    # --------------------------------------------------
                    # 6. PROCESS COMMAND IN BACKGROUND
                    # --------------------------------------------------

                    self._start_background_processing(
                        command_text
                    )

                except asyncio.CancelledError:
                    raise

                except Exception as error:
                    logger.error(
                        "[VOICE ORCHESTRATOR] "
                        "Wake loop error: %s",
                        error,
                        exc_info=True,
                    )

                    # Don't kill the entire voice assistant because
                    # one microphone/Whisper operation failed.
                    await asyncio.sleep(
                        1.0
                    )

        finally:
            self._wake_loop_running = False
            self.wake_listener.stop()

            # Clean up tracking tasks
            for task in list(self._background_tasks):
                task.cancel()
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)

            logger.info(
                "[VOICE ORCHESTRATOR] "
                "Wake-word loop stopped."
            )

    async def stop_voice_loop(self) -> None:
        """
        Stop the production wake-word loop.
        """

        self._wake_loop_running = False
        self.wake_listener.stop()

        for task in list(self._background_tasks):
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info(
            "[VOICE ORCHESTRATOR] "
            "Stop requested."
        )

    async def run_voice_loop(self) -> None:
        """
        Backwards-compatible entry point.

        Existing demo_voice.py calls run_voice_loop(),
        so we redirect it to the new wake-word loop.
        """

        await self.run_wake_word_loop()


if __name__ == "__main__":
    try:
        from .llm_service import get_llm_service
    except ImportError:
        from app.services.llm_service import get_llm_service

    async def main():
        settings = get_settings()
        stt = DefaultSTTService()
        tts = RimeTTSService()
        llm = get_llm_service(provider=settings.llm_provider)

        engine = get_conversation_engine(
            session_id="voice_demo_session",
            tts=tts,
            stt=stt,
            llm=llm,
        )

        orchestrator = VoiceOrchestrator(
            engine=engine,
            stt=stt,
            tts=tts,
            display_mode=True,
        )

        await orchestrator.run_voice_loop()

    asyncio.run(main())