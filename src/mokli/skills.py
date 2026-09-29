"""Skills are markdown files with a small frontmatter block. The UI toggles them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)
    body: str = ""
    path: Path | None = None
    enabled: bool = True


_FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def parse_skill(text: str, path: Path | None = None) -> Skill:
    match = _FRONT.match(text.strip() + "\n" if not text.endswith("\n") else text)
    if match is None:
        raise ValueError("skill is missing frontmatter")
    raw, body = match.group(1), match.group(2)
    data: dict[str, object] = {}
    current: str | None = None
    items: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current:
            items.append(line.split("  - ", 1)[1].strip())
            data[current] = items
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current = key.strip()
        items = []
        data[current] = value.strip()
    triggers = data.get("triggers")
    permissions = data.get("permissions")
    return Skill(
        name=str(data.get("name") or ""),
        description=str(data.get("description") or ""),
        triggers=list(triggers) if isinstance(triggers, list) else [],
        permissions=list(permissions) if isinstance(permissions, list) else [],
        body=body.strip(),
        path=path,
    )


def load_skills(root: Path) -> list[Skill]:
    skills: list[Skill] = []
    if not root.exists():
        return skills
    for path in sorted(root.glob("*/SKILL.md")):
        skills.append(parse_skill(path.read_text(encoding="utf-8"), path))
    return skills
