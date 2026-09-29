"""Mokli-owned agent loop for providers that have a model API and no agent SDK."""

from __future__ import annotations

import time
from collections.abc import Callable

from mokli.runtime.cost import estimate_cost
from mokli.runtime.events import event
from mokli.runtime.toolbridge import ToolBridge
from mokli.runtime.types import ModelTurn, MokliEvent, RunOutcome, UsageRecord


class ModelClient:
    provider = "mokli"
    runtime = "mokli_runtime"
    sdk = "mokli"
    model = "deterministic-xauusd"

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        raise NotImplementedError


def run_model_loop(
    client: ModelClient,
    bridge: ToolBridge,
    prompt: str,
    *,
    session_id: str,
    agent_id: str,
    parent_agent_id: str = "",
    cancel: Callable[[], bool] | None = None,
    token_budget: int | None = None,
    messages: list[dict[str, object]] | None = None,
    max_turns: int = 4,
) -> RunOutcome:
    started = time.perf_counter()
    events: list[MokliEvent] = [event("agent_started", agent_id=agent_id, provider=client.provider)]
    transcript: list[dict[str, object]] = list(messages or [])
    transcript.append({"role": "user", "content": prompt})
    usage = UsageRecord()
    text = ""
    status = "completed"
    schemas = bridge.json_schemas()
    for _turn in range(max_turns):
        if cancel is not None and cancel():
            status = "cancelled"
            events.append(event("agent_cancelled", agent_id=agent_id))
            break
        turn = client.complete(transcript, schemas)
        usage.input_tokens += turn.input_tokens
        usage.output_tokens += turn.output_tokens
        usage.cached_tokens += turn.cached_tokens
        if token_budget is not None and usage.input_tokens + usage.output_tokens > token_budget:
            status = "failed"
            events.append(event("agent_failed", detail="token budget exceeded"))
            break
        for delta in turn.deltas:
            events.append(event("agent_message_delta", text=delta))
        if turn.tool_calls:
            for name, arguments in turn.tool_calls:
                events.append(event("tool_call_started", name=name))
                try:
                    result = bridge.invoke(name, arguments)
                except PermissionError as exc:
                    events.append(event("approval_required", name=name, detail=str(exc)))
                    status = "approval_required"
                    text = str(exc)
                    break
                events.append(event("tool_call_completed", name=name, result=result))
                transcript.append({"role": "tool", "name": name, "content": result})
            if status == "approval_required":
                break
            continue
        text = turn.text
        events.append(event("agent_message_completed", text=text))
        break
    else:
        status = "failed"
        events.append(event("agent_failed", detail="turn limit"))
    usage.estimated_cost = estimate_cost(client.model, usage.input_tokens, usage.output_tokens)
    events.append(
        event(
            "usage_updated",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
        )
    )
    return RunOutcome(
        text=text,
        provider=client.provider,
        model=client.model,
        runtime=client.runtime,
        sdk=client.sdk,
        agent_id=agent_id,
        parent_agent_id=parent_agent_id,
        session_id=session_id,
        status=status,
        tools=[tool.name for tool in bridge.exposed()],
        events=events,
        usage=usage,
        latency_ms=int((time.perf_counter() - started) * 1000),
        tool_calls=len(bridge.calls),
    )


class DeterministicGoldClient(ModelClient):
    """Local loop used when no vendor key is selected. It only reads Mokli's snapshot."""

    def __init__(self, snapshot: str) -> None:
        self.snapshot = snapshot
        self._step = 0

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        self._step += 1
        names: list[str] = []
        for item in tools:
            function = item.get("function")
            if isinstance(function, dict):
                names.append(str(function.get("name")))
        if self._step == 1 and "get_gold_price" in names:
            return ModelTurn(tool_calls=[("get_gold_price", {})], input_tokens=8, output_tokens=2, deltas=["reading"])
        return ModelTurn(
            text=f"Price context: {self.snapshot}",
            input_tokens=10,
            output_tokens=6,
            deltas=["Price context: ", self.snapshot],
        )
