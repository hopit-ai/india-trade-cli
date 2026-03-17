# 🇮🇳 Indian Trading Platform

A guided, AI-powered stock & options trading terminal for Indian markets (NSE/BSE/NFO).

> **Philosophy:** Every trade must be justified — fundamental → technical → options → risk → confirm.

Built with Claude (Anthropic) as the reasoning engine, supporting Zerodha and Groww as brokers.

---

## Features

- 🔐 Login via **Zerodha** (Kite Connect) or **Groww** (Partner API)
- 📊 Live quotes, OHLCV history, options chain
- 🧠 **Claude AI** guides every decision step-by-step
- 📰 Real-time news, corporate events, RBI calendar
- 📐 Technical analysis: RSI, MACD, MAs, support/resistance
- 📋 Fundamental analysis: PE, ROE, ROCE, Screener.in data
- 🎲 Options analytics: Greeks, IV rank, PCR, max pain, payoff
- 📝 **Paper trading** mode — practice without real money
- 💼 Portfolio tracker with live P&L and net Greeks
- 🖥️ Claude Code-style split terminal UI

---

## Setup

### 1. Clone & install

```bash
git clone <repo>
cd trading-platform
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### Keys needed

| Key | Where to get |
|-----|-------------|
| `KITE_API_KEY` + `KITE_API_SECRET` | [developers.kite.trade](https://developers.kite.trade) |
| `GROWW_CLIENT_ID` + `GROWW_CLIENT_SECRET` | Groww Partner portal |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) (free tier) |

### 3. Run

```bash
python -m app.main
```

---

## Project Structure

```
trading-platform/
├── brokers/            # Broker API integrations
│   ├── base.py         # Unified BrokerAPI abstract interface
│   ├── zerodha.py      # Zerodha Kite Connect implementation
│   ├── groww.py        # Groww REST API implementation
│   └── session.py      # Login flow + singleton session
├── market/             # Market data layer
│   ├── quotes.py       # Live quotes
│   ├── history.py      # OHLCV historical data
│   ├── options.py      # Options chain
│   ├── indices.py      # NIFTY, BANKNIFTY, India VIX
│   ├── news.py         # NewsAPI + RSS feeds
│   ├── events.py       # Earnings, RBI, expiry calendar
│   └── sentiment.py    # FII/DII data + news sentiment
├── analysis/           # Analysis engines
│   ├── technical.py    # RSI, MACD, MAs, pivots
│   ├── fundamental.py  # PE, ROE, Screener.in data
│   └── options.py      # Greeks, IV rank, payoff
├── agent/              # Claude AI layer
│   ├── core.py         # TradingAgent (tool-calling)
│   ├── tools.py        # Tool schemas for Claude
│   └── prompts.py      # System + command prompts
├── engine/             # Trading logic
│   ├── paper.py        # Paper trading engine
│   ├── portfolio.py    # Portfolio tracker + Greeks
│   └── strategy.py     # Strategy recommendation engine
├── platform/           # CLI entry points
│   ├── main.py         # App entry point
│   ├── repl.py         # REPL command loop
│   └── commands/       # Individual command handlers
│       ├── morning_brief.py
│       └── trade.py
├── ui/                 # Textual TUI
│   ├── app.py          # Split panel layout
│   └── widgets/        # Reusable UI components
└── web/                # FastAPI backend (future)
    └── api.py
```

---

## Trading Modes

| Mode | Description |
|------|-------------|
| `PAPER` | Simulated trades, no real money. **Default.** |
| `LIVE`  | Real orders via connected broker. Requires explicit switch. |

Switch in `.env`: `TRADING_MODE=PAPER` or `TRADING_MODE=LIVE`

---

## CLI Commands

```
login           → Connect to Zerodha or Groww
morning-brief   → Daily market context + AI narrative
analyze <SYM>   → Full fundamental + technical + options analysis
portfolio       → Live holdings, positions, Greeks
trade           → Interactive strategy builder
orders          → Today's orders and status
paper           → Toggle paper trading mode
help            → Claude-guided help
```
