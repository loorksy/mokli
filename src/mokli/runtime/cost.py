"""Rough token-cost estimates. These are not invoices."""

from __future__ import annotations

# USD per 1M tokens: (input, output). Unknown models use a flat placeholder.
_RATES: dict[str, tuple[float, float]] = {
    "gpt-4.1": (2.0, 8.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "gemini-2.5-flash": (0.15, 0.6),
    "kimi-k2-turbo-preview": (1.0, 3.0),
    "glm-4.5": (0.6, 2.2),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = _RATES.get(model, (1.0, 3.0))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
