import time
import uuid
import asyncio
from typing import Optional, Any, Dict
from dataclasses import dataclass, field

from .state import ConversationState


@dataclass
class Turn:
    turn_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    user_input: str = ""
    state: ConversationState = ConversationState.IDLE
    created_at: float = field(
        default_factory=time.time
    )
    is_cancelled: bool = False
    response_text: Optional[str] = None

    asyncio_task: Optional[asyncio.Task] = field(
        default=None,
        repr=False,
    )

    tool_task: Optional[asyncio.Task] = field(
        default=None,
        repr=False,
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def cancel(self) -> None:
        """
        Mark the conversational turn as cancelled.

        STEP 6:
        A conversation turn can be cancelled while its tool
        operation continues running.

        We therefore cancel only the conversation asyncio task
        and intentionally DO NOT cancel tool_task.
        """

        self.is_cancelled = True
        self.state = ConversationState.CANCELLED

        # Cancel the conversation/LLM/TTS processing task.
        if (
            self.asyncio_task
            and not self.asyncio_task.done()
        ):
            self.asyncio_task.cancel()

        # IMPORTANT:
        # Do NOT cancel self.tool_task.
        #
        # The tool must be allowed to continue running even
        # after this conversation turn becomes stale.
        #
        # Example:
        #
        # Turn A -> timer tool starts
        # Turn B -> user asks another question
        # Turn A tool -> continues in background
