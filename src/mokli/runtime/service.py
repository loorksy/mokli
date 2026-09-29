"""Select a runtime, run it, and fall back without hiding the switch."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.engine import Engine

from mokli.config import Settings
from mokli.runtime.catalog import specs
from mokli.runtime.fallback import RuntimeStep, run_with_fallback
from mokli.runtime.loop import DeterministicGoldClient, run_model_loop
from mokli.runtime.model_clients import (
    AnthropicMessagesClient,
    GeminiGenAIClient,
    OllamaModelClient,
    OpenAIChatClient,
    OpenAICompatibleClient,
    OpenRouterModelClient,
    ZaiChatClient,
    ZaiHostedAgentClient,
)
from mokli.runtime.persist import persist_outcome
from mokli.runtime.toolbridge import ToolBridge, gold_price_tool
from mokli.runtime.types import RunOutcome


def bridge_for(snapshot: str) -> ToolBridge:
    bridge = ToolBridge()
    bridge.register(gold_price_tool(lambda: snapshot))
    return bridge


def _display(outcome: RunOutcome) -> RunOutcome:
    spec = specs().get(outcome.provider)
    if spec and not outcome.display_provider:
        outcome.display_provider = spec.display_provider
        outcome.display_runtime = spec.display_runtime
        outcome.display_model = outcome.model
    return outcome


async def run_selected(
    settings: Settings,
    provider: str,
    prompt: str,
    snapshot: str,
    *,
    session_id: str,
    engine: Engine | None = None,
    model_override: Any | None = None,
    claude_transport: Any | None = None,
    gemini_model: Any | None = None,
) -> RunOutcome:
    agent_id = uuid.uuid4().hex[:12]
    steps = _steps(
        settings,
        provider,
        prompt,
        snapshot,
        session_id=session_id,
        agent_id=agent_id,
        model_override=model_override,
        claude_transport=claude_transport,
        gemini_model=gemini_model,
    )
    outcome = _display(await run_with_fallback(steps))
    if engine is not None:
        persist_outcome(engine, outcome)
    return outcome


def _steps(
    settings: Settings,
    provider: str,
    prompt: str,
    snapshot: str,
    *,
    session_id: str,
    agent_id: str,
    model_override: Any | None,
    claude_transport: Any | None,
    gemini_model: Any | None,
) -> list[RuntimeStep]:
    steps: list[RuntimeStep] = []
    if provider == "openai":
        steps.append(
            RuntimeStep(
                "openai",
                settings.openai_model,
                "openai_agents_sdk",
                "openai-agents",
                lambda: _openai(prompt, snapshot, session_id, agent_id, settings, model_override),
            )
        )
        if settings.openai_api_key:
            steps.append(
                RuntimeStep(
                    "openai",
                    settings.openai_model,
                    "openai_chat",
                    "openai",
                    lambda: _openai_chat(prompt, snapshot, session_id, agent_id, settings),
                )
            )
    elif provider == "anthropic":
        steps.append(
            RuntimeStep(
                "anthropic",
                settings.anthropic_model,
                "claude_agent_sdk",
                "claude-agent-sdk",
                lambda: _claude(prompt, snapshot, session_id, agent_id, settings, claude_transport),
            )
        )
        if settings.anthropic_api_key:
            steps.append(
                RuntimeStep(
                    "anthropic",
                    settings.anthropic_model,
                    "anthropic_messages",
                    "anthropic",
                    lambda: _anthropic_messages(prompt, snapshot, session_id, agent_id, settings),
                )
            )
    elif provider == "gemini":
        steps.append(
            RuntimeStep(
                "gemini",
                settings.gemini_model,
                "google_adk",
                "google-adk",
                lambda: _gemini(prompt, snapshot, session_id, agent_id, gemini_model),
            )
        )
        if settings.gemini_api_key:
            steps.append(
                RuntimeStep(
                    "gemini",
                    settings.gemini_model,
                    "google_genai",
                    "google-genai",
                    lambda: _gemini_api(prompt, snapshot, session_id, agent_id, settings),
                )
            )
    elif provider == "openrouter" and settings.openrouter_api_key:
        steps.extend(_model_steps("openrouter", settings.openrouter_model or "unconfigured", settings, prompt, snapshot, session_id, agent_id))
    elif provider == "kimi" and settings.kimi_api_key:
        steps.extend(_model_steps("kimi", settings.kimi_model, settings, prompt, snapshot, session_id, agent_id))
    elif provider == "zai" and settings.zai_api_key:
        steps.extend(_model_steps("zai", settings.zai_model, settings, prompt, snapshot, session_id, agent_id))
    elif provider == "ollama" and settings.ollama_model:
        steps.extend(_model_steps("ollama", settings.ollama_model, settings, prompt, snapshot, session_id, agent_id))
    elif provider not in {"mokli", "openai", "anthropic", "gemini"}:
        steps.append(
            RuntimeStep(
                provider,
                "unconfigured",
                "mokli_runtime",
                "mokli",
                lambda: _missing(provider),
            )
        )
    fallback = settings.fallback_provider or "mokli"
    if provider != "mokli" and fallback == "mokli":
        steps.append(
            RuntimeStep(
                "mokli",
                "deterministic-xauusd",
                "mokli_runtime",
                "mokli",
                lambda: _mokli(prompt, snapshot, session_id, agent_id),
            )
        )
    elif not steps:
        steps.append(
            RuntimeStep(
                "mokli",
                "deterministic-xauusd",
                "mokli_runtime",
                "mokli",
                lambda: _mokli(prompt, snapshot, session_id, agent_id),
            )
        )
    return steps


async def _missing(provider: str) -> RunOutcome:
    raise RuntimeError(f"{provider} is not configured")


async def _openai(
    prompt: str, snapshot: str, session_id: str, agent_id: str, settings: Settings, model_override: Any | None
) -> RunOutcome:
    from mokli.runtime.openai_agent import run_openai_agent

    model = model_override if model_override is not None else settings.openai_model
    if model_override is None and not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    return await run_openai_agent(
        prompt, bridge_for(snapshot), model=model, session_id=session_id, agent_id=agent_id
    )


async def _claude(
    prompt: str, snapshot: str, session_id: str, agent_id: str, settings: Settings, transport: Any | None
) -> RunOutcome:
    from mokli.runtime.claude_agent import run_claude_agent

    if transport is None and not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    return await run_claude_agent(
        prompt,
        bridge_for(snapshot),
        model=settings.anthropic_model,
        session_id=session_id,
        agent_id=agent_id,
        transport=transport,
        workspace=settings.workspace_dir,
        subagent_prompt="Research only. Call get_gold_price.",
    )


async def _gemini(
    prompt: str, snapshot: str, session_id: str, agent_id: str, model: Any | None
) -> RunOutcome:
    from mokli.runtime.gemini_agent import run_gemini_agent

    if model is None:
        raise RuntimeError("GEMINI_API_KEY missing for a live ADK run")
    return await run_gemini_agent(
        prompt, bridge_for(snapshot), model=model, session_id=session_id, agent_id=agent_id
    )


async def _openai_chat(
    prompt: str, snapshot: str, session_id: str, agent_id: str, settings: Settings
) -> RunOutcome:
    from openai import OpenAI

    client = OpenAIChatClient(settings.openai_model, OpenAI(api_key=settings.openai_api_key))
    outcome = run_model_loop(client, bridge_for(snapshot), prompt, session_id=session_id, agent_id=agent_id)
    outcome.display_provider = "OpenAI"
    outcome.display_model = settings.openai_model
    outcome.display_runtime = "OpenAI Chat Completions"
    return outcome


async def _anthropic_messages(
    prompt: str, snapshot: str, session_id: str, agent_id: str, settings: Settings
) -> RunOutcome:
    import anthropic

    client = AnthropicMessagesClient(settings.anthropic_model, anthropic.Anthropic(api_key=settings.anthropic_api_key))
    outcome = run_model_loop(client, bridge_for(snapshot), prompt, session_id=session_id, agent_id=agent_id)
    outcome.display_provider = "Anthropic"
    outcome.display_model = settings.anthropic_model
    outcome.display_runtime = "Anthropic Messages API"
    return outcome


async def _gemini_api(
    prompt: str, snapshot: str, session_id: str, agent_id: str, settings: Settings
) -> RunOutcome:
    from google import genai

    client = GeminiGenAIClient(settings.gemini_model, genai.Client(api_key=settings.gemini_api_key))
    outcome = run_model_loop(client, bridge_for(snapshot), prompt, session_id=session_id, agent_id=agent_id)
    outcome.display_provider = "Gemini"
    outcome.display_model = settings.gemini_model
    outcome.display_runtime = "Google GenAI"
    return outcome


async def _mokli(prompt: str, snapshot: str, session_id: str, agent_id: str) -> RunOutcome:
    outcome = run_model_loop(
        DeterministicGoldClient(snapshot),
        bridge_for(snapshot),
        prompt,
        session_id=session_id,
        agent_id=agent_id,
    )
    outcome.display_provider = "Mokli"
    outcome.display_model = "deterministic-xauusd"
    outcome.display_runtime = "Mokli Runtime"
    return outcome


def _model_steps(
    provider: str,
    model: str,
    settings: Settings,
    prompt: str,
    snapshot: str,
    session_id: str,
    agent_id: str,
) -> list[RuntimeStep]:
    def run() -> Any:
        return _model(provider, model, settings, prompt, snapshot, session_id, agent_id)

    return [RuntimeStep(provider, model, "mokli_runtime", specs()[provider].sdk, run)]


async def _model(
    provider: str,
    model: str,
    settings: Settings,
    prompt: str,
    snapshot: str,
    session_id: str,
    agent_id: str,
) -> RunOutcome:
    client = _live_client(provider, model, settings)
    outcome = run_model_loop(client, bridge_for(snapshot), prompt, session_id=session_id, agent_id=agent_id)
    spec = specs()[provider]
    outcome.display_provider = spec.display_provider
    outcome.display_model = model
    outcome.display_runtime = spec.display_runtime
    return outcome


def _live_client(provider: str, model: str, settings: Settings) -> Any:
    if provider == "kimi":
        return OpenAICompatibleClient(settings.kimi_api_key, model, settings.kimi_base_url)
    if provider == "ollama":
        import ollama

        return OllamaModelClient(model, ollama.Client(host=settings.ollama_host))
    if provider == "openrouter":
        from openrouter import OpenRouter

        return OpenRouterModelClient(model, OpenRouter(api_key=settings.openrouter_api_key))
    if provider == "zai" and settings.zai_agent_id:
        from zai import ZaiClient

        return ZaiHostedAgentClient(model, settings.zai_agent_id, ZaiClient(api_key=settings.zai_api_key))
    if provider == "zai":
        from zai import ZaiClient

        return ZaiChatClient(model, ZaiClient(api_key=settings.zai_api_key))
    if provider == "anthropic":
        import anthropic

        return AnthropicMessagesClient(model, anthropic.Anthropic(api_key=settings.anthropic_api_key))
    if provider == "gemini":
        from google import genai

        return GeminiGenAIClient(model, genai.Client(api_key=settings.gemini_api_key))
    raise RuntimeError(f"no native client for {provider}")
