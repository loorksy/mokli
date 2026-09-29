"""Engine, sessions, and the one-time passphrase user."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from mokli.config import Settings
from mokli.schema import User


def create_db_engine(settings: Settings) -> Engine:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{settings.database_path}"
    return create_engine(url, connect_args={"check_same_thread": False})


_PROVIDER_COLUMNS = {
    "sdk": "VARCHAR DEFAULT ''",
    "agent_id": "VARCHAR DEFAULT ''",
    "parent_agent_id": "VARCHAR DEFAULT ''",
    "session_id": "VARCHAR DEFAULT ''",
    "estimated_cost": "FLOAT DEFAULT 0",
    "tool_calls": "INTEGER DEFAULT 0",
    "subagents": "INTEGER DEFAULT 0",
    "retries": "INTEGER DEFAULT 0",
    "failures": "VARCHAR DEFAULT ''",
    "fallbacks": "VARCHAR DEFAULT ''",
    "original_provider": "VARCHAR DEFAULT ''",
    "original_model": "VARCHAR DEFAULT ''",
    "original_runtime": "VARCHAR DEFAULT ''",
    "fallback_provider": "VARCHAR DEFAULT ''",
    "fallback_model": "VARCHAR DEFAULT ''",
    "fallback_runtime": "VARCHAR DEFAULT ''",
    "fallback_reason": "VARCHAR DEFAULT ''",
    "fallback_at": "DATETIME",
}


def init_database(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    if not inspector.has_table("providerrun"):
        return
    present = {column["name"] for column in inspector.get_columns("providerrun")}
    with engine.begin() as connection:
        for name, ddl in _PROVIDER_COLUMNS.items():
            if name not in present:
                connection.execute(text(f"ALTER TABLE providerrun ADD COLUMN {name} {ddl}"))


def hash_passphrase(passphrase: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def verify_passphrase(passphrase: str, stored: str) -> bool:
    salt_hex, _digest = stored.split(":", 1)
    candidate = hash_passphrase(passphrase, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, stored)


def ensure_user(engine: Engine, passphrase: str) -> None:
    with Session(engine) as session:
        existing = session.exec(select(User)).first()
        if existing is None:
            session.add(User(passphrase_hash=hash_passphrase(passphrase)))
            session.commit()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def fernet_key_bytes(settings: Settings) -> bytes:
    """Key material lives in the environment or a 0600 file under the data dir."""
    from cryptography.fernet import Fernet

    if settings.mokli_fernet_key:
        return settings.mokli_fernet_key.encode()
    path = settings.data_dir / "fernet.key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip().encode()
    key = Fernet.generate_key()
    path.write_text(key.decode(), encoding="utf-8")
    path.chmod(0o600)
    return key


def workspace_root_file() -> Path:
    return Path(__file__).resolve().parents[2] / "deploy" / "workspace-template"
