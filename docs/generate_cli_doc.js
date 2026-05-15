// generate_cli_doc.js — India Trade CLI Feature Reference
// Usage: node generate_cli_doc.js

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, ExternalHyperlink, LevelFormat,
  TableOfContents, PageBreak, UnderlineType,
} = require("docx");
const fs = require("fs");

// ── Palette ────────────────────────────────────────────────────────────────
const C = {
  navy:    "1B3A5C",
  teal:    "0D7377",
  gold:    "D4A017",
  green:   "1A7A4A",
  red:     "B22222",
  purple:  "5B2D8E",
  gray:    "5A6475",
  light:   "EEF2F7",
  tealBg:  "D8F0F0",
  goldBg:  "FFF8E7",
  greenBg: "E8F5EE",
  redBg:   "FFF0F0",
  white:   "FFFFFF",
};

// ── Border helpers ─────────────────────────────────────────────────────────
const border = (color = "CCCCCC", size = 4) =>
  ({ style: BorderStyle.SINGLE, size, color });
const noBorder = () =>
  ({ style: BorderStyle.NIL, size: 0, color: "FFFFFF" });
const allBorders = (color, size) => ({
  top: border(color, size), bottom: border(color, size),
  left: border(color, size), right: border(color, size),
});
const noInside = () => ({
  top: noBorder(), bottom: noBorder(),
  left: noBorder(), right: noBorder(),
});

// ── Typography helpers ─────────────────────────────────────────────────────
const run = (text, opts = {}) => new TextRun({ text, font: "Arial", ...opts });
const code = (text) => new TextRun({ text, font: "Courier New", size: 18, color: C.purple });

const p = (children, opts = {}) =>
  new Paragraph({ children: Array.isArray(children) ? children : [children], ...opts });

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [run(text, { bold: true, size: 36, color: C.navy })],
  spacing: { before: 480, after: 200 },
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [run(text, { bold: true, size: 28, color: C.teal })],
  spacing: { before: 360, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.teal, space: 4 } },
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [run(text, { bold: true, size: 24, color: C.navy })],
  spacing: { before: 280, after: 120 },
});

const h4 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_4,
  children: [run(text, { bold: true, size: 22, color: C.teal })],
  spacing: { before: 200, after: 80 },
});

const bodyP = (text, opts = {}) => new Paragraph({
  children: [run(text, { size: 20 })],
  spacing: { before: 40, after: 80 },
  ...opts,
});

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ── Bullet list ────────────────────────────────────────────────────────────
const bullet = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  children: typeof text === "string" ? [run(text, { size: 20 })] : text,
  spacing: { before: 40, after: 40 },
});

// ── Code block ────────────────────────────────────────────────────────────
const codeBlock = (lines) => {
  const content = Array.isArray(lines) ? lines.join("\n") : lines;
  return new Paragraph({
    children: [new TextRun({ text: content, font: "Courier New", size: 16, color: C.purple })],
    spacing: { before: 120, after: 120 },
    indent: { left: 360 },
    shading: { fill: "F5F0FF", type: ShadingType.CLEAR },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: C.teal, space: 4 } },
  });
};

// ── Info / note box ────────────────────────────────────────────────────────
const noteBox = (text, color = C.tealBg, accent = C.teal) =>
  new Paragraph({
    children: [run(text, { size: 18, italics: true })],
    spacing: { before: 100, after: 100 },
    indent: { left: 360, right: 360 },
    shading: { fill: color, type: ShadingType.CLEAR },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: accent, space: 6 } },
  });

// ── Simple 2-col table ─────────────────────────────────────────────────────
const twoColTable = (rows, headerLabels = ["Command / Item", "Description"]) => {
  const headerCells = headerLabels.map((label, i) => new TableCell({
    width: { size: i === 0 ? 3200 : 6160, type: WidthType.DXA },
    shading: { fill: C.navy, type: ShadingType.CLEAR },
    borders: allBorders(C.navy, 6),
    margins: { top: 100, bottom: 100, left: 160, right: 160 },
    children: [p(run(label, { bold: true, size: 20, color: C.white }))],
  }));

  const dataRows = rows.map(([col1, col2], idx) => new TableRow({
    children: [
      new TableCell({
        width: { size: 3200, type: WidthType.DXA },
        shading: { fill: idx % 2 === 0 ? C.light : C.white, type: ShadingType.CLEAR },
        borders: allBorders("CCCCCC", 4),
        margins: { top: 80, bottom: 80, left: 160, right: 160 },
        children: [p(code(col1))],
      }),
      new TableCell({
        width: { size: 6160, type: WidthType.DXA },
        shading: { fill: idx % 2 === 0 ? C.light : C.white, type: ShadingType.CLEAR },
        borders: allBorders("CCCCCC", 4),
        margins: { top: 80, bottom: 80, left: 160, right: 160 },
        children: [p(run(col2, { size: 19 }))],
      }),
    ],
  }));

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [3200, 6160],
    rows: [new TableRow({ children: headerCells }), ...dataRows],
  });
};

// ── 3-col table ────────────────────────────────────────────────────────────
const threeColTable = (rows, headerLabels, widths = [2400, 4000, 2960]) => {
  const total = widths.reduce((a, b) => a + b, 0);
  const headerCells = headerLabels.map((label, i) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: { fill: C.teal, type: ShadingType.CLEAR },
    borders: allBorders(C.teal, 6),
    margins: { top: 100, bottom: 100, left: 160, right: 160 },
    children: [p(run(label, { bold: true, size: 19, color: C.white }))],
  }));

  const dataRows = rows.map(([c1, c2, c3], idx) => new TableRow({
    children: [c1, c2, c3].map((val, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: idx % 2 === 0 ? C.light : C.white, type: ShadingType.CLEAR },
      borders: allBorders("CCCCCC", 4),
      margins: { top: 80, bottom: 80, left: 160, right: 160 },
      children: [p(run(val, { size: 18, font: i === 0 ? "Courier New" : "Arial", color: i === 0 ? C.purple : "000000" }))],
    })),
  }));

  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [new TableRow({ children: headerCells }), ...dataRows],
  });
};

// ── Spacer ─────────────────────────────────────────────────────────────────
const spacer = (before = 160) => new Paragraph({ children: [run("")], spacing: { before } });

// ══════════════════════════════════════════════════════════════════════════════
// DOCUMENT SECTIONS
// ══════════════════════════════════════════════════════════════════════════════

const coverPage = [
  spacer(2800),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("Vibe Trading", { bold: true, size: 72, color: C.navy })],
    spacing: { after: 120 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("India Trade CLI", { bold: true, size: 48, color: C.teal })],
    spacing: { after: 240 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.gold, space: 6 } },
    children: [run("")],
    spacing: { after: 240 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("Complete Feature Reference & Test Guide", { bold: true, size: 32, color: C.gray })],
    spacing: { after: 120 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("AI-Powered Multi-Agent Stock & Options Analysis Platform for Indian Markets", { size: 22, color: C.gray, italics: true })],
    spacing: { after: 480 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("Version: feat/overnight-batch  |  May 2026  |  For Codex Review", { size: 20, color: C.gray })],
  }),
  pageBreak(),
];

// ── 1. Introduction ─────────────────────────────────────────────────────────
const introSection = [
  h1("1. Introduction"),
  bodyP("Vibe Trading (india-trade-cli) is a terminal-first, AI-powered trading platform built for Indian equity and derivatives markets (NSE/BSE/NFO). It combines a rich interactive REPL, a multi-agent AI analyst team, a 26-strategy template library, full backtesting with advanced validation, real-time broker integration, and a FastAPI sidecar that drives an Electron macOS desktop app."),
  spacer(),
  h2("1.1 Architecture Overview"),
  threeColTable([
    ["CLI / REPL",       "app/repl.py + app/commands/",   "Primary user interface — prompt_toolkit REPL with Rich output"],
    ["Agent Layer",      "agent/",                         "LLM orchestration, multi-agent debate, tool calling, personas"],
    ["Market Layer",     "market/",                        "Live quotes, options chain, news, FII/DII, breadth, indices"],
    ["Analysis Layer",   "analysis/",                      "Technical, fundamental, DCF, GEX, volatility, ML, feature pipeline"],
    ["Engine Layer",     "engine/",                        "Backtesting, paper trading, alerts, risk gate, trade memory, strategy"],
    ["Broker Layer",     "brokers/",                       "Zerodha, Fyers, Groww, Angel One, Upstox, Mock broker"],
    ["Web / API Layer",  "web/",                           "FastAPI sidecar on :8765 — SSE streaming, macOS app backend"],
    ["Config Layer",     "config/",                        "Credentials (keychain), API keys, onboarding"],
  ], ["Layer", "Path", "Purpose"], [2400, 2600, 4360]),
  spacer(),
  h2("1.2 Launch Modes"),
  twoColTable([
    ["trade",            "Default — starts interactive REPL after broker login"],
    ["trade --no-broker","Skip broker login; use yfinance for market data (demo mode)"],
    ["trade --tui",      "Launch split-panel Textual TUI dashboard instead of REPL"],
  ]),
  spacer(),
  h2("1.3 Supported Brokers"),
  twoColTable([
    ["Zerodha (Kite Connect)", "OAuth browser redirect; India's largest retail broker"],
    ["Fyers",                  "OAuth redirect; strong options data; preferred for data role"],
    ["Groww",                  "OAuth2 redirect; newer entrant"],
    ["Angel One (SmartAPI)",   "TOTP auto-login — no browser redirect needed"],
    ["Upstox",                 "OAuth2, API v3"],
    ["Mock / Demo",            "No credentials needed; yfinance for prices; demo holdings/orders"],
  ], ["Broker", "Notes"]),
  spacer(),
  noteBox("Dual-broker mode: connect Fyers (data role) + Zerodha (execution role) simultaneously. Market data routes to Fyers; orders route to Zerodha. Auto-assigned when both are connected.", C.tealBg, C.teal),
  pageBreak(),
];

// ── 2. REPL Commands ─────────────────────────────────────────────────────────
const replSection = [
  h1("2. REPL Command Reference"),
  bodyP("After launch the platform drops into a prompt_toolkit REPL with tab-completion, coloured output, and persistent history (~/.trading_platform/.repl_history). Every command listed below is directly testable by typing it at the trade> prompt."),

  h2("2.1 Broker & Account Management"),
  twoColTable([
    ["login",               "Interactive broker selection. Presents numbered menu (0–5: Zerodha, Fyers, Groww, Angel One, Upstox, Demo). Triggers OAuth redirect or TOTP auto-login. Saves session token to keychain."],
    ["login zerodha",       "Skip menu; go straight to Zerodha OAuth flow."],
    ["connect <broker>",    "Add a secondary broker without replacing the primary. E.g. 'connect fyers' after logging into Zerodha. Both show up in 'brokers'."],
    ["disconnect <broker>", "Remove a secondary broker connection from the session."],
    ["brokers",             "List all connected brokers: name, role (DATA/EXECUTION/BOTH), available cash, authentication status."],
    ["logout",              "Disconnect all brokers and clear in-memory session tokens."],
    ["profile",             "Show primary broker account profile: user ID, name, email, broker name, exchanges enabled."],
    ["funds",               "Available cash, used margin, total balance from primary broker. Shows collateral value if pledged."],
    ["holdings",            "Long-term delivery (CNC) holdings: symbol, quantity, avg buy price, LTP, current value, P&L (absolute and %), day change."],
    ["positions",           "Open intraday and F&O positions: symbol, buy/sell, quantity, avg price, LTP, unrealized P&L, product (MIS/NRML)."],
    ["orders",              "Today's orders with ID, symbol, type, quantity, price, status (COMPLETE/OPEN/CANCELLED/REJECTED), timestamp."],
    ["portfolio",           "Unified view across all connected brokers: combined holdings, open positions, aggregate Greeks (Delta/Gamma/Theta/Vega), risk meter (0–100), margin usage."],
    ["paper",               "Show paper trading mode status (ON/OFF) and simulated portfolio cash."],
  ]),
  spacer(),

  h2("2.2 Market Data & Quotes"),
  twoColTable([
    ["quote RELIANCE",      "Live price snapshot: LTP, open, high, low, close, volume, day change (absolute and %), 52-week range. Works for NSE equities and F&O (NSE:NIFTY 50, NSE:NIFTY BANK, etc.)."],
    ["quote NIFTY",         "NIFTY 50 index quote. Auto-expands to NSE:NIFTY 50."],
    ["morning-brief",       "Daily AI-generated market briefing. Calls agent which runs: market snapshot → top 5 news → FII/DII flows → breadth → upcoming events → narrative synthesis. Shows GIFT NIFTY pre-market indicator, VIX regime, actionable agenda."],
    ["morning-brief --raw", "Skip AI narrative; print raw structured data directly (faster, no API key required)."],
    ["active",              "Top 10 NSE stocks by volume. Shows symbol, LTP, volume, change %."],
    ["active --by value",   "Top 10 by traded value (INR crore)."],
    ["earnings",            "Upcoming earnings calendar for NIFTY 50 companies. Shows company, earnings date, time (pre/post), avg historical move %, last 4 quarterly EPS."],
    ["events",              "Upcoming market events (7 days): weekly + monthly F&O expiry, RBI MPC dates, budget dates, earnings today."],
    ["flows",               "FII/DII flow intelligence: last 5 days net activity, buying/selling streaks, divergence (FII selling + DII buying = possible bottom), trading signal."],
    ["bulk-deals",          "Recent bulk and block deals from NSE. Shows acquirer/seller, company, price, quantity, % of total holding, deal type."],
    ["scan",                "F&O options scanner. Scans all F&O stocks for: high IV rank (>70), unusual OI buildup, put writing activity. Shows top 10 with IV rank, PCR, ATM IV, volume surge."],
  ]),
  spacer(),

  h2("2.3 Deep Analysis Commands"),
  twoColTable([
    ["analyze INFY",        "Full multi-agent analysis. Runs 5 specialized analysts in parallel (Technical, Fundamental, Options, News/Macro, Risk Manager), then LLM debate (bull vs bear), then final synthesis. Outputs: verdict, confidence, entry/SL/target, key risks, trade rationale."],
    ["analyze INFY --quick","Quick analysis: skip debate phase; direct synthesis from analyst reports. ~30 seconds vs ~2 minutes for full."],
    ["quick INFY",          "5-second quick sentiment scan: RSI level, FII net, news headline count, IV rank. Returns BULLISH/NEUTRAL/BEARISH."],
    ["sentiment INFY",      "Detailed sentiment aggregator: FII/DII flows (30%), news sentiment (25%), bulk deals (25%), market breadth (20%). Shows each component score and combined verdict."],
    ["fundamentals INFY",   "Structured fundamentals scorer with India-adjusted thresholds: ROE, ROCE, revenue growth, PAT growth, margins, D/E, promoter %, pledge %, dividend yield, FCF. Score -1.0 to +1.0 per metric. STRONG/NEUTRAL/WEAK signal."],
    ["dcf INFY",            "DCF valuation: revenue growth assumptions, terminal growth rate, WACC, intrinsic value, margin of safety %, sensitivity table (best/base/worst case). Shows whether stock is undervalued/overvalued vs LTP."],
    ["gex NIFTY",           "Gamma Exposure analysis. Shows: total dealer gamma (INR crore), GEX by strike (bar chart), gamma flip point (support when positive, resistance when negative), market regime (POSITIVE = pinning/low vol; NEGATIVE = breakout/high vol)."],
    ["oi NIFTY",            "Open Interest profile. Shows OI per strike for next expiry: call OI (resistance), put OI (support), PCR per strike. Highlights max call OI (overhead resistance) and max put OI (underlying support)."],
    ["patterns INFY",       "Chart pattern scanner: triangles (ascending/descending/symmetrical), head and shoulders, double top/bottom, flags, pennants, wedges. Shows pattern, entry, stop-loss, target."],
    ["mtf INFY",            "Multi-timeframe analysis: daily trend, weekly trend, monthly trend. Checks EMA alignment and RSI across timeframes. BULLISH if all 3 aligned up."],
    ["ensemble INFY",       "Signal ensemble: weights 5 strategies (Trend 25%, Mean Reversion 20%, Momentum 25%, Volatility 15%, Statistical 15%). Returns BULLISH/NEUTRAL/BEARISH + confidence + per-strategy breakdown."],
    ["pairs RELIANCE TCS",  "Pairs trading analysis: rolling 60-day correlation, spread Z-score, mean reversion signal. BUY spread if Z > 2 (RELIANCE cheap vs TCS), SELL spread if Z < -2."],
    ["deep-analyze INFY",   "Extended analysis with full 5-agent → debate → synthesis pipeline plus web search for latest news and a second synthesis pass. Takes 3–5 minutes."],
    ["debate INFY",         "5-investor debate. Each persona (Buffett, Jhunjhunwala, Lynch, Soros, Munger) analyzes INFY independently. Shows each verdict + confidence + top 3 reasons. AI synthesizes consensus."],
    ["persona buffett INFY","Single persona analysis. Applies Warren Buffett's checklist: ROE, D/E, FCF yield, moat assessment. Shows pass/fail per criterion, Buffett-style narrative."],
  ]),
  spacer(),

  h2("2.4 Options-Specific Commands"),
  twoColTable([
    ["oi NIFTY",              "OI profile for NIFTY: all strikes, call OI, put OI, OI change, PCR per strike, max pain strike."],
    ["scan",                  "Options scanner across all F&O stocks: high IV rank, OI buildup signals, put writing."],
    ["roll-options",          "Suggest rolling open options positions to next expiry: shows current leg, suggested roll-to leg, debit/credit for the roll, new breakeven."],
    ["iv-smile NIFTY",        "IV smile / skew visualization for NIFTY options: plots IV across strikes from ATM, shows call-put skew direction."],
    ["get_pcr NIFTY",         "Put-Call Ratio via agent tool. >1.2 = bearish sentiment; <0.8 = bullish sentiment."],
    ["get_max_pain NIFTY",    "Max pain strike: where aggregate option buyer losses are maximized. Often acts as magnet into expiry."],
  ]),
  spacer(),

  h2("2.5 Trading Commands"),
  twoColTable([
    ["trade",                 "Launches interactive guided trade builder. Prompts: symbol → view (BULLISH/BEARISH/NEUTRAL) → strategy recommendation → risk check → stop-loss → confirmation → order placement. Full flow described in Section 5."],
    ["trade RELIANCE",        "Skip symbol prompt; jump straight to view selection for RELIANCE."],
    ["buy RELIANCE 10",       "Quick buy: 10 shares of RELIANCE at market. Runs risk check first. Requires confirmation in live mode. Skips confirmation in paper mode."],
    ["sell RELIANCE 10",      "Quick sell: 10 shares of RELIANCE at market."],
    ["cancel <order_id>",     "Cancel an open order by ID (visible in 'orders' output)."],
    ["whatif 5",              "Simulate: if NIFTY drops/rises 5%, what happens to my portfolio? Shows position-wise P&L impact and net portfolio change."],
    ["whatif INFY 10",        "Simulate: if INFY rises 10%, what happens to positions involving INFY?"],
  ]),
  spacer(),

  h2("2.6 Risk & Greeks Commands"),
  twoColTable([
    ["greeks",                "Portfolio Greeks dashboard: net Delta, Gamma, Theta (daily decay in INR), Vega. Breakdown by underlying. Color-coded risk level (GREEN/YELLOW/RED)."],
    ["delta-hedge",           "Suggest trades to neutralize portfolio delta (target = 0). Shows instrument + quantity to hedge, approximate cost, new expected delta after hedge."],
    ["delta-hedge 0.5",       "Suggest trades to achieve target delta of 0.5 instead of delta-neutral."],
    ["risk-status",           "Current risk status: daily P&L vs daily loss cap, trades today vs max trades cap, open position count vs limits. Shows RED/YELLOW/GREEN status for each."],
    ["risk-report",           "Full risk analysis: VIX regime, concentration risk (top 3 positions as % of portfolio), beta-weighted delta, earnings exposure, margin usage, actionable recommendations."],
  ]),
  spacer(),

  h2("2.7 Alerts Commands"),
  twoColTable([
    ["alert",                 "Interactive alert builder. Prompts: symbol → alert type (price/technical/conditional) → condition → threshold. Creates and registers alert."],
    ["alert RELIANCE ABOVE 2800", "Quick price alert: triggers when RELIANCE price crosses above 2800."],
    ["alert INFY RSI BELOW 30",  "Quick technical alert: triggers when INFY RSI-14 falls below 30."],
    ["alerts",                "List all active (non-triggered) alerts with ID, symbol, condition, threshold, created time."],
    ["alerts remove <id>",    "Remove alert by ID."],
  ]),
  spacer(),

  h2("2.8 Memory & Learning Commands"),
  twoColTable([
    ["memory",                "View trade memory: last 10 analyses stored. Shows symbol, timestamp, verdict, confidence, outcome (if recorded), lesson."],
    ["memory stats",          "Aggregate memory statistics: total analyses, outcomes recorded, win rate %, total P&L, avg confidence, verdict distribution, top analyzed symbols."],
    ["search INFY",           "Full-text search over past analyses: finds all records mentioning INFY or related terms."],
    ["explain rsi divergence","Ask the AI to explain a concept, indicator, or trade in plain English."],
  ]),
  spacer(),

  h2("2.9 System & AI Commands"),
  twoColTable([
    ["ai <message>",          "Chat directly with the trading AI. Free-form: 'What is an iron condor?', 'Should I buy NIFTY calls today?', 'Explain the VIX spike yesterday.'"],
    ["provider",              "Show current AI provider (Anthropic/OpenAI/Gemini/Ollama) and model. Lists all configured providers."],
    ["provider openai",       "Switch AI provider to OpenAI GPT-4o for this session."],
    ["credentials",           "Manage API credentials: list saved keys, add/update key, clear all. Keys stored in macOS Keychain or secure config."],
    ["credentials list",      "Show all saved credential keys (masked values)."],
    ["credentials clear",     "Wipe all saved credentials and tokens. Requires re-login."],
    ["telegram",              "Configure Telegram push notifications: enter bot token + chat ID. Test notification sent immediately."],
    ["audit",                 "Broker API audit: lists all available broker API methods and whether they're working (authorized/unauthorized/error)."],
    ["tui",                   "Launch split-panel Textual TUI: market dashboard, chart panel, orders panel, chat panel. Full keyboard navigation."],
    ["web",                   "Start FastAPI web server on port 8765. Powers the macOS Electron app. Exposes /api/status, /api/portfolio, /stream/prices, /stream/alerts endpoints."],
    ["clear",                 "Clear terminal screen."],
    ["help",                  "Print command reference table."],
    ["quit / exit",           "Exit the platform gracefully. Closes broker WebSocket connections and flushes state."],
  ]),
  pageBreak(),
];

// ── 3. Strategy System ────────────────────────────────────────────────────────
const strategySection = [
  h1("3. Strategy System"),

  h2("3.1 Strategy Library (26 Templates)"),
  bodyP("The strategy library provides 26 pre-built options and equity strategy templates, organized into 5 categories. Each template includes a full explanation, when-to-use criteria, P&L profile, ideal IV/DTE range, and cached backtest results."),
  spacer(),
  noteBox("Access via: strategy library | strategy library bullish | strategy library --type options", C.goldBg, C.gold),
  spacer(),

  h3("Browse & Learn Commands"),
  twoColTable([
    ["strategy library",              "Show all 26 templates: ID, name, category, best market views, ideal IV, DTE range, complexity (beginner/intermediate/advanced)."],
    ["strategy library bullish",      "Filter to bullish templates only. Categories: bullish, bearish, income, volatility, hedging."],
    ["strategy library --type options","Show only options strategies (vs. equity/technical)."],
    ["strategy learn iron_condor",    "Full explanation panel: legs, entry criteria, P&L diagram description, max profit/loss, breakeven(s), greeks, when to use, risks, cached backtest P&L."],
    ["strategy use iron_condor NIFTY","Apply iron condor template to live NIFTY data. Fetches ATM price, calculates strikes (±1 SD), shows legs with LTPs, capital required, max profit/loss/breakeven, R:R ratio."],
    ["strategy use iron_condor NIFTY --lots 2 --dte 30", "Apply with 2 lots and 30 DTE preference."],
  ]),
  spacer(),

  h3("Template Categories"),
  threeColTable([
    ["long_call",           "Bullish",     "Buy ATM call. Unlimited upside, defined risk. Best when IV low, directional view."],
    ["bull_call_spread",    "Bullish",     "Buy ATM call + sell OTM call. Cheaper than long call, capped upside. Beginner-friendly."],
    ["synthetic_long",      "Bullish",     "Buy call + sell put same strike. Synthetic stock position, less capital."],
    ["call_ratio_spread",   "Bullish",     "Buy 1 ATM call, sell 2 OTM calls. Net credit/low debit. Advanced."],
    ["long_put",            "Bearish",     "Buy ATM put. Defined risk, unlimited downside profit. Best when IV low."],
    ["bear_put_spread",     "Bearish",     "Sell OTM put + buy lower OTM put. Credit strategy, defined risk. Beginner."],
    ["bear_call_spread",    "Bearish",     "Sell ATM call + buy OTM call. Credit on bearish outlook."],
    ["put_ratio_spread",    "Bearish",     "Sell 1 put + buy 2 lower puts. Advanced bearish play."],
    ["covered_call",        "Income",      "Own stock + sell OTM call. Generates premium income, caps upside."],
    ["cash_secured_put",    "Income",      "Sell put + hold cash. Income if stock stays above strike. Buy-the-dip income."],
    ["iron_butterfly",      "Income",      "Sell ATM strangle + buy OTM wings. High income, tight profit zone."],
    ["call_calendar_spread","Income",      "Sell near call + buy far call. Time-decay play with volatility expansion."],
    ["long_straddle",       "Volatility",  "Buy ATM call + put. Profits on large move either way. Buy before events."],
    ["short_straddle",      "Volatility",  "Sell ATM call + put. Income on range-bound market. High risk, advanced."],
    ["long_strangle",       "Volatility",  "Buy OTM call + put. Cheaper than straddle, wider breakevens."],
    ["short_strangle",      "Volatility",  "Sell OTM call + put. Premium income. Defined loss if broken."],
    ["iron_condor",         "Volatility",  "4-leg: sell OTM strangle + buy wider OTM wings. Credit, range-bound."],
    ["protective_put",      "Hedging",     "Own stock + buy put. Downside protection, keep unlimited upside."],
    ["collar",              "Hedging",     "Own stock + buy put + sell call. Downside protection at low/no cost."],
    ["protective_call",     "Hedging",     "Short stock + buy call. Caps loss on short position."],
  ], ["Template ID", "Category", "Summary"], [2800, 1800, 4760]),
  spacer(),

  h2("3.2 Custom Strategy Builder"),
  bodyP("Build fully custom algorithmic strategies through an AI-guided multi-turn conversation. The strategy is expressed as a Python class, backtested, and saved to disk."),
  spacer(),
  h3("Creation Flow"),
  twoColTable([
    ["strategy new",                  "Start interactive strategy builder. AI asks: description → type (momentum/mean-reversion/options/pairs) → symbol → data period."],
    ["strategy new 'RSI oversold'",   "Skip description prompt; describe inline."],
    ["strategy new --simple",         "Plain-language mode: simpler questions, no jargon."],
  ]),
  spacer(),
  h3("Strategy Management"),
  twoColTable([
    ["strategy list",                 "List all saved strategies: name, description, symbol, created date, last backtest CAGR, last backtest Sharpe."],
    ["strategy show my_rsi",          "Display strategy Python code, metadata, and last backtest result."],
    ["strategy backtest my_rsi",      "Re-backtest saved strategy on 1-year period. Shows total return, CAGR, Sharpe, max drawdown, win rate."],
    ["strategy backtest my_rsi --period 2y", "Backtest on 2-year lookback."],
    ["strategy run my_rsi",           "Generate today's signal from saved strategy. Shows BUY/SELL/NEUTRAL with confidence."],
    ["strategy run my_rsi INFY --paper","Generate signal and place paper trade if BUY/SELL signal."],
    ["strategy delete my_rsi",        "Remove strategy and its metadata from disk."],
    ["strategy export my_rsi --pine", "Export to TradingView Pine Script v5. Shows generated code ready to paste into TradingView."],
  ]),
  pageBreak(),
];

// ── 4. Multi-Agent Analysis ───────────────────────────────────────────────────
const agentSection = [
  h1("4. Multi-Agent Analysis Architecture"),
  bodyP("The analyze command triggers a multi-phase pipeline. Phase 1 runs 5 specialized Python analysts in parallel (no LLM calls — pure data). Phase 2 runs a structured LLM debate (2 calls). Phase 3 synthesizes a final recommendation (1 LLM call). Total: 3 LLM calls for full analysis."),
  spacer(),

  h2("4.1 Phase 1: Analyst Team (Parallel, Pure Data)"),
  bodyP("Five analysts run concurrently via ThreadPoolExecutor. Each returns an AnalystReport with verdict, confidence (0–100), score (-100 to +100), key points, and raw data."),
  spacer(),
  threeColTable([
    ["Technical Analyst",     "RSI-14, MACD, EMA20/50, SMA200, Bollinger Bands, ATR, support/resistance levels, pivot points, ADX trend strength",  "Score: -100 (oversold/bearish) to +100 (overbought/bullish). Verdict: BULLISH/BEARISH/NEUTRAL."],
    ["Fundamental Analyst",   "PE ratio, PB ratio, ROE, ROCE, net profit margin, revenue growth, debt/equity, FCF yield, promoter %, FII %, pledge %, analyst consensus",  "Score: 0–100 on India-adjusted thresholds. Verdict: STRONG/NEUTRAL/WEAK."],
    ["Options Analyst",       "IV rank (0–100), PCR, max pain strike, OI profile, ATM Greeks (delta, gamma, theta, vega), volatility regime",  "IV rank >70 = sell premium; IV rank <30 = buy options. Verdict: BEARISH/NEUTRAL/BULLISH."],
    ["News & Macro Analyst",  "FII/DII net (last 5 days), bulk/block deals, earnings calendar (3-day proximity), market breadth (A/D ratio), top 5 news headlines",  "Aggregated sentiment: BULLISH/NEUTRAL/BEARISH. Flags EARNINGS_PROXIMITY if <3 days."],
    ["Risk Manager",          "Daily P&L vs cap, trade count vs limit, VIX regime (>20 = high), position concentration, leverage check",  "Flags: HIGH_VOLATILITY, DAILY_LOSS_CAP, TRADE_LIMIT, POSITION_LIMIT. Verdict: ALLOW/WARN/BLOCK."],
  ], ["Analyst", "Data Consumed", "Output"], [2200, 4000, 3160]),
  spacer(),

  h2("4.2 Phase 2: LLM Debate"),
  twoColTable([
    ["Bullish Researcher",  "Given all 5 analyst reports, constructs the strongest possible BUY case. 3–5 specific reasons with supporting data points."],
    ["Bearish Researcher",  "Constructs the strongest SELL/AVOID case. Addresses and rebuts bullish points."],
    ["Facilitator",         "Summarizes key agreements and disagreements. Awards winner (BULL or BEAR). States what would change the outcome."],
  ], ["Role", "Description"]),
  spacer(),

  h2("4.3 Phase 3: Synthesis (Final Recommendation)"),
  bodyP("A Fund Manager persona weighs the debate outcome, analyst scorecard, and user's risk profile to produce the final recommendation:"),
  bullet("Verdict: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL"),
  bullet("Confidence: 0–100%"),
  bullet("Strategy: specific options or equity strategy"),
  bullet("Entry: price level (or 'at market')"),
  bullet("Stop-Loss: specific price (mandatory)"),
  bullet("Target: price with timeline"),
  bullet("Capital: INR amount recommended"),
  bullet("Risk-Reward Ratio"),
  bullet("Rationale: 3–5 sentence explanation"),
  spacer(),

  h2("4.4 DAG-Based Agent Swarm (#182)"),
  bodyP("Advanced mode: build custom analyst teams with dependency graphs. A topological sort (Kahn's algorithm) ensures analysts run in the correct order, with wave-based parallelism."),
  spacer(),
  h3("Preset DAGs"),
  twoColTable([
    ["fast",            "2 analysts: Technical + Risk. ~5 seconds."],
    ["full",            "All 7 analysts in dependency order. ~60 seconds."],
    ["options_focused", "Options + Technical + Risk: specialized for F&O decisions."],
    ["quick_trade",     "Technical + News/Macro + Risk: quick trade setup."],
  ]),
  spacer(),

  h2("4.5 Investor Personas (#165)"),
  bodyP("Five named investor personas, each with unique investment philosophies, weights, and checklists:"),
  spacer(),
  threeColTable([
    ["buffett",       "Warren Buffett",       "Value + moat. Weights: Fundamentals 65%, Macro 10%, Technicals 5%, Sentiment 10%, Options 10%. Checklist: ROE >15%, D/E <0.5, FCF yield >5%, durable competitive moat, pricing power, understandable business, quality management."],
    ["jhunjhunwala",  "Rakesh Jhunjhunwala",  "India macro + growth. Focus: India earnings trajectory, promoter quality, sectoral mega-themes (infra, pharma, defence), macro tailwinds. Growth-value hybrid."],
    ["lynch",         "Peter Lynch",          "GARP (Growth At Reasonable Price). Checklist: PEG ratio <1.0, explainable in 2 minutes, low institutional ownership (room to grow), growth trajectory intact."],
    ["soros",         "George Soros",         "Macro reflexivity + flow. Focus: participant bias creating reflexive loops, FII net flows, INR trend, boom-bust cycle positioning. Event-driven."],
    ["munger",        "Charlie Munger",        "Quality + inversion. Focus: management incentive alignment, accounting quality, complexity red flags, low leverage, invert and ask 'what could go wrong?'"],
  ], ["ID", "Persona", "Philosophy & Checklist"], [1400, 2000, 5960]),
  pageBreak(),
];

// ── 5. Trade Execution Flow ───────────────────────────────────────────────────
const tradeSection = [
  h1("5. Guided Trade Execution Flow"),
  bodyP("The 'trade' command implements a 9-step guided flow designed to prevent impulsive trading. Every step has safeguards: risk limits are enforced before order placement and explicit confirmation is always required."),
  spacer(),

  h2("5.1 Step-by-Step Flow"),
  twoColTable([
    ["Step 1: Symbol",      "User enters NSE symbol (e.g., RELIANCE, NIFTY, BANKNIFTY). Auto-suggests from recent analyses."],
    ["Step 2: View",        "User declares market view: BULLISH / BEARISH / NEUTRAL. This filters strategy recommendations."],
    ["Step 3: Live Data",   "Platform fetches LTP, IV rank, ATM strike, expiry. Displays: current price, capital available, max risk per trade (from risk limits), VIX level."],
    ["Step 4: Recommendations","Agent recommends top 3 strategies matching the view, sorted by fit score. Each shows: name, description, capital needed, max profit/loss, R:R ratio, best-for criteria."],
    ["Step 5: Selection",   "User picks strategy 1, 2, or 3. Platform fetches live option prices for all legs."],
    ["Step 6: Trade Summary","Full trade plan: each leg with instrument, action, quantity, LTP; total debit/credit; max profit, max loss, breakeven(s), R:R ratio."],
    ["Step 7: Risk Check",  "Runs deterministic RiskGate. If max_loss > daily_risk_cap: shows WARNING, asks for explicit override confirmation. If VIX >20: HIGH_VOLATILITY warning. If near earnings: EARNINGS_PROXIMITY warning."],
    ["Step 8: Stop-Loss",   "User must enter a stop-loss price. Platform warns if stop is >10% wide or >2× ATR. Default suggestion: 5% for directional, 10% for spreads."],
    ["Step 9: Confirmation","Prints final order summary. Asks 'Confirm trade? (yes/no)'. Only 'yes' proceeds. Any other input cancels. In live mode: places real orders. In paper mode: simulates fills."],
  ]),
  spacer(),

  h2("5.2 Risk Gate — Pre-Trade Checks"),
  bodyP("The RiskGate runs deterministically before every order recommendation. It does not require an LLM call. It returns an AllowedAction object that caps quantities and adds flags."),
  spacer(),
  threeColTable([
    ["Daily Loss Cap",       "Has today's realized P&L exceeded the daily loss limit?",    "BLOCK if yes. MAX_QTY = 0."],
    ["Trade Count Cap",      "Has trade count today exceeded the daily maximum?",           "BLOCK if yes."],
    ["Earnings Proximity",   "Is there an earnings event within 3 trading days?",           "FLAG: EARNINGS_PROXIMITY. Halve max_qty."],
    ["Position Limit",       "Would this trade make any single position >10% of capital?", "FLAG: POSITION_LIMIT. Cap qty accordingly."],
    ["Cash Check",           "Is there enough cash for at least 1 share/contract?",        "BLOCK if insufficient funds."],
    ["VIX Regime",           "Is India VIX above 20 (danger zone)?",                       "FLAG: HIGH_VOLATILITY. Halve max_qty."],
  ], ["Check", "Condition", "Action"], [2400, 4000, 2960]),
  pageBreak(),
];

// ── 6. Backtesting ────────────────────────────────────────────────────────────
const backtestSection = [
  h1("6. Backtesting Engine"),

  h2("6.1 Built-In Strategies"),
  twoColTable([
    ["rsi",       "RSI Mean Reversion. BUY when RSI-14 < 30 (oversold); SELL when RSI-14 > 70 (overbought). Configurable: buy_level, sell_level, period."],
    ["ma",        "EMA Crossover. BUY when EMA-20 crosses above EMA-50; SELL when crosses below. Configurable: fast_period, slow_period."],
    ["macd",      "MACD Signal Cross. BUY when MACD line crosses above signal line; SELL when crosses below. Standard 12/26/9 parameters."],
    ["bb",        "Bollinger Band Reversion. BUY at lower band (mean − 2σ); SELL at upper band (mean + 2σ). 20-period SMA."],
  ]),
  spacer(),

  h2("6.2 Backtest Output Metrics"),
  twoColTable([
    ["total_return",      "Cumulative % return over the period."],
    ["CAGR",              "Compound Annual Growth Rate (annualized return)."],
    ["Sharpe Ratio",      "Risk-adjusted return: (CAGR − risk_free) / annualized_std. >1.0 = good; >2.0 = excellent."],
    ["max_drawdown",      "Largest peak-to-trough decline %. Shows date of maximum drawdown."],
    ["win_rate",          "% of trades that were profitable."],
    ["profit_factor",     "Gross profit / gross loss. >1.5 = acceptable; >2.0 = good."],
    ["avg_win / avg_loss","Average winning trade % and average losing trade %."],
    ["avg_hold_days",     "Average duration of each trade in calendar days."],
    ["buy_hold_return",   "Benchmark: if you just bought and held for the period, what would the return be?"],
    ["total_trades",      "Number of completed round-trip trades."],
  ]),
  spacer(),
  noteBox("Run: backtest RELIANCE rsi --period 2y    or via agent: 'run_backtest' tool", C.goldBg, C.gold),
  spacer(),

  h2("6.3 Advanced Backtest Validation (#186)"),
  bodyP("Three advanced validation engines sit on top of the core backtester, designed to test strategy robustness and detect overfitting."),
  spacer(),
  h3("Monte Carlo Simulation"),
  bullet("Shuffles trade P&L returns 1,000 times to build a return distribution."),
  bullet("Outputs: CAGR percentiles (p5/p25/p50/p75/p95), Sharpe percentiles, max drawdown percentiles."),
  bullet("Key metric: prob_positive_return (% of simulations with positive total return)."),
  bullet("Key metric: prob_beat_nifty (% of simulations beating 12% benchmark)."),
  spacer(),
  h3("Bootstrap Confidence Intervals"),
  bullet("Resamples trades WITH replacement 1,000 times."),
  bullet("Computes 95% CI for Sharpe ratio and CAGR."),
  bullet("Key metric: is_statistically_significant — true if Sharpe 95% CI does not straddle zero."),
  spacer(),
  h3("Walk-Forward Validation"),
  bullet("Rolls train/test windows: default 12-month train, 3-month test."),
  bullet("Outputs: per-window metrics, consistency_ratio (% of test windows profitable), in-sample CAGR vs out-of-sample CAGR."),
  bullet("Key metric: overfitting_ratio = out_of_sample_cagr / in_sample_cagr. <0.5 = overfit warning."),
  spacer(),

  h2("6.4 Regime Analysis (#180)"),
  bodyP("Analyze backtest performance broken down by market regime — does your strategy work in bull markets but fail in bear markets?"),
  spacer(),
  bullet("Regimes: BULL (price > SMA200 + positive 20-day momentum), BEAR (price < SMA200 + negative momentum), SIDEWAYS (other)."),
  bullet("Each regime shows: trade count, win rate %, avg return %, total return %, Sharpe ratio, best/worst trade, coverage % of period."),
  bullet("Use to identify regime-dependent strategies and add regime filters."),
  pageBreak(),
];

// ── 7. Position Sizing & VaR ──────────────────────────────────────────────────
const sizingSection = [
  h1("7. Position Sizing & Portfolio Risk"),

  h2("7.1 Volatility-Adjusted Position Sizer (#173)"),
  bodyP("A mathematically rigorous position sizing engine that applies Kelly criterion, ATR-based volatility scaling, and portfolio correlation penalty in sequence."),
  spacer(),
  h3("Sizing Steps"),
  threeColTable([
    ["Step 1: Kelly Fraction",       "Kelly = win_rate / avg_loss − (1−win_rate) / avg_win",                                 "Half-Kelly safety cap applied. Prevents over-betting."],
    ["Step 2: Volatility Scalar",    "scalar = target_risk_pct / atr_pct, clamped to [0.25, 2.0]",                          "Reduces size when ATR is high; increases when ATR is low."],
    ["Step 3: Correlation Penalty",  "penalty = max(pairwise_pearson_corr, existing_positions) × 0.5",                       "Reduces size for correlated positions (e.g., adding INFY when TCS already held)."],
    ["Step 4: Final Size",           "final_pct = kelly × scalar × (1 − penalty), clamped to [0, max_position_pct]",        "Default max_position_pct = 10% of capital."],
    ["Step 5: Quantity",             "qty = floor(final_pct × total_capital / current_price), rounded to lot_size",          "Respects F&O lot sizes."],
  ], ["Step", "Formula", "Effect"], [2400, 4000, 2960]),
  spacer(),

  h2("7.2 Portfolio VaR"),
  bullet("Historical-simulation VaR: uses actual daily returns from OHLCV data (no parametric assumptions)."),
  bullet("Outputs: var_1day (INR), var_10day (INR √10 rule), CVaR / Expected Shortfall, volatility_annual."),
  bullet("Default confidence: 95%. Configurable to 99%."),
  spacer(),

  h2("7.3 Strategy Condition Alerts (#108)"),
  bodyP("Create threshold-based alerts that trigger when technical indicators breach specified levels. Backed by a JSON-persisted monitor with background polling."),
  spacer(),
  h3("Supported Conditions"),
  twoColTable([
    ["BB_PCT ABOVE 0.9",      "Bollinger Band %B above 0.9 (near upper band — overbought)"],
    ["BB_PCT BELOW 0.1",      "Bollinger Band %B below 0.1 (near lower band — oversold)"],
    ["VOLUME_RATIO ABOVE 2.0","Volume today is 2× the 20-day average (unusual activity)"],
    ["ADX ABOVE 25",          "ADX trending strength above 25 (strong trend)"],
    ["RSI ABOVE 70",          "RSI-14 above 70 (overbought)"],
    ["RSI BELOW 30",          "RSI-14 below 30 (oversold)"],
  ]),
  bullet("Operators: ABOVE, BELOW, BETWEEN (with min/max threshold)"),
  bullet("Persistence: saved to ~/.trading_platform/strategy_conditions.json"),
  bullet("Polling interval: configurable (default 60 seconds)"),
  pageBreak(),
];

// ── 8. Paper Trading ──────────────────────────────────────────────────────────
const paperSection = [
  h1("8. Paper Trading"),
  bodyP("Paper trading mode provides a full simulated broker experience with the same BrokerAPI interface as real brokers. No real money is at risk. State persists across sessions."),
  spacer(),

  h2("8.1 Activation & State"),
  twoColTable([
    ["paper on",      "Switch to paper mode. All subsequent buy/sell commands simulate orders."],
    ["paper off",     "Return to live mode."],
    ["paper",         "Show current mode status and simulated portfolio cash."],
  ]),
  spacer(),

  h2("8.2 Order Types & Fill Logic"),
  threeColTable([
    ["MARKET",   "Immediate fill at LTP ± 0.05% slippage (buy adds 0.05%, sell subtracts 0.05%).",  "CNC, MIS, NRML"],
    ["LIMIT",    "Fill only if price is favourable: BUY at/below limit price; SELL at/above limit.", "CNC, MIS, NRML"],
    ["SL",       "Stop-loss market — marked OPEN; not auto-triggered in simulation.",                 "MIS, NRML"],
    ["SL-M",     "Stop-loss market — marked OPEN; not auto-triggered in simulation.",                 "MIS, NRML"],
  ], ["Order Type", "Fill Logic", "Products"]),
  spacer(),

  h2("8.3 Margin Model"),
  twoColTable([
    ["CNC (delivery)",      "100% of order value required. No leverage."],
    ["MIS (intraday)",      "20% margin (5× leverage). Auto-squared off at 3:20 PM."],
    ["NRML (F&O overnight)","12% margin (~8× leverage). Held overnight."],
  ]),
  spacer(),
  noteBox("Initial capital: set via TOTAL_CAPITAL env var (default: ₹2,00,000). Resets on 'credentials clear'.", C.goldBg, C.gold),
  pageBreak(),
];

// ── 9. Alerts System ──────────────────────────────────────────────────────────
const alertsSection = [
  h1("9. Alerts System"),

  h2("9.1 Alert Types"),
  twoColTable([
    ["Price Alert",       "Triggers when stock price crosses ABOVE or BELOW a fixed level. E.g.: RELIANCE ABOVE 2800."],
    ["Technical Alert",   "Triggers when a technical indicator (RSI / MACD / ADX / ATR) crosses ABOVE or BELOW a threshold."],
    ["Conditional Alert", "Multiple conditions joined by AND logic. All must be simultaneously true to trigger. E.g.: price ABOVE 2800 AND RSI BELOW 60."],
  ]),
  spacer(),

  h2("9.2 Notification Channels"),
  twoColTable([
    ["Terminal",           "Rich panel notification with alert details + system bell. Always active."],
    ["macOS Desktop",      "Native macOS notification via osascript. Active if running on Darwin."],
    ["Telegram",           "Push to configured Telegram bot. Set up via 'telegram' command. Requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID."],
    ["Webhook",            "HTTP POST to external URL with JSON payload. Used for OpenClaw / third-party integrations."],
  ]),
  spacer(),

  h2("9.3 Evaluation Engine"),
  bullet("Market hours check: only evaluates Mon–Fri 9:15 AM – 3:30 PM IST."),
  bullet("WebSocket real-time: if broker WebSocket is connected, evaluates on every tick."),
  bullet("Polling fallback: background daemon thread polls every 60 seconds (if WebSocket unavailable)."),
  bullet("After trigger: alert fires notifications, is marked triggered, and is auto-removed from active list."),
  pageBreak(),
];

// ── 10. Broker Architecture ───────────────────────────────────────────────────
const brokerSection = [
  h1("10. Broker Architecture"),

  h2("10.1 Multi-Broker Session"),
  bodyP("The platform supports multiple simultaneously connected brokers. Each implements the BrokerAPI interface, allowing seamless switching between execution and data roles."),
  spacer(),
  threeColTable([
    ["Zerodha",    "OAuth browser redirect (Kite Connect v3). Supports equity + F&O. Industry standard.",    "login zerodha"],
    ["Fyers",      "OAuth redirect (Fyers API v3). Excellent options data. Preferred for data role.",        "login fyers"],
    ["Groww",      "OAuth2 redirect. Newer entrant. Equity focus.",                                          "login groww"],
    ["Angel One",  "SmartAPI TOTP auto-login. No browser redirect. Supports equity + F&O.",                 "login angelone"],
    ["Upstox",     "OAuth2 redirect (API v3). Good F&O data.",                                              "login upstox"],
    ["Mock",       "Zero credentials. Uses yfinance for prices. Demo holdings/orders. --no-broker flag.",   "login demo"],
  ], ["Broker", "Notes", "Command"], [1800, 5200, 2360]),
  spacer(),

  h2("10.2 Dual-Broker Role Routing (#178)"),
  bullet("When both Fyers and Zerodha are connected, roles are auto-assigned: Fyers = DATA, Zerodha = EXECUTION."),
  bullet("Market data calls (quotes, options chain, OI) route to the DATA broker."),
  bullet("Order placement calls route to the EXECUTION broker."),
  bullet("Manual override: POST /api/broker/role — set custom roles via web API."),
  bullet("Command: brokers — shows role badge (DATA / EXECUTION / BOTH) next to each connected broker."),
  spacer(),

  h2("10.3 Authentication Flows"),
  twoColTable([
    ["OAuth Redirect",    "Zerodha, Fyers, Groww, Upstox: opens browser tab to broker login page. User authorizes, broker redirects to localhost callback. Token captured automatically."],
    ["TOTP Auto-Login",   "Angel One: platform reads CLIENT_ID, MPIN, TOTP_SECRET from keychain. Computes live TOTP, logs in automatically — no browser needed."],
    ["Credential Storage","All secrets stored in macOS Keychain (python-keyring). Survives restarts. Clear with 'credentials clear'."],
  ]),
  pageBreak(),
];

// ── 11. Web API & SSE Streaming ────────────────────────────────────────────────
const webSection = [
  h1("11. Web API & SSE Streaming"),
  bodyP("The platform includes a FastAPI sidecar (port 8765) that powers the macOS Electron app and any browser-based clients. Start it with the 'web' command in the REPL."),
  spacer(),

  h2("11.1 REST Endpoints"),
  twoColTable([
    ["GET /",                  "Login page with broker buttons for all 6 brokers. Used by macOS app."],
    ["GET /zerodha/login",     "Redirects to Kite OAuth authorization URL."],
    ["GET /zerodha/callback",  "Handles request_token from Kite; completes login; redirects to /status."],
    ["GET /fyers/login",       "Redirects to Fyers OAuth URL."],
    ["GET /fyers/callback",    "Handles auth_code from Fyers; completes login."],
    ["GET /groww/login",       "Redirects to Groww OAuth URL."],
    ["GET /groww/callback",    "Handles Groww auth_code."],
    ["GET /angelone/login",    "TOTP auto-login for Angel One. No redirect needed."],
    ["GET /upstox/login",      "Redirects to Upstox OAuth URL."],
    ["GET /upstox/callback",   "Handles Upstox auth_code."],
    ["GET /demo",              "Activates mock broker (no credentials needed)."],
    ["GET /status",            "HTML status page showing all broker auth states."],
    ["GET /api/status",        "JSON: {broker_name, authenticated, role} for each connected broker."],
    ["GET /api/portfolio",     "JSON: combined holdings, positions, cash across all connected brokers."],
    ["POST /api/broker/role",  "Set broker role: {broker_key, role: 'data'|'execution'|'both'}. Returns updated role assignments."],
  ]),
  spacer(),

  h2("11.2 SSE Streaming Endpoints (#170)"),
  bodyP("Server-Sent Events allow the macOS app / browser to receive real-time price and alert updates without polling."),
  spacer(),
  twoColTable([
    ["GET /stream/prices",  "SSE stream. Content-Type: text/event-stream. Cache-Control: no-cache. Each event: data: {symbol, ltp, change_pct, ts}\\n\\n. Heartbeat every 15s: : heartbeat\\n\\n."],
    ["GET /stream/alerts",  "SSE stream for triggered alerts. Each event: data: {alert_id, symbol, message, ts}\\n\\n."],
  ]),
  spacer(),
  h3("SSEEventBus Architecture"),
  bullet("Pub/sub bus: asyncio Queue per channel subscriber."),
  bullet("Channels: 'price', 'alert', 'order' (extensible)."),
  bullet("Queue overflow: drops oldest event when queue exceeds 100 items."),
  bullet("Thread-safe: publish_sync() wrapper for calling from non-async (broker WebSocket) threads."),
  bullet("Subscriber cleanup: queue removed from channel on client disconnect (generator close)."),
  pageBreak(),
];

// ── 12. AI Feature Pipeline ───────────────────────────────────────────────────
const featurePipelineSection = [
  h1("12. AI Feature Pipeline & ML Analyst"),

  h2("12.1 Standardised Feature Pipeline (#147)"),
  bodyP("A unified cache-first feature computation layer. All analysts and tools call get_features() rather than independently fetching and computing indicators. Guarantees each indicator is computed once per symbol per TTL window."),
  spacer(),
  h3("Computed Features (25 fields)"),
  threeColTable([
    ["ltp, prev_close",       "Price",           "Last traded price and previous day close."],
    ["rsi",                   "Momentum",        "RSI-14 using Wilder's smoothing."],
    ["atr",                   "Volatility",      "Average True Range, 14-period."],
    ["bb_pct",                "Volatility",      "Bollinger %B = (price − lower) / (upper − lower)."],
    ["volume_ratio",          "Volume",          "Today's volume ÷ 20-day average volume."],
    ["ema20, ema50, ema200",  "Trend",           "Exponential moving averages."],
    ["adx",                   "Trend Strength",  "Wilder's ADX-14. >25 = trending."],
    ["momentum_5d, momentum_20d", "Momentum",   "5-day and 20-day price momentum %."],
    ["support, resistance",   "Structure",       "Nearest support and resistance levels."],
    ["macd_hist",             "Momentum",        "MACD histogram (MACD line − signal line)."],
  ], ["Feature(s)", "Category", "Description"], [2600, 1800, 4960]),
  spacer(),
  h3("Cache Behaviour"),
  bullet("TTL: 60 seconds. Cached per (symbol, exchange) key."),
  bullet("Thread-safe: protected by threading.Lock."),
  bullet("Force refresh: get_features('INFY', force_refresh=True)."),
  bullet("Never raises: returns zero-filled FeatureSet on any error — analysts degrade gracefully."),
  spacer(),

  h2("12.2 ML Prediction Analyst (#145)"),
  bodyP("A gradient boosting classifier that predicts whether a stock will be up more than 2% in 5 trading days, trained on 10 OHLCV-derived features."),
  spacer(),
  h3("Model Features (10)"),
  bullet("RSI-14, RSI-7 (short vs long momentum divergence)"),
  bullet("MACD histogram (signal line momentum)"),
  bullet("Bollinger %B (mean reversion position)"),
  bullet("ATR% (normalised volatility)"),
  bullet("Volume ratio (volume vs 20-day average)"),
  bullet("EMA20/50 ratio (trend direction)"),
  bullet("Momentum 5d, Momentum 20d (recent vs medium-term)"),
  bullet("HL range% (intraday range as % of price)"),
  spacer(),
  h3("Training & Prediction"),
  bullet("Target: 1 if price up >2% in next 5 days; 0 otherwise. Last 5 rows excluded (no future data)."),
  bullet("Split: 80/20 chronological train/test (respects time ordering — no data leakage)."),
  bullet("Model: XGBoost (if installed) → GradientBoostingClassifier (sklearn fallback)."),
  bullet("Output: direction (UP/DOWN/NEUTRAL), probability (0–1), confidence_pct (0–100), top 5 feature importances, test accuracy."),
  bullet("Verdict: BULLISH if direction=UP and probability >0.6; BEARISH if DOWN and probability >0.6; else NEUTRAL."),
  pageBreak(),
];

// ── 13. Credentials & Onboarding ─────────────────────────────────────────────
const credentialsSection = [
  h1("13. Credentials & Onboarding"),

  h2("13.1 Credential Keys"),
  bodyP("All credentials are stored in macOS Keychain (python-keyring) under the service 'trading_platform'. The platform auto-loads them at startup before any broker or AI call."),
  spacer(),
  h3("Broker Credentials"),
  threeColTable([
    ["zerodha_api_key",     "Zerodha",    "Kite Connect API key from developer.zerodha.com"],
    ["zerodha_api_secret",  "Zerodha",    "Kite Connect API secret"],
    ["fyers_client_id",     "Fyers",      "Fyers app Client ID from myapi.fyers.in"],
    ["fyers_secret_key",    "Fyers",      "Fyers app secret key"],
    ["groww_client_id",     "Groww",      "Groww API client ID"],
    ["groww_client_secret", "Groww",      "Groww API client secret"],
    ["angel_client_id",     "Angel One",  "Angel One client code"],
    ["angel_mpin",          "Angel One",  "Angel One MPIN (4-digit)"],
    ["angel_totp_secret",   "Angel One",  "TOTP secret for auto-login (from Angel One app)"],
    ["upstox_client_id",    "Upstox",     "Upstox API client ID"],
    ["upstox_client_secret","Upstox",     "Upstox API client secret"],
  ], ["Key", "Broker", "Description"], [2600, 1800, 4960]),
  spacer(),
  h3("AI Provider Keys"),
  twoColTable([
    ["ANTHROPIC_API_KEY",  "Claude (Anthropic) — default AI provider for analysis."],
    ["OPENAI_API_KEY",     "GPT-4o (OpenAI) — alternative AI provider."],
    ["GEMINI_API_KEY",     "Google Gemini — alternative AI provider."],
    ["OLLAMA_HOST",        "Local Ollama endpoint (default: http://localhost:11434) for offline use."],
  ]),
  spacer(),
  h3("Search & News Keys"),
  twoColTable([
    ["EXA_API_KEY",        "Exa neural search — highest quality for financial queries. Priority 1."],
    ["TAVILY_API_KEY",     "Tavily research search — well-structured results. Priority 2."],
    ["PERPLEXITY_API_KEY", "Perplexity Sonar — AI-synthesised answers with citations. Priority 3."],
    ["NEWSAPI_KEY",        "NewsAPI.org — additional news headlines source."],
  ]),
  spacer(),
  h3("Notification Keys"),
  twoColTable([
    ["TELEGRAM_BOT_TOKEN", "Telegram bot token from @BotFather."],
    ["TELEGRAM_CHAT_ID",   "Your Telegram chat ID (get from @userinfobot)."],
  ]),
  spacer(),

  h2("13.2 Credential Management Commands"),
  twoColTable([
    ["credentials",        "Interactive credential manager menu."],
    ["credentials list",   "Show all saved credential keys with masked values (***)."],
    ["credentials clear",  "Wipe all credentials and session tokens from keychain. Requires full re-login."],
  ]),
  spacer(),
  noteBox("Tip: Run 'credentials list' after first setup to verify all required keys are saved before live trading.", C.tealBg, C.teal),
  pageBreak(),
];

// ── 14. Key Testing Scenarios ─────────────────────────────────────────────────
const testingSection = [
  h1("14. End-to-End Testing Scenarios"),
  bodyP("The following scenarios represent complete user journeys that should be validated during Codex review. Each scenario is self-contained and tests a specific feature area."),
  spacer(),

  h2("14.1 Scenario A — Morning Routine"),
  threeColTable([
    ["Step 1",  "trade --no-broker",                  "Launch without credentials. Should show demo mode notice."],
    ["Step 2",  "morning-brief --raw",                "Run raw morning brief. Should show NIFTY, BANKNIFTY, VIX, top 5 news, FII/DII, breadth, events."],
    ["Step 3",  "morning-brief",                      "Run AI morning brief. Should produce narrative with posture (BULLISH/BEARISH/NEUTRAL/VOLATILE), VIX commentary, agenda."],
    ["Step 4",  "quote NIFTY",                        "Fetch NIFTY index quote. Should show LTP, change, OHLC, volume."],
    ["Step 5",  "flows",                              "Show FII/DII flow intelligence. Should show 5-day trend, streak, divergence signal."],
    ["Step 6",  "active",                             "Show most active stocks. Should list top 10 with LTP, volume, change."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  spacer(),

  h2("14.2 Scenario B — Full Stock Analysis"),
  threeColTable([
    ["Step 1",  "analyze RELIANCE",                   "Full multi-agent analysis. Should take ~2 min. Show verdict, confidence, entry/SL/target."],
    ["Step 2",  "fundamentals RELIANCE",              "Structured fundamentals score. Should show per-metric pass/fail table, STRONG/NEUTRAL/WEAK signal."],
    ["Step 3",  "dcf RELIANCE",                       "DCF valuation. Should show intrinsic value, margin of safety %, sensitivity table."],
    ["Step 4",  "ensemble RELIANCE",                  "Signal ensemble. Should show 5-strategy breakdown with weights and aggregate signal."],
    ["Step 5",  "debate RELIANCE",                    "5-persona debate. Should show all 5 verdicts + consensus."],
    ["Step 6",  "memory",                             "Check memory. RELIANCE analysis should now appear in recent records."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  spacer(),

  h2("14.3 Scenario C — Options Strategy"),
  threeColTable([
    ["Step 1",  "oi NIFTY",                           "OI profile. Should show call/put OI by strike, max pain, PCR."],
    ["Step 2",  "gex NIFTY",                          "GEX analysis. Should show dealer gamma, flip point, regime (POSITIVE/NEGATIVE)."],
    ["Step 3",  "strategy library volatility",         "Browse volatility strategies. Should show iron_condor, straddle, strangle templates."],
    ["Step 4",  "strategy learn iron_condor",          "Full explanation. Should show legs, P&L, breakevens, when-to-use, risks."],
    ["Step 5",  "strategy use iron_condor NIFTY",      "Apply to live NIFTY. Should show 4 legs with LTPs, capital, max profit/loss, breakevens."],
    ["Step 6",  "trade NIFTY",                        "Guided trade. Select NEUTRAL view; should recommend iron condor or strangle. Complete full 9-step flow in paper mode."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  spacer(),

  h2("14.4 Scenario D — Custom Strategy"),
  threeColTable([
    ["Step 1",  "strategy new",                       "Start builder. Describe 'buy when RSI oversold, sell when RSI overbought'. Should ask type, symbol."],
    ["Step 2",  "(Interview)",                        "Complete multi-turn interview. AI generates Python strategy code."],
    ["Step 3",  "(Validation)",                       "Code auto-validates. Backtest runs on 1-year NIFTY data."],
    ["Step 4",  "(Save)",                             "Save strategy as 'rsi_nifty'. Confirm saved."],
    ["Step 5",  "strategy list",                      "Should show rsi_nifty with CAGR, Sharpe from backtest."],
    ["Step 6",  "strategy backtest rsi_nifty --period 2y", "Re-backtest on 2 years. Should show results."],
    ["Step 7",  "strategy run rsi_nifty --paper",     "Generate signal. If BUY: confirm paper trade is placed. Check paper holdings."],
    ["Step 8",  "strategy export rsi_nifty --pine",   "Export to Pine Script. Should show valid Pine Script v5 code."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  spacer(),

  h2("14.5 Scenario E — Risk & Alerts"),
  threeColTable([
    ["Step 1",  "risk-status",                        "Show daily P&L vs cap, trade count, open positions. All metrics should be present."],
    ["Step 2",  "portfolio",                          "Show unified portfolio with Greeks, risk meter. Should work even in demo mode (uses mock holdings)."],
    ["Step 3",  "alert RELIANCE ABOVE 2800",          "Create price alert. Should confirm: Alert #1 created."],
    ["Step 4",  "alert INFY RSI BELOW 30",            "Create technical alert. Should confirm: Alert #2 created."],
    ["Step 5",  "alerts",                             "List active alerts. Both alerts should appear."],
    ["Step 6",  "alerts remove 1",                   "Remove alert #1. Confirm removed. 'alerts' should show only alert #2."],
    ["Step 7",  "greeks",                             "Portfolio Greeks. Should show Delta, Gamma, Theta, Vega (zeros/mock in demo mode)."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  spacer(),

  h2("14.6 Scenario F — Dual-Broker Mode"),
  threeColTable([
    ["Step 1",  "login zerodha",                      "Login to Zerodha via OAuth redirect. Confirm authenticated."],
    ["Step 2",  "connect fyers",                      "Add Fyers as secondary broker. Both should now appear in 'brokers'."],
    ["Step 3",  "brokers",                            "Should show: Zerodha (EXECUTION), Fyers (DATA) with roles auto-assigned."],
    ["Step 4",  "quote NIFTY",                        "Quote should route to Fyers (data broker). Confirm price loads."],
    ["Step 5",  "trade NIFTY --paper",                "Paper trade should route order to Zerodha (execution broker). Confirm order in paper positions."],
    ["Step 6",  "disconnect fyers",                   "Disconnect Fyers. 'brokers' should show only Zerodha. Zerodha role auto-changes to BOTH."],
  ], ["Step", "Command", "Expected Result"], [800, 3000, 5560]),
  pageBreak(),
];

// ── 15. Agent Tool Reference ──────────────────────────────────────────────────
const toolsSection = [
  h1("15. Agent Tool Reference"),
  bodyP("The AI agent has access to 60+ tools organized by category. These are called internally when you run 'analyze', 'morning-brief', 'ai <message>', etc. They can also be called directly from the 'ai' command in natural language."),
  spacer(),

  h2("15.1 Broker / Account Tools"),
  twoColTable([
    ["get_funds",          "Available cash, used margin, total balance."],
    ["get_holdings",       "Delivery holdings: symbol, qty, avg price, LTP, P&L."],
    ["get_positions",      "Open positions: symbol, product, qty, avg price, LTP, unrealized P&L."],
    ["get_orders",         "Today's orders with status (COMPLETE/OPEN/CANCELLED/REJECTED)."],
  ]),
  spacer(),

  h2("15.2 Market Data Tools"),
  twoColTable([
    ["get_quote",               "Live quotes for 1–500 instruments in NSE:SYMBOL format."],
    ["get_market_snapshot",     "NIFTY, BANKNIFTY, VIX, SENSEX, GIFT NIFTY + market posture (BULLISH/BEARISH/NEUTRAL/VOLATILE)."],
    ["get_gift_nifty",          "GIFT NIFTY pre-market futures: LTP, change, implied gap vs NIFTY spot."],
    ["get_vix",                 "India VIX level. >20 = danger; 15–20 = elevated; 12–15 = normal; <12 = complacent."],
    ["get_sector_snapshot",     "Sector index snapshots: IT, Pharma, Auto, FMCG, Realty, Metal, Energy."],
    ["get_most_active_stocks",  "Top 10 NSE stocks by volume or value. by='volume' (default) or by='value'."],
  ]),
  spacer(),

  h2("15.3 Options Tools"),
  twoColTable([
    ["get_options_chain",    "Full chain: all strikes, CE/PE price/OI/OI_change/volume/IV for specified expiry."],
    ["get_pcr",              "Put-Call Ratio by OI. >1.2 = bearish; <0.8 = bullish."],
    ["get_max_pain",         "Max pain strike: where aggregate option-buyer losses are maximized."],
    ["get_iv_rank",          "IV Rank 0–100 from 52-week realized volatility. >50 = elevated; <30 = low."],
    ["get_oi_profile",       "OI per strike: call (resistance) and put (support) OI, PCR per strike."],
    ["get_gex_analysis",     "Gamma Exposure: dealer positioning, flip point, market regime."],
    ["scan_options",         "Scanner: high IV rank stocks, unusual OI buildup, heavy put writing activity."],
    ["payoff_calculate",     "Multi-leg payoff table: max profit, max loss, breakevens, full P&L curve."],
  ]),
  spacer(),

  h2("15.4 Analysis Tools"),
  twoColTable([
    ["technical_analyse",      "RSI, MACD, EMA20/50, SMA200, Bollinger, ATR, support/resistance. Score -100 to +100."],
    ["fundamental_analyse",    "PE, PB, ROE, ROCE, margins, growth, D/E, FCF, shareholding. Score 0–100."],
    ["score_fundamentals",     "India-adjusted fundamentals scorer. Per-metric STRONG/NEUTRAL/WEAK breakdown."],
    ["signal_ensemble",        "5-strategy weighted ensemble. Returns per-strategy breakdown + aggregate signal."],
    ["compute_greeks",         "Black-Scholes: delta, gamma, theta, vega, implied volatility."],
    ["get_shareholding_pattern","Quarterly NSE shareholding: promoter %, FII %, DII %, pledge status."],
    ["get_portfolio_greeks",   "Net portfolio Delta, Gamma, Theta, Vega by underlying."],
    ["suggest_delta_hedge",    "Suggest instruments and quantities to reach target delta."],
  ]),
  spacer(),

  h2("15.5 News & Sentiment Tools"),
  twoColTable([
    ["web_search",             "Web search: providers Exa (neural) → Tavily → Perplexity → DuckDuckGo (auto-select by available keys). Returns title, URL, snippet, date."],
    ["get_market_news",        "Top N headlines from ET, MoneyControl, Business Standard RSS feeds."],
    ["get_stock_news",         "Recent news for specific stock (by symbol keyword search)."],
    ["get_upcoming_events",    "F&O expiry dates, earnings calendar, RBI MPC meetings (next N days)."],
    ["get_earnings_calendar",  "Quarterly earnings dates + historical average move % for NIFTY 50."],
    ["get_pre_earnings_iv",    "IV rank before earnings: high IV = sell premium; low IV = buy options."],
    ["get_fii_dii_data",       "FII and DII net buy/sell (INR crore) for last N trading days."],
    ["get_market_breadth",     "A/D ratio for NIFTY 500: >2 = broad rally; <0.5 = broad decline."],
    ["get_sentiment",          "Aggregated sentiment: FII (30%) + news (25%) + bulk deals (25%) + breadth (20%)."],
    ["get_flow_intelligence",  "FII/DII streaks, divergence, 5-day totals, trading signal."],
    ["get_bulk_block_deals",   "Recent NSE bulk and block deals by institution or promoter."],
    ["get_event_strategies",   "Event-driven strategy suggestions for upcoming events (expiry, RBI, earnings)."],
  ]),
  spacer(),

  h2("15.6 Backtest & Simulation Tools"),
  twoColTable([
    ["run_backtest",             "Run built-in strategy (rsi/ma/macd/bb) backtest. Returns CAGR, Sharpe, drawdown, win rate."],
    ["backtest_user_strategy",   "Run saved custom strategy backtest."],
    ["backtest_options",         "Options strategy backtest (straddle, iron_condor, covered_call, protective_put)."],
    ["list_user_strategies",     "List all saved custom strategies with metadata."],
    ["find_similar_strategies",  "Find existing strategies similar to a plain-English description."],
    ["whatif_market_move",       "Simulate portfolio P&L if NIFTY moves by X%."],
    ["whatif_stock_move",        "Simulate portfolio P&L if specific stock moves by X%."],
  ]),
  spacer(),

  h2("15.7 Alert Tools"),
  twoColTable([
    ["set_price_alert",         "Create price alert: symbol, ABOVE|BELOW condition, threshold."],
    ["set_technical_alert",     "Create technical alert: symbol, indicator (RSI/MACD/ADX/ATR), ABOVE|BELOW, threshold."],
    ["set_conditional_alert",   "Create multi-condition AND alert: list of {condition_type, condition, threshold, indicator} dicts."],
    ["list_alerts",             "List all active alerts."],
    ["remove_alert",            "Remove alert by ID."],
  ]),
  pageBreak(),
];

// ── 16. Error Handling & Fallbacks ─────────────────────────────────────────────
const fallbackSection = [
  h1("16. Error Handling & Data Fallbacks"),
  bodyP("The platform is designed to degrade gracefully. Every data fetch has a fallback chain so analysis can proceed even when primary sources are unavailable."),
  spacer(),

  h2("16.1 Market Data Fallback Chain"),
  twoColTable([
    ["Live quotes",          "1. Broker WebSocket (real-time tick)  →  2. Broker REST quote API  →  3. NSE scraper (public website)  →  4. yfinance (free, ~15 min delay)"],
    ["Options chain",        "1. Broker REST (authenticated)  →  2. NSE scraper  →  3. yfinance options"],
    ["Sector indices",       "1. NSE REST API  →  2. yfinance (^CNXIT, ^CNXPHARMA, etc.)"],
    ["News",                 "1. NewsAPI  →  2. RSS feeds (ET, MC, BS)  →  3. Web search"],
    ["Shareholding",         "1. NSE quarterly filing  →  2. yfinance institutional holders"],
    ["Earnings calendar",    "1. NSE website scraper  →  2. yfinance calendar"],
    ["GIFT NIFTY",           "1. NSE International website  →  2. yfinance (SGX proxy)  →  None (silently skipped)"],
  ]),
  spacer(),

  h2("16.2 Startup & Login Fallbacks"),
  bullet("If broker login fails → drop into REPL with MockBroker. Show 'credentials list' and 'login' hints."),
  bullet("If AI provider not configured → run ensure_ai_provider_configured() onboarding flow."),
  bullet("If no API keys at all → 'morning-brief --raw' still works (no AI call needed)."),
  bullet("If market closed → quotes return last known price with CLOSED flag."),
  spacer(),

  h2("16.3 Feature Pipeline Fallback"),
  bullet("get_features() never raises — returns zero-filled FeatureSet on any error."),
  bullet("Analysts receiving zero features: fall back to NEUTRAL verdict with 0 confidence."),
  bullet("ML analyst: returns NEUTRAL if scikit-learn not installed or fewer than 100 rows of data."),
  pageBreak(),
];

// ── 17. Configuration Reference ────────────────────────────────────────────────
const configSection = [
  h1("17. Configuration Reference"),

  h2("17.1 Environment Variables"),
  twoColTable([
    ["TOTAL_CAPITAL",        "Total trading capital in INR. Used for position sizing and risk limits. Default: 200000."],
    ["DAILY_LOSS_CAP_PCT",   "Max daily loss as % of capital before risk gate blocks all trades. Default: 2.0."],
    ["MAX_TRADES_PER_DAY",   "Maximum number of trades per day. Default: 10."],
    ["MAX_POSITION_PCT",     "Max single position as % of capital. Default: 10.0."],
    ["TARGET_RISK_PCT",      "Target risk per trade as % of capital (for ATR-based sizing). Default: 1.0."],
    ["PAPER_CAPITAL",        "Initial paper trading capital. Default: same as TOTAL_CAPITAL."],
    ["DEFAULT_EXCHANGE",     "Default exchange for unqualified symbols. Default: NSE."],
    ["ALERT_POLL_INTERVAL",  "Alert polling interval in seconds (fallback when no WebSocket). Default: 60."],
    ["PORT",                 "FastAPI web server port. Default: 8765."],
  ]),
  spacer(),

  h2("17.2 Data Files"),
  twoColTable([
    ["~/.trading_platform/paper_portfolio.json",     "Paper trading portfolio state (holdings, positions, orders, cash)."],
    ["~/.trading_platform/trade_memory.db",          "SQLite database of all past trade analyses, outcomes, lessons."],
    ["~/.trading_platform/strategies/",             "Directory of saved custom strategy Python files + metadata JSON."],
    ["~/.trading_platform/strategy_conditions.json", "Active strategy condition alerts (persisted across restarts)."],
    ["~/.trading_platform/.repl_history",            "REPL command history (used by prompt_toolkit for ↑ arrow recall)."],
    ["~/.trading_platform/alerts.json",              "Active price and technical alerts (persisted across restarts)."],
    [".env (project root)",                         "Development .env file. Loaded at startup. Overrides keychain values."],
  ]),
  pageBreak(),
];

// ── Appendix ─────────────────────────────────────────────────────────────────
const appendixSection = [
  h1("Appendix: Quick Command Cheatsheet"),
  spacer(),
  threeColTable([
    // Broker
    ["login",               "Broker",     "Interactive broker login"],
    ["connect fyers",       "Broker",     "Add secondary broker"],
    ["brokers",             "Broker",     "List all connected brokers + roles"],
    ["funds",               "Account",    "Available cash and margin"],
    ["holdings",            "Account",    "Delivery holdings"],
    ["positions",           "Account",    "Open positions"],
    ["orders",              "Account",    "Today's orders"],
    ["portfolio",           "Account",    "Combined portfolio + Greeks"],
    // Market
    ["quote INFY",          "Market",     "Live price + OHLC"],
    ["morning-brief",       "Market",     "AI daily briefing"],
    ["active",              "Market",     "Most active stocks"],
    ["flows",               "Market",     "FII/DII flow intel"],
    ["earnings",            "Market",     "Earnings calendar"],
    ["events",              "Market",     "Expiry + RBI + budget dates"],
    ["bulk-deals",          "Market",     "NSE bulk/block deals"],
    // Analysis
    ["analyze INFY",        "Analysis",   "Full multi-agent analysis"],
    ["quick INFY",          "Analysis",   "5-second quick scan"],
    ["sentiment INFY",      "Analysis",   "Sentiment aggregator"],
    ["fundamentals INFY",   "Analysis",   "Fundamentals scorer"],
    ["dcf INFY",            "Analysis",   "DCF intrinsic value"],
    ["ensemble INFY",       "Analysis",   "Signal ensemble (5 strategies)"],
    ["debate INFY",         "Analysis",   "5-persona investor debate"],
    ["persona buffett INFY","Analysis",   "Single persona analysis"],
    ["gex NIFTY",           "Options",    "Gamma Exposure analysis"],
    ["oi NIFTY",            "Options",    "Open Interest profile"],
    ["scan",                "Options",    "Options scanner"],
    ["patterns INFY",       "Technical",  "Chart pattern scanner"],
    ["mtf INFY",            "Technical",  "Multi-timeframe analysis"],
    ["pairs INFY TCS",      "Technical",  "Pairs trading analysis"],
    // Strategy
    ["strategy library",    "Strategy",   "Browse 26 templates"],
    ["strategy learn <id>", "Strategy",   "Full template explanation"],
    ["strategy use <id> SYM","Strategy",  "Apply template to live data"],
    ["strategy new",        "Strategy",   "Build custom strategy"],
    ["strategy list",       "Strategy",   "List saved strategies"],
    ["strategy backtest <n>","Strategy",  "Re-backtest strategy"],
    ["strategy run <n>",    "Strategy",   "Generate today's signal"],
    ["strategy export --pine","Strategy", "Export to Pine Script"],
    // Trade & Risk
    ["trade",               "Trade",      "Guided trade builder"],
    ["whatif 5",            "Risk",       "Portfolio impact if NIFTY ±5%"],
    ["risk-status",         "Risk",       "Daily risk limits status"],
    ["greeks",              "Risk",       "Portfolio Greeks"],
    ["delta-hedge",         "Risk",       "Delta neutralization suggestions"],
    // Alerts & Memory
    ["alert INFY ABOVE 200","Alerts",     "Create price alert"],
    ["alerts",              "Alerts",     "List active alerts"],
    ["memory",              "Memory",     "Recent trade analyses"],
    ["memory stats",        "Memory",     "Win rate + P&L stats"],
    // System
    ["paper on/off",        "System",     "Toggle paper trading"],
    ["ai <message>",        "System",     "Chat with AI directly"],
    ["provider",            "System",     "Show/switch AI provider"],
    ["credentials",         "System",     "Manage API keys"],
    ["tui",                 "System",     "Launch TUI dashboard"],
    ["web",                 "System",     "Start FastAPI web server"],
    ["help",                "System",     "Show command reference"],
  ], ["Command", "Category", "Description"], [2800, 1600, 4960]),
];

// ══════════════════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ══════════════════════════════════════════════════════════════════════════════

const allChildren = [
  ...coverPage,
  // TOC page
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  spacer(),
  spacer(),
  pageBreak(),
  // Sections
  ...introSection,
  ...replSection,
  ...strategySection,
  ...agentSection,
  ...tradeSection,
  ...backtestSection,
  ...sizingSection,
  ...paperSection,
  ...alertsSection,
  ...brokerSection,
  ...webSection,
  ...featurePipelineSection,
  ...credentialsSection,
  ...testingSection,
  ...toolsSection,
  ...fallbackSection,
  ...configSection,
  ...appendixSection,
];

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }, {
          level: 1, format: LevelFormat.BULLET, text: "◦",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } },
        }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 20 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: C.navy },
        paragraph: { spacing: { before: 480, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: C.teal },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: C.navy },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: C.teal },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 3 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            run("Vibe Trading  |  India Trade CLI — Feature Reference", { size: 16, color: C.gray }),
            new TextRun({ text: "\t", font: "Arial" }),
            run("Confidential — For Review", { size: 16, color: C.gray }),
          ],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.teal, space: 4 } },
          tabStops: [{ type: "right", position: 9360 }],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            run("Page ", { size: 16, color: C.gray }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: C.gray }),
            run("  of  ", { size: 16, color: C.gray }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 16, color: C.gray }),
          ],
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.teal, space: 4 } },
        })],
      }),
    },
    children: allChildren,
  }],
});

const OUTPUT = "/Users/arkidmitra/Desktop/TheFICompany/india-trade-cli/docs/india-trade-cli-feature-reference.docx";
Packer.toBuffer(doc).then((buffer) => {
  fs.mkdirSync("/Users/arkidmitra/Desktop/TheFICompany/india-trade-cli/docs", { recursive: true });
  fs.writeFileSync(OUTPUT, buffer);
  console.log("✅  Written:", OUTPUT);
});
