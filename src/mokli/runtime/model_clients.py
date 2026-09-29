"""Native model APIs used under the Mokli loop, or as the fallback after an agent SDK."""

from __future__ import annotations

import json
from typing import Any

import httpx

from mokli.runtime.loop import ModelClient
from mokli.runtime.types import ModelTurn


def _turn_from_message(message: dict[str, Any], usage: dict[str, Any] | None) -> ModelTurn:
    tool_calls: list[tuple[str, dict[str, object]]] = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw = function.get("arguments") or "{}"
        arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
        tool_calls.append((str(function.get("name")), arguments))
    usage = usage or {}
    details = usage.get("prompt_tokens_details") or {}
    text = str(message.get("content") or "")
    return ModelTurn(
        text=text,
        tool_calls=tool_calls,
        deltas=[text] if text else [],
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        cached_tokens=int(details.get("cached_tokens") or usage.get("cache_read_input_tokens") or 0),
    )


class OpenAIChatClient(ModelClient):
    """Official OpenAI chat completions client. This is the model API behind the Agents SDK."""

    provider = "openai"
    runtime = "openai_chat"
    sdk = "openai"

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        response = self.client.chat.completions.create(model=self.model, messages=messages, tools=tools)
        choice = response.choices[0].message
        raw_calls = []
        for call in choice.tool_calls or []:
            raw_calls.append(
                {
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    }
                }
            )
        usage = getattr(response, "usage", None)
        payload = {
            "content": choice.content,
            "tool_calls": raw_calls,
        }
        usage_payload = None
        if usage is not None:
            details = getattr(usage, "prompt_tokens_details", None)
            usage_payload = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "prompt_tokens_details": {
                    "cached_tokens": getattr(details, "cached_tokens", 0) or 0
                },
            }
        return _turn_from_message(payload, usage_payload)


class OpenAICompatibleClient(ModelClient):
    """Moonshot/Kimi native HTTP. kimi-sdk is not imported; see docs/PROVIDERS.md."""

    provider = "kimi"
    runtime = "mokli_runtime"
    sdk = "moonshot-http"
    model = "kimi-k2-turbo-preview"

    def __init__(self, api_key: str, model: str, base_url: str, http: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.Client(timeout=30)

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        response = self.http.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages, "tools": tools},
        )
        response.raise_for_status()
        body = response.json()
        choice = body["choices"][0]["message"]
        return _turn_from_message(choice, body.get("usage"))


class OllamaModelClient(ModelClient):
    provider = "ollama"
    runtime = "mokli_runtime"
    sdk = "ollama"
    model = ""

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        response = self.client.chat(model=self.model, messages=messages, tools=tools, stream=False)
        message = response.message if hasattr(response, "message") else response["message"]
        content = message.content if hasattr(message, "content") else message.get("content", "")
        raw_calls = message.tool_calls if hasattr(message, "tool_calls") else message.get("tool_calls") or []
        calls: list[tuple[str, dict[str, object]]] = []
        for call in raw_calls or []:
            function = call.function if hasattr(call, "function") else call.get("function", {})
            name = function.name if hasattr(function, "name") else function.get("name")
            arguments = function.arguments if hasattr(function, "arguments") else function.get("arguments", {})
            calls.append((str(name), dict(arguments or {})))
        text = str(content or "")
        return ModelTurn(text=text, tool_calls=calls, deltas=[text] if text else [], input_tokens=8, output_tokens=4)


class OpenRouterModelClient(ModelClient):
    provider = "openrouter"
    runtime = "mokli_runtime"
    sdk = "openrouter"

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        response = self.client.chat.send(model=self.model, messages=messages, tools=tools)
        data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        choice = data["choices"][0]["message"]
        return _turn_from_message(choice, data.get("usage"))


class ZaiChatClient(ModelClient):
    provider = "zai"
    runtime = "mokli_runtime"
    sdk = "zai-sdk"

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        response = self.client.chat.completions.create(model=self.model, messages=messages, tools=tools)
        data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        choice = data["choices"][0]["message"]
        return _turn_from_message(choice, data.get("usage"))


class ZaiHostedAgentClient(ModelClient):
    """Hosted Z.ai agent. Used only when ZAI_AGENT_ID is set. Mokli does not invent its tools."""

    provider = "zai"
    runtime = "zai_agents"
    sdk = "zai-sdk"

    def __init__(self, model: str, agent_id: str, client: Any) -> None:
        self.model = model
        self.agent_id = agent_id
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        del tools
        response = self.client.agents.invoke(agent_id=self.agent_id, messages=messages, stream=False)
        data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        text = str(data.get("choices", [{}])[0].get("message", {}).get("content") or data.get("content") or "")
        return ModelTurn(text=text, deltas=[text] if text else [], input_tokens=4, output_tokens=4)


class AnthropicMessagesClient(ModelClient):
    provider = "anthropic"
    runtime = "anthropic_messages"
    sdk = "anthropic"

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        anthropic_tools = []
        for item in tools:
            function = item["function"]
            if not isinstance(function, dict):
                continue
            anthropic_tools.append(
                {
                    "name": function["name"],
                    "description": function["description"],
                    "input_schema": function["parameters"],
                }
            )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=messages,
            tools=anthropic_tools,
        )
        text = ""
        calls: list[tuple[str, dict[str, object]]] = []
        for block in response.content:
            block_type = getattr(block, "type", "")
            if block_type == "text":
                text += block.text
            elif block_type == "tool_use":
                calls.append((block.name, dict(block.input)))
        usage = getattr(response, "usage", None)
        return ModelTurn(
            text=text,
            tool_calls=calls,
            deltas=[text] if text else [],
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cached_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        )


class GeminiGenAIClient(ModelClient):
    provider = "gemini"
    runtime = "google_genai"
    sdk = "google-genai"

    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, messages: list[dict[str, object]], tools: list[dict[str, object]]) -> ModelTurn:
        prompt = "\n".join(str(item.get("content") or "") for item in messages)
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = str(getattr(response, "text", "") or "")
        meta = getattr(response, "usage_metadata", None)
        return ModelTurn(
            text=text,
            deltas=[text] if text else [],
            input_tokens=int(getattr(meta, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(meta, "candidates_token_count", 0) or 0),
            cached_tokens=int(getattr(meta, "cached_content_token_count", 0) or 0),
        )
