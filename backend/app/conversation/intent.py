import re
from typing import Optional, Tuple
from enum import Enum

class Intent(Enum):
    START_RECIPE = "START_RECIPE"
    GET_RECIPE = "GET_RECIPE"
    NEXT_STEP = "NEXT_STEP"
    REPEAT_STEP = "REPEAT_STEP"
    CURRENT_STEP = "CURRENT_STEP"
    UNKNOWN = "UNKNOWN"

def detect_intent(text: str) -> Tuple[Intent, Optional[str]]:
    """
    Deterministically route natural language text to a recipe intent.
    Returns a tuple of (Intent, optional_recipe_name_or_query).
    """
    text = text.lower().strip()
    
    # 1. REPEAT_STEP
    repeat_patterns = [
        r"\brepeat that\b",
        r"\brepeat the step\b",
        r"\brepeat\b",
        r"\bwhat was that\b",
        r"\bsay that again\b"
    ]
    for p in repeat_patterns:
        if re.search(p, text):
            return Intent.REPEAT_STEP, None
            
    # 2. CURRENT_STEP
    current_patterns = [
        r"\bwhere are we\b",
        r"\bwhat step are we on\b",
        r"\bwhat am i doing\b",
        r"\bcurrent step\b"
    ]
    for p in current_patterns:
        if re.search(p, text):
            return Intent.CURRENT_STEP, None
            
    # 3. NEXT_STEP
    next_patterns = [
        r"\bwhat's next\b",
        r"\bwhat is next\b",
        r"\bwhat do i do next\b",
        r"\bnext step\b",
        r"\bcontinue\b",
        r"\bnext\b"
    ]
    for p in next_patterns:
        if re.search(p, text):
            return Intent.NEXT_STEP, None

    # 4. START_RECIPE
    start_patterns = [
        r"^(?:let's\s+|i want to\s+|can we\s+|please\s+)?cook\s+(.+)",
        r"^(?:let's\s+|i want to\s+|can we\s+|please\s+)?make\s+(.+)",
        r"^(?:let's\s+|i want to\s+|can we\s+|please\s+)?prepare\s+(.+)",
        r"^(?:let's\s+|i want to\s+|can we\s+|please\s+)?start\s+(.+)"
    ]
    for p in start_patterns:
        match = re.search(p, text)
        if match:
            # e.g., "let's make chicken pasta" -> "chicken pasta"
            recipe_query = match.group(1).replace("recipe", "").strip()
            return Intent.START_RECIPE, recipe_query

    # 5. GET_RECIPE
    get_patterns = [
        r"\brecipe for\s+(.+)",
        r"\bgive me a\s+(.+)\s+recipe\b",
        r"\bhow do i make\s+(.+)",
        r"\bhow to make\s+(.+)"
    ]
    for p in get_patterns:
        match = re.search(p, text)
        if match:
            recipe_query = match.group(1).replace("recipe", "").strip()
            return Intent.GET_RECIPE, recipe_query

    return Intent.UNKNOWN, None
