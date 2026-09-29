"""OpenAI Agents SDK path. The SDK owns the tool loop. Mokli tools stay behind the bridge."""

from __future__ import annotations

from agents import Agent, Runner, function_tool, set_tracing_disabled
from agents.models.interface import Model


async def run_with_snapshot_tool(
    prompt: str,
    snapshot_text: str,
    *,
    model: Model | str | None = None,
    instructions: str = "You are Mokli. Call gold_snapshot before you answer. Do not invent prices.",
) -> tuple[str, int]:
    set_tracing_disabled(True)
    calls = {"count": 0}

    @function_tool
    def gold_snapshot() -> str:
        """Return the deterministic XAUUSD snapshot already computed by Mokli."""
        calls["count"] += 1
        return snapshot_text

    if model is None:
        model = _scripted_model()
    agent = Agent(
        name="Mokli",
        instructions=instructions,
        tools=[gold_snapshot],
        model=model,
    )
    result = await Runner.run(agent, prompt)
    return str(result.final_output), calls["count"]


def _scripted_model() -> Model:
    from agents.testing.model import ScriptedModel
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseOutputText,
    )

    tool_call = ResponseFunctionToolCall(
        arguments="{}",
        call_id="call-gold",
        name="gold_snapshot",
        type="function_call",
        id="fc-gold",
        status="completed",
    )
    message = ResponseOutputMessage(
        id="msg-gold",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText(type="output_text", text="Snapshot read. No trade is proposed by the scripted model.", annotations=[])],
    )
    return ScriptedModel([[tool_call], [message]])


def live_model(name: str) -> str:
    return name
