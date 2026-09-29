"""In-process MCP tools. Broker actions are refused even if a server lists them."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

BROKER_TOOL_NAMES = frozenset(
    {"broker_market", "broker_close", "broker_modify", "broker_kill", "place_order"}
)


def analysis_server(atr_value: Callable[[], str]) -> MCPServer:
    server = MCPServer("mokli-analysis")

    @server.tool(description="Return the latest ATR already computed by Mokli.")
    def atr_value_tool() -> str:
        return atr_value()

    return server


def assert_mcp_tool_allowed(name: str) -> None:
    if name in BROKER_TOOL_NAMES:
        raise PermissionError(f"{name} is a broker tool and cannot be exposed through MCP")
