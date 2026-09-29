from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mokli.config import Settings
from mokli.execution.live_gate import execution_book, live_orders_enabled
from mokli.market.replay import ReplayClock
from mokli.memory import recall, remember
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
    assert session.finished_speaking().state == "listening"


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
    assert live_orders_enabled(mokli_live="0", confirmed=True) is False
    assert live_orders_enabled(mokli_live="1", confirmed=False) is False
    assert execution_book(mokli_live="0", confirmed=True) == "paper"
    assert live_orders_enabled(mokli_live="1", confirmed=True) is True


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
    assert client.post("/api/voice/spoken", headers=headers).json()["state"] == "listening"
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
