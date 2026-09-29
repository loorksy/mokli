"""Turn docs/SPEC_AR.md numbered rules into rules/*.yaml."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "SPEC_AR.md"
OUT = ROOT / "rules"

GUARDRAILS = {
    "field.035",
    "field.047",
    "field.118",
    "field.184",
    "field.187",
    "field.188",
    "field.189",
    "field.191",
    "field.194",
    "field.195",
    "field.197",
    "field.199",
    "news.001",
    "news.016",
    "news.035",
    "news.088",
}
DETECTORS = {
    "field.001",
    "field.004",
    "candle.010",
    "candle.016",
    "candle.017",
    "candle.018",
    "candle.020",
    "candle.030",
    "candle.031",
    "candle.046",
    "candle.100",
}

AR_CATEGORY = {
    "entry": "الدخول",
    "stop": "وقف الخسارة",
    "retest": "إعادة الاختبار",
    "trend": "خطوط الاتجاه",
    "gold": "سلوك الذهب",
    "targets": "الأهداف",
    "candles": "الشموع",
    "execution": "التنفيذ",
    "pre": "ما قبل الخبر",
    "data": "قراءة البيانات",
    "micro": "شمعة الخبر",
    "ride": "بعد الخبر",
    "geo": "الملاذ",
    "time": "توقيت الشمعة",
    "range": "المدى",
    "volume": "الحجم",
    "spread": "السبريد",
    "sync": "التزامن",
    "geometry": "شكل الشمعة",
    "breaking": "الأخبار العاجلة",
}


def category_for(part: str, number: int) -> str:
    if part == "field":
        bands = [(25, "entry"), (55, "stop"), (80, "retest"), (105, "trend"), (135, "gold"), (160, "targets"), (180, "candles"), (200, "execution")]
    elif part == "news":
        bands = [(18, "pre"), (34, "data"), (55, "micro"), (86, "ride"), (100, "geo")]
    else:
        bands = [(15, "time"), (30, "range"), (45, "volume"), (60, "spread"), (75, "sync"), (90, "geometry"), (100, "breaking")]
    for limit, name in bands:
        if number <= limit:
            return name
    return bands[-1][1]


def parse_part(text: str, start: str, end: str | None) -> list[tuple[int, str]]:
    body = text.split(start, 1)[1]
    if end:
        body = body.split(end, 1)[0]
    rules: list[tuple[int, str]] = []
    for match in re.finditer(r"(?m)^(\d+)\.\s+(.+)$", body):
        rules.append((int(match.group(1)), match.group(2).strip()))
    return rules


def dump(name: str, part: str, rows: list[tuple[int, str]]) -> None:
    payload = []
    for number, title in rows:
        rule_id = f"{part}.{number:03d}"
        if rule_id in GUARDRAILS:
            kind = "guardrail"
        elif rule_id in DETECTORS:
            kind = "detector"
        else:
            kind = "heuristic"
        category = category_for(part, number)
        payload.append(
            {
                "id": rule_id,
                "category": category,
                "title_en": title,
                "title_ar": f"{AR_CATEGORY[category]}: {title}",
                "type": kind,
                "params": {},
                "default_enabled": True,
                "weight": 1,
            }
        )
    path = OUT / name
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{path.name} {len(payload)}")


def main() -> None:
    text = SPEC.read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    dump("field.yaml", "field", parse_part(text, "PART B", "PART C"))
    dump("news_playbook.yaml", "news", parse_part(text, "PART C", "PART D"))
    dump("news_candle.yaml", "candle", parse_part(text, "PART D", None))


if __name__ == "__main__":
    main()
