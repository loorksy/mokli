"""Heartbeat stays quiet when the last candle is inside a dead range."""

from __future__ import annotations

from mokli.market.candles import Candle, atr


def heartbeat_action(candles: list[Candle], note: str) -> str | None:
    if "stay silent" not in note.lower() and "silent" not in note.lower():
        return "review"
    if len(candles) < 15:
        return None
    volatility = atr(candles)
    if volatility is None:
        return None
    if candles[-1].range < volatility * 0.35:
        return None
    return "review"
