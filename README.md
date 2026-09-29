# Mokli

Personal, self-hosted agent for XAUUSD. One operator. Paper by default.

The model can propose. Lot size, spread, stale ticks, daily loss, and the approval gate are ordinary Python. They do not depend on the model agreeing.

## Run

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
export MOKLI_PASSPHRASE='change-me'
.venv/bin/mokli serve
```

UI:

```bash
cd web && npm install && npm run dev
```

Open `http://127.0.0.1:5173`. Arabic is the default. The chart stays left-to-right.

`docker compose up --build` serves the API and the built UI on `127.0.0.1:8787`.

## Safety

- `MOKLI_LIVE` defaults to `0`.
- A settings checkbox stores confirmation. It does not enable live trading by itself.
- Broker tools are rejected if an MCP server tries to expose them.
- Missing prices stay missing. Replay data is labeled `SIMULATOR`.

## Layout

- `src/mokli` gateway, risk, paper broker, detectors, provider adapters
- `rules/*.yaml` from `docs/SPEC_AR.md`
- `web` React, TypeScript, Tailwind
- `mobile` Capacitor wrapper and `scripts/build_apk.sh`
- `docs/PROVIDERS.md` pinned SDKs
- `docs/ASSUMPTIONS.md` choices the brief left open

## Tests

```bash
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy src/mokli
```
