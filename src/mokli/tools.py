"""Callable surface of this foundation. Names here match the system contract."""

from __future__ import annotations

from mokli.journal import read_lessons, record_lesson
from mokli.news.classify import classify_news_candle
from mokli.risk.guardrails import (
    cooldown_deadline,
    daily_lock_status,
    drawdown_fraction,
    evaluate_proposal,
    pending_order_expired,
)
from mokli.risk.sizing import reward_risk, size_position
from mokli.risk.stops import breakeven_allowed, structural_stop, validate_stop_change

# Product default for staged targets. Field rule 137 (half off at 1R) stays in the
# rulebook as a heuristic. Debate can cite it. Execution uses this schedule.
SCALE_OUT = (
    ("target_one", 0.40),
    ("target_two", 0.30),
    ("runner", 0.30),
)


def scale_out_schedule() -> tuple[tuple[str, float], ...]:
    """Resolved partial-close schedule. The fractions sum to 1."""
    total = sum(fraction for _, fraction in SCALE_OUT)
    if abs(total - 1.0) > 1e-9:
        raise RuntimeError("scale-out fractions must sum to 1")
    return SCALE_OUT


__all__ = [
    "breakeven_allowed",
    "classify_news_candle",
    "cooldown_deadline",
    "daily_lock_status",
    "drawdown_fraction",
    "evaluate_proposal",
    "pending_order_expired",
    "read_lessons",
    "record_lesson",
    "reward_risk",
    "scale_out_schedule",
    "size_position",
    "structural_stop",
    "validate_stop_change",
]
