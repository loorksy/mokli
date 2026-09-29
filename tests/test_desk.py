from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from mokli.config import Settings
from mokli.db import create_db_engine
from mokli.execution.live_gate import execution_book, live_orders_enabled
from mokli.execution.live_order import submit_live_order
from mokli.market.replay import ReplayClock
from mokli.memory import recall, remember
from mokli.schema import Approval
from mokli.voice.local import WHISPER_MODEL, fixture_wav, silent_wav, synthesize, transcribe
from mokli.voice.session import VoiceSession, VoiceTurn


def test_ui_dist_points_at_a_built_index_when_present() -> None:
    from mokli.gateway.app import _ui_dist

    found = _ui_dist()
    assert found is None or (found / "index.html").is_file()


def test_replay_clock_steps_and_stops_at_the_end() -> None:
    clock = ReplayClock()
    assert clock.arm(0) == -1
    clock.arm(5, start=1)
    assert clock.step(5) == 2
    clock.index = 4
    assert clock.step(5) == 4


def test_voice_turn_taking_and_barge_in() -> None:
    session = VoiceSession()
    assert session.start().state == "listening"

    def reply_of(text: str) -> VoiceTurn:
        return VoiceTurn(state="speaking", reply=f"heard {text}", provider="Mokli", model="deterministic-xauusd", runtime="Mokli Runtime")

    spoken = session.hear("what is gold", reply_of)
    assert spoken.state == "speaking"
    assert "gold" in spoken.reply
    assert session.barge_in().state == "listening"
    assert session.turn.interrupted is True
    session.hear("again", reply_of)
    assert session.finished_speaking().state == "idle"


def test_local_spoken_loop_ends_idle(tmp_path: Path) -> None:
    packed = fixture_wav("ما وضع الذهب")
    assert transcribe(packed) == "ما وضع الذهب"
    with pytest.raises(ValueError):
        transcribe(silent_wav())
    reply = synthesize("الذهب على إعادة تجريبية", "ar")
    assert reply.startswith(b"RIFF")
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", mokli_live="0")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    spoken = client.post(
        "/api/voice/turn",
        headers=headers,
        json={"audio_base64": base64.b64encode(packed).decode("ascii"), "lang": "ar"},
    ).json()
    assert spoken["state"] == "speaking"
    assert spoken["transcript"] == "ما وضع الذهب"
    audio = base64.b64decode(spoken["audio_base64"])
    assert audio.startswith(b"RIFF")
    assert client.post("/api/voice/spoken", headers=headers).json()["state"] == "idle"
    quiet = client.post(
        "/api/voice/turn",
        headers=headers,
        json={"audio_base64": base64.b64encode(silent_wav()).decode("ascii"), "lang": "ar"},
    ).json()
    assert quiet["state"] == "idle"
    assert quiet["error"] == "silent"


def test_two_recordings_are_not_one_fixed_sentence() -> None:
    assert WHISPER_MODEL == "small"
    root = Path(__file__).resolve().parent / "fixtures" / "voice"
    gold = (root / "gold-ar.wav").read_bytes()
    close = (root / "close-ar.wav").read_bytes()
    assert b"mokl" not in gold and b"mokl" not in close
    heard_gold = transcribe(gold, lang="ar")
    heard_close = transcribe(close, lang="ar")
    assert heard_gold != heard_close
    assert heard_gold != "اقرأ الشريط"
    assert heard_close != "اقرأ الشريط"
    assert "الذهب" in heard_gold
    assert "صفقة" in heard_close
    heard_webm = transcribe((root / "gold-ar.webm").read_bytes(), lang="ar")
    assert "الذهب" in heard_webm
    assert heard_webm != heard_close


def test_memory_recalls_by_overlap(tmp_path: Path) -> None:
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass")
    from mokli.db import create_db_engine, init_database

    engine = create_db_engine(settings)
    init_database(engine)
    remember(engine, "lesson", "Gold stalled under the Asian high and the sweep failed.", tags="gold sweep")
    remember(engine, "lesson", "Equities were quiet.", tags="equities")
    found = recall(engine, "gold sweep failed")
    assert found
    assert "Gold" in found[0].body


def test_credentials_do_not_enable_live_orders() -> None:
    assert live_orders_enabled(switch=False, broker_connected=True) is False
    assert live_orders_enabled(switch=True, broker_connected=False) is False
    assert execution_book(switch=False, broker_connected=True) == "paper"
    assert live_orders_enabled(switch=True, broker_connected=True) is True


def test_desk_replay_voice_and_debate(tmp_path: Path) -> None:
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", mokli_live="0")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    loaded = client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 4, "count": 80})
    assert loaded.json()["state"] == "SIMULATOR"
    armed = client.post("/api/market/replay/arm", headers=headers, params={"start": 30})
    assert armed.json()["state"] == "SIMULATOR"
    stepped = client.post("/api/market/replay/step", headers=headers).json()
    assert stepped["index"] == 31
    assert stepped["bid"] is not None
    cycle = client.post("/api/cycle", headers=headers).json()
    assert "notes" in cycle
    tree = client.get("/api/agents/tree", headers=headers).json()["nodes"]
    assert any(node["parent_id"] for node in tree)
    voice = client.post("/api/voice/start", headers=headers).json()
    assert voice["state"] == "listening"
    spoken = client.post("/api/voice/utterance", headers=headers, json={"transcript": "read the tape"}).json()
    assert spoken["state"] == "speaking"
    assert spoken["provider"] == "Mokli"
    assert spoken["runtime"] == "Mokli Runtime"
    assert client.post("/api/voice/spoken", headers=headers).json()["state"] == "idle"
    again = client.post("/api/voice/utterance", headers=headers, json={"transcript": "step the replay"}).json()
    assert again["state"] == "speaking"
    assert client.post("/api/voice/barge", headers=headers).json()["interrupted"] is True
    assert client.post("/api/voice/spoken", headers=headers).json()["state"] == "listening"
    remembered = client.post("/api/memory", headers=headers, json={"kind": "note", "body": "Wait when the spread is wide.", "tags": "spread"}).json()
    assert remembered["id"]
    recalled = client.get("/api/memory", headers=headers, params={"q": "spread wide"}).json()["memories"]
    assert recalled
    mcp = client.get("/api/mcp", headers=headers).json()
    assert "atr_value_tool" in mcp["tools"]
    assert "place_order" in mcp["broker_blocked"]
    live = client.get("/api/live", headers=headers).json()
    assert live["mode"] == "paper"
    assert live["orders"] == "paper"
    killed = client.post("/api/broker/kill", headers=headers)
    assert killed.json()["killed"] is True
    notes = client.get("/api/notifications", headers=headers).json()
    assert notes["channel"] == "in_app"
    assert any(item["title"] in {"Kill switch", "إيقاف طارئ"} for item in notes["notifications"])


def test_gold_chat_embeds_a_chart_and_a_public_card(tmp_path: Path) -> None:
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", mokli_live="0")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    loaded = client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 7})
    assert loaded.status_code == 200
    reply = client.post("/api/chat", headers=headers, json={"message": "ما وضع الذهب"})
    body = reply.json()
    assert body["chart"]["instrument"] == "XAUUSD"
    assert "Price context" not in body["text"]
    assert "البطاقة" in body["text"]
    card = body["recommendation"]
    assert card["direction"] == "buy"
    assert card["entry"] is not None
    assert card["stop"] is not None
    assert card["targets"]
    assert card["rationale"]
    assert card["confidence"]
    dumped = json.dumps(card).casefold()
    for hidden in ("bull", "bear", "greed", "emotion", "professional", "notes"):
        assert hidden not in dumped
    listed = client.get("/api/recommendations", headers=headers).json()["recommendations"]
    assert listed[0]["direction"] == "buy"
    assert "notes" not in listed[0]
    plain = client.post("/api/chat", headers=headers, json={"message": "price?"})
    assert "chart" not in plain.json()
    book = client.get("/api/performance", headers=headers).json()
    assert book["mode"] == "paper"
    for key in ("equity_r", "win_rate", "expectancy_r", "daily_loss", "daily_limit", "open_position"):
        assert key in book


def test_settings_keep_secrets_and_live_locked(tmp_path: Path) -> None:
    secret = "sk-test-secret-value"
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", mokli_live="0")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    connected = client.post("/api/settings/providers", headers=headers, json={"id": "openai", "secret": secret})
    assert connected.status_code == 200
    assert secret not in connected.text
    openai = next(row for row in connected.json()["connections"] if row["id"] == "openai")
    assert openai["connected"] is True
    again = client.get("/api/settings", headers=headers)
    assert secret not in again.text
    page = again.json()
    assert page["live_locked"] is True
    assert page["mode"] == "paper"
    assert page["orders"] == "paper"
    assert page["live_confirmed"] is False
    refused = client.put("/api/settings", headers=headers, json={"risk_fraction": 0.5})
    assert refused.status_code == 400
    locked = client.put("/api/settings", headers=headers, json={"live_confirmed": True})
    assert locked.status_code == 200
    assert locked.json()["live_confirmed"] is False
    assert locked.json()["mode"] == "paper"
    assert secret not in locked.text
    off = client.post("/api/settings/providers", headers=headers, json={"id": "openai", "disconnect": True})
    row = next(item for item in off.json()["connections"] if item["id"] == "openai")
    assert row["connected"] is False
    stored = (tmp_path / "provider.env").read_text(encoding="utf-8")
    assert secret not in stored


def _desk(tmp_path: Path) -> tuple[TestClient, dict[str, str], Settings]:
    settings = Settings(mokli_data_dir=str(tmp_path), mokli_passphrase="secret-pass", mokli_live="0")
    from mokli.gateway.app import create_app

    client = TestClient(create_app(settings))
    token = client.post("/api/auth/login", json={"passphrase": "secret-pass"}).json()["token"]
    return client, {"Authorization": f"Bearer {token}"}, settings


def test_unconfirmed_proposal_creates_no_order(tmp_path: Path) -> None:
    client, headers, _settings = _desk(tmp_path)
    loaded = client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 7})
    assert loaded.status_code == 200
    reply = client.post("/api/chat", headers=headers, json={"message": "ما وضع الذهب"})
    assert "هل أنفّذ؟" in reply.json()["text"]
    book = client.get("/api/positions", headers=headers).json()
    orders = client.get("/api/orders", headers=headers).json()
    assert book["positions"] == []
    assert orders["orders"] == []
    refused = client.post("/api/chat", headers=headers, json={"message": "لا"})
    assert refused.json()["execution"] == "rejected"
    assert client.get("/api/positions", headers=headers).json()["positions"] == []
    later = client.post("/api/chat", headers=headers, json={"message": "نعم"})
    assert later.json()["text"]
    assert "execution" not in later.json()
    assert client.get("/api/orders", headers=headers).json()["orders"] == []


def test_confirmed_proposal_that_fails_risk_creates_no_order(tmp_path: Path) -> None:
    client, headers, settings = _desk(tmp_path)
    assert client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 7}).status_code == 200
    with Session(create_db_engine(settings)) as session:
        session.add(
            Approval(
                id="bad-risk",
                status="pending",
                payload=json.dumps(
                    {
                        "side": "buy",
                        "entry": 2426.0,
                        "stop": 2425.99,
                        "target": 2426.01,
                        "lots": 0.01,
                        "reason_code": "TEST",
                    }
                ),
            )
        )
        session.commit()
    reply = client.post("/api/chat", headers=headers, json={"message": "نعم"})
    assert reply.json()["execution"] == "rejected_at_gate"
    assert client.get("/api/positions", headers=headers).json()["positions"] == []
    assert client.get("/api/orders", headers=headers).json()["orders"] == []


def test_confirmed_proposal_in_paper_mode_fills_on_paper_only(tmp_path: Path) -> None:
    client, headers, _settings = _desk(tmp_path)
    assert client.post("/api/market/replay/synthetic", headers=headers, params={"seed": 7}).status_code == 200
    asked = client.post("/api/chat", headers=headers, json={"message": "ما وضع الذهب"})
    assert "هل أنفّذ؟" in asked.json()["text"]
    assert client.get("/api/positions", headers=headers).json()["positions"] == []
    filled = client.post("/api/chat", headers=headers, json={"message": "نعم"})
    body = filled.json()
    assert body["execution"] == "executed"
    assert body["book"] == "paper"
    positions = client.get("/api/positions", headers=headers).json()["positions"]
    assert len(positions) == 1
    live = client.get("/api/live", headers=headers).json()
    assert live["mode"] == "paper"
    assert live["orders"] == "paper"


def test_live_code_refuses_when_the_switch_is_off(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def transport(proposal: dict[str, object]) -> str:
        calls.append(proposal)
        return "live-1"

    result = submit_live_order(
        switch=False,
        broker_connected=True,
        proposal={"side": "buy", "entry": 1},
        transport=transport,
    )
    assert result.sent is False
    assert result.reason == "switch_off"
    assert calls == []
    client, headers, _settings = _desk(tmp_path)
    turned = client.put("/api/settings", headers=headers, json={"live_orders": True})
    assert turned.json()["live_orders"] is False
    assert turned.json()["mode"] == "paper"
    assert turned.json()["orders"] == "paper"


def test_bot_is_saved_and_does_not_trade(tmp_path: Path) -> None:
    client, headers, settings = _desk(tmp_path)
    message = "ابن بوت اتجاه على الذهب، فريم الساعة، دخول مع الكسر، خروج عند الهدف، وقف تحت القاع، مخاطرة 1%، جلسة لندن"
    created = client.post("/api/chat", headers=headers, json={"message": message}).json()
    bot = created["bot"]
    assert bot["instrument"] == "XAUUSD"
    assert bot["kind"] == "trend"
    assert bot["timeframe"] == "H1"
    assert bot["session"] == "London"
    assert "كسر" in bot["entry"]
    assert bot["size_rule"] == "1% of equity"
    assert client.get("/api/positions", headers=headers).json()["positions"] == []
    with Session(create_db_engine(settings)) as session:
        session.add(Approval(id="bot-ask", status="pending", payload=json.dumps({"kind": "order", "bot_id": bot["id"], "side": "buy"})))
        session.commit()
    deleted = client.post("/api/chat", headers=headers, json={"message": "احذف البوت"}).json()
    assert "حُذف" in deleted["text"]
    assert client.get("/api/bots", headers=headers).json()["bots"] == []
    with Session(create_db_engine(settings)) as session:
        row = session.get(Approval, "bot-ask")
        assert row is not None
        assert row.status == "cancelled"
    assert client.get("/api/orders", headers=headers).json()["orders"] == []
