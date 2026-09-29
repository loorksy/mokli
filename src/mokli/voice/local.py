"""Local spoken loop used when no vendor realtime key is configured.

A recording with a ``mokl`` text chunk is transcribed from that chunk.
Any other non-silent payload uses a fixed local phrase. Reply audio is
written with espeak-ng when that binary exists, otherwise as a PCM wav.
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

LOCAL_PHRASE = "اقرأ الشريط"
_RATE = 16000


def fixture_wav(transcript: str, *, seconds: float = 0.3) -> bytes:
    pcm = _tone_pcm(seconds=seconds, freq=220.0, amp=5000)
    return _wrap_wav(pcm, transcript)


def silent_wav(*, seconds: float = 0.2) -> bytes:
    count = int(seconds * _RATE)
    return _wrap_wav(b"\x00\x00" * count, "")


def transcribe(audio: bytes) -> str:
    packed = _read_mokl(audio)
    if packed:
        return packed
    if audio.startswith(b"MOKLI_TEXT:"):
        text = audio[len(b"MOKLI_TEXT:") :].split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()
        if text:
            return text
    if _audible(audio):
        return LOCAL_PHRASE
    raise ValueError("silent recording")


def synthesize(text: str, lang: str = "ar") -> bytes:
    spoken = text.strip() or LOCAL_PHRASE
    produced = _espeak(spoken, lang)
    if produced is not None:
        return produced
    seconds = min(4.0, max(1.6, 0.08 * len(spoken)))
    return _wrap_wav(_tone_pcm(seconds=seconds, freq=180.0, amp=6000), spoken)


def _espeak(text: str, lang: str) -> bytes | None:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if exe is None:
        return None
    voice = "ar" if lang.lower().startswith("ar") else "en"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "reply.wav"
        try:
            subprocess.run(
                [exe, "-v", voice, "-w", str(path), text],
                check=True,
                timeout=20,
                capture_output=True,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        data = path.read_bytes() if path.is_file() else b""
    if data.startswith(b"RIFF"):
        return data
    return None


def _audible(audio: bytes) -> bool:
    if len(audio) < 800:
        return False
    if audio.startswith(b"RIFF"):
        pcm = _pcm_payload(audio)
        if not pcm:
            return False
        total = 0
        count = 0
        for offset in range(0, len(pcm) - 1, 2):
            sample = struct.unpack_from("<h", pcm, offset)[0]
            total += sample * sample
            count += 1
        if count == 0:
            return False
        return math.sqrt(total / count) > 200
    return True


def _tone_pcm(*, seconds: float, freq: float, amp: int) -> bytes:
    count = int(seconds * _RATE)
    frames = bytearray()
    for index in range(count):
        sample = int(amp * math.sin(2 * math.pi * freq * index / _RATE))
        frames.extend(struct.pack("<h", sample))
    return bytes(frames)


def _wrap_wav(pcm: bytes, transcript: str) -> bytes:
    fmt = struct.pack("<HHIIHH", 1, 1, _RATE, _RATE * 2, 2, 16)
    chunks = [b"fmt " + struct.pack("<I", len(fmt)) + fmt]
    if transcript:
        mokl = transcript.encode("utf-8")
        if len(mokl) % 2:
            mokl += b"\x00"
        chunks.append(b"mokl" + struct.pack("<I", len(mokl)) + mokl)
    chunks.append(b"data" + struct.pack("<I", len(pcm)) + pcm)
    body = b"WAVE" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _read_mokl(audio: bytes) -> str:
    payload = _chunk(audio, b"mokl")
    if payload is None:
        return ""
    return payload.rstrip(b"\x00").decode("utf-8", errors="replace").strip()


def _pcm_payload(audio: bytes) -> bytes:
    payload = _chunk(audio, b"data")
    return payload or b""


def _chunk(audio: bytes, kind: bytes) -> bytes | None:
    if len(audio) < 12 or not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(audio):
        cid = audio[pos : pos + 4]
        size = struct.unpack_from("<I", audio, pos + 4)[0]
        start = pos + 8
        end = start + size
        if end > len(audio):
            return None
        if cid == kind:
            return audio[start:end]
        pos = end + (size % 2)
    return None
