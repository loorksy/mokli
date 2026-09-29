"""Live orders require the settings switch and a connected broker.

A token alone does nothing. The process flag alone does nothing. The switch
off means the live path refuses, even when a broker is connected.
"""

from __future__ import annotations


def live_orders_enabled(*, switch: bool, broker_connected: bool) -> bool:
    return bool(switch and broker_connected)


def execution_book(*, switch: bool, broker_connected: bool) -> str:
    if live_orders_enabled(switch=switch, broker_connected=broker_connected):
        return "live"
    return "paper"
