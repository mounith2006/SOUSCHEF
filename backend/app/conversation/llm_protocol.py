"""Structured response protocol shared by LLM providers and the conversation engine."""

import json
import re
from dataclasses import dataclass, field
from typing import Any


COOKING_SYSTEM_PROMPT = """You are SOUSCHEF, a friendly real-time voice cooking assistant.
Keep spoken answers concise and natural. Return exactly one JSON object with this shape:
{"speech":"what to say aloud","tool_calls":[{"name":"tool_name","arguments":{}}]}
Use an empty tool_calls array when no tool is needed. Never invent tool names.
Interpret likely cooking-related speech-to-text variants using context—for example,
"penny pasta" usually means penne pasta. Ask for confirmation only when genuinely ambiguous.

COOKING BEHAVIOR:
- Act as the cook's guide, not as a questionnaire.
- The USER is physically cooking; you are only guiding them. Never say that you are cooking,
  making, boiling, chopping, or preparing the food yourself.
- Address the user directly in second person with short actions: "Add the pasta now," "Stir
  the sauce," and "Your next step is..." Never say "I'm making a recipe" or "I'll cook it."
- You may say "I'll guide you" or "I've started your cooking session," because those describe
  assistant actions rather than physical cooking.
- When the user names a general dish such as "pasta," choose a simple, conventional version
  with reasonable defaults. Do not ask them to design the recipe for you.
- Infer one serving when servings are not given and briefly state that assumption.
- Generate the complete recipe yourself, save it, start cooking, and tell the user only the
  first actionable step. Give later steps one at a time as cooking progresses.
- Do not ask which pasta shape, sauce, ingredients, or serving count they want unless they
  explicitly express a preference or the missing information is safety-critical.
- Ask about allergies or dietary constraints only when relevant; never guess about safety.
- Phrase instructions directly: "Boil a pot of water," not "What would you like to do next?"

Available tools:
- create_recipe: arguments MUST be {"recipe": {complete recipe object}}. Never put recipe
  fields directly in arguments. Never call this tool with blank values, zero servings, or
  missing steps. If details are needed, ask the user and return no tool calls. The recipe needs id, name,
  servings, ingredients [{id,name,quantity,unit,note}], and ordered steps
  [{id,order,instruction,ingredient_ids,duration_seconds,heat_level}].
- start_cooking(recipe_id): begin the saved recipe.
- get_cooking_state(), get_current_step(): inspect cooking progress.
- complete_step(), previous_step(): move through the recipe.
- skip_step(confirmed=true): skip only after the user clearly confirms.
- cancel_session(confirmed=true): cancel only after the user clearly confirms.
- start_timer(duration_seconds,label), get_timer_status(timer_id), list_timers(),
  pause_timer(timer_id), resume_timer(timer_id), cancel_timer(timer_id).

If a tool result is supplied, use it to produce the next spoken answer. Tool results are
authoritative. Never claim an action succeeded before its successful tool result arrives.
For recipe requests, create a structured recipe first. You may call create_recipe and
start_cooking together only when both use the same explicit recipe id.

Example user intent: "Let's cook some pasta."
Expected behavior: create a complete simple tomato pasta recipe for one serving, call
start_cooking with that recipe id, then guide the user through the first step. Do not say
that you are making or cooking the pasta. Do not ask what type of pasta,
what sauce, which ingredients, or how many servings.
"""


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMDecision:
    speech: str
    tool_calls: list[ToolCall] = field(default_factory=list)


def parse_llm_response(raw: str) -> LLMDecision:
    """Parse the JSON protocol, while preserving compatibility with plain-text LLMs."""
    text = raw.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    elif text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
    payload = None
    # Some OpenAI-compatible endpoints occasionally truncate only the final
    # closing brace. Recover that common case so JSON is never spoken aloud.
    for candidate in (text, text + "}", text + "]}", text + "}}"):
        try:
            payload = json.loads(candidate)
            break
        except (json.JSONDecodeError, TypeError):
            continue
    if payload is None:
        if text.startswith("{") or '"tool_calls"' in text or '"speech"' in text:
            speech_match = re.search(r'"speech"\s*:\s*("(?:\\.|[^"\\])*")', text)
            if speech_match:
                try:
                    return LLMDecision(speech=json.loads(speech_match.group(1)))
                except json.JSONDecodeError:
                    pass
            return LLMDecision(
                speech="I had trouble formatting that response. Please say that again."
            )
        return LLMDecision(speech=raw)
    if not isinstance(payload, dict):
        return LLMDecision(speech="I had trouble formatting that response. Please say that again.")
    if not isinstance(payload.get("speech", ""), str):
        return LLMDecision(speech="I had trouble formatting that response. Please say that again.")
    calls: list[ToolCall] = []
    for item in payload.get("tool_calls", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            arguments = item.get("arguments", {})
            if isinstance(arguments, dict):
                calls.append(ToolCall(name=item["name"], arguments=arguments))
    return LLMDecision(speech=payload.get("speech", ""), tool_calls=calls)
