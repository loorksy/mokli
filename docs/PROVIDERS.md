# Providers

Versions were read from PyPI and the installed packages on 29 September 2026. Capabilities below are the ones confirmed from the installed SDK surface or the current official docs fetched for this build. Unconfirmed flags stay false.

## OpenAI

- Package: `openai-agents==0.22.3` with `openai>=3,<4` (installed 3.20.0 before other pins).
- Docs: https://openai.github.io/openai-agents-python/
- Auth: `OPENAI_API_KEY`.
- Runtime: official Agents SDK. `Agent`, `Runner`, `@function_tool`.
- Confirmed in this tree: a scripted `agents.testing.model.ScriptedModel` drives `Runner.run`, calls the Mokli `gold_snapshot` tool, and returns a final string. Tracing is disabled for that path.
- Streaming, handoffs, sessions, hosted MCP, and computer-use tools exist on the SDK. Mokli does not enable computer use or hosted web search.
- Agent SDK: yes. Sub-agents and handoffs: yes in the SDK. Mokli debate roles are separate runs with a parent id.

## Anthropic

- Package installed: `anthropic==1.9.0` (`Anthropic`, `AsyncAnthropic`).
- Official agent runtime: `claude-agent-sdk` 0.2.161, docs https://code.claude.com/docs/en/agent-sdk/overview (`ClaudeSDKClient`, `query`, in-process MCP).
- That package is not imported here. See assumptions. Runtime label: `anthropic_messages`. Agent SDK flag: false.
- Auth: `ANTHROPIC_API_KEY`.

## Gemini

- Model SDK: `google-genai==2.25.0` (`genai.Client`).
- Agent SDK: `google-adk==2.10.0` (`google.adk.Agent`, `google.adk.Runner`).
- Auth: `GEMINI_API_KEY`.
- Agent SDK: yes. A full `Runner.run_async` needs a session service and a live key, so the offline tests do not call Google.

## OpenRouter

- Package: `openrouter==1.3.4`. Client class `OpenRouter`, with `chat` and `responses`.
- Docs home: https://pypi.org/project/openrouter/
- Agent SDK: no. Mokli owns the loop. Auth: `OPENROUTER_API_KEY`.

## Kimi / Moonshot

- Official package `kimi-sdk==0.2.1` (PyPI owner MoonshotAI) exposes `Kimi`, `generate`, and `step`.
- It cannot be installed beside `openai-agents` 0.22.3. See assumptions.
- Native base URL documented by that package: `https://api.moonshot.ai/v1`.
- Auth: `KIMI_API_KEY`. Agent SDK in this process: false. Mokli owns orchestration.

## Z.ai / GLM

- Package: `zai-sdk==0.2.3`. `ZaiClient.chat` and `ZaiClient.agents.invoke(agent_id=...)`.
- Hosted agent runtime is used only when `ZAI_AGENT_ID` is set.
- Otherwise Mokli owns the loop over chat completions.
- Auth: `ZAI_API_KEY`.

## Ollama

- Package: `ollama==0.6.3` (`Client`, `AsyncClient`, `chat`, `Tool`).
- Local model runtime. No agent SDK. Mokli owns sessions, tools, and sub-agents.
- Host: `OLLAMA_HOST`. Model: `OLLAMA_MODEL`. If the model name is empty the provider is unconfigured.

## Fallback

Fallback is the configured `FALLBACK_PROVIDER`, default `mokli`. A failed vendor call must record `fallback_from` on `ProviderRun`. The deterministic runtime does not pretend to be the vendor that failed.

## Capability matrix

| Provider | agent SDK | native tools | Mokli owns loop |
| --- | --- | --- | --- |
| openai | yes | yes | no, SDK runner |
| gemini | yes (ADK) | yes | no, when ADK runs |
| anthropic | not in this process | messages API | yes |
| openrouter | no | chat/responses | yes |
| kimi | not co-installable | HTTP chat | yes |
| zai | only with agent id | yes | yes, without agent id |
| ollama | no | Tool type exists | yes |
| mokli | no | local functions | yes |
