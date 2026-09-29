"""One analysis pass: snapshot, debate, deterministic proposal, risk, approval."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from mokli.analysis.detectors import analyze
from mokli.execution.paper import PaperBroker
from mokli.market.candles import Candle, atr
from mokli.models import Account, Market, Proposal, RiskConfig
from mokli.news.machine import NewsState, news_state
from mokli.risk.guardrails import evaluate_proposal
from mokli.risk.stops import structural_stop
from mokli.units import POINT


@dataclass
class RoleNote:
    role: str
    text: str
    evidence: list[str]


@dataclass
class CycleResult:
    decision_id: str
    verdict: str
    proposal: dict[str, object] | None
    risk_status: str | None
    blocking_rule: str | None
    notes: list[RoleNote]
    snapshot: dict[str, object]
    approval_id: str | None


def build_proposal(candles: list[Candle], snapshot: dict[str, object], config: RiskConfig) -> Proposal | None:
    if len(candles) < 5 or snapshot.get("atr") in (None, 0):
        return None
    last = candles[-1].close
    raw_atr = snapshot.get("atr")
    if not isinstance(raw_atr, int | float):
        return None
    volatility = float(raw_atr)
    swings = snapshot.get("swings")
    if not isinstance(swings, list):
        return None
    lows = [float(item["price"]) for item in swings if isinstance(item, dict) and item.get("kind") == "low"]
    highs = [float(item["price"]) for item in swings if isinstance(item, dict) and item.get("kind") == "high"]
    bullish = snapshot.get("bos") == "bullish" or snapshot.get("sweep") == "bullish_sweep"
    bearish = snapshot.get("bos") == "bearish" or snapshot.get("sweep") == "bearish_sweep"
    if bullish and not bearish and lows:
        invalidation = min(lows[-1], min(candle.low for candle in candles[-4:]))
        stop = structural_stop("buy", invalidation, volatility, config)
        risk = last - stop
        if risk <= 0:
            return None
        return Proposal(
            side="buy",
            entry=round(last, 2),
            stop=round(stop, 2),
            target=round(last + risk * config.min_reward_risk, 2),
            reason_code="BOS_OR_SWEEP_BUY",
            higher_timeframe_agrees=True,
        )
    if bearish and not bullish and highs:
        invalidation = max(highs[-1], max(candle.high for candle in candles[-4:]))
        stop = structural_stop("sell", invalidation, volatility, config)
        risk = stop - last
        if risk <= 0:
            return None
        return Proposal(
            side="sell",
            entry=round(last, 2),
            stop=round(stop, 2),
            target=round(last - risk * config.min_reward_risk, 2),
            reason_code="BOS_OR_SWEEP_SELL",
            higher_timeframe_agrees=True,
        )
    return None


def debate(snapshot: dict[str, object], proposal: Proposal | None, news: NewsState) -> list[RoleNote]:
    evidence = _evidence(snapshot)
    bull = [item for item in evidence if "bull" in item or item.startswith("discount")]
    bear = [item for item in evidence if "bear" in item or item.startswith("premium")]
    notes = [
        RoleNote("bull", _sentence("The bull case uses only printed structure.", bull), bull),
        RoleNote("bear", _sentence("The bear case uses only printed structure.", bear), bear),
        RoleNote(
            "greed",
            "Size stays at the configured fraction. A clean structure is not a reason to add risk.",
            ["cap.3.1"],
        ),
        RoleNote(
            "emotion",
            "If the book is unclear, standing aside is the position.",
            ["field.181"],
        ),
        RoleNote(
            "professional",
            _verdict_text(proposal, news),
            evidence,
        ),
    ]
    return notes


def _evidence(snapshot: dict[str, object]) -> list[str]:
    items: list[str] = []
    if snapshot.get("bos"):
        items.append(f"{snapshot['bos']}_bos")
    if snapshot.get("choch"):
        items.append(f"{snapshot['choch']}_choch")
    if snapshot.get("sweep"):
        items.append(str(snapshot["sweep"]))
    fib = snapshot.get("fibonacci") or {}
    if isinstance(fib, dict) and fib.get("premium_discount"):
        items.append(str(fib["premium_discount"]))
    return items


def _sentence(prefix: str, evidence: list[str]) -> str:
    if not evidence:
        return prefix + " No confirming mark is on the snapshot."
    return prefix + " Marks: " + ", ".join(evidence) + "."


def _verdict_text(proposal: Proposal | None, news: NewsState) -> str:
    if not news.new_trades_allowed:
        return f"News phase is {news.phase.value}. No new risk."
    if proposal is None:
        return "No side has a structural invalidation that still pays the minimum reward. Wait."
    return (
        f"Propose {proposal.side} at {proposal.entry} stop {proposal.stop} "
        f"target {proposal.target}. Risk still has to accept it."
    )


def market_from_broker(broker: PaperBroker, when: datetime, volatility: float) -> Market:
    return Market(
        bid=broker.bid,
        ask=broker.ask,
        tick_time=when,
        now=when,
        atr=max(volatility, POINT),
        normal_spread_points=20,
    )


def run_cycle(
    candles: list[Candle],
    broker: PaperBroker,
    *,
    when: datetime | None = None,
    event_time: datetime | None = None,
    account: Account | None = None,
    config: RiskConfig | None = None,
    open_positions: int = 0,
) -> CycleResult:
    config = config or RiskConfig()
    when = when or datetime.now(timezone.utc)
    snapshot = analyze(candles) if candles else {"source": "unavailable"}
    news = news_state(when, event_time)
    proposal = build_proposal(candles, snapshot, config) if candles else None
    if proposal is not None and not news.new_trades_allowed:
        proposal = Proposal(
            side=proposal.side,
            entry=proposal.entry,
            stop=proposal.stop,
            target=proposal.target,
            reason_code=proposal.reason_code,
            higher_timeframe_agrees=proposal.higher_timeframe_agrees,
            event_day=True,
            minutes_to_high_impact=max((event_time - when).total_seconds() / 60, 0) if event_time else 0,
        )
    notes = debate(snapshot, proposal, news)
    decision_id = uuid.uuid4().hex[:12]
    risk_status: str | None = None
    blocking = None
    payload: dict[str, object] | None = None
    if proposal is not None and broker.bid > 0:
        volatility = atr(candles) or POINT
        account = account or Account(
            balance=broker.balance,
            equity=broker.equity(),
            day_start_equity=broker.balance,
            open_positions=open_positions,
        )
        decision = evaluate_proposal(proposal, account, market_from_broker(broker, when, volatility), config)
        risk_status = decision.status
        blocking = decision.blocking_rule_id
        built: dict[str, object] = {
            "side": proposal.side,
            "entry": proposal.entry,
            "stop": proposal.stop,
            "target": proposal.target,
            "lots": decision.lots,
            "reward_risk": decision.reward_risk,
            "reason_code": proposal.reason_code,
            "checks": [
                {"rule_id": check.rule_id, "ok": check.ok, "detail": check.detail} for check in decision.checks
            ],
        }
        payload = built
    elif proposal is None:
        risk_status = "no_proposal"
    verdict = "wait" if payload is None or risk_status not in {"approved", "pending_confirmation"} else proposal.side  # type: ignore[union-attr]
    return CycleResult(
        decision_id=decision_id,
        verdict=verdict if isinstance(verdict, str) else "wait",
        proposal=payload,
        risk_status=risk_status,
        blocking_rule=blocking,
        notes=notes,
        snapshot=snapshot,
        approval_id=None,
    )


def cycle_json(result: CycleResult) -> str:
    return json.dumps(
        {
            "decision_id": result.decision_id,
            "verdict": result.verdict,
            "proposal": result.proposal,
            "risk_status": result.risk_status,
            "blocking_rule": result.blocking_rule,
            "notes": [{"role": note.role, "text": note.text, "evidence": note.evidence} for note in result.notes],
        }
    )
