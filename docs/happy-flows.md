# Manual Happy Flow Test Guide

Each section is a self-contained flow. Run them top-to-bottom for a full regression pass, or jump to a specific area. Every step lists the exact command, what you should see, and what "pass" looks like.

---

## Prerequisites

```bash
# Install CLI in dev mode
pip install -e .

# Verify entry point works
trade --help

# Set a working AI provider (pick one)
export ANTHROPIC_API_KEY=sk-ant-...   # recommended
# OR
export GEMINI_API_KEY=AIza...
# OR
export OPENAI_API_KEY=sk-...
```

---

## Flow 1 — No-Broker Startup (Mock Mode)

Tests that the platform starts and is usable without any real broker account.

```
trade --no-broker
```

**Step 1 — REPL loads**
- You should see the welcome banner and `>>>` prompt
- No error about missing credentials

**Step 2 — Help works**
```
help
```
- Should print all available command categories

**Step 3 — Provider check**
```
provider
```
- Should show current AI provider (anthropic / gemini / openai / ollama) and model name

**Step 4 — Exit cleanly**
```
quit
```

---

## Flow 2 — Onboarding (First Run Setup)

Tests credential management before a broker is connected.

```
trade --no-broker
```

**Step 1 — Show current credentials**
```
credentials list
```
- Shows which keys are set (masked) and which are missing

**Step 2 — Set a credential**
```
credentials set NEWSAPI_KEY test-newsapi-key-123
```
- Should confirm the key was saved

**Step 3 — Clear a credential**
```
credentials clear NEWSAPI_KEY
```
- Should confirm cleared

---

## Flow 3 — Market Data (No Broker Required)

All market data falls back to yfinance when no broker is connected.

```
trade --no-broker
```

**Step 1 — Single quote**
```
quote RELIANCE
```
- LTP, open, high, low, volume, change%
- No crash, no "broker required" error

**Step 2 — Multi-quote**
```
quote TCS INFY WIPRO HDFCBANK
```
- Table with all 4 symbols side by side

**Step 3 — Macro snapshot**
```
macro
```
- USD/INR, Brent crude, Gold (MCX), US 10Y yield
- All values populated (may say N/A if yfinance is slow — that's OK)

**Step 4 — Earnings calendar**
```
earnings
```
- Upcoming results for NIFTY50 stocks; list is not empty

**Step 5 — Earnings filtered**
```
earnings INFY TCS WIPRO
```
- Only those 3 symbols in output

**Step 6 — FII/DII flows**
```
flows
```
- Buy/sell values for FII and DII; signal shown (bullish/bearish/neutral)

**Step 7 — Bulk deals**
```
deals
```
- Recent bulk/block deals table

**Step 8 — Most active stocks**
```
active
```
- Top stocks by volume, sorted

---

## Flow 4 — Quick AI Analysis

Single-LLM scan, should complete in 3–5 seconds.

```
trade --no-broker
```

**Step 1 — Quick scan single symbol**
```
quick INFY
```
- Returns BUY / SELL / HOLD with brief reasoning
- Completes in < 10 seconds

**Step 2 — Quick scan multiple symbols**
```
quick TCS HDFC RELIANCE
```
- Verdict for each symbol; table format

---

## Flow 5 — Full Multi-Agent Analysis

7-analyst debate + 3 trade plans. Slower (~30–90s) but comprehensive.

```
trade --no-broker
```

**Step 1 — Standard analysis**
```
analyze INFY
```
- See analysts streaming in (Technical, Fundamental, Options, News, Sentiment, Sector, Risk)
- Output ends with 3 ranked trade plans (aggressive / neutral / conservative)

**Step 2 — Analysis with explanation**
```
analyze TCS --explain
```
- Same as above but followed by a plain-English summary

**Step 3 — Analysis with PDF export**
```
analyze WIPRO --pdf
```
- Analysis runs; at the end prints a path like `~/Desktop/wipro_analysis.pdf`
- Verify the file exists on Desktop

**Step 4 — AI follow-up question**
After an `analyze` completes, ask a follow-up:
```
ai What is the risk if NIFTY drops 2%?
```
- Gets a contextual answer referencing the previous analysis

**Step 5 — Clear chat context**
```
clear
```
- Confirms conversation history cleared

---

## Flow 6 — Morning Brief

```
trade --no-broker
```

```
morning-brief
```
- Market overview: indices, top movers, macro snapshot
- AI narrative summarising the day's setup
- Completes without error

---

## Flow 7 — Backtesting

**Step 1 — Single strategy backtest**
```
trade --no-broker
```
```
backtest RELIANCE rsi
```
- Shows: total return, Sharpe ratio, max drawdown, win rate, trade count
- No crash

**Step 2 — Different strategy**
```
backtest TCS macd --period 1y
```
- Same metrics, 1-year window

**Step 3 — Vectorized fast backtest**
```
backtest INFY rsi --fast
```
- Completes in < 2 seconds
- Shows metrics (no slippage warning shown — that's expected for vectorized mode)

**Step 4 — Multi-strategy comparison**
```
backtest NIFTY rsi macd bb --compare
```
- Side-by-side table of all 3 strategies sorted by Sharpe ratio

**Step 5 — Compare with HTML report**
```
backtest RELIANCE rsi macd --compare --html
```
- Table shown in terminal
- "Report saved to ~/Desktop/backtest_report_*.html" printed
- Open the HTML file in browser: should show Chart.js equity curve + rankings table

**Step 6 — Walk-forward test**
```
walkforward RELIANCE rsi
```
- Shows rolling window results with consistency score

---

## Flow 8 — Options Analytics

These commands work best with a broker connected (Fyers or Zerodha). With `--no-broker` they may return mock/limited data.

```
trade --no-broker
```

**Step 1 — OI profile**
```
oi NIFTY
```
- OI by strike, max pain price, PCR, support/resistance levels

**Step 2 — IV smile**
```
iv-smile NIFTY
```
- IV values across strikes; skew visible (puts > calls for index)

**Step 3 — GEX**
```
gex NIFTY
```
- Positive/negative GEX by strike; gamma flip level

**Step 4 — Options scan (quick)**
```
scan --quick
```
- Fast scan: high-IV setups, unusual OI, put writing opportunities

---

## Flow 9 — Portfolio & Account

Requires a real broker login. Use Zerodha or Fyers.

**Start the web server first (for OAuth callback):**
```
trade
```
Then in the REPL:
```
web
```
- Browser opens at `http://localhost:8765`
- Click your broker, complete login

Then back in REPL:
```
profile
```
- Name, client ID, email, broker shown

```
funds
```
- Available cash, used margin, total balance

```
holdings
```
- Long-term delivery holdings with current value and P&L

```
positions
```
- Open intraday / F&O positions

```
orders
```
- Today's order book

```
portfolio
```
- Unified view: combines holdings + positions + funds + Greeks across all connected brokers

---

## Flow 10 — Dual Broker (Data + Execution)

Requires two brokers connected (e.g. Fyers + Zerodha).

```
trade
web
```
Login both brokers, then:

```
brokers
```
- Shows both brokers with roles (DATA / EXECUTION / BOTH)

```
data-broker fyers
exec-broker zerodha
```
- Confirm role assignment

```
quote RELIANCE
```
- Price comes from Fyers (data broker)

---

## Flow 11 — Paper Trading & Trade Execution

**Step 1 — Check current mode**
```
trade --no-broker
```
```
mode
```
- Should say `PAPER` (safe default)

**Step 2 — Paper buy (percentage-based sizing)**
```
buy INFY 5%
```
- Places paper order for 5% of trading capital
- Order confirmation shown with calculated quantity

**Step 3 — Paper buy (fixed quantity)**
```
buy TCS 10
```
- Confirms paper order for 10 shares

**Step 4 — Paper sell**
```
sell TCS 5
```
- Confirms paper sell for 5 shares

**Step 5 — Execute trade plan from analysis**
First run analysis:
```
analyze WIPRO
```
Then execute the neutral plan:
```
execute neutral
```
- Shows the paper order placed from the LLM-suggested trade plan

**Step 6 — Cancel orders**
```
cancel
```
- Interactive picker shows open orders
- Select one to cancel, confirm cancellation

---

## Flow 12 — Price & Technical Alerts

```
trade --no-broker
```

**Step 1 — Create price alert**
```
alert RELIANCE above 2800
```
- Confirms alert created with an ID like `alert-abc123`

**Step 2 — Create RSI alert**
```
alert NIFTY RSI above 70
```
- Confirms technical alert created

**Step 3 — Create conditional alert**
```
alert INFY above 1500 AND RSI above 65
```
- Confirms compound alert created

**Step 4 — List alerts**
```
alerts
```
- Shows all 3 active alerts with their IDs and conditions

**Step 5 — Remove an alert**
Copy one alert ID from the list, then:
```
alert remove <ID>
```
- Confirms removed; re-run `alerts` shows 2 remaining

---

## Flow 13 — Trade Memory & Reflection

```
trade --no-broker
```

**Step 1 — View memory**
```
memory
```
- Recent trade analyses (or "no trades recorded" if fresh start)

**Step 2 — Memory stats**
```
memory stats
```
- Win rate, avg return, best/worst trade, total trades recorded

**Step 3 — Symbol memory**
```
memory INFY
```
- Past analyses for INFY with timestamps

**Step 4 — Record an outcome**
After running `analyze INFY`, copy the trade ID from the memory:
```
memory
```
Copy the ID, then:
```
memory outcome <trade-id> WIN 4500
```
- Records outcome: WIN with P&L ₹4,500

**Step 5 — AI reflection**
```
memory reflect <trade-id>
```
- LLM generates a lesson like "RSI signal was strong; sector tailwind helped"
- Lesson stored to memory record

**Step 6 — Audit**
```
audit <trade-id>
```
- Full post-mortem: what the analysts said, what happened, what to learn

---

## Flow 14 — Advanced Analysis

```
trade --no-broker
```

**Step 1 — Multi-timeframe analysis**
```
mtf INFY
```
- 15m, 1h, 1D trend alignment; overall bias shown

**Step 2 — DCF valuation**
```
dcf RELIANCE
```
- Intrinsic value estimate with default growth/WACC assumptions

**Step 3 — DCF with custom parameters**
```
dcf INFY --growth 15 --wacc 12
```
- Re-runs DCF with 15% growth, 12% WACC

**Step 4 — Pair trading**
```
pairs RELIANCE TCS
```
- Correlation, spread stats, mean reversion z-score, signal (long/short/neutral)

**Step 5 — Patterns**
```
patterns
```
- Active India-specific chart patterns and sector rotation signals

**Step 6 — Events calendar**
```
events 7
```
- Events in next 7 days (earnings, splits, ex-dividend) + recommended strategies

**Step 7 — What-if scenario**
```
whatif nifty -3
```
- Shows portfolio impact if NIFTY falls 3% (P&L delta, Greeks impact)

---

## Flow 15 — Risk Management

```
trade --no-broker
```

**Step 1 — Risk report**
```
risk-report
```
- VaR (95%), CVaR, concentration by sector, portfolio volatility

**Step 2 — Portfolio Greeks**
```
greeks
```
- Net delta, theta, vega, gamma with colour-coded warnings

**Step 3 — Delta hedge suggestion**
```
delta-hedge
```
- Suggests trades to neutralize net delta (e.g. "Buy 2 NIFTY PE to reduce delta by 0.4")

**Step 4 — Delta hedge to target**
```
delta-hedge 0.5
```
- Suggests trades to reach delta = 0.5

**Step 5 — Roll expiring options**
```
roll-options
```
- Lists positions expiring within 3 DTE; suggests rolls with P&L comparison

**Step 6 — Model drift**
```
drift
```
- Analyst accuracy over last 30 trades; any models drifting below threshold flagged

---

## Flow 16 — Interactive Strategy Builder

```
trade --no-broker
```

**Step 1 — Start builder**
```
strategy new
```
- Prompts: "Describe your strategy in plain English"
- Type: `Buy when RSI is below 30 and price is above 200 MA. Exit when RSI crosses 60 or stop loss at 3%.`
- Builder asks clarifying questions (stop loss %, target %, position size)
- Answer each question

**Step 2 — Finalize strategy**
- After all questions answered, shows generated `StrategySpec` (entry rules, exit rules, code)
- Confirm to save

**Step 3 — List saved strategies**
```
strategy list
```
- New strategy appears in list

**Step 4 — Export strategy**
From strategy list, copy the strategy name, then:
```
strategy export <name> /tmp/my_strategy.json
```
- Creates JSON package at `/tmp/my_strategy.json`
- File contains `version`, `name`, `description`, `code` fields

**Step 5 — Import strategy**
```
strategy import /tmp/my_strategy.json
```
- Imports successfully; shows strategy name
- Appears in `strategy list`

---

## Flow 17 — AI Provider Switching

```
trade --no-broker
```

**Step 1 — Check current provider**
```
provider
```
- Shows provider name and model

**Step 2 — Switch provider (if you have multiple API keys set)**
```
provider gemini
```
- Confirms switched to Gemini

**Step 3 — Run a quick test**
```
quick RELIANCE
```
- Analysis runs on new provider

**Step 4 — Switch back**
```
provider anthropic
```

---

## Flow 18 — Settings Panel (macOS App)

Requires the macOS Electron app running with the sidecar.

**Step 1 — Start sidecar**
```bash
trade --no-broker &
```

**Step 2 — Start macOS app**
```bash
cd macos-app
npm run dev
```

**Step 3 — Open settings**
- Click the **gear icon** in the bottom-left of the sidebar
- Settings panel slides open

**Step 4 — Verify sections load**
- AI Provider section shows current provider + model
- Trading section shows capital and risk limits
- Notifications section shows telegram/webhook toggles
- Values are populated from the backend (`GET /skills/settings`)

**Step 5 — Change a setting**
- Change AI Provider model (e.g. from claude-3-5-sonnet to claude-3-7-sonnet)
- Click Save
- No error toast; value persists on reload

**Step 6 — Sensitive fields are masked**
- Any field containing a key/secret shows a green dot (●) but not the actual value
- The input shows `•••••••••` placeholder

---

## Flow 19 — PDF Export & Explain

```
trade --no-broker
```

**Step 1 — Run analysis**
```
analyze INFY
```

**Step 2 — Save as PDF**
```
save-pdf
```
- Saves the previous output as PDF to `~/Desktop/`
- Prints exact file path

**Step 3 — Explain in simple English**
```
explain
```
- Rephrases the analysis without jargon
- "In simple terms: INFY looks bullish because..."

**Step 4 — Explain and save**
```
explain-save
```
- Simplification + PDF saved in one step

**Step 5 — List exports**
```
exports
```
- Shows all saved PDFs with timestamps

**Step 6 — Clear old exports**
```
exports clear --older-than 30d
```
- Deletes PDFs older than 30 days; confirms count deleted

---

## Flow 20 — Web API (Sidecar Endpoints)

Start the sidecar first:
```bash
trade --no-broker &
# wait 2 seconds for it to start
```

Or from the REPL:
```
web
```

**Step 1 — Health check**
```bash
curl http://localhost:8765/health
# Expected: {"status": "ok"}
```

**Step 2 — API status**
```bash
curl http://localhost:8765/api/status
# Expected: JSON with broker auth flags
```

**Step 3 — Skill: quote**
```bash
curl -s -X POST http://localhost:8765/skills/quote \
  -H "Content-Type: application/json" \
  -d '{"symbol": "INFY", "exchange": "NSE"}' | python3 -m json.tool
# Expected: last, open, high, low, volume, change_pct
```

**Step 4 — Skill: quick analyze**
```bash
curl -s -X POST http://localhost:8765/skills/quick_analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TCS", "exchange": "NSE"}' | python3 -m json.tool
# Expected: signal (BUY/SELL/HOLD), reasoning
```

**Step 5 — Skill: settings GET**
```bash
curl -s http://localhost:8765/skills/settings | python3 -m json.tool
# Expected: ai_provider, capital, risk_per_trade, etc. (secrets masked)
```

**Step 6 — Skill: settings POST**
```bash
curl -s -X POST http://localhost:8765/skills/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "AI_PROVIDER", "value": "anthropic"}' | python3 -m json.tool
# Expected: {"ok": true}
```

**Step 7 — Skill: explain**
```bash
curl -s -X POST http://localhost:8765/skills/explain \
  -H "Content-Type: application/json" \
  -d '{"content": "INFY shows bullish divergence on RSI with strong MACD crossover above 200 EMA"}' \
  | python3 -m json.tool
# Expected: {"simplified": "INFY looks like a good buy because..."}
```

**Step 8 — Skill: backtest**
```bash
curl -s -X POST http://localhost:8765/skills/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "strategy": "rsi", "period": "1y", "fast": true}' \
  | python3 -m json.tool
# Expected: total_return, sharpe, max_drawdown, win_rate, trade_count
```

**Step 9 — Skill: chat**
```bash
curl -s -X POST http://localhost:8765/skills/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Should I buy INFY today?", "session_id": "test-session-1"}' \
  | python3 -m json.tool
# Expected: {"response": "..."}
```

**Step 10 — Skill: chat (multi-turn same session)**
```bash
curl -s -X POST http://localhost:8765/skills/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What about the risk?", "session_id": "test-session-1"}' \
  | python3 -m json.tool
# Expected: response references the previous INFY context
```

**Step 11 — OpenClaw manifest**
```bash
curl -s http://localhost:8765/.well-known/openclaw.json | python3 -m json.tool | head -40
# Expected: valid OpenClaw manifest with skills list
```

---

## Flow 21 — Multi-Session UI (macOS App)

Requires macOS app running.

**Step 1 — Default session**
- App opens with one session ("New Session" or similar)
- Type `analyze INFY` — analysis appears in current session

**Step 2 — Create new session**
- Press **Cmd+N** (macOS) or click **+ New** in the sidebar
- New empty session opens; previous session still visible in sidebar

**Step 3 — Session is independent**
- Type `quick TCS` in the new session
- Switch back to first session: INFY analysis is still there, not polluted

**Step 4 — Session auto-title**
- First session should now show title like "INFY Analysis" in sidebar
- Second session should show "TCS" or the first message text truncated

**Step 5 — Switch between sessions**
- Click session 1 in sidebar → INFY analysis shown
- Click session 2 → TCS result shown

---

## Flow 22 — Telegram Bot

Requires `TELEGRAM_BOT_TOKEN` set.

```
trade --no-broker
```

**Step 1 — Check bot status**
```
telegram
```
- Shows if bot is connected and listening

**Step 2 — Setup (first time)**
```
telegram setup
```
- Guided setup: asks for bot token, confirms connection

**Step 3 — Send from Telegram**
On your phone/Telegram, message the bot:
```
/quote RELIANCE
```
- Bot responds with live quote

```
/quick INFY
```
- Bot responds with BUY/SELL/HOLD

---

## Flow 23 — Docker Deployment

Requires Docker Desktop running.

```bash
cd docker
```

**Step 1 — Build image**
```bash
docker build -f Dockerfile -t india-trade-cli:test ..
# Should build successfully in 2 stages; no errors
```

**Step 2 — Health check**
```bash
docker run --rm -p 8765:8765 \
  -e NO_BROKER=1 \
  india-trade-cli:test &

sleep 5
curl http://localhost:8765/health
# Expected: {"status": "ok"}

docker stop $(docker ps -q --filter ancestor=india-trade-cli:test)
```

**Step 3 — Docker Compose (dev)**
```bash
cp .env.example .env
# Edit .env: set at minimum ANTHROPIC_API_KEY

docker compose up -d
curl http://localhost:8765/health
docker compose down
```

---

## Flow 24 — DMG Build Workflow (CI)

This validates the GitHub Actions workflow file (no actual CI run needed for local check).

```bash
# Validate YAML is parseable
python3 -c "import yaml; print(yaml.safe_load(open('.github/workflows/build-mac.yml').read())['name'])"
# Expected: Build macOS DMG

# Confirm key fields present
grep -c "workflow_dispatch" .github/workflows/build-mac.yml    # should be >= 1
grep -c "macos-latest"       .github/workflows/build-mac.yml   # should be >= 1
grep -c "CSC_IDENTITY_AUTO"  .github/workflows/build-mac.yml   # should be >= 1
grep -c "upload-artifact"    .github/workflows/build-mac.yml   # should be >= 1
grep -c "action-gh-release"  .github/workflows/build-mac.yml   # should be >= 1
```

All `grep -c` results should be `1` or more.

---

## Flow 25 — Full Automated Test Suite

Before merging / after any change:

```bash
# From repo root
pytest -q

# Expected: 1013 passed, 2 failed (pre-existing failures in test_p0_fixes.py::TestDataGapGuardrail)
# Any NEW failure = regression, investigate before merging

# Lint
ruff check .
ruff format --check .
# Expected: no output (all clean)
```

---

## Quick Smoke Test (< 5 minutes)

For a fast sanity check after any change, run just these:

```bash
trade --no-broker <<'EOF'
quote INFY
quick TCS
backtest RELIANCE rsi --fast
alert NIFTY above 20000
alerts
memory stats
provider
quit
EOF
```

All 7 commands should run without exceptions. That's the minimum bar for "nothing is catastrophically broken."

---

## Known Limitations (Not Bugs)

| Symptom | Reason | Action |
|---------|--------|--------|
| `flows`, `deals`, `earnings` return empty data | NSE website scraping may be rate-limited | Retry after 30s or use broker |
| `analyze` takes > 2 min | LLM provider slow or rate-limited | Switch provider or wait |
| `oi NIFTY` shows mock data | No broker with live options data connected | Connect Fyers or Zerodha |
| PDF export says "fpdf2 not installed" | Optional dependency not installed | `pip install fpdf2` |
| Telegram commands don't work | Bot not configured or not running | `telegram setup` |
| DCF shows "N/A" for some fields | Financial data not available via yfinance for that symbol | Try a major NIFTY50 stock |
