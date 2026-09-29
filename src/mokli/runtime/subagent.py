"""Sub-agent spawn. Native handoff is used only when the provider runtime supports it."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from mokli.runtime.events import event
from mokli.runtime.types import MokliEvent, RunOutcome


@dataclass
class SubAgentSpec:
    role: str
    provider: str
    model: str
    runtime: str
    parent_agent_id: str
    context: dict[str, object]
    tool_names: list[str]
    token_budget: int
    native: bool = False


@dataclass
class SubAgentRecord:
    parent_agent_id: str
    child_agent_id: str
    provider: str
    model: str
    runtime: str
    context: dict[str, object]
    tool_names: list[str]
    token_budget: int
    cancelled: bool
    audit: list[str] = field(default_factory=list)
    outcome: RunOutcome | None = None
    events: list[MokliEvent] = field(default_factory=list)


async def spawn_subagent(
    spec: SubAgentSpec,
    runner: Callable[[SubAgentSpec, str], Awaitable[RunOutcome]],
    *,
    cancel: Callable[[], bool] | None = None,
) -> SubAgentRecord:
    child_id = uuid.uuid4().hex[:12]
    isolated = copy.deepcopy(spec.context)
    record = SubAgentRecord(
        parent_agent_id=spec.parent_agent_id,
        child_agent_id=child_id,
        provider=spec.provider,
        model=spec.model,
        runtime=spec.runtime if spec.native else "mokli_runtime",
        context=isolated,
        tool_names=list(spec.tool_names),
        token_budget=spec.token_budget,
        cancelled=False,
        audit=[
            f"spawn parent={spec.parent_agent_id} child={child_id} "
            f"provider={spec.provider} runtime={spec.runtime} native={spec.native}"
        ],
    )
    record.events.append(
        event(
            "subagent_started",
            parent_agent_id=spec.parent_agent_id,
            child_agent_id=child_id,
            provider=spec.provider,
            model=spec.model,
            runtime=record.runtime,
        )
    )
    if cancel is not None and cancel():
        record.cancelled = True
        record.audit.append("cancelled before start")
        record.events.append(event("agent_cancelled", child_agent_id=child_id))
        return record
    child_spec = SubAgentSpec(
        role=spec.role,
        provider=spec.provider,
        model=spec.model,
        runtime=spec.runtime,
        parent_agent_id=spec.parent_agent_id,
        context=isolated,
        tool_names=list(spec.tool_names),
        token_budget=spec.token_budget,
        native=spec.native,
    )
    outcome = await runner(child_spec, child_id)
    outcome.parent_agent_id = spec.parent_agent_id
    if outcome.usage.input_tokens + outcome.usage.output_tokens > spec.token_budget:
        outcome.status = "failed"
        outcome.events.append(event("agent_failed", detail="sub-agent token budget exceeded"))
        record.audit.append("token budget exceeded")
    record.outcome = outcome
    record.events.append(
        event(
            "subagent_completed",
            parent_agent_id=spec.parent_agent_id,
            child_agent_id=child_id,
            status=outcome.status,
        )
    )
    record.audit.append(f"finished status={outcome.status}")
    return record
