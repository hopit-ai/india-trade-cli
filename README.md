# India Trade CLI

AI-powered multi-agent stock & options analysis platform for Indian markets (NSE/BSE/NFO).

> **Philosophy:** Every trade must be justified. Analyze first, debate second, execute third.

---

## Architecture

```
analyze RELIANCE
        |
  [7 Analyst Agents]  ← pure Python, parallel
  Technical | Fundamental | Options | News(LLM) | Sentiment | Sector Rotation | Risk Manager
        |
  [Analyst Scorecard]  ← weighted composite score + conflict detection
        |
  [Multi-Round Debate]  ← 5 LLM calls
  Bull R1 → Bear R1 → Bull Rebuttal → Bear Rebuttal → Facilitator
        |
  [Fund Manager Synthesis]  ← 1 LLM call
  Verdict: BUY/SELL/HOLD + confidence + rationale
        |
  [Risk Management Team]  ← pure Python
  Aggressive | Neutral | Conservative trade plans
        |
  [Trade Plan]
  Entry orders, stop-loss, targets, position sizing, scaling logic
```

**Standard mode: 8 LLM calls.** Deep mode (`deep-analyze`): 11 LLM calls — every analyst is LLM-powered.

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/ArchieIndian/india-trade-cli.git
cd india-trade-cli
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run

```bash
python -m app.main
```

First run prompts you to:
1. Choose a broker (or Demo for mock data)
2. Choose an AI provider

**No broker needed for analysis** — yfinance provides free Indian market data automatically.

---

## Broker Setup

### Fyers (Recommended — free, real-time data)

Fyers is the primary supported broker with full API integration including WebSocket for real-time quotes.

1. **Create account** at [fyers.in](https://fyers.in)
2. **Create API app** at [myapi.fyers.in](https://myapi.fyers.in)
   - App Name: anything (e.g. "TradeCLI")
   - Redirect URL: `http://127.0.0.1:8765/fyers/callback` (must be exact)
3. **Get credentials**: App ID (format `XXXX-100`) + Secret ID
4. **Login in the platform**:
   ```
   python -m app.main
   > Choose: [5] Fyers
   > Enter App ID: HFT99GVTDY-100
   > Enter Secret Key: (paste, won't show — that's normal for secrets)
   ```
5. Browser opens → login with Fyers credentials → copy `auth_code` from redirect URL → paste back

Token is saved for 12 hours. Next login auto-resumes if token is valid.

**WebSocket**: Auto-connects on login for real-time quotes (instant instead of 1-3s REST calls).

### Other Brokers (WIP)

Basic implementations exist for these brokers but are not fully tested. Fyers is the recommended primary broker:

| Broker | Status | Notes |
|--------|--------|-------|
| **Fyers** | **Fully supported** | Free API, WebSocket, options chain |
| Zerodha | Basic implementation | Requires Kite Connect (paid) |
| Angel One | Basic implementation | Free SmartAPI, TOTP login |
| Upstox | Basic implementation | Free API, OAuth redirect |
| Groww | Basic implementation | No historical data API |
| Mock/Demo | Fully supported | Synthetic data, no login needed |

### No broker needed

The platform works without any broker login:

```bash
python -m app.main --no-broker
```

- **yfinance** provides free real NSE/BSE data (~15 min delayed)
- All analysis, backtesting, multi-timeframe, and AI features work with real data
- Account commands (funds, holdings) show demo data with a warning
- Options data uses NSE public API when available
- Connect a broker later via `login` command in the REPL

---

## AI Provider Setup

Choose one AI provider for the analysis brain:

| Provider | Cost | Setup |
|----------|------|-------|
| **Claude subscription** | Free (your plan) | Install `claude` CLI: `npm i -g @anthropic-ai/claude-code` → `claude login` |
| **Gemini** | Free tier available | Get key at [aistudio.google.com](https://aistudio.google.com) |
| Claude API | Pay per token | Key from [console.anthropic.com](https://console.anthropic.com) |
| OpenAI GPT-4o | Pay per token | Key from [platform.openai.com](https://platform.openai.com) |

Switch anytime: `provider gemini` or `provider claude_subscription`

---

## Optional: NewsAPI Setup

Provides better stock-specific news. Free tier (100 requests/day). Without it, RSS feeds (ET Markets, MoneyControl) are used automatically.

1. Get free key at [newsapi.org](https://newsapi.org)
2. Save it:
   ```
   > credentials setup
   > Enter NEWSAPI_KEY: 7665663ab8c04212ac8c26321a9d5cae
   ```
3. Toggle: `NEWSAPI_ENABLED=0` in env to disable, `1` to enable (default)

---

## Optional: Telegram Bot

Push alerts, quotes, and briefs to your phone via Telegram.

1. Open Telegram → search `@BotFather` → send `/newbot` → get token
2. Save token: `credentials setup` → enter `TELEGRAM_BOT_TOKEN`
3. Start bot: `telegram` command in REPL (runs in background)
4. Send `/start` to your bot on Telegram

**13 bot commands**: `/quote`, `/analyze`, `/brief`, `/flows`, `/earnings`, `/events`, `/macro`, `/alert`, `/alerts`, `/memory`, `/pnl`, `/help`

Alerts auto-push to Telegram when triggered.

---

## All CLI Commands

### Core Analysis
```
analyze RELIANCE                   Full multi-agent analysis (8 LLM calls)
analyze RELIANCE --explain-save    Analyze + explain simply + save PDF
deep-analyze RELIANCE              Deep mode — every analyst is LLM (11 calls)
ai <message>                       Chat with AI (freeform questions)
morning-brief                      Daily market context + AI narrative
mtf RELIANCE                       Multi-timeframe analysis (weekly/daily/hourly)
```

### Market Data
```
earnings                 Quarterly results calendar (NIFTY 50)
earnings RELIANCE TCS    Earnings for specific stocks
flows                    FII/DII flow intelligence with signals
events                   Event-driven strategy recommendations
patterns                 Active India-specific market patterns
macro                    USD/INR, crude, gold, US 10Y snapshot
macro RELIANCE           Macro impact on a specific stock
```

### Backtesting & Simulation
```
backtest RELIANCE rsi              RSI overbought/oversold
backtest RELIANCE ma 20 50         EMA crossover
backtest RELIANCE macd             MACD signal crossover
backtest RELIANCE bb               Bollinger Bands
walkforward RELIANCE rsi           Walk-forward test (rolling windows)
whatif nifty -3                    What if NIFTY drops 3%? (uses real beta)
whatif RELIANCE -10                What if RELIANCE drops 10%?
whatif RELIANCE -5 HDFCBANK 3      Custom multi-stock scenario
```

### Risk & Portfolio
```
risk-report              VaR/CVaR portfolio risk analysis
greeks                   Portfolio Greeks (net Delta, Theta, Vega)
pairs                    Pair trading opportunities scan
pairs HDFCBANK ICICIBANK Analyze a specific pair
```

### Paper Trading
```
paper-execute                      Execute last trade plan (neutral risk)
paper-execute aggressive           Execute aggressive risk plan
paper-execute conservative         Execute conservative risk plan
```

### Memory & Learning
```
memory                   Recent trade analyses
memory stats             Performance statistics
memory RELIANCE          Past analyses for a symbol
memory outcome ID WIN 1250   Record trade outcome
profile                  Your personal trading style profile
drift                    Model drift detection
audit <ID>               Post-mortem analysis of a trade
```

### Alerts
```
alert RELIANCE above 2800                     Price alert
alert NIFTY RSI above 70                      Technical alert
alert RELIANCE above 2800 AND RSI above 70    Conditional (AND logic)
alert list / alerts                           List active alerts
alert remove <ID>                             Remove an alert
```

### Portfolio & Trading
```
funds                    Available cash and margin
holdings                 Long-term delivery holdings
positions                Open intraday/F&O positions
orders                   Today's orders and status
portfolio                Unified view — all brokers
```

### Output & Export
```
save-pdf                           Save previous output as PDF
explain                            Explain previous output simply
explain-save                       Explain + save as PDF
--pdf                              Flag: append to any command
--explain                          Flag: append to any command
--explain-save                     Flag: explain + PDF in one shot
```

### Account & Config
```
login                    Connect to a broker
connect                  Add a second broker
disconnect               Remove a secondary broker
brokers                  List all connected brokers
logout                   Disconnect all brokers
profile                  Your trading style profile
provider                 Show/switch AI provider
telegram                 Start Telegram bot (background)
clear                    Reset AI conversation history
credentials              Manage API keys
```

---

## Project Structure

```
india-trade-cli/
├── agent/                    # AI layer
│   ├── core.py               # TradingAgent + 6 LLM providers
│   ├── multi_agent.py         # 7 analysts, scorecard, debate, synthesis
│   ├── deep_agent.py          # Full LLM mode (11 calls)
│   ├── tools.py               # 45+ tool definitions for LLM function calling
│   └── prompts.py             # System prompt + command templates
├── brokers/                  # Broker integrations
│   ├── base.py                # Unified BrokerAPI abstract interface
│   ├── fyers.py               # Fyers API v3 (official SDK) ← primary
│   ├── zerodha.py             # Zerodha Kite Connect (WIP)
│   ├── upstox.py              # Upstox API v2 (WIP)
│   ├── angelone.py            # Angel One SmartAPI (WIP)
│   ├── groww.py               # Groww Partner API (WIP)
│   ├── mock.py                # Mock broker (paper trading)
│   └── session.py             # Multi-broker session manager
├── market/                   # Market data
│   ├── quotes.py              # Quotes: WebSocket → broker REST → yfinance
│   ├── websocket.py           # Fyers WebSocket for real-time ticks
│   ├── history.py             # Historical OHLCV: broker → yfinance → mock
│   ├── options.py             # NSE options chain
│   ├── indices.py             # NIFTY 50, BANKNIFTY, India VIX, sectors
│   ├── news.py                # NewsAPI + RSS feeds (toggle-able)
│   ├── events.py              # Earnings calendar, RBI, expiry dates
│   ├── sentiment.py           # FII/DII data + market breadth
│   ├── earnings.py            # Earnings agent + surprise prediction
│   ├── flow_intel.py          # FII/DII flow intelligence + signals
│   ├── macro.py               # Currency/commodity linkage analysis
│   └── yfinance_provider.py   # Free NSE/BSE data via Yahoo Finance
├── analysis/                 # Analysis engines
│   ├── technical.py           # RSI, MACD, EMAs, Bollinger, ATR, pivots
│   ├── fundamental.py         # PE, ROE, ROCE from Screener.in
│   ├── options.py             # Greeks, payoff, iron condor, butterfly, calendar
│   └── multi_timeframe.py     # Weekly/daily/hourly confluence analysis
├── engine/                   # Trading logic
│   ├── trader.py              # Trader Agent + 3 risk personas
│   ├── backtest.py            # Backtester + walk-forward testing
│   ├── simulator.py           # What-if with real beta
│   ├── memory.py              # Trade memory (situation-outcome pairs)
│   ├── patterns.py            # India-specific market patterns
│   ├── event_strategies.py    # Event-driven strategy recommendations
│   ├── risk_metrics.py        # VaR, CVaR, correlation, HHI
│   ├── drift.py               # Model drift detection
│   ├── pairs.py               # Pair trading / relative value
│   ├── audit.py               # Decision audit trail
│   ├── profile.py             # Personal trading style profile
│   ├── alerts.py              # Price + technical + conditional alerts + real-time
│   ├── paper.py               # Paper trading engine
│   ├── paper_execute.py       # Execute trade plans in paper mode
│   ├── output.py              # PDF export + simple explainer (--explain-save)
│   ├── portfolio.py           # Portfolio tracker + aggregated Greeks
│   └── strategy.py            # Strategy recommendation engine
├── bot/                      # Telegram bot
│   └── telegram_bot.py       # 13 commands + alert push notifications
├── app/                      # Application layer
│   ├── main.py                # Entry point
│   ├── repl.py                # Command REPL (35+ commands, tab-complete)
│   └── commands/              # Command handlers
├── config/                   # Configuration
│   └── credentials.py        # OS keychain credential management
├── web/                      # Web API (FastAPI)
│   └── api.py                # REST + WebSocket endpoints
└── requirements.txt
```

---

## Data Flow Priority

Quotes and prices are fetched in this priority order:

1. **WebSocket** (instant) — real-time ticks from Fyers, auto-connected on login
2. **Broker REST API** (1-3s) — fallback when no WebSocket tick cached
3. **yfinance** (~15 min delayed) — free fallback when no broker logged in
4. **Mock data** (synthetic) — last resort, random walk

---

## Position Sizing

The Trader Agent calculates position size using this formula:

```
Max Risk = Capital × Risk% × VIX Adjustment
Shares   = Max Risk / Stop-Loss Distance (per share)
```

Example (TCS at ₹2,360, VIX > 20):
```
Capital     = ₹200,000 (TOTAL_CAPITAL env var)
Risk/trade  = 2% (DEFAULT_RISK_PCT env var)
VIX factor  = 0.5 (VIX > 20 → halve position size for safety)
Max risk    = ₹200,000 × 2% × 0.5 = ₹2,000
SL distance = 1.5 × ATR ≈ ₹180/share
Shares      = ₹2,000 / ₹180 = 11 shares
Deployed    = 11 × ₹2,360 = ₹25,960 (13% of capital)
```

VIX adjustment (automatic):
| VIX Level | Position Size |
|-----------|--------------|
| < 15 | 100% (normal) |
| 15-20 | 85% |
| 20-25 | 65% |
| > 25 | 50% (halved) |

To change defaults, set in `.env` or shell:
```bash
export TOTAL_CAPITAL=500000    # your actual trading capital in INR
export DEFAULT_RISK_PCT=2      # max risk per trade (%)
```

---

## Environment Variables

```bash
# AI Provider (choose one)
AI_PROVIDER=claude_subscription    # or: anthropic, openai, gemini
ANTHROPIC_API_KEY=sk-ant-...       # only if using anthropic provider
OPENAI_API_KEY=sk-...              # only if using openai provider
GEMINI_API_KEY=AIza...             # only if using gemini provider

# Trading Capital & Risk
TOTAL_CAPITAL=200000               # your trading capital in INR
DEFAULT_RISK_PCT=2                 # max risk per trade (%)
TRADING_MODE=PAPER                 # PAPER or LIVE

# News (optional)
NEWSAPI_KEY=...                    # free at newsapi.org
NEWSAPI_ENABLED=1                  # set to 0 to disable

# Telegram (optional)
TELEGRAM_BOT_TOKEN=...             # from @BotFather
```

---

## Roadmap

### Completed (34/43 issues closed)
- [x] 5-phase competitive roadmap (all phases shipped)
- [x] 7 analyst agents + weighted scorecard (excludes UNAVAILABLE analysts)
- [x] Multi-round debate with facilitator (2 rounds + summary)
- [x] Trader Agent + 3 risk personas (aggressive/neutral/conservative)
- [x] Trade memory + India pattern knowledge base
- [x] Strategy backtesting + walk-forward testing
- [x] What-if simulator with real stock beta
- [x] Earnings agent + surprise prediction
- [x] FII/DII flow intelligence + divergence detection
- [x] Event-driven strategies (expiry, RBI, budget, earnings)
- [x] Advanced options (iron condor, butterfly, calendar, ratio, diagonal)
- [x] Currency/commodity macro linkages (USD/INR, crude, gold, US 10Y)
- [x] VaR/CVaR portfolio risk + correlation matrix + HHI
- [x] Model drift detection + decision audit trail
- [x] Pair trading with mean reversion signals (12 Indian pairs)
- [x] Personal trading style profile
- [x] Full LLM deep mode (11 calls)
- [x] Telegram bot (13 commands + alert push)
- [x] Fyers WebSocket for real-time quotes
- [x] Fyers broker rewrite using official SDK
- [x] Multi-timeframe analysis (weekly/daily/hourly confluence)
- [x] Paper trading execution with auto-alert creation
- [x] PDF export + simple explainer (--pdf, --explain, --explain-save flags)
- [x] Post-processing commands (save-pdf, explain, explain-save)
- [x] Fast path for data queries (skip LLM for simple price lookups)
- [x] --no-broker mode with yfinance passthrough (real data, no fake prices)
- [x] Categorized help command (8 Rich panels)
- [x] Real-time alert evaluation via WebSocket ticks
- [x] 3-channel alert notifications (terminal + macOS desktop + Telegram)

### Open Issues
- [ ] #18 SEBI compliance layer (margin validation, tax harvesting)
- [ ] #22 OpenClaw agent integration
- [ ] #23 Telegram bot token setup + testing
- [ ] #24 Web UI (FastAPI backend)
- [ ] #25 Textual TUI (split-panel terminal)
- [ ] #26 Real-time portfolio dashboard
- [ ] #27 Broker order placement flow with confirmation
- [ ] #28 End-to-end test suite
- [ ] #29 Place F&O orders via broker API
- [ ] #30 Options strategy execution (multi-leg orders)
- [ ] #31 Options-specific backtesting
- [ ] #32 Greeks-based position management (delta-hedge, roll)
- [ ] #33 Options scanner (high IV, unusual OI)
- [ ] #34 Expiry day tools (gamma scalping, last-hour strategies)

---

## License

Private. All rights reserved.
