import pytest
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

# Bypass PyTorch DLL crash on this environment during collection
sys.modules['whisper'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

from app.services.recipe_service import RecipeService
from app.tools.recipe_tools import RecipeToolRunner
from app.conversation.engine import ConversationEngine
from app.conversation.context import ConversationContext
from app.conversation.state import ConversationState
from app.services.llm_service import LocalTestLLM
from app.conversation.interfaces import TTSInterface, STTInterface

# Test A & B: Recipe lookup and start recipe
@pytest.mark.asyncio
async def test_find_and_start_recipe():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )

    turn = await engine.handle_user_input("let's make chicken pasta")
    
    assert engine.context.active_recipe == "Chicken Pasta"
    assert engine.context.active_step == 0
    assert "Let's make Chicken Pasta" in turn.response_text
    
# Test C: Next step
@pytest.mark.asyncio
async def test_next_step():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )
    
    # Start recipe
    await engine.handle_user_input("cook pancakes")
    assert engine.context.active_step == 0
    
    # Next step
    turn = await engine.handle_user_input("what do I do next?")
    assert engine.context.active_step == 1
    assert "Next," in turn.response_text
    
# Test D: Repeat
@pytest.mark.asyncio
async def test_repeat_step():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )
    
    # Start
    await engine.handle_user_input("make carbonara")
    assert engine.context.active_step == 0
    
    # Repeat
    turn = await engine.handle_user_input("repeat the step")
    assert engine.context.active_step == 0
    assert "Next, boil the spaghetti" in turn.response_text # step 0 text

# Test E: Context retention across turns
@pytest.mark.asyncio
async def test_context_retention():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )
    
    await engine.handle_user_input("make chicken pasta")
    await engine.handle_user_input("next")
    
    assert engine.context.active_recipe == "Chicken Pasta"
    assert engine.context.active_step == 1
    
    # unrelated question
    turn = await engine.handle_user_input("how long do I cook pasta")
    assert "For most pasta" in turn.response_text
    assert engine.context.active_step == 1 # unchanged
    
    turn2 = await engine.handle_user_input("next step")
    assert engine.context.active_step == 2
    
# Test F & G: Tool Integration and Local LLM fallback
@pytest.mark.asyncio
async def test_local_llm_fallback():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )
    
    turn = await engine.handle_user_input("tell me a joke")
    assert "I heard 'tell me a joke'. This is a local test response." in turn.response_text

@pytest.mark.asyncio
async def test_tool_runner_is_connected():
    from app.services.conversation_service import get_conversation_engine, _manager
    _manager.clear_session("test_session_tools")
    
    engine = get_conversation_engine("test_session_tools")
    assert engine.tool_runner is not None
    assert "RecipeToolRunner" in engine.tool_runner.__class__.__name__

@pytest.mark.asyncio
async def test_completion():
    tts = AsyncMock(spec=TTSInterface)
    llm = LocalTestLLM()
    tool_runner = RecipeToolRunner()
    
    engine = ConversationEngine(
        tts=tts,
        llm=llm,
        stt=None,
        tool_runner=tool_runner
    )
    
    # Pancakes has 6 steps (0-5)
    await engine.handle_user_input("make pancakes")
    for _ in range(5):
        await engine.handle_user_input("next")
        
    assert engine.context.active_step == 5
    
    turn = await engine.handle_user_input("next")
    assert "You have completed all the steps" in turn.response_text
