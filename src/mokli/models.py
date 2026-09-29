"""Facts the guardrails are allowed to read. Callers supply them. Nothing here is fetched."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Side = Literal["buy", "sell"]
Outcome = Literal["loss", "win", "scratch", "skipped"]
DecisionStatus = Literal["approved", "pending_confirmation", "rejected", "locked"]
Timeframe = Literal["M1", "M5", "M15", "H1", "H4"]


@dataclass(frozen=True)
class RiskConfig:
    """Operator limits.

    The caps are the foundation defaults from the capability rules: at most 2% of
    balance at risk on one idea, at most 3% day-loss, and a planned reward at least
    twice the risk. A config that asks for more is rejected at construction.
    """

    risk_fraction: float = 0.01
    event_day_risk_fraction: float = 0.005
    daily_loss_fraction: float = 0.03
    min_reward_risk: float = 2.0
    max_open_positions: int = 2
    max_spread_multiple: float = 3.0
    normal_spread_points: float = 20.0
    stale_tick_seconds: float = 5.0
    cooldown_minutes: int = 120
    execution_min_reward_risk: float = 1.5
    consecutive_losses_to_cool: int = 2
    bad_tick_atr_multiple: float = 5.0
    min_stop_buffer_points: float = 25.0
    stop_buffer_atr_fraction: float = 0.5
    news_freeze_minutes: int = 15
    pending_order_max_age_hours: float = 3.0
    no_trade_before_close_minutes: int = 15
    execution_mode: Literal["confirm", "autonomous"] = "confirm"

    def __post_init__(self) -> None:
        if not 0 < self.risk_fraction <= 0.02:
            raise ValueError("risk_fraction must be in (0, 0.02]")
        if not 0 < self.event_day_risk_fraction <= self.risk_fraction:
            raise ValueError("event_day_risk_fraction must be in (0, risk_fraction]")
        if not 0 < self.daily_loss_fraction <= 0.03:
            raise ValueError("daily_loss_fraction must be in (0, 0.03]")
        if self.min_reward_risk < 2.0:
            raise ValueError("min_reward_risk cannot be set below 2")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.max_spread_multiple < 1:
            raise ValueError("max_spread_multiple must be at least 1")
        if self.normal_spread_points <= 0:
            raise ValueError("normal_spread_points must be positive")
        if self.stale_tick_seconds <= 0:
            raise ValueError("stale_tick_seconds must be positive")
        if not 60 <= self.cooldown_minutes <= 240:
            raise ValueError("cooldown_minutes must be between 60 and 240")
        if self.execution_min_reward_risk < 1.5:
            raise ValueError("execution_min_reward_risk cannot be set below 1.5")
        if self.consecutive_losses_to_cool < 2:
            raise ValueError("consecutive_losses_to_cool cannot be below 2")
        if self.bad_tick_atr_multiple <= 0:
            raise ValueError("bad_tick_atr_multiple must be positive")
        if self.min_stop_buffer_points < 25:
            raise ValueError("min_stop_buffer_points cannot be below 25")
        if self.stop_buffer_atr_fraction <= 0:
            raise ValueError("stop_buffer_atr_fraction must be positive")
        if self.news_freeze_minutes < 15:
            raise ValueError("news_freeze_minutes cannot be shorter than 15")
        if self.pending_order_max_age_hours <= 0 or self.pending_order_max_age_hours > 3:
            raise ValueError("pending_order_max_age_hours must be in (0, 3]")
        if self.no_trade_before_close_minutes < 15:
            raise ValueError("no_trade_before_close_minutes cannot be shorter than 15")
        if self.execution_mode not in ("confirm", "autonomous"):
            raise ValueError("execution_mode must be confirm or autonomous")


@dataclass(frozen=True)
class Account:
    balance: float
    equity: float
    day_start_equity: float
    open_positions: int = 0
    consecutive_losses: int = 0
    cooldown_until: datetime | None = None
    same_direction_loser_open: bool = False
    kill_switch: bool = False
    daily_lock: bool = False


@dataclass(frozen=True)
class Market:
    bid: float
    ask: float
    tick_time: datetime
    now: datetime
    atr: float
    last_mid: float | None = None
    normal_spread_points: float | None = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_price(self) -> float:
        return self.ask - self.bid

    @property
    def tick_age_seconds(self) -> float:
        return (self.now - self.tick_time).total_seconds()


@dataclass(frozen=True)
class Proposal:
    side: Side
    entry: float
    stop: float
    target: float
    reason_code: str
    higher_timeframe_agrees: bool
    event_day: bool = False
    minutes_to_high_impact: float | None = None
    minutes_to_session_close: float | None = None
    in_rollover_window: bool = False
    holiday: bool = False
    geopolitical_escalation: bool = False


@dataclass(frozen=True)
class Check:
    rule_id: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class SizeResult:
    lots: float
    risk_amount: float
    budget: float
    stop_distance: float


@dataclass(frozen=True)
class Decision:
    status: DecisionStatus
    checks: tuple[Check, ...]
    lots: float | None
    risk_amount: float | None
    reward_risk: float | None
    flatten_required: bool
    blocking_rule_id: str | None

    @property
    def allowed_to_stage(self) -> bool:
        return self.status in ("approved", "pending_confirmation")


@dataclass(frozen=True)
class CandleStats:
    timeframe: Timeframe
    high: float
    low: float
    open: float
    close: float
    atr: float
    tick_volume: float | None = None
    tick_volume_mean: float | None = None
    tick_volume_std: float | None = None
    range_mean: float | None = None
    range_std: float | None = None
    spread_points: float | None = None
    normal_spread_points: float | None = None
    average_daily_range: float | None = None
    dead_hours: bool = False
    prior_10_range_sum: float | None = None
    seconds_from_calendar_event: float | None = None


@dataclass(frozen=True)
class NewsClassification:
    is_news_candle: bool
    inevitable: bool
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class Lesson:
    rule_id: str
    summary: str
    outcome: Outcome
    created_at: datetime
