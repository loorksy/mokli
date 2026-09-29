"""Stop placement and the ban on widening. Field rules 28, 31, 35, 38, and 46."""

from __future__ import annotations

from mokli.models import Check, RiskConfig
from mokli.units import POINT


def structural_stop(side: str, invalidation: float, atr: float, config: RiskConfig) -> float:
    """Place the stop beyond the price that kills the idea.

    The source left the ATR multiple blank. The buffer is the greater of 25 points
    and half the current ATR, which keeps rule 28's floor and widens in a large range.
    """
    if atr <= 0:
        raise ValueError("atr must be positive")
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    buffer = max(config.min_stop_buffer_points * POINT, config.stop_buffer_atr_fraction * atr)
    if side == "buy":
        return invalidation - buffer
    return invalidation + buffer


def validate_stop_change(side: str, old_stop: float, new_stop: float) -> Check:
    """Rule 35: a stop may move only toward smaller loss."""
    if side == "buy":
        widened = new_stop < old_stop
    elif side == "sell":
        widened = new_stop > old_stop
    else:
        raise ValueError("side must be buy or sell")
    if widened:
        return Check(
            "field.35",
            False,
            "Stop widened. The planned loss cannot be increased after entry.",
        )
    return Check("field.35", True, "Stop moved tighter or stayed put.")


def breakeven_allowed(
    side: str,
    entry: float,
    initial_stop: float,
    price: float,
    m15_swing_confirmed: bool,
) -> Check:
    """Rules 38 and 46: breakeven waits for one full risk unit and a new M15 swing."""
    risk = abs(entry - initial_stop)
    traveled = (price - entry) if side == "buy" else (entry - price)
    if side not in ("buy", "sell"):
        raise ValueError("side must be buy or sell")
    if traveled + 1e-9 < risk:
        return Check(
            "field.38",
            False,
            "Price has not traveled a full stop distance. Breakeven stays off.",
        )
    if not m15_swing_confirmed:
        return Check(
            "field.46",
            False,
            "No new M15 swing in favor yet. An early breakeven is noise.",
        )
    return Check("field.38", True, "One risk unit has traveled and the M15 swing is in.")
