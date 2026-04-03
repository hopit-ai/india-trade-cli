# India Trade CLI

AI-powered multi-agent stock & options analysis platform for Indian markets (NSE/BSE/NFO).

> **Philosophy:** Every trade must be justified. Analyze first, debate second, execute third.

[![CI](https://github.com/archieindian/india-trade-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/archieindian/india-trade-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What It Does

A terminal-first trading assistant that runs **7 AI analyst agents** on any Indian stock, makes them **debate** bull vs bear, then produces a **fund-manager-grade synthesis** with concrete trade plans.

```
analyze RELIANCE
        |
  [7 Analyst Agents]  <- pure Python, parallel
  Technical | Fundamental | Options | News(LLM) | Sentiment | Sector Rotation | Risk Manager
        |
  [Analyst Scorecard]  <- weighted composite score + conflict detection
        |
  [Multi-Round Debate]  <- 5 LLM calls
  Bull R1 -> Bear R1 -> Bull Rebuttal -> Bear Rebuttal -> Facilitator
        |
  [Fund Manager Synthesis]  <- 1 LLM call
  Verdict: BUY/SELL/HOLD + confidence + rationale
        |
  [Risk Management Team]  <- pure Python
  Aggressive | Neutral | Conservative trade plans
        |
  [Trade Plan]
  Entry orders, stop-loss, targets, position sizing, scaling logic
```

**Standard mode: 8 LLM calls.** Deep mode (`deep-analyze`): 11 LLM calls with every analyst LLM-powered.

---

## Quick Start — Zero to First Analysis in 5 Minutes

### Prerequisites

- **Python 3.11+** (3.11 and 3.12 are tested in CI; 3.13+ should work but py_vollib/numba may not be available)

### Step 1: Install

```bash
git clone https://github.com/ArchieIndian/india-trade-cli.git
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
   Copy the `auth_code` value (everything between `auth_code=` and `&`) and paste it into the terminal when prompted.

### Step 4: Get news headlines (optional)

1. Sign up at [newsapi.org](https://newsapi.org) (free for development)
2. Copy your API key

### Step 5: Run it

```bash
trade
```

First run walks you through:
1. **Broker** → Choose **Fyers** → enter App ID + Secret Key (from Step 3 above)
2. **AI Provider** → Choose **Gemini** (paste API key) or **Claude subscription** (no key needed)
3. **NewsAPI** → paste your key (or press Enter to skip)

You're in the REPL. Try it:

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

Uses yfinance for real NSE/BSE data (~15 min delayed). Technical, fundamental, sentiment, and sector analysis all work. Options chain data requires a broker connection (Fyers recommended). Connect a broker later via the `login` command in the REPL.

> **Note:** `--no-broker` is a CLI flag, not an interactive menu option. The broker selection menu offers Demo, Zerodha, Groww, Angel One, Upstox, and Fyers.

---

## AI Provider Setup

You need one AI provider for the analysis brain. The platform guides you through setup on first run, or you can configure manually:

| Provider | Cost | Setup |
|----------|------|-------|
| **Gemini** | Free tier available | Get key at [aistudio.google.com](https://aistudio.google.com) |
| **Claude (subscription)** | Free with Pro/Max plan | Install CLI: `npm i -g @anthropic-ai/claude-code` then `claude login` |
| Claude API | Pay per token | Key from [console.anthropic.com](https://console.anthropic.com) |
| OpenAI GPT-4o | Pay per token | Key from [platform.openai.com](https://platform.openai.com) |

**Switch anytime:** `provider gemini` or `provider claude_subscription`

### Manual config (optional)

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Or use the interactive credential manager:

```bash
trade
> credentials setup
```

API keys and secrets are stored in your OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Locker) via the `keyring` library. Broker session tokens (access tokens obtained after login) are cached as JSON files under `~/.trading_platform/` for session resumption and are automatically deleted on logout.

---

## Broker Setup (Optional)

### Fyers (Recommended - free, real-time data)

1. Create account at [fyers.in](https://fyers.in)
2. Create API app at [myapi.fyers.in](https://myapi.fyers.in)
   - Redirect URL: `http://127.0.0.1:8765/fyers/callback` (must be exact)
3. Login in the platform:
   ```
   trade
   > login
   > Choose: Fyers
   > Enter App ID and Secret Key when prompted
   ```
4. Browser opens for Fyers login. Token saved for 12 hours.

**WebSocket**: Auto-connects on login for real-time quotes.

### Other Brokers

| Broker | Status | Notes |
|--------|--------|-------|
| **Fyers** | **Fully supported** | Free API, WebSocket, options chain |
| Zerodha | Basic | Requires Kite Connect subscription |
| Angel One | Basic | Free SmartAPI, TOTP login |
| Upstox | Basic | Free API, OAuth |
| Groww | Basic | No historical data API |
| Mock/Demo | Full | Synthetic data, no login needed |

---

## Telegram Bot (Optional)

Push alerts, quotes, and full analyses to your phone.

```
trade
> telegram setup
```

The guided wizard walks you through:
1. Creating a bot via @BotFather
2. Validating your token
3. Connecting your chat

**14 bot commands**: `/quote`, `/analyze`, `/deepanalyze`, `/brief`, `/flows`, `/earnings`, `/events`, `/macro`, `/alert`, `/alerts`, `/memory`, `/pnl`, `/help`

Alerts auto-push to Telegram when triggered. The REPL shows a status badge when Telegram commands are running.

---

## All CLI Commands

### Analysis (AI-powered)
| Command | Description |
|---------|-------------|
| `analyze RELIANCE` | Multi-agent analysis (7 analysts + debate + trade plans) |
| `deep-analyze RELIANCE` | Full LLM mode (11 calls, every analyst uses AI) |
| `ai <message>` | Chat with AI — follow-ups keep context, `clear` to reset |
| `morning-brief` | Daily market context + AI narrative |
| `mtf RELIANCE` | Multi-timeframe analysis (weekly/daily/hourly) |

### Strategy Builder (experimental)
| Command | Description |
|---------|-------------|
| `strategy new` | Describe a strategy in plain English, AI interviews you, generates code, backtests |
| `strategy new --simple` | Same but explained like you're 17 (no jargon) |
| `strategy list` | List all saved strategies with backtest stats |
| `strategy backtest <name> --period 2y` | Re-backtest a saved strategy |
| `strategy run <name> RELIANCE --paper` | Generate latest signal, paper trade if BUY |
| `strategy show <name>` | View generated Python code |
| `strategy delete <name>` | Remove a saved strategy |

Supports single-symbol strategies (RSI, MACD, EMA crossover, etc.) and multi-symbol pairs strategies (z-score spread trading with both legs tracked). The AI gives data-backed recommendations for each parameter.

### Market Data
| Command | Description |
|---------|-------------|
| `earnings` | Quarterly results calendar (NIFTY 50) |
| `earnings RELIANCE TCS` | Earnings for specific stocks |
| `flows` | FII/DII flow intelligence with signals |
| `events` | Event-driven strategy recommendations |
| `patterns` | Active India-specific market patterns |
| `macro` | USD/INR, crude, gold, US 10Y snapshot |
| `macro RELIANCE` | Macro impact on a specific stock |

### Backtesting & Simulation
| Command | Description |
|---------|-------------|
| `backtest RELIANCE rsi` | RSI overbought/oversold |
| `backtest RELIANCE ma 20 50` | EMA crossover |
| `backtest RELIANCE macd` | MACD signal crossover |
| `backtest RELIANCE bb` | Bollinger Bands |
| `walkforward RELIANCE rsi` | Walk-forward test (rolling windows) |
| `whatif nifty -3` | What if NIFTY drops 3%? (uses real beta) |

### Risk & Portfolio
| Command | Description |
|---------|-------------|
| `risk-report` | VaR/CVaR portfolio risk analysis |
| `greeks` | Portfolio Greeks (net Delta, Theta, Vega) |
| `pairs` | Pair trading opportunities scan |
| `pairs HDFCBANK ICICIBANK` | Analyze a specific pair |

### Paper Trading
| Command | Description |
|---------|-------------|
| `paper-execute` | Execute last trade plan (neutral risk) |
| `paper-execute aggressive` | Execute aggressive plan |
| `paper-execute conservative` | Execute conservative plan |

### Memory & Learning
| Command | Description |
|---------|-------------|
| `memory` | Recent trade analyses |
| `memory stats` | Performance statistics |
| `memory RELIANCE` | Past analyses for a symbol |
| `memory outcome ID WIN 1250` | Record trade outcome |
| `profile` | Your personal trading style profile |
| `drift` | Model drift detection |
| `audit <ID>` | Post-mortem analysis of a trade |

### Alerts
| Command | Description |
|---------|-------------|
| `alert RELIANCE above 2800` | Price alert |
| `alert NIFTY RSI above 70` | Technical alert |
| `alert RELIANCE above 2800 AND RSI above 70` | Conditional alert |
| `alerts` | List active alerts |
| `alert remove <ID>` | Remove an alert |

### Portfolio & Trading
| Command | Description |
|---------|-------------|
| `funds` | Available cash and margin |
| `holdings` | Long-term delivery holdings |
| `positions` | Open intraday/F&O positions |
| `orders` | Today's orders and status |
| `portfolio` | Unified view across all brokers |

### Output & Export
| Command | Description |
|---------|-------------|
| `save-pdf` | Save previous output as PDF |
| `explain` | Explain previous output simply |
| `explain-save` | Explain + save as PDF |
| `--pdf` | Flag: append to any command |
| `--explain` | Flag: append to any command |
| `--explain-save` | Flag: explain + PDF in one shot |

### Account & Config
| Command | Description |
|---------|-------------|
| `login` | Connect to a broker |
| `connect` | Add a second broker |
| `disconnect` | Remove a secondary broker |
| `brokers` | List all connected brokers |
| `logout` | Disconnect all brokers |
| `provider` | Show/switch AI provider |
| `telegram` / `telegram setup` | Start bot / run guided setup |
| `credentials` | Manage API keys |

---

## Configuration

### Environment Variables

```bash
# AI Provider (choose one)
AI_PROVIDER=gemini              # or: anthropic, openai, claude_subscription
GEMINI_API_KEY=AIza...          # if using gemini
ANTHROPIC_API_KEY=sk-ant-...    # if using anthropic
OPENAI_API_KEY=sk-...           # if using openai

# Trading Capital & Risk
TOTAL_CAPITAL=200000            # your trading capital in INR
DEFAULT_RISK_PCT=2              # max risk per trade (%)
TRADING_MODE=PAPER              # PAPER or LIVE

# News (optional)
NEWSAPI_KEY=...                 # free at newsapi.org
NEWSAPI_ENABLED=1               # set to 0 to disable

# Telegram (optional)
TELEGRAM_BOT_TOKEN=...          # from @BotFather
```

### Position Sizing

The Trader Agent calculates position size using:

```
Max Risk = Capital x Risk% x VIX Adjustment
Shares   = Max Risk / Stop-Loss Distance (per share)
```

VIX-based auto-adjustment:
| VIX Level | Position Size |
|-----------|--------------|
| < 15 | 100% (normal) |
| 15-20 | 85% |
| 20-25 | 65% |
| > 25 | 50% (halved) |

### Data Flow Priority

Quotes are fetched in this order:
1. **WebSocket** (instant) - real-time ticks from Fyers
2. **Broker REST API** (1-3s) - fallback
3. **yfinance** (~15 min delayed) - free fallback when no broker
4. **Mock data** (synthetic) - last resort

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
|   |-- quotes.py             # Quotes: WebSocket -> broker REST -> yfinance
|   |-- websocket.py          # Fyers WebSocket for real-time ticks
|   |-- history.py            # Historical OHLCV
|   |-- options.py            # NSE options chain
|   |-- indices.py            # NIFTY 50, BANKNIFTY, India VIX, sectors
|   |-- news.py               # NewsAPI + RSS feeds
|   |-- events.py             # Earnings calendar, RBI, expiry dates
|   |-- sentiment.py          # FII/DII data + market breadth
|   |-- earnings.py           # Earnings agent + surprise prediction
|   |-- flow_intel.py         # FII/DII flow intelligence + signals
|   |-- macro.py              # Currency/commodity linkage analysis
|   +-- yfinance_provider.py  # Free NSE/BSE data via Yahoo Finance
|-- analysis/                 # Analysis engines
|   |-- technical.py          # RSI, MACD, EMAs, Bollinger, ATR, pivots
|   |-- fundamental.py        # PE, ROE, ROCE from Screener.in
|   |-- options.py            # Greeks, payoff, iron condor, butterfly
|   +-- multi_timeframe.py    # Weekly/daily/hourly confluence
|-- engine/                   # Trading logic
|   |-- trader.py             # Trader Agent + 3 risk personas
|   |-- backtest.py           # Backtester + walk-forward testing
|   |-- simulator.py          # What-if with real beta
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
|   +-- strategy_builder.py  # Interactive strategy builder (AI-guided)
|-- bot/                      # Telegram bot
|   |-- telegram_bot.py       # 14 commands + alert push notifications
|   +-- status.py             # REPL status badge for bot activity
|-- app/                      # Application layer
|   |-- main.py               # Entry point
|   |-- repl.py               # Command REPL (35+ commands, tab-complete)
|   +-- commands/             # Command handlers
|-- config/                   # Configuration
|   +-- credentials.py        # OS keychain credential management
|-- web/                      # Web API (FastAPI)
|   +-- api.py                # REST + WebSocket endpoints
|-- requirements.txt
|-- pyproject.toml
+-- .env.example
```

---

## Contributing

Contributions welcome! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide (dev setup, running tests, code style).

**Quick version:**

1. Fork & clone → `pip install -e .` → `python -m venv .venv`
2. Run tests: `pytest` (no API keys needed — network tests are excluded by default)
3. Test the app: `trade --no-broker` (uses yfinance, no broker account needed)
4. Submit a PR against `main`

**Requires Python 3.11+.**

### Areas where help is needed

Check [open issues](https://github.com/ArchieIndian/india-trade-cli/issues) for current priorities. Good areas to contribute:

- **Trade execution & broker integrations** ([#80](https://github.com/ArchieIndian/india-trade-cli/issues/80)) — bridge TraderAgent plans to real orders, deepen Zerodha/Angel One/Upstox support, add new brokers (Dhan, ICICI Direct, 5paisa)
- **Integration tests** ([#79](https://github.com/ArchieIndian/india-trade-cli/issues/79)) — live broker/market-data test suite
- **Options backtesting** — strategy-specific backtest engine
- **Options scanner** — scan for high IV, unusual OI
- **Web dashboard** — FastAPI backend exists, frontend needed
- Bug fixes and documentation improvements are always welcome

---

## Roadmap

### Shipped
- 7 analyst agents + weighted scorecard
- Multi-round bull/bear debate with facilitator
- Trader Agent + 3 risk personas (aggressive/neutral/conservative)
- Trade memory + India pattern knowledge base
- Strategy backtesting + walk-forward testing
- What-if simulator with real stock beta
- Earnings agent + surprise prediction
- FII/DII flow intelligence + divergence detection
- Event-driven strategies (expiry, RBI, budget, earnings)
- Advanced options (iron condor, butterfly, calendar, ratio, diagonal)
- Currency/commodity macro linkages
- VaR/CVaR portfolio risk + correlation matrix
- Model drift detection + decision audit trail
- Pair trading with mean reversion signals
- Full LLM deep mode (11 calls)
- Telegram bot (14 commands + alert push)
- Fyers WebSocket for real-time quotes
- Multi-timeframe analysis
- Paper trading execution
- PDF export + simple explainer
- Real-time alert evaluation via WebSocket
- Telegram bot (14 commands + alert push + REPL status badge)
- Auto-archived PDF exports with timestamped copies
- Multi-symbol backtester (pairs trading with both legs tracked)
- Options-specific backtesting (straddle, iron condor, covered call, protective put)
- Options scanner (high IV, unusual OI)
- Greeks-based position management (delta-hedge, roll-options)
- Volatility surface and IV smile analysis
- GEX analysis (dealer gamma positioning)
- Broker order placement flow (Zerodha, Fyers, Upstox, Angel One, Groww)
- DCF valuation model with reverse DCF, FCF quality, scenarios

### Experimental
- Interactive strategy builder (plain English to backtest to paper trade to save)

### Planned
- Strategy template library (curated strategies with explanations)
- TradingView/ChartInk webhook support
- Web UI dashboard (FastAPI — OAuth login flow exists, dashboard pending)
- SEBI compliance layer

See [all open issues](https://github.com/ArchieIndian/india-trade-cli/issues) for the full list.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: kiteconnect` | Broker SDKs are optional. Install only the one you use: `pip install kiteconnect` for Zerodha, or use Demo mode (`login 0`). |
| `ModuleNotFoundError: feedparser` | Install with `pip install feedparser`. RSS news feeds are optional — the CLI works without them. |
| `py_vollib` errors on Python 3.13+ | py_vollib uses numba which may not support newer Python versions yet. The platform gracefully falls back to built-in Black-Scholes calculations. |
| NSE API returns empty data | NSE rate-limits automated requests. Wait a few minutes and retry. The CLI uses browser-like headers to reduce blocks. |
| Fyers `invalid app id hash` | Your App ID and Secret Key don't match. To clear and re-enter: `credentials delete FYERS_APP_ID` then `credentials delete FYERS_SECRET_KEY` then `login`. Verify values at [myapi.fyers.in](https://myapi.fyers.in) (App ID format: `XXXX-100`). |
| `No active broker session` | Run `login` or `login 0` (demo mode) before using broker-dependent commands like `portfolio` or `orders`. |
| AI commands return errors | Run `credentials setup` to configure your AI provider (Anthropic, OpenAI, or Gemini). Free tier available with Google AI Studio. |
| `keyring` errors on Linux | Install the SecretService backend: `sudo apt install gnome-keyring` or set credentials via environment variables in `.env`. |
| Tests failing locally | Run `pip install pytest pytest-mock && pytest tests/ -v`. Some tests require optional dependencies — check the error for which package to install. |

---

## Disclaimer

This software is for **educational and informational purposes only**. It is not financial advice. Trading in stocks and derivatives involves substantial risk of loss. Past performance (including backtests) does not guarantee future results. Always do your own research and consult a qualified financial advisor before making investment decisions. The authors are not responsible for any financial losses incurred through use of this software.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
