"""Provider fallback. A failed runtime is recorded. Nothing switches silently."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from mokli.runtime.events import event
from mokli.runtime.types import MokliEvent, RunOutcome


class SafeFailure(RuntimeError):
    def __init__(self, events: list[MokliEvent], reason: str) -> None:
        super().__init__(reason)
        self.events = events
        self.reason = reason


@dataclass
class RuntimeStep:
    provider: str
    model: str
    runtime: str
    sdk: str
    run: Callable[[], Awaitable[RunOutcome]]


async def run_with_fallback(steps: list[RuntimeStep]) -> RunOutcome:
    if not steps:
        raise SafeFailure([], "no runtime configured")
    original = steps[0]
    events: list[MokliEvent] = []
    failures: list[str] = []
    fallbacks: list[dict[str, str]] = []
    last_reason = "no runtime succeeded"
    for index, step in enumerate(steps):
        if index:
            events.append(
                event(
                    "provider_fallback_started",
                    from_provider=original.provider,
                    to_provider=step.provider,
                    to_runtime=step.runtime,
                )
            )
        try:
            outcome = await step.run()
        except Exception as exc:
            reason = str(exc)
            last_reason = reason
            failures.append(f"{step.provider}:{reason}")
            events.append(
                event(
                    "provider_fallback_failed" if index else "agent_failed",
                    provider=step.provider,
                    runtime=step.runtime,
                    reason=reason,
                )
            )
            continue
        outcome.events = events + outcome.events
        outcome.failures = failures + outcome.failures
        outcome.retries = index
        outcome.original_provider = original.provider
        outcome.original_model = original.model
        outcome.original_runtime = original.runtime
        if index:
            stamp = datetime.now(timezone.utc).isoformat()
            record = {
                "provider": step.provider,
                "model": step.model,
                "runtime": step.runtime,
                "reason": last_reason,
                "timestamp": stamp,
            }
            fallbacks.append(record)
            outcome.fallback_provider = step.provider
            outcome.fallback_model = step.model
            outcome.fallback_runtime = step.runtime
            outcome.fallback_reason = last_reason
            outcome.events.append(
                event("provider_fallback_completed", **record)
            )
        outcome.fallbacks = fallbacks
        return outcome
    events.append(event("agent_failed", detail=last_reason))
    raise SafeFailure(events, last_reason)
