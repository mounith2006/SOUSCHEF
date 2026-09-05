from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    turn_id: str

class ConversationContext:
    """Bounded in-memory conversation context manager with turn rollback support."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._messages: List[Message] = []
        self.active_recipe: Optional[str] = None
        self.active_step: Optional[int] = None

    def add_user_message(self, content: str, turn_id: str) -> None:
        self._messages.append(Message(role="user", content=content, turn_id=turn_id))
        self._trim_history()

    def add_assistant_message(self, content: str, turn_id: str) -> None:
        self._messages.append(Message(role="assistant", content=content, turn_id=turn_id))
        self._trim_history()

    def remove_turn_messages(self, turn_id: str) -> None:
        """Purge messages belonging to a cancelled or invalidated turn."""
        self._messages = [m for m in self._messages if m.turn_id != turn_id]

    def _trim_history(self) -> None:
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history:]

    def get_messages(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def clear(self) -> None:
        self._messages.clear()
        self.active_recipe = None
        self.active_step = None
