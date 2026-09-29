"""HTTP and WebSocket gateway. The model never reaches the broker from this layer."""

from __future__ import annotations

import asyncio
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
from mokli.execution.paper import PaperBroker
from mokli.execution.reconcile import reconcile
from mokli.market.candles import Candle, load_csv, synthetic_candles
from mokli.market.candles import atr as atr_value
from mokli.models import Account, Market, Proposal
from mokli.news.classify import classify_news_candle
from mokli.news.machine import news_state
from mokli.risk.guardrails import execution_recheck
from mokli.rules_loader import load_rules
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
    User,
    utcnow,
)
from mokli.skills import Skill, load_skills

_TEMPLATE = Path(__file__).resolve().parents[3] / "deploy" / "workspace-template"


class LoginBody(BaseModel):
    passphrase: str
    totp: str | None = None


class ChatBody(BaseModel):
    message: str
    session_id: str = "main"


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
        if self.settings.live_flag and confirmed:
            return "live"
        return "paper"

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
        return {
            "broker": snap,
            "market_state": hub.market_state,
            "mode": hub.live_mode(),
            "live_flag": hub.settings.live_flag,
            "live_confirmed": hub.setting("live_confirmed", "0") == "1",
            "provider": hub.setting("active_provider", hub.settings.active_provider),
            "runtime": _runtime_name(hub),
            "model": _model_name(hub),
            "killed": hub.broker.killed,
            "freshness": hub.candles[-1].time.isoformat() if hub.candles else None,
            "source": hub.candles[-1].source if hub.candles else hub.market_state,
        }

    @app.post("/api/market/replay/synthetic")
    def synthetic(_user: User = Depends(current_user), count: int = 180, seed: int = 7) -> dict[str, object]:
        hub.candles = synthetic_candles(count=count, seed=seed)
        hub.market_state = "SIMULATOR"
        last = hub.candles[-1]
        hub.broker.quote(last.close - 0.09, last.close + 0.09, last.time)
        _store_candles(hub)
        hub.audit("user", "replay.synthetic", f"seed={seed} count={count}")
        return {"state": hub.market_state, "candles": len(hub.candles), "last": last.close}

    @app.post("/api/market/replay/csv")
    def replay_csv(path: str, _user: User = Depends(current_user)) -> dict[str, object]:
        file_path = Path(path)
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="csv not found")
        hub.candles = load_csv(file_path)
        hub.market_state = "SIMULATOR"
        if hub.candles:
            last = hub.candles[-1]
            hub.broker.quote(last.close - 0.09, last.close + 0.09, last.time)
        _store_candles(hub)
        return {"state": hub.market_state, "candles": len(hub.candles)}

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
    def chat(body: ChatBody, _user: User = Depends(current_user)) -> dict[str, object]:
        hub.allow("chat", 40)
        language = hub.setting("language", "ar")
        with Session(hub.engine) as session:
            session.add(Message(session_id=body.session_id, role="user", body=body.message))
            session.commit()
        result = _run_and_store(hub)
        text = _chat_text(language, result)
        with Session(hub.engine) as session:
            session.add(Message(session_id=body.session_id, role="mokli", body=text))
            session.commit()
        hub.publish("agent_message_completed", {"text": text, "session_id": body.session_id})
        return {"text": text, "cycle": result}

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
        _notify(hub, "critical", "Kill switch", "Positions flattened and pending orders cancelled.", [])
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
                {"id": row.id, "level": row.level, "title": row.title, "body": row.body, "actions": json.loads(row.actions)}
                for row in rows
            ]
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

    dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


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
    return [
        {"id": "mokli", "runtime": "mokli_runtime", "agent_sdk": False, "configured": True},
        {"id": "openai", "runtime": "openai_agents_sdk", "agent_sdk": True, "configured": bool(hub.settings.openai_api_key)},
        {"id": "gemini", "runtime": "google_adk", "agent_sdk": True, "configured": bool(hub.settings.gemini_api_key)},
        {"id": "anthropic", "runtime": "anthropic_messages", "agent_sdk": False, "configured": bool(hub.settings.anthropic_api_key)},
        {"id": "openrouter", "runtime": "mokli_runtime", "agent_sdk": False, "configured": bool(hub.settings.openrouter_api_key)},
        {"id": "kimi", "runtime": "mokli_runtime", "agent_sdk": False, "configured": bool(hub.settings.kimi_api_key)},
        {"id": "zai", "runtime": "zai_agents" if hub.settings.zai_agent_id else "mokli_runtime", "agent_sdk": bool(hub.settings.zai_agent_id), "configured": bool(hub.settings.zai_api_key)},
        {"id": "ollama", "runtime": "mokli_runtime", "agent_sdk": False, "configured": bool(hub.settings.ollama_model)},
    ]


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
    roles = ["research", "bull", "bear", "greed", "emotion", "professional", "review"]
    with Session(hub.engine) as session:
        session.add(AgentRun(id=parent, role="mokli", provider=provider, runtime=runtime, model=model, status="completed", session_id="main"))
        for role in roles:
            session.add(
                AgentRun(
                    id=uuid.uuid4().hex[:12],
                    parent_id=parent,
                    role=role,
                    provider=provider,
                    runtime=runtime,
                    model=model,
                    status="completed",
                    session_id="main",
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
            session.add(
                Notification(
                    id=uuid.uuid4().hex[:12],
                    level="action",
                    title="Approval required",
                    body=f"{result.verdict} {result.proposal.get('entry')}",
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
    }
