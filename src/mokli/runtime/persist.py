"""Write one agent run, its events, and its provider record."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session

from mokli.runtime.types import RunOutcome
from mokli.schema import AgentEvent, AgentRun, ProviderRun, ToolCall


def persist_outcome(engine: Engine, outcome: RunOutcome) -> None:
    fallback_at = datetime.now(timezone.utc) if outcome.fallback_provider else None
    with Session(engine) as session:
        session.add(
            AgentRun(
                id=outcome.agent_id,
                parent_id=outcome.parent_agent_id or None,
                role="mokli" if not outcome.parent_agent_id else "subagent",
                provider=outcome.provider,
                runtime=outcome.runtime,
                model=outcome.model,
                status=outcome.status,
                session_id=outcome.session_id,
                finished_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            ProviderRun(
                id=f"pr-{outcome.agent_id}",
                run_id=outcome.agent_id,
                provider=outcome.provider,
                runtime=outcome.runtime,
                model=outcome.model,
                sdk=outcome.sdk,
                agent_id=outcome.agent_id,
                parent_agent_id=outcome.parent_agent_id,
                session_id=outcome.session_id,
                input_tokens=outcome.usage.input_tokens,
                output_tokens=outcome.usage.output_tokens,
                cached_tokens=outcome.usage.cached_tokens,
                estimated_cost=outcome.usage.estimated_cost,
                latency_ms=outcome.latency_ms,
                tool_calls=outcome.tool_calls,
                subagents=outcome.subagents,
                retries=outcome.retries,
                failures=json.dumps(outcome.failures),
                fallbacks=json.dumps(outcome.fallbacks),
                original_provider=outcome.original_provider or outcome.provider,
                original_model=outcome.original_model or outcome.model,
                original_runtime=outcome.original_runtime or outcome.runtime,
                fallback_provider=outcome.fallback_provider,
                fallback_model=outcome.fallback_model,
                fallback_runtime=outcome.fallback_runtime,
                fallback_reason=outcome.fallback_reason,
                fallback_at=fallback_at,
                fallback_from=outcome.original_provider if outcome.fallback_provider else "",
                error=";".join(outcome.failures),
            )
        )
        for item in outcome.events:
            session.add(AgentEvent(run_id=outcome.agent_id, kind=item.kind, payload=json.dumps(item.payload)))
        for index in range(outcome.tool_calls):
            session.add(
                ToolCall(
                    id=f"{outcome.agent_id}-tool-{index}",
                    run_id=outcome.agent_id,
                    name=outcome.tools[0] if outcome.tools else "tool",
                    arguments="{}",
                    result="",
                    ok=True,
                )
            )
        session.commit()


def outcome_payload(outcome: RunOutcome) -> dict[str, object]:
    return {
        "text": outcome.text,
        "provider": outcome.display_provider or outcome.provider,
        "provider_id": outcome.provider,
        "model": outcome.display_model or outcome.model,
        "runtime": outcome.display_runtime or outcome.runtime,
        "agent": outcome.agent_name,
        "agent_id": outcome.agent_id,
        "status": outcome.status,
        "tools": outcome.tools,
        "sdk": outcome.sdk,
        "session_id": outcome.session_id,
        "events": [item.kind for item in outcome.events],
    }
