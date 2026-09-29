"""Position size from balance and stop distance. Field rules 47, 188, and 199."""

from __future__ import annotations

import math

from mokli.models import SizeResult
from mokli.units import LOT_STEP, MIN_LOT, loss_per_lot


class SizeError(ValueError):
    """The risk fraction cannot be expressed without exceeding it, or the inputs are unusable."""


def size_position(balance: float, entry: float, stop: float, risk_fraction: float) -> SizeResult:
    """Size off closed balance, then check the currency risk a second time.

    Lots are stepped down to 0.01 so the loss at the stop is never above the budget.
    A one-cent lot step cannot land on the budget exactly for every distance.
    """
    if not all(math.isfinite(value) for value in (balance, entry, stop, risk_fraction)):
        raise SizeError("size inputs must be finite")
    if balance <= 0:
        raise SizeError("balance must be positive")
    if not 0 < risk_fraction <= 0.02:
        raise SizeError("risk_fraction must be in (0, 0.02]")
    distance = abs(entry - stop)
    if distance <= 0:
        raise SizeError("stop distance must be positive")

    budget = balance * risk_fraction
    raw_lots = budget / loss_per_lot(distance)
    steps = math.floor((raw_lots + 1e-12) / LOT_STEP)
    lots = round(steps * LOT_STEP, 2)
    if lots < MIN_LOT:
        raise SizeError("lot size would round below 0.01 and cannot be sent")

    first = lots * loss_per_lot(distance)
    second = lots * distance * 100.0
    if abs(first - second) > 1e-6 or first > budget + 1e-6:
        raise SizeError("dual lot check failed")
    return SizeResult(lots=lots, risk_amount=first, budget=budget, stop_distance=distance)


def reward_risk(side: str, entry: float, stop: float, target: float) -> float:
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0
    if side == "buy":
        if not stop < entry < target:
            return 0.0
        reward = target - entry
    elif side == "sell":
        if not target < entry < stop:
            return 0.0
        reward = entry - target
    else:
        raise SizeError("side must be buy or sell")
    return reward / risk
