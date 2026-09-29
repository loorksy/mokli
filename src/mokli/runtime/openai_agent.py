"""OpenAI Agents SDK runtime. Execution goes through Agent and Runner."""

from __future__ import annotations

import time
from typing import Any

from agents import Agent, Runner, set_tracing_disabled
from agents.memory import SQLiteSession
from agents.models.interface import Model
from pydantic import BaseModel

from mokli.runtime.cost import estimate_cost
from mokli.runtime.events import event, from_openai_stream
from mokli.runtime.toolbridge import ToolBridge
from mokli.runtime.types import Capabilities, RunOutcome, UsageRecord

CAPABILITIES = Capabilities(
    streaming=True,
    native_tools=True,
    structured_output=True,
    agent_sdk=True,
    subagents=True,
    handoffs=True,
    sessions=True,
    reasoning=True,
    computer_use=False,
    web_search=False,
    mcp=True,
    background_tasks=False,
    prompt_caching=True,
)


class SnapshotAnswer(BaseModel):
    summary: str


def scripted_tool_model(final_text: str = "Snapshot read. No trade is proposed by the scripted model.") -> Model:
    from agents.testing.model import ScriptedModel
    from agents.usage import Usage
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseOutputText,
    )

    tool_call = ResponseFunctionToolCall(
        arguments="{}",
        call_id="call-gold",
        name="get_gold_price",
        type="function_call",
        id="fc-gold",
        status="completed",
    )
    message = ResponseOutputMessage(
        id="msg-gold",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText(type="output_text", text=final_text, annotations=[])],
    )
    model = ScriptedModel([[tool_call], [message]])
    model.set_default_usage(
        Usage(requests=1, input_tokens=20, output_tokens=8, total_tokens=28)
    )
    return model


async def run_openai_agent(
    prompt: str,
    bridge: ToolBridge,
    *,
    model: Model | str,
    session_id: str,
    agent_id: str,
    parent_agent_id: str = "",
    instructions: str = "You are Mokli. Call get_gold_price before you answer. Do not invent prices.",
    session_path: str | None = None,
    output_type: type[BaseModel] | None = None,
    handoffs: list[Any] | None = None,
    stream: bool = True,
) -> RunOutcome:
    set_tracing_disabled(True)
    started = time.perf_counter()
    events = [event("agent_started", agent_id=agent_id, provider="openai")]
    session = SQLiteSession(session_id, session_path or ":memory:")
    agent = Agent(
        name="Mokli",
        instructions=instructions,
        tools=bridge.openai_tools(),
        model=model,
        handoffs=handoffs or [],
        output_type=output_type,
    )
    usage = UsageRecord()
    text = ""
    status = "completed"
    try:
        if stream:
            streamed = Runner.run_streamed(agent, prompt, session=session)
            async for item in streamed.stream_events():
                events.extend(from_openai_stream(item))
            text = str(streamed.final_output)
            raw_usage = streamed.context_wrapper.usage
        else:
            result = await Runner.run(agent, prompt, session=session)
            text = str(result.final_output)
            raw_usage = result.context_wrapper.usage
            events.append(event("agent_message_completed", text=text))
        usage.input_tokens = int(raw_usage.input_tokens)
        usage.output_tokens = int(raw_usage.output_tokens)
        usage.cached_tokens = int(getattr(raw_usage.input_tokens_details, "cached_tokens", 0) or 0)
    except Exception as exc:
        status = "failed"
        events.append(event("agent_failed", detail=str(exc)))
        raise
    usage.estimated_cost = estimate_cost("gpt-4.1", usage.input_tokens, usage.output_tokens)
    events.append(event("usage_updated", input_tokens=usage.input_tokens, output_tokens=usage.output_tokens))
    return RunOutcome(
        text=text,
        provider="openai",
        model=model if isinstance(model, str) else "scripted",
        runtime="openai_agents_sdk",
        sdk="openai-agents",
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        session_id=session_id,
        status=status,
        tools=[tool.name for tool in bridge.exposed()],
        events=events,
        usage=usage,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=len(bridge.calls),
        display_provider="OpenAI",
        display_model=model if isinstance(model, str) else "scripted",
        display_runtime="OpenAI Agents SDK",
    )
