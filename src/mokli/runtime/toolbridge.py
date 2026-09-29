"""One Mokli tool, translated into each provider's native tool shape.

Broker execution tools are refused here. No provider SDK receives broker
credentials or broker methods through this bridge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mokli.runtime.types import SideEffect

BROKER_TOOL_NAMES = frozenset(
    {"broker_market", "broker_close", "broker_modify", "broker_kill", "place_order"}
)


@dataclass
class MokliTool:
    name: str
    description: str
    parameters: dict[str, object]
    handler: Callable[[dict[str, object]], str]
    side_effect: SideEffect = "read"
    requires_approval: bool = False


@dataclass
class ToolBridge:
    tools: list[MokliTool] = field(default_factory=list)
    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def register(self, tool: MokliTool) -> None:
        if tool.name in BROKER_TOOL_NAMES or tool.side_effect == "broker":
            raise PermissionError(f"{tool.name} is a broker tool and cannot be exposed")
        self.tools = [item for item in self.tools if item.name != tool.name]
        self.tools.append(tool)

    def exposed(self) -> list[MokliTool]:
        return [
            tool
            for tool in self.tools
            if tool.name not in BROKER_TOOL_NAMES and tool.side_effect != "broker"
        ]

    def invoke(self, name: str, arguments: dict[str, object]) -> str:
        if name in BROKER_TOOL_NAMES:
            raise PermissionError(f"{name} is a broker tool and cannot be executed by an agent")
        match = next((tool for tool in self.exposed() if tool.name == name), None)
        if match is None:
            raise KeyError(name)
        if match.requires_approval:
            raise PermissionError(f"{name} requires approval before execution")
        self.calls.append((name, arguments))
        return match.handler(arguments)

    def openai_tools(self) -> list[Any]:
        built: list[Any] = []
        for tool in self.exposed():
            built.append(_openai_tool(self, tool.name, tool.description))
        return built

    def claude_server(self) -> object:
        from claude_agent_sdk import create_sdk_mcp_server

        wrapped: list[Any] = []
        for item in self.exposed():
            wrapped.append(_claude_tool(self, item.name, item.description))
        return create_sdk_mcp_server(name="mokli", version="0.1.0", tools=wrapped)

    def adk_tools(self) -> list[Any]:
        from google.adk.tools.function_tool import FunctionTool

        built: list[Any] = []
        for item in self.exposed():
            built.append(FunctionTool(_adk_tool(self, item.name, item.description)))
        return built

    def json_schemas(self) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.exposed()
        ]


def _claude_tool(bridge: ToolBridge, name: str, description: str) -> Any:
    from claude_agent_sdk import tool

    async def handler(args: dict[str, object]) -> dict[str, object]:
        text = bridge.invoke(name, args or {})
        return {"content": [{"type": "text", "text": text}]}

    return tool(name, description, {"type": "object", "properties": {}})(handler)


def _openai_tool(bridge: ToolBridge, name: str, description: str) -> Any:
    from agents import function_tool

    def impl() -> str:
        return bridge.invoke(name, {})

    impl.__name__ = name
    impl.__doc__ = description
    return function_tool(impl, name_override=name, description_override=description, strict_mode=False)


def _adk_tool(bridge: ToolBridge, name: str, description: str):
    def impl() -> str:
        return bridge.invoke(name, {})

    impl.__name__ = name
    impl.__doc__ = description
    return impl


def gold_price_tool(reader: Callable[[], str]) -> MokliTool:
    def handler(_arguments: dict[str, object]) -> str:
        return reader()

    return MokliTool(
        name="get_gold_price",
        description="Return the latest XAUUSD price already computed by Mokli. Do not invent a price.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=handler,
        side_effect="read",
    )
