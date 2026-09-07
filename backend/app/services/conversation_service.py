from typing import Optional, Dict
from ..conversation.engine import ConversationEngine
from ..conversation.interfaces import LLMInterface, TTSInterface, STTInterface
from .rime_tts_service import RimeTTSService
from .stt_service import DefaultSTTService
from .llm_service import get_llm_service, LocalTestLLM

class SessionConversationManager:
    """Registry managing session-scoped ConversationEngine instances for multi-session safety."""

    def __init__(self):
        self._engines: Dict[str, ConversationEngine] = {}

    def get_engine_for_session(
        self,
        session_id: str = "default_session",
        tts: Optional[TTSInterface] = None,
        llm: Optional[LLMInterface] = None,
        stt: Optional[STTInterface] = None,
    ) -> ConversationEngine:
        if session_id not in self._engines:
            tts_inst = tts or RimeTTSService()
            llm_inst = llm or get_llm_service()
            stt_inst = stt or DefaultSTTService()
            self._engines[session_id] = ConversationEngine(
                tts=tts_inst,
                llm=llm_inst,
                stt=stt_inst,
                session_id=session_id,
            )
        return self._engines[session_id]

    def clear_session(self, session_id: str) -> None:
        if session_id in self._engines:
            del self._engines[session_id]

_manager = SessionConversationManager()

def get_conversation_engine(
    session_id: str = "default_session",
    tts: Optional[TTSInterface] = None,
    llm: Optional[LLMInterface] = None,
    stt: Optional[STTInterface] = None,
) -> ConversationEngine:
    """Helper to retrieve or create session-scoped ConversationEngine instance."""
    return _manager.get_engine_for_session(session_id=session_id, tts=tts, llm=llm, stt=stt)
