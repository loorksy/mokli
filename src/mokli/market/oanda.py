"""OANDA v20 REST. Practice is the default host. Missing credentials stay UNAVAILABLE."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from mokli.market.candles import Candle

_HOSTS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

_GRANULARITY = {
    "M1": "M1",
    "M5": "M5",
    "M15": "M15",
    "M30": "M30",
    "H1": "H1",
    "H4": "H4",
    "D1": "D",
}


class OandaError(RuntimeError):
    pass


async def fetch_candles(
    *,
    token: str,
    environment: str,
    instrument: str = "XAU_USD",
    timeframe: str = "M15",
    count: int = 200,
) -> tuple[list[Candle], str]:
    if not token:
        return [], "UNAVAILABLE"
    if environment not in _HOSTS:
        raise OandaError("oanda environment must be practice or live")
    granularity = _GRANULARITY.get(timeframe)
    if granularity is None:
        raise OandaError("unsupported timeframe")
    url = f"{_HOSTS[environment]}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, str | int] = {"granularity": granularity, "count": count, "price": "MBA"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise OandaError(f"oanda status {response.status_code}")
    candles: list[Candle] = []
    for row in response.json().get("candles", []):
        if not row.get("complete", True):
            continue
        mid = row.get("mid") or {}
        bid = row.get("bid") or {}
        ask = row.get("ask") or {}
        spread = None
        if bid.get("c") and ask.get("c"):
            spread = (float(ask["c"]) - float(bid["c"])) / 0.01
        stamp = datetime.fromisoformat(row["time"].replace("Z", "+00:00")).astimezone(timezone.utc)
        candles.append(
            Candle(
                time=stamp,
                open=float(mid["o"]),
                high=float(mid["h"]),
                low=float(mid["l"]),
                close=float(mid["c"]),
                volume=float(row.get("volume") or 0),
                spread_points=spread,
                source="oanda",
            )
        )
    return candles, "LIVE"
