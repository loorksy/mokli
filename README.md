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

- `MOKLI_LIVE` defaults to unset, which the process reads as `0`. Leave it unset.
- A settings checkbox stores confirmation. It does not enable live trading by itself.
- A MetaApi token, an OANDA token, or a Telegram bot token does not place a live order.
- Live orders need both `MOKLI_LIVE=1` and the confirmation flag. This build still refuses that path: approval returns 409 and the fill stays on `PaperBroker`. Do not set `MOKLI_LIVE` until a later release wires a live adapter on purpose.
- Broker tools are rejected if an MCP server tries to expose them.
- Missing prices stay missing. Replay data is labeled `SIMULATOR`.

## Safe live deployment

Paper and replay are the deployment you run. Bind the API to `127.0.0.1`. Put secrets in the environment, never in the repo.

```bash
export MOKLI_PASSPHRASE='change-me'
# Do not export MOKLI_LIVE.
docker compose up --build
```

Compose publishes `127.0.0.1:8787` and sets `MOKLI_LIVE=0` inside the container. The process listens on `0.0.0.0` only so the published port can reach it.

If you later add broker credentials for a rehearsal:

1. Keep `MOKLI_LIVE` unset.
2. Leave the settings confirmation off.
3. Confirm `/api/live` reports `mode=paper` and `orders=paper` before any approval.
4. Treat MetaApi as disconnected. A token alone leaves it `SIMULATOR` or `UNAVAILABLE`.
5. Kill switch flattens the paper book and writes an in-app notification. It does not call a broker.

Voice records from the microphone, transcribes on the server with faster-whisper `small`, and plays Mokli's reply as audio. A packed transcript is only a test shortcut. A normal recording is transcribed from the audio, including Arabic. The turn shows listening, then speaking, then idle. It does not open a paid realtime socket.

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
