import asyncio
import uuid
import logging
from typing import Optional, List, Dict, Any

from .state import ConversationState, can_transition
from .turn import Turn
from .context import ConversationContext
from .interfaces import (
    TTSInterface,
    STTInterface,
    LLMInterface,
    ToolInterface,
)
from .events import EventType, log_event


logger = logging.getLogger("souschef.conversation")


class ConversationEngine:
    """
    Modular Conversation Engine for SOUSCHEF.

    Responsible for:
    - conversation state
    - current turn
    - interruption
    - cancellation
    - context management
    - stale response protection
    - asynchronous tool execution
    - allowing new conversation turns while tools are running
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
            self.stt.set_on_speech_started(
                self.on_user_speech_started
            )
            self.stt.set_on_transcript(
                self.handle_user_input
            )

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def current_turn(self) -> Optional[Turn]:
        return self._current_turn

    @property
    def current_turn_id(self) -> Optional[str]:
        return (
            self._current_turn.turn_id
            if self._current_turn
            else None
        )

    def is_current_turn(self, turn_id: str) -> bool:
        """
        Check whether turn_id is still the active conversation turn.
        """
        if not self._current_turn:
            return False

        return (
            self._current_turn.turn_id == turn_id
            and not self._current_turn.is_cancelled
        )

    def _set_state(
        self,
        new_state: ConversationState,
        turn_id: Optional[str] = None,
    ) -> None:
        if not can_transition(self._state, new_state):
            logger.warning(
                f"Invalid transition from "
                f"{self._state} to {new_state} "
                f"for turn {turn_id}"
            )

        old_state = self._state
        self._state = new_state

        log_event(
            EventType.STATE_CHANGED,
            turn_id=turn_id,
            detail=(
                f"{old_state.value} -> "
                f"{new_state.value}"
            ),
        )

    async def on_user_speech_started(self) -> None:
        """
        Interruption trigger invoked when STT/VAD detects
        user speech.

        SPEAKING and THINKING are interrupted normally.

        TOOL_RUNNING is also interruptible, but the underlying
        tool operation is allowed to continue in the background.
        """

        async with self._lock:
            if self._state in (
                ConversationState.SPEAKING,
                ConversationState.THINKING,
                ConversationState.TOOL_RUNNING,
            ):
                await self._cancel_current_turn_internal(
                    reason="User speech barge-in detected"
                )

    def reset_to_idle(self) -> None:
        """
        Reset engine state to IDLE if currently INTERRUPTED
        or CANCELLED.
        """
        if self._state in (
            ConversationState.INTERRUPTED,
            ConversationState.CANCELLED,
        ):
            self._set_state(
                ConversationState.IDLE
            )

    async def interrupt(self) -> None:
        """
        Explicit public interface to trigger interruption.
        """
        await self.on_user_speech_started()

    async def cancel_current_turn(
        self,
        reason: str = "Explicit cancellation",
    ) -> None:
        """
        Public helper to cancel current active turn.
        """
        async with self._lock:
            await self._cancel_current_turn_internal(
                reason=reason
            )

    async def _cancel_current_turn_internal(
        self,
        reason: str,
    ) -> None:
        """
        Cancel the current conversational turn.

        IMPORTANT FOR STEP 6:

        Turn.cancel() cancels the conversation task,
        but does NOT cancel the underlying tool task.

        This means:
            conversation can move on
            while the tool continues running.
        """

        if not self._current_turn:
            return

        turn = self._current_turn

        log_event(
            EventType.INTERRUPTION,
            turn_id=turn.turn_id,
            detail=reason,
        )

        # 1. Mark turn as cancelled.
        #
        # Turn.cancel() must NOT cancel tool_task.
        turn.cancel()

        log_event(
            EventType.TURN_CANCELLED,
            turn_id=turn.turn_id,
            detail=reason,
        )

        # 2. Remove uncommitted context belonging
        #    to the cancelled turn.
        self.context.remove_turn_messages(
            turn.turn_id
        )

        # 3. Stop TTS immediately.
        try:
            await self.tts.stop()

            log_event(
                EventType.TTS_STOP,
                turn_id=turn.turn_id,
                detail="TTS stop requested",
            )

        except Exception as e:
            logger.error(
                f"Error calling tts.stop() "
                f"for turn {turn.turn_id}: {e}"
            )

        # 4. Mark conversation interrupted.
        self._set_state(
            ConversationState.INTERRUPTED,
            turn_id=turn.turn_id,
        )

    async def start_turn(self, text: str) -> Turn:
        """
        Start a new turn for user input.
        """
        return await self.handle_user_input(text)

    async def handle_user_input(
        self,
        text: str,
    ) -> Optional[Turn]:
        """
        Main entry point for user text input.

        STEP 6 BEHAVIOR:

        If the previous turn is TOOL_RUNNING,
        do NOT cancel it.

        Instead:
            - leave the tool running
            - create a new conversation turn
            - allow the user to continue talking
        """

        log_event(
            EventType.USER_SPEECH,
            detail=f"Text: '{text}'",
        )

        async with self._lock:

            # -------------------------------------------------
            # Cancel previous conversational work when needed.
            #
            # IMPORTANT:
            # TOOL_RUNNING is intentionally NOT included here.
            #
            # This is the core Step 6 change.
            # -------------------------------------------------
            if (
                self._current_turn
                and not self._current_turn.is_cancelled
            ):
                if self._state in (
                    ConversationState.SPEAKING,
                    ConversationState.THINKING,
                    ConversationState.INTERRUPTED,
                ):
                    await self._cancel_current_turn_internal(
                        reason="New user input arrived"
                    )

            # -------------------------------------------------
            # Create brand-new turn.
            # -------------------------------------------------
            new_turn = Turn(
                user_input=text,
                state=ConversationState.LISTENING,
            )

            self._current_turn = new_turn

            log_event(
                EventType.TURN_STARTED,
                turn_id=new_turn.turn_id,
                detail=f"Input: '{text}'",
            )

            # -------------------------------------------------
            # New user input becomes the active conversation.
            # -------------------------------------------------
            self._set_state(
                ConversationState.THINKING,
                turn_id=new_turn.turn_id,
            )

            new_turn.state = ConversationState.THINKING

            # -------------------------------------------------
            # Add new user message to context.
            # -------------------------------------------------
            self.context.add_user_message(
                text,
                turn_id=new_turn.turn_id,
            )

        # -----------------------------------------------------
        # Process asynchronously.
        # -----------------------------------------------------
        task = asyncio.create_task(
            self._process_turn(new_turn)
        )

        new_turn.asyncio_task = task

        try:
            await task
            return new_turn

        except asyncio.CancelledError:
            log_event(
                EventType.TURN_CANCELLED,
                turn_id=new_turn.turn_id,
                detail="Asyncio task cancelled",
            )

            return new_turn

    async def execute_tool_task(
        self,
        turn: Turn,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool asynchronously.

        STEP 6:

        The tool continues running even if the conversation
        turn becomes cancelled or stale.

        Example:

            Turn A
              |
              +---- Tool running --------------------+
                                                     |
            Turn B <---- new user input               |
                                                     |
            Turn A tool result ----------------------+
                       |
                       +---- discarded if stale
        """

        # -----------------------------------------------------
        # Do not start a tool for an already stale turn.
        # -----------------------------------------------------
        if not self.is_current_turn(
            turn.turn_id
        ):
            log_event(
                EventType.STALE_RESPONSE_DISCARDED,
                turn_id=turn.turn_id,
                detail=(
                    "Tool launch aborted "
                    "due to stale turn"
                ),
            )

            return None

        # -----------------------------------------------------
        # Mark conversation as TOOL_RUNNING.
        # -----------------------------------------------------
        async with self._lock:

            self._set_state(
                ConversationState.TOOL_RUNNING,
                turn_id=turn.turn_id,
            )

            turn.state = (
                ConversationState.TOOL_RUNNING
            )

            log_event(
                EventType.TOOL_STARTED,
                turn_id=turn.turn_id,
                detail=f"Tool: {tool_name}",
            )

        # -----------------------------------------------------
        # No tool runner configured.
        # -----------------------------------------------------
        if not self.tool_runner:
            log_event(
                EventType.TOOL_COMPLETED,
                turn_id=turn.turn_id,
                detail=(
                    "No tool runner configured"
                ),
            )

            return None

        try:

            # -------------------------------------------------
            # Create independent tool task.
            # -------------------------------------------------
            tool_job = asyncio.create_task(
                self.tool_runner.execute_tool(
                    tool_name,
                    tool_args,
                )
            )

            turn.tool_task = tool_job

            # -------------------------------------------------
            # IMPORTANT:
            #
            # shield() prevents cancellation of the parent
            # conversation task from cancelling the tool.
            # -------------------------------------------------
            result = await asyncio.shield(
                tool_job
            )

            # -------------------------------------------------
            # Tool finished, but conversation may have moved
            # to another turn.
            # -------------------------------------------------
            if not self.is_current_turn(
                turn.turn_id
            ):
                log_event(
                    EventType.STALE_RESPONSE_DISCARDED,
                    turn_id=turn.turn_id,
                    detail=(
                        "Tool result discarded "
                        "because turn is stale"
                    ),
                )

                return None

            # -------------------------------------------------
            # Tool completed successfully.
            # -------------------------------------------------
            log_event(
                EventType.TOOL_COMPLETED,
                turn_id=turn.turn_id,
                detail=f"Result: {result}",
            )

            # -------------------------------------------------
            # Return to THINKING so the LLM can process
            # the tool result.
            # -------------------------------------------------
            async with self._lock:

                if not self.is_current_turn(
                    turn.turn_id
                ):
                    log_event(
                        EventType.STALE_RESPONSE_DISCARDED,
                        turn_id=turn.turn_id,
                        detail=(
                            "Tool result became stale "
                            "before state update"
                        ),
                    )

                    return None

                self._set_state(
                    ConversationState.THINKING,
                    turn_id=turn.turn_id,
                )

                turn.state = (
                    ConversationState.THINKING
                )

            return result

        except asyncio.CancelledError:

            # -------------------------------------------------
            # The conversation task was cancelled.
            #
            # DO NOT cancel tool_job.
            #
            # Because it is protected by asyncio.shield(),
            # the tool continues running.
            # -------------------------------------------------
            log_event(
                EventType.TURN_CANCELLED,
                turn_id=turn.turn_id,
                detail=(
                    "Conversation cancelled "
                    "while tool continues"
                ),
            )

            raise

        except Exception as e:

            logger.error(
                f"Tool execution error "
                f"in turn {turn.turn_id}: {e}"
            )

            return None

    async def _process_turn(
        self,
        turn: Turn,
    ) -> None:
        """
        Process a conversational turn.

        Current pipeline:
            user input
                ↓
            LLM
                ↓
            TTS

        Tool execution can be invoked through
        execute_tool_task().
        """

        try:

            # -------------------------------------------------
            # 1. PRE-LLM STALENESS CHECK
            # -------------------------------------------------
            if not self.is_current_turn(
                turn.turn_id
            ):
                log_event(
                    EventType.STALE_RESPONSE_DISCARDED,
                    turn_id=turn.turn_id,
                    detail=(
                        "Pre-LLM check failed"
                    ),
                )

                self.context.remove_turn_messages(
                    turn.turn_id
                )

                return

            log_event(
                EventType.LLM_STARTED,
                turn_id=turn.turn_id,
            )

            history = self.context.get_messages()
            
            # -------------------------------------------------
            # INTENT ROUTING & TOOL EXECUTION
            # -------------------------------------------------
            from .intent import detect_intent, Intent
            
            intent, query = detect_intent(turn.user_input)
            if intent != Intent.UNKNOWN and self.tool_runner:
                tool_name = None
                tool_args = {}

                if intent in (Intent.START_RECIPE, Intent.GET_RECIPE):
                    tool_name = "find_recipe"
                    tool_args = {"query": query}
                elif intent == Intent.NEXT_STEP:
                    if self.context.active_recipe:
                        tool_name = "get_step"
                        tool_args = {
                            "recipe_name": self.context.active_recipe,
                            "step_index": self.context.active_step + 1 if self.context.active_step is not None else 0
                        }
                    else:
                        tool_name = "no_recipe_active"
                elif intent in (Intent.REPEAT_STEP, Intent.CURRENT_STEP):
                    if self.context.active_recipe:
                        tool_name = "get_step"
                        tool_args = {
                            "recipe_name": self.context.active_recipe,
                            "step_index": self.context.active_step if self.context.active_step is not None else 0
                        }
                    else:
                        tool_name = "no_recipe_active"

                if tool_name:
                    tool_result = await self.execute_tool_task(turn, tool_name, tool_args)
                    
                    if not self.is_current_turn(turn.turn_id):
                        log_event(
                            EventType.STALE_RESPONSE_DISCARDED,
                            turn_id=turn.turn_id,
                            detail="Stale turn after tool execution"
                        )
                        return
                        
                    if tool_result:
                        action = tool_result.get("action")
                        # Only START_RECIPE updates active recipe. GET_RECIPE just retrieves it.
                        if action == "found_recipe" and intent == Intent.START_RECIPE:
                            self.context.active_recipe = tool_result.get("recipe_name")
                            self.context.active_step = 0
                        elif action == "step_retrieved":
                            self.context.active_step = tool_result.get("step_index")
                            
                        # Append tool context for the LLM
                        history.append({"role": "system", "content": f"[TOOL RESULT: {tool_result}]"})

            # -------------------------------------------------
            # Generate LLM response.
            # -------------------------------------------------
            try:

                response_text = (
                    await self.llm.generate_response(
                        turn.user_input,
                        history,
                    )
                )

                turn.response_text = response_text

                log_event(
                    EventType.LLM_COMPLETED,
                    turn_id=turn.turn_id,
                    detail=(
                        f"Response: "
                        f"'{response_text}'"
                    ),
                )

            except asyncio.CancelledError:
                raise

            except Exception as e:

                logger.error(
                    f"LLM failure in turn "
                    f"{turn.turn_id}: {e}"
                )

                async with self._lock:

                    self.context.remove_turn_messages(
                        turn.turn_id
                    )

                    self._set_state(
                        ConversationState.IDLE,
                        turn_id=turn.turn_id,
                    )

                return

            # -------------------------------------------------
            # 2. STRICT PRE-TTS STALE CHECK
            # -------------------------------------------------
            async with self._lock:

                if not self.is_current_turn(
                    turn.turn_id
                ):
                    log_event(
                        EventType.STALE_RESPONSE_DISCARDED,
                        turn_id=turn.turn_id,
                        detail=(
                            "Discarded stale response "
                            "before TTS "
                            f"(active="
                            f"{self.current_turn_id})"
                        ),
                    )

                    self.context.remove_turn_messages(
                        turn.turn_id
                    )

                    return

                self._set_state(
                    ConversationState.SPEAKING,
                    turn_id=turn.turn_id,
                )

                turn.state = (
                    ConversationState.SPEAKING
                )

                self.context.add_assistant_message(
                    response_text,
                    turn_id=turn.turn_id,
                )

                log_event(
                    EventType.TTS_STARTED,
                    turn_id=turn.turn_id,
                )

            # -------------------------------------------------
            # 3. SPEAK
            # -------------------------------------------------
            try:

                await self.tts.speak(
                    response_text
                )

                log_event(
                    EventType.TTS_COMPLETED,
                    turn_id=turn.turn_id,
                )

            except asyncio.CancelledError:
                raise

            except Exception as e:

                logger.error(
                    f"TTS failure in turn "
                    f"{turn.turn_id}: {e}"
                )

                async with self._lock:

                    self._set_state(
                        ConversationState.IDLE,
                        turn_id=turn.turn_id,
                    )

                return

            # -------------------------------------------------
            # 4. POST-TTS STALE CHECK
            # -------------------------------------------------
            async with self._lock:

                if not self.is_current_turn(
                    turn.turn_id
                ):
                    log_event(
                        EventType.STALE_RESPONSE_DISCARDED,
                        turn_id=turn.turn_id,
                        detail=(
                            "Discarded post-speech "
                            "due to turn supersedence"
                        ),
                    )

                    self.context.remove_turn_messages(
                        turn.turn_id
                    )

                    return

                turn.state = (
                    ConversationState.COMPLETED
                )

                self._set_state(
                    ConversationState.COMPLETED,
                    turn_id=turn.turn_id,
                )

                self._set_state(
                    ConversationState.IDLE,
                    turn_id=turn.turn_id,
                )

                log_event(
                    EventType.TURN_COMPLETED,
                    turn_id=turn.turn_id,
                )

        except asyncio.CancelledError:

            log_event(
                EventType.TURN_CANCELLED,
                turn_id=turn.turn_id,
                detail=(
                    "Cancelled during processing"
                ),
            )

            turn.is_cancelled = True
            turn.state = (
                ConversationState.CANCELLED
            )

            self.context.remove_turn_messages(
                turn.turn_id
            )

            raise

        except Exception as e:

            logger.error(
                f"Unhandled error in turn "
                f"{turn.turn_id}: {e}",
                exc_info=True,
            )

            async with self._lock:

                turn.state = (
                    ConversationState.CANCELLED
                )

                self.context.remove_turn_messages(
                    turn.turn_id
                )

                self._set_state(
                    ConversationState.IDLE,
                    turn_id=turn.turn_id,
                )