"""Spoken turn-taking. Listening, thinking, and speaking are explicit states.

This is the self-hosted path. It does not call a vendor realtime socket.
The browser supplies recognition and speech when those APIs exist. Tests
drive the same session with text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class VoiceTurn:
    state: str
    transcript: str = ""
    reply: str = ""
    interrupted: bool = False
    provider: str = ""
    model: str = ""
    runtime: str = ""
    agent: str = "Mokli"
    status: str = ""
    tools: list[str] = field(default_factory=list)


class VoiceSession:
    def __init__(self) -> None:
        self.turn = VoiceTurn(state="idle")

    def start(self) -> VoiceTurn:
        self.turn = VoiceTurn(state="listening")
        return self.turn

    def hear(self, transcript: str, reply_of: Callable[[str], VoiceTurn]) -> VoiceTurn:
        text = transcript.strip()
        if self.turn.state == "speaking":
            self.barge_in()
        if self.turn.state not in {"listening", "idle"}:
            raise RuntimeError(f"voice session cannot hear while {self.turn.state}")
        if not text:
            raise ValueError("empty utterance")
        self.turn = VoiceTurn(state="thinking", transcript=text)
        spoken = reply_of(text)
        self.turn = VoiceTurn(
            state="speaking",
            transcript=text,
            reply=spoken.reply,
            provider=spoken.provider,
            model=spoken.model,
            runtime=spoken.runtime,
            agent=spoken.agent or "Mokli",
            status=spoken.status,
            tools=list(spoken.tools),
        )
        return self.turn

    def deliver(self, transcript: str, spoken: VoiceTurn) -> VoiceTurn:
        text = transcript.strip()
        if self.turn.state == "speaking":
            self.barge_in()
        if self.turn.state not in {"listening", "idle"}:
            raise RuntimeError(f"voice session cannot hear while {self.turn.state}")
        if not text:
            raise ValueError("empty utterance")
        self.turn = VoiceTurn(
            state="speaking",
            transcript=text,
            reply=spoken.reply,
            provider=spoken.provider,
            model=spoken.model,
            runtime=spoken.runtime,
            agent=spoken.agent or "Mokli",
            status=spoken.status,
            tools=list(spoken.tools),
        )
        return self.turn

    def finished_speaking(self) -> VoiceTurn:
        if self.turn.state == "listening":
            return self.turn
        if self.turn.state != "speaking":
            raise RuntimeError(f"nothing is speaking ({self.turn.state})")
        self.turn = VoiceTurn(
            state="listening",
            transcript=self.turn.transcript,
            reply=self.turn.reply,
            provider=self.turn.provider,
            model=self.turn.model,
            runtime=self.turn.runtime,
            agent=self.turn.agent,
            status=self.turn.status,
            tools=list(self.turn.tools),
        )
        return self.turn

    def barge_in(self) -> VoiceTurn:
        if self.turn.state != "speaking":
            return self.turn
        self.turn = VoiceTurn(state="listening", transcript=self.turn.transcript, interrupted=True)
        return self.turn

    def snapshot(self) -> dict[str, object]:
        turn = self.turn
        return {
            "state": turn.state,
            "transcript": turn.transcript,
            "reply": turn.reply,
            "interrupted": turn.interrupted,
            "provider": turn.provider,
            "model": turn.model,
            "runtime": turn.runtime,
            "agent": turn.agent,
            "status": turn.status,
            "tools": turn.tools,
        }
