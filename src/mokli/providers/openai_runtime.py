"""OpenAI Agents SDK path. The SDK owns the tool loop. Mokli tools stay behind the bridge."""

from __future__ import annotations

from agents.models.interface import Model

from mokli.runtime.openai_agent import run_openai_agent, scripted_tool_model
from mokli.runtime.toolbridge import ToolBridge, gold_price_tool


async def run_with_snapshot_tool(
    prompt: str,
    snapshot_text: str,
    *,
    model: Model | str | None = None,
    instructions: str = "You are Mokli. Call get_gold_price before you answer. Do not invent prices.",
) -> tuple[str, int]:
    bridge = ToolBridge()
    bridge.register(gold_price_tool(lambda: snapshot_text))
    outcome = await run_openai_agent(
        prompt,
        bridge,
        model=model if model is not None else scripted_tool_model(),
        session_id="openai-snapshot",
        agent_id="openai-snapshot",
        instructions=instructions,
        stream=False,
    )
    return outcome.text, outcome.tool_calls


def live_model(name: str) -> str:
    return name
