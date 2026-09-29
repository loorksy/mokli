"""Chat confirmation. Silence, refusal, and expiry do not send an order."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

PROPOSAL_TTL = timedelta(minutes=30)

_MARKS = str.maketrans("", "", "؟?!.,،")
_YES = {"نعم", "نفذ", "انفذ", "موافق", "yes", "execute", "confirm"}
_NO = {"لا", "رفض", "no", "reject", "لا تنفذ"}


def fold_reply(message: str) -> str:
    folded = message.casefold().strip().translate(_MARKS).strip()
    for mark in ("أ", "إ", "آ"):
        folded = folded.replace(mark, "ا")
    folded = re.sub(r"[\u064b-\u0652]", "", folded)
    return " ".join(folded.split())


def reply_kind(message: str) -> str | None:
    folded = fold_reply(message)
    if folded in _YES:
        return "yes"
    if folded in _NO:
        return "no"
    return None


def proposal_expired(created_at: datetime, now: datetime, ttl: timedelta = PROPOSAL_TTL) -> bool:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now - created_at > ttl
