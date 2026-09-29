"""Shared agent-runtime types. Provider SDKs do not leak past this module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EVENT_KINDS = (
    "agent_started",
    "agent_message_delta",
    "agent_message_completed",
    "tool_call_started",
    "tool_call_completed",
    "subagent_started",
    "subagent_completed",
    "handoff_started",
    "handoff_completed",
    "approval_required",
    "agent_cancelled",
    "agent_failed",
    "usage_updated",
    "provider_fallback_started",
    "provider_fallback_completed",
    "provider_fallback_failed",
)

SideEffect = Literal["read", "write", "broker"]


@dataclass
class MokliEvent:
    kind: str
    payload: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"unknown Mokli event {self.kind}")


@dataclass(frozen=True)
class Capabilities:
    streaming: bool = False
    native_tools: bool = False
    structured_output: bool = False
    agent_sdk: bool = False
    subagents: bool = False
    handoffs: bool = False
    sessions: bool = False
    reasoning: bool = False
    computer_use: bool = False
    web_search: bool = False
    mcp: bool = False
    background_tasks: bool = False
    prompt_caching: bool = False

    def enabled(self) -> list[str]:
        return [name for name, value in self.__dict__.items() if value]


@dataclass
class UsageRecord:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class RunOutcome:
    text: str
    provider: str
    model: str
    runtime: str
    sdk: str
    agent_id: str
    session_id: str
    status: str
    tools: list[str]
    events: list[MokliEvent]
    usage: UsageRecord
    latency_ms: int = 0
    parent_agent_id: str = ""
    tool_calls: int = 0
    subagents: int = 0
    retries: int = 0
    failures: list[str] = field(default_factory=list)
    fallbacks: list[dict[str, str]] = field(default_factory=list)
    original_provider: str = ""
    original_model: str = ""
    original_runtime: str = ""
    fallback_provider: str = ""
    fallback_model: str = ""
    fallback_runtime: str = ""
    fallback_reason: str = ""
    display_provider: str = ""
    display_model: str = ""
    display_runtime: str = ""
    agent_name: str = "Mokli"


@dataclass
class ModelTurn:
    text: str = ""
    tool_calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    deltas: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
