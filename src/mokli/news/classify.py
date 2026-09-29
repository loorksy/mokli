"""Numeric fingerprints from the news-candle rulebook.

Time-of-day names, headlines, and cross-market symbols are not inferred here.
Those stay with the caller. This function fires only when the supplied statistic
crosses the threshold written in the rule.
"""

from __future__ import annotations

from mokli.models import CandleStats, NewsClassification
from mokli.units import POINT

# Rule 17 states "more than 60 to 80 points". 70 is the midpoint of that band.
M1_NEWS_POINTS = 70.0


def classify_news_candle(stats: CandleStats) -> NewsClassification:
    if stats.atr <= 0:
        raise ValueError("atr must be positive")
    if stats.high < stats.low:
        raise ValueError("high must be at least low")

    fired: list[str] = []
    candle_range = stats.high - stats.low

    if candle_range > 3.0 * stats.atr:
        fired.append("candle.16")

    if (
        stats.timeframe == "M1"
        and not stats.dead_hours
        and candle_range / POINT > M1_NEWS_POINTS
    ):
        fired.append("candle.17")

    if (
        stats.timeframe == "M5"
        and stats.average_daily_range is not None
        and stats.average_daily_range > 0
        and candle_range > 0.40 * stats.average_daily_range
    ):
        fired.append("candle.18")

    if stats.prior_10_range_sum is not None and candle_range >= stats.prior_10_range_sum > 0:
        fired.append("candle.20")

    if stats.range_std is not None and stats.range_mean is not None and stats.range_std > 0:
        z_score = (candle_range - stats.range_mean) / stats.range_std
        if z_score > 4:
            fired.append("candle.30")

    if (
        stats.tick_volume is not None
        and stats.tick_volume_mean is not None
        and stats.tick_volume_std is not None
        and stats.tick_volume_std > 0
        and (stats.tick_volume - stats.tick_volume_mean) / stats.tick_volume_std > 3.5
    ):
        fired.append("candle.31")

    if (
        stats.spread_points is not None
        and stats.normal_spread_points is not None
        and stats.normal_spread_points > 0
        and stats.spread_points > 3.0 * stats.normal_spread_points
    ):
        fired.append("candle.46")

    if stats.seconds_from_calendar_event is not None and abs(stats.seconds_from_calendar_event) < 60:
        fired.append("candle.10")

    inevitable = "candle.16" in fired and "candle.31" in fired and "candle.46" in fired
    if inevitable:
        fired.append("candle.100")

    return NewsClassification(
        is_news_candle=bool(fired),
        inevitable=inevitable,
        rule_ids=tuple(fired),
    )
