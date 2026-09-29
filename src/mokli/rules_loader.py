"""Load rules/*.yaml. Enabled flags live in the database and do not edit the files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    title_en: str
    title_ar: str
    type: str
    params: dict[str, object]
    default_enabled: bool
    weight: float


def rules_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "rules"


def load_rules(directory: Path | None = None) -> list[Rule]:
    root = directory or rules_dir()
    found: list[Rule] = []
    if not root.exists():
        return found
    for path in sorted(root.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for item in payload:
            found.append(
                Rule(
                    id=str(item["id"]),
                    category=str(item["category"]),
                    title_en=str(item["title_en"]),
                    title_ar=str(item["title_ar"]),
                    type=str(item["type"]),
                    params=dict(item.get("params") or {}),
                    default_enabled=bool(item.get("default_enabled", True)),
                    weight=float(item.get("weight", 1)),
                )
            )
    return found


def relevant_rules(rules: list[Rule], text: str, limit: int = 8) -> list[Rule]:
    words = {word.lower() for word in text.split() if len(word) > 3}
    ranked = []
    for rule in rules:
        if not rule.default_enabled or rule.type == "guardrail":
            continue
        haystack = f"{rule.title_en} {rule.category}".lower()
        score = sum(1 for word in words if word in haystack)
        if score:
            ranked.append((score * rule.weight, rule))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [rule for _score, rule in ranked[:limit]]
