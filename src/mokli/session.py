"""Session clocks. Times are supplied by the caller. This module only compares them."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


def in_rollover_window(now: datetime, platform_tz: str = "UTC") -> bool:
    """Field rule 118: 23:55–00:15 platform time. The spread trap is not a trade window."""
    local = now.astimezone(ZoneInfo(platform_tz))
    current = local.timetz().replace(tzinfo=None)
    return current >= time(23, 55) or current < time(0, 15)


def minutes_until_session_close(now: datetime, close_at: time, session_tz: str) -> float:
    zone = ZoneInfo(session_tz)
    local = now.astimezone(zone)
    close_dt = datetime.combine(local.date(), close_at, tzinfo=zone)
    return (close_dt - local).total_seconds() / 60.0


def is_foundation_holiday(day: datetime, holiday_tz: str = "America/New_York") -> bool:
    """The named holidays the rulebook disables by date.

    Field rule 197 names New Year's Day and Thanksgiving. Field rule 127 names
    US bank holidays and gives Labor Day as the example. Other closures are a
    caller flag, not a guessed calendar.
    """
    local = day.astimezone(ZoneInfo(holiday_tz)).date()
    if local.month == 1 and local.day == 1:
        return True
    if local.month == 11 and local.weekday() == 3 and 22 <= local.day <= 28:
        return True
    if local.month == 9 and local.weekday() == 0 and local.day <= 7:
        return True
    return False
