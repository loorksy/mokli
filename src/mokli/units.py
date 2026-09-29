"""XAUUSD price units.

Field rule 134: a one-dollar move equals 100 points. One point is 0.01 in price.
One standard lot is 100 troy ounces, so a one-dollar move is 100 currency units per lot.
"""

from __future__ import annotations

POINT = 0.01
POINTS_PER_DOLLAR = 100
OUNCES_PER_LOT = 100.0
LOT_STEP = 0.01
MIN_LOT = 0.01


def price_to_points(distance: float) -> float:
    return abs(distance) / POINT


def loss_per_lot(stop_distance: float) -> float:
    """Currency loss on 1.00 lot if price travels `stop_distance` against the position."""
    return abs(stop_distance) * OUNCES_PER_LOT
