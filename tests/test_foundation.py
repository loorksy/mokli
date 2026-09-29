from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mokli.agent.mcp_bridge import analysis_server, assert_mcp_tool_allowed
from mokli.analysis.detectors import analyze, fair_value_gaps
from mokli.config import Settings
from mokli.execution.paper import PaperBroker
from mokli.execution.reconcile import reconcile
from mokli.market.candles import atr, calculated_dxy, synthetic_candles, trending_long_setup
from mokli.models import Account, Market, Proposal, RiskConfig
from mokli.news.machine import NewsPhase, news_state
from mokli.providers.openai_runtime import run_with_snapshot_tool
from mokli.risk.guardrails import evaluate_proposal, execution_recheck
from mokli.risk.sizing import size_position
from mokli.skills import parse_skill


def test_lot_size_uses_balance_and_never_exceeds_budget() -> None:
    sized = size_position(10_000, 2400, 2397.5, 0.01)
    assert sized.lots == 0.4
    assert sized.risk_amount <= sized.budget


def test_config_rejects_elevated_risk() -> None:
    with pytest.raises(ValueError):
        RiskConfig(risk_fraction=0.05)
    with pytest.raises(ValueError):
        RiskConfig(cooldown_minutes=30)


def test_atr_and_dxy() -> None:
    candles = synthetic_candles(40, seed=1)
    assert atr(candles) is not None
    value = calculated_dxy(1.1, 150, 1.25, 1.35, 10.5, 0.9)
    assert 90 < value < 120


def test_bullish_fvg_detected() -> None:
    zones = fair_value_gaps(trending_long_setup())
    assert any(zone.kind == "bullish_fvg" for zone in zones)


def test_news_phases() -> None:
    event = datetime(2026, 3, 6, 12, 30, tzinfo=timezone.utc)
    assert news_state(event - timedelta(minutes=10), event).phase is NewsPhase.PRE_FREEZE
    assert news_state(event + timedelta(seconds=20), event).phase is NewsPhase.VOID
    assert news_state(event + timedelta(minutes=5), event).new_trades_allowed is False
    assert news_state(event + timedelta(minutes=20), event).phase is NewsPhase.SETTLING
    assert news_state(event + timedelta(hours=2), event).phase is NewsPhase.NORMAL


def test_proposal_requires_two_r_and_execution_floor_is_lower() -> None:
    config = RiskConfig()
    account = Account(balance=10_000, equity=10_000, day_start_equity=10_000)
    now = datetime(2026, 3, 2, tzinfo=timezone.utc)
    market = Market(bid=2400, ask=2400.2, tick_time=now, now=now, atr=2)
    weak = Proposal("buy", 2400, 2398, 2403, "TEST", True)
    rejected = evaluate_proposal(weak, account, market, config)
    assert rejected.blocking_rule_id == "cap.3.6"
    strong = Proposal("buy", 2400, 2398, 2404, "TEST", True)
    accepted = evaluate_proposal(strong, account, market, config)
    assert accepted.status == "pending_confirmation"
    slipped = Proposal("buy", 2400.4, 2398, 2404, "TEST", True)
    gate = execution_recheck(slipped, account, market, config)
    assert gate.blocking_rule_id == "policy.exec_rr"


def test_paper_fill_slippage_partial_and_kill() -> None:
    broker = PaperBroker(slippage_points=2)
    now = datetime(2026, 3, 2, tzinfo=timezone.utc)
    broker.quote(2400, 2400.2, now)
    position = broker.market("buy", 0.1, stop_loss=2390, take_profit=2420, comment="T")
    assert position.entry == pytest.approx(2400.22)
    broker.quote(2420, 2420.2, now)
    assert broker.balance > 10_000
    broker.kill()
    assert broker.killed
    assert all(item.status == "closed" or item.remaining == 0 for item in broker.positions.values())


def test_reconcile_does_not_hide_a_mismatch() -> None:
    result = reconcile({"a": {"remaining": 0.1, "side": "buy"}}, {"a": {"remaining": 0.2, "side": "buy"}})
    assert result.state == "DESYNCED"


def test_skill_frontmatter() -> None:
    skill = parse_skill(Path("deploy/workspace-template/skills/xauusd-structure/SKILL.md").read_text())
    assert skill.name == "xauusd-structure"
    assert "market.read" in skill.permissions


def test_mcp_refuses_broker_tools() -> None:
    server = analysis_server(lambda: "1.2")
    listed = asyncio.run(server.list_tools())
    names = [tool.name for tool in listed]
    assert "atr_value_tool" in names
    with pytest.raises(PermissionError):
        assert_mcp_tool_allowed("broker_market")


def test_openai_agents_sdk_calls_the_mokli_tool() -> None:
    text, calls = asyncio.run(run_with_snapshot_tool("What is gold doing?", "last=2410 source=simulator"))
    assert calls == 1
    assert "Snapshot" in text


def test_heartbeat_is_silent_in_a_dead_range() -> None:
    from mokli.heartbeat import heartbeat_action
    from mokli.market.candles import Candle

    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    candles = []
    for index in range(20):
        opened = start + timedelta(minutes=15 * index)
        if index < 19:
            candles.append(Candle(opened, 2400, 2403, 2398, 2401, 40, source="simulator"))
        else:
            candles.append(Candle(opened, 2401, 2401.05, 2400.98, 2401.01, 12, source="simulator"))
    assert heartbeat_action(candles, "If the range is dead, stay silent.") is None


def test_google_adk_agent_constructs() -> None:
    from google.adk import Agent

    agent = Agent(name="Mokli", model="gemini-2.5-flash", instruction="Wait when structure conflicts.")
    assert agent.name == "Mokli"


def test_api_paper_cycle(tmp_path: Path) -> None:
    settings = Settings(
        mokli_data_dir=str(tmp_path),
        mokli_passphrase="secret-pass",
        mokli_cors_origins="http://localhost:5173",
    )
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    denied = client.get("/api/dashboard")
    assert denied.status_code == 401
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    loaded = client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 3})
    assert loaded.json()["state"] == "SIMULATOR"
    candles = client.get("/api/market/candles", headers=headers).json()["candles"]
    assert candles[-1]["source"] == "simulator"
    cycle = client.post("/api/cycle", headers=headers).json()
    assert cycle["verdict"] in {"buy", "sell", "wait"}
    assert client.get("/api/dashboard", headers=headers).json()["mode"] == "paper"
    killed = client.post("/api/broker/kill", headers=headers)
    assert killed.json()["killed"] is True
    snapshot = analyze(trending_long_setup())
    assert "fvg" in snapshot
