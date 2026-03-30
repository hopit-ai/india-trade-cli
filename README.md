# India Trade CLI

AI-powered multi-agent stock & options analysis platform for Indian markets (NSE/BSE/NFO).

> **Philosophy:** Every trade must be justified. Analyze first, debate second, execute third.

Inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents) (Tauric Research) but purpose-built for India with real broker integration.

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

**Total: 8 LLM calls per analysis.** 7 analysts and trade plans are pure Python for speed and accuracy.

---

## Features

### Multi-Agent Analysis
- 7 specialist analysts run in parallel (Technical, Fundamental, Options, News/Macro, Sentiment, Sector Rotation, Risk)
- LLM-powered news sentiment analysis (understands context, not just keywords)
- Dedicated sentiment analyst (FII/DII flows, breadth, PCR signals)
- Sector rotation analyst (identifies sector tailwinds/headwinds for each stock)
- Weighted analyst scorecard with conflict detection (e.g. "Technical BULLISH vs Fundamental BEARISH")
- 2-round bull/bear debate with facilitator summary
- Fund manager synthesis with structured verdict

### Risk Management Team
- 3 risk personas: Aggressive (3% risk, tight stops), Neutral (2%, balanced), Conservative (1%, wide stops)
- Side-by-side comparison of all 3 trade plans
- ATR-based dynamic stop-loss, VIX-adjusted position sizing
- Dual profit targets with trailing logic

### Trader Agent
- Converts "BUY RELIANCE" into an executable trade plan
- Risk-based position sizing (not fixed %)
- Scale-in logic (50% market + 50% limit at support)
- Entry orders, stop-loss, target 1 (partial close), target 2, trailing stop
- F&O lot size handling for options strategies

### India Intelligence
- Earnings season calendar (NIFTY 50 stocks, pre-earnings IV analysis)
- FII/DII flow intelligence (streaks, divergence detection, momentum signals)
- Event-driven strategies (expiry, RBI policy, budget, earnings)
- 15+ India-specific calendar patterns (Monday gaps, Diwali rally, FY-end selling)

### Backtesting & Simulation
- 4 strategies: RSI, EMA crossover, MACD, Bollinger Bands
- Walk-forward testing: rolling window analysis across market regimes
- Real historical data via yfinance (works without broker login)
- Metrics: CAGR, Sharpe ratio, max drawdown, win rate vs buy-and-hold
- What-if simulator with real stock beta (not assumed beta=1)
- Multi-stock scenarios: "whatif RELIANCE -5 HDFCBANK 3"

### Advanced Options
- Iron condor, butterfly, calendar spread, ratio spread, diagonal builders
- Earnings straddle evaluator (is the straddle fairly priced vs avg move?)
- Full payoff calculator for any multi-leg strategy

### Macro Intelligence
- USD/INR, Brent Crude, Gold, US 10Y yield tracking
- Per-stock macro sensitivity mapping (e.g. IT benefits from weak INR)
- Tailwind/headwind detection based on current macro moves
- Earnings surprise prediction (technical momentum + IV + historical beat rates)

### Trade Memory
- Every analysis stored with full market context (VIX, FII flows, analyst scores)
- Query past analyses by symbol, date, conditions
- Record outcomes (WIN/LOSS/P&L) to track performance over time
- Past analyses injected into synthesis prompt for continuity

### Market Data
- Real-time quotes via Fyers API (free)
- Free data via yfinance when no broker logged in (~15 min delayed)
- Historical OHLCV up to 20 years
- NSE options chain, PCR, max pain, IV rank
- FII/DII flows, market breadth, sector indices

### 6 AI Providers
| Provider | Command | Cost |
|----------|---------|------|
| Claude subscription | `provider claude_subscription` | Free (your plan) |
| Claude API | `provider anthropic` | Pay per token |
| Gemini | `provider gemini` | Free tier available |
| OpenAI GPT-4o | `provider openai` | Pay per token |
| ChatGPT subscription | `provider openai_subscription` | Unofficial |
| Gemini Vertex AI | `provider gemini_subscription` | GCP billing |

### 6 Brokers
| Broker | API Cost | Auth Method |
|--------|----------|-------------|
| Zerodha | Paid (Rs 2k/mo) | OAuth redirect |
| Fyers | Free | OAuth redirect |
| Upstox | Free | OAuth redirect |
| Angel One | Free | TOTP auto-login |
| Groww | Free (limited) | OAuth redirect |
| Mock/Demo | Free | No login needed |

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

First run will prompt you to:
1. Choose a broker (or Demo for mock data)
2. Choose an AI provider (Claude subscription, Gemini free tier, etc.)

**No broker needed for analysis** — yfinance provides free Indian market data.

### 3. Optional: Fyers setup (free real-time data)

1. Create account at [fyers.in](https://fyers.in)
2. Create API app at [myapi.fyers.in](https://myapi.fyers.in)
3. Set redirect URL: `http://127.0.0.1:8765/fyers/callback`
4. Login via the platform: `login` → choose Fyers

---

## CLI Commands

### Core Analysis
```
analyze RELIANCE         Full multi-agent analysis (8 LLM calls)
ai <message>             Chat with AI agent (freeform questions)
morning-brief            Daily market context + AI narrative
```

### Market Data
```
earnings                 Quarterly results calendar (NIFTY 50)
earnings RELIANCE TCS    Earnings for specific stocks
flows                    FII/DII flow intelligence with signals
events                   Event-driven strategy recommendations
patterns                 Active India-specific market patterns
```

### Backtesting & Simulation
```
backtest RELIANCE rsi              RSI overbought/oversold strategy
backtest RELIANCE ma 20 50         20/50 EMA crossover
backtest RELIANCE macd             MACD signal crossover
backtest RELIANCE bb               Bollinger Bands
walkforward RELIANCE rsi           Walk-forward test (rolling 6-month windows)
walkforward RELIANCE ma --period 5y    Walk-forward with custom period
whatif nifty -3                    What if NIFTY drops 3%? (uses real beta)
whatif RELIANCE -10                What if RELIANCE drops 10%?
whatif RELIANCE -5 HDFCBANK 3      Custom multi-stock scenario
macro                              USD/INR, crude, gold, US 10Y snapshot
macro RELIANCE                     Macro impact on RELIANCE specifically
```

### Portfolio & Trading
```
portfolio                Unified view — all brokers, Greeks, risk
holdings                 Long-term delivery holdings
positions                Open intraday/F&O positions
orders                   Today's orders and status
funds                    Available cash and margin
```

### Memory & History
```
memory                   Recent trade analyses
memory stats             Performance statistics (win rate, P&L)
memory RELIANCE          Past analyses for a symbol
memory outcome ID WIN 1250   Record trade outcome
```

### Alerts
```
alert RELIANCE above 2800        Price alert
alert NIFTY below 22000          Price alert
alert RELIANCE RSI above 70      Technical indicator alert
alert list                       Show all active alerts
alert remove <ID>                Remove an alert
```

### Account
```
login                    Connect to a broker
connect                  Add a second broker
disconnect               Remove a secondary broker
brokers                  List all connected brokers
logout                   Disconnect all brokers
profile                  Account details
provider                 Show/switch AI provider
clear                    Reset AI conversation history
```

---

## Project Structure

```
india-trade-cli/
├── agent/                    # AI layer
│   ├── core.py               # TradingAgent + 6 LLM providers
│   ├── multi_agent.py         # Multi-agent pipeline (analysts, debate, synthesis)
│   ├── tools.py               # 40+ tool definitions for LLM function calling
│   └── prompts.py             # System prompt + command templates
├── brokers/                  # Broker integrations
│   ├── base.py                # Unified BrokerAPI abstract interface
│   ├── zerodha.py             # Zerodha Kite Connect
│   ├── fyers.py               # Fyers API v3
│   ├── upstox.py              # Upstox API v2
│   ├── angelone.py            # Angel One SmartAPI
│   ├── groww.py               # Groww Partner API
│   ├── mock.py                # Mock broker (paper trading)
│   └── session.py             # Multi-broker session manager
├── market/                   # Market data
│   ├── quotes.py              # Live quotes (broker → yfinance fallback)
│   ├── history.py             # Historical OHLCV (broker → yfinance → mock)
│   ├── options.py             # NSE options chain
│   ├── indices.py             # NIFTY 50, BANKNIFTY, India VIX, sectors
│   ├── news.py                # NewsAPI + RSS feeds (ET, MC, BS)
│   ├── events.py              # Earnings calendar, RBI, expiry dates
│   ├── sentiment.py           # FII/DII data + market breadth
│   ├── earnings.py            # Earnings season agent + pre-earnings IV
│   ├── flow_intel.py          # FII/DII flow intelligence + signals
│   ├── macro.py               # Currency/commodity linkage analysis
│   └── yfinance_provider.py   # Free NSE/BSE data via Yahoo Finance
├── analysis/                 # Analysis engines
│   ├── technical.py           # RSI, MACD, EMAs, Bollinger, ATR, pivots
│   ├── fundamental.py         # PE, ROE, ROCE from Screener.in
│   └── options.py             # Greeks, IV rank, payoff calculator
├── engine/                   # Trading logic
│   ├── trader.py              # Trader Agent + 3 risk personas
│   ├── backtest.py            # Strategy backtester (RSI, MA, MACD, BB)
│   ├── simulator.py           # What-if portfolio stress testing
│   ├── memory.py              # Trade memory (situation-outcome pairs)
│   ├── patterns.py            # India-specific market pattern knowledge
│   ├── event_strategies.py    # Event-driven strategy recommendations
│   ├── alerts.py              # Price + technical alerts with polling
│   ├── paper.py               # Paper trading engine
│   ├── portfolio.py           # Portfolio tracker + Greeks
│   └── strategy.py            # Strategy recommendation engine
├── app/                      # Application layer
│   ├── main.py                # Entry point
│   ├── repl.py                # Command REPL with tab-complete
│   └── commands/              # Command handlers
├── config/                   # Configuration
│   └── credentials.py        # OS keychain credential management
├── web/                      # Web API (FastAPI)
│   └── api.py                # REST + WebSocket endpoints
└── requirements.txt
```

---

## How Multi-Agent Analysis Works

When you run `analyze RELIANCE`:

**Phase 1: Analyst Team** (7 analysts, parallel, ~2s)
- Technical Analyst: RSI, MACD, EMAs, support/resistance, volume
- Fundamental Analyst: PE, ROE, ROCE, debt, growth, promoter holding
- Options Analyst: PCR, max pain, IV rank
- News & Macro Analyst: headlines, FII/DII, breadth, events (1 LLM call for sentiment)
- Sentiment Analyst: FII/DII flow signals, market breadth, PCR
- Sector Rotation Analyst: sector performance, stock's sector tailwind/headwind
- Risk Manager: VIX, position sizing, portfolio exposure

**Phase 1.5: Analyst Scorecard** (instant)
- Weighted composite score from all 7 analysts
- Conflict detection (e.g. "Technical BULLISH vs Fundamental BEARISH")
- Agreement % across analysts

**Phase 2: Research Debate** (sequential, ~30-60s)
- Round 1: Bull builds investment case → Bear counters with risks
- Round 2: Bull rebuts bear's points → Bear's final counter
- Facilitator: summarizes agreements, disagreements, picks winner

**Phase 3: Fund Manager Synthesis** (1 LLM call, ~15s)
- Weighs analyst data + debate + trade memory + market patterns
- Outputs: VERDICT, CONFIDENCE, STRATEGY, ENTRY, SL, TARGET

**Phase 4: Risk Management Team** (pure Python, instant)
- Generates 3 trade plans: Aggressive, Neutral, Conservative
- Side-by-side comparison with different sizing, stops, targets

**Phase 5: Trade Plan** (pure Python, instant)
- Concrete entry orders (market/limit/scale-in)
- Dynamic stop-loss (ATR-based, support-aware)
- Dual profit targets with trailing logic
- Pre-condition checks (events, VIX, confidence)

---

## Environment Variables

```bash
# AI Provider (choose one)
AI_PROVIDER=claude_subscription    # or: anthropic, openai, gemini
ANTHROPIC_API_KEY=sk-ant-...       # only if using anthropic provider
OPENAI_API_KEY=sk-...              # only if using openai provider
GEMINI_API_KEY=AIza...             # only if using gemini provider

# Trading
TOTAL_CAPITAL=200000               # your trading capital in INR
DEFAULT_RISK_PCT=2                 # max risk per trade (%)
TRADING_MODE=PAPER                 # PAPER or LIVE

# News (optional)
NEWSAPI_KEY=...                    # free at newsapi.org
```

---

## Roadmap

- [x] Phase 1: WebSearch, historical OHLCV, smart tools, alerts
- [x] Phase 2: Multi-agent analysis (5 analysts + debate + synthesis)
- [x] Phase 3: Trade memory + India pattern knowledge base
- [x] Phase 4: Strategy backtesting + what-if simulator
- [x] Phase 5: Earnings agent, FII/DII intelligence, event strategies
- [x] Trader Agent with 3 risk personas
- [x] Multi-round debate with facilitator
- [x] Sentiment Analyst + Sector Rotation Analyst (7 total)
- [x] Weighted analyst scorecard with conflict detection
- [x] Walk-forward backtesting (rolling window regime analysis)
- [x] Earnings surprise prediction
- [x] Real beta in what-if simulator
- [x] Advanced options (iron condor, butterfly, calendar, ratio, diagonal)
- [x] Currency/commodity macro linkages (USD/INR, crude, gold, US 10Y)
- [ ] SEBI compliance layer (margin validation, tax harvesting)
- [ ] Personal trading style profile (learn from trade outcomes)
- [ ] Full LLM multi-agent mode (`--deep`, 11+ LLM calls)
- [ ] WhatsApp/Telegram bot integration

---

## License

Private. All rights reserved.
