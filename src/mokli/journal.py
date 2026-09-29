"""Lessons record. Credentials never land in the file. Field rule set 5.4 and security 7.2."""

from __future__ import annotations

import json
import re
from pathlib import Path

from mokli.models import Lesson

_SECRET = re.compile(r"password|api[_ ]?key|passphrase|account[_ ]?login", re.IGNORECASE)
_OUTCOMES = {"loss", "win", "scratch", "skipped"}


class JournalError(ValueError):
    """The lesson is empty, secret-bearing, or the file is not the journal format."""


def record_lesson(path: Path, lesson: Lesson) -> None:
    _validate(lesson)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "rule_id": lesson.rule_id,
            "summary": lesson.summary,
            "outcome": lesson.outcome,
            "created_at": lesson.created_at.isoformat(),
        },
        ensure_ascii=False,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_lessons(path: Path) -> tuple[Lesson, ...]:
    if not path.exists():
        return ()
    from datetime import datetime

    lessons: list[Lesson] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
            lesson = Lesson(
                rule_id=str(payload["rule_id"]),
                summary=str(payload["summary"]),
                outcome=payload["outcome"],
                created_at=datetime.fromisoformat(payload["created_at"]),
            )
            _validate(lesson)
        except (KeyError, TypeError, ValueError, JournalError) as exc:
            raise JournalError(f"line {line_number} is not a lesson") from exc
        lessons.append(lesson)
    return tuple(lessons)


def _validate(lesson: Lesson) -> None:
    if not lesson.rule_id.strip():
        raise JournalError("rule_id is required")
    if not lesson.summary.strip():
        raise JournalError("summary is required")
    if lesson.outcome not in _OUTCOMES:
        raise JournalError("outcome is not a known value")
    if _SECRET.search(lesson.summary) or _SECRET.search(lesson.rule_id):
        raise JournalError("lesson contains a forbidden credential field")
