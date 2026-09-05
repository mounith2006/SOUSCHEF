import time
import uuid
import asyncio
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from .state import ConversationState

@dataclass
class Turn:
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str = ""
    state: ConversationState = ConversationState.IDLE
    created_at: float = field(default_factory=time.time)
    is_cancelled: bool = False
    response_text: Optional[str] = None
    asyncio_task: Optional[asyncio.Task] = field(default=None, repr=False)
    tool_task: Optional[asyncio.Task] = field(default=None, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def cancel(self) -> None:
        """Mark turn as cancelled and cancel its underlying asyncio tasks if running."""
        self.is_cancelled = True
        self.state = ConversationState.CANCELLED
        if self.asyncio_task and not self.asyncio_task.done():
            self.asyncio_task.cancel()
        if self.tool_task and not self.tool_task.done():
            self.tool_task.cancel()
