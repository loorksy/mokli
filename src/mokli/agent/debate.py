"""Turn cycle role notes into isolated sub-agent runs."""

from __future__ import annotations

import uuid

from mokli.cycle import CycleResult
from mokli.runtime.subagent import SubAgentSpec, spawn_subagent
from mokli.runtime.types import RunOutcome, UsageRecord


async def run_debate(
    result: CycleResult,
    *,
    parent_id: str,
    provider: str,
    model: str,
    runtime: str,
) -> list[dict[str, object]]:
    records = []
    for note in result.notes:
        spec = SubAgentSpec(
            role=note.role,
            provider=provider,
            model=model,
            runtime=runtime,
            parent_agent_id=parent_id,
            context={"role": note.role, "evidence": list(note.evidence), "verdict": result.verdict},
            tool_names=[],
            token_budget=400,
            native=False,
        )

        async def runner(child: SubAgentSpec, child_id: str, text: str = note.text) -> RunOutcome:
            return RunOutcome(
                text=text,
                provider=child.provider,
                model=child.model,
                runtime="mokli_runtime",
                sdk="mokli",
                agent_id=child_id,
                session_id="debate",
                status="completed",
                tools=[],
                events=[],
                usage=UsageRecord(input_tokens=12, output_tokens=8),
                agent_name=child.role,
            )

        record = await spawn_subagent(spec, runner)
        item: dict[str, object] = {
            "id": record.child_agent_id or uuid.uuid4().hex[:12],
            "parent_id": record.parent_agent_id,
            "role": note.role,
            "provider": record.provider,
            "model": record.model,
            "runtime": record.runtime,
            "text": note.text,
            "audit": list(record.audit),
            "status": record.outcome.status if record.outcome else "failed",
        }
        records.append(item)
    return records
