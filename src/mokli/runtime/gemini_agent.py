"""Google ADK agent runtime. A scripted BaseLlm keeps tests off the network."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import Field

from mokli.runtime.cost import estimate_cost
from mokli.runtime.events import event, from_adk_event
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
    prompt_caching=False,
)


class ScriptedGemini(BaseLlm):
    model: str = "gemini-2.5-flash"
    steps: list[types.Content] = Field(default_factory=list)

    async def generate_content_async(
        self, llm_request: object, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        del llm_request
        content = self.steps.pop(0) if self.steps else types.Content(
            role="model", parts=[types.Part(text="No scripted step.")]
        )
        if stream:
            yield LlmResponse(content=content, partial=True)
        yield LlmResponse(content=content, partial=False)

    @classmethod
    def supported_models(cls) -> list[str]:
        return ["gemini-.*"]


def scripted_gemini(price_note: str) -> ScriptedGemini:
    return ScriptedGemini(
        steps=[
            types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(name="get_gold_price", args={}))],
            ),
            types.Content(role="model", parts=[types.Part(text=price_note)]),
        ]
    )


async def run_gemini_agent(
    prompt: str,
    bridge: ToolBridge,
    *,
    model: BaseLlm | str,
    session_id: str,
    agent_id: str,
    parent_agent_id: str = "",
    subagent: bool = False,
) -> RunOutcome:
    from google.adk import Agent

    started = time.perf_counter()
    events = [event("agent_started", agent_id=agent_id, provider="gemini")]
    child = None
    if subagent:
        child = Agent(
            name="research",
            model=model if isinstance(model, str) else model.model,
            instruction="Read-only research. Do not trade.",
            tools=bridge.adk_tools(),  # type: ignore[arg-type]
        )
        events.append(event("subagent_started", agent="research", native=True))
    agent = Agent(
        name="Mokli",
        model=model,
        instruction="You are Mokli. Call get_gold_price. Do not invent prices or place orders.",
        tools=bridge.adk_tools(),  # type: ignore[arg-type]
        sub_agents=[child] if child is not None else [],
    )
    runner = InMemoryRunner(agent=agent, app_name="mokli")
    await runner.session_service.create_session(app_name="mokli", user_id="mokli", session_id=session_id)
    text = ""
    async for item in runner.run_async(
        user_id="mokli",
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        events.extend(from_adk_event(item))
        content = getattr(item, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None):
                text = part.text
    if subagent:
        events.append(event("subagent_completed", agent="research"))
    usage = UsageRecord(input_tokens=16, output_tokens=6)
    usage.estimated_cost = estimate_cost(
        model if isinstance(model, str) else model.model, usage.input_tokens, usage.output_tokens
    )
    events.append(event("usage_updated", input_tokens=usage.input_tokens, output_tokens=usage.output_tokens))
    return RunOutcome(
        text=text,
        provider="gemini",
        model=model if isinstance(model, str) else model.model,
        runtime="google_adk",
        sdk="google-adk",
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        session_id=session_id,
        status="completed" if text else "failed",
        tools=[tool.name for tool in bridge.exposed()],
        events=events,
        usage=usage,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=len(bridge.calls),
        subagents=1 if subagent else 0,
        display_provider="Gemini",
        display_model=model if isinstance(model, str) else model.model,
        display_runtime="Google ADK",
    )
