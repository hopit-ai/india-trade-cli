# Command Reference

Full list of REPL commands. Run `help` inside the REPL for a live summary.

---

## Analysis

| Command | Description |
|---------|-------------|
| `analyze RELIANCE` | 7 analyst agents + bull-bear debate + 3 risk-profiled trade plans (8 LLM calls) |
| `deep-analyze INFY` | Full LLM mode — every analyst AI-powered (11 calls) |
| `morning-brief` | Daily market context + AI narrative |
| `mtf RELIANCE` | Multi-timeframe confluence (weekly / daily / hourly) |
| `ai <message>` | Chat with the trading agent — context-aware follow-ups |

---

## Strategy Library (curated templates)

| Command | Description |
|---------|-------------|
| `strategy library` | Browse all 58 strategies (26 options + 32 technical) |
| `strategy library --type options` | Options strategies only |
| `strategy library --type technical` | Technical / systematic strategies only |
| `strategy library <category>` | Filter by category (e.g. `momentum`, `income`, `breakout`) |
| `strategy learn <id>` | Full explanation — layman section, signals, parameters, cached backtest stats |
| `strategy use <id> SYMBOL` | Options: apply with live ATM data. Technical: run backtest + current signal |

---

## Strategy Builder (AI-generated)

> **Warning:** The builder executes AI-generated Python code on your machine. Only run strategies from sources you trust.

| Command | Description |
|---------|-------------|
| `strategy new` | Describe in plain English → AI interviews, generates code, backtests |
| `strategy new --simple` | Same without jargon |
| `strategy list` | All saved strategies with backtest stats |
| `strategy backtest <name> [--period 2y]` | Re-backtest a saved strategy |
| `strategy run <name> SYMBOL [--paper]` | Generate signal, paper trade if BUY |
| `strategy show <name>` | View the generated Python code |
| `strategy delete <name>` | Remove a saved strategy |

---

## Market Data

| Command | Description |
|---------|-------------|
| `quote TCS` | Live price, OHLC, volume, change |
| `flows` | FII/DII flow intelligence + buy/sell signals |
| `earnings` | Quarterly results calendar (NIFTY 50) |
| `earnings RELIANCE TCS` | Earnings for specific stocks |
| `deals` | Today's bulk / block deals |
| `macro` | USD/INR, crude oil, gold, US 10Y snapshot |
| `macro RELIANCE` | Macro impact on a specific stock |
| `events` | Event-driven strategy recommendations (expiry, RBI, budget) |
| `patterns` | Active India-specific market patterns |

---

## Backtesting & Simulation

| Command | Description |
|---------|-------------|
| `backtest RELIANCE rsi` | RSI overbought / oversold |
| `backtest RELIANCE ma 20 50` | EMA crossover |
| `backtest RELIANCE macd` | MACD signal crossover |
| `backtest RELIANCE bb` | Bollinger Bands mean reversion |
| `walkforward RELIANCE rsi` | Walk-forward test (rolling windows) |
| `whatif nifty -3` | What if NIFTY drops 3%? (uses real stock beta) |

---

## Risk & Portfolio

| Command | Description |
|---------|-------------|
| `risk-report` | VaR / CVaR portfolio risk analysis |
| `greeks` | Net Delta, Theta, Vega across all positions |
| `pairs` | Scan for pair trading opportunities |
| `pairs HDFCBANK ICICIBANK` | Analyse a specific stock pair |
| `portfolio` | Unified view across all connected brokers |

---

## Trade Execution

| Command | Description |
|---------|-------------|
| `execute` | Execute last trade plan (neutral risk) — LIVE or PAPER, auto-detected |
| `execute aggressive` | Execute aggressive plan |
| `execute conservative` | Execute conservative plan |

---

## Trade Memory & Learning

| Command | Description |
|---------|-------------|
| `memory` | Recent trade analyses |
| `memory stats` | Win rate, P&L, and performance statistics |
| `memory RELIANCE` | Past analyses for a specific symbol |
| `memory outcome <ID> WIN 1250` | Record trade outcome |
| `profile` | Your personal trading style profile |
| `drift` | Model drift detection — is the AI losing edge? |
| `audit <ID>` | Post-mortem analysis of a specific trade |

---

## Alerts

| Command | Description |
|---------|-------------|
| `alert RELIANCE above 2800` | Simple price alert |
| `alert NIFTY RSI above 70` | Technical indicator alert |
| `alert RELIANCE above 2800 AND RSI above 70` | Conditional alert (AND logic) |
| `alerts` | List all active alerts |
| `alert remove <ID>` | Remove an alert |

---

## Broker & Account

| Command | Description |
|---------|-------------|
| `funds` | Available cash and margin |
| `holdings` | Long-term delivery holdings |
| `positions` | Open intraday / F&O positions |
| `orders` | Today's orders and status |
| `login` | Connect to a broker |
| `connect` | Add a second broker (multi-broker mode) |
| `logout` | Disconnect all brokers |

---

## Output & Config

| Command | Description |
|---------|-------------|
| `save-pdf` | Save previous output as PDF |
| `explain` | Explain previous output in plain English |
| `--pdf` / `--explain` / `--explain-save` | Flags: append to any command |
| `provider` | Show / switch AI provider |
| `telegram setup` | Connect Telegram bot |
| `credentials` | Manage API keys |
| `web` | Start OpenClaw HTTP skill server |

---

## Telegram Bot

Run `telegram setup` once. After that, 14 bot commands are available from your phone:

`/quote` `/analyze` `/deepanalyze` `/brief` `/flows` `/earnings` `/events` `/macro` `/alert` `/alerts` `/memory` `/pnl` `/help`

Alerts fire to Telegram automatically when triggered.
