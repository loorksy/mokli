"""Provider run observability columns."""

from alembic import op
from sqlalchemy import inspect

revision = "0002_provider_observability"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

COLUMNS = {
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


def upgrade() -> None:
    bind = op.get_bind()
    present = {column["name"] for column in inspect(bind).get_columns("providerrun")}
    for name, ddl in COLUMNS.items():
        if name not in present:
            op.execute(f"ALTER TABLE providerrun ADD COLUMN {name} {ddl}")


def downgrade() -> None:
    pass
