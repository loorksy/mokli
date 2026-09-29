"""Capability discovery. Flags describe the runtime that is actually wired."""

from __future__ import annotations

from dataclasses import dataclass

from mokli.runtime.claude_agent import CAPABILITIES as CLAUDE
from mokli.runtime.gemini_agent import CAPABILITIES as GEMINI
from mokli.runtime.openai_agent import CAPABILITIES as OPENAI
from mokli.runtime.types import Capabilities

MOKLI = Capabilities(
    streaming=True,
    native_tools=True,
    structured_output=False,
    agent_sdk=False,
    subagents=False,
    handoffs=False,
    sessions=True,
    reasoning=False,
    computer_use=False,
    web_search=False,
    mcp=True,
    background_tasks=False,
    prompt_caching=False,
)

ANTHROPIC_MESSAGES = Capabilities(
    streaming=True,
    native_tools=True,
    structured_output=True,
    agent_sdk=False,
    subagents=False,
    handoffs=False,
    sessions=False,
    reasoning=True,
    computer_use=False,
    web_search=False,
    mcp=False,
    background_tasks=False,
    prompt_caching=True,
)

GEMINI_GENAI = Capabilities(
    streaming=True,
    native_tools=True,
    structured_output=True,
    agent_sdk=False,
    subagents=False,
    handoffs=False,
    sessions=False,
    reasoning=True,
    computer_use=False,
    web_search=False,
    mcp=False,
    background_tasks=False,
    prompt_caching=True,
)


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    display_provider: str
    display_runtime: str
    runtime: str
    sdk: str
    capabilities: Capabilities
    status: str


def specs() -> dict[str, ProviderSpec]:
    return {
        "openai": ProviderSpec(
            "openai", "OpenAI", "OpenAI Agents SDK", "openai_agents_sdk", "openai-agents", OPENAI,
            "IMPLEMENTED — Native Agent SDK",
        ),
        "anthropic": ProviderSpec(
            "anthropic", "Anthropic", "Claude Agent SDK", "claude_agent_sdk", "claude-agent-sdk", CLAUDE,
            "IMPLEMENTED — Native Agent SDK",
        ),
        "gemini": ProviderSpec(
            "gemini", "Gemini", "Google ADK", "google_adk", "google-adk", GEMINI,
            "IMPLEMENTED — Native Agent SDK",
        ),
        "openrouter": ProviderSpec(
            "openrouter", "OpenRouter", "Mokli Runtime", "mokli_runtime", "openrouter", MOKLI,
            "IMPLEMENTED — Mokli Agent Runtime",
        ),
        "kimi": ProviderSpec(
            "kimi", "Kimi", "Mokli Runtime", "mokli_runtime", "moonshot-http", MOKLI,
            "IMPLEMENTED — Mokli Agent Runtime",
        ),
        "zai": ProviderSpec(
            "zai", "Z.ai", "Mokli Runtime", "mokli_runtime", "zai-sdk", MOKLI,
            "IMPLEMENTED — Mokli Agent Runtime",
        ),
        "ollama": ProviderSpec(
            "ollama", "Ollama", "Mokli Runtime", "mokli_runtime", "ollama", MOKLI,
            "IMPLEMENTED — Mokli Agent Runtime",
        ),
        "mokli": ProviderSpec(
            "mokli", "Mokli", "Mokli Runtime", "mokli_runtime", "mokli", MOKLI,
            "IMPLEMENTED — Mokli Agent Runtime",
        ),
    }


def public_catalog(configured: dict[str, bool], zai_agent: bool) -> list[dict[str, object]]:
    rows = []
    for spec in specs().values():
        capabilities = spec.capabilities
        runtime = spec.runtime
        display_runtime = spec.display_runtime
        status = spec.status
        if spec.id == "zai" and zai_agent:
            runtime = "zai_agents"
            display_runtime = "Z.ai Agents"
            status = "IMPLEMENTED — Native Model API"
        rows.append(
            {
                "id": spec.id,
                "provider": spec.display_provider,
                "runtime": runtime,
                "display_runtime": display_runtime,
                "sdk": spec.sdk,
                "agent_sdk": capabilities.agent_sdk,
                "configured": configured.get(spec.id, False),
                "status": status,
                "capabilities": capabilities.enabled(),
            }
        )
    return rows
