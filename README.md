# India Trade CLI

Open-source terminal for trading Indian stocks and derivatives (NSE / BSE / NFO). Runs AI analyst agents, backtests quant strategies, pushes Telegram alerts, and exposes everything as HTTP skills.

> Every trade must be justified. Analyze first, debate second, execute third.

[![CI](https://github.com/hopit-ai/india-trade-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/hopit-ai/india-trade-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## How it works

```
analyze RELIANCE
        │
  7 Analyst Agents  (parallel, pure Python)
  Technical · Fundamental · Options · News · Sentiment · Sector · Risk
        │
  Weighted Scorecard + Conflict Detection
        │
  Multi-Round Debate  (5 LLM calls)
  Bull → Bear → Rebuttal → Rebuttal → Facilitator
        │
  Fund Manager Synthesis  (1 LLM call)
  Verdict: BUY / SELL / HOLD + confidence + rationale
        │
  3 Risk-Profiled Trade Plans
  Aggressive · Neutral · Conservative — entry, stop, targets, sizing
```

Standard `analyze`: 8 LLM calls. `deep-analyze`: 11 calls, every analyst fully AI-powered.

---

## Quick start

```bash
git clone https://github.com/hopit-ai/india-trade-cli.git
cd india-trade-cli
python -m venv .venv && source .venv/bin/activate
pip install -e .
trade --no-broker   # yfinance data, no broker account needed
```

Inside the REPL:
```
> analyze RELIANCE
> morning-brief
> strategy library
```

### AI provider

| Provider | Cost | How |
|----------|------|-----|
| **Gemini** | Free tier | Key from [aistudio.google.com](https://aistudio.google.com) |
| **Claude** (Pro/Max sub) | Free with subscription | `npm i -g @anthropic-ai/claude-code` → `claude login` |
| **Claude API** | Pay per token | Key from [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI** | Pay per token | Key from [platform.openai.com](https://platform.openai.com) |
| **Ollama** | Free, local | `ollama pull llama3.1` |
| **OpenRouter / Groq / etc.** | Varies | Set `OPENAI_BASE_URL` in `.env` |

Switch anytime: `provider gemini` or `provider claude_subscription`.

### Real-time market data (Fyers — free)

1. Create a free account at [fyers.in](https://fyers.in)
2. Go to [myapi.fyers.in](https://myapi.fyers.in) → **Create App** — redirect URL must be `http://127.0.0.1:8765/fyers/callback`
3. Copy the **App ID** (`XXXX-100`) and **Secret Key**
4. `trade` → choose `[5] Fyers` → paste credentials → browser OAuth completes automatically

Without Fyers, `--no-broker` uses yfinance (~15 min delayed). Options chain needs a broker.

---

## What you can do

**[Full command reference →](docs/commands.md)**

The highlights:

- **`analyze RELIANCE`** — 7 AI analysts, a bull-bear debate, and three trade plans in one command
- **`strategy library`** — browse 58 curated strategies (26 options + 32 technical) with plain-English explanations and cached backtest results
- **`strategy learn supertrend`** — deep-dive on any strategy: what it is, when to use it, real ₹ examples, and last backtest stats
- **`strategy use iron_condor NIFTY`** — apply an options template with live ATM data, get P&L summary instantly
- **`strategy new`** — describe a strategy in plain English, the AI generates + backtests the Python code
- **`backtest RELIANCE rsi`** — quick strategy backtests on NSE history
- **`morning-brief`** — daily AI market brief
- **`flows`** — FII/DII intelligence with directional signals
- **`telegram setup`** — connect a bot; get quotes, analysis, and price alerts on your phone

---

## Configuration

```bash
# .env  (see .env.example for all options)
AI_PROVIDER=gemini              # gemini | anthropic | openai | claude_subscription
GEMINI_API_KEY=AIza...

TOTAL_CAPITAL=200000            # INR — used for position sizing
DEFAULT_RISK_PCT=2              # max risk per trade (%)
TRADING_MODE=PAPER              # PAPER or LIVE

NEWSAPI_KEY=...                 # optional — improves morning-brief quality
TELEGRAM_BOT_TOKEN=...          # optional
```

Position sizing auto-adjusts for VIX: 100% normal → 85% at VIX 15–20 → 65% at 20–25 → 50% above 25.

API keys are stored in the OS keychain (macOS Keychain / Linux SecretService / Windows Credential Locker).

---

## Brokers

| Broker | Status |
|--------|--------|
| **Fyers** | Fully supported — free real-time API, options chain, WebSocket |
| **Mock / Demo** | Fully supported — no login needed (`trade --no-broker`) |
| Zerodha / Angel One / Upstox / Groww | WIP — [#80](https://github.com/hopit-ai/india-trade-cli/issues/80) |

---

## OpenClaw HTTP skills

```bash
uvicorn web.api:app --host 127.0.0.1 --port 8765
# or from REPL: web
```

Exposes 17 skills as `POST /skills/<name>`. Discovery: `GET /.well-known/openclaw.json`.

Includes: `quote`, `analyze`, `deep_analyze`, `backtest`, `flows`, `morning_brief`, `chat` (session-aware), `options_chain`, `deals`, `earnings`, `macro`, `alerts/*`.

> No auth — keep on `127.0.0.1` or put behind a proxy.

---

## Project structure

```
agent/      AI layer — LLM providers, analyst agents, debate, synthesis
brokers/    Broker integrations — Fyers, mock, Zerodha/Upstox/Angel (WIP)
market/     Market data — quotes, WebSocket, options chain, news, FII/DII
analysis/   Technical, fundamental, options Greeks, multi-timeframe
engine/     Backtester, 58-strategy library, risk metrics, alerts, trade executor
bot/        Telegram bot
app/        REPL entry point and command handlers
web/        FastAPI — OAuth + 17 OpenClaw skill endpoints
```

---

## Roadmap

**Shipped:** 7 analyst agents · scorecard · debate · 3 risk personas · trade memory · backtesting · walk-forward · what-if · FII/DII flows · event strategies · options analytics (iron condor, butterfly, straddle) · VaR/CVaR · DCF valuation · model drift · pair trading · Telegram bot · Fyers WebSocket · paper trading · PDF export · OpenClaw skills · 58-strategy template library · backtest cache

**Planned:** additional broker integrations · web UI frontend · TradingView webhook support · SEBI compliance layer

See [open issues](https://github.com/hopit-ai/india-trade-cli/issues).

---

## Contributing

```bash
pip install -e .
pytest                    # no API keys needed, network tests skipped by default
trade --no-broker         # smoke test
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Most wanted: broker integrations ([#80](https://github.com/hopit-ai/india-trade-cli/issues/80)), web UI frontend, integration tests ([#79](https://github.com/hopit-ai/india-trade-cli/issues/79)).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: kiteconnect` | Broker SDKs are optional. Use Demo mode (`login 0`). |
| NSE API returns empty | NSE rate-limits scrapers. Wait a minute and retry. |
| Fyers `invalid app id hash` | App ID / Secret mismatch. `credentials delete FYERS_APP_ID` then re-login. App ID format: `XXXX-100`. |
| `No active broker session` | Run `login` or `login 0` (demo) first. |
| AI commands error | Run `credentials setup` to configure your AI provider. |
| `keyring` errors on Linux | `sudo apt install gnome-keyring` or set credentials via `.env`. |
| Tests failing locally | `pip install pytest pytest-mock && pytest -m "not network"` |

---

**Disclaimer:** For educational purposes only. Not financial advice. Trading involves substantial risk of loss. The authors are not responsible for financial losses.

MIT — see [LICENSE](LICENSE).
