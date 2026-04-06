"""
engine/technical_library.py
────────────────────────────
Curated library of 32 technical and systematic trading strategies for Indian markets.

Companion to engine/strategy_library.py (options strategies). Same architecture:
each strategy is a TechnicalTemplate — educational metadata + parameter definitions
+ a backtest_key that maps to an entry in engine/backtest.STRATEGIES.

Templates without a backtest_key require intraday data, specialised data feeds,
or multi-asset infrastructure not yet available — they are documented for learning
only and will gain backtest support in future iterations.

Usage:
    from engine.technical_library import tech_library

    template = tech_library.get("supertrend")
    print(template.layman_explanation)
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Constants ─────────────────────────────────────────────────

TECH_CATEGORIES = (
    "momentum",
    "mean_reversion",
    "scalping",
    "breakout",
    "pairs",
    "macro",
    "quantitative",
)


# ── Dataclass ─────────────────────────────────────────────────


@dataclass
class TechnicalTemplate:
    """Metadata and educational content for a named technical strategy."""

    id: str
    name: str
    category: str  # one of TECH_CATEGORIES
    layman_explanation: str  # plain English, zero jargon
    explanation: str  # technical description
    when_to_use: str
    when_not_to_use: str
    signal_rules: list[dict]  # [{"signal": "BUY"|"SELL"|"HOLD", "condition": str, "example": str}]
    parameters: dict  # {param_name: {"default": val, "description": str, "type": str}}
    timeframes: list[str]  # e.g. ["5m", "15m", "1D"]
    instruments: list[str]  # e.g. ["stocks", "indices", "futures"]
    risks: list[str]
    tags: list[str]
    complexity: str = "beginner"  # "beginner" | "intermediate" | "advanced"
    backtest_key: str | None = (
        None  # key in engine/backtest.STRATEGIES; None = not yet backtestable
    )


# ── Template definitions ──────────────────────────────────────

TECH_TEMPLATES: dict[str, TechnicalTemplate] = {
    # ── MOMENTUM (8) ──────────────────────────────────────────
    "ema_crossover": TechnicalTemplate(
        id="ema_crossover",
        name="EMA Crossover",
        category="momentum",
        layman_explanation=(
            "Think of two runners on a track — one fast (9-day average), one slow (21-day average). "
            "When the fast runner overtakes the slow runner, the market has picked up speed: buy. "
            "When the fast runner falls behind, the market is slowing down: sell. "
            "Example: RELIANCE at ₹1,200 — its 9-day average rises to ₹1,215 and crosses above "
            "its 21-day average at ₹1,208. That crossing tells you: recent buyers are outrunning "
            "longer-term sellers. The trend is turning up."
        ),
        explanation=(
            "Uses two exponential moving averages (default 9/21 for intraday, 20/50 for swing). "
            "A bullish signal fires when the fast EMA crosses above the slow EMA; bearish on the reverse. "
            "Adding an ADX > 20 filter avoids false signals in choppy markets."
        ),
        when_to_use="Trending markets with clear directional momentum; works on any timeframe.",
        when_not_to_use="Sideways/range-bound markets — generates repeated false crossovers.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Fast EMA crosses above Slow EMA",
                "example": "e.g. RELIANCE: 9 EMA rises to ₹1,255, crosses above 21 EMA at ₹1,248 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Fast EMA crosses below Slow EMA",
                "example": "e.g. RELIANCE: 9 EMA falls to ₹1,230, crosses below 21 EMA at ₹1,238 → SELL",
            },
            {
                "signal": "HOLD",
                "condition": "EMAs are not crossing — trend is intact",
                "example": "9 EMA is clearly above 21 EMA and both are rising → hold long",
            },
        ],
        parameters={
            "fast": {"default": 20, "description": "Fast EMA period", "type": "int"},
            "slow": {"default": 50, "description": "Slow EMA period", "type": "int"},
        },
        timeframes=["5m", "15m", "1h", "1D"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "Whipsaws in sideways markets — fast/slow periods cross repeatedly with no follow-through",
            "Lagging indicator — entry is always after the move has started",
            "Works poorly during news-driven gaps",
        ],
        tags=["momentum", "trend", "ema", "crossover", "beginner"],
        complexity="beginner",
        backtest_key="ema",
    ),
    "macd_system": TechnicalTemplate(
        id="macd_system",
        name="MACD System",
        category="momentum",
        layman_explanation=(
            "Think of a car's accelerator — MACD doesn't tell you how fast the car is going, "
            "it tells you whether you're pressing harder or easing off. "
            "When you start pressing harder (the bar turns green and grows), buy. "
            "When you lift your foot (bar shrinks or flips red), sell. "
            "Example: NIFTY's MACD histogram was -18 for five days (sellers accelerating). "
            "It flips to +4 today — buyers just took over the pedal. "
            "The absolute value is small, but the direction change is what matters."
        ),
        explanation=(
            "MACD(12,26,9): MACD line = 12 EMA - 26 EMA; signal line = 9 EMA of MACD. "
            "Three entry triggers: (1) histogram flip — earliest; (2) signal line crossover; "
            "(3) zero-line cross — highest conviction. Best aligned with 200 EMA direction."
        ),
        when_to_use="Swing and positional trades where you want to catch momentum shifts.",
        when_not_to_use="Scalping or very short timeframes — too much lag for quick trades.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "MACD histogram turns positive (crosses above zero)",
                "example": "e.g. NIFTY: histogram was -15, now +3 → bulls taking control → BUY",
            },
            {
                "signal": "SELL",
                "condition": "MACD histogram turns negative (crosses below zero)",
                "example": "e.g. NIFTY: histogram was +12, now -5 → momentum flipping → SELL",
            },
            {
                "signal": "HOLD",
                "condition": "Histogram is positive and growing — trend intact",
                "example": "Histogram at +20 and expanding → stay long",
            },
        ],
        parameters={
            "fast": {"default": 12, "description": "Fast EMA period", "type": "int"},
            "slow": {"default": 26, "description": "Slow EMA period", "type": "int"},
            "signal": {"default": 9, "description": "Signal line period", "type": "int"},
        },
        timeframes=["15m", "1h", "1D", "1W"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "Divergence signals can be premature — price may continue before reversing",
            "Lags the market — you will never catch the exact top or bottom",
            "Many false signals during low-volatility chop",
        ],
        tags=["momentum", "macd", "histogram", "swing", "beginner"],
        complexity="beginner",
        backtest_key="macd",
    ),
    "supertrend": TechnicalTemplate(
        id="supertrend",
        name="Supertrend",
        category="momentum",
        layman_explanation=(
            "Imagine a safety net beneath a tightrope walker. "
            "As long as the walker stays above the net, keep watching them climb. "
            "The moment they fall through — exit immediately. "
            "The net also rises as the walker climbs, locking in gains. "
            "Example: NIFTY climbs from ₹22,000 to ₹24,500. The Supertrend net sits at ₹23,800. "
            "One bad day drops NIFTY to ₹23,750 — below the net. Exit. "
            "You captured most of the ₹2,500 move and got out before the reversal deepened."
        ),
        explanation=(
            "ATR-based trailing stop: upper band = (High+Low)/2 + multiplier×ATR; "
            "lower band = (High+Low)/2 - multiplier×ATR. "
            "Default: ATR period 10, multiplier 3.0. "
            "When close crosses the band, the trend flips and the SAR level switches sides."
        ),
        when_to_use="Strongly trending markets — works well on NIFTY futures and liquid large-caps.",
        when_not_to_use="Range-bound or low-ATR markets — produces frequent, costly whipsaws.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price closes above the Supertrend line (trend flips bullish)",
                "example": "e.g. NIFTY at ₹24,100 closes above Supertrend at ₹24,050 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Price closes below the Supertrend line (trend flips bearish)",
                "example": "e.g. NIFTY at ₹23,900 closes below Supertrend at ₹23,950 → SELL",
            },
        ],
        parameters={
            "period": {"default": 10, "description": "ATR lookback period", "type": "int"},
            "multiplier": {
                "default": 3.0,
                "description": "ATR multiplier for band width",
                "type": "float",
            },
        },
        timeframes=["5m", "15m", "1h", "1D"],
        instruments=["indices", "stocks", "futures"],
        risks=[
            "Whipsaws in choppy markets can generate 5-6 consecutive small losses",
            "ATR widens after volatile sessions — stop moves far from price",
            "Does not work well near major support/resistance zones",
        ],
        tags=["momentum", "trend", "atr", "trailing_stop", "popular", "beginner"],
        complexity="beginner",
        backtest_key="supertrend",
    ),
    "heikin_ashi": TechnicalTemplate(
        id="heikin_ashi",
        name="Heikin Ashi Trend",
        category="momentum",
        layman_explanation=(
            "Normal price charts are like trying to hear someone in a noisy crowd — chaotic. "
            "Heikin Ashi is like noise-cancelling headphones: it smooths out the price chaos "
            "so you can see the real trend clearly. "
            "A perfectly clean green bar with no downward tail means buyers were completely in charge — "
            "sellers couldn't push price down even for a moment during that entire candle. "
            "Example: INFY shows five consecutive clean green Heikin Ashi bars, each closing higher, "
            "all above its 21-day average. No ambiguity — that's a strong uptrend. Hold long."
        ),
        explanation=(
            "HA Close = (O+H+L+C)/4; HA Open = (prev HA Open + prev HA Close)/2. "
            "Full bullish signal: no lower wick (HA Low = HA Open) + green candle + price above EMA. "
            "Full bearish: no upper wick (HA High = HA Open) + red candle + price below EMA."
        ),
        when_to_use="Strong trending moves; useful for holding positions without getting shaken out by noise.",
        when_not_to_use="At major turning points — HA candles are lagging and can miss reversals.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Full green HA candle (no lower wick) above the EMA",
                "example": "e.g. INFY: HA candle is fully green, no lower wick, price above 21 EMA → strong BUY",
            },
            {
                "signal": "SELL",
                "condition": "Full red HA candle (no upper wick) below the EMA",
                "example": "e.g. INFY: HA candle is fully red, no upper wick, price below 21 EMA → SELL",
            },
        ],
        parameters={
            "ema_period": {
                "default": 21,
                "description": "EMA period for trend filter",
                "type": "int",
            },
        },
        timeframes=["15m", "1h", "1D"],
        instruments=["stocks", "indices"],
        risks=[
            "HA prices are not real prices — stop-loss levels need converting back to actual OHLC",
            "Candles lag real price action — exits can be late in fast reversals",
        ],
        tags=["momentum", "trend", "heikin_ashi", "candles", "intermediate"],
        complexity="intermediate",
        backtest_key="heikin_ashi",
    ),
    "adx_trend": TechnicalTemplate(
        id="adx_trend",
        name="ADX Trend Strength Filter",
        category="momentum",
        layman_explanation=(
            "Before deciding how to trade, you need to know: is the market actually going somewhere, "
            "or just wobbling in place? ADX is a thermometer for the market's energy — not direction, just strength. "
            "Example: NIFTY ADX reads 34 — that's a strong trend. It doesn't matter which way; "
            "use a trend strategy and ride it. ADX reads 13 — the market is meandering aimlessly. "
            "Don't try to catch a trend that isn't there. Switch to a range-trading strategy instead."
        ),
        explanation=(
            "ADX > 25 = strong trend → use EMA crossover, MACD, Supertrend. "
            "ADX < 20 = range-bound → use Bollinger, RSI reversion, Keltner. "
            "Standalone variant: +DI/-DI crossover with ADX confirmation above 20 as a directional signal."
        ),
        when_to_use="As a regime filter layered on top of any other strategy to avoid whipsaws.",
        when_not_to_use="As the sole entry signal — ADX alone gives no direction.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "+DI crosses above -DI with ADX > 20",
                "example": "e.g. NIFTY: +DI at 28, -DI at 18, ADX at 26 → trending bullishly → BUY",
            },
            {
                "signal": "SELL",
                "condition": "-DI crosses above +DI with ADX > 20",
                "example": "e.g. NIFTY: -DI at 30, +DI at 15, ADX at 28 → trending bearishly → SELL",
            },
            {
                "signal": "HOLD",
                "condition": "ADX < 20 — market is ranging, avoid directional trades",
                "example": "ADX at 14 → no trend signal; switch to mean-reversion strategy",
            },
        ],
        parameters={
            "period": {"default": 14, "description": "ADX lookback period", "type": "int"},
            "trend_threshold": {
                "default": 25,
                "description": "ADX level above which market is trending",
                "type": "int",
            },
        },
        timeframes=["1h", "1D"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "ADX can remain above 25 during a counter-trend correction — direction still matters",
            "Slow to respond to sudden trend changes",
        ],
        tags=["momentum", "adx", "regime_filter", "trend_strength", "intermediate"],
        complexity="intermediate",
        backtest_key=None,  # regime filter — combine with another strategy
    ),
    "donchian_breakout": TechnicalTemplate(
        id="donchian_breakout",
        name="Donchian Channel Breakout",
        category="momentum",
        layman_explanation=(
            "If a stock has been stuck under a ceiling for 20 days and then bursts through it, "
            "that's not random — new buyers arrived who are willing to pay more than anyone in the past month. "
            "That conviction usually keeps going. "
            "Example: TCS has been ranging ₹3,600–₹3,800 for three weeks. "
            "Today it closes at ₹3,825 — a new 20-day high. Buy. "
            "The Turtle Traders of the 1980s turned $1.6 million into $175 million doing exactly this."
        ),
        explanation=(
            "Buy when price closes above the 20-day highest high; sell when below 20-day lowest low. "
            "Filter: only trade in the direction of the 50-day Donchian midpoint to avoid counter-trend trades. "
            "Works best on liquid large-caps and index futures."
        ),
        when_to_use="Strong trending markets; after a long consolidation period near a resistance level.",
        when_not_to_use="Already-extended trends; choppy markets where breakouts frequently fail.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Close > 20-day highest high AND price > 50-day channel midpoint",
                "example": "e.g. TCS: 20-day high is ₹3,800, today closes at ₹3,820 → BUY breakout",
            },
            {
                "signal": "SELL",
                "condition": "Close < 20-day lowest low AND price < 50-day channel midpoint",
                "example": "e.g. TCS: 20-day low is ₹3,600, today closes at ₹3,580 → SELL breakdown",
            },
        ],
        parameters={
            "period": {
                "default": 20,
                "description": "Breakout lookback period (days)",
                "type": "int",
            },
            "filter_period": {
                "default": 50,
                "description": "Trend filter channel period",
                "type": "int",
            },
        },
        timeframes=["1D", "1W"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "High false breakout rate in Indian markets — price often reverses after touching new highs",
            "Requires wide stop loss (beyond the channel) — large capital at risk per trade",
            "Not suitable for intraday — needs daily closing prices",
        ],
        tags=["momentum", "breakout", "donchian", "turtle", "trend_following", "intermediate"],
        complexity="intermediate",
        backtest_key="donchian",
    ),
    "parabolic_sar": TechnicalTemplate(
        id="parabolic_sar",
        name="Parabolic SAR",
        category="momentum",
        layman_explanation=(
            "Imagine a dog on a leash walking behind you. When you walk forward (uptrend), "
            "the dog follows slightly behind. The moment you turn back, the leash snaps tight. "
            "The SAR dot is that leash — it trails the stock as it rises. "
            "Example: BANKNIFTY climbs from ₹46,000 to ₹48,500 over two weeks. "
            "The dot sits below at ₹47,900. One bad session drops BANKNIFTY to ₹47,850 — "
            "below the dot. Exit immediately, flip short. One rule, zero ambiguity."
        ),
        explanation=(
            "The SAR accelerates toward price as the trend extends (acceleration factor starts at 0.02, "
            "increases by 0.02 each new extreme, max 0.20). When price touches the SAR, "
            "the system flips direction and resets the AF. Generates continuous long/short signals."
        ),
        when_to_use="Strongly trending markets with low volatility noise; good for riding established trends.",
        when_not_to_use="Sideways markets — constant flip-flop causes rapid small losses.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price closes above the SAR (SAR flips below price)",
                "example": "e.g. BANKNIFTY: SAR was at ₹47,200 above price; price closes at ₹47,300 → SAR flips below → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Price closes below the SAR (SAR flips above price)",
                "example": "e.g. BANKNIFTY: SAR was at ₹46,800 below price; price drops to ₹46,750 → SAR flips above → SELL",
            },
        ],
        parameters={
            "step": {
                "default": 0.02,
                "description": "Acceleration factor step size",
                "type": "float",
            },
            "max_step": {
                "default": 0.20,
                "description": "Maximum acceleration factor",
                "type": "float",
            },
        },
        timeframes=["15m", "1h", "1D"],
        instruments=["indices", "stocks", "futures"],
        risks=[
            "Extremely choppy in range-bound markets — many small consecutive losses",
            "Stop moves far from price in high-ATR environments",
            "Fully mechanical — no discretion to skip poor setups",
        ],
        tags=["momentum", "trailing_stop", "sar", "trend_following", "beginner"],
        complexity="beginner",
        backtest_key="psar",
    ),
    "ichimoku": TechnicalTemplate(
        id="ichimoku",
        name="Ichimoku Cloud",
        category="momentum",
        layman_explanation=(
            "The Ichimoku Cloud is like a weather forecast for stocks. "
            "The coloured cloud is the storm zone: price above it means clear skies (uptrend), "
            "inside means fog (uncertain), below means stormy (downtrend). "
            "Example: HDFC Bank at ₹1,820. The cloud spans ₹1,700–₹1,760 — "
            "price is well above the storm zone, the fast line (₹1,800) is above the slow line (₹1,775), "
            "and the lagging line confirms. All five components agree: strong buy signal. "
            "Used by Japanese traders for 70+ years before the West discovered it."
        ),
        explanation=(
            "Five components: Tenkan-sen (9-period midpoint), Kijun-sen (26-period midpoint), "
            "Senkou Span A & B (future cloud), Chikou Span (close shifted back 26 periods). "
            "Strongest entry: price above cloud, Tenkan > Kijun, Chikou above price, cloud bullish (A > B)."
        ),
        when_to_use="All three conditions aligned in trending markets; especially on daily/weekly charts.",
        when_not_to_use="Range-bound or thin-volume stocks — cloud becomes messy and unreliable.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price above cloud + Tenkan > Kijun + Chikou above price 26 periods ago",
                "example": "e.g. HDFC: price at ₹1,800, cloud between ₹1,720–₹1,750, Tenkan at ₹1,780 > Kijun ₹1,760 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Price below cloud + Tenkan < Kijun + Chikou below price",
                "example": "e.g. HDFC: price at ₹1,650, cloud at ₹1,700–₹1,720 acting as resistance → SELL",
            },
        ],
        parameters={
            "tenkan": {"default": 9, "description": "Tenkan-sen period", "type": "int"},
            "kijun": {"default": 26, "description": "Kijun-sen period", "type": "int"},
            "senkou_b": {"default": 52, "description": "Senkou Span B period", "type": "int"},
        },
        timeframes=["1h", "1D", "1W"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "Complex — five components to interpret simultaneously",
            "Lagging by design (Senkou spans are plotted ahead and behind)",
            "Less effective on Indian intraday charts due to market microstructure",
        ],
        tags=["momentum", "trend", "ichimoku", "cloud", "advanced"],
        complexity="advanced",
        backtest_key=None,  # multi-component — future implementation
    ),
    # ── MEAN REVERSION (5) ────────────────────────────────────
    "bollinger_reversion": TechnicalTemplate(
        id="bollinger_reversion",
        name="Bollinger Band Reversion",
        category="mean_reversion",
        layman_explanation=(
            "Picture a rubber band stretched around a ball. When pulled too far out — it snaps back. "
            "Bollinger Bands work the same way: a stock's 20-day average is the center, "
            "and the bands mark 'unusually far' above and below it. "
            "Example: RELIANCE 20-day average = ₹3,000. Lower band = ₹2,840. "
            "Price drops to ₹2,830 — it has been stretched far below normal. "
            "Historically, this kind of stretch almost always snaps back to ₹3,000 within a few days. Buy."
        ),
        explanation=(
            "20-period SMA ± 2 standard deviations. "
            "Buy when price touches lower band in an uptrend (SMA sloping up); "
            "sell at upper band in a downtrend. "
            "Squeeze variant: when bands are very narrow (low volatility), "
            "a breakout in either direction is imminent."
        ),
        when_to_use="Range-bound markets with mean-reverting behaviour; after volatility compression.",
        when_not_to_use="Strong trending markets — price can 'walk the band' for extended periods.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Close touches or breaks below lower Bollinger Band",
                "example": "e.g. RELIANCE: lower band at ₹2,800, price closes at ₹2,790 → oversold → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Close touches or breaks above upper Bollinger Band",
                "example": "e.g. RELIANCE: upper band at ₹3,200, price closes at ₹3,210 → overbought → SELL",
            },
        ],
        parameters={
            "period": {"default": 20, "description": "SMA lookback period", "type": "int"},
            "std_dev": {
                "default": 2.0,
                "description": "Standard deviation multiplier",
                "type": "float",
            },
        },
        timeframes=["15m", "1h", "1D"],
        instruments=["stocks", "indices"],
        risks=[
            "In trending markets price walks along the band — losses mount",
            "Standard deviation expands after a big move — bands widen just as you want to fade",
            "No built-in exit rule — need to define a take-profit level",
        ],
        tags=["mean_reversion", "bollinger", "volatility", "bands", "beginner"],
        complexity="beginner",
        backtest_key="bb",
    ),
    "rsi_reversion": TechnicalTemplate(
        id="rsi_reversion",
        name="RSI Oversold / Overbought",
        category="mean_reversion",
        layman_explanation=(
            "RSI measures how exhausted buyers or sellers are, on a scale of 0 to 100. "
            "Below 30: sellers are completely out of breath — time to buy. "
            "Above 70: buyers are gasping — time to sell. "
            "Example: WIPRO has fallen 12% over eight days. RSI hits 24. "
            "That's not a company in crisis — that's exhausted sellers who have nothing left to sell. "
            "The stock almost always bounces from here. Buy the exhaustion, sell the euphoria."
        ),
        explanation=(
            "RSI(14) below 30 = oversold → buy; above 70 = overbought → sell. "
            "Best used when ADX < 20 (ranging market) to avoid buying falling knives in downtrends. "
            "RSI(2) ultra-short variant for intraday scalping extremes (< 10 = buy, > 90 = sell)."
        ),
        when_to_use="Range-bound markets; high-quality stocks in a sideways phase.",
        when_not_to_use="Strong trends — RSI can stay oversold/overbought for weeks in a trending move.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "RSI(14) crosses below 30 (oversold)",
                "example": "e.g. WIPRO: RSI drops to 28 after a 10-day selloff → oversold → BUY",
            },
            {
                "signal": "SELL",
                "condition": "RSI(14) crosses above 70 (overbought)",
                "example": "e.g. WIPRO: RSI rises to 74 after a strong rally → overbought → SELL",
            },
        ],
        parameters={
            "period": {"default": 14, "description": "RSI lookback period", "type": "int"},
            "buy_level": {
                "default": 30,
                "description": "Oversold threshold (buy signal)",
                "type": "int",
            },
            "sell_level": {
                "default": 70,
                "description": "Overbought threshold (sell signal)",
                "type": "int",
            },
        },
        timeframes=["15m", "1h", "1D"],
        instruments=["stocks", "indices"],
        risks=[
            "In a downtrend, RSI can stay below 30 for weeks — buying too early",
            "Works best with an ADX filter to confirm a ranging environment",
            "RSI divergence (leading) is not captured in this simple version",
        ],
        tags=["mean_reversion", "rsi", "oscillator", "beginner"],
        complexity="beginner",
        backtest_key="rsi",
    ),
    "vwap_reversion": TechnicalTemplate(
        id="vwap_reversion",
        name="VWAP Reversion (Intraday)",
        category="mean_reversion",
        layman_explanation=(
            "VWAP is today's 'fair price' — the average where the most actual money changed hands today. "
            "Big institutions use it as their benchmark: their mandate says 'buy at or below today's VWAP'. "
            "So when price drifts well above VWAP, they stop buying — and price drifts back. "
            "Example: NIFTY's VWAP is ₹24,100 at 10 AM. Price shoots to ₹24,320 (0.9% above). "
            "Institutions pause. Price drifts back to ₹24,130 by 11 AM. "
            "Wait for that drift back, then buy the return to fair value."
        ),
        explanation=(
            "Fade price when it is > 2 standard deviations above/below the VWAP band. "
            "Best window: 10:30 AM–2:00 PM IST (avoid first and last 30 min). "
            "Exit target: price returns to VWAP. Stop: beyond the extreme band."
        ),
        when_to_use="High-volume intraday sessions on NIFTY, BANKNIFTY futures; avoid low-volume stocks.",
        when_not_to_use="Strong trend days — price can stay extended from VWAP for hours.",
        signal_rules=[
            {
                "signal": "SELL",
                "condition": "Price > VWAP + 2 standard deviations",
                "example": "e.g. NIFTY futures at ₹24,400, VWAP at ₹24,000, +2σ band at ₹24,350 → fade the move → SELL",
            },
            {
                "signal": "BUY",
                "condition": "Price < VWAP - 2 standard deviations",
                "example": "e.g. NIFTY futures at ₹23,600, VWAP at ₹24,000, -2σ band at ₹23,650 → buy the dip → BUY",
            },
        ],
        parameters={
            "std_bands": {
                "default": 2.0,
                "description": "Standard deviation band multiplier",
                "type": "float",
            },
            "start_time": {
                "default": "10:30",
                "description": "Earliest entry time (IST)",
                "type": "str",
            },
            "end_time": {
                "default": "14:00",
                "description": "Latest entry time (IST)",
                "type": "str",
            },
        },
        timeframes=["1m", "3m", "5m"],
        instruments=["indices", "futures"],
        risks=[
            "Intraday data required — does not work on daily bars",
            "Trend days cause extended VWAP deviations with no reversion",
            "News-driven moves ignore VWAP entirely",
        ],
        tags=["mean_reversion", "vwap", "intraday", "intermediate"],
        complexity="intermediate",
        backtest_key=None,  # requires intraday tick data
    ),
    "zscore_reversion": TechnicalTemplate(
        id="zscore_reversion",
        name="Z-Score Mean Reversion",
        category="mean_reversion",
        layman_explanation=(
            "Z-score answers: 'Is this price weird, or normal?' "
            "Example: AXISBANK usually trades around ₹1,000 and swings about ₹20 a day. "
            "Today it closes at ₹1,080 — ₹80 above normal, which is 4 times its typical daily swing. "
            "Z-score = +4. That's extreme. Extremes almost always correct back toward normal. "
            "If it drops to ₹900 (Z-score = -5), that's even more extreme in the other direction — buy hard. "
            "The math is pure: buy when something is historically cheap, sell when historically expensive."
        ),
        explanation=(
            "Rolling z-score = (close - N-day mean) / N-day std. "
            "Enter long when z < -2, short when z > +2. Exit when z reverts to 0. "
            "Default lookback: 20 days. Best for stable, low-beta stocks with mean-reverting behaviour."
        ),
        when_to_use="Stable, liquid, large-cap stocks in sideways markets; pairs trading spread.",
        when_not_to_use="High-beta, news-driven stocks or during trending markets.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Rolling z-score drops below -2.0",
                "example": "e.g. HDFC Bank: 20-day mean ₹1,600, std ₹40. Price at ₹1,520 → z = -2.0 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Rolling z-score rises above +2.0",
                "example": "e.g. HDFC Bank: price at ₹1,680 → z = +2.0 → SELL",
            },
            {
                "signal": "EXIT",
                "condition": "Z-score returns to 0 (price back at rolling mean)",
                "example": "Price returns to ₹1,600 → z = 0 → take profit",
            },
        ],
        parameters={
            "lookback": {
                "default": 20,
                "description": "Rolling mean/std lookback period",
                "type": "int",
            },
            "entry_z": {
                "default": 2.0,
                "description": "Z-score threshold to enter",
                "type": "float",
            },
        },
        timeframes=["1D"],
        instruments=["stocks"],
        risks=[
            "Mean may shift permanently — stock may not revert after a fundamental change",
            "Z-score of -2 in a downtrend is just 'cheaper expensive stock'",
            "Requires the underlying to be genuinely stationary (mean-reverting)",
        ],
        tags=["mean_reversion", "zscore", "statistical", "intermediate"],
        complexity="intermediate",
        backtest_key="zscore",
    ),
    "keltner_reversion": TechnicalTemplate(
        id="keltner_reversion",
        name="Keltner Channel Reversion",
        category="mean_reversion",
        layman_explanation=(
            "Keltner Channels are highway guardrails — stocks stay inside them most of the time. "
            "When a stock strays outside a guardrail, it naturally drifts back to the center lane. "
            "Example: NIFTY's center is ₹24,000. Upper guardrail at ₹24,350. "
            "Price closes at ₹24,380 — outside the guardrail. "
            "Short it, target ₹24,000. "
            "Works like Bollinger Bands but is smoother, built on actual average daily swings "
            "rather than pure statistical math."
        ),
        explanation=(
            "Middle = 20 EMA. Upper = 20 EMA + 2×ATR(10). Lower = 20 EMA - 2×ATR(10). "
            "Fade price at the extremes: buy lower band touch, sell upper band touch. "
            "Keltner channels are tighter than Bollinger during low-volatility periods — "
            "when price breaks out of both (BB outside Keltner = 'squeeze'), expect a big move."
        ),
        when_to_use="Range-bound markets as a cleaner alternative to Bollinger Bands.",
        when_not_to_use="Trending markets where price consistently stays above or below the channel.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price closes below the lower Keltner Band",
                "example": "e.g. ASIANPAINT: lower band ₹2,600, price closes ₹2,580 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Price closes above the upper Keltner Band",
                "example": "e.g. ASIANPAINT: upper band ₹3,000, price closes ₹3,020 → SELL",
            },
        ],
        parameters={
            "ema_period": {
                "default": 20,
                "description": "EMA period for channel midline",
                "type": "int",
            },
            "atr_multiplier": {
                "default": 2.0,
                "description": "ATR multiplier for band width",
                "type": "float",
            },
        },
        timeframes=["1h", "1D"],
        instruments=["stocks", "indices"],
        risks=[
            "Trending stocks can walk the upper/lower band indefinitely",
            "ATR expands during volatility — bands widen right when you want to fade",
        ],
        tags=["mean_reversion", "keltner", "atr", "bands", "intermediate"],
        complexity="intermediate",
        backtest_key="keltner",
    ),
    # ── SCALPING (4) ──────────────────────────────────────────
    "orb": TechnicalTemplate(
        id="orb",
        name="Opening Range Breakout (ORB)",
        category="scalping",
        layman_explanation=(
            "The first 15 minutes after 9:15 AM is a knife fight — buyers and sellers "
            "arguing over where prices should be. That fight creates a range: a high and a low. "
            "One side will eventually win. When price breaks above that range — buyers won. Ride with them. "
            "Example: 9:15–9:30, NIFTY ranges ₹24,000–₹24,120. "
            "At 9:35, price closes at ₹24,145 — above the range. Buy, target ₹24,240 "
            "(same ₹120 distance as the opening range). Stop-loss below ₹24,000."
        ),
        explanation=(
            "Define the opening range as the high/low of the first 15 or 30 minutes (9:15–9:30 AM IST). "
            "Entry on breakout of range with a close above/below. "
            "Exit at 1:1 or 2:1 R:R or at 3:00 PM. "
            "Skip on gap-open days (> 0.5% gap) as the range is distorted."
        ),
        when_to_use="Trending intraday sessions; NIFTY/BANKNIFTY futures and F&O liquid stocks.",
        when_not_to_use="Gap-open days, event days (RBI, results) where the range is meaningless.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price closes above the opening range high with volume confirmation",
                "example": "e.g. NIFTY: 9:15–9:30 range is ₹24,000–₹24,120. Price closes at ₹24,135 at 9:35 AM → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Price closes below the opening range low",
                "example": "e.g. NIFTY: price closes at ₹23,990 at 9:35 AM → SELL",
            },
        ],
        parameters={
            "range_minutes": {
                "default": 15,
                "description": "Opening range duration in minutes",
                "type": "int",
            },
            "rr_target": {
                "default": 2.0,
                "description": "Reward:risk ratio for exit",
                "type": "float",
            },
            "gap_filter_pct": {
                "default": 0.5,
                "description": "Skip if gap open > this %",
                "type": "float",
            },
        },
        timeframes=["1m", "3m", "5m"],
        instruments=["indices", "futures"],
        risks=[
            "False breakouts common — price breaks range then reverses immediately",
            "Requires intraday data and discipline to take every signal",
            "Afternoon sessions often lose the ORB momentum",
        ],
        tags=["scalping", "intraday", "breakout", "orb", "beginner"],
        complexity="beginner",
        backtest_key=None,  # requires intraday OHLCV
    ),
    "rsi_scalping": TechnicalTemplate(
        id="rsi_scalping",
        name="RSI Scalping (Ultra-short)",
        category="scalping",
        layman_explanation=(
            "Sometimes a big sell order hits the market and a stock drops ₹15 in 3 minutes — "
            "not because anything is wrong, just because someone was forced to sell in a hurry. "
            "RSI scalping catches that panic: when the 2-minute RSI falls below 10, "
            "the selling was so violent that a snap-back is almost certain. "
            "Example: HDFC Bank drops ₹18 in 4 minutes, 2-minute RSI hits 7. Buy immediately. "
            "Hold 5-10 minutes, exit at ₹8-12 gain per share. Small profit, very frequent. "
            "Requires fast execution and strict discipline — not for beginners."
        ),
        explanation=(
            "RSI(2) or RSI(5) on 1m/3m chart. "
            "Buy when RSI < 10 (extreme oversold), sell short when RSI > 90. "
            "Exit when RSI crosses 50 or at a fixed point target (5–8 points on NIFTY). "
            "Works best on index futures during high-volume sessions."
        ),
        when_to_use="High-volume intraday sessions on liquid index futures; 10:00 AM–2:30 PM IST.",
        when_not_to_use="Low-volume midday sessions; trending days where RSI stays extreme.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "RSI(2) < 10 on a 1-minute or 3-minute chart",
                "example": "e.g. NIFTY futures: 3-min RSI drops to 7 → extreme short-term oversold → quick BUY scalp",
            },
            {
                "signal": "SELL",
                "condition": "RSI(2) > 90 on a 1-minute or 3-minute chart",
                "example": "e.g. NIFTY futures: 3-min RSI spikes to 94 → short scalp → SELL",
            },
        ],
        parameters={
            "rsi_period": {"default": 2, "description": "Ultra-short RSI period", "type": "int"},
            "buy_level": {"default": 10, "description": "Oversold entry level", "type": "int"},
            "sell_level": {"default": 90, "description": "Overbought entry level", "type": "int"},
        },
        timeframes=["1m", "3m"],
        instruments=["indices", "futures"],
        risks=[
            "Extremely high trade frequency — commissions and slippage add up quickly",
            "Requires laser focus — positions held for seconds to minutes",
            "Needs Level 2 / depth-of-market data for best execution",
        ],
        tags=["scalping", "rsi", "intraday", "ultra_short", "advanced"],
        complexity="advanced",
        backtest_key=None,  # requires tick/1m data
    ),
    "vwap_scalp": TechnicalTemplate(
        id="vwap_scalp",
        name="VWAP Scalp",
        category="scalping",
        layman_explanation=(
            "Institutional fund managers are evaluated against VWAP — their mandate says 'execute at VWAP'. "
            "This means when price dips back to VWAP, they are waiting there with large buy orders. "
            "You step in just before them. "
            "Example: NIFTY VWAP = ₹24,100 at 11 AM. Price has been above it all morning at ₹24,180. "
            "It dips to ₹24,105 — touching VWAP. Buy. Institution shows up, price bounces to ₹24,160. "
            "Exit. You made ₹55 in 8 minutes by knowing where the buying wall was."
        ),
        explanation=(
            "Long on first touch of VWAP after a sustained move above it (VWAP reclaim). "
            "Short on rejection from VWAP after a sustained move below. "
            "Tight stop: 5–8 points on NIFTY, just beyond VWAP. Target: prior swing high/low."
        ),
        when_to_use="Trending intraday days where VWAP is acting as a dynamic support/resistance.",
        when_not_to_use="Choppy days with price crossing VWAP every 15 minutes.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price bounces off VWAP after being above it; bullish candle at VWAP",
                "example": "e.g. BANKNIFTY: trading above VWAP all morning, pulls back to VWAP at ₹47,200, forms doji → BUY scalp",
            },
            {
                "signal": "SELL",
                "condition": "Price rejects VWAP from below; bearish candle at VWAP",
                "example": "e.g. BANKNIFTY: below VWAP all session, rallies to VWAP at ₹47,500, reversal candle → SELL",
            },
        ],
        parameters={
            "stop_points": {
                "default": 8,
                "description": "Stop loss in index points",
                "type": "int",
            },
            "require_confirmation": {
                "default": True,
                "description": "Wait for reversal candle at VWAP",
                "type": "bool",
            },
        },
        timeframes=["1m", "3m", "5m"],
        instruments=["indices", "futures"],
        risks=[
            "Intraday VWAP only available with tick/intraday data feed",
            "Multiple VWAP tests in one session reduce reliability",
            "News events can blow through VWAP with no bounce",
        ],
        tags=["scalping", "vwap", "intraday", "support_resistance", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    "prev_day_hl": TechnicalTemplate(
        id="prev_day_hl",
        name="Previous Day High / Low Breakout",
        category="scalping",
        layman_explanation=(
            "Yesterday's high and low are invisible walls where thousands of stop-loss orders sit. "
            "When price breaks through yesterday's high, every stop triggers at once — "
            "a sudden flood of buyers enters and price accelerates. "
            "Example: Yesterday RELIANCE high = ₹1,280. Today at 10:15 AM, "
            "price crosses ₹1,283 with heavy volume. Every short-seller's stop triggers. "
            "Price shoots to ₹1,295 in 20 minutes. "
            "You entered at ₹1,283, captured ₹12 — an avalanche others set up for you."
        ),
        explanation=(
            "PDH/PDL are strong intraday reference levels. "
            "Buy on a 5-minute candle close above PDH with volume > 1.5× average. "
            "Short on close below PDL. "
            "Target: PDH + (PDH - PDL) i.e. range extension. Stop: below PDH."
        ),
        when_to_use="First 90 minutes of trading (9:15–10:45 AM IST); trending market days.",
        when_not_to_use="Days that gap above PDH at open — PDH is no longer meaningful.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "5-min candle closes above previous day high with volume surge",
                "example": "e.g. RELIANCE: PDH ₹2,900. Price breaks ₹2,905 at 9:40 AM with 2× volume → BUY",
            },
            {
                "signal": "SELL",
                "condition": "5-min candle closes below previous day low",
                "example": "e.g. RELIANCE: PDL ₹2,820. Price breaks ₹2,815 at 9:50 AM → SELL",
            },
        ],
        parameters={
            "confirmation_candles": {
                "default": 1,
                "description": "Candles needed to confirm break",
                "type": "int",
            },
            "volume_multiplier": {
                "default": 1.5,
                "description": "Volume vs average to confirm",
                "type": "float",
            },
        },
        timeframes=["5m", "15m"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "False breakouts happen often — price pokes above PDH then reverses",
            "Requires previous day OHLC data and intraday bars",
            "Stop is tight — noise can stop you out before the move develops",
        ],
        tags=["scalping", "breakout", "intraday", "pdh", "pdl", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    # ── BREAKOUT (3) ──────────────────────────────────────────
    "pivot_breakout": TechnicalTemplate(
        id="pivot_breakout",
        name="Pivot Point Breakout",
        category="breakout",
        layman_explanation=(
            "Pivot points are calculated by every trader, every algorithm, every prop desk — "
            "all using the same formula from yesterday's numbers. "
            "Because everyone watches the same levels, they become self-fulfilling. "
            "Example: NIFTY Pivot = ₹24,000, R1 = ₹24,200. Price stalls below ₹24,200 all morning. "
            "At 1:15 PM it blasts through ₹24,205 on high volume. Next target is R2 = ₹24,380. "
            "You entered at ₹24,210 and rode ₹170 — just by reading the same map as everyone else."
        ),
        explanation=(
            "Standard pivots: P = (H + L + C) / 3; R1 = 2P - L; R2 = P + (H - L); "
            "S1 = 2P - H; S2 = P - (H - L). "
            "Trade breakouts of R1/R2 (long) or S1/S2 (short) with a close beyond the level on a 5-minute bar."
        ),
        when_to_use="Intraday trending days; most effective in the first 2 hours of trading.",
        when_not_to_use="Days with large overnight gaps that skew the pivot calculations.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Price closes above R1 on a 5-minute bar",
                "example": "e.g. NIFTY: R1 at ₹24,200. 5-min candle closes at ₹24,215 → BUY, target R2 at ₹24,400",
            },
            {
                "signal": "SELL",
                "condition": "Price closes below S1 on a 5-minute bar",
                "example": "e.g. NIFTY: S1 at ₹23,800. Closes at ₹23,785 → SELL, target S2 at ₹23,600",
            },
        ],
        parameters={
            "pivot_type": {
                "default": "standard",
                "description": "Pivot type: standard/camarilla/fibonacci/woodie",
                "type": "str",
            },
            "level": {
                "default": "R1",
                "description": "Which level to trade: R1, R2, S1, S2",
                "type": "str",
            },
        },
        timeframes=["5m", "15m"],
        instruments=["indices", "futures"],
        risks=[
            "Calculated from previous day's OHLC — gaps or limit moves distort them",
            "R1 is often hit and reversed before reaching R2",
            "Multiple overlapping pivot levels create conflicting signals",
        ],
        tags=["breakout", "pivot", "intraday", "support_resistance", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    "inside_bar": TechnicalTemplate(
        id="inside_bar",
        name="Inside Bar Breakout",
        category="breakout",
        layman_explanation=(
            "An inside bar is a day where the market couldn't make a new high or a new low — "
            "buyers and sellers reached a perfect standoff. Think of it as a coiled spring. "
            "Example: Monday, HDFC Bank ranged ₹1,750–₹1,820. "
            "Tuesday closes entirely inside: ₹1,760–₹1,808. "
            "The spring is coiling. Wednesday morning opens at ₹1,815, breaks above ₹1,820 — "
            "buyers won the standoff. Buy ₹1,822, stop-loss ₹1,749 (Monday's low). "
            "The sharper the breakout, the more energy was stored."
        ),
        explanation=(
            "Inside bar: current high < previous high AND current low > previous low. "
            "Signal fires on the next candle: close above prior high = bullish break; "
            "close below prior low = bearish break. "
            "Best on daily and weekly charts for swing trades. "
            "ATR-based stop: beyond the prior candle's extreme."
        ),
        when_to_use="After a strong directional move; consolidation at key support/resistance on daily chart.",
        when_not_to_use="Choppy markets where inside bars occur every other day with no follow-through.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Candle after the inside bar closes above the prior candle's high",
                "example": "e.g. TCS: inside bar on Tuesday (H: ₹3,850, L: ₹3,790). Wednesday closes ₹3,870 → BUY",
            },
            {
                "signal": "SELL",
                "condition": "Candle after the inside bar closes below the prior candle's low",
                "example": "e.g. TCS: Wednesday closes ₹3,770 → SELL",
            },
        ],
        parameters={
            "atr_stop_multiplier": {
                "default": 1.0,
                "description": "ATR multiplier for stop beyond the pattern",
                "type": "float",
            },
        },
        timeframes=["1D", "1W"],
        instruments=["stocks", "indices"],
        risks=[
            "False breakouts common — especially if inside bar is very small",
            "Requires patience — inside bars on daily charts may only occur a few times per month",
        ],
        tags=["breakout", "price_action", "inside_bar", "swing", "beginner"],
        complexity="beginner",
        backtest_key="inside_bar",
    ),
    "flag_pennant": TechnicalTemplate(
        id="flag_pennant",
        name="Flag / Pennant Continuation",
        category="breakout",
        layman_explanation=(
            "A stock jumps 7% in two days — that's the flagpole. Then it drifts sideways for a week "
            "as traders take profits — that's the flag. Not a reversal, just a rest. "
            "When price breaks out of that tight sideways range in the same direction, "
            "the next leg tends to be the same size as the original jump. "
            "Example: INFY runs from ₹1,500 to ₹1,605 (+7%) in two days. Drifts sideways ₹1,575–₹1,600. "
            "Breaks above ₹1,602. Buy. Target: ₹1,707 (another +7% from breakout). "
            "You're buying after the stock has rested and reloaded."
        ),
        explanation=(
            "Flag: a tight rectangular consolidation after a sharp move, sloping slightly against the trend. "
            "Pennant: converging trendlines (triangle) after an impulse move. "
            "Entry on breakout of the flag/pennant boundary with volume expansion. "
            "Target: entry + flagpole length. Stop: below the flag low."
        ),
        when_to_use="Strong trending stocks after a clear impulse move and consolidation.",
        when_not_to_use="When the 'flagpole' is less than 5% — pattern is too weak to trade.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Break above the flag's upper boundary after a bullish impulse move",
                "example": "e.g. INFY: sharp 8% move up, 5-day sideways flag. Break of flag top → BUY, target = +8% from breakout",
            },
            {
                "signal": "SELL",
                "condition": "Break below flag bottom after a bearish impulse move",
                "example": "e.g. INFY: sharp -7% move, flag forms. Break below flag base → SELL",
            },
        ],
        parameters={
            "min_impulse_pct": {
                "default": 5.0,
                "description": "Minimum flagpole move % to qualify",
                "type": "float",
            },
            "max_consolidation_days": {
                "default": 15,
                "description": "Max days of flag/pennant",
                "type": "int",
            },
        },
        timeframes=["1h", "1D"],
        instruments=["stocks", "indices"],
        risks=[
            "Pattern recognition is subjective — two traders may see different flags",
            "Breakouts after weak impulse moves often fail",
            "Cannot be easily automated without pattern detection algorithms",
        ],
        tags=["breakout", "price_action", "flag", "pennant", "continuation", "intermediate"],
        complexity="intermediate",
        backtest_key=None,  # requires pattern recognition
    ),
    # ── PAIRS (4) ─────────────────────────────────────────────
    "pairs_trading": TechnicalTemplate(
        id="pairs_trading",
        name="Pairs Trading",
        category="pairs",
        layman_explanation=(
            "TCS and Infosys are siblings — same business, same cycle, almost always move together. "
            "Normally TCS trades at about 1.4× the price of Infosys. "
            "One day: TCS jumps to ₹4,200, Infosys stays at ₹2,700. Ratio = 1.56 — TCS is too expensive. "
            "Buy ₹1 lakh of Infosys, short ₹1 lakh of TCS. "
            "Over the next few days the ratio drifts back to 1.4. "
            "Both legs close in profit. The market's direction doesn't matter — only the gap between siblings does."
        ),
        explanation=(
            "Cointegration test to find a stationary pair. "
            "Spread = log(Stock A) - hedge_ratio × log(Stock B). "
            "Trade when z-score of spread > 2 (short the spread) or < -2 (long the spread). "
            "Exit when z-score returns to 0. Stop at z = 3."
        ),
        when_to_use="Sector pairs with stable long-term relationships; market-neutral view.",
        when_not_to_use="When the pair's fundamental relationship has broken (e.g. one company has a large acquisition).",
        signal_rules=[
            {
                "signal": "BUY SPREAD",
                "condition": "Z-score of spread < -2.0 (Stock A unusually cheap vs B)",
                "example": "e.g. TCS/INFY spread z-score = -2.3 → buy TCS, sell INFY (equal INR value)",
            },
            {
                "signal": "SELL SPREAD",
                "condition": "Z-score of spread > +2.0 (Stock A unusually expensive vs B)",
                "example": "e.g. TCS/INFY spread z-score = +2.1 → sell TCS, buy INFY",
            },
        ],
        parameters={
            "lookback": {
                "default": 60,
                "description": "Rolling window for z-score (days)",
                "type": "int",
            },
            "entry_z": {
                "default": 2.0,
                "description": "Z-score to enter position",
                "type": "float",
            },
            "stop_z": {"default": 3.0, "description": "Z-score to stop out", "type": "float"},
        },
        timeframes=["1D"],
        instruments=["stocks"],
        risks=[
            "Cointegration can break permanently — mean may never revert",
            "Requires simultaneous execution of two orders — slippage on both legs",
            "Market impact if position size is large relative to stock volume",
        ],
        tags=["pairs", "statistical_arbitrage", "market_neutral", "cointegration", "advanced"],
        complexity="advanced",
        backtest_key=None,  # uses MultiBacktester; future integration
    ),
    "index_arb": TechnicalTemplate(
        id="index_arb",
        name="Index Arbitrage",
        category="pairs",
        layman_explanation=(
            "NIFTY futures should cost slightly more than the actual index, because you're agreeing to buy later "
            "and your cash earns interest in the meantime. That 'fair price' is a formula. "
            "Example: NIFTY = ₹24,000. Fair value of 30-day futures (at 7% interest) = ₹24,140. "
            "Futures are trading at ₹24,280 — ₹140 above fair value. "
            "Sell ₹24,280 futures, buy the equivalent of all 50 NIFTY stocks. Lock in ₹140 per lot. "
            "By expiry, futures must converge to ₹24,000. The ₹140 profit is yours regardless of market direction."
        ),
        explanation=(
            "Fair value = Spot × e^(r×t) where r = risk-free rate, t = DTE/365. "
            "If futures premium > fair value → sell futures + buy basket. "
            "If futures at discount → buy futures + sell basket. "
            "Requires simultaneous execution of futures and all 50 NIFTY constituents."
        ),
        when_to_use="When futures premium/discount significantly exceeds fair value; requires high capital.",
        when_not_to_use="Near expiry when convergence is guaranteed — window too short for entry/exit cost.",
        signal_rules=[
            {
                "signal": "BUY FUTURES / SELL BASKET",
                "condition": "Futures at discount to fair value",
                "example": "e.g. NIFTY spot ₹24,000, fair value ₹24,080, futures at ₹24,050 → buy futures",
            },
            {
                "signal": "SELL FUTURES / BUY BASKET",
                "condition": "Futures at premium to fair value",
                "example": "e.g. NIFTY futures at ₹24,150 vs fair value ₹24,080 → sell futures",
            },
        ],
        parameters={
            "risk_free_rate": {"default": 0.065, "description": "RBI repo rate", "type": "float"},
        },
        timeframes=["1m"],
        instruments=["indices", "futures"],
        risks=[
            "Extremely capital intensive — need to buy/sell all 50 NIFTY components",
            "Execution risk — spread can widen before both legs are filled",
            "Institutional strategy — retail participation not practical",
        ],
        tags=["pairs", "arbitrage", "index", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    "etf_arb": TechnicalTemplate(
        id="etf_arb",
        name="ETF Arbitrage",
        category="pairs",
        layman_explanation=(
            "NIFTYBEES is a basket holding all 50 NIFTY stocks. "
            "It should be worth exactly what those 50 stocks are worth — but sometimes it isn't. "
            "Example: The 50 stocks are collectively worth ₹240.10 per NIFTYBEES unit, "
            "but NIFTYBEES is trading at ₹241.80 on NSE — a ₹1.70 premium. "
            "Buy the 50 stocks at ₹240.10, sell NIFTYBEES at ₹241.80. "
            "Collect ₹1.70 per unit as both sides converge. Zero directional risk. Pure gap capture."
        ),
        explanation=(
            "Monitor iNAV (intraday NAV) vs market price of ETF. "
            "If ETF market price > iNAV by > 0.1% → sell ETF, buy underlying (creation). "
            "If ETF price < iNAV by > 0.1% → buy ETF, redeem for underlying. "
            "Authorised participants do this continuously — retail window is very small."
        ),
        when_to_use="When ETF premium/discount exceeds round-trip transaction costs.",
        when_not_to_use="For retail investors — gap is usually too small after costs; institutional play.",
        signal_rules=[
            {
                "signal": "BUY ETF",
                "condition": "ETF market price < iNAV - transaction cost threshold",
                "example": "e.g. NIFTYBEES iNAV ₹230.50, market price ₹229.80 → discount of 0.30% → BUY",
            },
            {
                "signal": "SELL ETF",
                "condition": "ETF market price > iNAV + transaction cost threshold",
                "example": "e.g. NIFTYBEES iNAV ₹230.50, market price ₹231.50 → premium → SELL",
            },
        ],
        parameters={
            "min_gap_pct": {
                "default": 0.1,
                "description": "Minimum premium/discount % to trade",
                "type": "float",
            },
        },
        timeframes=["1m", "5m"],
        instruments=["etfs"],
        risks=[
            "iNAV data requires a real-time data feed",
            "Creation/redemption is only available to authorised participants",
            "Gap closes quickly — execution must be near-instant",
        ],
        tags=["pairs", "arbitrage", "etf", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    "calendar_spread_futures": TechnicalTemplate(
        id="calendar_spread_futures",
        name="Calendar Spread (Futures)",
        category="pairs",
        layman_explanation=(
            "January and March NIFTY futures are the same index — the only difference is time. "
            "The price gap between them should equal roughly 2 months of interest on your capital. "
            "At 7% annual interest, that's about ₹280 per ₹24,000 lot. "
            "Example: January futures at ₹24,050, March futures at ₹24,480 — gap of ₹430, not ₹280. "
            "Sell March at ₹24,480, buy January at ₹24,050. Lock in ₹150 extra. "
            "By March expiry, the gap must collapse to zero. No prediction needed."
        ),
        explanation=(
            "Fair spread = Spot × r × (T2 - T1)/365. "
            "If actual spread > fair spread → sell near, buy far (spread will narrow). "
            "If spread < fair → buy near, sell far. "
            "Instruments: NIFTY, BANKNIFTY, single stock futures."
        ),
        when_to_use="When the term structure of futures is significantly mis-priced relative to cost-of-carry.",
        when_not_to_use="Near expiry of the near-month contract — liquidity drops sharply.",
        signal_rules=[
            {
                "signal": "SELL SPREAD (sell near, buy far)",
                "condition": "Near–far spread > cost-of-carry fair value",
                "example": "e.g. NIFTY near ₹24,300, far ₹24,500, fair spread ₹120. Actual spread ₹200 → sell near, buy far",
            },
            {
                "signal": "BUY SPREAD (buy near, sell far)",
                "condition": "Near–far spread < cost-of-carry fair value",
                "example": "e.g. Actual spread ₹40 vs fair ₹120 → buy near, sell far",
            },
        ],
        parameters={
            "risk_free_rate": {
                "default": 0.065,
                "description": "RBI repo rate (decimal)",
                "type": "float",
            },
        },
        timeframes=["1D"],
        instruments=["futures"],
        risks=[
            "Low liquidity on far-month contracts — wide bid-ask spreads",
            "Requires simultaneous execution of two futures contracts",
            "Rollover costs reduce profitability if held too long",
        ],
        tags=["pairs", "futures", "calendar", "cost_of_carry", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    # ── MACRO (5) ─────────────────────────────────────────────
    "rbi_policy": TechnicalTemplate(
        id="rbi_policy",
        name="RBI Policy Trade",
        category="macro",
        layman_explanation=(
            "RBI rate decisions cause big market moves — but nobody knows which way. "
            "Strategy 1 (straddle): NIFTY at ₹24,000. Buy a ₹24,000 call for ₹120 and a ₹24,000 put for ₹110. "
            "Total cost: ₹230. If NIFTY moves more than ₹230 in either direction — you profit. "
            "Strategy 2 (momentum): Wait for the announcement. If markets start rallying hard, "
            "buy the first pullback. Both strategies work. Neither requires you to predict the RBI."
        ),
        explanation=(
            "Pre-event: buy ATM straddle 2 days before → exit within 30 minutes of announcement. "
            "Post-event: if rate cut → buy BANKNIFTY, sell NIFTY (bank-heavy). "
            "If rate hold/surprise hike → buy interest-rate sensitive shorts. "
            "RBI meets 6 times a year."
        ),
        when_to_use="Before scheduled RBI Monetary Policy Committee meetings.",
        when_not_to_use="When market has already priced in the expected move — IV is already very high.",
        signal_rules=[
            {
                "signal": "BUY STRADDLE (pre-event)",
                "condition": "2 days before RBI announcement and IV is not elevated",
                "example": "e.g. NIFTY at ₹24,000, buy 24000 CE + 24000 PE. If market moves 1%+ either way, straddle profits.",
            },
            {
                "signal": "BUY (post-event, rate cut)",
                "condition": "RBI cuts rates → financials and rate-sensitive stocks rally",
                "example": "RBI cuts 25bps → buy BANKNIFTY futures → target 2% move in next 30 minutes",
            },
        ],
        parameters={
            "days_before": {
                "default": 2,
                "description": "Days before announcement to enter straddle",
                "type": "int",
            },
            "exit_minutes": {
                "default": 30,
                "description": "Minutes after announcement to exit",
                "type": "int",
            },
        },
        timeframes=["1D", "5m"],
        instruments=["indices", "futures", "options"],
        risks=[
            "IV crush after announcement can wipe out gains even if the market moves",
            "Post-announcement direction trade can reverse within minutes",
            "RBI surprises (hawkish hold, emergency cut) are unpredictable",
        ],
        tags=["macro", "event_driven", "rbi", "straddle", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    "fii_flow": TechnicalTemplate(
        id="fii_flow",
        name="FII Flow Following",
        category="macro",
        layman_explanation=(
            "Foreign investors (FIIs) are the single biggest force in Indian markets — "
            "their buying and selling moves NIFTY by 100-300 points. "
            "SEBI publishes exactly how much they bought or sold each day. "
            "Example: FIIs net bought ₹3,200 cr on Monday, ₹4,800 cr on Tuesday, ₹2,600 cr on Wednesday. "
            "Three consecutive days of heavy buying. On Thursday morning, buy NIFTY futures. "
            "Don't predict — follow the elephant. When it walks in one direction, get out of the way or join it."
        ),
        explanation=(
            "NSE publishes daily FII/DII buy-sell data. "
            "Signal: FII net buy > ₹2,000 Cr for 3 consecutive days → long NIFTY. "
            "FII net sell > ₹2,000 Cr for 3 days → reduce longs / go short. "
            "Hold position until signal reverses or 10 trading days pass."
        ),
        when_to_use="As a medium-term (weekly) market direction filter; combine with technical entry.",
        when_not_to_use="During global risk-off events where FII flows are driven by factors outside India.",
        signal_rules=[
            {
                "signal": "BUY NIFTY",
                "condition": "FII net buy > ₹2,000 Cr for 3 consecutive sessions",
                "example": "e.g. FII buy: Day1 ₹2,500 Cr, Day2 ₹3,100 Cr, Day3 ₹2,200 Cr → BUY NIFTY",
            },
            {
                "signal": "REDUCE / SHORT",
                "condition": "FII net sell > ₹2,000 Cr for 3 consecutive sessions",
                "example": "e.g. FII sell: 3 days of ₹2,000+ Cr outflows → reduce equity exposure",
            },
        ],
        parameters={
            "threshold_cr": {
                "default": 2000,
                "description": "FII net buy/sell threshold in ₹ Cr",
                "type": "int",
            },
            "consecutive_days": {
                "default": 3,
                "description": "Days of consistent flow to trigger signal",
                "type": "int",
            },
        },
        timeframes=["1D"],
        instruments=["indices", "futures"],
        risks=[
            "Lagging indicator — FII data published end-of-day, after the move is underway",
            "FII can reverse rapidly — 3-day trend can break on day 4",
            "During global crises, FII flows are not actionable — exit speed matters",
        ],
        tags=["macro", "fii", "flow", "sentiment", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    "vix_reversion": TechnicalTemplate(
        id="vix_reversion",
        name="VIX Mean Reversion",
        category="macro",
        layman_explanation=(
            "India VIX is the market's fear-o-meter. "
            "Example: VIX spikes to 24 during a geopolitical scare. "
            "A NIFTY straddle that normally costs ₹300 now costs ₹520 — people are overpaying for insurance. "
            "Sell the straddle at ₹520. Over the next 7 days, fear fades and VIX drops to 14. "
            "The straddle is now worth ₹180. Buy it back. Pocket ₹340. "
            "Flip side: VIX at 10 = everyone relaxed, options at ₹150. Buy cheap insurance before the next shock."
        ),
        explanation=(
            "India VIX > 20 → short straddle, iron condor — collect elevated premiums that will deflate as VIX normalises. "
            "India VIX < 11 → buy straddles, long options — cheap insurance before next volatility spike. "
            "VIX typically mean-reverts within 5–15 trading days of an extreme."
        ),
        when_to_use="After a volatility spike (VIX > 20) — sell premium. Before expected events when VIX < 11.",
        when_not_to_use="During structural changes to the market — VIX can sustain elevated levels for months.",
        signal_rules=[
            {
                "signal": "SELL PREMIUM",
                "condition": "India VIX > 20 (fear elevated → options overpriced)",
                "example": "e.g. India VIX at 23 post-election concern → sell NIFTY iron condor, collect inflated premium",
            },
            {
                "signal": "BUY OPTIONS",
                "condition": "India VIX < 11 (complacency → options cheap)",
                "example": "e.g. VIX at 10.5 in a calm market → buy cheap NIFTY straddle before next catalyst",
            },
        ],
        parameters={
            "high_vix": {
                "default": 20,
                "description": "VIX level above which premium selling is favoured",
                "type": "int",
            },
            "low_vix": {
                "default": 11,
                "description": "VIX level below which buying options is favoured",
                "type": "int",
            },
        },
        timeframes=["1D"],
        instruments=["indices", "options"],
        risks=[
            "VIX can spike further after you sell premium — unlimited loss on naked positions",
            "Low VIX can persist for months without a spike materialising",
            "India VIX data requires a separate data source (not standard OHLCV feed)",
        ],
        tags=["macro", "vix", "volatility", "regime", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    "earnings_momentum": TechnicalTemplate(
        id="earnings_momentum",
        name="Earnings Momentum",
        category="macro",
        layman_explanation=(
            "Before quarterly results, nobody knows if a company will beat or miss. "
            "That uncertainty alone makes options expensive — fear and greed both peak. "
            "Strategy 1 (pre-results): Infosys results in 6 days. Buy the ₹1,800 call for ₹22. "
            "Day before results, the same call costs ₹42 — fear of missing a big move has driven it up. "
            "Sell at ₹42. ₹20 profit, and you never even took the earnings risk. "
            "Strategy 2 (post-beat): Infosys beats by 8%. Next morning, buy the stock. "
            "Analyst upgrades and fund flows typically push it another 5-10% over 2-3 weeks."
        ),
        explanation=(
            "Pre-earnings IV play: buy ATM straddle 5 days before → sell on announcement day (capture IV expansion). "
            "Post-earnings momentum: buy breakout on next day if results beat estimates by > 10% and stock gaps up > 2%. "
            "Hold for 3–5 days to capture the follow-through momentum."
        ),
        when_to_use="Around quarterly earnings season (April, July, October, January for most NSE companies).",
        when_not_to_use="When IV is already inflated before earnings (market expects a big move — too expensive).",
        signal_rules=[
            {
                "signal": "BUY STRADDLE (pre-earnings)",
                "condition": "5 days before earnings date and IV is not already elevated",
                "example": "e.g. WIPRO results in 5 days. Current IV normal. Buy 400CE + 400PE → sell morning of results.",
            },
            {
                "signal": "BUY (post-earnings momentum)",
                "condition": "Results beat estimates > 10% + stock gaps up > 2% on results day",
                "example": "e.g. HDFC reports 15% profit beat. Stock gaps up 3%. Buy at open, hold 3 days.",
            },
        ],
        parameters={
            "pre_days": {
                "default": 5,
                "description": "Days before earnings to enter IV play",
                "type": "int",
            },
            "beat_threshold_pct": {
                "default": 10,
                "description": "Earnings beat % to trigger momentum buy",
                "type": "float",
            },
            "gap_threshold_pct": {
                "default": 2.0,
                "description": "Gap up % required on results day",
                "type": "float",
            },
        },
        timeframes=["1D"],
        instruments=["stocks", "options"],
        risks=[
            "IV crush on announcement day can wipe out straddle gains even on a big move",
            "Earnings calendar requires an external data source",
            "Post-earnings momentum can reverse sharply if sector/market conditions worsen",
        ],
        tags=["macro", "earnings", "event_driven", "momentum", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    "sector_rotation": TechnicalTemplate(
        id="sector_rotation",
        name="Sector Rotation",
        category="macro",
        layman_explanation=(
            "The economy moves in cycles — banks lead one phase, then IT, then pharma, then FMCG. "
            "Each phase lasts months, and the winner of last month often keeps winning next month. "
            "Example: April check — PSU Banks +9%, IT +2%, Pharma -1%, FMCG +3%. "
            "For May: put your money in the PSU Bank ETF and FMCG ETF. "
            "Check again at end of May, rotate to whatever is leading then. "
            "No prediction needed — just follow who is already winning."
        ),
        explanation=(
            "Rank all NIFTY sector indices by trailing 1-month return. "
            "Allocate equally to the top 2 sectors via sector ETFs (BANKBEES, ITBEES, PHARMABEES, etc.). "
            "Rebalance on the last Thursday of each month to align with F&O expiry. "
            "Filter: only hold a sector if its 1-month return is positive (absolute momentum filter)."
        ),
        when_to_use="Monthly rebalancing strategy; best in trending, rotation-heavy market regimes.",
        when_not_to_use="During sharp market-wide corrections — all sectors fall together.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Sector ranks in top 2 by 1-month return AND return is positive",
                "example": "e.g. April: PSU Banks up 8%, Pharma up 6%, IT up 1%. Allocate to PSU Banks + Pharma ETFs.",
            },
            {
                "signal": "EXIT / ROTATE",
                "condition": "Sector drops out of top 2 on monthly rebalance day",
                "example": "e.g. May rebalance: IT surges to top 2, Pharma drops → sell Pharma ETF, buy IT ETF",
            },
        ],
        parameters={
            "top_n": {"default": 2, "description": "Number of top sectors to hold", "type": "int"},
            "lookback_days": {
                "default": 21,
                "description": "Return lookback in trading days",
                "type": "int",
            },
        },
        timeframes=["1D"],
        instruments=["etfs"],
        risks=[
            "Momentum crash risk — top sectors of last month can be worst next month",
            "ETF liquidity (ITBEES, PHARMABEES) is lower than direct stocks",
            "Sector ETF data not always available via standard data feeds",
        ],
        tags=["macro", "rotation", "etf", "momentum", "monthly", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
    # ── QUANTITATIVE (3) ──────────────────────────────────────
    "dual_momentum": TechnicalTemplate(
        id="dual_momentum",
        name="Dual Momentum (Antonacci)",
        category="quantitative",
        layman_explanation=(
            "Once a month, answer two questions. "
            "Q1: Is NIFTY higher today than it was 3 months ago? "
            "If no — sell everything, sit in cash or FD. Done. "
            "If yes — Q2: Did NIFTY do better than Nifty Midcap over those 3 months? "
            "Hold whichever won. That's the complete system — two questions, once a month. "
            "Example: April check — NIFTY 3 months ago ₹22,000, today ₹24,100 (+9.5%). Q1: Yes. "
            "NIFTY +9.5% vs Midcap +6.2%. Q2: Hold NIFTY for May. Check again May 31."
        ),
        explanation=(
            "Absolute momentum: if N-day return of NIFTY > 0 → stay in equities. "
            "Relative momentum (multi-asset): hold the stronger of two assets (e.g. NIFTY vs Gold) "
            "based on trailing 3-month return. Rebalance monthly. "
            "Simplest implementation: single asset, stay long if 90-day return > 0, else cash (0)."
        ),
        when_to_use="Long-term (months to years) systematic investing; eliminates most bear market drawdowns.",
        when_not_to_use="Short-term trading — monthly rebalance is too slow for tactical adjustments.",
        signal_rules=[
            {
                "signal": "BUY (stay long)",
                "condition": "90-day return > 0 on monthly rebalance day",
                "example": "e.g. NIFTY was at ₹22,000 three months ago, now ₹24,000. Return +9% → stay long",
            },
            {
                "signal": "EXIT (go to cash)",
                "condition": "90-day return ≤ 0 on monthly rebalance day",
                "example": "e.g. NIFTY three months ago ₹25,000, now ₹23,500. Return -6% → exit to cash",
            },
        ],
        parameters={
            "lookback": {
                "default": 90,
                "description": "Return lookback in trading days (~3 months)",
                "type": "int",
            },
        },
        timeframes=["1D"],
        instruments=["indices", "etfs"],
        risks=[
            "Monthly rebalance misses intra-month crashes — drawdown before signal fires",
            "Whipsaw risk in choppy markets — alternates long/cash frequently",
            "Simple version ignores relative momentum — combine with sector rotation for full system",
        ],
        tags=["quantitative", "momentum", "systematic", "monthly", "long_term", "beginner"],
        complexity="beginner",
        backtest_key="dual_momentum",
    ),
    "factor_quality_momentum": TechnicalTemplate(
        id="factor_quality_momentum",
        name="Factor Strategy — Quality + Momentum",
        category="quantitative",
        layman_explanation=(
            "A two-round talent show for 500 NSE stocks. "
            "Round 1 — Quality: ROE above 20%? Debt-to-equity below 0.5? Profit growing? "
            "Say 90 stocks pass. "
            "Round 2 — Momentum: of those 90, which 25 have risen the most in the past 6 months? "
            "Keep those 25. Rebalance monthly. "
            "Example: Round 1 leaves Bajaj Finance, Titan, Pidilite, HDFC AMC. "
            "Round 2 picks the 25 with best 6-month price performance from that shortlist. "
            "You own great businesses that the market is already rewarding — a potent combination."
        ),
        explanation=(
            "Quality screen: ROE > 15%, Debt/Equity < 1, positive EPS growth. "
            "Momentum screen: top quartile 6-month price return among quality stocks. "
            "Portfolio: equal-weight top 20 stocks passing both filters. "
            "Rebalance monthly on last Thursday. "
            "Historical outperformance: Quality + Momentum factor portfolios have beaten NIFTY by 4-8% annually on NSE."
        ),
        when_to_use="Core long-term equity portfolio; works best over 3+ year horizons.",
        when_not_to_use="During factor rotation periods where value outperforms momentum strongly.",
        signal_rules=[
            {
                "signal": "BUY",
                "condition": "Stock passes quality screen AND ranks top quartile in 6-month momentum",
                "example": "e.g. DIXON Tech: ROE 28%, D/E 0.3, 6-month return +35% → qualifies → BUY",
            },
            {
                "signal": "EXIT",
                "condition": "Stock drops below quality or momentum thresholds on monthly rebalance",
                "example": "e.g. Stock's 6-month return drops below top quartile → rotate out",
            },
        ],
        parameters={
            "min_roe": {"default": 15, "description": "Minimum Return on Equity %", "type": "int"},
            "max_debt_equity": {
                "default": 1.0,
                "description": "Maximum Debt/Equity ratio",
                "type": "float",
            },
            "momentum_months": {
                "default": 6,
                "description": "Momentum lookback in months",
                "type": "int",
            },
            "portfolio_size": {
                "default": 20,
                "description": "Number of stocks to hold",
                "type": "int",
            },
        },
        timeframes=["1D"],
        instruments=["stocks"],
        risks=[
            "Requires fundamental data (ROE, debt) — not available in standard price feeds",
            "Factor crowding — if many funds use same screen, stocks get bid up",
            "Monthly rebalance incurs significant turnover and transaction costs",
        ],
        tags=["quantitative", "factor", "quality", "momentum", "fundamental", "advanced"],
        complexity="advanced",
        backtest_key=None,
    ),
    "volatility_sizing": TechnicalTemplate(
        id="volatility_sizing",
        name="Volatility-Adjusted Position Sizing",
        category="quantitative",
        layman_explanation=(
            "If you always buy 100 shares, you're betting 10x more on volatile stocks without realising it. "
            "100 shares of HDFC Bank (moves ₹20/day) = ₹2,000 daily risk. "
            "100 shares of BANKNIFTY (moves ₹200/day) = ₹20,000 daily risk — same share count, 10x the risk. "
            "Volatility sizing fixes this: you decide your risk per trade (say ₹5,000). "
            "HDFC Bank: buy 250 shares (₹5,000 ÷ ₹20). BANKNIFTY: buy 25 shares (₹5,000 ÷ ₹200). "
            "Every trade now risks the same rupees. One bad BANKNIFTY day can't wipe out a week of work."
        ),
        explanation=(
            "ATR-based sizing: quantity = (capital × risk_pct) / (ATR × stop_atr_multiplier). "
            "Kelly criterion variant: size = edge / odds (requires win rate and avg win/loss estimates). "
            "Portfolio volatility target: adjust all positions so total portfolio volatility = target% per day. "
            "Not a standalone signal generator — a sizing layer applied on top of any entry signal."
        ),
        when_to_use="On every trade as a risk management overlay; especially useful in a diversified portfolio.",
        when_not_to_use="As a standalone signal — this generates no entry/exit signals by itself.",
        signal_rules=[
            {
                "signal": "SIZE UP",
                "condition": "ATR is low relative to historical average → stock is calm → more shares",
                "example": "e.g. HDFC: ATR ₹15 (below 20-day avg ₹25). Capital ₹2L, risk 1% → trade 133 shares (₹2L × 1% / ₹15)",
            },
            {
                "signal": "SIZE DOWN",
                "condition": "ATR is high → stock is volatile → fewer shares",
                "example": "e.g. HDFC: ATR spikes to ₹50 (post-results). Same ₹2L capital → trade only 40 shares",
            },
        ],
        parameters={
            "risk_pct": {
                "default": 1.0,
                "description": "Risk per trade as % of capital",
                "type": "float",
            },
            "atr_period": {"default": 14, "description": "ATR lookback period", "type": "int"},
            "stop_atr": {
                "default": 2.0,
                "description": "Stop loss in ATR multiples",
                "type": "float",
            },
        },
        timeframes=["1D"],
        instruments=["stocks", "indices", "futures"],
        risks=[
            "Low ATR (calm market) can lead to oversized positions right before a volatility spike",
            "Requires accurate ATR calculation — different data feeds give slightly different values",
            "Kelly criterion can recommend very large sizes — use fractional Kelly (0.25–0.5×) for safety",
        ],
        tags=["quantitative", "risk_management", "position_sizing", "atr", "kelly", "intermediate"],
        complexity="intermediate",
        backtest_key=None,
    ),
}


# ── TechnicalLibrary class ────────────────────────────────────


class TechnicalLibrary:
    """Registry and search interface for the technical strategy template library."""

    def __init__(self, templates: dict[str, TechnicalTemplate]) -> None:
        self._templates = templates

    def list_all(self) -> list[TechnicalTemplate]:
        """Return all templates sorted by TECH_CATEGORIES order then name."""
        cat_order = {c: i for i, c in enumerate(TECH_CATEGORIES)}
        return sorted(
            self._templates.values(),
            key=lambda t: (cat_order.get(t.category, 99), t.name),
        )

    def list_by_category(self, category: str) -> list[TechnicalTemplate]:
        """Filter by category (case-insensitive). Raises ValueError for unknown categories."""
        cat = category.lower()
        if cat not in TECH_CATEGORIES:
            raise ValueError(f"Unknown category '{category}'. Valid: {', '.join(TECH_CATEGORIES)}")
        return [t for t in self.list_all() if t.category == cat]

    def get(self, id: str) -> TechnicalTemplate:
        """Exact-match lookup by id. Raises KeyError if not found."""
        if id not in self._templates:
            raise KeyError(
                f"Strategy '{id}' not found. Run 'strategy library --type technical' to see all."
            )
        return self._templates[id]

    def search(self, query: str) -> list[TechnicalTemplate]:
        """Case-insensitive search across id, name, tags, and explanation."""
        q = query.lower()
        results: list[tuple[int, TechnicalTemplate]] = []
        for t in self._templates.values():
            score = 0
            if q in t.id:
                score += 3
            if q in t.name.lower():
                score += 3
            if any(q in tag for tag in t.tags):
                score += 2
            if q in t.explanation.lower():
                score += 1
            if score > 0:
                results.append((score, t))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results]


# ── Module-level singleton ────────────────────────────────────

tech_library = TechnicalLibrary(TECH_TEMPLATES)
