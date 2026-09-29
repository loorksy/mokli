"""Live orders require both the process flag and an explicit confirmation.

A broker token, a MetaApi account, or the settings checkbox alone does nothing.
"""

from __future__ import annotations


def live_orders_enabled(*, mokli_live: str, confirmed: bool) -> bool:
    return mokli_live == "1" and confirmed


def execution_book(*, mokli_live: str, confirmed: bool) -> str:
    if live_orders_enabled(mokli_live=mokli_live, confirmed=confirmed):
        return "live"
    return "paper"
