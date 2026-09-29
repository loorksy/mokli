"""HTTP and WebSocket gateway. The model never reaches the broker from this layer."""

from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, col, select

from mokli.agent.debate import run_debate
from mokli.agent.mcp_bridge import analysis_server
from mokli.charts import render_snapshot
from mokli.config import Settings, load_settings
from mokli.cycle import cycle_json, run_cycle
from mokli.db import (
    create_db_engine,
    ensure_user,
    fernet_key_bytes,
    hash_token,
    init_database,
    new_token,
    verify_passphrase,
)
from mokli.execution.live_gate import execution_book
from mokli.execution.metaapi import status as metaapi_status
from mokli.execution.paper import PaperBroker
from mokli.execution.reconcile import reconcile
from mokli.market.candles import Candle, load_csv, synthetic_candles
from mokli.market.candles import atr as atr_value
from mokli.market.replay import ReplayClock, market_status, quote_from_candle
from mokli.memory import recall, remember
from mokli.models import Account, Market, Proposal
from mokli.news.classify import classify_news_candle
from mokli.news.machine import news_state
from mokli.risk.guardrails import execution_recheck
from mokli.rules_loader import load_rules
from mokli.runtime.catalog import public_catalog, specs
from mokli.runtime.mcp_registry import McpRegistry
from mokli.runtime.persist import outcome_payload
from mokli.runtime.service import run_selected
from mokli.schema import (
    AgentEvent,
    AgentRun,
    Approval,
    AuditLog,
    AuthSession,
    BrokerSnapshot,
    CandleRow,
    Decision,
    JournalEntry,
    LessonRow,
    Message,
    Notification,
    PositionRow,
    ProviderRun,
    Reconciliation,
    RiskCheck,
    RuleState,
    SettingRow,
    Signal,
    SkillState,
    ToolCall,
    User,
    utcnow,
)
from mokli.skills import Skill, load_skills
from mokli.voice.local import synthesize, transcribe
from mokli.voice.session import VoiceSession, VoiceTurn

_TEMPLATE = Path(__file__).resolve().parents[3] / "deploy" / "workspace-template"


class LoginBody(BaseModel):
    passphrase: str
    totp: str | None = None


class ChatBody(BaseModel):
    message: str
    session_id: str = "main"
    include_market: bool = True
    include_news: bool = False


class VoiceBody(BaseModel):
    transcript: str = ""


class VoiceAudioBody(BaseModel):
    audio_base64: str
    lang: str = "ar"


class MemoryBody(BaseModel):
    kind: str = "note"
    body: str
    tags: str = ""


class SettingsBody(BaseModel):
    language: str | None = None
    live_confirmed: bool | None = None
    execution_mode: str | None = None
    active_provider: str | None = None


class Hub:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_db_engine(settings)
        init_database(self.engine)
        ensure_user(self.engine, settings.mokli_passphrase)
        fernet_key_bytes(settings)
        self.broker = PaperBroker(
            balance=settings.paper_balance,
            point=settings.point_size,
            slippage_points=settings.paper_slippage_points,
            contract_ounces=settings.contract_ounces,
        )
        self.candles: list[Candle] = []
        self.instrument = "XAUUSD"
        self.timeframe = "M15"
        self.market_state = "UNAVAILABLE"
        self.queues: list[asyncio.Queue[dict[str, object]]] = []
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.event_time: datetime | None = None
        self.replay = ReplayClock()
        self.voice = VoiceSession()
        self._seed_workspace()
        self._reconcile_boot()

    def _seed_workspace(self) -> None:
        destination = self.settings.workspace_dir
        destination.mkdir(parents=True, exist_ok=True)
        if not _TEMPLATE.exists():
            return
        for path in _TEMPLATE.rglob("*"):
            if not path.is_file():
                continue
            target = destination / path.relative_to(_TEMPLATE)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def _reconcile_boot(self) -> None:
        local = self._local_positions()
        positions = self.broker.snapshot()["positions"]
        broker_map: dict[str, dict[str, object]] = {}
        if isinstance(positions, list):
            for item in positions:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    broker_map[item["id"]] = item
        result = reconcile(local, broker_map)
        with Session(self.engine) as session:
            session.add(Reconciliation(state=result.state if local or broker_map else "SIMULATOR", payload=json.dumps(result.discrepancies)))
            session.add(BrokerSnapshot(broker="paper", payload=json.dumps(self.broker.snapshot())))
            session.commit()

    def _local_positions(self) -> dict[str, dict[str, object]]:
        with Session(self.engine) as session:
            rows = session.exec(select(PositionRow)).all()
        found: dict[str, dict[str, object]] = {}
        for row in rows:
            payload = json.loads(row.payload)
            if payload.get("status") == "open":
                found[row.id] = payload
        return found

    def allow(self, key: str, limit: int = 60) -> None:
        now = time.monotonic()
        bucket = self.hits[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="rate limit")
        bucket.append(now)

    def publish(self, kind: str, payload: dict[str, object]) -> None:
        event: dict[str, object] = {"kind": kind, "payload": payload, "at": utcnow().isoformat()}
        for queue in list(self.queues):
            if queue.full():
                continue
            queue.put_nowait(event)

    def setting(self, key: str, default: str) -> str:
        with Session(self.engine) as session:
            row = session.get(SettingRow, key)
            return default if row is None else row.value

    def put_setting(self, key: str, value: str) -> None:
        with Session(self.engine) as session:
            row = session.get(SettingRow, key)
            if row is None:
                session.add(SettingRow(key=key, value=value))
            else:
                row.value = value
                session.add(row)
            session.commit()

    def live_mode(self) -> str:
        confirmed = self.setting("live_confirmed", "0") == "1"
        return execution_book(mokli_live=self.settings.mokli_live, confirmed=confirmed)

    def audit(self, actor: str, action: str, detail: str) -> None:
        with Session(self.engine) as session:
            session.add(AuditLog(actor=actor, action=action, detail=detail))
            session.commit()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Mokli", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )
    hub = Hub(settings)
    app.state.hub = hub

    def current_user(authorization: str | None = Header(default=None)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="auth required")
        token = authorization.removeprefix("Bearer ").strip()
        with Session(hub.engine) as session:
            row = session.exec(select(AuthSession).where(AuthSession.token_hash == hash_token(token))).first()
            if row is None or row.expires_at < utcnow():
                raise HTTPException(status_code=401, detail="session expired")
            user = session.get(User, row.user_id)
            if user is None:
                raise HTTPException(status_code=401, detail="auth required")
            return user

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": hub.live_mode(), "market": hub.market_state}

    @app.post("/api/auth/login")
    def login(body: LoginBody) -> dict[str, str]:
        hub.allow("login", 20)
        with Session(hub.engine) as session:
            user = session.exec(select(User)).first()
            if user is None or not verify_passphrase(body.passphrase, user.passphrase_hash):
                raise HTTPException(status_code=401, detail="invalid passphrase")
            if hub.settings.mokli_totp_enabled == "1":
                if not body.totp:
                    raise HTTPException(status_code=401, detail="totp required")
                import pyotp

                secret = user.totp_secret
                if not secret or not pyotp.TOTP(secret).verify(body.totp):
                    raise HTTPException(status_code=401, detail="invalid totp")
            token = new_token()
            session.add(
                AuthSession(
                    id=uuid.uuid4().hex,
                    user_id=user.id or 0,
                    token_hash=hash_token(token),
                    expires_at=utcnow() + timedelta(hours=18),
                )
            )
            session.add(AuditLog(actor="user", action="login", detail="passphrase session"))
            session.commit()
        return {"token": token}

    @app.get("/api/dashboard")
    def dashboard(_user: User = Depends(current_user)) -> dict[str, object]:
        snap = hub.broker.snapshot()
        provider_id = hub.setting("active_provider", hub.settings.active_provider)
        spec = specs().get(provider_id, specs()["mokli"])
        last = _latest_run(hub)
        return {
            "broker": snap,
            "market_state": hub.market_state,
            "mode": hub.live_mode(),
            "live_flag": hub.settings.live_flag,
            "live_confirmed": hub.setting("live_confirmed", "0") == "1",
            "provider": spec.display_provider,
            "provider_id": provider_id,
            "runtime": spec.display_runtime,
            "model": _model_name(hub),
            "agent": "Mokli",
            "status": last.get("status", "idle"),
            "tools": last.get("tools", []),
            "killed": hub.broker.killed,
            "freshness": hub.candles[hub.replay.index].time.isoformat() if hub.candles and hub.replay.index >= 0 else None,
            "source": hub.candles[hub.replay.index].source if hub.candles and hub.replay.index >= 0 else hub.market_state,
            "book": _market_payload(hub),
        }

    @app.post("/api/market/replay/synthetic")
    def synthetic(_user: User = Depends(current_user), count: int = 180, seed: int = 7) -> dict[str, object]:
        hub.candles = synthetic_candles(count=count, seed=seed)
        hub.replay.arm(len(hub.candles), start=len(hub.candles) - 1)
        _apply_replay_quote(hub)
        _store_candles(hub)
        hub.audit("user", "replay.synthetic", f"seed={seed} count={count}")
        return {"state": hub.market_state, "candles": len(hub.candles), "last": hub.candles[-1].close}

    @app.post("/api/market/replay/csv")
    def replay_csv(path: str, _user: User = Depends(current_user)) -> dict[str, object]:
        file_path = Path(path)
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="csv not found")
        hub.candles = load_csv(file_path)
        hub.replay.arm(len(hub.candles), start=max(len(hub.candles) - 1, 0))
        _apply_replay_quote(hub)
        _store_candles(hub)
        return {"state": hub.market_state, "candles": len(hub.candles)}

    @app.post("/api/market/replay/arm")
    def replay_arm(_user: User = Depends(current_user), start: int = 40) -> dict[str, object]:
        if not hub.candles:
            raise HTTPException(status_code=409, detail="UNAVAILABLE")
        hub.replay.arm(len(hub.candles), start=start)
        _apply_replay_quote(hub)
        return _market_payload(hub)

    @app.post("/api/market/replay/step")
    def replay_step(_user: User = Depends(current_user)) -> dict[str, object]:
        if not hub.candles:
            raise HTTPException(status_code=409, detail="UNAVAILABLE")
        hub.replay.step(len(hub.candles))
        _apply_replay_quote(hub)
        return _market_payload(hub)

    @app.get("/api/market/status")
    def market_status_route(_user: User = Depends(current_user)) -> dict[str, object]:
        return _market_payload(hub)

    @app.get("/api/market/candles")
    def candles(_user: User = Depends(current_user)) -> dict[str, object]:
        return {
            "state": hub.market_state,
            "instrument": hub.instrument,
            "timeframe": hub.timeframe,
            "candles": [
                {
                    "time": candle.time.isoformat(),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "source": candle.source,
                }
                for candle in hub.candles[-300:]
            ],
        }

    @app.get("/api/analysis")
    def analysis(_user: User = Depends(current_user)) -> dict[str, object]:
        from mokli.analysis.detectors import analyze

        if not hub.candles:
            return {"state": "UNAVAILABLE", "snapshot": None}
        return {"state": hub.market_state, "snapshot": analyze(hub.candles)}

    @app.post("/api/cycle")
    def cycle(_user: User = Depends(current_user)) -> dict[str, object]:
        return _run_and_store(hub)

    @app.post("/api/chat")
    async def chat(body: ChatBody, _user: User = Depends(current_user)) -> dict[str, object]:
        hub.allow("chat", 40)
        with Session(hub.engine) as session:
            session.add(Message(session_id=body.session_id, role="user", body=body.message))
            session.commit()
        snapshot = "UNAVAILABLE"
        if body.include_market and hub.candles:
            last = hub.candles[-1]
            snapshot = f"close={last.close} source={last.source}"
        if body.include_news:
            phase = news_state(datetime.now(timezone.utc), hub.event_time).phase.value
            snapshot = f"{snapshot} news={phase}"
        provider = hub.setting("active_provider", hub.settings.active_provider)
        outcome = await run_selected(
            hub.settings,
            provider,
            body.message,
            snapshot,
            session_id=body.session_id,
            engine=hub.engine,
        )
        payload = outcome_payload(outcome)
        with Session(hub.engine) as session:
            session.add(Message(session_id=body.session_id, role="mokli", body=str(payload["text"])))
            session.commit()
        hub.publish("agent_message_completed", {"text": payload["text"], "session_id": body.session_id, "provider": payload["provider"], "runtime": payload["runtime"]})
        events = payload["events"]
        if isinstance(events, list) and "provider_fallback_started" in events:
            notice_title, notice_body = _desk_copy(hub, "fallback", provider=str(payload["provider"]), runtime=str(payload["runtime"]))
            _notify(hub, "info", notice_title, notice_body, [])
        return payload

    @app.get("/api/voice")
    def voice_state(_user: User = Depends(current_user)) -> dict[str, object]:
        return hub.voice.snapshot()

    @app.post("/api/voice/start")
    def voice_start(_user: User = Depends(current_user)) -> dict[str, object]:
        hub.voice.start()
        hub.audit("user", "voice.start", "listening")
        return hub.voice.snapshot()

    @app.post("/api/voice/stop")
    def voice_stop(_user: User = Depends(current_user)) -> dict[str, object]:
        hub.voice.stop()
        hub.audit("user", "voice.stop", "idle")
        return hub.voice.snapshot()

    @app.post("/api/voice/turn")
    async def voice_turn(body: VoiceAudioBody, _user: User = Depends(current_user)) -> dict[str, object]:
        try:
            raw = base64.b64decode(body.audio_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="bad audio") from exc
        hub.voice.start()
        try:
            transcript = transcribe(raw, body.lang)
        except ValueError:
            hub.voice.stop()
            snap = hub.voice.snapshot()
            snap["error"] = "silent"
            return snap
        snapshot = "UNAVAILABLE"
        if hub.candles and hub.replay.index >= 0:
            candle = hub.candles[hub.replay.index]
            snapshot = f"close={candle.close} source={candle.source}"
        outcome = await run_selected(
            hub.settings,
            hub.setting("active_provider", hub.settings.active_provider),
            transcript,
            snapshot,
            session_id="voice",
            engine=hub.engine,
        )
        payload = outcome_payload(outcome)
        tools = payload["tools"] if isinstance(payload["tools"], list) else []
        hub.voice.deliver(
            transcript,
            VoiceTurn(
                state="speaking",
                reply=str(payload["text"]),
                provider=str(payload["provider"]),
                model=str(payload["model"]),
                runtime=str(payload["runtime"]),
                agent=str(payload["agent"]),
                status=str(payload["status"]),
                tools=[str(item) for item in tools],
            ),
        )
        audio = synthesize(str(payload["text"]), body.lang)
        snap = hub.voice.snapshot()
        snap["audio_base64"] = base64.b64encode(audio).decode("ascii")
        return snap

    @app.post("/api/voice/utterance")
    async def voice_utterance(body: VoiceBody, _user: User = Depends(current_user)) -> dict[str, object]:
        snapshot = "UNAVAILABLE"
        if hub.candles and hub.replay.index >= 0:
            candle = hub.candles[hub.replay.index]
            snapshot = f"close={candle.close} source={candle.source}"
        if hub.voice.turn.state == "idle":
            hub.voice.start()
        outcome = await run_selected(
            hub.settings,
            hub.setting("active_provider", hub.settings.active_provider),
            body.transcript,
            snapshot,
            session_id="voice",
            engine=hub.engine,
        )
        payload = outcome_payload(outcome)
        tools = payload["tools"] if isinstance(payload["tools"], list) else []
        hub.voice.deliver(
            body.transcript,
            VoiceTurn(
                state="speaking",
                reply=str(payload["text"]),
                provider=str(payload["provider"]),
                model=str(payload["model"]),
                runtime=str(payload["runtime"]),
                agent=str(payload["agent"]),
                status=str(payload["status"]),
                tools=[str(item) for item in tools],
            ),
        )
        return hub.voice.snapshot()

    @app.post("/api/voice/spoken")
    def voice_spoken(_user: User = Depends(current_user)) -> dict[str, object]:
        hub.voice.finished_speaking()
        return hub.voice.snapshot()

    @app.post("/api/voice/barge")
    def voice_barge(_user: User = Depends(current_user)) -> dict[str, object]:
        hub.voice.barge_in()
        hub.audit("user", "voice.barge", hub.voice.turn.state)
        return hub.voice.snapshot()

    @app.get("/api/activity")
    def activity(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            events = list(session.exec(select(AgentEvent).order_by(col(AgentEvent.id).desc())).all())[:80]
            runs = list(session.exec(select(ProviderRun).order_by(col(ProviderRun.created_at).desc())).all())[:40]
        return {
            "events": [{"kind": item.kind, "payload": json.loads(item.payload), "at": item.created_at.isoformat()} for item in reversed(events)],
            "providers": [
                {
                    "provider": item.provider,
                    "runtime": item.runtime,
                    "model": item.model,
                    "fallback_from": item.fallback_from,
                    "fallback_provider": item.fallback_provider,
                    "fallback_reason": item.fallback_reason,
                    "error": item.error,
                }
                for item in runs
            ],
        }

    @app.get("/api/agents/tree")
    def tree(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            runs = session.exec(select(AgentRun).order_by(AgentRun.started_at.desc())).all()[:40]  # type: ignore[attr-defined]
        return {
            "nodes": [
                {
                    "id": item.id,
                    "parent_id": item.parent_id,
                    "role": item.role,
                    "provider": item.provider,
                    "runtime": item.runtime,
                    "model": item.model,
                    "status": item.status,
                }
                for item in runs
            ]
        }

    @app.get("/api/approvals")
    def approvals(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            rows = session.exec(select(Approval).where(Approval.status == "pending")).all()
        return {"approvals": [{"id": row.id, "payload": json.loads(row.payload)} for row in rows]}

    @app.post("/api/approvals/{approval_id}/approve")
    def approve(approval_id: str, _user: User = Depends(current_user)) -> dict[str, object]:
        return _resolve(hub, approval_id, True)

    @app.post("/api/approvals/{approval_id}/reject")
    def reject(approval_id: str, _user: User = Depends(current_user)) -> dict[str, object]:
        return _resolve(hub, approval_id, False)

    @app.post("/api/broker/kill")
    def kill(_user: User = Depends(current_user)) -> dict[str, object]:
        hub.broker.kill()
        hub.audit("user", "kill_switch", "flattened paper book")
        hub.publish("agent_message_completed", {"level": "critical", "title": "Kill switch"})
        title, body = _desk_copy(hub, "kill")
        _notify(hub, "critical", title, body, [])
        return hub.broker.snapshot()

    @app.get("/api/positions")
    def positions(_user: User = Depends(current_user)) -> dict[str, object]:
        return {"positions": hub.broker.snapshot()["positions"], "mode": hub.live_mode()}

    @app.get("/api/orders")
    def orders(_user: User = Depends(current_user)) -> dict[str, object]:
        return {"orders": hub.broker.snapshot()["orders"]}

    @app.get("/api/journal")
    def journal(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            rows = session.exec(select(JournalEntry)).all()
        return {"entries": [json.loads(row.payload) for row in rows]}

    @app.get("/api/lessons")
    def lessons(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            rows = session.exec(select(LessonRow)).all()
        return {"lessons": [{"rule_id": row.rule_id, "summary": row.summary, "outcome": row.outcome} for row in rows]}

    @app.get("/api/reports/daily")
    def daily(_user: User = Depends(current_user)) -> dict[str, object]:
        return _report(hub)

    @app.get("/api/reports/weekly")
    def weekly(_user: User = Depends(current_user)) -> dict[str, object]:
        report = _report(hub)
        report["period"] = "week"
        return report

    @app.get("/api/skills")
    def skills(_user: User = Depends(current_user)) -> dict[str, object]:
        found = _skills(hub)
        return {"skills": [{"name": item.name, "description": item.description, "enabled": item.enabled} for item in found]}

    @app.post("/api/skills/{name}/toggle")
    def toggle_skill(name: str, _user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            row = session.get(SkillState, name)
            enabled = False if row is None else not row.enabled
            if row is None:
                session.add(SkillState(name=name, enabled=enabled))
            else:
                row.enabled = enabled
                session.add(row)
            session.commit()
        return {"name": name, "enabled": enabled}

    @app.get("/api/rules")
    def rules(_user: User = Depends(current_user)) -> dict[str, object]:
        states = _rule_states(hub)
        payload = []
        for rule in load_rules():
            payload.append(
                {
                    "id": rule.id,
                    "category": rule.category,
                    "title_en": rule.title_en,
                    "title_ar": rule.title_ar,
                    "type": rule.type,
                    "enabled": states.get(rule.id, rule.default_enabled),
                }
            )
        return {"rules": payload}

    @app.post("/api/rules/{rule_id}/toggle")
    def toggle_rule(rule_id: str, _user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            row = session.get(RuleState, rule_id)
            enabled = False if row is None else not row.enabled
            if row is None:
                session.add(RuleState(rule_id=rule_id, enabled=enabled))
            else:
                row.enabled = enabled
                session.add(row)
            session.commit()
        return {"id": rule_id, "enabled": enabled}

    @app.get("/api/news")
    def news(_user: User = Depends(current_user)) -> dict[str, object]:
        state = news_state(datetime.now(timezone.utc), hub.event_time)
        candle_rules: list[str] = []
        if hub.candles:
            from mokli.models import CandleStats

            last = hub.candles[-1]
            volatility = atr_value(hub.candles) or 0.01
            classified = classify_news_candle(
                CandleStats(
                    timeframe="M15",
                    high=last.high,
                    low=last.low,
                    open=last.open,
                    close=last.close,
                    atr=volatility,
                    spread_points=last.spread_points,
                    normal_spread_points=20,
                )
            )
            candle_rules = list(classified.rule_ids)
        return {
            "phase": state.phase.value,
            "detail": state.detail,
            "calendar": "UNAVAILABLE" if hub.event_time is None else "LIVE",
            "candle_rules": candle_rules,
        }

    @app.get("/api/settings")
    def get_settings(_user: User = Depends(current_user)) -> dict[str, object]:
        return {
            "language": hub.setting("language", "ar"),
            "execution_mode": hub.setting("execution_mode", "approval"),
            "active_provider": hub.setting("active_provider", "mokli"),
            "live_flag": hub.settings.live_flag,
            "live_confirmed": hub.setting("live_confirmed", "0") == "1",
            "mode": hub.live_mode(),
            "timezone": hub.settings.display_timezone,
            "providers": _provider_catalog(hub),
            "capabilities": _active_capabilities(hub),
        }

    @app.put("/api/settings")
    def put_settings(body: SettingsBody, _user: User = Depends(current_user)) -> dict[str, object]:
        if body.language in {"ar", "en"}:
            hub.put_setting("language", body.language)
        if body.execution_mode in {"advise", "approval", "auto"}:
            hub.put_setting("execution_mode", body.execution_mode)
        if body.active_provider:
            hub.put_setting("active_provider", body.active_provider)
            hub.audit("user", "provider.change", body.active_provider)
        if body.live_confirmed is not None:
            hub.put_setting("live_confirmed", "1" if body.live_confirmed else "0")
            hub.audit("user", "live.confirm", hub.setting("live_confirmed", "0"))
        return get_settings()

    @app.get("/api/notifications")
    def notifications(_user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            rows = session.exec(select(Notification).order_by(Notification.created_at.desc())).all()[:50]  # type: ignore[attr-defined]
        return {
            "notifications": [
                {
                    "id": row.id,
                    "level": row.level,
                    "title": row.title,
                    "body": row.body,
                    "read": row.read,
                    "actions": json.loads(row.actions),
                }
                for row in rows
            ],
            "channel": "in_app" if not (hub.settings.telegram_bot_token and hub.settings.telegram_chat_id) else "telegram",
        }

    @app.post("/api/notifications/{note_id}/read")
    def read_notification(note_id: str, _user: User = Depends(current_user)) -> dict[str, object]:
        with Session(hub.engine) as session:
            row = session.get(Notification, note_id)
            if row is None:
                raise HTTPException(status_code=404, detail="notification not found")
            row.read = True
            session.add(row)
            session.commit()
        return {"id": note_id, "read": True}

    @app.get("/api/memory")
    def memory_list(q: str = "", _user: User = Depends(current_user)) -> dict[str, object]:
        rows = recall(hub.engine, q)
        return {"memories": [{"id": row.id, "kind": row.kind, "body": row.body} for row in rows]}

    @app.post("/api/memory")
    def memory_add(body: MemoryBody, _user: User = Depends(current_user)) -> dict[str, object]:
        row = remember(hub.engine, body.kind, body.body, body.tags)
        return {"id": row.id, "kind": row.kind, "body": row.body}

    @app.get("/api/mcp")
    def mcp_tools(_user: User = Depends(current_user)) -> dict[str, object]:
        registry = McpRegistry()
        registry.register(
            "analysis",
            analysis_server(lambda: "desk"),
            {"atr_value_tool"},
            side_effects={"atr_value_tool": "read"},
        )
        registry.permit("mokli", {"atr_value_tool"})
        names = asyncio.run(registry.discover("mokli"))
        return {"tools": names, "broker_blocked": ["place_order", "broker_market", "broker_close", "broker_modify", "broker_kill"]}

    @app.get("/api/live")
    def live_status(_user: User = Depends(current_user)) -> dict[str, object]:
        adapter = metaapi_status(
            token=hub.settings.metaapi_token,
            account_id=hub.settings.metaapi_account_id,
            live_mode=hub.live_mode(),
        )
        return {
            "mode": hub.live_mode(),
            "mokli_live": hub.settings.mokli_live,
            "confirmed": hub.setting("live_confirmed", "0") == "1",
            "orders": "paper",
            "metaapi": adapter.state,
            "detail": adapter.detail,
        }

    @app.get("/api/chart.png")
    def chart(_user: User = Depends(current_user)) -> FileResponse:
        path = hub.settings.data_dir / "charts" / "latest.png"
        render_snapshot(hub.candles, path, title=f"{hub.instrument} {hub.timeframe} {hub.market_state}")
        return FileResponse(path, media_type="image/png")

    @app.websocket("/api/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=100)
        hub.queues.append(queue)
        try:
            while True:
                event = await queue.get()
                await socket.send_json(event)
        except WebSocketDisconnect:
            hub.queues.remove(queue)

    @app.get("/api/events")
    def events(_user: User = Depends(current_user)) -> StreamingResponse:
        async def stream():
            queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=100)
            hub.queues.append(queue)
            try:
                while True:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
            except TimeoutError:
                yield "data: {\"kind\": \"ping\"}\n\n"
            finally:
                if queue in hub.queues:
                    hub.queues.remove(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    dist = _ui_dist()
    if dist is not None:
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


def _ui_dist() -> Path | None:
    candidates = [
        Path(__file__).resolve().parents[3] / "web" / "dist",
        Path("/app/web/dist"),
        Path.cwd() / "web" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _apply_replay_quote(hub: Hub) -> None:
    if not hub.candles or hub.replay.index < 0:
        hub.market_state = "UNAVAILABLE"
        return
    candle = hub.candles[hub.replay.index]
    bid, ask = quote_from_candle(candle, hub.settings.point_size)
    hub.broker.quote(bid, ask, candle.time)
    hub.market_state = "SIMULATOR" if candle.source == "simulator" else candle.source.upper()


def _market_payload(hub: Hub) -> dict[str, object]:
    return market_status(
        hub.candles,
        hub.replay.index,
        bid=hub.broker.bid,
        ask=hub.broker.ask,
        killed=hub.broker.killed,
    )


def _runtime_name(hub: Hub) -> str:
    provider = hub.setting("active_provider", "mokli")
    return {
        "openai": "openai_agents_sdk",
        "anthropic": "anthropic_messages",
        "gemini": "google_adk",
        "openrouter": "mokli_runtime",
        "kimi": "mokli_runtime",
        "zai": "zai_agents" if hub.settings.zai_agent_id else "mokli_runtime",
        "ollama": "mokli_runtime",
        "mokli": "mokli_runtime",
    }.get(provider, "mokli_runtime")


def _model_name(hub: Hub) -> str:
    provider = hub.setting("active_provider", "mokli")
    return {
        "openai": hub.settings.openai_model,
        "anthropic": hub.settings.anthropic_model,
        "gemini": hub.settings.gemini_model,
        "openrouter": hub.settings.openrouter_model or "unconfigured",
        "kimi": hub.settings.kimi_model,
        "zai": hub.settings.zai_model,
        "ollama": hub.settings.ollama_model or "unconfigured",
        "mokli": "deterministic-xauusd",
    }.get(provider, "deterministic-xauusd")


def _provider_catalog(hub: Hub) -> list[dict[str, object]]:
    configured = {
        "mokli": True,
        "openai": bool(hub.settings.openai_api_key),
        "gemini": bool(hub.settings.gemini_api_key),
        "anthropic": bool(hub.settings.anthropic_api_key),
        "openrouter": bool(hub.settings.openrouter_api_key),
        "kimi": bool(hub.settings.kimi_api_key),
        "zai": bool(hub.settings.zai_api_key),
        "ollama": bool(hub.settings.ollama_model),
    }
    return public_catalog(configured, bool(hub.settings.zai_agent_id))


def _active_capabilities(hub: Hub) -> list[str]:
    provider = hub.setting("active_provider", "mokli")
    spec = specs().get(provider, specs()["mokli"])
    return spec.capabilities.enabled()


def _latest_run(hub: Hub) -> dict[str, object]:
    with Session(hub.engine) as session:
        row = session.exec(select(AgentRun).order_by(col(AgentRun.started_at).desc())).first()
        if row is None:
            return {"status": "idle", "tools": []}
        tools = session.exec(select(ToolCall).where(ToolCall.run_id == row.id)).all()
        return {"status": row.status, "tools": [item.name for item in tools]}


def _skills(hub: Hub) -> list[Skill]:
    found = load_skills(hub.settings.workspace_dir / "skills")
    with Session(hub.engine) as session:
        states = {row.name: row.enabled for row in session.exec(select(SkillState)).all()}
    for skill in found:
        if skill.name in states:
            skill.enabled = states[skill.name]
    return found


def _rule_states(hub: Hub) -> dict[str, bool]:
    with Session(hub.engine) as session:
        return {row.rule_id: row.enabled for row in session.exec(select(RuleState)).all()}


def _store_candles(hub: Hub) -> None:
    with Session(hub.engine) as session:
        for candle in hub.candles[-50:]:
            session.add(
                CandleRow(
                    instrument=hub.instrument,
                    timeframe=hub.timeframe,
                    open_time=candle.time,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    spread_points=candle.spread_points,
                    source=candle.source,
                )
            )
        session.commit()


def _run_and_store(hub: Hub) -> dict[str, object]:
    parent = uuid.uuid4().hex[:12]
    provider = hub.setting("active_provider", "mokli")
    runtime = _runtime_name(hub)
    model = _model_name(hub)
    result = run_cycle(hub.candles, hub.broker, event_time=hub.event_time)
    children = asyncio.run(
        run_debate(result, parent_id=parent, provider=provider, model=model, runtime=runtime)
    )
    with Session(hub.engine) as session:
        session.add(AgentRun(id=parent, role="mokli", provider=provider, runtime=runtime, model=model, status="completed", session_id="main"))
        for child in children:
            session.add(
                AgentRun(
                    id=str(child["id"]),
                    parent_id=parent,
                    role=str(child["role"]),
                    provider=str(child["provider"]),
                    runtime=str(child["runtime"]),
                    model=str(child["model"]),
                    status=str(child["status"]),
                    session_id="debate",
                )
            )
            session.add(
                AgentEvent(
                    run_id=str(child["id"]),
                    kind="subagent_completed",
                    payload=json.dumps({"role": child["role"], "text": child["text"], "audit": child["audit"]}),
                )
            )
        for note in result.notes:
            session.add(AgentEvent(run_id=parent, kind="agent_message_completed", payload=json.dumps({"role": note.role, "text": note.text})))
        session.add(Decision(id=result.decision_id, verdict=result.verdict, payload=cycle_json(result)))
        session.add(Signal(id=uuid.uuid4().hex[:12], payload=cycle_json(result)))
        session.add(ProviderRun(id=uuid.uuid4().hex[:12], run_id=parent, provider=provider, runtime=runtime, model=model))
        if result.proposal:
            checks = result.proposal.get("checks")
            if isinstance(checks, list):
                for check in checks:
                    if not isinstance(check, dict):
                        continue
                    session.add(
                        RiskCheck(
                            decision_id=result.decision_id,
                            rule_id=str(check.get("rule_id")),
                            ok=bool(check.get("ok")),
                            detail=str(check.get("detail")),
                        )
                    )
        approval_id = None
        mode = hub.setting("execution_mode", "approval")
        if result.verdict in {"buy", "sell"} and result.proposal and mode == "approval":
            approval_id = uuid.uuid4().hex[:12]
            session.add(Approval(id=approval_id, status="pending", payload=json.dumps(result.proposal), decision_id=result.decision_id))
            title, body = _desk_copy(hub, "approval", verdict=result.verdict, entry=result.proposal.get("entry"))
            session.add(
                Notification(
                    id=uuid.uuid4().hex[:12],
                    level="action",
                    title=title,
                    body=body,
                    actions=json.dumps([{"id": "approve", "approval_id": approval_id}, {"id": "reject", "approval_id": approval_id}]),
                )
            )
        session.add(JournalEntry(id=result.decision_id, payload=cycle_json(result)))
        session.commit()
    hub.publish("agent_message_completed", {"decision_id": result.decision_id, "verdict": result.verdict})
    payload = json.loads(cycle_json(result))
    payload["approval_id"] = approval_id
    return payload


def _resolve(hub: Hub, approval_id: str, accept: bool) -> dict[str, object]:
    with Session(hub.engine) as session:
        row = session.get(Approval, approval_id)
        if row is None or row.status != "pending":
            raise HTTPException(status_code=404, detail="approval not found")
        proposal_data = json.loads(row.payload)
        if not accept:
            row.status = "rejected"
            row.resolved_at = utcnow()
            session.add(row)
            session.commit()
            hub.audit("user", "approval.reject", approval_id)
            return {"status": "rejected"}
        if hub.live_mode() == "live":
            row.status = "blocked"
            session.add(row)
            session.commit()
            raise HTTPException(status_code=409, detail="live adapter is not the active paper path")
        proposal = Proposal(
            side=proposal_data["side"],
            entry=float(proposal_data["entry"]),
            stop=float(proposal_data["stop"]),
            target=float(proposal_data["target"]),
            reason_code=str(proposal_data["reason_code"]),
            higher_timeframe_agrees=True,
        )
        when = hub.candles[-1].time if hub.candles else utcnow()
        volatility = atr_value(hub.candles) or 0.01
        account = Account(balance=hub.broker.balance, equity=hub.broker.equity(), day_start_equity=hub.broker.balance)
        gate = execution_recheck(
            proposal,
            account,
            Market(bid=hub.broker.bid, ask=hub.broker.ask, tick_time=when, now=when, atr=volatility),
        )
        if gate.status == "rejected" or gate.status == "locked":
            row.status = "rejected_at_gate"
            row.resolved_at = utcnow()
            session.add(row)
            session.commit()
            return {"status": row.status, "rule": gate.blocking_rule_id}
        lots = float(proposal_data.get("lots") or 0.01)
        position = hub.broker.market(
            proposal.side,
            lots,
            stop_loss=proposal.stop,
            take_profit=proposal.target,
            comment=proposal.reason_code,
            when=when,
        )
        row.status = "executed"
        row.resolved_at = utcnow()
        session.add(row)
        session.add(PositionRow(id=position.id, payload=json.dumps({"id": position.id, "side": position.side, "remaining": position.remaining, "status": "open"}), status="open"))
        session.add(LessonRow(rule_id=proposal.reason_code, summary="Proposal passed a fresh execution check and was filled on the paper broker.", outcome="skipped", tags=proposal.side))
        session.commit()
    hub.audit("user", "approval.execute", approval_id)
    return {"status": "executed", "snapshot": hub.broker.snapshot()}


def _desk_copy(hub: Hub, key: str, **values: object) -> tuple[str, str]:
    arabic = hub.setting("language", "ar") == "ar"
    if key == "kill":
        if arabic:
            return "إيقاف طارئ", "أُغلقت المراكز وأُلغيت الأوامر المعلقة."
        return "Kill switch", "Positions flattened and pending orders cancelled."
    if key == "approval":
        verdict = values.get("verdict")
        entry = values.get("entry")
        if arabic:
            return "موافقة مطلوبة", f"اقتراح {verdict} عند {entry}"
        return "Approval required", f"{verdict} {entry}"
    provider = values.get("provider")
    runtime = values.get("runtime")
    if arabic:
        return "تحويل المزوّد", f"{provider} عبر {runtime}"
    return "Provider fallback", f"{provider} via {runtime}"


def _notify(hub: Hub, level: str, title: str, body: str, actions: list[dict[str, str]]) -> None:
    with Session(hub.engine) as session:
        session.add(Notification(id=uuid.uuid4().hex[:12], level=level, title=title, body=body, actions=json.dumps(actions)))
        session.commit()
    hub.publish("approval_required" if level == "action" else "agent_message_completed", {"title": title, "body": body, "level": level})


def _chat_text(language: str, result: dict[str, object]) -> str:
    verdict = str(result.get("verdict"))
    if language == "ar":
        if verdict == "wait":
            return "لا توجد صفقة تستوفي الحراسة. الانتظار هو القرار."
        return f"اقتراح {verdict} بانتظار الموافقة. المخاطرة حُسبت خارج النموذج."
    if verdict == "wait":
        return "No proposal cleared the guardrails. Waiting is the decision."
    return f"{verdict} proposal is waiting for approval. Size was calculated outside the model."


def _report(hub: Hub) -> dict[str, object]:
    closed = [item for item in hub.broker.positions.values() if item.status == "closed"]
    wins = [item for item in closed if item.realized > 0]
    return {
        "period": "day",
        "balance": round(hub.broker.balance, 2),
        "equity": round(hub.broker.equity(), 2),
        "closed_trades": len(closed),
        "win_rate": (len(wins) / len(closed)) if closed else None,
        "realized": round(sum(item.realized for item in closed), 2),
        "mode": hub.live_mode(),
        "market_state": hub.market_state,
        "open_positions": sum(1 for item in hub.broker.positions.values() if item.status == "open"),
    }
