from enum import Enum, auto

class ConversationState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    TOOL_RUNNING = "TOOL_RUNNING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

# Valid state transitions map
VALID_TRANSITIONS = {
    ConversationState.IDLE: {ConversationState.LISTENING, ConversationState.THINKING},
    ConversationState.LISTENING: {ConversationState.THINKING, ConversationState.CANCELLED, ConversationState.INTERRUPTED, ConversationState.IDLE},
    ConversationState.THINKING: {ConversationState.TOOL_RUNNING, ConversationState.SPEAKING, ConversationState.CANCELLED, ConversationState.INTERRUPTED, ConversationState.IDLE},
    ConversationState.TOOL_RUNNING: {ConversationState.THINKING, ConversationState.SPEAKING, ConversationState.CANCELLED, ConversationState.INTERRUPTED, ConversationState.IDLE},
    ConversationState.SPEAKING: {ConversationState.IDLE, ConversationState.COMPLETED, ConversationState.INTERRUPTED, ConversationState.CANCELLED, ConversationState.LISTENING},
    ConversationState.INTERRUPTED: {ConversationState.CANCELLED, ConversationState.LISTENING, ConversationState.THINKING, ConversationState.IDLE},
    ConversationState.CANCELLED: {ConversationState.IDLE, ConversationState.LISTENING, ConversationState.THINKING},
    ConversationState.COMPLETED: {ConversationState.IDLE, ConversationState.LISTENING, ConversationState.THINKING},
}

def can_transition(current: ConversationState, target: ConversationState) -> bool:
    if current == target:
        return True
    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed
