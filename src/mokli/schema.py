"""SQLite tables. Every trading decision can be reconstructed from these rows."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    passphrase_hash: str
    totp_secret: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int
    token_hash: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime


class AgentRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    parent_id: str | None = Field(default=None, index=True)
    role: str
    provider: str
    runtime: str
    model: str
    status: str
    session_id: str = Field(index=True)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None


class AgentEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    kind: str
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str
    body: str
    created_at: datetime = Field(default_factory=utcnow)


class ToolCall(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    name: str
    arguments: str
    result: str
    ok: bool
    created_at: datetime = Field(default_factory=utcnow)


class ProviderRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    provider: str
    runtime: str
    model: str
    sdk: str = ""
    agent_id: str = ""
    parent_agent_id: str = ""
    session_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost: float = 0
    latency_ms: int = 0
    tool_calls: int = 0
    subagents: int = 0
    retries: int = 0
    failures: str = ""
    fallbacks: str = ""
    original_provider: str = ""
    original_model: str = ""
    original_runtime: str = ""
    fallback_provider: str = ""
    fallback_model: str = ""
    fallback_runtime: str = ""
    fallback_reason: str = ""
    fallback_at: datetime | None = None
    fallback_from: str = ""
    error: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Approval(SQLModel, table=True):
    id: str = Field(primary_key=True)
    status: str = Field(index=True)
    payload: str
    decision_id: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class CandleRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    instrument: str = Field(index=True)
    timeframe: str = Field(index=True)
    open_time: datetime = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread_points: float | None = None
    source: str


class Signal(SQLModel, table=True):
    id: str = Field(primary_key=True)
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class Decision(SQLModel, table=True):
    id: str = Field(primary_key=True)
    verdict: str
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class RiskCheck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    decision_id: str = Field(index=True)
    rule_id: str
    ok: bool
    detail: str
    created_at: datetime = Field(default_factory=utcnow)


class OrderRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    broker: str
    payload: str
    status: str
    created_at: datetime = Field(default_factory=utcnow)


class FillRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    order_id: str = Field(index=True)
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class PositionRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    payload: str
    status: str = Field(index=True)
    updated_at: datetime = Field(default_factory=utcnow)


class BrokerSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    broker: str
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class Reconciliation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state: str
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class LessonRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    rule_id: str
    summary: str
    outcome: str
    tags: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class MemoryItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    kind: str
    body: str
    created_at: datetime = Field(default_factory=utcnow)


class JournalEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)
    payload: str
    created_at: datetime = Field(default_factory=utcnow)


class Notification(SQLModel, table=True):
    id: str = Field(primary_key=True)
    level: str
    title: str
    body: str
    actions: str = "[]"
    read: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actor: str
    action: str
    detail: str
    created_at: datetime = Field(default_factory=utcnow)


class SettingRow(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str


class SkillState(SQLModel, table=True):
    name: str = Field(primary_key=True)
    enabled: bool = True


class RuleState(SQLModel, table=True):
    rule_id: str = Field(primary_key=True)
    enabled: bool = True


class ConditionalRule(SQLModel, table=True):
    id: str = Field(primary_key=True)
    phrase: str
    payload: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=utcnow)
