"""Bots described in chat. A saved bot does not place an order."""

from __future__ import annotations

import re
import uuid

_TYPES = (
    ("mean_reversion", ("mean-reversion", "mean reversion", "ارتداد")),
    ("breakout", ("breakout", "اختراق")),
    ("grid", ("grid", "شبكة")),
    ("session", ("session bot", "بوت جلسة")),
    ("trend", ("trend", "اتجاه", "ترند")),
)
_TYPE_LABELS = {
    "trend": "اتجاه",
    "mean_reversion": "ارتداد",
    "breakout": "اختراق",
    "session": "جلسة",
    "grid": "شبكة",
    "custom": "مخصص",
}


def looks_like_bot(message: str) -> bool:
    folded = message.casefold()
    return any(token in folded or token in message for token in ("بوت", "روبوت", "bot"))


def bot_command(message: str) -> str | None:
    folded = message.casefold()
    text = f"{folded} {message}"
    if any(token in text for token in ("احذف البوت", "امسح البوت", "delete bot", "delete the bot")):
        return "delete"
    if any(token in text for token in ("أوقف البوت", "اوقف البوت", "pause bot", "pause the bot")):
        return "pause"
    if any(token in text for token in ("شغّل البوت", "شغل البوت", "resume bot", "resume the bot")):
        return "resume"
    if any(token in text for token in ("عدّل البوت", "عدل البوت", "edit bot", "edit the bot")):
        return "edit"
    if any(token in text for token in ("إشارة البوت", "اشارة البوت", "bot signal")):
        return "signal"
    if looks_like_bot(message):
        return "create"
    return None


def parse_bot(message: str) -> dict[str, str]:
    folded = message.casefold()
    kind = "custom"
    for name, words in _TYPES:
        if any(word in folded or word in message for word in words):
            kind = name
            break
    instrument = "XAUUSD"
    symbol = re.search(r"\b(XAUUSD|EURUSD|GBPUSD|USDJPY)\b", message, re.IGNORECASE)
    if symbol:
        instrument = symbol.group(1).upper()
    if any(token in message or token in folded for token in ("ذهب", "gold", "xau")):
        instrument = "XAUUSD"
    timeframe = "M15"
    if any(token in message or token in folded for token in ("ساعة", "ساعه", "h1")):
        timeframe = "H1"
    elif any(token in folded for token in ("h4", "4h")) or "أربع" in message:
        timeframe = "H4"
    elif "m5" in folded:
        timeframe = "M5"
    session = "all"
    if "لندن" in message or "london" in folded:
        session = "London"
    elif "نيويورك" in message or "new york" in folded:
        session = "New York"
    elif any(token in message for token in ("آسيا", "اسيا")) or "asia" in folded:
        session = "Asia"
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", message)
    size_rule = f"{percent.group(1)}% of equity" if percent else "configured risk fraction"
    return {
        "id": uuid.uuid4().hex[:12],
        "name": f"{_TYPE_LABELS[kind]} {instrument}",
        "kind": kind,
        "instrument": instrument,
        "timeframe": timeframe,
        "entry": _clause(message, ("دخول", "entry")) or _default_entry(kind),
        "exit": _clause(message, ("خروج", "exit")) or _default_exit(kind),
        "stop": _clause(message, ("وقف", "stop")) or "beyond the structure",
        "size_rule": size_rule,
        "session": session,
        "status": "active",
    }


def _default_entry(kind: str) -> str:
    if kind == "mean_reversion":
        return "fade the extreme back toward the mean"
    if kind == "breakout":
        return "break of the printed structure"
    if kind == "grid":
        return "grid around the session price"
    if kind == "session":
        return "trade only inside the named session"
    if kind == "trend":
        return "with the trend after a break"
    return "as described"


def _default_exit(kind: str) -> str:
    if kind == "mean_reversion":
        return "at the mean"
    return "at the planned target"


def _clause(message: str, labels: tuple[str, ...]) -> str:
    pattern = "|".join(re.escape(label) for label in labels)
    found = re.search(rf"(?:{pattern})\s*[:\-]?\s*([^،,\n]+)", message, re.IGNORECASE)
    if found is None:
        return ""
    text = found.group(1).strip()
    for stop in ("خروج", "وقف", "مخاطرة", "جلسة", "entry", "exit", "stop"):
        if stop in text and stop not in labels:
            text = text.split(stop)[0].strip()
    return text
