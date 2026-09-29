"""Normalize provider stream objects into Mokli events."""

from __future__ import annotations

from mokli.runtime.types import MokliEvent


def event(kind: str, **payload: object) -> MokliEvent:
    return MokliEvent(kind=kind, payload=payload)


def from_openai_stream(item: object) -> list[MokliEvent]:
    kind = getattr(item, "type", "")
    if kind == "raw_response_event":
        data = getattr(item, "data", None)
        data_type = getattr(data, "type", "")
        if data_type == "response.output_text.delta":
            return [event("agent_message_delta", text=getattr(data, "delta", ""))]
        return []
    if kind == "run_item_stream_event":
        name = getattr(item, "name", "")
        mapping = {
            "tool_called": "tool_call_started",
            "tool_output": "tool_call_completed",
            "message_output_created": "agent_message_completed",
            "handoff_requested": "handoff_started",
            "handoff_occured": "handoff_completed",
            "mcp_approval_requested": "approval_required",
        }
        mapped = mapping.get(name)
        if mapped is None:
            return []
        return [event(mapped, name=name)]
    if kind == "agent_updated_stream_event":
        agent = getattr(item, "new_agent", None)
        return [event("subagent_started", agent=getattr(agent, "name", ""))]
    return []


def from_claude_message(message: object) -> list[MokliEvent]:
    from claude_agent_sdk import (
        AssistantMessage,
        ResultMessage,
        StreamEvent,
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
    )

    if isinstance(message, AssistantMessage):
        found: list[MokliEvent] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                found.append(event("agent_message_delta", text=block.text))
                found.append(event("agent_message_completed", text=block.text))
            elif isinstance(block, ToolUseBlock):
                found.append(event("tool_call_started", name=block.name))
            elif isinstance(block, ThinkingBlock):
                found.append(event("agent_message_delta", text=block.thinking, reasoning=True))
        if message.usage:
            found.append(event("usage_updated", usage=dict(message.usage)))
        if message.parent_tool_use_id:
            found.append(event("subagent_completed", parent_tool_use_id=message.parent_tool_use_id))
        return found
    if isinstance(message, StreamEvent):
        inner = message.event or {}
        delta = inner.get("delta") if isinstance(inner, dict) else None
        text = ""
        if isinstance(delta, dict):
            text = str(delta.get("text") or "")
        if text:
            return [event("agent_message_delta", text=text)]
        return []
    if isinstance(message, ResultMessage):
        found = [event("usage_updated", usage=dict(message.usage or {}), cost=message.total_cost_usd)]
        if message.is_error:
            found.append(event("agent_failed", detail=message.result or message.subtype))
        return found
    return []


def from_adk_event(item: object) -> list[MokliEvent]:
    content = getattr(item, "content", None)
    parts = getattr(content, "parts", None) or []
    found: list[MokliEvent] = []
    for part in parts:
        function_call = getattr(part, "function_call", None)
        function_response = getattr(part, "function_response", None)
        text = getattr(part, "text", None)
        if function_call is not None:
            found.append(event("tool_call_started", name=getattr(function_call, "name", "")))
        elif function_response is not None:
            found.append(event("tool_call_completed", name=getattr(function_response, "name", "")))
        elif text:
            found.append(event("agent_message_delta", text=text))
            found.append(event("agent_message_completed", text=text))
    return found
