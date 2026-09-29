"""Deterministic structure. The model may describe these marks. It does not compute them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from mokli.market.candles import Candle, atr, macd, rsi, zscore


@dataclass(frozen=True)
class Swing:
    kind: str
    index: int
    price: float
    time: datetime


@dataclass(frozen=True)
class Zone:
    kind: str
    start: float
    end: float
    index: int
    filled: str


def swing_points(candles: list[Candle], wing: int = 2) -> list[Swing]:
    points: list[Swing] = []
    for index in range(wing, len(candles) - wing):
        high = candles[index].high
        low = candles[index].low
        if all(candles[j].high < high for j in range(index - wing, index + wing + 1) if j != index):
            points.append(Swing("high", index, high, candles[index].time))
        if all(candles[j].low > low for j in range(index - wing, index + wing + 1) if j != index):
            points.append(Swing("low", index, low, candles[index].time))
    return points


def fair_value_gaps(candles: list[Candle]) -> list[Zone]:
    zones: list[Zone] = []
    for index in range(2, len(candles)):
        left = candles[index - 2]
        right = candles[index]
        if left.high < right.low:
            zones.append(_fill_state(candles, index, "bullish_fvg", right.low, left.high))
        elif left.low > right.high:
            zones.append(_fill_state(candles, index, "bearish_fvg", left.low, right.high))
    return zones


def _fill_state(candles: list[Candle], index: int, kind: str, top: float, bottom: float) -> Zone:
    filled = "open"
    for later in candles[index + 1 :]:
        if later.low <= bottom and later.high >= top:
            filled = "full"
            break
        if later.low < top and later.high > bottom:
            filled = "partial"
    return Zone(kind, min(bottom, top), max(bottom, top), index, filled)


def structure_shift(candles: list[Candle]) -> dict[str, object]:
    swings = swing_points(candles)
    highs = [item for item in swings if item.kind == "high"]
    lows = [item for item in swings if item.kind == "low"]
    bos = None
    choch = None
    if len(highs) >= 1 and len(lows) >= 1 and candles:
        last = candles[-1]
        if last.close > highs[-1].price and (len(lows) < 2 or lows[-1].price >= lows[-2].price):
            bos = "bullish"
        elif last.close < lows[-1].price and (len(highs) < 2 or highs[-1].price <= highs[-2].price):
            bos = "bearish"
        if len(lows) >= 1 and last.close < lows[-1].price and bos != "bearish":
            choch = "bearish"
        if len(highs) >= 1 and last.close > highs[-1].price and bos != "bullish":
            choch = "bullish"
    return {"swings": swings, "bos": bos, "choch": choch}


def equal_levels(swings: list[Swing], tolerance: float = 0.3) -> list[dict[str, float | str]]:
    found: list[dict[str, float | str]] = []
    for index, left in enumerate(swings):
        for right in swings[index + 1 :]:
            if left.kind == right.kind and abs(left.price - right.price) <= tolerance:
                found.append({"kind": left.kind, "price": round((left.price + right.price) / 2, 2)})
    return found


def liquidity_sweep(candles: list[Candle]) -> str | None:
    swings = swing_points(candles, wing=1)
    if len(candles) < 3 or not swings:
        return None
    last = candles[-1]
    prior_highs = [item.price for item in swings if item.kind == "high" and item.index < len(candles) - 1]
    prior_lows = [item.price for item in swings if item.kind == "low" and item.index < len(candles) - 1]
    if prior_highs and last.high > max(prior_highs) and last.close < max(prior_highs):
        return "bearish_sweep"
    if prior_lows and last.low < min(prior_lows) and last.close > min(prior_lows):
        return "bullish_sweep"
    return None


def fibonacci(candles: list[Candle]) -> dict[str, float | str] | None:
    if len(candles) < 2:
        return None
    highest = max(candles, key=lambda candle: candle.high)
    lowest = min(candles, key=lambda candle: candle.low)
    span = highest.high - lowest.low
    if span <= 0:
        return None
    if highest.time >= lowest.time:
        end = highest.high
        direction = "up"
    else:
        end = lowest.low
        direction = "down"
    levels: dict[str, float | str] = {}
    for ratio in (0.5, 0.618, 0.786):
        if direction == "up":
            levels[str(ratio)] = round(end - span * ratio, 2)
        else:
            levels[str(ratio)] = round(end + span * ratio, 2)
    midpoint = (highest.high + lowest.low) / 2
    price = candles[-1].close
    levels["premium_discount"] = "premium" if price > midpoint else "discount"
    levels["direction"] = direction
    return levels


def supply_demand(candles: list[Candle]) -> list[Zone]:
    zones: list[Zone] = []
    for index in range(1, len(candles) - 1):
        candle = candles[index]
        nxt = candles[index + 1]
        body = abs(nxt.close - nxt.open)
        if body < (nxt.high - nxt.low) * 0.6:
            continue
        if nxt.close > nxt.open and candle.close < candle.open:
            zones.append(Zone("demand", candle.low, max(candle.open, candle.close), index, "open"))
        if nxt.close < nxt.open and candle.close > candle.open:
            zones.append(Zone("supply", min(candle.open, candle.close), candle.high, index, "open"))
    return zones


def asian_range(candles: list[Candle]) -> dict[str, float] | None:
    zone = ZoneInfo("Asia/Tokyo")
    session = [
        candle
        for candle in candles
        if time(0, 0) <= candle.time.astimezone(zone).time() < time(9, 0)
    ]
    if not session:
        return None
    return {"high": max(candle.high for candle in session), "low": min(candle.low for candle in session)}


def candle_morphology(candle: Candle) -> str:
    span = candle.range or 1e-9
    body = abs(candle.close - candle.open)
    upper = candle.high - max(candle.open, candle.close)
    lower = min(candle.open, candle.close) - candle.low
    if body / span < 0.1:
        return "doji"
    if lower > body * 2 and upper < body:
        return "hammer"
    if upper > body * 2 and lower < body:
        return "shooting_star"
    if body / span >= 0.8:
        return "marubozu"
    return "standard"


def volume_zscore(candles: list[Candle]) -> float | None:
    if len(candles) < 5:
        return None
    history = [candle.volume for candle in candles[-51:-1]]
    return zscore(candles[-1].volume, history)


def rsi_divergence(candles: list[Candle]) -> str | None:
    values = rsi(candles)
    swings = [item for item in swing_points(candles) if item.kind == "high"]
    usable = [item for item in swings if item.index < len(values) and values[item.index] is not None]
    if len(usable) < 2:
        return None
    left, right = usable[-2], usable[-1]
    left_rsi = values[left.index]
    right_rsi = values[right.index]
    if left_rsi is None or right_rsi is None:
        return None
    if right.price > left.price and right_rsi < left_rsi:
        return "bearish"
    lows = [item for item in swing_points(candles) if item.kind == "low"]
    usable_lows = [item for item in lows if values[item.index] is not None]
    if len(usable_lows) >= 2:
        a, b = usable_lows[-2], usable_lows[-1]
        if b.price < a.price and (values[b.index] or 0) > (values[a.index] or 0):
            return "bullish"
    return None


def macd_divergence(candles: list[Candle]) -> str | None:
    line, _signal = macd(candles)
    highs = [item for item in swing_points(candles) if item.kind == "high" and line[item.index] is not None]
    if len(highs) < 2:
        return None
    left, right = highs[-2], highs[-1]
    left_macd = line[left.index]
    right_macd = line[right.index]
    if left_macd is None or right_macd is None:
        return None
    if right.price > left.price and right_macd < left_macd:
        return "bearish"
    return None


def analyze(candles: list[Candle]) -> dict[str, object]:
    structure = structure_shift(candles)
    swings = structure["swings"]
    assert isinstance(swings, list)
    return {
        "atr": atr(candles),
        "swings": [
            {"kind": item.kind, "price": item.price, "time": item.time.isoformat()} for item in swings
        ],
        "bos": structure["bos"],
        "choch": structure["choch"],
        "fvg": [
            {"kind": zone.kind, "low": zone.start, "high": zone.end, "filled": zone.filled}
            for zone in fair_value_gaps(candles)
        ],
        "supply_demand": [
            {"kind": zone.kind, "low": zone.start, "high": zone.end} for zone in supply_demand(candles)
        ],
        "equal_levels": equal_levels(swings),
        "sweep": liquidity_sweep(candles),
        "fibonacci": fibonacci(candles),
        "asian_range": asian_range(candles),
        "morphology": candle_morphology(candles[-1]) if candles else None,
        "volume_zscore": volume_zscore(candles),
        "rsi_divergence": rsi_divergence(candles),
        "macd_divergence": macd_divergence(candles),
        "last": candles[-1].close if candles else None,
        "source": candles[-1].source if candles else "unavailable",
    }
