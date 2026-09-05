# SOUSCHEF Conversation Engine Specification & Integration Contract

## Overview
The **Conversation Engine** (`backend/app/conversation/`) is the central voice conversation state machine, turn manager, and event orchestrator for **SOUSCHEF**.

It manages real-time voice interaction dynamics:
1. **True Barge-In / Interruption Handling**: Instantly halting active TTS playback and speaker hardware when user speech onset is detected.
2. **Turn Cancellation**: Cancelling running LLM and tool `asyncio` tasks cleanly upon interruption.
3. **Stale Response Protection**: Discarding superseded turn outputs before they reach the TTS layer.
4. **Bounded Context Management**: Maintaining bounded conversation history and rolling back uncommitted turn context upon cancellation.
5. **Session Isolation**: Guaranteeing isolated conversation states across multiple user sessions via `SessionConversationManager`.

---

## System Architecture

```
🎤 MICROPHONE
     │
     ▼
REAL STT / WHISPER
     │
     ├──────── SPEECH_STARTED ──────► ConversationEngine.on_user_speech_started()
     │                                     │
     ▼                                     ▼
TRANSCRIPT_READY                      cancel_current_turn() ──► Rime.stop()
     │                                     │
     ▼                                     ▼
ConversationEngine.handle_user_input()   [INTERRUPTED]
     │
     ▼
LLM / LocalTestLLM
     │
     ▼
Stale-Result Guard (is_current_turn)
     │
     ▼
Rime TTS & Speaker Playback
```

---

## State Machine Model

| State | Description |
| :--- | :--- |
| `IDLE` | Engine is idle, ready for user input. |
| `LISTENING` | User speech is being captured or transcribed by STT. |
| `THINKING` | LLM or tool processing is underway for the current turn. |
| `TOOL_RUNNING` | Async tool (e.g., recipe lookup, timer) is executing. |
| `SPEAKING` | Rime TTS is actively playing audio through local speakers. |
| `INTERRUPTED` | User interrupted ongoing speech or thinking. |
| `CANCELLED` | Turn was marked cancelled. |
| `COMPLETED` | Turn completed successfully. |

### Valid Lifecycle Transitions:
- **Normal Turn**: `IDLE` ➔ `LISTENING` ➔ `THINKING` ➔ `SPEAKING` ➔ `COMPLETED` ➔ `IDLE`
- **Interruption**: `SPEAKING` / `THINKING` / `TOOL_RUNNING` ➔ `INTERRUPTED` ➔ `LISTENING` ➔ `THINKING` ➔ `SPEAKING` ➔ `IDLE`

---

## Turn Lifecycle & Turn IDs

Every user utterance creates a unique UUID `turn_id`.

- When Turn A is interrupted by Turn B:
  - Turn A is marked `is_cancelled = True`.
  - `engine.current_turn_id` is updated to Turn B's UUID.
  - Any late-arriving output from Turn A checks `is_current_turn(turn_a_id)`. Since `turn_a` is cancelled and superseded, `is_current_turn` returns `False`, and Turn A's output is **discarded immediately**.
  - Uncommitted conversation context for Turn A is purged.

---

## Component Interfaces

### 1. STT Interface (`STTInterface`)
- `set_on_speech_started(callback)`: Registers callback for instant barge-in detection.
- `set_on_transcript(callback)`: Registers callback for delivering transcribed speech text.
- `listen_and_transcribe()`: Async method capturing microphone audio and returning final transcript.

### 2. LLM Interface (`LLMInterface`)
- `async generate_response(user_input, history)`: Generates text response given current transcript and conversation context. (Uses `LocalTestLLM` for deterministic keyless local test runs or `OpenAILLMService` when configured).

### 3. TTS Interface (`TTSInterface`)
- `async speak(text)`: Synthesizes text and streams WAV audio to hardware speakers.
- `async stop()`: Instantly halts active synthesis, stops `sounddevice` speaker output, and flushes audio buffers.

---

## Event Logging System

Internal events logged for debugging and observability:
- `USER_SPEECH`
- `TURN_STARTED`
- `STATE_CHANGED`
- `INTERRUPTION`
- `TURN_CANCELLED`
- `LLM_STARTED` / `LLM_COMPLETED`
- `TOOL_STARTED` / `TOOL_COMPLETED`
- `STALE_RESPONSE_DISCARDED`
- `TTS_STARTED` / `TTS_STOP` / `TTS_COMPLETED`
- `TURN_COMPLETED`

---

## How to Run Tests & Voice Demo

### 1. Run Automated Pytest Suite
From `backend/`:
```bash
python -m pytest tests/ -v
```

### 2. Run Interruption Engine Verification Demo
From `backend/`:
```bash
python demo_interruption.py
```

### 3. Run Real Microphone Voice Demo
From `backend/`:
```bash
python demo_voice.py
```

To enable verbose internal debugging logs:
```bash
VOICE_DEBUG=1 python demo_voice.py
```

---

## Environment Configuration

Configuration is managed via `app/config.py` and `.env`:
- `LLM_PROVIDER`: Set to `local` (default) or `openai`.
- `WHISPER_MODEL`: Default `base`.
- `STT_LANGUAGE`: Default `en`.
- `RIME_API_KEY`: Set to enable real Rime cloud synthesis (optional).

---

## Known Limitations & Operational Notes
- Local deterministic runs (`LLM_PROVIDER=local`) use `LocalTestLLM` to avoid external API dependencies.
- Hardware speaker stopping relies on `sounddevice.stop()`. If sounddevice is unavailable, hardware audio fallback gracefully handles execution.
