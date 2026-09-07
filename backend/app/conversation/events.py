import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger("souschef.conversation")

class EventType(str, Enum):
    USER_SPEECH = "USER_SPEECH"
    TURN_STARTED = "TURN_STARTED"
    STATE_CHANGED = "STATE_CHANGED"
    INTERRUPTION = "INTERRUPTION"
    TURN_CANCELLED = "TURN_CANCELLED"
    LLM_STARTED = "LLM_STARTED"
    LLM_COMPLETED = "LLM_COMPLETED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    STALE_RESPONSE_DISCARDED = "STALE_RESPONSE_DISCARDED"
    TTS_STARTED = "TTS_STARTED"
    TTS_STOP = "TTS_STOP"
    TTS_COMPLETED = "TTS_COMPLETED"
    TURN_COMPLETED = "TURN_COMPLETED"

def log_event(event_type: EventType, turn_id: Optional[str] = None, detail: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    msg = f"[{event_type.value}] turn_id={turn_id or 'NONE'}"
    if detail:
        msg += f" | {detail}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)
