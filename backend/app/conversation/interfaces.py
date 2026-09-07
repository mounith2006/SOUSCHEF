from abc import ABC, abstractmethod
from typing import Callable, Awaitable, List, Dict, Any, Optional

class TTSInterface(ABC):
    """
    Interface/Protocol for Text-to-Speech (Rime).
    RIME DEVELOPER REQUIREMENT:
    The Rime developer MUST implement `stop()` to immediately halt active audio playback
    when an interruption occurs.
    """

    @abstractmethod
    async def speak(self, text: str) -> None:
        """Stream or play spoken audio for the given response text."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Immediately stop any ongoing audio playback and clear audio buffers."""
        pass


class STTInterface(ABC):
    """
    Interface/Protocol for Speech-to-Text (Whisper / Microphone).
    STT DEVELOPER REQUIREMENT:
    The STT layer must trigger registered callbacks when user speech is detected or transcribed.
    """

    @abstractmethod
    def set_on_speech_started(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register callback for when user speech onset/barge-in is detected."""
        pass

    @abstractmethod
    def set_on_transcript(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Register callback for when final transcript is available."""
        pass


class LLMInterface(ABC):
    """Interface for LLM and Tool Orchestration layer."""

    @abstractmethod
    async def generate_response(self, user_input: str, conversation_history: List[Dict[str, str]]) -> str:
        """Generate response text for user input given conversation history."""
        pass


class ToolInterface(ABC):
    """Interface for asynchronous tool execution (timers, recipe tools)."""

    @abstractmethod
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a tool asynchronously."""
        pass
