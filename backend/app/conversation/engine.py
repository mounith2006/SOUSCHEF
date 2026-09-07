import asyncio
import uuid
import logging
from typing import Optional, List, Dict, Any
from .state import ConversationState, can_transition
from .turn import Turn
from .context import ConversationContext
from .interfaces import TTSInterface, STTInterface, LLMInterface, ToolInterface
from .events import EventType, log_event

logger = logging.getLogger("souschef.conversation")

class ConversationEngine:
    """
    Modular Conversation Engine for SOUSCHEF.
    Single source of truth for conversation state, current turn, interruption,
    cancellation, context management, and stale response protection.
    """

    def __init__(
        self,
        tts: TTSInterface,
        llm: LLMInterface,
        stt: Optional[STTInterface] = None,
        tool_runner: Optional[ToolInterface] = None,
        context: Optional[ConversationContext] = None,
        session_id: Optional[str] = None,
    ):
        self.tts = tts
        self.llm = llm
        self.stt = stt
        self.tool_runner = tool_runner
        self.context = context or ConversationContext()
        self.session_id = session_id or str(uuid.uuid4())

        self._state: ConversationState = ConversationState.IDLE
        self._current_turn: Optional[Turn] = None
        self._lock = asyncio.Lock()

        # Wire up STT callbacks if provided
        if self.stt:
            self.stt.set_on_speech_started(self.on_user_speech_started)
            self.stt.set_on_transcript(self.handle_user_input)

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def current_turn(self) -> Optional[Turn]:
        return self._current_turn

    @property
    def current_turn_id(self) -> Optional[str]:
        return self._current_turn.turn_id if self._current_turn else None

    def is_current_turn(self, turn_id: str) -> bool:
        """Check if turn_id matches active current_turn_id and is not cancelled."""
        if not self._current_turn:
            return False
        return (self._current_turn.turn_id == turn_id) and not self._current_turn.is_cancelled

    def _set_state(self, new_state: ConversationState, turn_id: Optional[str] = None) -> None:
        if not can_transition(self._state, new_state):
            logger.warning(
                f"Invalid transition from {self._state} to {new_state} for turn {turn_id}"
            )
        old_state = self._state
        self._state = new_state
        log_event(
            EventType.STATE_CHANGED,
            turn_id=turn_id,
            detail=f"{old_state.value} -> {new_state.value}"
        )

    async def on_user_speech_started(self) -> None:
        """
        Interruption trigger invoked when STT/VAD detects user speech.
        If state is THINKING, TOOL_RUNNING, or SPEAKING, cancel current turn & stop TTS.
        """
        async with self._lock:
            if self._state in (ConversationState.SPEAKING, ConversationState.THINKING, ConversationState.TOOL_RUNNING):
                await self._cancel_current_turn_internal(reason="User speech barge-in detected")

    def reset_to_idle(self) -> None:
        """Reset engine state to IDLE if currently INTERRUPTED or CANCELLED."""
        if self._state in (ConversationState.INTERRUPTED, ConversationState.CANCELLED):
            self._set_state(ConversationState.IDLE)

    async def interrupt(self) -> None:
        """Explicit public interface to trigger interruption flow."""
        await self.on_user_speech_started()

    async def cancel_current_turn(self, reason: str = "Explicit cancellation") -> None:
        """Public helper to cancel current active turn."""
        async with self._lock:
            await self._cancel_current_turn_internal(reason=reason)

    async def _cancel_current_turn_internal(self, reason: str) -> None:
        """Internal helper to stop TTS, cancel turn tasks, purge turn context, and update state."""
        if not self._current_turn:
            return

        turn = self._current_turn
        log_event(EventType.INTERRUPTION, turn_id=turn.turn_id, detail=reason)
        
        # 1. Mark turn as cancelled and cancel any pending asyncio tasks
        turn.cancel()
        log_event(EventType.TURN_CANCELLED, turn_id=turn.turn_id, detail=reason)

        # 2. Rollback uncommitted conversation context for this cancelled turn
        self.context.remove_turn_messages(turn.turn_id)

        # 3. Request TTS layer to stop immediately
        try:
            await self.tts.stop()
            log_event(EventType.TTS_STOP, turn_id=turn.turn_id, detail="TTS stop requested")
        except Exception as e:
            logger.error(f"Error calling tts.stop() for turn {turn.turn_id}: {e}")

        # 4. Transition engine state
        self._set_state(ConversationState.INTERRUPTED, turn_id=turn.turn_id)

    async def start_turn(self, text: str) -> Turn:
        """Start a new turn for user input."""
        return await self.handle_user_input(text)

    async def handle_user_input(self, text: str) -> Optional[Turn]:
        """
        Main entry point for user text input (from STT transcript or API).
        Creates a new Turn, manages cancellation of prior turns, and coordinates processing.
        """
        log_event(EventType.USER_SPEECH, detail=f"Text: '{text}'")

        async with self._lock:
            # If previous turn is active or interrupted, perform clean cancellation
            if self._current_turn and not self._current_turn.is_cancelled:
                if self._state in (ConversationState.SPEAKING, ConversationState.THINKING, ConversationState.TOOL_RUNNING, ConversationState.INTERRUPTED):
                    await self._cancel_current_turn_internal(reason="New user input arrived")

            # Create a brand new Turn with unique ID
            new_turn = Turn(user_input=text, state=ConversationState.LISTENING)
            self._current_turn = new_turn
            log_event(EventType.TURN_STARTED, turn_id=new_turn.turn_id, detail=f"Input: '{text}'")

            # Transition state to THINKING
            self._set_state(ConversationState.THINKING, turn_id=new_turn.turn_id)
            new_turn.state = ConversationState.THINKING

            # Add user message to context
            self.context.add_user_message(text, turn_id=new_turn.turn_id)

        # Execute turn processing as an asyncio Task so it can be cancelled asynchronously
        task = asyncio.create_task(self._process_turn(new_turn))
        new_turn.asyncio_task = task

        try:
            await task
            return new_turn
        except asyncio.CancelledError:
            log_event(EventType.TURN_CANCELLED, turn_id=new_turn.turn_id, detail="Asyncio task cancelled")
            return new_turn

    async def execute_tool_task(self, turn: Turn, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Helper to run an async tool within the turn execution lifecycle."""
        if not self.is_current_turn(turn.turn_id):
            log_event(EventType.STALE_RESPONSE_DISCARDED, turn_id=turn.turn_id, detail="Tool launch aborted due to stale turn")
            return None

        async with self._lock:
            self._set_state(ConversationState.TOOL_RUNNING, turn_id=turn.turn_id)
            turn.state = ConversationState.TOOL_RUNNING
            log_event(EventType.TOOL_STARTED, turn_id=turn.turn_id, detail=f"Tool: {tool_name}")

        if not self.tool_runner:
            log_event(EventType.TOOL_COMPLETED, turn_id=turn.turn_id, detail="No tool runner configured")
            return None

        try:
            tool_job = asyncio.create_task(self.tool_runner.execute_tool(tool_name, tool_args))
            turn.tool_task = tool_job
            result = await tool_job
            
            # Post-tool stale check
            if not self.is_current_turn(turn.turn_id):
                log_event(EventType.STALE_RESPONSE_DISCARDED, turn_id=turn.turn_id, detail="Tool result discarded due to stale turn")
                return None

            log_event(EventType.TOOL_COMPLETED, turn_id=turn.turn_id, detail=f"Result: {result}")
            async with self._lock:
                self._set_state(ConversationState.THINKING, turn_id=turn.turn_id)
                turn.state = ConversationState.THINKING
            return result
        except asyncio.CancelledError:
            log_event(EventType.TURN_CANCELLED, turn_id=turn.turn_id, detail="Tool execution cancelled")
            raise
        except Exception as e:
            logger.error(f"Tool execution error in turn {turn.turn_id}: {e}")
            return None

    async def _process_turn(self, turn: Turn) -> None:
        """Process turn: generate LLM response, validate staleness, and speak via TTS."""
        try:
            # 1. Pre-LLM Staleness Check
            if not self.is_current_turn(turn.turn_id):
                log_event(EventType.STALE_RESPONSE_DISCARDED, turn_id=turn.turn_id, detail="Pre-LLM check failed")
                self.context.remove_turn_messages(turn.turn_id)
                return

            log_event(EventType.LLM_STARTED, turn_id=turn.turn_id)
            history = self.context.get_messages()

            # Generate LLM Response
            try:
                response_text = await self.llm.generate_response(turn.user_input, history)
                turn.response_text = response_text
                log_event(EventType.LLM_COMPLETED, turn_id=turn.turn_id, detail=f"Response: '{response_text}'")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"LLM failure in turn {turn.turn_id}: {e}")
                async with self._lock:
                    self.context.remove_turn_messages(turn.turn_id)
                    self._set_state(ConversationState.IDLE, turn_id=turn.turn_id)
                return

            # 2. STALE RESPONSE PROTECTION (STRICT PRE-TTS GUARD)
            async with self._lock:
                if not self.is_current_turn(turn.turn_id):
                    log_event(
                        EventType.STALE_RESPONSE_DISCARDED,
                        turn_id=turn.turn_id,
                        detail=f"Discarded stale response before TTS (active={self.current_turn_id})"
                    )
                    self.context.remove_turn_messages(turn.turn_id)
                    return

                self._set_state(ConversationState.SPEAKING, turn_id=turn.turn_id)
                turn.state = ConversationState.SPEAKING
                self.context.add_assistant_message(response_text, turn_id=turn.turn_id)
                log_event(EventType.TTS_STARTED, turn_id=turn.turn_id)

            # 3. Speak via TTS
            try:
                await self.tts.speak(response_text)
                log_event(EventType.TTS_COMPLETED, turn_id=turn.turn_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"TTS failure in turn {turn.turn_id}: {e}")
                async with self._lock:
                    self._set_state(ConversationState.IDLE, turn_id=turn.turn_id)
                return

            # 4. Post-TTS Staleness Guard & State Transition
            async with self._lock:
                if not self.is_current_turn(turn.turn_id):
                    log_event(
                        EventType.STALE_RESPONSE_DISCARDED,
                        turn_id=turn.turn_id,
                        detail="Discarded post-speech due to turn supersedence"
                    )
                    self.context.remove_turn_messages(turn.turn_id)
                    return

                turn.state = ConversationState.COMPLETED
                self._set_state(ConversationState.COMPLETED, turn_id=turn.turn_id)
                self._set_state(ConversationState.IDLE, turn_id=turn.turn_id)
                log_event(EventType.TURN_COMPLETED, turn_id=turn.turn_id)

        except asyncio.CancelledError:
            log_event(EventType.TURN_CANCELLED, turn_id=turn.turn_id, detail="Cancelled during processing")
            turn.is_cancelled = True
            turn.state = ConversationState.CANCELLED
            self.context.remove_turn_messages(turn.turn_id)
            raise
        except Exception as e:
            logger.error(f"Unhandled error in turn {turn.turn_id}: {e}", exc_info=True)
            async with self._lock:
                turn.state = ConversationState.CANCELLED
                self.context.remove_turn_messages(turn.turn_id)
                self._set_state(ConversationState.IDLE, turn_id=turn.turn_id)
