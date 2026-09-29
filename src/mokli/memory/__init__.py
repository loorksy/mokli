"""Operator memory. Similar notes are found by tag overlap. No embeddings."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from mokli.schema import MemoryItem


def remember(engine: Engine, kind: str, body: str, tags: str = "") -> MemoryItem:
    if not body.strip():
        raise ValueError("memory body is empty")
    stored = body.strip() if not tags.strip() else f"{body.strip()}\n#{tags.strip()}"
    row = MemoryItem(kind=kind, body=stored)
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def recall(engine: Engine, query: str, limit: int = 8) -> list[MemoryItem]:
    needles = {part for part in query.lower().split() if len(part) > 2}
    with Session(engine) as session:
        rows = list(session.exec(select(MemoryItem).order_by(col(MemoryItem.id).desc())).all())
    if not needles:
        return rows[:limit]
    scored = []
    for row in rows:
        haystack = f"{row.kind} {row.body}".lower()
        score = sum(1 for needle in needles if needle in haystack)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]
