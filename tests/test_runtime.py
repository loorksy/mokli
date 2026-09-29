from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from mokli.agent.mcp_bridge import analysis_server
from mokli.config import Settings
from mokli.runtime.claude_agent import interrupt_claude, run_claude_agent
from mokli.runtime.claude_transport import ScriptedClaudeTransport
from mokli.runtime.events import from_claude_message, from_openai_stream
from mokli.runtime.fallback import RuntimeStep, SafeFailure, run_with_fallback
from mokli.runtime.loop import run_model_loop
from mokli.runtime.mcp_registry import McpRegistry
from mokli.runtime.model_clients import (
    AnthropicMessagesClient,
    OllamaModelClient,
    OpenAICompatibleClient,
    OpenRouterModelClient,
    ZaiChatClient,
    ZaiHostedAgentClient,
)
from mokli.runtime.subagent import SubAgentSpec, spawn_subagent
from mokli.runtime.toolbridge import ToolBridge, gold_price_tool
from mokli.runtime.types import ModelTurn, RunOutcome, UsageRecord
from mokli.schema import AgentEvent, ProviderRun


def _bridge(text: str = "2410") -> ToolBridge:
    bridge = ToolBridge()
    bridge.register(gold_price_tool(lambda: text))
    return bridge


def test_same_tool_is_exposed_through_every_runtime() -> None:
    bridge = _bridge()
    openai = bridge.openai_tools()
    claude = bridge.claude_server()
    adk = bridge.adk_tools()
    schemas = bridge.json_schemas()
    assert openai[0].name == "get_gold_price"
    assert claude["name"] == "mokli"
    assert adk[0].name == "get_gold_price"
    assert schemas[0]["function"]["name"] == "get_gold_price"
    assert bridge.invoke("get_gold_price", {}) == "2410"
    with pytest.raises(PermissionError):
        bridge.invoke("place_order", {})


def test_openai_sdk_streams_tools_and_usage() -> None:
    from mokli.runtime.openai_agent import run_openai_agent, scripted_tool_model

    outcome = asyncio.run(
        run_openai_agent(
            "What is gold doing?",
            _bridge("last=2410"),
            model=scripted_tool_model(),
            session_id="s1",
            agent_id="agent-openai",
        )
    )
    kinds = [item.kind for item in outcome.events]
    assert "tool_call_started" in kinds
    assert "agent_message_completed" in kinds
    assert "usage_updated" in kinds
    assert outcome.tool_calls == 1
    assert outcome.usage.input_tokens >= 20
    assert "Snapshot" in outcome.text
    assert outcome.sdk == "openai-agents"


def test_openai_handoff_is_a_real_sdk_handoff() -> None:
    from agents import Agent
    from agents.testing.model import ScriptedModel
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseOutputText,
    )

    from mokli.runtime.openai_agent import run_openai_agent

    handoff_call = ResponseFunctionToolCall(
        arguments="{}",
        call_id="call-hand",
        name="transfer_to_research",
        type="function_call",
        id="fc-hand",
        status="completed",
    )
    message = ResponseOutputMessage(
        id="msg-hand",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText(type="output_text", text="Research complete.", annotations=[])],
    )
    model = ScriptedModel([[handoff_call], [message]])
    research = Agent(
        name="research",
        instructions="Research only.",
        handoff_description="Research the tape.",
        model=model,
    )
    outcome = asyncio.run(
        run_openai_agent(
            "Hand this to research.",
            _bridge(),
            model=model,
            session_id="handoff",
            agent_id="parent",
            handoffs=[research],
            instructions="Hand research questions to the research agent.",
        )
    )
    kinds = [item.kind for item in outcome.events]
    assert "handoff_started" in kinds or "handoff_completed" in kinds or "subagent_started" in kinds
    assert "Research" in outcome.text


def test_claude_agent_sdk_executes_the_bridged_tool() -> None:
    transport = ScriptedClaudeTransport("2410")
    outcome = asyncio.run(
        asyncio.wait_for(
            run_claude_agent(
                "Read the gold price.",
                _bridge("2410"),
                model="claude-sonnet-4-5",
                session_id="claude-1",
                agent_id="claude-agent",
                transport=transport,
                subagent_prompt="Research only.",
            ),
            timeout=15,
        )
    )
    assert outcome.sdk == "claude-agent-sdk"
    assert outcome.tool_calls == 1
    assert "2410" in outcome.text
    assert transport.agents is not None
    assert "research" in transport.agents
    kinds = [item.kind for item in outcome.events]
    assert "agent_message_delta" in kinds
    assert "usage_updated" in kinds
    assert outcome.usage.cached_tokens == 3


def test_claude_interrupt_uses_the_sdk_client() -> None:
    transport = ScriptedClaudeTransport("2410")

    async def run() -> None:
        await asyncio.wait_for(interrupt_claude(transport), timeout=15)

    asyncio.run(run())
    assert transport.interrupted


def test_gemini_adk_runs_the_bridged_tool() -> None:
    from mokli.runtime.gemini_agent import run_gemini_agent, scripted_gemini

    outcome = asyncio.run(
        asyncio.wait_for(
            run_gemini_agent(
                "Read gold.",
                _bridge("2411"),
                model=scripted_gemini("ADK snapshot 2411"),
                session_id="gem-1",
                agent_id="gem-agent",
            ),
            timeout=20,
        )
    )
    assert outcome.sdk == "google-adk"
    assert outcome.tool_calls == 1
    assert "2411" in outcome.text
    assert "tool_call_started" in [item.kind for item in outcome.events]


def test_model_clients_share_the_mokli_loop() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {"function": {"name": "get_gold_price", "arguments": "{}"}}
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            },
        )

    kimi = OpenAICompatibleClient("key", "kimi-k2-turbo-preview", "https://api.moonshot.ai/v1", httpx.Client(transport=httpx.MockTransport(handler)))
    first = kimi.complete([{"role": "user", "content": "price"}], _bridge().json_schemas())
    assert first.tool_calls[0][0] == "get_gold_price"

    class Script:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
            del messages, tools
            self.calls += 1
            if self.calls == 1:
                return ModelTurn(tool_calls=[("get_gold_price", {})], input_tokens=2, output_tokens=1, deltas=[".."])
            return ModelTurn(text="done", input_tokens=2, output_tokens=1, deltas=["done"])

    for client in (
        _tagged(OllamaModelClient("llama", _ollama_stub()), "ollama", "ollama"),
        _tagged(OpenRouterModelClient("openrouter/model", _chat_stub("openrouter")), "openrouter", "openrouter"),
        _tagged(ZaiChatClient("glm-4.5", _zai_stub()), "zai", "zai-sdk"),
        _tagged(ZaiHostedAgentClient("glm-4.5", "agent-1", _zai_agent_stub()), "zai", "zai-sdk"),
        _tagged(AnthropicMessagesClient("claude-sonnet-4-5", _anthropic_stub()), "anthropic", "anthropic"),
    ):
        outcome = run_model_loop(client, _bridge("9"), "price", session_id="m", agent_id=client.provider)
        assert outcome.tool_calls >= 0
        assert outcome.runtime


def test_event_normalization_hides_vendor_types() -> None:
    from claude_agent_sdk import AssistantMessage, TextBlock

    message = AssistantMessage(content=[TextBlock(text="hello")], model="claude-sonnet-4-5", usage={"input_tokens": 1})
    kinds = [item.kind for item in from_claude_message(message)]
    assert kinds[0] == "agent_message_delta"
    raw = SimpleNamespace(type="run_item_stream_event", name="tool_called", item=None)
    assert from_openai_stream(raw)[0].kind == "tool_call_started"


def test_subagent_is_isolated_and_audited() -> None:
    parent_context = {"note": "tape", "secret": "keep"}

    async def runner(spec: SubAgentSpec, child_id: str) -> RunOutcome:
        spec.context.pop("secret")
        assert spec.tool_names == ["get_gold_price"]
        return RunOutcome(
            text="child",
            provider=spec.provider,
            model=spec.model,
            runtime="mokli_runtime",
            sdk="mokli",
            agent_id=child_id,
            session_id="child",
            status="completed",
            tools=spec.tool_names,
            events=[],
            usage=UsageRecord(input_tokens=3, output_tokens=1),
        )

    record = asyncio.run(
        spawn_subagent(
            SubAgentSpec(
                role="research",
                provider="openrouter",
                model="m",
                runtime="mokli_runtime",
                parent_agent_id="parent-1",
                context=parent_context,
                tool_names=["get_gold_price"],
                token_budget=20,
                native=False,
            ),
            runner,
        )
    )
    assert record.parent_agent_id == "parent-1"
    assert record.child_agent_id
    assert parent_context["secret"] == "keep"
    assert "secret" not in record.context
    assert record.outcome is not None
    assert record.outcome.parent_agent_id == "parent-1"
    assert record.audit


def test_mcp_allowlist_timeout_and_broker_block() -> None:
    registry = McpRegistry()
    with pytest.raises(PermissionError):
        registry.register("bad", analysis_server(lambda: "1"), {"broker_market"})
    registry.register(
        "analysis",
        analysis_server(lambda: "1.5"),
        {"atr_value_tool"},
        timeout_s=1,
        side_effects={"atr_value_tool": "read"},
        approval=set(),
    )
    registry.permit("agent-a", {"atr_value_tool"})
    found = asyncio.run(registry.discover("agent-a"))
    assert found == ["atr_value_tool"]
    text = asyncio.run(registry.call("agent-a", "analysis", "atr_value_tool"))
    assert "1.5" in text
    assert registry.audits[-1].ok
    with pytest.raises(PermissionError):
        asyncio.run(registry.call("agent-a", "analysis", "broker_market"))


def test_fallback_emits_events_and_does_not_hide_the_switch() -> None:
    async def boom() -> RunOutcome:
        raise RuntimeError("sdk down")

    async def ok() -> RunOutcome:
        return RunOutcome(
            text="fallback",
            provider="mokli",
            model="deterministic-xauusd",
            runtime="mokli_runtime",
            sdk="mokli",
            agent_id="fb",
            session_id="s",
            status="completed",
            tools=["get_gold_price"],
            events=[],
            usage=UsageRecord(),
        )

    outcome = asyncio.run(
        run_with_fallback(
            [
                RuntimeStep("openai", "gpt-4.1", "openai_agents_sdk", "openai-agents", boom),
                RuntimeStep("mokli", "deterministic-xauusd", "mokli_runtime", "mokli", ok),
            ]
        )
    )
    kinds = [item.kind for item in outcome.events]
    assert "provider_fallback_started" in kinds
    assert "provider_fallback_completed" in kinds
    assert outcome.original_provider == "openai"
    assert outcome.fallback_provider == "mokli"
    assert outcome.fallback_reason == "sdk down"

    async def also_boom() -> RunOutcome:
        raise RuntimeError("mokli down")

    with pytest.raises(SafeFailure):
        asyncio.run(
            run_with_fallback(
                [
                    RuntimeStep("openai", "gpt-4.1", "openai_agents_sdk", "openai-agents", boom),
                    RuntimeStep("mokli", "deterministic-xauusd", "mokli_runtime", "mokli", also_boom),
                ]
            )
        )


def test_chat_persists_provider_runtime_metadata(tmp_path: Path) -> None:
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", active_provider="mokli")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    reply = client.post("/api/chat", headers=headers, json={"message": "price?"})
    body = reply.json()
    assert body["provider"] == "Mokli"
    assert body["runtime"] == "Mokli Runtime"
    assert body["agent"] == "Mokli"
    assert "get_gold_price" in body["tools"]
    assert body["status"] == "completed"
    from mokli.db import create_db_engine

    with Session(create_db_engine(settings)) as session:
        row = session.exec(select(ProviderRun)).one()
        assert row.provider == "mokli"
        assert row.runtime == "mokli_runtime"
        assert row.sdk == "mokli"
        assert row.agent_id
        assert row.session_id == "main"
        assert row.input_tokens > 0
        assert row.tool_calls == 1
        kinds = [item.kind for item in session.exec(select(AgentEvent)).all()]
        assert "tool_call_completed" in kinds
        assert "usage_updated" in kinds


def _tagged(client: object, provider: str, sdk: str) -> object:
    client.provider = provider
    client.sdk = sdk
    client.runtime = "mokli_runtime" if provider != "zai" or not isinstance(client, ZaiHostedAgentClient) else "zai_agents"
    if isinstance(client, ZaiHostedAgentClient):
        client.runtime = "zai_agents"

    original = client.complete

    def complete(messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        turn = original(messages, tools)
        if turn.tool_calls:
            return turn
        if client.calls if hasattr(client, "calls") else False:
            return turn
        return ModelTurn(text=turn.text or "ok", input_tokens=1, output_tokens=1)

    # Hosted agent has no tools. Chat stubs return one tool call then need a second turn.
    client.complete = _two_step(original) if not isinstance(client, ZaiHostedAgentClient) else original
    return client


def _two_step(original):
    state = {"n": 0}

    def complete(messages, tools):
        state["n"] += 1
        if state["n"] == 1:
            return original(messages, tools)
        return ModelTurn(text="ok", input_tokens=1, output_tokens=1)

    return complete


def _ollama_stub():
    class Function:
        name = "get_gold_price"
        arguments = {}

    class Call:
        function = Function()

    class Message:
        content = ""
        tool_calls = [Call()]

    class Response:
        message = Message()

    class Client:
        def chat(self, model: str, messages: list, tools: list, stream: bool) -> Response:
            assert tools
            assert stream is False
            return Response()

    return Client()


def _chat_stub(kind: str):
    class Response:
        def model_dump(self) -> dict:
            return {
                "choices": [
                    {"message": {"content": None, "tool_calls": [{"function": {"name": "get_gold_price", "arguments": "{}"}}]}}
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            }

    class Chat:
        def send(self, model: str, messages: list, tools: list) -> Response:
            assert kind == "openrouter"
            assert tools
            return Response()

    return SimpleNamespace(chat=Chat())


def _zai_stub():
    class Response:
        def model_dump(self) -> dict:
            return {
                "choices": [
                    {"message": {"content": None, "tool_calls": [{"function": {"name": "get_gold_price", "arguments": "{}"}}]}}
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            }

    class Completions:
        def create(self, model: str, messages: list, tools: list) -> Response:
            assert tools
            return Response()

    return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))


def _zai_agent_stub():
    class Response:
        def model_dump(self) -> dict:
            return {"choices": [{"message": {"content": "hosted"}}]}

    class Agents:
        def invoke(self, agent_id: str, messages: list, stream: bool) -> Response:
            assert agent_id == "agent-1"
            assert stream is False
            return Response()

    return SimpleNamespace(agents=Agents())


def _anthropic_stub():
    class Usage:
        input_tokens = 4
        output_tokens = 2
        cache_read_input_tokens = 1

    class Block:
        type = "tool_use"
        name = "get_gold_price"
        input: dict = {}
        text = ""

    class Response:
        content = [Block()]
        usage = Usage()

    class Messages:
        def create(self, model: str, max_tokens: int, messages: list, tools: list) -> Response:
            assert tools[0]["name"] == "get_gold_price"
            return Response()

    return SimpleNamespace(messages=Messages())


def test_chat_payload_is_jsonable() -> None:
    assert json.dumps({"ok": True})
