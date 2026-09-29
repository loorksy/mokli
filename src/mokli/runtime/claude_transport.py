"""In-memory Claude Agent SDK transport for offline tests.

The SDK still runs query(): it writes the initialize control request, routes
in-process MCP tool calls, and parses assistant and result frames. This class
stands in for the Claude Code CLI process, which is not started.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import Transport


class ScriptedClaudeTransport(Transport):
    def __init__(self, price_text: str) -> None:
        self.price_text = price_text
        self.written: list[dict[str, Any]] = []
        self.agents: dict[str, Any] | None = None
        self._queue: list[dict[str, Any] | None] = []
        self._waiting: list[Any] = []
        self._ready = False
        self._phase = "idle"
        self.interrupted = False

    async def connect(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def write(self, data: str) -> None:
        payload = json.loads(data)
        self.written.append(payload)
        if payload.get("type") == "control_request":
            request = payload.get("request") or {}
            subtype = request.get("subtype")
            if subtype == "initialize":
                self.agents = request.get("agents")
                self._push(_ok(payload["request_id"], {"commands": [], "output_style": "normal"}))
            elif subtype == "interrupt":
                self.interrupted = True
                self._push(_ok(payload["request_id"], {}))
            else:
                self._push(_ok(payload["request_id"], {}))
            return
        if payload.get("type") == "user" and self._phase == "idle":
            self._phase = "initialize"
            self._push(_mcp("initialize", 1, {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "mokli-offline", "version": "0"},
            }))
            return
        if payload.get("type") != "control_response":
            return
        response = payload.get("response", {}).get("response", {})
        mcp = response.get("mcp_response") if isinstance(response, dict) else None
        if self._phase == "initialize":
            self._phase = "initialized"
            self._push(_mcp_notification("notifications/initialized"))
            return
        if self._phase == "initialized":
            self._phase = "call"
            self._push(_mcp("tools/call", 2, {"name": "get_gold_price", "arguments": {}}))
            return
        if self._phase == "call":
            self._phase = "done"
            text = self.price_text
            if isinstance(mcp, dict):
                content = mcp.get("result", {}).get("content")
                if isinstance(content, list) and content:
                    text = str(content[0].get("text", text))
            self._push({
                "type": "assistant",
                "session_id": "claude-session",
                "message": {
                    "role": "assistant",
                    "model": "claude-sonnet-4-5",
                    "content": [{"type": "text", "text": text}],
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 5,
                        "cache_read_input_tokens": 3,
                    },
                },
            })
            self._push({
                "type": "stream_event",
                "uuid": "stream-1",
                "session_id": "claude-session",
                "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}},
            })
            self._push({
                "type": "result",
                "subtype": "success",
                "duration_ms": 12,
                "duration_api_ms": 9,
                "is_error": False,
                "num_turns": 2,
                "session_id": "claude-session",
                "total_cost_usd": 0.0002,
                "usage": {
                    "input_tokens": 11,
                    "output_tokens": 5,
                    "cache_read_input_tokens": 3,
                },
                "result": text,
                "structured_output": {"summary": text},
            })
            self._push(None)

    def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        return self._read()

    async def _read(self) -> AsyncIterator[dict[str, Any]]:
        import anyio

        while True:
            if self._queue:
                item = self._queue.pop(0)
                if item is None:
                    return
                yield item
                continue
            event = anyio.Event()
            self._waiting.append(event)
            await event.wait()

    async def close(self) -> None:
        self._ready = False
        self._push(None)

    async def end_input(self) -> None:
        self._push(None)

    def _push(self, item: dict[str, Any] | None) -> None:
        self._queue.append(item)
        waiting, self._waiting = self._waiting, []
        for event in waiting:
            event.set()


def _ok(request_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "control_response",
        "response": {"subtype": "success", "request_id": request_id, "response": body},
    }


def _mcp(method: str, request_id: int, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "control_request",
        "request_id": f"cli-{request_id}",
        "request": {
            "subtype": "mcp_message",
            "server_name": "mokli",
            "message": {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        },
    }


def _mcp_notification(method: str) -> dict[str, Any]:
    return {
        "type": "control_request",
        "request_id": "cli-note",
        "request": {
            "subtype": "mcp_message",
            "server_name": "mokli",
            "message": {"jsonrpc": "2.0", "method": method},
        },
    }
