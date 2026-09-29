# Runbook

## Paper, on this machine

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
# set MOKLI_PASSPHRASE
.venv/bin/mokli serve
```

The API listens on `127.0.0.1:8787`. Build the UI with `cd web && npm install && npm run build`, or run `npm run dev` and open `http://127.0.0.1:5173`.

Sign in with the passphrase. On the dashboard, load a replay. That marks the feed `SIMULATOR`. Run a cycle. Approvals appear when the deterministic book proposes a buy or sell that passes risk. Approving runs the execution re-check, then the paper broker.

The kill switch flattens the paper book and cancels pending orders.

## Live

Leave `MOKLI_LIVE` unset or `0`. Turning on the settings checkbox only stores confirmation. Both that flag and `MOKLI_LIVE=1` are required, and the MetaApi adapter still reports disconnected until its extra is installed and a connect call is made. Do not point a live account at this process until you have watched a paper session.

## Docker

```bash
MOKLI_PASSPHRASE='a long passphrase' docker compose up --build
```

The published port is localhost only.

## Checks

```bash
ruff check src tests
mypy src/mokli
pytest
cd web && npm run typecheck
```

## Secrets

Fernet key material is `MOKLI_FERNET_KEY` or a `0600` file `fernet.key` under the data directory. Do not commit `.env`.
