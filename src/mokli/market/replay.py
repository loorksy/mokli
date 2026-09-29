"""Replay clock. A missing book stays UNAVAILABLE. Simulator bars stay labeled."""

from __future__ import annotations

from dataclasses import dataclass

from mokli.market.candles import Candle


@dataclass
class ReplayClock:
    index: int = -1

    def arm(self, count: int, start: int = 40) -> int:
        if count <= 0:
            self.index = -1
            return self.index
        self.index = min(max(start, 0), count - 1)
        return self.index

    def step(self, count: int) -> int:
        if count <= 0:
            self.index = -1
            return self.index
        if self.index < 0:
            self.index = 0
        elif self.index < count - 1:
            self.index += 1
        return self.index


def quote_from_candle(candle: Candle, point: float) -> tuple[float, float]:
    spread_points = candle.spread_points if candle.spread_points is not None else 18.0
    half = (spread_points * point) / 2
    return candle.close - half, candle.close + half


def market_status(
    candles: list[Candle],
    index: int,
    *,
    bid: float,
    ask: float,
    killed: bool,
) -> dict[str, object]:
    if not candles or index < 0 or index >= len(candles):
        return {
            "state": "UNAVAILABLE",
            "source": "UNAVAILABLE",
            "index": index,
            "total": len(candles),
            "bid": None,
            "ask": None,
            "freshness": None,
            "spread_points": None,
            "killed": killed,
        }
    candle = candles[index]
    spread = None if bid <= 0 or ask <= 0 else round((ask - bid) / 0.01, 2)
    source = "SIMULATOR" if candle.source == "simulator" else candle.source.upper()
    return {
        "state": source,
        "source": candle.source,
        "index": index,
        "total": len(candles),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "freshness": candle.time.isoformat(),
        "spread_points": spread,
        "close": candle.close,
        "killed": killed,
    }
