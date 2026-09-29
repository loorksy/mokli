# Providers

Status labels are only these five:

- IMPLEMENTED — Native Agent SDK
- IMPLEMENTED — Native Model API
- IMPLEMENTED — Mokli Agent Runtime
- PLANNED
- UNAVAILABLE

Versions were read from the installed environment on 29 September 2026. A flag is true only when this tree executes that path. Official docs were read for the Claude Agent SDK before it was wired.

## OpenAI

- Status: IMPLEMENTED — Native Agent SDK
- Package: `openai-agents==0.22.3` with `openai` 3.x
- Docs: https://openai.github.io/openai-agents-python/
- Runtime: `openai_agents_sdk`. `Agent`, `Runner.run`, `Runner.run_streamed`, `@function_tool`, `handoff` via `Agent` handoffs, `SQLiteSession`.
- Native model fallback: IMPLEMENTED — Native Model API through `openai.OpenAI.chat.completions` when `OPENAI_API_KEY` is set and the Agents SDK raises.
- Capabilities: streaming, native_tools, structured_output, agent_sdk, subagents, handoffs, sessions, reasoning, mcp, prompt_caching.
- Not enabled: computer_use, web_search, background_tasks.
- Tests: scripted `ScriptedModel` through `Runner` calls `get_gold_price` via ToolBridge, records usage, and completes a handoff to a second `Agent`. No API key.

## Anthropic

- Status: IMPLEMENTED — Native Agent SDK
- Package: `claude-agent-sdk==0.2.161`
- Docs: https://code.claude.com/docs/en/agent-sdk/python
- Runtime: `query()` with `ClaudeAgentOptions`, in-process MCP from `create_sdk_mcp_server` / `@tool`, `AgentDefinition` for a native sub-agent, `resume` for the session id, `include_partial_messages` for stream events.
- Cancellation: `ClaudeSDKClient.interrupt()`. `query()` cannot interrupt. That is an SDK limitation, not a Mokli one.
- Live turns start the Claude Code CLI. `ClaudeAgentOptions.cwd` points at the Mokli workspace for that CLI transport. A custom `Transport` does not receive CLI flags or store-backed session resume. Offline tests use `Transport` and do not call Anthropic or start the CLI.
- Fallback after the Agent SDK fails: IMPLEMENTED — Native Model API via `anthropic==1.9.0` `messages.create`, only when `ANTHROPIC_API_KEY` is set.
- Capabilities: streaming, native_tools, structured_output, agent_sdk, subagents, sessions, reasoning, mcp, prompt_caching.
- Not enabled, so the flags stay false: handoffs (Claude uses sub-agents, not OpenAI handoffs), computer_use, web_search, background_tasks. Bash, Read, Write, Edit, WebSearch, WebFetch, and Agent are disallowed on the options object.
- Native sub-agent execution inside the CLI is not reproduced offline. The test proves `AgentDefinition` is placed on the SDK initialize control request and that the in-process MCP tool runs.

## Gemini

- Status: IMPLEMENTED — Native Agent SDK
- Packages: `google-adk==2.10.0`, `google-genai==2.25.0`
- Docs: https://google.github.io/adk-docs/
- Runtime: `google.adk.Agent`, `InMemoryRunner`, `InMemorySessionService`, `FunctionTool`.
- Fallback after ADK fails: IMPLEMENTED — Native Model API via `google.genai.Client.models.generate_content` when `GEMINI_API_KEY` is set.
- Capabilities: streaming, native_tools, structured_output, agent_sdk, subagents (`Agent.sub_agents`), sessions, reasoning, mcp (ADK has an MCP tool type; Mokli tools still enter through ToolBridge).
- Not enabled: handoffs, computer_use, web_search, background_tasks, prompt_caching on the ADK path.
- Tests: a `BaseLlm` script feeds a function call and a final text. No Google call.
- Limitation: ADK token usage is not returned by the scripted model. The persisted estimate uses the scripted turn counts.

## OpenRouter

- Status: IMPLEMENTED — Mokli Agent Runtime
- Package: `openrouter==1.3.4` (`OpenRouter.chat.send`)
- Docs: https://openrouter.ai/docs
- Mokli owns the agent loop, sessions, tools, sub-agents, and fallback. OpenRouter is a model API. It is not an agent SDK.
- Capabilities exposed in the UI: streaming (Mokli deltas from the completed native response), native_tools, sessions, mcp. `agent_sdk`, `subagents`, and `handoffs` are false.
- Limitation: this build reads the completed chat payload. It does not consume OpenRouter SSE.

## Kimi / Moonshot

- Status: IMPLEMENTED — Mokli Agent Runtime
- Native API: `POST {KIMI_BASE_URL}/chat/completions`, default `https://api.moonshot.ai/v1`, the base URL documented by Moonshot's Python SDK.
- Package `kimi-sdk==0.2.1`: UNAVAILABLE in this process. It cannot be installed beside `openai-agents` 0.22.3 (`kosong` pins `openai<2.15` and `mcp<2`). `generate` and `step` are not imported.
- Mokli owns the loop. `agent_sdk` is false.
- Tests: `httpx.MockTransport` against the chat-completions body. No Moonshot call.

## Z.ai / GLM

- Status: IMPLEMENTED — Mokli Agent Runtime
- Package: `zai-sdk==0.2.3`
- Default runtime: `ZaiClient.chat.completions.create` inside the Mokli loop.
- When `ZAI_AGENT_ID` is set, the catalog switches to `ZaiClient.agents.invoke` and the status shown for that row is IMPLEMENTED — Native Model API. That hosted invoke does not give Mokli native tools, sub-agents, or a vendor event stream. Tool use stays on the Mokli loop unless the hosted agent is selected, in which case Mokli does not pretend the hosted agent shares ToolBridge.
- `agent_sdk` stays false.

## Ollama

- Status: IMPLEMENTED — Mokli Agent Runtime
- Package: `ollama==0.6.3` (`Client.chat`)
- No Ollama agent SDK is used. Mokli owns sessions, tools, and sub-agents.
- Empty `OLLAMA_MODEL` means the provider is not configured. The UI does not mark it configured.
- Limitation: `Client.chat` is called with `stream=False`. Mokli still emits `agent_message_delta` from the completed text.

## Mokli

- Status: IMPLEMENTED — Mokli Agent Runtime
- No vendor SDK. The deterministic client reads the snapshot through `get_gold_price` and does not invent a price.
- This is the default provider and the last fallback.

## ToolBridge

`get_gold_price` has one handler. `ToolBridge` builds the OpenAI Agents function tool, the Claude in-process MCP tool, the ADK `FunctionTool`, and the JSON schema used by OpenRouter, Kimi, Z.ai, and Ollama. Broker names (`place_order`, `broker_market`, `broker_close`, `broker_modify`, `broker_kill`) are refused before any SDK sees them.

## MCP

IMPLEMENTED for Mokli's registry: server registration, allowlist, discovery, per-agent permission, timeout, audit, side-effect label, and approval refusal. Broker tools cannot be registered. Claude's native in-process MCP is used on the Anthropic path. Other providers receive the same Mokli tool through ToolBridge rather than a second implementation.

## Sub-agents

`spawn_subagent` copies context, keeps `parent_agent_id` and `child_agent_id`, records provider, model, runtime, tool allowlist, token budget, cancellation, and an audit line. OpenAI uses SDK handoffs. Claude sends `AgentDefinition`. Gemini can attach `sub_agents`. OpenRouter, Kimi, Z.ai, and Ollama use the Mokli-managed child. Those providers do not advertise native sub-agents.

## Fallback

Order: native agent SDK, then native model API when that client exists, then the configured `FALLBACK_PROVIDER` (default `mokli`), then `SafeFailure`. Each switch emits `provider_fallback_started` and then `provider_fallback_completed` or `provider_fallback_failed`. The `ProviderRun` row stores original provider, model, and runtime, plus fallback provider, model, runtime, reason, and timestamp.

## Observability

`ProviderRun` stores provider, model, runtime, SDK, agent id, parent agent id, session id, latency, input, output, and cached tokens, estimated cost, tool-call count, sub-agent count, retries, failures, and fallbacks. Chat writes that row. Estimated cost is a local rate table, not an invoice.

## Test matrix

| Provider | Runtime | Streaming | Tools | Subagents | Tested |
| --- | --- | --- | --- | --- | --- |
| OpenAI | OpenAI Agents SDK | ✓ | ✓ | ✓ | ✓ |
| Anthropic | Claude Agent SDK | ✓ | ✓ | ✓ definition on the SDK initialize request; CLI execution needs Claude Code | ✓ |
| Gemini | Google ADK | ✓ | ✓ | ✓ `sub_agents` on `Agent`; offline run covers the parent tool loop | ✓ |
| OpenRouter | Mokli Runtime | ✓ Mokli deltas from the completed response | ✓ | Mokli | ✓ |
| Kimi | Mokli Runtime over Moonshot HTTP | ✓ Mokli deltas from the completed response | ✓ | Mokli | ✓ |
| Z.ai | Mokli Runtime over `zai-sdk` chat; hosted `agents.invoke` only with `ZAI_AGENT_ID` | ✓ Mokli deltas from the completed response | ✓ on the chat loop; N/A on hosted invoke | Mokli | ✓ |
| Ollama | Mokli Runtime over `ollama.Client` | ✓ Mokli deltas from the completed response | ✓ | Mokli | ✓ |

N/A is not used to hide a missing feature. Hosted Z.ai invoke does not take Mokli tools. `kimi-sdk` itself is UNAVAILABLE.
