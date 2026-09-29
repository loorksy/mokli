"""Optional Telegram channel. Missing credentials are UNAVAILABLE, not a silent drop."""

from __future__ import annotations

import httpx


async def send_telegram(token: str, chat_id: str, text: str) -> str:
    if not token or not chat_id:
        return "UNAVAILABLE"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json={"chat_id": chat_id, "text": text})
    if response.status_code != 200:
        return "DEGRADED"
    return "LIVE"
