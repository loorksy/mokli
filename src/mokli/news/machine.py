"""News phase clock. Times are UTC. The caller supplies the next high-impact release."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NewsPhase(str, Enum):
    PRE_FREEZE = "PRE_FREEZE"
    VOID = "VOID"
    DISCOVERY = "DISCOVERY"
    SETTLING = "SETTLING"
    NORMAL = "NORMAL"


@dataclass(frozen=True)
class NewsState:
    phase: NewsPhase
    new_trades_allowed: bool
    cancel_pending: bool
    risk_multiplier: float
    ignore_m1: bool
    detail: str


def news_state(now: datetime, event_time: datetime | None) -> NewsState:
    if event_time is None:
        return NewsState(NewsPhase.NORMAL, True, False, 1.0, False, "No high-impact release is scheduled.")
    seconds = (now - event_time).total_seconds()
    if -15 * 60 <= seconds < 0:
        return NewsState(
            NewsPhase.PRE_FREEZE,
            False,
            True,
            0.5,
            False,
            "Fifteen-minute freeze. Pending orders are cancelled and open risk is reduced.",
        )
    if 0 <= seconds < 60:
        return NewsState(NewsPhase.VOID, False, True, 0.5, True, "First 60 seconds. No entry and no one-minute read.")
    if 60 <= seconds < 15 * 60:
        return NewsState(
            NewsPhase.DISCOVERY,
            False,
            False,
            0.5,
            True,
            "Discovery. The first five-minute close is the reference. One-minute noise is ignored.",
        )
    if 15 * 60 <= seconds < 30 * 60:
        return NewsState(
            NewsPhase.SETTLING,
            True,
            False,
            0.5,
            False,
            "Settling window. Retest and deep-pullback entries are allowed at half risk.",
        )
    return NewsState(NewsPhase.NORMAL, True, False, 1.0, False, "News window has expired.")
