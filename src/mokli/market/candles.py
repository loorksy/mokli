"""Candle math, synthetic series, CSV replay, and the ICE dollar-index formula."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread_points: float | None = None
    source: str = "simulator"

    @property
    def range(self) -> float:
        return self.high - self.low


def true_ranges(candles: list[Candle]) -> list[float]:
    values: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            values.append(candle.high - candle.low)
            continue
        previous = candles[index - 1].close
        values.append(max(candle.high - candle.low, abs(candle.high - previous), abs(candle.low - previous)))
    return values


def atr(candles: list[Candle], period: int = 14) -> float | None:
    ranges = true_ranges(candles)
    if len(ranges) < period:
        return None
    value = sum(ranges[:period]) / period
    for item in ranges[period:]:
        value = (value * (period - 1) + item) / period
    return value


def rsi(candles: list[Candle], period: int = 14) -> list[float | None]:
    if len(candles) < period + 1:
        return [None] * len(candles)
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(candles)):
        change = candles[index].close - candles[index - 1].close
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    output: list[float | None] = [None] * (period)
    output.append(_rsi_value(avg_gain, avg_loss))
    for index in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[index]) / period
        avg_loss = (avg_loss * (period - 1) + losses[index]) / period
        output.append(_rsi_value(avg_gain, avg_loss))
    return output


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    relative = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative))


def ema(values: list[float], period: int) -> list[float | None]:
    if len(values) < period:
        return [None] * len(values)
    seed = sum(values[:period]) / period
    output: list[float | None] = [None] * (period - 1)
    output.append(seed)
    alpha = 2.0 / (period + 1)
    current = seed
    for value in values[period:]:
        current = (value - current) * alpha + current
        output.append(current)
    return output


def macd(candles: list[Candle]) -> tuple[list[float | None], list[float | None]]:
    closes = [candle.close for candle in candles]
    fast = ema(closes, 12)
    slow = ema(closes, 26)
    line: list[float | None] = []
    for left, right in zip(fast, slow, strict=True):
        line.append(None if left is None or right is None else left - right)
    compact = [value if value is not None else 0.0 for value in line]
    signal = ema(compact, 9)
    for index, value in enumerate(line):
        if value is None:
            signal[index] = None
    return line, signal


def zscore(value: float, population: list[float]) -> float | None:
    if len(population) < 2:
        return None
    mean = sum(population) / len(population)
    variance = sum((item - mean) ** 2 for item in population) / len(population)
    std = math.sqrt(variance)
    if std == 0:
        return None
    return (value - mean) / std


DXY_CONSTANT = 50.14348112


def calculated_dxy(
    eurusd: float,
    usdjpy: float,
    gbpusd: float,
    usdcad: float,
    usdsek: float,
    usdchf: float,
) -> float:
    """ICE-style basket. The result is calculated, not a direct DXY print."""
    return (
        DXY_CONSTANT
        * eurusd**-0.576
        * usdjpy**0.136
        * gbpusd**-0.119
        * usdcad**0.091
        * usdsek**0.042
        * usdchf**0.036
    )


def synthetic_candles(
    count: int = 180,
    *,
    start: float = 2400.0,
    seed: int = 7,
    timeframe_minutes: int = 15,
    drift: float = 0.15,
) -> list[Candle]:
    """Deterministic walk used by replay tests. Source is always simulator."""
    rng = random.Random(seed)
    now = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    price = start
    candles: list[Candle] = []
    step = timedelta(minutes=timeframe_minutes)
    for index in range(count):
        change = drift + rng.uniform(-0.35, 0.45)
        open_ = price
        close = open_ + change
        high = max(open_, close) + rng.uniform(0.05, 0.25)
        low = min(open_, close) - rng.uniform(0.05, 0.2)
        volume = 80 + rng.random() * 40
        candles.append(
            Candle(
                time=now + step * index,
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 2),
                spread_points=18,
                source="simulator",
            )
        )
        price = close
    return candles


def trending_long_setup() -> list[Candle]:
    """A hand-built series with a higher low, a bullish fair-value gap, and room to 2R."""
    start = datetime(2026, 3, 2, 7, 0, tzinfo=timezone.utc)
    raw = [
        (2400, 2402, 2398, 2401),
        (2401, 2404, 2399, 2403),
        (2403, 2405, 2400, 2401),
        (2401, 2403, 2396, 2397),
        (2397, 2400, 2395, 2399),
        (2399, 2412, 2398, 2411),
        (2411, 2416, 2410, 2415),
        (2415, 2418, 2408, 2410),
        (2410, 2414, 2407, 2413),
        (2413, 2420, 2412, 2419),
    ]
    candles: list[Candle] = []
    for index, (open_, high, low, close) in enumerate(raw):
        candles.append(
            Candle(
                time=start + timedelta(minutes=15 * index),
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=100 + index * 5,
                spread_points=16,
                source="simulator",
            )
        )
    return candles


def load_csv(path: Path, *, source: str = "csv") -> list[Candle]:
    candles: list[Candle] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stamp = datetime.fromisoformat(row["time"])
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            spread = row.get("spread_points") or ""
            candles.append(
                Candle(
                    time=stamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0),
                    spread_points=float(spread) if spread else None,
                    source=source,
                )
            )
    return candles
