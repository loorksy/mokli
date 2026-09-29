"""Ordered capital gate. The first failing check is the blocking rule."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from mokli.models import Account, Check, Decision, DecisionStatus, Market, Proposal, RiskConfig
from mokli.risk.sizing import SizeError, reward_risk, size_position
from mokli.units import POINT


def cooldown_deadline(now: datetime, config: RiskConfig) -> datetime:
    return now + timedelta(minutes=config.cooldown_minutes)


def drawdown_fraction(account: Account) -> float:
    if account.day_start_equity <= 0 or not math.isfinite(account.day_start_equity):
        raise ValueError("day_start_equity must be a positive finite number")
    if not math.isfinite(account.equity):
        raise ValueError("equity must be finite")
    return (account.day_start_equity - account.equity) / account.day_start_equity


def pending_order_expired(age_hours: float, config: RiskConfig) -> bool:
    """Field rule 183. Three hours unfilled cancels the order. Rule 12's four hours loses."""
    if age_hours < 0 or not math.isfinite(age_hours):
        raise ValueError("age_hours must be a non-negative finite number")
    return age_hours >= config.pending_order_max_age_hours


def daily_lock_status(account: Account, config: RiskConfig | None = None) -> Decision:
    config = config or RiskConfig()
    checks: list[Check] = []
    if account.kill_switch:
        checks.append(Check("sec.7.1", False, "Kill switch is on."))
        return _decision(checks, config, locked=True, flatten=True)
    fraction = drawdown_fraction(account)
    if account.daily_lock or fraction >= config.daily_loss_fraction:
        checks.append(
            Check(
                "field.191",
                False,
                f"Daily loss {fraction:.4%} has reached the {config.daily_loss_fraction:.2%} cap.",
            )
        )
        return _decision(checks, config, locked=True, flatten=True)
    checks.append(Check("field.191", True, f"Daily loss {fraction:.4%} is inside the cap."))
    return _decision(checks, config, locked=False, flatten=False)


def evaluate_proposal(
    proposal: Proposal,
    account: Account,
    market: Market,
    config: RiskConfig | None = None,
) -> Decision:
    config = config or RiskConfig()
    _require_market(market)
    checks: list[Check] = []

    if account.kill_switch:
        checks.append(
            Check("sec.7.1", False, "Kill switch is on. Flatten positions and cancel pending orders.")
        )
        return _decision(checks, config, locked=True, flatten=True)

    fraction = drawdown_fraction(account)
    if account.daily_lock or fraction >= config.daily_loss_fraction:
        checks.append(
            Check(
                "field.191",
                False,
                f"Daily loss {fraction:.4%} has reached the {config.daily_loss_fraction:.2%} cap.",
            )
        )
        return _decision(checks, config, locked=True, flatten=True)
    checks.append(Check("field.191", True, f"Daily loss {fraction:.4%} is inside the cap."))

    if _cooldown_active(account, market.now, config):
        checks.append(
            Check("field.187", False, "Two session losses are in. New orders stay blocked for the cooldown.")
        )
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.187", True, "Cooldown is clear."))

    if market.tick_age_seconds > config.stale_tick_seconds or market.tick_age_seconds < -1:
        checks.append(Check("field.189", False, "The latest tick is stale or clock-skewed. Send is cancelled."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.189", True, "Tick age is inside the send window."))

    if _bad_tick(market, config):
        checks.append(Check("sec.7.4", False, "The tick jumped beyond the bad-tick multiple of ATR."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("sec.7.4", True, "Tick is inside the bad-tick band."))

    news_block = _news_block(proposal, config)
    if news_block is not None:
        checks.append(news_block)
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("news.1", True, "No pre-release freeze and no first-minute void."))

    normal_spread = market.normal_spread_points or config.normal_spread_points
    spread_points = market.spread_price / POINT
    if spread_points > config.max_spread_multiple * normal_spread:
        checks.append(
            Check(
                "cap.3.3",
                False,
                f"Spread {spread_points:.1f} points is above {config.max_spread_multiple:.0f}× normal.",
            )
        )
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("cap.3.3", True, f"Spread {spread_points:.1f} points is tradable."))

    if proposal.holiday:
        checks.append(Check("field.197", False, "The session is a disabled holiday."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.197", True, "Not a disabled holiday."))

    if proposal.in_rollover_window:
        checks.append(Check("field.118", False, "Platform rollover window. No new trade and no tight stop."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.118", True, "Outside the rollover window."))

    if _near_session_close(proposal, config):
        checks.append(Check("field.195", False, "Inside the last 15 minutes before the session close."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.195", True, "Session-close blackout is clear."))

    if account.open_positions >= config.max_open_positions:
        checks.append(Check("cap.3.5", False, "Open gold positions are already at the cap."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("cap.3.5", True, "Position count is under the cap."))

    if proposal.side == "sell" and proposal.geopolitical_escalation:
        checks.append(Check("news.88", False, "Safe-haven escalation is active. A new short is banned."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("news.88", True, "Short ban is not active."))

    if not proposal.reason_code.strip():
        checks.append(Check("field.194", False, "The order comment has no technical reason code."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.194", True, "Reason code is present."))

    if not proposal.higher_timeframe_agrees:
        checks.append(Check("field.198", False, "Higher timeframe and the entry timeframe disagree."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.198", True, "Timeframes agree."))

    if account.same_direction_loser_open:
        checks.append(Check("field.184", False, "A same-direction gold position is already open and losing."))
        return _decision(checks, config, locked=False, flatten=False)
    checks.append(Check("field.184", True, "No same-direction loser is open."))

    ratio = reward_risk(proposal.side, proposal.entry, proposal.stop, proposal.target)
    if ratio < config.min_reward_risk:
        checks.append(
            Check(
                "cap.3.6",
                False,
                f"Planned reward/risk is {ratio:.2f}. New risk needs at least {config.min_reward_risk:.1f}.",
            )
        )
        return _decision(checks, config, locked=False, flatten=False, reward_risk=ratio)
    checks.append(Check("cap.3.6", True, f"Planned reward/risk is {ratio:.2f}."))

    risk_fraction = config.event_day_risk_fraction if proposal.event_day else config.risk_fraction
    try:
        sized = size_position(account.balance, proposal.entry, proposal.stop, risk_fraction)
    except SizeError as exc:
        checks.append(Check("field.47", False, str(exc)))
        return _decision(checks, config, locked=False, flatten=False, reward_risk=ratio)
    checks.append(
        Check(
            "field.188",
            True,
            f"Lot {sized.lots:.2f} risks {sized.risk_amount:.2f} against a {sized.budget:.2f} budget.",
        )
    )
    return _decision(
        checks,
        config,
        locked=False,
        flatten=False,
        lots=sized.lots,
        risk_amount=sized.risk_amount,
        reward_risk=ratio,
    )


def _cooldown_active(account: Account, now: datetime, config: RiskConfig) -> bool:
    if account.consecutive_losses < config.consecutive_losses_to_cool:
        return False
    if account.cooldown_until is None:
        return True
    return now < account.cooldown_until


def _bad_tick(market: Market, config: RiskConfig) -> bool:
    if market.last_mid is None:
        return False
    return abs(market.mid - market.last_mid) > config.bad_tick_atr_multiple * market.atr


def _news_block(proposal: Proposal, config: RiskConfig) -> Check | None:
    minutes = proposal.minutes_to_high_impact
    if minutes is None:
        return None
    if 0 <= minutes <= config.news_freeze_minutes:
        return Check("news.1", False, "Inside the pre-release freeze. No new trade.")
    seconds_since = -minutes * 60.0
    if 0 < seconds_since < 60:
        return Check("news.35", False, "First 60 seconds after the print. No entry.")
    return None


def _near_session_close(proposal: Proposal, config: RiskConfig) -> bool:
    minutes = proposal.minutes_to_session_close
    if minutes is None:
        return False
    return 0 <= minutes <= config.no_trade_before_close_minutes


def _require_market(market: Market) -> None:
    values = (market.bid, market.ask, market.atr)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("bid, ask, and atr must be finite")
    if market.bid <= 0 or market.ask <= 0 or market.ask < market.bid:
        raise ValueError("bid and ask must be positive and ask must be at least bid")
    if market.atr <= 0:
        raise ValueError("atr must be positive")


def execution_recheck(
    proposal: Proposal,
    account: Account,
    market: Market,
    config: RiskConfig | None = None,
) -> Decision:
    """Fresh check immediately before a fill.

    A proposal must have been planned at the configured minimum (default 2R).
    By the time the order is sent, reward/risk may have slipped. The send is
    cancelled only when it falls through the execution floor (default 1.5R).
    """
    config = config or RiskConfig()
    _require_market(market)
    checks: list[Check] = []
    fraction = drawdown_fraction(account)
    if account.kill_switch or account.daily_lock or fraction >= config.daily_loss_fraction:
        checks.append(Check("field.191", False, "Account is locked. Execution is refused."))
        return _decision(checks, config, locked=True, flatten=account.kill_switch or fraction >= config.daily_loss_fraction)
    if market.tick_age_seconds > config.stale_tick_seconds:
        checks.append(Check("field.189", False, "Quote went stale before the fill."))
        return _decision(checks, config, locked=False, flatten=False)
    normal_spread = market.normal_spread_points or config.normal_spread_points
    spread_points = market.spread_price / POINT
    if spread_points > config.max_spread_multiple * normal_spread:
        checks.append(Check("cap.3.3", False, "Spread widened before the fill."))
        return _decision(checks, config, locked=False, flatten=False)
    ratio = reward_risk(proposal.side, proposal.entry, proposal.stop, proposal.target)
    if ratio < config.execution_min_reward_risk:
        checks.append(
            Check(
                "policy.exec_rr",
                False,
                f"Live reward/risk {ratio:.2f} is below the {config.execution_min_reward_risk:.1f} execution floor.",
            )
        )
        return _decision(checks, config, locked=False, flatten=False, reward_risk=ratio)
    checks.append(Check("policy.exec_rr", True, f"Live reward/risk {ratio:.2f} still clears the execution floor."))
    return _decision(checks, config, locked=False, flatten=False, reward_risk=ratio)


def _decision(
    checks: list[Check],
    config: RiskConfig,
    *,
    locked: bool,
    flatten: bool,
    lots: float | None = None,
    risk_amount: float | None = None,
    reward_risk: float | None = None,
) -> Decision:
    failed = next((check for check in checks if not check.ok), None)
    status: DecisionStatus
    if locked:
        status = "locked"
    elif failed is not None:
        status = "rejected"
    elif config.execution_mode == "autonomous":
        status = "approved"
    else:
        status = "pending_confirmation"
    return Decision(
        status=status,
        checks=tuple(checks),
        lots=lots,
        risk_amount=risk_amount,
        reward_risk=reward_risk,
        flatten_required=flatten,
        blocking_rule_id=None if failed is None else failed.rule_id,
    )
