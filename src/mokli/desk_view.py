"""Shapes the three visible surfaces. Debate, tools, and secrets stay in the backend."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from mokli.config import Settings
from mokli.execution.paper import PaperBroker
from mokli.models import RiskConfig

_GOLD = ("ذهب", "xau", "gold", "توصية", "recommendation")
_RISK_KEYS = (
    "risk_fraction",
    "event_day_risk_fraction",
    "daily_loss_fraction",
    "min_reward_risk",
    "cooldown_minutes",
    "max_open_positions",
)
_SECRET_FIELDS = {
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "gemini": "gemini_api_key",
    "openrouter": "openrouter_api_key",
    "kimi": "kimi_api_key",
    "zai": "zai_api_key",
    "oanda": "oanda_api_token",
    "metaapi": "metaapi_token",
    "telegram": "telegram_bot_token",
}
_PLAIN_FIELDS = {
    "ollama": ("ollama_host", "ollama_model"),
    "oanda": ("oanda_account_id",),
    "metaapi": ("metaapi_account_id",),
    "telegram": ("telegram_chat_id",),
    "zai": ("zai_agent_id",),
}
CONNECTIONS = (
    ("openai", "OpenAI", "model"),
    ("anthropic", "Anthropic", "model"),
    ("gemini", "Gemini", "model"),
    ("openrouter", "OpenRouter", "model"),
    ("kimi", "Kimi", "model"),
    ("zai", "Z.ai", "model"),
    ("ollama", "Ollama", "model"),
    ("oanda", "OANDA", "market"),
    ("metaapi", "MetaApi", "market"),
    ("telegram", "Telegram", "market"),
)


def wants_chart(message: str) -> bool:
    folded = message.casefold()
    return any(token in folded for token in _GOLD)


def env_path(settings: Settings) -> Path:
    return settings.data_dir / "provider.env"


def load_env_store(settings: Settings) -> None:
    path = env_path(settings)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        field = key.strip().lower()
        if field in {"mokli_live", "mokli_passphrase", "mokli_fernet_key"}:
            continue
        if not hasattr(settings, field):
            continue
        current = getattr(settings, field)
        try:
            setattr(settings, field, type(current)(value) if not isinstance(current, str) else value)
        except (TypeError, ValueError):
            continue


def write_env_value(settings: Settings, field: str, value: str) -> None:
    if field.lower() in {"mokli_live", "mokli_passphrase", "mokli_fernet_key"}:
        return
    path = env_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, stored = line.split("=", 1)
            rows[key.strip().upper()] = stored
    name = field.upper()
    if value:
        rows[name] = value
    else:
        rows.pop(name, None)
    body = "".join(f"{key}={item}\n" for key, item in rows.items())
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)
    current = getattr(settings, field)
    setattr(settings, field, type(current)(value) if not isinstance(current, str) else value)


def stored_risk(read: Callable[[str, str], str]) -> RiskConfig:
    return risk_config({key: read(key, "") for key in _RISK_KEYS})


def risk_config(values: dict[str, str]) -> RiskConfig:
    defaults = RiskConfig()

    def number(key: str) -> float:
        raw = values.get(key, "")
        return float(raw) if raw else float(getattr(defaults, key))

    def whole(key: str) -> int:
        raw = values.get(key, "")
        return int(raw) if raw else int(getattr(defaults, key))

    risk_fraction = number("risk_fraction")
    event_raw = values.get("event_day_risk_fraction", "")
    event_day = float(event_raw) if event_raw else min(defaults.event_day_risk_fraction, risk_fraction)
    return RiskConfig(
        risk_fraction=risk_fraction,
        event_day_risk_fraction=event_day,
        daily_loss_fraction=number("daily_loss_fraction"),
        min_reward_risk=number("min_reward_risk"),
        cooldown_minutes=whole("cooldown_minutes"),
        max_open_positions=whole("max_open_positions"),
    )


def risk_values(config: RiskConfig) -> dict[str, float | int]:
    return {key: getattr(config, key) for key in _RISK_KEYS}


def connected(settings: Settings, provider_id: str) -> bool:
    secret = _SECRET_FIELDS.get(provider_id)
    if secret and str(getattr(settings, secret, "")).strip():
        return True
    if provider_id == "ollama":
        return bool(str(settings.ollama_model).strip())
    return False


def connection_rows(settings: Settings) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for provider_id, name, group in CONNECTIONS:
        rows.append(
            {
                "id": provider_id,
                "name": name,
                "group": group,
                "connected": connected(settings, provider_id),
            }
        )
    return rows


def apply_provider(settings: Settings, provider_id: str, *, secret: str, account: str, host: str, disconnect: bool) -> None:
    if provider_id not in {item[0] for item in CONNECTIONS}:
        raise KeyError(provider_id)
    if disconnect:
        secret_field = _SECRET_FIELDS.get(provider_id)
        if secret_field:
            write_env_value(settings, secret_field, "")
        if provider_id == "ollama":
            write_env_value(settings, "ollama_model", "")
        return
    secret_field = _SECRET_FIELDS.get(provider_id)
    if secret_field and secret.strip():
        write_env_value(settings, secret_field, secret.strip())
    if provider_id == "ollama":
        if host.strip():
            write_env_value(settings, "ollama_host", host.strip())
        if account.strip():
            write_env_value(settings, "ollama_model", account.strip())
        return
    plain = _PLAIN_FIELDS.get(provider_id, ())
    if account.strip() and plain:
        write_env_value(settings, plain[0], account.strip())


def public_recommendation(payload: dict[str, object], language: str) -> dict[str, object]:
    proposal = payload.get("proposal") if isinstance(payload.get("proposal"), dict) else None
    verdict = str(payload.get("verdict") or "wait")
    direction = verdict if verdict in {"buy", "sell"} else "wait"
    checks = proposal.get("checks") if isinstance(proposal, dict) else None
    ok = 0
    total = 0
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            total += 1
            if check.get("ok"):
                ok += 1
    reason = str(proposal.get("reason_code")) if isinstance(proposal, dict) else ""
    approval = payload.get("approval_id")
    outcome = str(payload.get("outcome") or "")
    if not outcome:
        if direction == "wait":
            outcome = "wait"
        elif approval:
            outcome = "pending"
        else:
            outcome = str(payload.get("risk_status") or "pending")
    targets: list[object] = []
    if isinstance(proposal, dict) and proposal.get("target") is not None:
        targets = [proposal.get("target")]
    return {
        "id": str(payload.get("decision_id") or ""),
        "direction": direction,
        "entry": proposal.get("entry") if isinstance(proposal, dict) else None,
        "stop": proposal.get("stop") if isinstance(proposal, dict) else None,
        "targets": targets,
        "rationale": _rationale(reason, direction, language),
        "confidence": f"{ok}/{total}" if total else None,
        "outcome": outcome,
    }


def performance_view(broker: PaperBroker, config: RiskConfig, day_start: float) -> dict[str, object]:
    equity = broker.equity()
    unit = day_start * config.risk_fraction
    equity_r = (equity - day_start) / unit if unit else 0.0
    closed = [item for item in broker.positions.values() if item.status == "closed"]
    wins = [item for item in closed if item.realized > 0]
    trade_r: list[float] = []
    for item in closed:
        if item.stop_loss is None or item.lots <= 0:
            continue
        risk_money = abs(item.entry - item.stop_loss) * broker.contract_ounces * item.lots
        if risk_money > 0:
            trade_r.append(item.realized / risk_money)
    open_rows = [item for item in broker.positions.values() if item.status == "open"]
    open_position = None
    if open_rows:
        item = open_rows[0]
        open_position = {
            "side": item.side,
            "lots": item.remaining,
            "entry": item.entry,
            "stop": item.stop_loss,
        }
    loss = max(0.0, day_start - equity)
    loss_fraction = loss / day_start if day_start else 0.0
    return {
        "equity_r": round(equity_r, 2),
        "win_rate": (len(wins) / len(closed)) if closed else None,
        "expectancy_r": round(sum(trade_r) / len(trade_r), 2) if trade_r else None,
        "closed": len(closed),
        "open_position": open_position,
        "daily_loss": round(loss_fraction, 4),
        "daily_limit": config.daily_loss_fraction,
        "mode": "paper",
    }


def _rationale(reason: str, direction: str, language: str) -> str:
    arabic = language == "ar"
    if reason == "BOS_OR_SWEEP_BUY":
        return "كسر أو مسح صاعد على الهيكل المطبوع." if arabic else "Printed structure broke or swept upward."
    if reason == "BOS_OR_SWEEP_SELL":
        return "كسر أو مسح هابط على الهيكل المطبوع." if arabic else "Printed structure broke or swept downward."
    if direction == "wait":
        return "لا توجد صفقة تستوفي الحراسة." if arabic else "No plan cleared the guardrails."
    return reason
