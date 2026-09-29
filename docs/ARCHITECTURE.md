# Architecture

Mokli is a single-user gateway for XAUUSD. The model proposes. Policy, risk, and the approval gate decide. The broker is last.

```
Web / Capacitor
      |
Mokli Gateway (FastAPI, sessions, event bus, SQLite)
      |
Agent runtime
  openai-agents SDK | Google ADK | Mokli deterministic runtime | provider APIs
      |
Tool bridge and in-process MCP (analysis only)
      |
Risk engine and execution re-check
      |
Approval
      |
Paper broker (default) or a live adapter that stays disconnected
```

## What was already in the repository

- `docs/SPEC_AR.md`: the translated gold rulebook.
- `docs/Engineering-skills`: a prompt-writing contract. It is reference material. The running agent is this service, not a standalone prompt file.
- An uncommitted risk kernel (sizing, stops, guardrails, news-candle marks, journal). Those functions are the risk and news core. Defaults were aligned with the product brief: cooldown 120 minutes, execution floor 1.5R, scale-out 40/30/30.

Nothing in that kernel sent orders. It was kept and wrapped by the gateway.

## Boundaries

- `evaluate_proposal` must pass before an approval can be staged.
- `execution_recheck` runs again on the fresh quote before a paper fill.
- MCP tool names in the broker set raise `PermissionError`.
- Provider changes are audited. The dashboard shows the provider, runtime, and model that were stored on the run.
- Market rows carry `source`. Simulator candles are labeled `simulator`. Empty books are `UNAVAILABLE`.

## Persistence

SQLite via SQLModel. `alembic/versions/0001_initial.py` creates the same metadata. Workspace markdown lives under `MOKLI_DATA_DIR/workspace` and is seeded from `deploy/workspace-template` without overwriting operator edits.

## Processes

`mokli serve` starts uvicorn on `MOKLI_HOST:MOKLI_PORT`. The web build in `web/dist` is served by the same process when it exists. Development uses Vite on port 5173 and proxies `/api`.
