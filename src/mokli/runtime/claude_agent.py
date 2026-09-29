"""Claude Agent SDK runtime. Live runs use query(); tests inject a Transport."""

from __future__ import annotations

import time
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    Transport,
    query,
)

from mokli.runtime.cost import estimate_cost
from mokli.runtime.events import event, from_claude_message
from mokli.runtime.toolbridge import ToolBridge
from mokli.runtime.types import Capabilities, RunOutcome, UsageRecord

CAPABILITIES = Capabilities(
    streaming=True,
    native_tools=True,
    structured_output=True,
    agent_sdk=True,
    subagents=True,
    handoffs=False,
    sessions=True,
    reasoning=True,
    computer_use=False,
    web_search=False,
    mcp=True,
    background_tasks=False,
    prompt_caching=True,
)


async def run_claude_agent(
    prompt: str,
    bridge: ToolBridge,
    *,
    model: str,
    session_id: str,
    agent_id: str,
    parent_agent_id: str = "",
    transport: Transport | None = None,
    workspace: Path | None = None,
    subagent_prompt: str | None = None,
) -> RunOutcome:
    started = time.perf_counter()
    events = [event("agent_started", agent_id=agent_id, provider="anthropic")]
    agents = None
    if subagent_prompt:
        agents = {
            "research": AgentDefinition(
                description="Read-only XAUUSD research sub-agent.",
                prompt=subagent_prompt,
                tools=["mcp__mokli__get_gold_price"],
                model="inherit",
            )
        }
        events.append(event("subagent_started", agent="research", native=True))
    options = ClaudeAgentOptions(
        model=model,
        system_prompt="You are Mokli. Use get_gold_price. Do not invent prices or place orders.",
        mcp_servers={"mokli": bridge.claude_server()},  # type: ignore[dict-item]
        allowed_tools=["mcp__mokli__get_gold_price"],
        disallowed_tools=["Bash", "Read", "Write", "Edit", "WebSearch", "WebFetch", "Agent"],
        cwd=workspace,
        include_partial_messages=True,
        resume=session_id or None,
        max_turns=4,
        agents=agents,
        permission_mode="dontAsk",
    )
    text = ""
    usage = UsageRecord()
    cost = 0.0
    async for message in query(prompt=prompt, options=options, transport=transport):
        events.extend(from_claude_message(message))
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text
            if message.usage:
                usage.input_tokens = int(message.usage.get("input_tokens") or usage.input_tokens)
                usage.output_tokens = int(message.usage.get("output_tokens") or usage.output_tokens)
                usage.cached_tokens = int(message.usage.get("cache_read_input_tokens") or 0)
        if isinstance(message, ResultMessage):
            text = message.result or text
            if message.usage:
                usage.input_tokens = int(message.usage.get("input_tokens") or 0)
                usage.output_tokens = int(message.usage.get("output_tokens") or 0)
                usage.cached_tokens = int(message.usage.get("cache_read_input_tokens") or 0)
            cost = float(message.total_cost_usd or 0)
            if message.is_error:
                events.append(event("agent_failed", detail=message.subtype))
    if subagent_prompt:
        events.append(event("subagent_completed", agent="research"))
    usage.estimated_cost = cost or estimate_cost(model, usage.input_tokens, usage.output_tokens)
    return RunOutcome(
        text=text,
        provider="anthropic",
        model=model,
        runtime="claude_agent_sdk",
        sdk="claude-agent-sdk",
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        session_id=session_id,
        status="completed" if text else "failed",
        tools=[tool.name for tool in bridge.exposed()],
        events=events,
        usage=usage,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=len(bridge.calls),
        subagents=1 if subagent_prompt else 0,
        display_provider="Anthropic",
        display_model=model,
        display_runtime="Claude Agent SDK",
    )


async def interrupt_claude(transport: Transport) -> None:
    """Cancellation is ClaudeSDKClient.interrupt(). query() cannot interrupt."""
    options = ClaudeAgentOptions(model="claude-sonnet-4-5")
    client = ClaudeSDKClient(options=options, transport=transport)
    await client.connect()
    await client.interrupt()
    await client.disconnect()
