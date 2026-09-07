import asyncio
import unittest
from app.conversation.engine import ConversationEngine
from app.conversation.state import ConversationState
from app.conversation.turn import Turn
from app.conversation.context import ConversationContext
from app.conversation.interfaces import TTSInterface, LLMInterface, ToolInterface
from app.services.conversation_service import SessionConversationManager

class MockTTS(TTSInterface):
    def __init__(self, speak_delay: float = 0.0, should_fail: bool = False):
        self.speak_delay = speak_delay
        self.should_fail = should_fail
        self.spoken_texts = []
        self.stop_called_count = 0

    async def speak(self, text: str) -> None:
        if self.should_fail:
            raise RuntimeError("Simulated TTS audio failure")
        if self.speak_delay > 0:
            await asyncio.sleep(self.speak_delay)
        self.spoken_texts.append(text)

    async def stop(self) -> None:
        self.stop_called_count += 1


class MockLLM(LLMInterface):
    def __init__(self, delay: float = 0.0, should_fail: bool = False, responses: dict = None):
        self.delay = delay
        self.should_fail = should_fail
        self.responses = responses or {}
        self.calls = []

    async def generate_response(self, user_input: str, conversation_history: list) -> str:
        self.calls.append((user_input, conversation_history))
        if self.should_fail:
            raise RuntimeError("Simulated LLM API failure")
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return self.responses.get(user_input, f"Response for '{user_input}'")


class MockToolRunner(ToolInterface):
    def __init__(self, delay: float = 0.0, should_fail: bool = False):
        self.delay = delay
        self.should_fail = should_fail
        self.tool_calls = []

    async def execute_tool(self, tool_name: str, tool_args: dict) -> str:
        self.tool_calls.append((tool_name, tool_args))
        if self.should_fail:
            raise RuntimeError("Simulated Tool failure")
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return f"Tool {tool_name} executed"


class TestConversationEnginePhase2(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.tts = MockTTS()
        self.llm = MockLLM()
        self.context = ConversationContext()
        self.tool_runner = MockToolRunner()
        self.engine = ConversationEngine(
            tts=self.tts,
            llm=self.llm,
            tool_runner=self.tool_runner,
            context=self.context,
            session_id="test_session"
        )

    # 1. Normal turn
    async def test_01_normal_turn(self):
        turn = await self.engine.handle_user_input("How long should I cook pasta?")
        self.assertIsNotNone(turn)
        self.assertEqual(turn.response_text, "Response for 'How long should I cook pasta?'")
        self.assertEqual(self.tts.spoken_texts, ["Response for 'How long should I cook pasta?'"])
        self.assertEqual(self.engine.state, ConversationState.IDLE)

    # 2. Speaking interruption
    async def test_02_speaking_interruption(self):
        self.tts.speak_delay = 0.2
        self.llm.delay = 0.01

        task_a = asyncio.create_task(self.engine.handle_user_input("First turn"))
        await asyncio.sleep(0.05)

        # User interrupts while assistant is speaking
        await self.engine.interrupt()
        turn_b = await self.engine.handle_user_input("Second turn")
        await task_a

        self.assertIn("Response for 'Second turn'", self.tts.spoken_texts)

    # 3. TTS stop called
    async def test_03_tts_stop_called(self):
        self.tts.speak_delay = 0.2
        task = asyncio.create_task(self.engine.handle_user_input("Question"))
        await asyncio.sleep(0.05)

        await self.engine.interrupt()
        await task
        self.assertGreater(self.tts.stop_called_count, 0)

    # 4. Old turn cancelled
    async def test_04_old_turn_cancelled(self):
        self.llm.delay = 0.2
        task_a = asyncio.create_task(self.engine.handle_user_input("Turn A"))
        await asyncio.sleep(0.02)
        turn_a = self.engine.current_turn

        await self.engine.interrupt()
        await task_a

        self.assertTrue(turn_a.is_cancelled)
        self.assertEqual(turn_a.state, ConversationState.CANCELLED)

    # 5. New turn created
    async def test_05_new_turn_created(self):
        turn_a = await self.engine.handle_user_input("Turn A")
        turn_b = await self.engine.handle_user_input("Turn B")

        self.assertIsNotNone(turn_a.turn_id)
        self.assertIsNotNone(turn_b.turn_id)
        self.assertNotEqual(turn_a.turn_id, turn_b.turn_id)

    # 6. Old response discarded
    async def test_06_old_response_discarded(self):
        async def delayed_llm(user_input, history):
            if user_input == "Slow A":
                await asyncio.sleep(0.2)
                return "Slow Response A"
            return "Fast Response B"

        self.llm.generate_response = delayed_llm

        task_a = asyncio.create_task(self.engine.handle_user_input("Slow A"))
        await asyncio.sleep(0.02)
        task_b = asyncio.create_task(self.engine.handle_user_input("Fast B"))

        await asyncio.gather(task_a, task_b)

        self.assertIn("Fast Response B", self.tts.spoken_texts)
        self.assertNotIn("Slow Response A", self.tts.spoken_texts)

    # 7. New response spoken
    async def test_07_new_response_spoken(self):
        turn = await self.engine.handle_user_input("Hello Chef")
        self.assertIn("Response for 'Hello Chef'", self.tts.spoken_texts)

    # 8. LLM task cancellation
    async def test_08_llm_task_cancellation(self):
        self.llm.delay = 0.2
        task = asyncio.create_task(self.engine.handle_user_input("Slow LLM"))
        await asyncio.sleep(0.02)
        
        turn = self.engine.current_turn
        await self.engine.cancel_current_turn("Test cancellation")
        await task

        self.assertTrue(turn.is_cancelled)
        self.assertEqual(self.tts.spoken_texts, [])

    # 9. Tool task cancellation/invalidation
    async def test_09_tool_task_cancellation(self):
        self.tool_runner.delay = 0.2
        turn = Turn(user_input="Set timer", turn_id="tool_turn_1")
        self.engine._current_turn = turn

        tool_task = asyncio.create_task(self.engine.execute_tool_task(turn, "set_timer", {"duration": 500}))
        await asyncio.sleep(0.02)

        await self.engine.cancel_current_turn("User changed mind")
        try:
            res = await tool_task
        except asyncio.CancelledError:
            res = None

        self.assertTrue(turn.is_cancelled)
        self.assertIsNone(res)

    # 10. Rapid interruption
    async def test_10_rapid_interruption(self):
        self.llm.delay = 0.05
        tasks = []
        for i in range(5):
            tasks.append(asyncio.create_task(self.engine.handle_user_input(f"Query {i}")))
            await asyncio.sleep(0.01)

        await asyncio.gather(*tasks, return_exceptions=True)
        self.assertEqual(len(self.tts.spoken_texts), 1)
        self.assertEqual(self.tts.spoken_texts[0], "Response for 'Query 4'")

    # 11. Context retained
    async def test_11_context_retained(self):
        await self.engine.handle_user_input("Boil water")
        await self.engine.handle_user_input("Add pasta")

        msgs = self.context.get_messages()
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[0]["content"], "Boil water")
        self.assertEqual(msgs[2]["content"], "Add pasta")

    # 12. Cancelled turn does not modify context incorrectly
    async def test_12_cancelled_turn_context_purged(self):
        self.llm.delay = 0.1
        task = asyncio.create_task(self.engine.handle_user_input("Cancelled turn text"))
        await asyncio.sleep(0.02)

        turn = self.engine.current_turn
        await self.engine.cancel_current_turn("Purge test")
        await task

        msgs = self.context.get_messages()
        # Verify messages for the cancelled turn were purged
        turn_msgs = [m for m in msgs if m.get("content") == "Cancelled turn text"]
        self.assertEqual(len(turn_msgs), 0)

    # 13. TTS failure handling
    async def test_13_tts_failure_handling(self):
        self.tts.should_fail = True
        turn = await self.engine.handle_user_input("TTS Failure Test")

        # Engine should reset state safely to IDLE without crashing unhandled
        self.assertEqual(self.engine.state, ConversationState.IDLE)

    # 14. LLM failure handling
    async def test_14_llm_failure_handling(self):
        self.llm.should_fail = True
        turn = await self.engine.handle_user_input("LLM Failure Test")

        # Engine should recover safely to IDLE
        self.assertEqual(self.engine.state, ConversationState.IDLE)

    # 15. Tool failure handling
    async def test_15_tool_failure_handling(self):
        self.tool_runner.should_fail = True
        turn = Turn(user_input="Run broken tool", turn_id="err_tool_turn")
        self.engine._current_turn = turn

        res = await self.engine.execute_tool_task(turn, "broken_tool", {})
        self.assertIsNone(res)

    # 16. Repeated interruption
    async def test_16_repeated_interruption(self):
        self.tts.speak_delay = 0.2
        task = asyncio.create_task(self.engine.handle_user_input("Question"))
        await asyncio.sleep(0.02)

        # Trigger repeated interruptions
        await self.engine.interrupt()
        await self.engine.interrupt()
        await self.engine.interrupt()

        await task
        self.assertGreaterEqual(self.tts.stop_called_count, 1)

    # 17. Response arriving exactly around cancellation
    async def test_17_response_arriving_around_cancellation(self):
        self.llm.delay = 0.05
        task = asyncio.create_task(self.engine.handle_user_input("Edge case"))
        await asyncio.sleep(0.049)  # Right before LLM returns

        turn = self.engine.current_turn
        turn.cancel()
        await task

        self.assertEqual(self.tts.spoken_texts, [])

    # 18. Multiple concurrent sessions (Session isolation test)
    async def test_18_multi_session_isolation(self):
        manager = SessionConversationManager()
        engine_a = manager.get_engine_for_session("session_a", tts=MockTTS(), llm=MockLLM())
        engine_b = manager.get_engine_for_session("session_b", tts=MockTTS(), llm=MockLLM())

        turn_a = await engine_a.handle_user_input("Session A message")
        turn_b = await engine_b.handle_user_input("Session B message")

        self.assertNotEqual(engine_a.session_id, engine_b.session_id)
        self.assertNotEqual(turn_a.turn_id, turn_b.turn_id)
        
        # Interrupt Session A; Session B must remain unaffected
        await engine_a.interrupt()
        self.assertEqual(engine_b.state, ConversationState.IDLE)


if __name__ == "__main__":
    unittest.main()
