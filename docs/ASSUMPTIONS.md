# Assumptions

Recorded where the product brief left a choice open. Each item is the option the code follows.

1. The attached reference is a dark Arabic chat app. Mokli copies its craft: near-black ground, large calm type, thin rounded cards, pills, a bottom composer, a side list, and sheet menus. It does not copy that app's name, ghost mark, upgrade marketing, or sample tools. The empty chat uses an original camel silhouette, not their logo. The display name defaults to Ahmed and stays editable. Latin names stay left-to-right inside Arabic. Gold remains the trading accent, used sparingly.

2. `docs/SPEC_AR.md` in this repository is an English translation. Rule `title_ar` values prefix the English sentence with an Arabic category name. The application chrome itself is written in Arabic and English.

3. Conflicting discretionary rules stay enabled together. Debate cites both. The risk engine does not pick a winner for them. The numbered product defaults in the build brief are enforced as policy: proposal reward/risk at least 2, execution cancelled below 1.5, cooldown default 120 minutes inside 60–240, staged exits 40/30/30, daily loss 3%, normal risk 1%, major-news risk 0.5%.

4. The source left the ATR stop multiple blank. The stop buffer is the greater of 25 points and half the current ATR, placed beyond the structural invalidation.

5. One gold point defaults to 0.01 price and one standard lot to 100 ounces. Both are settings, not constants buried in formulas.

6. Lot size rounds down to 0.01 so the loss at the stop never exceeds the budget. A one-cent step cannot hit the budget exactly on every distance.

7. Live trading is paper unless `MOKLI_LIVE=1` and the settings flag `live_confirmed` are both true. Credentials never flip the mode.

8. The default active provider is the explicit Mokli runtime. If a selected vendor runtime fails, Mokli emits `provider_fallback_started`, `provider_fallback_completed`, or `provider_fallback_failed` and stores the original provider, model, runtime, the fallback, the reason, and the time. It does not switch silently.

9. `kimi-sdk` 0.2.1 cannot be installed next to `openai-agents` 0.22.3, because its `kosong` dependency pins `openai<2.15` and `mcp<2`. Kimi calls the native Moonshot HTTP API documented by that SDK (`https://api.moonshot.ai/v1`). Mokli owns the Kimi loop. The hosted agent helpers `generate` and `step` are not imported in-process.

10. Claude Agent SDK (`claude-agent-sdk` 0.2.161) is installed and is the Anthropic agent runtime. `query()` executes the turn. `ClaudeSDKClient.interrupt()` is the cancellation path because `query()` cannot interrupt. A live turn starts the Claude Code CLI; offline tests inject the SDK `Transport` and do not call Anthropic. The messages API (`anthropic` 1.9.0) is only the fallback after the Agent SDK fails. Computer use, web search, and shell/file tools are disallowed. Workspace `cwd` is applied by the CLI transport, not by a custom transport.

11. Z.ai `agents.invoke` is the hosted agent API and needs `ZAI_AGENT_ID`. Without that id, chat completions run inside the Mokli loop.

12. Google ADK 2.10.0 is the Gemini agent runtime. `google-genai` 2.25.0 remains the model client.

13. OANDA is the market source when a practice token exists. Otherwise the book is `SIMULATOR` or `UNAVAILABLE`. Missing intermarket values stay missing.

14. The DXY figure is the published basket formula and is labeled calculated.

15. A holiday calendar beyond New Year, Thanksgiving, and Labor Day is a caller flag. The engine does not invent a full exchange calendar.

16. MetaApi and mt5linux are adapter slots. `mt5linux` is pinned to 0.2.4 in the `mt5` extra. The 1.x line is not used. The default broker is the paper simulator.

17. Bind address defaults to `127.0.0.1`. Docker publishes `127.0.0.1:8787` and the process inside the container listens on `0.0.0.0` so the published port can reach it.

18. Embeddings are not required. Similar setups are retrieved by tag overlap.

19. `scripts/build_apk.sh` looks for a command-line Android SDK in `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `/opt/android-sdk`, the home Android directory, and the repo `.android-sdk`. If none of those exist it installs the command-line tools and platform 35, then runs Gradle. The generated `android/` tree and the APK stay gitignored.

20. Voice is a spoken turn on the paper app. The microphone records audio, `POST /api/voice/turn` transcribes it, Mokli answers, and the browser plays the reply wav. The UI shows listening, then speaking, then idle. A finished reply returns to idle and does not keep listening. There is no vendor realtime key and none is hardcoded. A recording that carries a `mokl` text chunk is transcribed from that chunk. Any other non-silent payload uses the local phrase `اقرأ الشريط` because no speech model is installed. Reply audio uses `espeak-ng` when that binary is on the machine, otherwise a PCM wav. Barging in cancels speech and opens a new listen. A late "finished speaking" callback while already listening is a no-op.

21. Daily and weekly reports are snapshots of the current paper book. They are not a reconstructed historical ledger.

22. OANDA, MetaApi, and Telegram stay disconnected when their credentials are absent. Credentials without `MOKLI_LIVE=1` and the settings confirmation do not enable live orders. This build refuses the live approval path even when both flags are set.
