"""MCP registration, allowlist, discovery, timeout, and audit.

Broker execution tools are never registered, even if a server lists them.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from mcp.server.mcpserver import MCPServer

from mokli.runtime.toolbridge import BROKER_TOOL_NAMES


@dataclass
class McpRegistration:
    name: str
    server: MCPServer
    allowlist: frozenset[str]
    timeout_s: float
    side_effects: dict[str, str]
    approval: frozenset[str]


@dataclass
class McpAudit:
    agent_id: str
    server: str
    tool: str
    ok: bool
    detail: str
    latency_ms: int


@dataclass
class McpRegistry:
    servers: dict[str, McpRegistration] = field(default_factory=dict)
    audits: list[McpAudit] = field(default_factory=list)
    agent_permissions: dict[str, frozenset[str]] = field(default_factory=dict)

    def register(
        self,
        name: str,
        server: MCPServer,
        allowlist: set[str],
        *,
        timeout_s: float = 5,
        side_effects: dict[str, str] | None = None,
        approval: set[str] | None = None,
    ) -> None:
        clean = {item for item in allowlist if item not in BROKER_TOOL_NAMES}
        rejected = allowlist - clean
        if rejected:
            raise PermissionError(f"broker tools cannot be registered: {sorted(rejected)}")
        self.servers[name] = McpRegistration(
            name=name,
            server=server,
            allowlist=frozenset(clean),
            timeout_s=timeout_s,
            side_effects=side_effects or {},
            approval=frozenset(approval or set()),
        )

    def permit(self, agent_id: str, tools: set[str]) -> None:
        self.agent_permissions[agent_id] = frozenset(tools - BROKER_TOOL_NAMES)

    async def discover(self, agent_id: str) -> list[str]:
        allowed = self.agent_permissions.get(agent_id, frozenset())
        found: list[str] = []
        for registration in self.servers.values():
            listed = await registration.server.list_tools()
            for tool in listed:
                if tool.name in BROKER_TOOL_NAMES:
                    continue
                if tool.name in registration.allowlist and tool.name in allowed:
                    found.append(tool.name)
        return found

    async def call(self, agent_id: str, server: str, tool: str) -> str:
        started = time.perf_counter()
        registration = self.servers.get(server)
        if registration is None:
            self._audit(agent_id, server, tool, False, "unknown server", started)
            raise KeyError(server)
        if tool in BROKER_TOOL_NAMES or tool not in registration.allowlist:
            self._audit(agent_id, server, tool, False, "not allowlisted", started)
            raise PermissionError(f"{tool} is not allowlisted")
        if tool not in self.agent_permissions.get(agent_id, frozenset()):
            self._audit(agent_id, server, tool, False, "agent permission denied", started)
            raise PermissionError(f"{agent_id} cannot call {tool}")
        if tool in registration.approval:
            self._audit(agent_id, server, tool, False, "approval required", started)
            raise PermissionError(f"{tool} requires approval")
        try:
            result = await asyncio.wait_for(registration.server.call_tool(tool, {}), registration.timeout_s)
        except TimeoutError:
            self._audit(agent_id, server, tool, False, "timeout", started)
            raise
        text = _tool_text(result)
        self._audit(agent_id, server, tool, True, registration.side_effects.get(tool, "read"), started)
        return text

    def _audit(self, agent_id: str, server: str, tool: str, ok: bool, detail: str, started: float) -> None:
        self.audits.append(
            McpAudit(
                agent_id=agent_id,
                server=server,
                tool=tool,
                ok=ok,
                detail=detail,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        )


def _tool_text(result: object) -> str:
    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        return str(getattr(first, "text", first))
    if isinstance(result, tuple) and result:
        return _tool_text(result[0]) if not isinstance(result[0], str) else str(result[0])
    return str(result)
