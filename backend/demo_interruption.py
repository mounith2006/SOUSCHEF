import asyncio
import logging
from app.conversation.engine import ConversationEngine
from app.conversation.interfaces import TTSInterface, LLMInterface
from app.conversation.events import EventType, log_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class DemoTTS(TTSInterface):
    def __init__(self):
        self.is_speaking = False
        self.stop_requested = False

    async def speak(self, text: str) -> None:
        self.is_speaking = True
        self.stop_requested = False
        print(f"\n[RIME TTS STARTED SPEAKING]: '{text}'")
        for i in range(1, 6):
            if self.stop_requested:
                print(f"[RIME TTS HARD STOPPED] Audio playback physically aborted at step {i}/5!")
                self.is_speaking = False
                return
            await asyncio.sleep(0.08)
        self.is_speaking = False
        print("[RIME TTS COMPLETED SPEAKING]\n")

    async def stop(self) -> None:
        print("[RIME TTS STOP REQUESTED] Halting audio hardware & flushing buffers...")
        self.stop_requested = True
        self.is_speaking = False

class DemoLLM(LLMInterface):
    async def generate_response(self, user_input: str, history: list) -> str:
        if "Turn A" in user_input or "How long" in user_input:
            # Simulate a slow LLM response for Turn A
            await asyncio.sleep(0.15)
            return "Add two teaspoons of salt and cook the pasta for eight minutes."
        elif "Turn B" in user_input or "how much pasta" in user_input:
            # Fast LLM response for Turn B
            await asyncio.sleep(0.05)
            return "Use 200 grams of pasta per portion."
        return f"Processed input: {user_input}"

async def run_demo():
    print("=" * 80)
    print("       SOUSCHEF CONVERSATION ENGINE - PHASE 2 INTERRUPTION & STALE GUARD DEMO")
    print("=" * 80)

    tts = DemoTTS()
    llm = DemoLLM()
    engine = ConversationEngine(tts=tts, llm=llm)

    # 1. TURN A STARTED
    print("\n--- 1. TURN A STARTED: User asks 'How long should I cook pasta?' ---")
    turn_a_task = asyncio.create_task(engine.handle_user_input("How long should I cook pasta?"))
    
    # Wait until Turn A LLM finishes and Rime TTS starts speaking
    await asyncio.sleep(0.18)
    print(f"Engine State during Turn A speech: {engine.state.value} | Active Turn ID: {engine.current_turn_id}")

    # 2. USER INTERRUPTS WHILE ASSISTANT IS SPEAKING
    print("\n--- 2. USER INTERRUPTS: User speaks 'Wait! How much pasta?' ---")
    # VAD detects speech onset -> triggers interruption flow
    await engine.on_user_speech_started()

    # 3. TURN B STARTED FOR INTERRUPTING SPEECH
    print("\n--- 3. TURN B STARTED: Engine processes new input 'Wait! How much pasta?' ---")
    turn_b_task = asyncio.create_task(engine.handle_user_input("Wait! How much pasta?"))

    await asyncio.gather(turn_a_task, turn_b_task, return_exceptions=True)

    print("\n" + "=" * 80)
    print("                             DEMO SUMMARY")
    print("=" * 80)
    print(f"Final Engine State: {engine.state.value}")
    print(f"Final Active Turn ID: {engine.current_turn_id}")
    print(f"Spoken Responses: {tts.stop_requested}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_demo())
