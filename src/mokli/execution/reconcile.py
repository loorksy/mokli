"""Compare local rows with broker truth. Broker quantities are not overwritten."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationResult:
    state: str
    discrepancies: tuple[str, ...]


def reconcile(local: dict[str, dict[str, object]], broker: dict[str, dict[str, object]]) -> ReconciliationResult:
    notes: list[str] = []
    ids = set(local) | set(broker)
    for position_id in sorted(ids):
        left = local.get(position_id)
        right = broker.get(position_id)
        if left is None:
            notes.append(f"{position_id} exists at the broker and not locally")
            continue
        if right is None:
            notes.append(f"{position_id} exists locally and not at the broker")
            continue
        if left.get("remaining") != right.get("remaining") or left.get("side") != right.get("side"):
            notes.append(f"{position_id} quantity or side differs")
    if notes:
        return ReconciliationResult("DESYNCED", tuple(notes))
    return ReconciliationResult("LIVE", ())
