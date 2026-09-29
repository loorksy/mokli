GOLD TRADING AGENT (XAUUSD) — CAPABILITY DOCUMENT, FIELD RULES, NEWS RULES, AND NEWS-CANDLE DETECTION
English translation of the source documents

================================================================================
PART A — FINAL CAPABILITY DOCUMENT
Gold Trading Agent (XAUUSD Core Engine)
================================================================================

1. TECHNICAL ANALYSIS AND PRICE ACTION
1.1 Detect supply and demand zones and Fair Value Gaps (FVG).
1.2 Analyze trend and its alignment across multiple timeframes (M15 / H1 / H4 / D1).
1.3 Detect false breaks and liquidity traps (Liquidity Sweeps and Turtle Soups).
1.4 Identify market structure and shifts in character (CHoCH / BOS), plus structural swing highs and swing lows.
1.5 Draw Fibonacci levels and dynamic levels automatically.
1.6 Measure candle momentum and volatility using tick volume and ATR.
1.7 Detect trend-reversing price divergence against RSI / MACD.

2. FUNDAMENTAL AND MACRO ANALYSIS (MACRO AND SENTIMENT RADAR)
2.1 Monitor the live economic calendar (interest rates, CPI inflation, NFP employment).
2.2 Track the US Dollar Index (DXY) and link its intraday and cumulative movement to gold’s path.
2.3 Analyze the tone of data and Federal Reserve remarks from open news sources.
2.4 Radar for sudden geopolitical headlines that increase safe-haven demand.

3. RISK MANAGEMENT AND CAPITAL RULES (RISK GUARDRAILS)
3.1 Calculate position size (lot size) automatically from the defined risk percentage and the stop-loss distance.
3.2 Daily drawdown breaker that freezes activity the moment the loss limit is hit.
3.3 Spread-width filter that blocks execution during thin liquidity or market opens.
3.4 Mandatory cooldown lock after consecutive losing trades, to prevent revenge trading.
3.5 Cap the maximum number of contracts and simultaneous open gold positions.
3.6 Reject any recommendation that does not meet a minimum reward-to-risk ratio (1:2 R:R or better).

4. EXECUTION AND ACTIVE TRADE MANAGEMENT
4.1 Direct, secure order execution through MetaTrader 5 (market and pending orders).
4.2 Dynamic trailing stop behind swing highs and lows, or by ATR.
4.3 Move the stop loss to entry automatically (auto breakeven) after the first target is hit.
4.4 Partial take-profit management across successive targets, to lock in profit.
4.5 News shield: alert or protect open trades minutes before major releases.
4.6 Generate early-exit recommendations when candle momentum weakens suddenly.

5. MEMORY AND SELF-REVIEW
5.1 Search for historically similar gold price-behavior patterns and match them before a decision.
5.2 Fast backtest to check how the pattern behaved on recent data.
5.3 Post-trade self-review after every close, scoring plan compliance and exit quality.
5.4 Log price mistakes and surprises in a lessons-learned record so they are not repeated.
5.5 Internal pre-check (technical view crossed with risk constraints) before a trade is approved.

6. ALERTS AND OPERATOR INTERFACE
6.1 Instant alert with an annotated chart snapshot showing entry, stop, targets, and the reason.
6.2 Human-in-the-loop confirmation via approve/cancel buttons before execution.
6.3 Detailed morning brief of key levels and pivot points before the London and New York sessions.
6.4 Periodic performance reports: realized results, net profit and loss, and win rate.
6.5 Immediate natural-language replies when the operator asks about the current gold situation.
6.6 Immediate notice if the market connection drops or the price feed stops.
6.7 Broadcast alerts and reports to Telegram and the platform at the same time.

7. SECURITY AND OPERATIONAL RESILIENCE
7.1 Master kill switch that closes positions and cancels pending orders immediately.
7.2 Encrypt and secure connection keys and trading-account data locally.
7.3 Persist trade and order state locally so it is restored automatically after a restart.
7.4 Bad-tick filter that protects the account from platform price errors.
7.5 Detect positions the operator opened manually and manage them if the operator wants that.

8. MULTI-TASKING AND SCENARIO MANAGEMENT
8.1 Keep scanning for new technical opportunities while managing open trades, without conflict.
8.2 Propose two conditional scenarios (buy the breakout / sell the rejection) and activate whichever price behavior confirms first.
8.3 Separate intraday scalps from swing trades on the same account without mixing their accounting.
8.4 Accept immediate natural-language instructions and apply them directly to active trades.
8.5 Operator panel to enable or disable any strategic skill with one control.

9. PERSONALITY AND BEHAVIORAL ALIGNMENT
9.1 Adaptive communication modes (strict when risk rules are about to be broken, lightly ironic about overconfidence, supportive after a loss).
9.2 Direct, objective technical admission of error when a stop is hit, without invented excuses.
9.3 Complete silence and no random trade ideas during narrow, untradeable ranges.
9.4 A short reflective question at the end of the day to score emotional calm and discipline in the trading journal.

--------------------------------------------------------------------------------
DETAILED CAPABILITY SPECIFICATION
--------------------------------------------------------------------------------

1. TECHNICAL ANALYSIS AND PRICE ACTION

1.1 Supply and demand zones and Fair Value Gaps (FVG)
An algorithm scans three-candle sequences to find price-imbalance gaps created by strong liquidity flows. It draws those zones precisely and marks whether the gap is fully or partially filled, so they can be used as primary reaction zones or as targets for scaling out contracts.

1.2 Multi-timeframe analysis
A layered reading system. It extracts the higher-timeframe bias and structural zones from the daily (D1) and four-hour (H4) charts, then drops to the hourly (H1) and 15-minute (M15) charts to time the entry. The purpose is to stop intraday trades that fight the dominant higher-timeframe path.

1.3 False breaks and liquidity traps (sweeps and fakeouts)
It watches price at historical highs and lows. If price breaks the level, runs the stops, then closes back inside the range with a long rejection wick, the agent treats that as a liquidity trap (Turtle Soup) and prepares a reversal entry with the market maker.

1.4 Market structure (BOS and CHoCH)
An engine that marks true swing highs and swing lows. It reads trend continuation as a break of highs in an uptrend or lows in a downtrend (Break of Structure, BOS). It reads an early reversal as soon as the last low that created a new high is broken (Change of Character, CHoCH).

1.5 Automatic Fibonacci and dynamic levels
It identifies the latest impulse leg and calculates institutional retracement levels automatically (discount and premium pricing, and the 0.618–0.786 “golden” zone), and it computes intraday support and resistance without manual drawing.

1.6 Approximate volume (tick volume) and ATR
It uses the tick volume available in MT5 to confirm that a break has real momentum and to ignore hollow candles with no liquidity. Combined with Average True Range (ATR), it estimates gold’s normal swing distance and sets logical stop distances.

1.7 Divergence against RSI / MACD
It continuously compares gold’s swing highs and lows with momentum indicators. Positive or negative divergence is treated as an early warning that buyers or sellers are weakening, before the reversal shows up in the candles.

2. FUNDAMENTAL AND MACRO ANALYSIS (MACRO RADAR)

2.1 Live economic calendar (rates, inflation, employment)
Connected to an open economic calendar for releases that move gold directly (Federal Reserve rate decision, CPI, NFP). It measures the gap between the forecast and the actual print to size the price shock.

2.2 US Dollar Index (DXY) linked to gold
It tracks DXY in real time. Because gold is priced in dollars and the two have a strong inverse relationship, a confirmed dollar break or bounce is a required confluence for gold buy or sell decisions, so the agent does not buy gold into a rising dollar.

2.3 Tone of central-bank remarks from available news
It processes news summaries of Federal Reserve official speeches with sentiment analysis and classifies the tone immediately (hawkish pressure tends to push gold down; dovish tone tends to support gold higher).

2.4 Geopolitical radar for safe-haven demand
It scans open breaking headlines for keywords tied to geopolitical crises and wars, so buy setups are prioritized and gold is not sold during global fear waves.

3. RISK MANAGEMENT AND CAPITAL RULES (RISK GUARDRAILS)

3.1 Automatic lot size from risk percent and stop distance
A formula sizes the contract as soon as entry and stop are defined, so the potential loss equals a fixed share of account equity (for example 1% or 2%), with no manual arithmetic.

3.2 Daily drawdown breaker
A software safety valve tracks the day’s total loss. Once losses reach the preset limit (for example 3% of equity), the system closes every open trade and blocks trading until the next day.

3.3 Spread guard
It checks the Bid–Ask spread in MT5 before sending an order. If the spread is abnormal (market close or violent news), execution is cancelled immediately so profit is not eaten at the fill.

3.4 Cooldown lock after consecutive losses
A forced pause (for example two to four hours) after two consecutive losses, to cut off emotional decisions and revenge trading.

3.5 Maximum number of positions open at once
A hard cap on active gold positions (for example two). This limits floating exposure and keeps margin from being scattered during sudden moves.

3.6 Reject setups below a minimum R:R (1:2 floor)
A mathematical filter checks target versus stop before a trade is accepted. If expected reward is less than twice the risk, the trade is dropped, so the account can still grow with a moderate win rate.

4. EXECUTION AND TRADE MANAGEMENT

4.1 Direct MetaTrader 5 execution
A direct connection to the platform to send, modify, and cancel market orders and pending orders (limit / stop) with low latency and no extra intermediaries.

4.2 Automatic trailing stop
It follows rising or falling price and walks the stop behind intraday swing highs and lows, or by an ATR multiple, so a growing share of profit is protected while the move continues.

4.3 Move the stop to entry (auto breakeven)
It watches progress. Once gold hits the programmed first target, the stop is modified to the entry price, so the trade has no remaining financial risk.

4.4 Partial close at successive targets
The contract is split so defined fractions close automatically (for example 50% at target one and 25% at target two), leaving the rest to capture the rest of the trend.

4.5 News shield
It alerts the operator, or protects open positions, ten minutes before high-impact releases, to avoid slippage and sudden spread widening.

4.6 Early-exit recommendation when momentum fades
It watches candles while the trade is open. If a strong reversal appears, or price clearly loses momentum before target or stop, the agent recommends or executes an immediate exit to keep profit or cut the loss.

5. MEMORY AND SELF-REVIEW

5.1 Search for similar historical gold cases before the decision
It compares the current technical structure with stored historical gold moves under similar volatility and liquidity-sweep conditions, and estimates how often that pattern worked before the execute button is pressed.

5.2 Fast backtest on recent gold data
A quick simulation on the last 100 to 200 gold candles, to check that the strategy still fits the current market regime and is not a setup built for a different environment.

5.3 Self-review after every closed trade
An automatic technical log is written when a contract closes. It records the gap between expectation and result, and whether the exit followed the plan or an undisciplined action.

5.4 Log of repeated mistakes (lessons record)
Cases that caused losses (early entry before the candle close, trading a dead market, and similar) are stored as lessons and recalled as pre-checks so the same error is blocked later.

5.5 Simple internal review (technical angle plus risk angle)
A two-engine check before an order is sent. The technical engine proposes the idea. The risk engine checks lot size, spread, and exposure. The trade passes only if both approve.

6. ALERTS AND OPERATOR INTERFACE

6.1 Instant alert with a chart image (entry / stop / targets)
An automatic chart image showing entry zones, the stop line, targets, and the technical reason, sent immediately so the operator sees the idea visually and numerically.

6.2 Human confirmation before execution (human-in-the-loop)
The recommendation is sent with interactive buttons (“Approve” / “Ignore”). If the operator wants full control, the system waits for a manual approval.

6.3 Morning brief of key gold levels before London / New York
A focused morning briefing of liquidity levels, prior highs and lows, and gold’s main pivot points before the major sessions, so the day has a plan before it starts.

6.4 Daily / weekly profit-and-loss and win-rate report
Periodic numeric reports: net return, win rate, realized risk/reward, and the maximum drawdown over the period.

6.5 Interactive answers about gold’s state
The operator can ask in natural language (for example, “What is gold’s current trend?”) and receive a short, data-backed answer immediately.

6.6 Alert when the price feed drops
A continuous MT5 server heartbeat. If ticks are late or the connection drops beyond a set number of seconds, the operator gets an immediate alarm.

6.7 Broadcast the same recommendation to more than one channel (Telegram and the platform)
Parallel delivery publishes updates and recommendations at the same time to follower channels, the admin panel, and the platform, with no lag between them.

7. SECURITY AND RESILIENCE

7.1 [The source left this item without a detailed paragraph. The capability summary defines it as: Master Kill Switch — close all positions and cancel all pending orders immediately.]

7.2 Encrypted storage of account keys
Account passwords and connection details are stored in encrypted, locally protected environment files (.env) so sensitive trading data is not exposed.

7.3 Local trade-state persistence for recovery after any outage
Ticket IDs and technical state are written continuously to a local database (SQLite), so the agent can resume management of active positions immediately after a restart.

7.4 Bad-tick filter
Incoming price is compared with the last traded price. An implausible jump caused by a broker software fault is ignored, so the account does not open bad orders.

7.5 Adopt and manage the operator’s manual trades
Orders the operator opens manually from a phone or computer are detected. The agent asks whether it should take over management, protection, and gradual profit locking.

8. MULTI-TASKING AND SCENARIOS

8.1 Continuous gold scan while a position is open
Asynchronous processing lets the agent trail and protect live contracts second by second while it also scans the gold chart for new confluence signals, without conflict.

8.2 Two alternative plans (buy the break / sell the failure), and activate the confirmed one
Two conditional technical scenarios are staged. If price proves the breakout, the buy is armed and the sell idea is cancelled. If price shows a false break, the sell is armed and the buy is cancelled immediately.

8.3 Separate scalps from swings at the same time without overlap
A multi-day swing on the daily chart can be managed while scalp trades are opened and closed on minute charts, using independent magic numbers.

8.4 Natural-language steering commands
Direct text orders from the operator are applied in code immediately (for example: “Move the stop on every gold trade to entry if price touches 2500”).

8.5 Enable or disable specific skills from a control panel
Feature toggles let the operator turn any capability on or off (for example disable the news shield, or enable early exit) with one control and without editing code.

9. PERSONALITY AND BEHAVIORAL ALIGNMENT

9.1 Adaptive behavioral modes (strict, ironic, supportive, decisive)
Tone follows the situation. It becomes firm and military if the operator tries to break risk rules or remove a stop. It is lightly ironic after a fast winning streak, to check arrogance. It is calm and supportive after losses, to steady the operator.

9.2 Explicit admission of error after a losing trade
An honest, immediate technical review when a stop is hit, with no fictional excuses. It states how market makers trapped the pattern and what was lost in numbers.

9.3 Total silence in an untradeable range
No signals and no notifications during dead chop, so compulsive trading is avoided and the operator waits for real liquidity.

9.4 A simple reflective question at the end of the day
A short, specific question after each trading day (for example: “Did you follow your plan today without hesitation or rushing?”) so psychological state is recorded in the trading journal.


================================================================================
PART B — TECHNICAL AND FIELD RULES FOR THE GOLD TRADING AGENT (XAUUSD)
200 OPERATIONAL RULES
================================================================================

SECTION 1 — ENTRY-ZONE FLEXIBILITY AND INTRADAY TIMING (RULES 1–25)

1. Move past classic support and resistance. The agent does not have to wait for a touch of a horizontal line. In strong trends, gold often reacts from dynamic trendlines or from liquidity gaps in the middle of the distance.
2. Immediate entry without waiting. If buy or sell conditions are complete and liquidity has already been swept, send a market entry. Do not wait for extra downside or upside that misses the move.
3. Distance-versus-target contradiction. If entry requires a 100-point pullback to a level, while the total target is only 100 points, the trade is logically inconsistent. Priority goes to entering with current momentum.
4. Anticipatory entry before the close. On explosive gold momentum candles, waiting for the close is not always required. Waiting can consume 60% of the expected range.
5. Incomplete retracement (front-running). Institutions often place orders several points before support and resistance. Open an entry window that starts 15 to 30 gold points before the level.
6. Enter the liquidity gap (FVG), not the high. In an uptrend, gold often turns from the first fair value gap above the broken high, rather than falling back to retest that high.
7. Entry with a counter engulfing candle. If prior candles drifted lower and a strong bullish candle engulfs two of them, that is an immediate buy. A support touch is not required.
8. Direct breakout entry during liquidity hours. At the London or New York open, a sharp break of the Asian range is treated as a momentum entry. Do not wait for a pullback.
9. Entry at equilibrium. In large impulse waves, the 50% level of the wave is a preferred entry even if it does not match a prior high or low.
10. Two timeframes agreeing on timing. If an M15 reversal pattern forms while H1 is mid-candle in a directional candle, priority is the intraday entry in the H1 direction.
11. Fan-line entry. When gold’s decline or rally accelerates, build the entry on the steeper trendline, not the slow primary trendline.
12. Cancel a conditional entry when time stalls. If price has not reached the conditional entry zone within 4 hours, cancel the idea. A break of the zone is then more likely than a bounce.
13. Entry from the news-candle low. The candle produced by an economic release becomes support by itself. Enter on a touch of that candle’s wick, not by waiting for the day’s low.
14. Entry on price absorption. Repeated lower wicks inside a tight price area are an immediate buy signal. Drawn technical lines are not required.
15. “Break the minor trendline” entry. During a correction, a break of the minor descending trendline is the buy signal in the direction of the higher uptrend.
16. Do not wait for a pullback in a steep trend. When gold’s rally angle exceeds 60 degrees, waiting for a deep pullback misses the entire rally.
17. Entry on round-number touches. Levels such as 2400 or 2450 are automatic psychological entry zones if a reversal candle prints there, even without prior support.
18. Entry after a bearish pattern fails. If a double top fails to push price down and price breaks the neckline upward, activate the opposite buy immediately.
19. Entry conditioned on candle sequence. Three rising candles with expanding volume (Three White Soldiers) after chop are a sufficient entry reason. Indicators are not required.
20. Reclaim entry. A drop below support followed by a fast close back above it in the same candle is an immediate buy.
21. Hourly-close entry. Enter at minute 59 of the hour if that candle confirms a break of an important level, to avoid slippage in the first minute of the new hour.
22. Entry along the fast moving average. In strong trends, a gold reaction from the 20 EMA is enough. Prior lows are not required.
23. Counter-entry after the daily range is exhausted. If gold has already moved 150% of its average daily range (ADR), a counter-entry is justified on the first intraday reversal candle.
24. Split-order entry. Split the entry into two clips (a market order and a pending order 20 points away) instead of missing the move or putting full size on one price.
25. Buy the broken prior high that has flipped to support. The classic role-reversal rule is used only if the reaction is fast and the rejection candle is clear.

SECTION 2 — STOP-LOSS REALITY AND PROTECTION ZONES (RULES 26–55)

26. The stop is not the support line. Placing the stop directly under classic support or a classic low is a serious error. That zone is where market makers prefer to run liquidity.
27. A hit stop can become the next entry. If the stop is tagged by a wick and price quickly closes back inside the range, the old stop level is itself the better new entry.
28. Mandatory buffer zone. Always add a protection margin under lows of at least 25 to 40 gold points, to absorb random noise.
29. ATR-based stop. Stop distance must be a multiple of true volatility (the source left the example multiple blank), not a fixed point count.
30. Stop beyond the explosive candle. On sells, place the stop above the wick of the candle that caused the break, not above a distant historical high.
31. Structural stop, not a point stop. A fixed stop (for example “always 30 points”) is abolished. The stop sits at the price that invalidates the technical idea completely.
32. Do not park the stop on round numbers. Market makers target clean numbers. Place the stop on awkward fractions (for example 2447.80 instead of 2450.00).
33. Stop on a dynamic trendline. On some trades, a candle close through the trendline is the stop criterion, not a fixed numeric price.
34. Tighten the stop when a confirmation candle prints. Once price launches and prints a momentum candle in the trade direction, pull the stop immediately behind that candle’s low to cut risk.
35. Moving the stop backward is forbidden. Under no circumstance may the stop be widened after entry to accept a larger loss than planned.
36. Time stop. If gold opens a trade and chops in a dead range for more than 3 hours without launching, close the contract or tighten the stop in case of a reversal spike.
37. Stop behind a liquidity pool. Place the stop a safe distance behind equal lows. Those lows attract candle wicks.
38. Breakeven rule. Move the stop to entry only after price has traveled a distance equal to the stop itself and a new low has formed on M15. (The source had an empty parenthesis after “the stop itself.”)
39. Protect profit near the high. If the trade has reached 70% of the target, place a profit-protection stop at 50% of the move so the market cannot turn a winner into a loser.
40. Order-block buffer. Place the stop 15 points beyond the end of the institutional order block, not exactly on it.
41. Separate the sell stop from the spread. On sells, add the spread width at the time of exit to the stop distance, so a phantom spread does not knock the trade out.
42. Dynamic chandelier exit. Use the highest high of the last 10 candles minus an ATR multiple as a trailing stop that follows price.
43. Stop behind the Asian high. If gold is sold after an Asian-session liquidity sweep, place the stop 10 points above the highest wick of the sweep candle.
44. Do not place the stop inside open gaps. Never put a stop in the middle of an open FVG. Price will return to fill it.
45. Intraday momentum-break stop. Exit if two consecutive candles close against the trade on M5 with rising momentum, even before the original stop is hit.
46. Do not move to breakeven too early. Moving the stop to entry before a minor swing high is cleared gets the trade tagged by noise before the move to target.
47. Portfolio-percent stop. The distance from entry to stop must equal exactly 1% or 2% of equity in code, by adjusting lot size.
48. Close-based reference stop. In some cases the stop is programmed as “an hourly candle close below the level,” not a fast wick touch.
49. Protect trades into news. Five minutes before a hot release, the stop must sit in an area clear of liquidity gaps, to reduce slippage.
50. Split stops on split contracts. When entering with two contracts, the first stop can be tight and the second can sit behind the larger structural low, to spread risk.
51. Stop on a channel midline break. Inside a price channel, a break of the equidistant median is an early stop, before the channel extreme.
52. Overnight safety stop. Before the rollover, widen the stop by an extra 20 points to absorb the temporary spread expansion.
53. Stop behind an inverted hammer (shooting star). On a sell, place the stop 10 points above the highest point of the shooting-star wick.
54. Stop based on supply/demand balance. On a buy, place the stop under the demand zone that absorbed the last full downswing.
55. Protective exit on an opposite pattern. Cancel the trade and hit the stop manually if a clear head-and-shoulders reversal forms on H1.

SECTION 3 — THE REALITY AND PHILOSOPHY OF THE RETEST (RULES 56–80)

56. A retest is not mandatory. In genuine gold explosions, price runs away with no retest of the broken level. Waiting misses the trade.
57. A retest can be evidence of reversal. If price drifts slowly and hesitantly back to the broken level and bearish candles start to dominate, this is often not a retest. It is a failed break and a real reversal.
58. Deep retest. Gold often pushes back through a broken resistance to retest deeper demand underneath before rallying.
59. Speed of the test candle. A successful retest candle must be fast and rejected with a long wick. Full-bodied candles that settle on the level mean the breakout failed.
60. Retest the trendline, not the horizontal line. Price may ignore the horizontal level and retest a previously broken sloping trendline, then launch from it.
61. Fake retest used to grab liquidity. A return to the broken zone may exist only to trigger traders’ pending buy orders, then dump hard and trap them.
62. A failed retest is a sell. When price fails to bounce from the retest level and trades back through it, flip immediately to a sell with the new direction.
63. Retest on a smaller timeframe. What looks like a straight breakout on H1 often contains a complete, clean retest on M1 or M5.
64. Volume effect on the test. A retest on weak tick volume is the safer and more credible continuation.
65. Fibonacci retest. Gold prefers to retest the 61.8% Fibonacci of the broken wave rather than the zero point of the break.
66. Right-shoulder test. In head-and-shoulders patterns, price may never retest the neckline. It may simply fall after the right shoulder forms.
67. Repeated retests weaken the level. Three returns to the same level do not prove strength. They show buy orders being consumed and a break getting closer.
68. Time-conditioned retest. If the breakout candle took one minute and the retest candle took 30 minutes of hesitant decline, that is a healthy pullback.
69. Retest zones, not lines. Treat retest levels as a price band of 15 to 30 points, not a single number.
70. Weekly opening-gap retest. Gaps left at the Monday open are later retest targets that tend to be filled during the week.
71. Runaway breakout with no test. If the breakout is accompanied by a strong opposite move in DXY, gold will fall with no retest of the highs.
72. Confirm the retest with reversal candles. Do not enter a retest just because price touched the level. Require an M15 pin bar or engulfing candle that confirms rejection.
73. Retest of a broken Asian low. When gold breaks the Asian-session low at the London open, the maximum bounce is a tag of that same low before the sharp decline.
74. Mid-air retest. Price may turn 20 points before the broken support and only test the nearest moving average.
75. Retest of parallel trendlines. After a descending channel breaks, price often retests the channel’s outer ceiling as new support.
76. Psychological-level retest. Holding above a level such as 2400.00 after clearing it is stronger confirmation than retesting a random high.
77. Retest after a storm news release. News shocks leave violent break levels. Those levels are often retested calmly after the session ends.
78. All-time-high retest. When gold prints a new all-time high, the retest may be a long sideways range rather than a sharp drop.
79. Failed test in exhaustion zones. If RSI is deeply oversold on H4, any retest of a broken resistance will turn into a buy explosion.
80. Cancel the retest idea when the range is too wide. If the retest decline exceeds 78.6% of the breakout leg, cancel the scenario. The break was fully false.

SECTION 4 — TRENDLINE AND CHANNEL SECRETS (RULES 81–105)

81. Multiple trendlines on the same chart. An inner steep trendline and an outer primary trendline can both be drawn on the same candles. Entry starts from the inner line.
82. A trendline is a zone, not a hairline. Draw it as a price band that contains both wicks and bodies, so gold’s momentary wick pierces are absorbed.
83. Bounce from the trendline without touching support. Gold often ignores horizontal levels completely and reverses on a touch of a rising trendline.
84. Third-touch rule. The third touch of a trendline is the strongest and the highest-probability quick profit. The fourth and fifth touches carry a high break risk.
85. A trendline break is not automatically a reversal. A break of gold’s rising trendline often produces a sideways accumulation path, not necessarily a sharp decline.
86. Adjusted trendlines. If a wick pierces the trendline and the candle closes back above it, redraw the line to include that wick as the new slope.
87. Parallel twin trendline. A line parallel to the trendline across the opposite swings creates a channel. A tag of the channel ceiling is a mandatory profit target.
88. Accelerating departure from a flat trendline. Price racing away from the trendline at a right angle signals a nearby explosion that ends with a collapse back toward the line.
89. Minor trendline break as confirmation. Do not buy a horizontal support touch until the small descending trendline breaks on the 5-minute chart.
90. The market-maker’s fake trendline. Trendlines that are obvious to beginners are drawn so they can be broken and the stops parked just behind them can be taken.
91. Counter-trendlines. Scalp entries are built on breaks of trendlines that run against the day’s main path.
92. Channel median. The midline acts as a price magnet. A bounce from it confirms trend strength and a run to the opposite side.
93. Trendline crossing a horizontal level. The mathematical intersection of a sloping trendline and horizontal support is the highest-probability entry (confluence zone).
94. Break and retest of the trendline. After a rising trendline breaks, the entry is the later tag of that line from below, now acting as resistance.
95. Wicks versus bodies. On gold, trendlines drawn on body closes are more honest about a real break than lines drawn on random wicks.
96. Speed resistance fan. Draw three trendlines at different angles. A break of the first warns of a drop to the second. A break of the second targets the third.
97. RSI trendline. Draw trendlines on RSI. A break of the indicator’s trendline leads the actual price trendline break by two to three candles.
98. Higher-timeframe trendlines. A trendline drawn on D1 remains a hard barrier. It is not easily crossed except by a violent macro release.
99. Price diverging away from the trendline. A very large distance above a rising trendline bans immediate buying until price breathes back toward the line.
100. Break of a double-top trendline. A break of the trendline connecting the two troughs of a double top activates the sell even before the neckline breaks.
101. A broken trendline reverses its job. A rising trendline broken with force later becomes a resistance ceiling that rejects new rally attempts.
102. Symmetrical-triangle trendlines. A narrowing gap between the rising and falling trendlines inside a triangle warns of an explosion whose direction is the side that breaks.
103. Trendlines as moving targets. On a buy, the upper descending trendline can be the moving profit target as time passes.
104. Trendline break on a doji. A break by weak doji candles is a false break caused by missing liquidity, not a real shift in control.
105. Trendline aligned with the session. A touch of a rising trendline in the first minute of the London open gives the trade maximum thrust.

SECTION 5 — GOLD-SPECIFIC BEHAVIOR AND LIQUIDITY (XAUUSD DYNAMICS) (RULES 106–135)

106. Asian-range liquidity sweep. On about 80% of days, gold at the London open breaks the Asian high or Asian low to grab liquidity, then reverses completely.
107. Gold does not forgive a late stop. Once the reversal starts, a 20-point loss is better than waiting. Gold can travel 300 points without pausing.
108. Major psychological-number traps. Around levels such as 2400.00, gold repeatedly fakes breaks by 50 to 80 points to flush retail contracts before the real move.
109. The 3:30 p.m. Mecca-time candle (New York open). This candle often erases everything London built, in minutes. Close or fully protect intraday contracts before it.
110. Gold is a fear haven, not an intraday inflation trade. In moments of urgent military tension, technical analysis is suspended. Gold is bought as a fact, driven by institutional market orders.
111. Temporary decoupling from DXY. Gold can rise with the dollar during severe banking panic. Do not treat the inverse relationship as a 100% sacred rule.
112. Gold’s normal volatility (gold ATR). Gold’s natural daily range is about 250 to 400 points. A move under 150 points means the market has not started its explosion.
113. News-wick trap. The first move in the 5 seconds after CPI or a rate decision is often a reverse trap that swallows liquidity before the real direction.
114. Equal highs and equal lows are targets. Gold does not leave equal highs or equal lows without returning to break them and run the stops behind them, even days later.
115. Sharp liquidity void. Very long candles left during news are attraction zones. Price later returns to fill at least 50% of them.
116. Gold likes the 78.6% Fibonacci retracement. Unlike currencies that often stop at 50% or 61.8%, gold prefers very deep pullbacks that hit the largest number of stops before launching.
117. Daily fixing flow. From 6:00 to 7:00 p.m. London time, spot gold is fixed and sudden contract liquidations occur. (Translated as written.)
118. The midnight spread trap. From 11:55 p.m. to 12:15 a.m. platform time, gold’s spread widens violently. Do not trade, and do not use tight stops, in that window.
119. A real support break becomes a vertical dump. If gold breaks genuine support and holds below it with two H1 candles, it does not correct. It collapses vertically toward the next historical support.
120. Do not chase giant green candles. Buying after gold has already risen 150 points in 5 minutes is trading suicide. The correct buy is in the quiet zone before the explosion.
121. Real yields (TIPS). A sustained rise in bond yields is a standing brake on gold rallies on higher timeframes.
122. Friday behavior. Friday closes often bring profit-taking and liquidation by large funds, producing strong moves against the week’s direction.
123. Monday’s first hour. The weekly open reflects holiday sentiment and often fills leftover price gaps.
124. Gold invalidates oscillators in ranges. RSI or Stochastics fire repeated false signals when gold is trapped in a tight 70-point range.
125. Safe-haven runaway. On geopolitical-panic days, every dip, however small, is an immediate buy. Do not hesitate.
126. Harmonic link with silver. If silver breaks its prior high and gold has not yet broken its own high, gold will catch up, and it will do so quickly (silver leading).
127. Do not trade US bank holidays. On US holidays (for example Labor Day), gold is dead and random, and the spread burns the account.
128. Late New York reversal. After 8:00 p.m. Mecca time, gold often starts a correction against the direction it held all day.
129. Gold tests invisible liquidity. Prior-day closes are magnetic support and resistance on gold.
130. A break of the 200 EMA on H4. This is the dividing line between gold’s long-term uptrend and downtrend. Above it, the standing bias is buy. Below it, the standing bias is sell.
131. Pre-NFP stagnation. Gold stays in a very tight range in the days before the US jobs report. Trading inside it drains the account.
132. Gold moves as a block with mining equities. The gold-miners index (GDX) gives a lead on actual gold by hours.
133. Bollinger Band extreme. A gold candle that closes fully outside the outer Bollinger Band on H1 warns of an immediate corrective return toward the middle line.
134. Contract size and pricing. A one-dollar move in gold equals 100 points in the point calculation. Precise risk math is what prevents a margin call on a single candle.
135. Quiet rallies, violent declines. Gold rallies often take days of slow grind. Profit-taking and declines happen in a few hours, with giant engulfing candles.

SECTION 6 — TARGETS AND PROFIT TAKING (RULES 136–160)

136. The target is not always support or resistance. Target one can be a sloping trendline, a channel midline, or a percentage distance measured by ATR.
137. Mandatory partial close. Take 50% of the contract’s profit as soon as price travels a distance equal to the stop, and move the stop to entry immediately.
138. Open targets at historical extremes. When gold prints a new all-time high and prior resistance does not exist, set targets with Fibonacci extensions (1.272 and 1.618).
139. Exit before the psychological level, with a safety margin. If resistance is 2500.00, place take-profit at 2496.00 so price does not turn before the round number.
140. Time exit before the session close. Close open intraday trades one hour before the New York close, whether or not the final target was reached.
141. Prior-day extremes as targets. Yesterday’s high and yesterday’s low are the most accurate and reliable daily targets on gold.
142. Extend the target on engulfing momentum. If price reaches target one on a giant full marubozu, do not close. Extend the target to the next level. Momentum is exceptional.
143. Take profit on extreme oscillator readings. Close manually if RSI exceeds 85 on H1, even if the technical target is farther.
144. Exit on momentum exhaustion. If price needs 10 candles to travel a distance it previously covered in one candle, close the profit immediately.
145. Target the first opposing liquidity gap. On buys, the first bearish FVG in the path is a primary exit. It will stall the rally.
146. Do not demand the entire wave. Take 70% to 80% of the expected range and leave the rest. Wave endings reverse sharply.
147. Lock profit after target two. When target two is hit, pull the stop behind target one so that profit is already secured.
148. The opposite side of the channel is the only target. A buy from the channel floor targets the channel ceiling. Do not try to trade a breakout of it.
149. Shrink targets before major news. If a trade is in profit 15 minutes before a rate decision, close at the available profit immediately.
150. External liquidity as the target. The logical target of a buy that launched from a low is the high from which the original decline began.
151. Adjust targets for the spread. On buys, the profit target must be calculated so it covers the spread cost taken at the exit.
152. Head-and-shoulders target. Measure the vertical distance from the head to the neckline and project it from the break point.
153. Staged scale-out. Split take-profit into three levels: 40% at target one, 30% at target two, and 30% left as a runner for the larger trend.
154. Exit on a reversal pattern on a smaller timeframe. If you are long on H1 and a clear double top prints on M5, close immediately.
155. Promote an intraday trade to a swing. If the entry is a confirmed weekly low, cancel the limited daily target and trail profit on the longer horizon.
156. The 50-day average as a target. In corrective moves, the 50-day SMA is a decisive target for the bounce.
157. Take profit before the weekend. Do not hold through Saturday and Sunday. A gap open against the trade can be severe.
158. Liquidation-run target. Place the target below the cluster of buy stops, to capture the full flush.
159. Elliott proportional target. In a bullish third wave, the minimum target is 1.618 times the length of wave one.
160. Accept available profit when structure changes. Exit at any available profit as soon as the first minor M15 low breaks. Do not wait for the entry stop to be hit.

SECTION 7 — CANDLE PSYCHOLOGY AND PRICE TRAPS (RULES 161–180)

161. Hammer trap. A hammer in the middle of a move, with no real liquidity zone under it, is a trap that gets retail traders long before the decline.
162. Quiet-breakout deception. A resistance break on a small-bodied candle does not show buyer strength. A real break needs a body that is about 80% of the candle’s range.
163. A doji means indecision, not reversal. A doji does not require a counter-entry. It means both sides are waiting for new liquidity that may continue the same trend.
164. Failed engulfing trap. If a bearish candle engulfs the prior bullish candle, then the next candle fails to continue down, that was a sell trap. Buy immediately.
165. Shooting star at an all-time high. It has the highest sell credibility when the upper wick is three times the body.
166. Gradual engulfing (momentum shift). Candles changing from large bearish bodies to tiny bearish bodies show selling exhaustion and a nearby upside explosion.
167. Multiple-high break trap. New highs by only a few points, with long wicks, reflect cautious institutional distribution and warn of a nearby collapse.
168. Inside bars. Three candles trapped inside a giant mother candle show compression that is followed by an explosion in the break direction.
169. London’s first impulse-candle trap. The first 15-minute candle of the London open is often a trap that points attention at a false direction.
170. Close in the top quarter. A candle that closes in the top 25% of its range confirms bull control, regardless of the lower wick.
171. Late-entry trap behind a candle streak. Five consecutive bullish M15 candles make a correction more likely than continuation. Buying is banned there.
172. Double rejection wicks. Two consecutive long wicks in the same price zone confirm an institutional wall that cannot be broken for now.
173. Lower absorption candle. A strong bearish candle followed by a bullish candle that fully engulfs it on the same timeframe wipes seller control and confirms the rally.
174. False break of the prior daily low. A wick through yesterday’s low and a fast close back inside yesterday’s range is the strongest bullish reversal pattern.
175. Wicks disappear in a strong trend. A strong trend does not carry long upper and lower wicks. It is one-color candles pushing price in order.
176. Range-box trap. Price leaves a sideways range in one direction to fake a breakout, then reverses and breaks the opposite side completely.
177. Selling climax. A giant bearish candle with historical volume after a long decline is the end of the decline and a flush of contracts, not the start.
178. Bodies tell the truth; wicks hunt liquidity. Use open and close of candle bodies for the real direction. Ignore wick noise.
179. Gap-fill trap. Not every gap must close immediately. Breakaway gaps from a structural separation can stay open for months.
180. Spinning tops at support. They show seller hesitation after a decline and are the start of a new bullish base.

SECTION 8 — EXECUTION LOGIC AND STRICT ALGORITHMIC DISCIPLINE (RULES 181–200)

181. Standing aside is itself a trade. When the picture is unclear and signals conflict, staying a spectator is a profitable decision. It protects capital.
182. Zero-hesitation execution. Once the algorithmic conditions are met, send the order immediately. Do not wait for a late human consultation.
183. Auto-cancel pending orders. Any pending order (buy limit / sell limit) that has not filled within 3 hours of being placed is cancelled in code. The technical context has expired.
184. No double entry on the same instrument. Do not open a new gold buy if a prior gold buy is still open and losing. Do not stack losses.
185. Separate scalps from swings. Each strategy has its own magic number. Do not merge an intraday stop with a longer-term stop.
186. Immediate exit on a leaked hot headline. If gold moves 80 points in one minute with no technical reason and no scheduled release, close positions immediately. An emergency headline may have leaked.
187. Revenge trading is banned in code. Freeze the platform and block new orders for 60 minutes after two consecutive losses in the same session.
188. Dual lot-size check. The position-size calculation is reviewed twice in code before send, so a decimal-point error cannot become an account disaster.
189. Refresh the live feed before send. Check the latest MT5 tick. If the data is older than 5 seconds, cancel execution. The connection may be down.
190. Flexibility when the market changes. If gold suddenly reverses and breaks structure, drop the bullish bias immediately. Do not cling to the previous analysis.
191. Respect the daily loss cap. If the account reaches a 3% daily drawdown, the agent closes every trade and disconnects until the next morning.
192. Market orders when confirmation is decisive. Use market orders rather than limits when a break-and-confirm candle is seen, so the move is not missed.
193. Cancel the idea if price has already traveled half the distance to target. If price runs toward the target before the pending entry fills, cancel the trade. Do not chase it on the way back.
194. Log the entry reason on the order. Write the technical code the trade was built on (for example BOS_M15_FVG_Retest) in the comment field of every contract, for later review.
195. No new trades in the last 15 minutes before the daily close. Liquidity is thin, and rollover and spread costs are high.
196. Recalculate reward-to-risk live. If price moves one point worse than the planned entry and R:R falls below 1:1.5, cancel the entry.
197. No trading on official holidays. Disable the trading algorithm entirely on New Year’s Day and Thanksgiving. Market makers and major central banks are absent.
198. The chart must be free of contradictions. If H4 is a clear buy while M15 shows a completed bearish distribution pattern, entry is banned until the two timeframes agree.
199. Lot size follows closed balance, not floating equity. Increasing size as the account grows is based on settled closing balance, not floating profit (equity versus balance).
200. The standing golden rule. The market is always right. Technical analysis is only a map of probabilities. Protecting capital comes first. Profit comes second.


================================================================================
PART C — NEWS AND VIOLENT-VOLATILITY PLAYBOOK
100 OPERATIONAL RULES
================================================================================

Note: The source numbered Section 1 as rules 1–18, Section 2 as 19–34, Section 3 as 35–55, then jumped to Section 5 at rule 73. Rules 56–72 and Section 4 were not in the source. They are not invented here.

SECTION 1 — PRECAUTIONARY PROTOCOLS BEFORE THE RELEASE (RULES 1–18)

1. Mandatory pre-news freeze window. No new trades in the 15 minutes before high-impact releases (CPI, NFP, FOMC), to avoid liquidity-sweep chaos.
2. Cancel all pending orders. Delete every buy and sell pending order (limit and stop) 10 minutes before the release, so slippage cannot activate them.
3. Protect open winners. Move the stop of trades already open to entry, or close 70% of size, 10 minutes before pivotal data.
4. Flatten trades sitting near entry. Close any trade that is not more than 30 gold points away from entry, so spread expansion does not hit the stop immediately.
5. Watch spread expansion in advance. Measure the spread two minutes before the release. If it is more than 3 times normal, arm the automatic trading lock immediately.
6. Priced-in analysis. Compare the prior 4 hours of price with the consensus. A sharp directional move before the release means the market has already absorbed the result.
7. Mark the quiet pre-news range. Draw the highest high and lowest low of the last 30 minutes before the release. Those become break boundaries and liquidity traps.
8. Disable a tight trailing stop. Turn off intraday trailing immediately before the release. The first random spike will hit the trail and steal the later trend.
9. Filter simultaneous releases. Raise the danger rating when two prints land together (for example the unemployment rate alongside NFP).
10. Check connection quality and ping. MT5 server latency must be under 50 ms one minute before the release. If delay is higher, trading is fully banned.
11. Do not trade if the release coincides with the daily rollover. No entry if the print lands on the contract roll and swap update.
12. Consensus deviation threshold. Code the forecast-versus-actual gap required to move the market for real (for example a 50,000-job miss or beat on NFP).
13. Silence during the Fed Chair’s testimony. Stay completely quiet for the entire congressional testimony and until the press conference is fully over.
14. Watch DXY liquidity rushing in before the print. If the dollar index is breaking lows minutes before the release with no visible reason, treat it as an early leak of dollar-negative data that supports gold higher.
15. Mark macro extreme zones. Draw the nearest daily support and resistance 150 to 300 points from the current price, in case the news candle tags them.
16. Exceptional lot-size cap. Cut allowed risk in half (0.5% instead of 1%) for any execution on a major-data day.
17. Stop-market trap ban. Do not place buy-stop or sell-stop orders to catch the news explosion. They fill at the worst slippage.
18. Separate scheduled news from surprises. Code a distinction between calendar events and geopolitical shocks that require immediate action with no timetable.

SECTION 2 — DECODING THE DATA SHOCK AND LIVE NUMBERS (RULES 19–34)

19. CPI shock logic. Inflation above forecast means higher yields and a stronger dollar, and a sharp, fast drop in gold. The opposite is also true.
20. NFP dynamics. Very strong hiring with falling unemployment supports a delay in rate cuts, and immediate selling pressure on gold.
21. Split-data paralysis. If payrolls are dollar-positive and average earnings are dollar-negative, classify the market as “conflicted, high risk” and cancel every trade automatically.
22. Revisions matter. Watch the prior month’s revision. A downward revision of last month immediately cancels a positive current print and flips the bias toward gold.
23. The rate decision versus the press conference. The hold or hike sets the first move. The Chair’s tone 30 minutes later sets the day’s final direction.
24. Buy the rumor, sell the fact. If gold has already rallied hard into a rate cut priced at 99%, the moment of the actual print often brings a distribution decline as profits are taken.
25. Surprise-delta score. Do not react if the print matches consensus exactly. A match means stability and a tight, directionless range.
26. PMI reading. A purchasing-managers index below 50.0 signals economic contraction and pushes gold up quickly as an investment haven.
27. Ignore secondary numbers. Filter out consumer confidence and home sales if they land in the same week as major inflation and employment data.
28. Immediate yield divergence. If the print is dollar-positive but 10-year yields fall, gold’s decline will be temporary and it will bounce quickly.
29. PPI as an early CPI warning. Positive PPI surprises pave the way for gradual downside waves in gold ahead of CPI.
30. Absorption speed. Measure how long price takes to return to the print level. Negative data absorbed in under 5 minutes shows overwhelming institutional buying.
31. Weekly jobless claims. Unusually large jumps in claims show a weaker labor market and give gold an immediate buy bid.
32. Fed speeches via keywords. Flag dovish phrases such as “slowdown,” “downside risks,” and “watching employment” as support for an intraday buy.
33. Rate-futures probability shift. Track the FedWatch tool immediately after the print. A jump in cut odds supports gold staying bid for the rest of the session.
34. Isolate the dollar’s intraday effect. If gold falls while the dollar falls at the same time, the driver is a broad liquidity liquidation, not a normal data response.

SECTION 3 — ANATOMY OF THE NEWS CANDLE AND MICROSTRUCTURE (RULES 35–55)

35. The dead first minute (the 60-second void). A hard ban on any entry or analysis during the first 60 seconds after the print. Candles in that minute are algorithmic chaos.
36. Two-sided liquidity sweep. A candle that takes the pre-news high and, in the same minute, takes the pre-news low is a liquidation of traders’ contracts, not a trend.
37. The M5 close is the primary reference. The first 5-minute candle that closes after the print is the technical standard. Trade the direction of its body if the body is more than 70% of the range.
38. Long rejection-wick rule. If the news candle leaves an upper wick twice the body after a sudden spike, classify the spike as a trap and activate the sell immediately.
39. News fair value gap. A huge price void on the one-minute candle defines a later reaction zone. Do not buy until price has filled 50% of that void.
40. A real break of the pre-news range. The post-news direction counts only if an M15 candle closes entirely outside the range marked before the print.
41. Instant engulfing deception. If gold rises 100 points in one minute and the next candle engulfs that entire rise in minute two, the day’s real direction is down.
42. Do not enter the middle of a giant candle. If gold has already moved 150 points, buying the high out of fear of missing out is banned. Entry is only on the pullback.
43. Consecutive tick volume. If tick volume fades immediately after the first candle, algorithmic fuel is spent and the move is about to stall.
44. Range reclaim reversal. If the print breaks a major daily low and price trades back above that low within 10 minutes, that is a decisive sell trap and a major buy.
45. Wicks vanish in a sweeping trend. When the following minute candles open and run in one direction with no wicks, institutional flow is continuous. Ride it.
46. False break of the Asian high. Using the news candle to poke a few points through the Asian high and then collapse is one of gold’s clearest daily liquidity sweeps.
47. One-minute noise filter. Do not use one-minute closes for high-stakes decisions during news. Use M5 and M15 to filter noise.
48. Outer Bollinger explosion. A news candle that closes 90% outside the upper Bollinger Band is extreme extension and forces a correction toward the middle line.
49. The shock wick as support. The lowest point of a bullish news candle’s wick is the ideal stop for any later buy.
50. Candles aligned with a trendline break. If the news explosion breaks a major H1 descending trendline and closes above it, the bias flips to a sustained uptrend automatically.
51. Paralyzed volatility (compression trap). If gold does not move after an important print and stays inside a 20-point range, a violent delayed explosion arrives within 30 minutes.
52. Hollow support break. A fast break of support on weak tick volume, caused by a liquidity vacuum, is a false break. Do not sell it.
53. Balance on a news doji. If the first M15 candle after the print closes as a doji on huge volume, buyers and sellers are tied. Trading is banned until one side of that doji breaks.
54. Momentum reversal on the first minor-low break. In an explosive rally, a break of the prior one-minute candle’s low is the first warning that profit-taking and a correction have started.
55. Holding above the news high. If gold holds above the high of the first news candle for more than 15 minutes, the upside path continues toward new historical targets.

[Rules 56–72 and Section 4 were not present in the source document.]

SECTION 5 — RIDING THE REAL TREND AFTER THE RELEASE (RULES 73–86)

73. The golden stability window (the 15-minute rule). The best time for high-probability entries starts 15 to 30 minutes after the print.
74. Retest entry of the shock candle’s high or low. Wait for a calm return to the break level of the first news candle, and enter with the reaction direction.
75. H1 closes after the print. Gold’s honest direction is set by the close of the first hourly candle after the release. Trade in the direction of that close.
76. Retracement to the optimal trade entry (OTE). After the first explosive leg, draw Fibonacci on the whole candle. Entry is between 61.8% and 78.6%.
77. New York momentum continuation. If the 3:30 p.m. Mecca-time news confirms gold’s direction, the move often continues in that direction until about 6:30 p.m.
78. Staged exits after major news. Split profit targets into three successive parts, to absorb the long extensions that economic data can create.
79. Confirmation by a break of historical levels. If the news explosion coincides with a break and hold above a prior weekly high, treat it as a multi-day swing buy.
80. Absorption after the shock. If price cannot print a new high in the three candles after the news candle, that warns of a reversal or the start of a correction.
81. Confirmed engulfing after the pullback. Wait for the news-candle correction to finish and for an M5 candle that engulfs the corrective candles, then enter immediately with the main direction.
82. Counter-trade only after the daily range is exhausted. If gold has already traveled 200% of its average daily range on the news move, stop chasing. Look for reversal signals instead.
83. Broken resistance becomes a solid support wall. Any ceiling blown apart by news becomes the best buy on the first calm pullback that tags it.
84. DXY confluence after the shock. Do not buy gold after the print unless the dollar index confirms the move by continuing to break its intraday lows.
85. Exit on a broadening wedge. Successive higher highs and lower lows after the print mean chaotic noise. Exit the market immediately.
86. Follow post-data remarks. Watch Federal Reserve officials in the hours after the data. Remarks that support the print lock the direction. Remarks that oppose it reverse it.

SECTION 6 — SUDDEN GEOPOLITICAL NEWS AND THE SAFE HAVEN (RULES 87–100)

87. Suspend technical analysis during military crises. When wars or sudden air strikes begin, technical resistance and overbought readings are cancelled. Gold is an outright buy.
88. Absolute ban on shorting a safe-haven wave. No gold shorts, however attractive the technicals, while attacks and geopolitical crises are escalating.
89. Immediate buy on the first credible breaking report. Send a direct market buy as soon as global news agencies confirm a major geopolitical event. Do not wait for a pullback.
90. Handling a hot weekend gap. If gold gaps up by more than 150 points because of events over the weekend, do not chase the buy immediately. Wait for the gap to be cleared.
91. Full decoupling from the dollar and equities. In global panic, gold rises together with the dollar while equity markets fall. Do not require a weak dollar as a condition for gold to rise in that regime.
92. Historical highs as open targets. In geopolitical panic, nearby targets are cancelled. External Fibonacci extensions (2.0 and 2.618) become the primary targets.
93. De-escalation invalidation. The moment an official statement signals calming or a ceasefire, close buy trades immediately. A violent, fast collapse is possible.
94. Riding banking-panic waves. When major banks fail or a sovereign default hits, gold is treated as the primary survival asset. Every corrective dip is a necessary buy.
95. Stop under the breaking-news candle low. Place the stop 20 points under the low from which price launched when the geopolitical report spread.
96. Beware of media amplification. Distinguish limited skirmishes from major crises. Inflating a passing event is followed by strong downside distribution within a few hours.
97. Do not buy the peak of the panic wave. When gold and gold buying lead general news channels watched by non-traders, the rally is late. Beware the corrective decline.
98. News-velocity metric. Watch how fast urgent headlines arrive. Escalatory headlines every few minutes are a green light to stay in buy trades.
99. Managing gold when global trade chokepoints close. Crises that threaten shipping lanes and oil prices lift inflation and gold together. Buying is the only strategic option then.
100. Sovereign rule for gold volatility. In panic and major news, remember: the skilled trader is not the one who captures every point. It is the one who crosses the storm with sound position sizing and protected capital.


================================================================================
PART D — NEWS-CANDLE DETECTION PLAYBOOK
100 ALGORITHMIC RULES
================================================================================

SECTION 1 — TIME ALIGNMENT AND THE ECONOMIC CALENDAR (RULES 1–15)

1. The zero minute of US data (the 8:30 a.m. / 10:00 a.m. EST rule). If a wide-range candle forms at minute 00 or 30 together with a major US release time, classify it as a news candle immediately.
2. The minute-45 candle (flash PMI releases). Explosive candles at minute 45 (for example 9:45 a.m. New York) are usually preliminary purchasing-managers releases and are treated as news candles.
3. Federal Reserve decision window (FOMC, 2:00 p.m. EST). Any candle that forms at exactly 2:00 p.m. Washington time, every six weeks, is the rate-decision candle, regardless of its shape.
4. Fed press-conference candle (2:30 p.m.). The sequence of candles that starts at 2:30 p.m. and runs for 45 minutes is live remarks and is classified as a chain of news candles.
5. Jobs-report candle (first Friday of the month). The 8:30 a.m. New York candle on the first Friday of each calendar month is officially the NFP candle. No extra technical confirmation is required.
6. London-open news flow. Large candles between 8:00 and 8:15 a.m. London time that coincide with UK GDP or UK inflation are classified as a European macro candle.
7. London PM gold fix. At 3:00 p.m. London time, sudden high-volume candles reflect interbank spot-gold reprice flows.
8. US Treasury auction candles. Explosive candles at 1:00 p.m. New York time are tied to 10-year or 30-year Treasury auction results.
9. Monthly contract-expiry candle (options expiry / futures expiration). Abnormal volatility on the last Friday of the month, at gold futures expiry, is classified as liquidation and settlement flow.
10. Calendar API sync. If the gap between the start of the candle and a red (high-impact) calendar event is under 60 seconds, classify it as a news candle automatically.
11. Oil-inventory report and its spillover. Wednesday, 10:30 a.m. US Eastern. If it drives a violent gold move together with an oil spike, record it as a linked energy news candle.
12. European Central Bank decision. The Thursday 2:15 p.m. Central European Time candle on meeting days is treated as a monetary shock for currencies, and it feeds through to gold.
13. OPEC+ meeting candle. Explosive candles on OPEC meeting days, caused by production decisions that are not scheduled to the hour, are classified as commodity news.
14. Unscheduled central-bank governor speeches. The candle that coincides with a live broadcast or a published text from the Fed Chair at an economic forum.
15. Quarter-end rebalancing candle. Abnormal candles in the last 30 minutes of trading at the end of March, June, September, and December are classified as institutional portfolio-rebalance candles.

SECTION 2 — RANGE DYNAMICS AND ATR MULTIPLES (RULES 16–30)

16. The 3× ATR rule. If the candle’s range (high minus low) is greater than 3 times the 14-period ATR, it is a confirmed news candle.
17. One-minute range outlier. Gold moving more than 60 to 80 points in a single one-minute candle, outside dead hours, is a direct fingerprint of a news candle.
18. Intraday daily-range break. If a 5-minute candle covers more than 40% of gold’s average daily range in one push, record it immediately as a news candle.
19. Distance velocity. Price moving faster than 1.5 points per second, continuously, with no pullback, for 30 seconds.
20. Range versus the last 20 candles. If the current candle’s size equals the combined length of the previous 10 candles, the driver is an external news engine.
21. Hidden intraday gap. Price jumps from one tick to the next with no trades in the space between, leaving a price void inside the intraday candle.
22. Instant break of Bollinger extremes (beyond 3.5 standard deviations). A close outside the 3.5-sigma Bollinger Band marks a sweeping news event.
23. Weekly-range liquidation candle. A single one-hour candle engulfs the entire trading range of the previous three days, up or down.
24. Spike candle. A fast vertical move of more than 100 points in under 120 seconds, followed by a sudden stop at a pivotal number.
25. Expanding-bar anomaly. Consecutive M5 candles grow in a doubling geometric progression within a few minutes. (The source left the progression formula blank.)
26. Low-volatility discharge candle. A huge candle after an extremely tight range of no more than 15 points. The shock contrast confirms a news engine.
27. Yesterday’s high and low broken inside one 15-minute candle. Breaking both yesterday’s high and yesterday’s low inside the same M15 candle marks a major data shock.
28. One-way extended range. A candle longer than 120 points with almost no upper or lower wick (full-body marubozu) on M5.
29. Air retracement candle. Price travels a huge distance, then retraces 80% inside the same candle, without building clear support or a structured correction.
30. Statistical range outlier (range z-score greater than 4). The current candle’s range is more than four standard deviations above the session’s historical average.

SECTION 3 — TICK FLOW AND INTRADAY VOLUME (RULES 31–45)

31. Tick-volume explosion (tick-volume z-score greater than 3.5). The tick count inside the candle exceeds the average tick volume of the last 50 candles by more than three standard deviations.
32. Ticks per second spike. Tick flow rises from a normal 5–15 ticks per second to more than 80–150 ticks per second on gold.
33. Volume climax. 70% of the candle’s total tick volume concentrates in the first 15 seconds of the candle, then the pace collapses.
34. Extreme one-minute volume. A single M1 candle’s tick volume exceeds what a full H1 candle would print in quiet trading.
35. Explosive volume with no time gaps. A continuous order stream that does not allow more than 5 milliseconds between ticks.
36. Buy volume inside a giant bearish candle. Heavy buy tick volume concentrated at the bottom of a fast bearish candle. That is an intraday news-absorption fingerprint of the market maker.
37. One candle doubles the session’s cumulative volume. A single candle contributes 25% of all volume activity in the session up to that moment.
38. Opposite volume vacuum. A rocket move followed immediately by falling volume on the next candles. The response was news-driven and is not supported by sustained liquidity.
39. Volume explosion on a historical-high break. The day’s highest tick reading prints at the moment a major level breaks, driven by economic data.
40. Heavy delta imbalance. One side of the market (buy or sell) controls more than 90% of the candle’s ticks.
41. Ask evaporation. Buy ticks increase with wide price jumps because market makers have pulled their limit offers.
42. Compare volume with the same minute historically. Compare this candle’s volume with the same minute on prior days. An increase of more than 500% means it is certainly a news candle.
43. Trading density at the candle extremes. Ticks cluster at the upper or lower wick, showing a fast liquidation battle during the release.
44. Volume jump with a brief price freeze. Ticks freeze for two seconds because the broker server is processing orders, then explode as 200 ticks at once.
45. Total volume air-pocket. A large price slip on relatively low ticks, because opposing liquidity was simply absent from the book at the moment of the number.

SECTION 4 — SPREAD BEHAVIOR AND INTRADAY LIQUIDITY VOIDS (RULES 46–60)

46. Sudden spread expansion (spread greater than 3 times normal). The Bid–Ask gap jumps from 15–20 points to 60–120 points in fractions of a second.
47. Pumping spread. The spread expands and contracts wildly on every new tick. That is the classic fingerprint of defensive liquidity-pull algorithms.
48. Wide spread with a directional bullish candle. Price rockets higher while the spread stays very wide. Liquidity providers are refusing to quote a stable offer.
49. Bid or Ask freeze. The Ask freezes while the Bid keeps jumping higher. A momentary pricing imbalance caused by a news shock.
50. Slippage on live fills. Slippage between order price and fill price exceeds 20 points on the engine’s probe orders.
51. Order-book clearance. Deep liquidity (depth of market) disappears, leaving a void that small trades can move.
52. Spread widens 10 seconds before price moves. Liquidity providers front-run the statement by widening the spread on purpose before price itself moves.
53. Gapped ticks. Price jumps from 2450.10 to 2451.80 in one tick, skipping the prices in between.
54. Liquidity collapse at peak hours. A sudden spread widening in the middle of the New York session, when liquidity should be at its best, is decisive evidence of an emergency event.
55. Rejection through an open spread. Price reaches resistance as the spread doubles, then reverses. A market-maker trap that triggers buy stops at poor prices.
56. Spread does not normalize after the candle closes. Spread staying wide for more than 3 minutes after the explosive candle confirms that panic is still in the market.
57. Spread divergence between gold and currencies. Gold’s spread is 5 times normal while EURUSD’s spread is normal. The news is specific to metals or to political tension.
58. High broken by the spread alone. A historical high is tagged only because the Ask expanded, while the actual Bid never reached it, in order to liquidate short positions.
59. Liquidity-vacuum slip. Gold’s candle falls with no opposing bids, so the decline looks like a straight line with no resistance.
60. Spread expansion together with a drop in intraday “voltage.” Prices pull apart and candles hesitate in the minutes before the Fed Chair speaks.

SECTION 5 — CROSS-MARKET SYNCHRONIZATION (RULES 61–75)

61. Instant opposite explosion in DXY (mirror spike). A violent bullish gold candle forms in the same second as an equally violent bearish candle on the dollar index.
62. US 10-year yield shock. 10-year yields move more than 1.5% up or down at the moment the gold candle forms.
63. Full sync with silver (XAGUSD). Gold’s candle speed matches silver’s candle with more than 95% agreement in the same minute.
64. Exceptional decoupling. Gold rockets and the dollar rockets in the same candle. That is decisive evidence of war news or a severe banking crisis (absolute safe haven).
65. Equity decline with a gold rally. A giant bearish S&P 500 candle coincides with a giant bullish gold candle (risk-off shock).
66. Synchronized crude-oil jump. Gold and Brent explode in the same minute. That is the fingerprint of geopolitical tension in the Middle East or in energy supply.
67. USDJPY flash move. USDJPY moves 80 points in the same moment as the gold candle. Confirmation of a shared US release (inflation or employment).
68. Industrial-metals response (copper). If gold moves alone while copper is flat, the news is monetary or rates. If they move together, the news is about global growth and PMI.
69. VIX spike. The fear and volatility index rises more than 5% within a few minutes, together with the gold candle.
70. Sync with safe-haven currencies (franc and yen). Gold and the Swiss franc rise together against other currencies, confirming the safe-haven character of the news candle.
71. Central-bank float or intervention candle. Currency pairs linked to gold move by record amounts because of direct central-bank intervention (for example Bank of Japan intervention).
72. Opposite crypto shock. Bitcoin and high-risk liquidity fall as gold’s green candle explodes. Liquidity is leaving toward traditional assets.
73. Gold breaks together with euro-priced gold (XAUEUR). A historical high on gold in both dollars and euros in the same candle means the move is not merely dollar weakness.
74. Inflation-linked bond response (TIPS breakdown). A record drop in real yields fuels a historical gold buy candle the moment CPI is released.
75. Gold lags the currency reaction. A violent EURUSD move 10 seconds before gold’s candle is an early signal to the agent that gold’s news candle is about to print.

SECTION 6 — TECHNICAL GEOMETRY OF THE NEWS CANDLE (RULES 76–90)

76. Two-horned spoon candle (expanding horn). A long upper wick, a long lower wick, and a tiny body. The result of violent two-way news volatility.
77. Instant full engulfing flush. The candle breaks the prior high by 30 points, then falls through the prior low and closes 50 points below it, inside the same timeframe.
78. One-tailed rocket (exhaustion pin bar). The wick is more than 80% of a total length greater than 150 points. The classic news-rejection pattern.
79. Small shadows disappear along the path. Shadows vanish entirely from consecutive M1 and M5 candles. Institutional buy or sell pressure is continuous and allows no correction.
80. Hollow tower candle. A vertical candle cuts through several technical zones without pausing, leaving a complete liquidity imbalance behind it.
81. Extreme outside bar. The candle’s range is above the highest high of the last 5 candles and below the lowest low of those same candles.
82. V-reversal attack. The one-minute candle falls 80 points, then the next candle rises 100 points immediately. A fast flush before the upside path.
83. Body holds outside resistance with no correction. A 15-minute candle closes entirely above solid resistance with no upper wick. That is news thrust.
84. Three merged news candles (3-bar cascade). Three M5 candles in a row with the same size, momentum, and direction, and almost no wicks. This is rare and happens after major data.
85. Simultaneous break of trendlines and levels. One candle breaks a descending trendline, a horizontal resistance, and a Fibonacci level at the same time.
86. Oversized doji. A 200-point range whose close matches its open exactly. A brutal fight between bulls and bears during the statement.
87. Fake rising hanging candle. The candle rallies hard to a high, then collapses in the last 10 seconds, leaving a giant wick and a small red body at the bottom.
88. Intraday breakaway tick gap. The next one-minute candle opens 15 points above the prior close inside the live market, with no daily close involved.
89. Asian range taken in one pulse. One candle sweeps the entire Tokyo-session range in the first minute of the New York open.
90. Marubozu on higher timeframes. A full H4 candle becomes a driving marubozu because a sequence of aligned headlines stacked together.

SECTION 7 — BREAKING NEWS AND GEOPOLITICAL DISRUPTION (RULES 91–100)

91. Abnormal midnight candle (Asian midnight flash). A move of more than 100 points on gold during the quietest hours (early Asia) is decisive evidence of military news or an emergency statement.
92. Temporary trading-halt candle. A Chicago Mercantile Exchange circuit breaker that freezes gold futures for minutes shows up on the spot chart as frozen ticks, then a huge price jump.
93. Weekend news gap. Monday’s first candle opens with a gap larger than 150 points because of political events while markets were closed.
94. Warning and military-strike candle. A vertical bullish candle with record buy volume appears as soon as reports of a military attack or a closed shipping strait circulate.
95. Silent candles, then a sudden explosion. Price is completely still, then launches 80 points in one candle with nothing on the economic calendar. That is the fingerprint of a breaking wire headline.
96. Presidential intervention or economic-sanctions candle. Candles caused by sudden tariff announcements or international sanctions packages that affect gold and metals trade.
97. Fast banking-collapse candle. A drop in regional-bank shares produces a panic-buying candle on gold as an immediate refuge from systemic risk.
98. Reverse reaction to a political calming. Gold collapses on a giant bearish candle the moment an official statement announces a ceasefire or the end of a diplomatic crisis.
99. Sudden sovereign-downgrade candle. Gold ignites after a major rating agency cuts the United States’ sovereign credit rating.
100. Reference rule for deciding that a candle is news. If ATR has tripled, tick volume has jumped hard, and the spread has widened suddenly, the agent classifies the candle as an “inevitable news candle” and immediately arms the news-shield and protection protocol, whether the event was on the calendar or was a surprise.
