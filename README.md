# India Trade CLI

**Open-source AI trading assistant for Indian stock markets (NSE / BSE / NFO).** Multi-agent stock analysis, quantitative strategy builder, Telegram alerts, paper trading, and OpenClaw HTTP skills — all from the terminal.

> **Philosophy:** Every trade must be justified. Analyze first, debate second, execute third.

[![CI](https://github.com/hopit-ai/india-trade-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/hopit-ai/india-trade-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is India Trade CLI?

India Trade CLI is a free, open-source quantitative trading platform for Indian equity and derivatives markets. It runs **seven AI analyst agents** on any NSE or BSE listed stock — Technical, Fundamental, Options, News & Macro, Sentiment, Sector Rotation, and Risk Manager — forces them into a structured bull-vs-bear debate, and produces a fund-manager-grade synthesis with concrete trade plans across three risk profiles.

Beyond single-stock analysis, the platform ships:

- **AI-guided strategy builder** — describe a strategy in plain English (RSI mean reversion, EMA crossover, MACD momentum, pairs spread trading), the AI interviews you, generates Python code, backtests it on NSE history, and saves it locally.
- **Telegram trading bot** — 14 commands for live quotes, full AI analysis, FII/DII flows, earnings calendar, and price alerts pushed directly to your phone.
- **Paper trading engine** — execute AI-recommended trade plans (aggressive / neutral / conservative) without real money.
- **OpenClaw HTTP skills** — every capability exposed as a discoverable REST endpoint so any OpenClaw agent can call Indian market data or trigger multi-agent analysis over HTTP.

**Supports:** Gemini (free), Claude (subscription or API), OpenAI, Ollama (local), and any OpenAI-compatible endpoint (OpenRouter, Groq, etc.).
**Brokers:** Fyers (fully supported, free real-time API), Mock/Demo mode, Zerodha / Angel One / Upstox / Groww (WIP).

---

## How it works

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
  [Risk Management]  ← pure Python
  Aggressive | Neutral | Conservative trade plans
        |
  [Trade Plan]
  Entry orders, stop-loss, targets, position sizing, scaling logic
```

**Standard mode:** 8 LLM calls. **Deep mode** (`deep-analyze`): 11 LLM calls with every analyst AI-powered.

---

## Quick Start — Zero to First Analysis in 5 Minutes

### Prerequisites

- **Python 3.11+** (3.11, 3.12, and 3.13 tested in CI)

### Step 1: Install

```bash
git clone https://github.com/hopit-ai/india-trade-cli.git
cd india-trade-cli
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### Step 2: Set up an AI provider

Pick **one** of these options:

**Option A — Gemini (free)**
1. Go to [aistudio.google.com](https://aistudio.google.com) and sign in with Google
2. Click **Get API Key** → **Create API key**
3. Copy the key (starts with `AIza...`)

**Option B — Claude (if you have a Pro/Max subscription)**
1. Install the Claude CLI: `npm install -g @anthropic-ai/claude-code`
2. Run `claude login` and authenticate in your browser
3. That's it — no API key needed, the platform calls the CLI directly

### Step 3: Get free market data (Fyers)

1. Create a free account at [fyers.in](https://fyers.in)
2. Go to [myapi.fyers.in](https://myapi.fyers.in) → **Create App**
   - Redirect URL: `http://127.0.0.1:8765/fyers/callback` (must be exact)
3. Note the **App ID** and **Secret Key**
4. When you run `trade` and choose Fyers, enter these credentials. A browser window opens for Fyers login. After login, the browser redirects to a URL like:
   ```
   http://127.0.0.1:8765/fyers/callback?auth_code=eyJ0...&state=...
   ```
   Copy the `auth_code` value and paste it into the terminal when prompted.

### Step 4: Get news headlines (optional)

1. Sign up at [newsapi.org](https://newsapi.org) (free for development)
2. Copy your API key

### Step 5: Run it

```bash
trade
```

First run walks you through broker, AI provider, and NewsAPI setup. You're in the REPL. Try:

```
> analyze RELIANCE
```

This runs 7 analyst agents, a bull-vs-bear debate, and produces a fund-manager synthesis with trade plans across 3 risk profiles.

```
> deep-analyze INFY        # full LLM mode (11 AI calls)
> morning-brief            # daily market overview
> deals                    # today's bulk/block deals
> quote TCS                # live quote
```

### No-broker mode (quick start without Fyers)

```bash
trade --no-broker
```

Uses yfinance for real NSE/BSE data (~15 min delayed). Technical, fundamental, sentiment, and sector analysis all work. Options chain data requires a broker connection (Fyers recommended).

---

## Supported AI Providers

| Provider | Cost | Setup |
|----------|------|-------|
| **Gemini** | Free tier available | Get key at [aistudio.google.com](https://aistudio.google.com) |
| **Claude (subscription)** | Free with Pro/Max plan | Install CLI: `npm i -g @anthropic-ai/claude-code` then `claude login` |
| **Claude API** | Pay per token | Key from [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI API** | Pay per token | Key from [platform.openai.com](https://platform.openai.com) |
| **Any OpenAI-compatible** | Varies | OpenRouter, Groq, Together, LM Studio, vLLM |
| **Ollama (local)** | Free | Run models locally: `ollama pull llama3.1` |

**Switch anytime:** `provider gemini` or `provider claude_subscription`

### Custom OpenAI-compatible endpoint

For providers like OpenRouter, Groq, etc.:

```bash
# In .env
AI_PROVIDER=openai
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-...
OPENAI_MODEL=anthropic/claude-sonnet-4
```

Or interactively: `credentials setup` → AI Provider → **Custom (OpenAI-compatible)**

API keys are stored in your OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Locker) via the `keyring` library. Broker session tokens are cached under `~/.trading_platform/` and deleted on logout.

---

## Supported Brokers

| Broker | Status | Notes |
|--------|--------|-------|
| **Fyers** | **Fully supported** | Free API, real-time WebSocket, options chain |
| **Mock/Demo** | **Fully supported** | Synthetic data, no login needed |
| Zerodha | WIP | Requires Kite Connect subscription ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)) |
| Angel One | WIP | Free SmartAPI, TOTP login ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)) |
| Upstox | WIP | Free API, OAuth ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)) |
| Groww | WIP | No historical data API ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)) |

> Broker integrations beyond Fyers are work-in-progress. See [#80](https://github.com/hopit-ai/india-trade-cli/issues/80). Contributions welcome.

### Fyers Setup (recommended — free, real-time NSE/BSE data)

1. Create account at [fyers.in](https://fyers.in)
2. Create API app at [myapi.fyers.in](https://myapi.fyers.in) — Redirect URL: `http://127.0.0.1:8765/fyers/callback`
3. Run `trade` → `login` → choose Fyers → enter App ID and Secret Key
4. Browser opens for OAuth login. Token saved for 12 hours. WebSocket auto-connects for real-time quotes.

### NewsAPI (optional but recommended)

A free [NewsAPI](https://newsapi.org) key significantly improves `morning-brief` and news-driven analysis. Free tier: 100 requests/day.

```bash
NEWSAPI_KEY=your_key_here
NEWSAPI_ENABLED=1
```

---

## Telegram Trading Bot for Indian Markets

Send commands from your phone — receive full AI analysis, live NSE/BSE quotes, FII/DII flow data, earnings events, and price alerts with automatic push notifications.

```
trade
> telegram setup
```

The wizard walks you through creating a bot via @BotFather and connecting your chat.

**14 bot commands:** `/quote`, `/analyze`, `/deepanalyze`, `/brief`, `/flows`, `/earnings`, `/events`, `/macro`, `/alert`, `/alerts`, `/memory`, `/pnl`, `/help`

Alerts auto-push to Telegram when triggered. The REPL shows a live status badge when bot commands are running.

---

## OpenClaw Integration — HTTP Skills for Indian Market Data

Expose every capability as **discoverable HTTP skill endpoints** that any OpenClaw agent can call — no CLI installation needed on the agent side.

```
OpenClaw Agent
    │  GET /.well-known/openclaw.json   ← discover available skills
    │  POST /skills/analyze             ← call a skill
    ▼
india-trade-cli Skill Server (FastAPI)
    │
    ▼ (existing Python modules, unchanged)
agent/ market/ engine/ analysis/
```

### Start the skill server

```bash
uvicorn web.api:app --host 127.0.0.1 --port 8765
```

Or from the REPL: `web`

> **Security:** The skills server has no authentication. Keep it bound to `127.0.0.1` (localhost only). Do not expose on `0.0.0.0` without adding a reverse proxy with authentication.

### Skill discovery

```bash
curl http://localhost:8765/.well-known/openclaw.json
```

Returns a manifest with all 17 skills, their JSON input schemas, and descriptions. Any OpenClaw agent reads this URL to know what's available.

### Available skills

| Skill | Input | Speed |
|-------|-------|-------|
| `quote` | `{ "symbol": "RELIANCE" }` | Instant |
| `options_chain` | `{ "symbol": "NIFTY" }` | Instant |
| `flows` | `{}` | Instant |
| `earnings` | `{ "symbols": ["TCS"] }` | Instant |
| `macro` | `{}` | Instant |
| `deals` | `{ "symbol": "INFY" }` | Instant |
| `morning_brief` | `{}` | ~2s |
| `backtest` | `{ "symbol": "INFY", "strategy": "rsi" }` | ~5s |
| `pairs` | `{ "stock_a": "HDFCBANK", "stock_b": "ICICIBANK" }` | ~5s |
| `chat` | `{ "message": "Analyse RELIANCE", "session_id": "abc" }` | ~5s |
| `chat/reset` | `{ "session_id": "abc" }` | Instant |
| `analyze` | `{ "symbol": "RELIANCE" }` | 30–90s (8 LLM calls) |
| `deep_analyze` | `{ "symbol": "RELIANCE" }` | 3–8 min (11 LLM calls) |
| `alerts/add` | `{ "symbol": "RELIANCE", "condition": "ABOVE", "threshold": 2800 }` | Instant |
| `alerts/list` | `{}` | Instant |
| `alerts/remove` | `{ "alert_id": "abc12345" }` | Instant |
| `alerts/check` | `{}` | ~2s |

All endpoints return `{ "status": "ok", "data": { ... } }` on success.

### Example calls

```bash
# Live NSE quote
curl -X POST http://localhost:8765/skills/quote \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE"}'

# Full multi-agent analysis
curl -X POST http://localhost:8765/skills/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE"}'

# Multi-turn chat with the trading agent
curl -X POST http://localhost:8765/skills/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the RSI on NIFTY?", "session_id": "my-agent"}'
```

### Webhook alerts

Register a callback URL — the server POSTs to it the moment an alert fires:

```bash
curl -X POST http://localhost:8765/skills/alerts/add \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "condition": "ABOVE",
    "threshold": 2800,
    "webhook_url": "https://my-agent.example.com/on-alert"
  }'
```

Payload on trigger:
```json
{
  "event": "alert_triggered",
  "alert_id": "abc12345",
  "symbol": "RELIANCE",
  "description": "RELIANCE price ABOVE ₹2,800.00",
  "triggered_at": "2026-04-03T11:00:00",
  "ltp": 2815.5
}
```

See [#83](https://github.com/hopit-ai/india-trade-cli/issues/83) for the full integration roadmap (manifest registration, API key auth, Docker image).

---

## All CLI Commands

### Analysis (AI-powered)
| Command | Description |
|---------|-------------|
| `analyze RELIANCE` | Multi-agent analysis — 7 analysts + debate + 3 trade plans |
| `deep-analyze RELIANCE` | Full LLM mode (11 calls, every analyst uses AI) |
| `ai <message>` | Chat with the trading agent — follow-ups keep context, `clear` to reset |
| `morning-brief` | Daily NSE/BSE market context + AI narrative |
| `mtf RELIANCE` | Multi-timeframe analysis (weekly / daily / hourly confluence) |

### Quantitative Strategy Builder

> **Warning:** The strategy builder executes AI-generated Python code on your machine. Only run strategies from sources you trust. Never copy-paste strategy code from untrusted sources into `~/.trading_platform/strategies/`.

| Command | Description |
|---------|-------------|
| `strategy new` | Describe a strategy in plain English — AI interviews you, generates code, backtests |
| `strategy new --simple` | Same but explained without jargon |
| `strategy list` | List all saved strategies with backtest stats |
| `strategy backtest <name> --period 2y` | Re-backtest a saved strategy |
| `strategy run <name> RELIANCE --paper` | Generate latest signal, paper trade if BUY |
| `strategy show <name>` | View generated Python code |
| `strategy delete <name>` | Remove a saved strategy |

Supports single-symbol strategies (RSI, MACD, EMA crossover, Bollinger Bands) and multi-symbol pairs strategies (z-score spread trading with both legs tracked). The AI gives data-backed recommendations for each parameter.

### Market Data
| Command | Description |
|---------|-------------|
| `earnings` | Quarterly results calendar (NIFTY 50) |
| `earnings RELIANCE TCS` | Earnings for specific stocks |
| `flows` | FII/DII flow intelligence with buy/sell signals |
| `events` | Event-driven strategy recommendations |
| `patterns` | Active India-specific market patterns |
| `macro` | USD/INR, crude oil, gold, US 10Y snapshot |
| `macro RELIANCE` | Macro impact analysis for a specific stock |

### Backtesting & Simulation
| Command | Description |
|---------|-------------|
| `backtest RELIANCE rsi` | RSI overbought/oversold strategy |
| `backtest RELIANCE ma 20 50` | EMA crossover |
| `backtest RELIANCE macd` | MACD signal crossover |
| `backtest RELIANCE bb` | Bollinger Bands mean reversion |
| `walkforward RELIANCE rsi` | Walk-forward test (rolling windows) |
| `whatif nifty -3` | What if NIFTY drops 3%? (uses real stock beta) |

### Risk & Portfolio
| Command | Description |
|---------|-------------|
| `risk-report` | VaR / CVaR portfolio risk analysis |
| `greeks` | Portfolio Greeks — net Delta, Theta, Vega |
| `pairs` | Scan for pair trading opportunities |
| `pairs HDFCBANK ICICIBANK` | Analyze a specific stock pair |

### Paper Trading
| Command | Description |
|---------|-------------|
| `paper-execute` | Execute last trade plan (neutral risk) |
| `paper-execute aggressive` | Execute aggressive plan |
| `paper-execute conservative` | Execute conservative plan |

### Trade Memory & Learning
| Command | Description |
|---------|-------------|
| `memory` | Recent trade analyses |
| `memory stats` | Win rate, P&L, and performance statistics |
| `memory RELIANCE` | Past analyses for a specific symbol |
| `memory outcome ID WIN 1250` | Record trade outcome |
| `profile` | Your personal trading style profile |
| `drift` | Model drift detection — is the AI losing edge? |
| `audit <ID>` | Post-mortem analysis of a specific trade |

### Alerts
| Command | Description |
|---------|-------------|
| `alert RELIANCE above 2800` | Simple price alert |
| `alert NIFTY RSI above 70` | Technical indicator alert |
| `alert RELIANCE above 2800 AND RSI above 70` | Conditional alert |
| `alerts` | List all active alerts |
| `alert remove <ID>` | Remove an alert |

### Portfolio & Broker
| Command | Description |
|---------|-------------|
| `funds` | Available cash and margin |
| `holdings` | Long-term delivery holdings |
| `positions` | Open intraday / F&O positions |
| `orders` | Today's orders and status |
| `portfolio` | Unified view across all connected brokers |

### Output & Export
| Command | Description |
|---------|-------------|
| `save-pdf` | Save previous output as PDF |
| `explain` | Explain previous output in plain English |
| `--pdf` | Flag: append to any command |
| `--explain` | Flag: append to any command |
| `--explain-save` | Explain + PDF in one shot |

### Account & Config
| Command | Description |
|---------|-------------|
| `login` | Connect to a broker |
| `connect` | Add a second broker (multi-broker mode) |
| `logout` | Disconnect all brokers |
| `provider` | Show / switch AI provider |
| `telegram` / `telegram setup` | Start bot / run guided setup |
| `credentials` | Manage API keys |

---

## Configuration

### Environment Variables

```bash
# AI Provider (choose one)
AI_PROVIDER=gemini              # or: anthropic, openai, claude_subscription
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Trading Capital & Risk
TOTAL_CAPITAL=200000            # your trading capital in INR
DEFAULT_RISK_PCT=2              # max risk per trade (%)
TRADING_MODE=PAPER              # PAPER or LIVE

# News (optional)
NEWSAPI_KEY=...
NEWSAPI_ENABLED=1

# Telegram (optional)
TELEGRAM_BOT_TOKEN=...          # from @BotFather
```

### Position Sizing

```
Max Risk = Capital × Risk% × VIX Adjustment
Shares   = Max Risk / Stop-Loss Distance (per share)
```

VIX-based auto-adjustment:

| VIX Level | Position Size |
|-----------|--------------|
| < 15 | 100% (normal) |
| 15–20 | 85% |
| 20–25 | 65% |
| > 25 | 50% (halved) |

### Data Flow Priority

| Source | Latency | When used |
|--------|---------|-----------|
| Fyers WebSocket | Real-time | Primary (when broker connected) |
| Broker REST API | 1–3s | Fallback |
| yfinance | ~15 min delayed | No broker login |
| Mock data | Synthetic | Demo mode |

---

## Project Structure

```
india-trade-cli/
|-- agent/                    # AI layer
|   |-- core.py               # TradingAgent + 6 LLM providers
|   |-- multi_agent.py        # 7 analysts, scorecard, debate, synthesis
|   |-- deep_agent.py         # Full LLM mode (11 calls)
|   |-- tools.py              # 45+ tool definitions for LLM function calling
|   +-- prompts.py            # System prompt + command templates
|-- brokers/                  # Broker integrations
|   |-- base.py               # Unified BrokerAPI abstract interface
|   |-- fyers.py              # Fyers API v3 (official SDK)
|   |-- zerodha.py            # Zerodha Kite Connect
|   |-- upstox.py             # Upstox API v2
|   |-- angelone.py           # Angel One SmartAPI
|   |-- groww.py              # Groww Partner API
|   |-- mock.py               # Mock broker (paper trading)
|   +-- session.py            # Multi-broker session manager
|-- market/                   # Market data
|   |-- quotes.py             # Quotes: WebSocket → broker REST → yfinance
|   |-- websocket.py          # Fyers WebSocket for real-time ticks
|   |-- history.py            # Historical OHLCV
|   |-- options.py            # NSE options chain
|   |-- indices.py            # NIFTY 50, BANKNIFTY, India VIX, sectors
|   |-- news.py               # NewsAPI + RSS feeds
|   |-- events.py             # Earnings calendar, RBI policy, expiry dates
|   |-- sentiment.py          # FII/DII data + market breadth
|   |-- earnings.py           # Earnings agent + surprise prediction
|   |-- flow_intel.py         # FII/DII flow intelligence + signals
|   |-- macro.py              # Currency / commodity linkage analysis
|   +-- yfinance_provider.py  # Free NSE/BSE data via Yahoo Finance
|-- analysis/                 # Analysis engines
|   |-- technical.py          # RSI, MACD, EMAs, Bollinger, ATR, pivots
|   |-- fundamental.py        # PE, ROE, ROCE from Screener.in
|   |-- options.py            # Greeks, payoff, iron condor, butterfly
|   +-- multi_timeframe.py    # Weekly/daily/hourly confluence
|-- engine/                   # Trading logic
|   |-- trader.py             # Trader Agent + 3 risk personas
|   |-- backtest.py           # Backtester + walk-forward testing
|   |-- simulator.py          # What-if with real stock beta
|   |-- memory.py             # Trade memory (situation-outcome pairs)
|   |-- patterns.py           # India-specific market patterns
|   |-- event_strategies.py   # Event-driven strategy recommendations
|   |-- risk_metrics.py       # VaR, CVaR, correlation, HHI
|   |-- drift.py              # Model drift detection
|   |-- pairs.py              # Pair trading / relative value
|   |-- audit.py              # Decision audit trail
|   |-- profile.py            # Personal trading style profile
|   |-- alerts.py             # Price + technical + conditional alerts
|   |-- paper.py              # Paper trading engine
|   |-- paper_execute.py      # Execute trade plans in paper mode
|   |-- output.py             # PDF export + simple explainer
|   |-- portfolio.py          # Portfolio tracker + aggregated Greeks
|   |-- strategy.py           # Strategy recommendation engine
|   +-- strategy_builder.py   # Interactive strategy builder (AI-guided)
|-- bot/                      # Telegram bot
|   |-- telegram_bot.py       # 14 commands + alert push notifications
|   +-- status.py             # REPL status badge for bot activity
|-- app/                      # Application layer
|   |-- main.py               # Entry point
|   |-- repl.py               # Command REPL (35+ commands, tab-complete)
|   +-- commands/             # Command handlers
|-- config/
|   +-- credentials.py        # OS keychain credential management
|-- web/                      # Web API (FastAPI)
|   |-- api.py                # Broker OAuth login + OpenClaw skill server
|   |-- skills.py             # 17 OpenClaw skill endpoints (POST /skills/*)
|   +-- openclaw.py           # OpenClaw discovery manifest
|-- pyproject.toml
+-- .env.example
```

---

## Contributing

Contributions welcome. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for dev setup, running tests, and code style.

**Quick version:**
1. Fork & clone → `pip install -e .`
2. Run tests: `pytest` (no API keys needed — network tests excluded by default)
3. Test the app: `trade --no-broker` (uses yfinance)
4. Submit a PR against `main`

**Python 3.11+** required.

### Where help is needed

Check [open issues](https://github.com/hopit-ai/india-trade-cli/issues) for current priorities:

- **Broker integrations** ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)) — deepen Zerodha / Angel One / Upstox support, add Dhan, ICICI Direct, 5paisa
- **Integration tests** ([#79](https://github.com/hopit-ai/india-trade-cli/issues/79)) — live broker / market-data test suite
- **Web dashboard** — FastAPI backend and OAuth flow exist, frontend needed
- **Options backtesting** — strategy-specific backtest engine for options
- Bug fixes and documentation improvements are always welcome

---

## Roadmap

### Shipped
- 7 AI analyst agents + weighted scorecard + conflict detection
- Multi-round bull/bear debate with facilitator and fund manager synthesis
- Trader Agent + 3 risk personas (aggressive / neutral / conservative)
- Trade memory + India-specific market pattern knowledge base
- Strategy backtesting + walk-forward testing + what-if simulator
- Earnings agent + surprise prediction + FII/DII flow intelligence
- Event-driven strategies (expiry, RBI policy, budget, earnings)
- Advanced options — iron condor, butterfly, calendar, ratio, diagonal spreads
- VaR / CVaR portfolio risk + correlation matrix + GEX analysis
- Model drift detection + decision audit trail
- Pair trading with mean reversion signals
- Telegram bot (14 commands + alert push + REPL status badge)
- Fyers WebSocket for real-time NSE/BSE quotes
- Multi-timeframe analysis (weekly / daily / hourly)
- Paper trading execution engine
- PDF export + plain-English explainer
- DCF valuation with reverse DCF, FCF quality checks, scenario analysis
- OpenClaw integration — 17 HTTP skill endpoints + webhook alerts + session-aware chat

### Experimental
- Interactive strategy builder (plain English → backtest → paper trade → save)

### Planned
- Strategy template library (curated strategies with explanations)
- TradingView / ChartInk webhook support
- Web UI dashboard (backend exists, frontend pending)
- SEBI compliance layer

See [all open issues](https://github.com/hopit-ai/india-trade-cli/issues).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: kiteconnect` | Broker SDKs are optional. Install only the one you use: `pip install kiteconnect` for Zerodha, or use Demo mode (`login 0`). |
| `ModuleNotFoundError: feedparser` | Install with `pip install feedparser`. RSS news feeds are optional — the CLI works without them. |
| `py_vollib` errors | py_vollib uses numba which may not support all environments. The platform falls back to built-in Black-Scholes calculations. |
| NSE API returns empty data | NSE rate-limits automated requests. Wait a few minutes and retry. The CLI uses browser-like headers to reduce blocks. |
| Fyers `invalid app id hash` | App ID and Secret Key mismatch. Clear with `credentials delete FYERS_APP_ID` and `credentials delete FYERS_SECRET_KEY`, then `login`. App ID format: `XXXX-100`. |
| `No active broker session` | Run `login` or `login 0` (demo mode) before broker-dependent commands. |
| AI commands return errors | Run `credentials setup` to configure your AI provider. Free tier available with Google AI Studio (Gemini). |
| `keyring` errors on Linux | Install the SecretService backend: `sudo apt install gnome-keyring` or set credentials via `.env`. |
| Tests failing locally | Run `pip install pytest pytest-mock && pytest tests/ -v -m "not network"`. |

---

## Disclaimer

This software is for **educational and informational purposes only**. It is not financial advice. Trading in stocks and derivatives involves substantial risk of loss. Past performance — including backtests — does not guarantee future results. Always do your own research and consult a qualified financial advisor before making investment decisions. The authors are not responsible for any financial losses.

---

## License

MIT — see [LICENSE](LICENSE).
