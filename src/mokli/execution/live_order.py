"""Live send. The switch off never calls a broker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LiveResult:
    sent: bool
    reason: str
    order_id: str = ""


def submit_live_order(
    *,
    switch: bool,
    broker_connected: bool,
    proposal: dict[str, object],
    transport: Callable[[dict[str, object]], str] | None = None,
) -> LiveResult:
    if not switch:
        return LiveResult(False, "switch_off")
    if not broker_connected:
        return LiveResult(False, "broker_disconnected")
    sender = transport or _closed_transport
    try:
        order_id = sender(proposal)
    except Exception:
        return LiveResult(False, "broker_unavailable")
    if not order_id:
        return LiveResult(False, "broker_unavailable")
    return LiveResult(True, "sent", order_id)


def submit_live_flat(
    *,
    switch: bool,
    broker_connected: bool,
    transport: Callable[[dict[str, object]], str] | None = None,
) -> LiveResult:
    return submit_live_order(
        switch=switch,
        broker_connected=broker_connected,
        proposal={"kind": "flatten"},
        transport=transport,
    )


def _closed_transport(_proposal: dict[str, object]) -> str:
    raise RuntimeError("live broker transport is not open")
