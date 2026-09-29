"""PNG snapshots of the last candles plus entry, stop, and target lines."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from mokli.market.candles import Candle


def render_snapshot(
    candles: list[Candle],
    path: Path,
    *,
    entry: float | None = None,
    stop: float | None = None,
    target: float | None = None,
    title: str = "XAUUSD",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    image = Image.new("RGB", (width, height), "#12161d")
    draw = ImageDraw.Draw(image)
    draw.text((24, 16), title, fill="#d7b15a")
    window = candles[-80:]
    if not window:
        draw.text((24, 48), "No candles", fill="#ece8e1")
        image.save(path)
        return path
    prices = [candle.low for candle in window] + [candle.high for candle in window]
    for level in (entry, stop, target):
        if level is not None:
            prices.append(level)
    low = min(prices)
    high = max(prices)
    span = high - low or 1
    left, right, top, bottom = 40, width - 20, 48, height - 30

    def y_of(price: float) -> float:
        return top + (high - price) / span * (bottom - top)

    slot = (right - left) / len(window)
    for index, candle in enumerate(window):
        x = left + index * slot + slot / 2
        color = "#2fbf8a" if candle.close >= candle.open else "#e15d66"
        draw.line((x, y_of(candle.high), x, y_of(candle.low)), fill=color, width=1)
        body_top = y_of(max(candle.open, candle.close))
        body_bottom = y_of(min(candle.open, candle.close))
        draw.rectangle((x - slot * 0.3, body_top, x + slot * 0.3, max(body_bottom, body_top + 1)), fill=color)
    for level, color, label in (
        (entry, "#d7b15a", "entry"),
        (stop, "#e15d66", "stop"),
        (target, "#2fbf8a", "target"),
    ):
        if level is None:
            continue
        y = y_of(level)
        draw.line((left, y, right, y), fill=color, width=1)
        draw.text((left, y - 14), f"{label} {level:.2f}", fill=color)
    image.save(path)
    return path
