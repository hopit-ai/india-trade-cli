"""
engine/strategy_library.py
──────────────────────────
Curated library of 26 well-known options strategies for Indian markets.

Each strategy is a StrategyTemplate — a data-driven, symbol-agnostic description
of a strategy's structure (legs, capital type, ideal conditions) plus educational
content (explanation, when to use, risks, tags).

Templates are resolved to live StrategyResult objects via apply_template(), which
takes real ATM market data and returns the same StrategyResult type that
engine/strategy.py produces — so all existing display code works unchanged.

Usage:
    from engine.strategy_library import strategy_library, apply_template

    template = strategy_library.get("iron_condor")
    result = apply_template(template, symbol="NIFTY", spot=24000, ...)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from engine.strategy import StrategyResult

try:
    from analysis.options import PayoffLeg, payoff as calc_payoff

    _PAYOFF_AVAILABLE = True
except Exception:
    _PAYOFF_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────

CATEGORIES = ("bullish", "bearish", "income", "volatility", "hedging")


# ── Dataclasses ───────────────────────────────────────────────


@dataclass
class TemplateLeg:
    """Abstract leg for a strategy template.

    strike_offset_pct is relative to spot:
      0.0   = ATM
     +0.03  = 3% OTM on the call side (strike above spot)
     -0.03  = 3% OTM on the put side (strike below spot)

    For STOCK legs, strike_offset_pct is unused (always purchased at spot).
    """

    option_type: str  # "CE" | "PE" | "STOCK"
    action: str  # "BUY" | "SELL"
    strike_offset_pct: float  # signed percentage of spot
    lots_multiplier: int = 1  # relative lot count (2 = double leg for ratio spreads)


@dataclass
class StrategyTemplate:
    """Metadata and educational content for a named options strategy."""

    id: str  # snake_case unique key
    name: str  # Display name
    category: str  # one of CATEGORIES
    views: list[str]  # e.g. ["BULLISH"] — views this strategy suits
    legs: list[TemplateLeg]  # abstract leg definitions
    max_profit: str  # human description, e.g. "Capped at spread width minus debit"
    max_loss: str  # e.g. "Net debit paid"
    ideal_iv: str  # "low" | "high" | "any"
    ideal_dte: tuple[int, int]  # (min_days, max_days)
    layman_explanation: str  # 1-2 sentences in plain language, zero jargon
    explanation: str  # 2-4 sentence technical description
    when_to_use: str  # 1-2 sentences
    when_not_to_use: str  # 1-2 sentences
    risks: list[str]  # bullet-point risks
    tags: list[str]  # searchable tags
    capital_type: str = "debit"  # "debit" | "credit" | "margin" | "stock"
    complexity: str = "beginner"  # "beginner" | "intermediate" | "advanced"


# ── Template definitions ──────────────────────────────────────

TEMPLATES: dict[str, StrategyTemplate] = {
    # ── BULLISH ───────────────────────────────────────────────
    "long_call": StrategyTemplate(
        id="long_call",
        name="Long Call",
        category="bullish",
        views=["BULLISH"],
        legs=[TemplateLeg("CE", "BUY", 0.0)],
        max_profit="Unlimited — profits as stock rises above breakeven",
        max_loss="Limited to premium paid",
        ideal_iv="low",
        ideal_dte=(7, 45),
        layman_explanation=(
            "You pay a small fee today for the right to buy a stock at today's price later. "
            "If the stock goes up, you profit. If it doesn't, you only lose the fee you paid — nothing more."
        ),
        explanation=(
            "Buy an ATM call option for the right to buy the underlying at the strike price. "
            "Profit is unlimited if the stock rises strongly; loss is capped at the premium paid. "
            "This is the simplest leveraged bullish trade with defined risk."
        ),
        when_to_use="Strong directional conviction; expecting a fast, large move before expiry.",
        when_not_to_use="When IV is elevated — you pay a high premium and need a larger move to profit.",
        risks=[
            "Full premium lost if stock does not move above breakeven by expiry",
            "Theta decay accelerates in the last 2 weeks — avoid holding too long",
            "High IV at entry makes breakeven very far from current price",
        ],
        tags=["directional", "debit", "unlimited_profit", "defined_risk", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "bull_call_spread": StrategyTemplate(
        id="bull_call_spread",
        name="Bull Call Spread",
        category="bullish",
        views=["BULLISH"],
        legs=[
            TemplateLeg("CE", "BUY", 0.0),
            TemplateLeg("CE", "SELL", 0.03),
        ],
        max_profit="Capped — spread width minus net debit, multiplied by lot size",
        max_loss="Net debit paid",
        ideal_iv="low",
        ideal_dte=(15, 45),
        layman_explanation=(
            "You bet the stock will rise, but only moderately. "
            "You buy one call and sell another at a higher price to cut your cost — "
            "your profit is capped, but so is what you can lose."
        ),
        explanation=(
            "Buy an ATM call and sell an OTM call at the same expiry. "
            "The short call reduces cost but caps your upside at the short strike. "
            "Ideal when you expect a moderate bullish move, not a parabolic rally."
        ),
        when_to_use="Moderately bullish; want to reduce premium outlay vs a naked long call.",
        when_not_to_use="When expecting a very large move — profits are capped at the short strike.",
        risks=[
            "Max profit capped if stock rallies past the short call strike",
            "Both legs lose value if stock falls — full debit at risk",
            "Wider spreads need more capital and a bigger move to profit",
        ],
        tags=["directional", "debit", "defined_risk", "spread", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "bull_put_spread": StrategyTemplate(
        id="bull_put_spread",
        name="Bull Put Spread",
        category="bullish",
        views=["BULLISH", "NEUTRAL"],
        legs=[
            TemplateLeg("PE", "SELL", -0.02),
            TemplateLeg("PE", "BUY", -0.05),
        ],
        max_profit="Net credit received",
        max_loss="Spread width minus net credit",
        ideal_iv="high",
        ideal_dte=(15, 45),
        layman_explanation=(
            "Someone pays you money now to bet the stock won't fall below a certain level. "
            "If you're right, you keep the cash. If you're wrong, your loss is capped."
        ),
        explanation=(
            "Sell an OTM put and buy a further OTM put for protection. "
            "You collect a net credit upfront; keep it all if the stock stays above the short put. "
            "This is a credit spread that profits from time decay and upward price action."
        ),
        when_to_use="Moderately bullish or neutral; high IV inflating put premiums.",
        when_not_to_use="When strongly bearish or expecting a sharp fall below the short put.",
        risks=[
            "Full spread-width loss if stock falls below the long put strike",
            "Margin required — can tie up capital even though loss is defined",
            "Profit capped at the initial credit — no upside beyond that",
        ],
        tags=["credit", "defined_risk", "spread", "theta", "intermediate"],
        capital_type="credit",
        complexity="intermediate",
    ),
    "synthetic_long": StrategyTemplate(
        id="synthetic_long",
        name="Synthetic Long",
        category="bullish",
        views=["BULLISH"],
        legs=[
            TemplateLeg("CE", "BUY", 0.0),
            TemplateLeg("PE", "SELL", 0.0),
        ],
        max_profit="Unlimited — mirrors stock ownership",
        max_loss="Effectively unlimited on the downside (put assignment risk)",
        ideal_iv="any",
        ideal_dte=(30, 90),
        layman_explanation=(
            "It acts just like owning the stock — rises and falls with it — "
            "but you only put up a fraction of the capital. "
            "The catch: if it falls, you lose just as much as if you owned the shares."
        ),
        explanation=(
            "Buy an ATM call and sell an ATM put at the same strike and expiry. "
            "The payoff mimics owning the stock — unlimited upside, full downside — "
            "but requires far less capital. Used by traders who want stock-like exposure "
            "without deploying full stock capital."
        ),
        when_to_use="Strong bullish conviction; want stock-like leverage with less capital outlay.",
        when_not_to_use="When uncertain — the put sale gives you unlimited downside, same as stock.",
        risks=[
            "Unlimited downside risk via short put assignment",
            "High margin required for the short put leg",
            "Early assignment risk if deep ITM near expiry",
        ],
        tags=["directional", "margin", "unlimited_risk", "leverage", "advanced"],
        capital_type="margin",
        complexity="advanced",
    ),
    "call_ratio_backspread": StrategyTemplate(
        id="call_ratio_backspread",
        name="Call Ratio Backspread",
        category="bullish",
        views=["BULLISH"],
        legs=[
            TemplateLeg("CE", "SELL", 0.0, lots_multiplier=1),
            TemplateLeg("CE", "BUY", 0.03, lots_multiplier=2),
        ],
        max_profit="Unlimited above the long strike; also profits if stock falls sharply",
        max_loss="Maximum loss between the two strikes near expiry",
        ideal_iv="low",
        ideal_dte=(15, 45),
        layman_explanation=(
            "You sell one expensive bet and use the money to buy two cheaper bets on a bigger move. "
            "You win big if the stock shoots up or crashes — "
            "but lose if it just drifts to a middle level."
        ),
        explanation=(
            "Sell 1 ATM call and buy 2 OTM calls. The position profits from a large rally "
            "or a sharp fall (if entered for a net credit). The loss zone is between the two strikes. "
            "Traders use this to get leveraged upside with a credit or near-zero cost."
        ),
        when_to_use="Expecting a large breakout up; also acceptable for a crash scenario.",
        when_not_to_use="When the stock is expected to stay range-bound — maximum loss occurs there.",
        risks=[
            "Maximum loss if stock pins between the short and long strikes at expiry",
            "Requires 2× the long legs — more commission",
            "Complex to manage and exit",
        ],
        tags=["directional", "ratio", "unlimited_profit", "advanced"],
        capital_type="credit",
        complexity="advanced",
    ),
    # ── BEARISH ───────────────────────────────────────────────
    "long_put": StrategyTemplate(
        id="long_put",
        name="Long Put",
        category="bearish",
        views=["BEARISH"],
        legs=[TemplateLeg("PE", "BUY", 0.0)],
        max_profit="Substantial — profits as stock falls below breakeven",
        max_loss="Limited to premium paid",
        ideal_iv="low",
        ideal_dte=(7, 45),
        layman_explanation=(
            "You pay a small fee to profit if the stock falls. "
            "Think of it as insurance that pays out when prices drop — "
            "if the stock rises instead, you only lose the fee."
        ),
        explanation=(
            "Buy an ATM put option for the right to sell the underlying at the strike. "
            "Profits grow as the stock falls; max loss is the premium paid if stock rises or stays flat. "
            "The mirror image of the long call for bearish directional trades."
        ),
        when_to_use="Strong bearish conviction; expecting a fast, meaningful decline before expiry.",
        when_not_to_use="When IV is high — premium is expensive and the stock must fall more to profit.",
        risks=[
            "Full premium lost if stock stays flat or rises",
            "Theta decay: put loses value every day if stock doesn't move",
            "Stock can only fall to zero — downside is capped unlike short stock",
        ],
        tags=["directional", "debit", "defined_risk", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "bear_put_spread": StrategyTemplate(
        id="bear_put_spread",
        name="Bear Put Spread",
        category="bearish",
        views=["BEARISH"],
        legs=[
            TemplateLeg("PE", "BUY", 0.0),
            TemplateLeg("PE", "SELL", -0.03),
        ],
        max_profit="Capped — spread width minus net debit",
        max_loss="Net debit paid",
        ideal_iv="low",
        ideal_dte=(15, 45),
        layman_explanation=(
            "You bet the stock will fall, but not by a lot. "
            "Buying one put and selling another cheaper one cuts your upfront cost — "
            "you give up some profit potential but pay less to enter."
        ),
        explanation=(
            "Buy an ATM put and sell an OTM put at the same expiry. "
            "Profits from a moderate decline; the short put caps the downside gain "
            "but meaningfully reduces the premium outlay vs a naked long put."
        ),
        when_to_use="Moderately bearish; want cheaper downside exposure than a naked put.",
        when_not_to_use="When expecting a crash — profits are capped at the short put strike.",
        risks=[
            "Max profit capped at the short put strike",
            "Full debit lost if stock rises or stays flat",
            "Needs the stock to fall at least to breakeven to profit",
        ],
        tags=["directional", "debit", "defined_risk", "spread", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "bear_call_spread": StrategyTemplate(
        id="bear_call_spread",
        name="Bear Call Spread",
        category="bearish",
        views=["BEARISH", "NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.02),
            TemplateLeg("CE", "BUY", 0.05),
        ],
        max_profit="Net credit received",
        max_loss="Spread width minus net credit",
        ideal_iv="high",
        ideal_dte=(15, 45),
        layman_explanation=(
            "Someone pays you money now to bet the stock won't rise above a certain level. "
            "If you're right, you keep the cash. If the stock surges past your limit, your loss is capped."
        ),
        explanation=(
            "Sell an OTM call and buy a further OTM call for protection. "
            "Collect a net credit; keep it if the stock stays below the short call. "
            "A credit spread that benefits from time decay and bearish or sideways price action."
        ),
        when_to_use="Moderately bearish or neutral; high IV inflating call premiums.",
        when_not_to_use="When strongly bullish — you have unlimited loss above the long call if not hedged.",
        risks=[
            "Full spread-width loss if stock rallies above the long call strike",
            "Requires margin for the short call",
            "Profit capped at the initial credit received",
        ],
        tags=["credit", "defined_risk", "spread", "theta", "intermediate"],
        capital_type="credit",
        complexity="intermediate",
    ),
    "synthetic_short": StrategyTemplate(
        id="synthetic_short",
        name="Synthetic Short",
        category="bearish",
        views=["BEARISH"],
        legs=[
            TemplateLeg("PE", "BUY", 0.0),
            TemplateLeg("CE", "SELL", 0.0),
        ],
        max_profit="Substantial — mirrors short stock downside",
        max_loss="Effectively unlimited on the upside (call assignment risk)",
        ideal_iv="any",
        ideal_dte=(30, 90),
        layman_explanation=(
            "It acts like short-selling the stock without actually borrowing shares — "
            "you profit as the price falls. "
            "But if the stock shoots up, you lose just as much as a short-seller would."
        ),
        explanation=(
            "Buy an ATM put and sell an ATM call at the same strike and expiry. "
            "The payoff mimics short-selling the stock without actually borrowing shares. "
            "Profits on a decline; exposed to unlimited loss if the stock rallies."
        ),
        when_to_use="Strong bearish conviction; want stock-short-like exposure without a margin account.",
        when_not_to_use="When uncertain — the short call carries unlimited upside risk.",
        risks=[
            "Unlimited upside risk via short call assignment",
            "Large margin requirement for the short call",
            "Early assignment risk near expiry",
        ],
        tags=["directional", "margin", "unlimited_risk", "leverage", "advanced"],
        capital_type="margin",
        complexity="advanced",
    ),
    "put_ratio_backspread": StrategyTemplate(
        id="put_ratio_backspread",
        name="Put Ratio Backspread",
        category="bearish",
        views=["BEARISH"],
        legs=[
            TemplateLeg("PE", "SELL", 0.0, lots_multiplier=1),
            TemplateLeg("PE", "BUY", -0.03, lots_multiplier=2),
        ],
        max_profit="Substantial below the long put strike; also profits on a sharp rally",
        max_loss="Maximum loss between the two strikes near expiry",
        ideal_iv="low",
        ideal_dte=(15, 45),
        layman_explanation=(
            "Same idea as the call ratio backspread but for a falling market — "
            "you sell one expensive put and buy two cheaper ones on a bigger drop. "
            "Win on a crash or a rally; lose if the stock lands in the middle."
        ),
        explanation=(
            "Sell 1 ATM put and buy 2 OTM puts. Profits from a large decline "
            "or a sharp rally (if entered for a net credit). Loss zone is between the two strikes. "
            "Mirror of the call ratio backspread for bearish directional bets."
        ),
        when_to_use="Expecting a large breakdown; also works for a crash hedge.",
        when_not_to_use="Range-bound markets — maximum loss occurs between the two strikes.",
        risks=[
            "Maximum loss if stock pins between short and long strikes at expiry",
            "2× the long legs means higher commissions",
            "Difficult to manage once in the loss zone",
        ],
        tags=["directional", "ratio", "advanced"],
        capital_type="credit",
        complexity="advanced",
    ),
    # ── INCOME ────────────────────────────────────────────────
    "iron_condor": StrategyTemplate(
        id="iron_condor",
        name="Iron Condor",
        category="income",
        views=["NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.03),
            TemplateLeg("CE", "BUY", 0.06),
            TemplateLeg("PE", "SELL", -0.03),
            TemplateLeg("PE", "BUY", -0.06),
        ],
        max_profit="Net credit received",
        max_loss="Wing width minus net credit (defined)",
        ideal_iv="high",
        ideal_dte=(20, 45),
        layman_explanation=(
            "You collect rent by betting the stock will stay parked between two price levels. "
            "As long as it doesn't go too high or too low by expiry, you keep all the money. "
            "Think of it as drawing a profit box around the current price."
        ),
        explanation=(
            "Sell an OTM call spread and an OTM put spread simultaneously. "
            "Profits if the underlying stays between the two short strikes through expiry. "
            "The net credit received is the maximum profit; the wing width limits the loss."
        ),
        when_to_use="After an IV spike when you expect range-bound action; high VIX environment.",
        when_not_to_use="When a strong directional catalyst is pending or IV is already low.",
        risks=[
            "Full wing-width loss if price breaks out of the profit zone",
            "Requires four legs — higher transaction costs",
            "Assignment risk if a short leg goes deep ITM near expiry",
        ],
        tags=[
            "neutral",
            "income",
            "defined_risk",
            "credit",
            "high_iv",
            "four_legs",
            "intermediate",
        ],
        capital_type="credit",
        complexity="intermediate",
    ),
    "iron_butterfly": StrategyTemplate(
        id="iron_butterfly",
        name="Iron Butterfly",
        category="income",
        views=["NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.0),
            TemplateLeg("CE", "BUY", 0.04),
            TemplateLeg("PE", "SELL", 0.0),
            TemplateLeg("PE", "BUY", -0.04),
        ],
        max_profit="Net credit received (both short legs at ATM)",
        max_loss="Wing width minus net credit",
        ideal_iv="high",
        ideal_dte=(15, 30),
        layman_explanation=(
            "Like an iron condor but with a tighter profit zone right at the current price. "
            "You collect more cash upfront, but the stock needs to land almost exactly where it is now for you to keep it."
        ),
        explanation=(
            "Sell ATM call and put (straddle) and buy OTM wings for protection. "
            "Higher credit than an iron condor because the short strikes are ATM, "
            "but the profit zone is narrower — stock must pin near the short strikes."
        ),
        when_to_use="Very high IV around a specific price level; expecting a pin at expiry.",
        when_not_to_use="When any meaningful move is expected — profit zone is tight.",
        risks=[
            "Profit zone is very narrow; any significant move causes a loss",
            "ATM short strikes have high gamma risk near expiry",
            "More expensive to close early due to wide bid-ask on 4 legs",
        ],
        tags=["neutral", "income", "credit", "high_iv", "four_legs", "intermediate"],
        capital_type="credit",
        complexity="intermediate",
    ),
    "short_straddle": StrategyTemplate(
        id="short_straddle",
        name="Short Straddle",
        category="income",
        views=["NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.0),
            TemplateLeg("PE", "SELL", 0.0),
        ],
        max_profit="Net credit (both ATM premiums)",
        max_loss="Unlimited in either direction",
        ideal_iv="high",
        ideal_dte=(15, 30),
        layman_explanation=(
            "You collect rent from both the bulls and the bears, betting the stock goes nowhere. "
            "Great income if the stock stays flat — but if it makes a big move either way, your losses are unlimited."
        ),
        explanation=(
            "Sell an ATM call and an ATM put at the same strike and expiry. "
            "You collect the combined premium; the stock must stay near the strike to profit. "
            "This is the highest-credit income strategy but carries unlimited risk on both sides."
        ),
        when_to_use="Extreme IV crush expected (post-earnings, post-event); very high VIX.",
        when_not_to_use="When any directional move is expected — losses are unlimited.",
        risks=[
            "Unlimited loss if stock makes a large move in either direction",
            "High margin requirement — broker may require 15-20% of notional",
            "Gamma risk is severe in the last week before expiry",
        ],
        tags=["neutral", "income", "margin", "unlimited_risk", "high_iv", "advanced"],
        capital_type="margin",
        complexity="advanced",
    ),
    "short_strangle": StrategyTemplate(
        id="short_strangle",
        name="Short Strangle",
        category="income",
        views=["NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.03),
            TemplateLeg("PE", "SELL", -0.03),
        ],
        max_profit="Net credit (both OTM premiums)",
        max_loss="Unlimited in either direction",
        ideal_iv="high",
        ideal_dte=(15, 30),
        layman_explanation=(
            "A roomier version of the short straddle — you give the stock more space to wander "
            "before it hurts you, but you collect less cash. Still unlimited loss if it moves big."
        ),
        explanation=(
            "Sell an OTM call and an OTM put at the same expiry. "
            "The profit zone is wider than a short straddle (between the two short strikes) "
            "but the credit collected is smaller. Still carries unlimited risk on both sides."
        ),
        when_to_use="Expecting range-bound action after high-IV event; wider comfort zone than straddle.",
        when_not_to_use="When any large directional move is possible — unlimited loss potential.",
        risks=[
            "Unlimited loss outside the short strikes",
            "Requires large margin",
            "One losing leg can exceed many months of premium income",
        ],
        tags=["neutral", "income", "margin", "unlimited_risk", "high_iv", "advanced"],
        capital_type="margin",
        complexity="advanced",
    ),
    "covered_call": StrategyTemplate(
        id="covered_call",
        name="Covered Call",
        category="income",
        views=["NEUTRAL", "BULLISH"],
        legs=[
            TemplateLeg("STOCK", "BUY", 0.0),
            TemplateLeg("CE", "SELL", 0.03),
        ],
        max_profit="Capped — (short call strike - stock buy price + premium received)",
        max_loss="Stock falls to zero minus premium received",
        ideal_iv="any",
        ideal_dte=(20, 45),
        layman_explanation=(
            "You own a stock and charge someone a fee for the option to buy it from you at a higher price. "
            "You earn extra income every month — but if the stock rockets, they take your shares at the agreed price."
        ),
        explanation=(
            "Own the stock and sell an OTM call against it each month. "
            "The premium reduces your cost basis and provides income; "
            "the call caps your upside if the stock rallies past the strike. "
            "Best suited for stocks you plan to hold long-term."
        ),
        when_to_use="Already own shares; want to generate monthly income and are willing to sell if called.",
        when_not_to_use="When expecting a large rally — the call caps your gains.",
        risks=[
            "Stock position still has full downside (premium provides only small buffer)",
            "Opportunity cost if stock surges past the short strike",
            "Tax implications of stock assignment",
        ],
        tags=["income", "stock", "theta", "beginner"],
        capital_type="stock",
        complexity="beginner",
    ),
    "cash_secured_put": StrategyTemplate(
        id="cash_secured_put",
        name="Cash-Secured Put",
        category="income",
        views=["NEUTRAL", "BULLISH"],
        legs=[TemplateLeg("PE", "SELL", -0.03)],
        max_profit="Net premium received",
        max_loss="Short put strike minus premium (stock falls to zero)",
        ideal_iv="any",
        ideal_dte=(20, 45),
        layman_explanation=(
            "You tell the market: 'I'm happy to buy this stock if it falls to ₹X — pay me now for that promise.' "
            "You earn cash upfront. If the stock stays above ₹X, you keep the cash and do it again next month."
        ),
        explanation=(
            "Sell an OTM put and set aside the capital to buy the shares if assigned. "
            "You earn the premium and may acquire the stock at a price you are happy to own it. "
            "If the stock stays above the strike, you keep the premium and repeat."
        ),
        when_to_use="Willing to buy a stock at a lower price; want to earn income while waiting.",
        when_not_to_use="When you would not actually want to own the stock at the strike price.",
        risks=[
            "Obligated to buy shares at strike even if stock keeps falling",
            "Premium earned may not cover a large price decline",
            "Capital is tied up as margin/collateral",
        ],
        tags=["income", "margin", "theta", "beginner"],
        capital_type="margin",
        complexity="beginner",
    ),
    "jade_lizard": StrategyTemplate(
        id="jade_lizard",
        name="Jade Lizard",
        category="income",
        views=["NEUTRAL", "BULLISH"],
        legs=[
            TemplateLeg("CE", "SELL", 0.03),
            TemplateLeg("PE", "SELL", -0.03),
            TemplateLeg("PE", "BUY", -0.06),
        ],
        max_profit="Net credit received (no upside risk if credit > call strike distance)",
        max_loss="Put spread width minus total credit (downside risk only)",
        ideal_iv="high",
        ideal_dte=(20, 40),
        layman_explanation=(
            "You collect rent from three bets at once and engineer it so there's no way to lose if the stock rises. "
            "The only way you lose is if the stock falls hard — and even that loss is capped."
        ),
        explanation=(
            "Sell an OTM call, sell an OTM put, and buy a further OTM put for protection. "
            "The total credit exceeds the call strike distance, eliminating upside risk. "
            "All risk is on the downside, limited to the put spread width minus the credit received."
        ),
        when_to_use="Bullish to neutral; high IV; want no upside risk and defined downside.",
        when_not_to_use="Bearish outlook — all risk is on the downside put spread.",
        risks=[
            "Put spread width loss if stock falls sharply",
            "Short call can still lose if stock rallies but credit is insufficient",
            "Three legs require more commission and management",
        ],
        tags=["income", "credit", "high_iv", "defined_risk", "advanced"],
        capital_type="credit",
        complexity="advanced",
    ),
    # ── VOLATILITY ────────────────────────────────────────────
    "long_straddle": StrategyTemplate(
        id="long_straddle",
        name="Long Straddle",
        category="volatility",
        views=["BULLISH", "BEARISH"],
        legs=[
            TemplateLeg("CE", "BUY", 0.0),
            TemplateLeg("PE", "BUY", 0.0),
        ],
        max_profit="Unlimited in either direction",
        max_loss="Total premium paid for both legs",
        ideal_iv="low",
        ideal_dte=(15, 60),
        layman_explanation=(
            "You don't know which way the stock will move, but you're sure it'll move a lot. "
            "So you buy both a 'goes up' bet and a 'goes down' bet — "
            "whichever direction it explodes in, you win."
        ),
        explanation=(
            "Buy an ATM call and an ATM put at the same strike and expiry. "
            "Profits from a large move in either direction; the exact direction does not matter. "
            "Best entered when IV is low and a big event (earnings, RBI, budget) is upcoming."
        ),
        when_to_use="Large move expected but direction uncertain; IV is low before a known catalyst.",
        when_not_to_use="When IV is already high — you pay a large premium and need an even bigger move.",
        risks=[
            "Full combined premium lost if stock stays near the strike",
            "IV crush after the event can wipe out gains even if the stock moves",
            "Expensive — both legs are ATM so total premium is high",
        ],
        tags=["volatility", "debit", "unlimited_profit", "event_driven", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "long_strangle": StrategyTemplate(
        id="long_strangle",
        name="Long Strangle",
        category="volatility",
        views=["BULLISH", "BEARISH"],
        legs=[
            TemplateLeg("CE", "BUY", 0.03),
            TemplateLeg("PE", "BUY", -0.03),
        ],
        max_profit="Unlimited in either direction beyond the breakevens",
        max_loss="Total premium paid (less than straddle)",
        ideal_iv="low",
        ideal_dte=(15, 60),
        layman_explanation=(
            "Same idea as a straddle — bet on a big move in either direction — "
            "but cheaper because you buy slightly out-of-the-money bets. "
            "The trade-off: the stock needs to move even more before you start making money."
        ),
        explanation=(
            "Buy an OTM call and an OTM put at the same expiry. "
            "Cheaper than a straddle because both legs are OTM; "
            "however, the stock needs to move more to profit. "
            "Suits traders who want volatility exposure with a lower absolute cost."
        ),
        when_to_use="Large move expected; want lower premium cost than a straddle.",
        when_not_to_use="Slow-moving markets — the required move to breakeven is larger than a straddle.",
        risks=[
            "Needs a bigger move than a straddle to start profiting",
            "Both legs can expire worthless if the stock stays range-bound",
            "IV crush after events can hurt even if the stock moves",
        ],
        tags=["volatility", "debit", "event_driven", "beginner"],
        capital_type="debit",
        complexity="beginner",
    ),
    "long_calendar_spread": StrategyTemplate(
        id="long_calendar_spread",
        name="Long Calendar Spread",
        category="volatility",
        views=["NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.0),  # near-term expiry (shorter)
            TemplateLeg("CE", "BUY", 0.0),  # far-term expiry (longer)
        ],
        max_profit="Near-term premium captured as near leg decays; far leg retains value",
        max_loss="Net debit paid (far premium minus near premium received)",
        ideal_iv="any",
        ideal_dte=(15, 45),
        layman_explanation=(
            "You rent out a short-term bet to someone while holding a longer-term one yourself. "
            "The short-term rent expires and loses value faster — you pocket that difference. "
            "Works best if the stock stays near its current price in the short run."
        ),
        explanation=(
            "Sell a near-term ATM call and buy a longer-term ATM call at the same strike. "
            "The near-term leg decays faster; you profit from the difference in theta decay rates. "
            "Note: this template approximates both legs at the same expiry for display purposes — "
            "in practice the two legs have different expiry dates."
        ),
        when_to_use="Expecting stock to stay near the strike in the near term but move later.",
        when_not_to_use="When a large near-term move is expected — the short near-term call is exposed.",
        risks=[
            "Large near-term move causes the short leg to lose faster than the long leg gains",
            "IV differential risk — if near-term IV rises more than far-term IV",
            "Requires rolling the near leg at expiry if position is to continue",
        ],
        tags=["volatility", "debit", "theta", "calendar", "intermediate"],
        capital_type="debit",
        complexity="intermediate",
    ),
    "diagonal_spread": StrategyTemplate(
        id="diagonal_spread",
        name="Diagonal Spread",
        category="volatility",
        views=["BULLISH", "NEUTRAL"],
        legs=[
            TemplateLeg("CE", "SELL", 0.02),  # near-term slightly OTM
            TemplateLeg("CE", "BUY", 0.0),  # far-term ATM
        ],
        max_profit="Near-term credit plus intrinsic value of far leg if stock rises moderately",
        max_loss="Net debit paid (far premium minus near credit received)",
        ideal_iv="any",
        ideal_dte=(20, 60),
        layman_explanation=(
            "You buy a long-term bullish bet and partially fund it by selling a short-term, smaller bet. "
            "You stay bullish overall while collecting near-term rent to reduce your cost."
        ),
        explanation=(
            "Sell a near-term OTM call and buy a far-term ATM call — different strikes and expiries. "
            "Combines the theta benefit of the short near leg with the directional benefit of the long far leg. "
            "This is a hybrid between a covered call and a calendar spread."
        ),
        when_to_use="Mildly bullish; want to reduce far-leg cost by selling near-term premium.",
        when_not_to_use="When expecting a fast, large move — the short near call caps immediate gains.",
        risks=[
            "Short near call can be challenged if stock rallies quickly",
            "Complex to manage — two different expiry dates",
            "Vega sensitivity differs between the two legs",
        ],
        tags=["volatility", "debit", "calendar", "theta", "advanced"],
        capital_type="debit",
        complexity="advanced",
    ),
    # ── HEDGING ───────────────────────────────────────────────
    "protective_put": StrategyTemplate(
        id="protective_put",
        name="Protective Put",
        category="hedging",
        views=["BULLISH"],
        legs=[
            TemplateLeg("STOCK", "BUY", 0.0),
            TemplateLeg("PE", "BUY", -0.02),
        ],
        max_profit="Unlimited — stock upside minus put premium cost",
        max_loss="(Stock price - put strike + put premium) per share × lot size",
        ideal_iv="any",
        ideal_dte=(30, 90),
        layman_explanation=(
            "You own a stock and buy insurance against it falling. "
            "Like car insurance — you pay a premium, and if something bad happens (a big drop), the policy pays out. "
            "Your upside is still unlimited; your downside is capped."
        ),
        explanation=(
            "Own the stock and buy a slightly OTM put as insurance. "
            "If the stock falls, the put gains value and limits your downside. "
            "If the stock rises, you keep the full upside minus the put premium paid."
        ),
        when_to_use="Already own the stock and want downside protection before a risky event.",
        when_not_to_use="When the cost of protection (put premium) is too high relative to position size.",
        risks=[
            "Put premium is a recurring cost — erodes returns if paid every month",
            "If stock stays flat, you lose the premium repeatedly",
            "High IV makes protective puts expensive",
        ],
        tags=["hedging", "debit", "defined_risk", "stock", "insurance", "beginner"],
        capital_type="stock",
        complexity="beginner",
    ),
    "collar": StrategyTemplate(
        id="collar",
        name="Collar",
        category="hedging",
        views=["NEUTRAL", "BULLISH"],
        legs=[
            TemplateLeg("STOCK", "BUY", 0.0),
            TemplateLeg("PE", "BUY", -0.05),
            TemplateLeg("CE", "SELL", 0.05),
        ],
        max_profit="Capped — (short call strike - stock price + net option credit/debit)",
        max_loss="(Stock price - long put strike + net option debit) — defined",
        ideal_iv="any",
        ideal_dte=(30, 90),
        layman_explanation=(
            "You put a safety floor under your stock and fund it by agreeing to sell at a ceiling price. "
            "Your loss is limited and the hedge is often free — but you give up gains above the ceiling."
        ),
        explanation=(
            "Own the stock, buy a downside put for protection, and sell an upside call to fund the put. "
            "The sold call partially or fully offsets the cost of the protective put. "
            "Both upside and downside are bounded — this is a zero-cost or near-zero-cost hedge."
        ),
        when_to_use="Holding a large stock position; want cheap or free downside protection.",
        when_not_to_use="When expecting a strong rally — the short call caps your upside.",
        risks=[
            "Upside capped at the short call strike",
            "Still exposed to downside between stock price and put strike",
            "Tax implications if short call is assigned",
        ],
        tags=["hedging", "stock", "defined_risk", "zero_cost", "intermediate"],
        capital_type="stock",
        complexity="intermediate",
    ),
    "married_put": StrategyTemplate(
        id="married_put",
        name="Married Put",
        category="hedging",
        views=["BULLISH"],
        legs=[
            TemplateLeg("STOCK", "BUY", 0.0),
            TemplateLeg("PE", "BUY", 0.0),
        ],
        max_profit="Unlimited — stock upside minus ATM put premium",
        max_loss="Put premium paid (stock is protected at ATM strike)",
        ideal_iv="any",
        ideal_dte=(30, 60),
        layman_explanation=(
            "You buy a stock and full insurance at the same time. "
            "If the stock crashes to zero, your insurance policy pays out dollar-for-dollar — "
            "the most you can ever lose is the insurance premium."
        ),
        explanation=(
            "Buy the stock and simultaneously buy an ATM put. "
            "The put fully protects the position — if the stock falls, the put gains dollar-for-dollar. "
            "Maximum loss is just the put premium. Effectively a call option on the stock."
        ),
        when_to_use="Initiating a new stock position with full downside protection from day one.",
        when_not_to_use="When protection cost is high — ATM puts are expensive and eat into returns.",
        risks=[
            "ATM put premium is substantial — expensive insurance",
            "Stock must rise more than the put premium to be profitable",
            "If stock stays flat, put expires worthless and you lose the premium",
        ],
        tags=["hedging", "stock", "defined_risk", "insurance", "beginner"],
        capital_type="stock",
        complexity="beginner",
    ),
    "seagull": StrategyTemplate(
        id="seagull",
        name="Seagull Spread",
        category="hedging",
        views=["NEUTRAL", "BULLISH"],
        legs=[
            TemplateLeg("PE", "BUY", -0.03),
            TemplateLeg("PE", "SELL", -0.06),
            TemplateLeg("CE", "SELL", 0.05),
        ],
        max_profit="Net credit or near-zero cost; profits if stock holds or rises moderately",
        max_loss="Put spread width minus total net credit received — defined downside",
        ideal_iv="high",
        ideal_dte=(30, 90),
        layman_explanation=(
            "You build a cheap safety net under your portfolio by selling two different bets to fund it. "
            "Often costs nothing or pays you a small credit — you're hedged below and capped above."
        ),
        explanation=(
            "Buy an OTM put, sell a further OTM put, and sell an OTM call. "
            "The put spread provides cheap downside protection; the short call funds it. "
            "The three-way structure typically costs near-zero or generates a small credit, "
            "making it popular for cost-efficient portfolio hedging."
        ),
        when_to_use="Want cheap downside protection on a stock you own; high IV reduces cost further.",
        when_not_to_use="When expecting a large upside rally — the short call caps gains significantly.",
        risks=[
            "Short call caps upside beyond the call strike",
            "Still exposed below the short put strike (put spread does not protect fully)",
            "Three legs require more commission and careful management",
        ],
        tags=["hedging", "credit", "defined_risk", "three_legs", "intermediate"],
        capital_type="credit",
        complexity="intermediate",
    ),
    "long_fence": StrategyTemplate(
        id="long_fence",
        name="Long Fence",
        category="hedging",
        views=["NEUTRAL", "BULLISH"],
        legs=[
            TemplateLeg("PE", "BUY", -0.03),
            TemplateLeg("CE", "SELL", 0.05),
        ],
        max_profit="Capped at the short call strike — profitable if stock stays in range or rises to call",
        max_loss="(Stock price - put strike - net credit) if stock falls below put",
        ideal_iv="any",
        ideal_dte=(30, 60),
        layman_explanation=(
            "You buy cheap downside insurance and let someone else pay for it by giving up your upside. "
            "It's like getting free flood insurance on your house by agreeing to sell it below market if prices rise."
        ),
        explanation=(
            "Buy a slightly OTM put and sell a further OTM call (no stock position). "
            "The short call funds the put and provides a net credit or near-zero cost hedge. "
            "Used as a standalone position or to hedge an existing stock holding cheaply."
        ),
        when_to_use="Cheap downside protection when you don't want to pay full put premium.",
        when_not_to_use="When expecting a big rally — the short call caps gains significantly.",
        risks=[
            "Upside capped by the short call",
            "Still exposed below the put strike (downside not fully protected)",
            "Short call carries assignment risk if stock rallies sharply",
        ],
        tags=["hedging", "credit", "defined_risk", "intermediate"],
        capital_type="credit",
        complexity="intermediate",
    ),
}


# ── StrategyLibrary class ─────────────────────────────────────


class StrategyLibrary:
    """Registry and search interface for the options strategy template library."""

    def __init__(self, templates: dict[str, StrategyTemplate]) -> None:
        self._templates = templates

    def list_all(self) -> list[StrategyTemplate]:
        """Return all templates sorted by category (CATEGORIES order) then name."""
        cat_order = {c: i for i, c in enumerate(CATEGORIES)}
        return sorted(
            self._templates.values(),
            key=lambda t: (cat_order.get(t.category, 99), t.name),
        )

    def list_by_category(self, category: str) -> list[StrategyTemplate]:
        """Filter by category (case-insensitive). Raises ValueError for unknown categories."""
        cat = category.lower()
        if cat not in CATEGORIES:
            raise ValueError(
                f"Unknown category '{category}'. Valid categories: {', '.join(CATEGORIES)}"
            )
        return [t for t in self.list_all() if t.category == cat]

    def get(self, id: str) -> StrategyTemplate:
        """Exact-match lookup by id. Raises KeyError if not found."""
        if id not in self._templates:
            raise KeyError(
                f"Strategy '{id}' not found. Run 'strategy library' to see all available strategies."
            )
        return self._templates[id]

    def search(self, query: str) -> list[StrategyTemplate]:
        """
        Case-insensitive search across id, name, tags, views, and explanation.
        Returns list sorted by relevance (name/id matches rank highest).
        """
        q = query.lower()
        results: list[tuple[int, StrategyTemplate]] = []
        for t in self._templates.values():
            score = 0
            if q in t.id:
                score += 3
            if q in t.name.lower():
                score += 3
            if any(q in tag for tag in t.tags):
                score += 2
            if any(q in v.lower() for v in t.views):
                score += 1
            if q in t.explanation.lower():
                score += 1
            if score > 0:
                results.append((score, t))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results]


# ── Module-level singleton ────────────────────────────────────

strategy_library = StrategyLibrary(TEMPLATES)


# ── Premium resolution helpers ────────────────────────────────


def _resolve_premium(
    leg: TemplateLeg,
    atm_ce_prem: float,
    atm_pe_prem: float,
) -> float:
    """
    Estimate the premium for a leg given ATM premiums.

    Uses exponential moneyness decay consistent with market behaviour:
    - k=10 gives ~74% of ATM at 3% OTM, ~55% at 6% OTM.
    - ITM options are scaled up proportionally.
    """
    if leg.option_type == "STOCK":
        return 0.0

    offset = leg.strike_offset_pct
    abs_offset = abs(offset)

    if leg.option_type == "CE":
        base = atm_ce_prem
        if offset > 0:
            # OTM call — apply decay
            resolved = base * math.exp(-10 * abs_offset)
        elif offset < 0:
            # ITM call — premium increases
            resolved = base * (1 + abs_offset * 3)
        else:
            resolved = base
    else:  # PE
        base = atm_pe_prem
        if offset < 0:
            # OTM put — apply decay
            resolved = base * math.exp(-10 * abs_offset)
        elif offset > 0:
            # ITM put — premium increases
            resolved = base * (1 + abs_offset * 3)
        else:
            resolved = base

    return max(1.0, round(resolved, 2))


def _resolve_strike(atm_strike: float, spot: float, leg: TemplateLeg) -> float:
    """Resolve the absolute strike for a template leg."""
    if leg.option_type == "STOCK":
        return spot
    raw = atm_strike + spot * leg.strike_offset_pct
    return round(raw / 100) * 100  # round to nearest 100 (Indian index strikes)


def _fit_score(template: StrategyTemplate, dte: int) -> int:
    """
    Score 0–100 how well the given DTE fits the template's ideal range.
    80 = within range, 60 = within 50% of range, 40 = well outside.
    """
    lo, hi = template.ideal_dte
    if lo <= dte <= hi:
        return 80
    margin = (hi - lo) * 0.5
    if (lo - margin) <= dte <= (hi + margin):
        return 60
    return 40


def _build_description(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],  # (leg, strike, premium)
    symbol: str,
) -> str:
    """One-line description: 'Buy 24000CE @ ₹150 + Sell 25000CE @ ₹55'."""
    parts = []
    for leg, strike, premium in resolved:
        if leg.option_type == "STOCK":
            parts.append(f"{leg.action} {symbol} stock @ ₹{strike:,.0f}")
        else:
            multiplier = f"×{leg.lots_multiplier} " if leg.lots_multiplier > 1 else ""
            parts.append(f"{leg.action} {multiplier}{strike:.0f}{leg.option_type} @ ₹{premium:.0f}")
    return " + ".join(parts)


def _build_legs_dicts(
    resolved: list[tuple[TemplateLeg, float, float]],
    lots: int,
) -> list[dict]:
    """Build leg dicts in the same format as engine/strategy.py."""
    legs = []
    for leg, strike, premium in resolved:
        d: dict = {
            "action": leg.action,
            "type": leg.option_type,
            "strike": strike,
            "lots": lots * leg.lots_multiplier,
        }
        if leg.option_type != "STOCK":
            d["premium"] = premium
        legs.append(d)
    return legs


# ── apply_template() ──────────────────────────────────────────


def apply_template(
    template: StrategyTemplate,
    symbol: str,
    spot: float,
    atm_ce_prem: float,
    atm_pe_prem: float,
    atm_strike: float,
    lot_size: int,
    lots: int = 1,
    dte: int = 30,
) -> StrategyResult:
    """
    Resolve a StrategyTemplate with live market data and return a StrategyResult.

    Args:
        template:     The template to apply
        symbol:       NSE symbol (e.g. "NIFTY")
        spot:         Current spot price
        atm_ce_prem:  ATM call premium
        atm_pe_prem:  ATM put premium
        atm_strike:   ATM strike price
        lot_size:     Lot size for this symbol
        lots:         Number of lots to trade (default 1)
        dte:          Days to expiry (default 30)

    Returns:
        StrategyResult compatible with engine/strategy.py output format.
    """
    # Step 1: resolve each leg to (leg, strike, premium)
    resolved: list[tuple[TemplateLeg, float, float]] = []
    for leg in template.legs:
        strike = _resolve_strike(atm_strike, spot, leg)
        premium = _resolve_premium(leg, atm_ce_prem, atm_pe_prem)
        resolved.append((leg, strike, premium))

    unit = lot_size * lots  # total contracts in one lot-set

    # Step 2: compute P&L metrics by capital_type
    capital_needed, max_profit, max_loss, breakeven = _compute_pnl(
        template, resolved, spot, atm_strike, unit
    )

    # Step 3: build payoff chart (options legs only)
    pf = None
    if _PAYOFF_AVAILABLE:
        try:
            payoff_legs = []
            for leg, strike, premium in resolved:
                if leg.option_type == "STOCK":
                    continue
                payoff_legs.append(
                    PayoffLeg(
                        option_type=leg.option_type,
                        transaction=leg.action,
                        strike=strike,
                        premium=premium,
                        lot_size=lot_size,
                        lots=lots * leg.lots_multiplier,
                    )
                )
            if payoff_legs:
                pf = calc_payoff(payoff_legs, (spot * 0.80, spot * 1.20))
        except Exception:
            pf = None

    # Step 4: assemble StrategyResult
    rr = 0.0
    if max_loss and max_loss != float("-inf") and max_profit and max_profit != float("inf"):
        rr = round(abs(max_profit / max_loss), 2) if max_loss != 0 else 0.0

    return StrategyResult(
        name=template.name,
        description=_build_description(template, resolved, symbol),
        legs=_build_legs_dicts(resolved, lots),
        capital_needed=round(capital_needed, 2),
        max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2),
        breakeven=breakeven,
        rr_ratio=rr,
        fit_score=_fit_score(template, dte),
        best_for=template.when_to_use,
        risks="; ".join(template.risks[:2]),
        payoff=pf,
    )


def _compute_pnl(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],
    spot: float,
    atm_strike: float,
    unit: int,
) -> tuple[float, float, float, list[float]]:
    """
    Compute (capital_needed, max_profit, max_loss, breakeven) for a template.

    Dispatches on template.capital_type for the appropriate formula.
    Returns approximate values for complex multi-expiry structures.
    """
    # Helpers
    buy_prems = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type != "STOCK"
    ]
    sell_prems = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type != "STOCK"
    ]
    stock_legs = [(leg, s, p) for leg, s, p in resolved if leg.option_type == "STOCK"]

    total_buy = sum(p * leg.lots_multiplier for leg, _, p in buy_prems)
    total_sell = sum(p * leg.lots_multiplier for leg, _, p in sell_prems)
    net_debit = total_buy - total_sell
    net_credit = total_sell - total_buy

    cap_type = template.capital_type

    if cap_type == "debit" and not stock_legs:
        return _pnl_debit(template, resolved, net_debit, unit, atm_strike)

    if cap_type == "credit" and not stock_legs:
        return _pnl_credit(template, resolved, net_credit, net_debit, unit, atm_strike, spot)

    if cap_type == "margin" and not stock_legs:
        return _pnl_margin(template, resolved, net_credit, unit, spot)

    if cap_type in ("stock", "debit", "credit") and stock_legs:
        return _pnl_stock(template, resolved, net_credit, net_debit, unit, spot)

    # Fallback: generic debit
    capital = abs(net_debit) * unit
    return capital, capital * 2, -capital, [atm_strike + net_debit]


def _pnl_debit(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],
    net_debit: float,
    unit: int,
    atm_strike: float,
) -> tuple[float, float, float, list[float]]:
    """P&L for pure debit strategies (long call, bear put spread, straddle, etc.)."""
    capital = net_debit * unit
    max_loss = -capital

    legs_list = resolved
    buy_ce = [
        (leg, s, p) for leg, s, p in legs_list if leg.action == "BUY" and leg.option_type == "CE"
    ]
    buy_pe = [
        (leg, s, p) for leg, s, p in legs_list if leg.action == "BUY" and leg.option_type == "PE"
    ]
    sell_ce = [
        (leg, s, p) for leg, s, p in legs_list if leg.action == "SELL" and leg.option_type == "CE"
    ]
    sell_pe = [
        (leg, s, p) for leg, s, p in legs_list if leg.action == "SELL" and leg.option_type == "PE"
    ]

    has_ce = bool(buy_ce)
    has_pe = bool(buy_pe)
    has_short_ce = bool(sell_ce)
    has_short_pe = bool(sell_pe)

    if has_ce and has_pe and not has_short_ce and not has_short_pe:
        # Straddle / strangle — two breakevens
        ce_strike = buy_ce[0][1]
        pe_strike = buy_pe[0][1]
        be_up = ce_strike + net_debit
        be_dn = pe_strike - net_debit
        max_profit = unit * (atm_strike * 0.25)  # large representative value
        return capital, round(max_profit, 2), max_loss, sorted([round(be_dn, 2), round(be_up, 2)])

    if has_ce and has_short_ce:
        # Bull call spread / calendar
        long_strike = buy_ce[0][1]
        short_strike = sell_ce[0][1]
        spread_width = abs(short_strike - long_strike)
        if spread_width == 0:
            # Calendar — same strike, approximate
            max_profit = buy_ce[0][2] * unit * 0.5  # near leg premium capture estimate
        else:
            max_profit = (spread_width - net_debit) * unit
        be = round(long_strike + net_debit, 2)
        return capital, round(max_profit, 2), max_loss, [be]

    if has_pe and has_short_pe:
        # Bear put spread
        long_strike = buy_pe[0][1]
        short_strike = sell_pe[0][1]
        spread_width = abs(long_strike - short_strike)
        max_profit = (spread_width - net_debit) * unit
        be = round(long_strike - net_debit, 2)
        return capital, round(max_profit, 2), max_loss, [be]

    if has_ce and not has_short_ce:
        # Naked long call
        ce_strike = buy_ce[0][1]
        prem = buy_ce[0][2]
        be = round(ce_strike + prem, 2)
        max_profit = unit * ce_strike * 0.20  # representative uncapped value
        return capital, round(max_profit, 2), max_loss, [be]

    if has_pe and not has_short_pe:
        # Naked long put
        pe_strike = buy_pe[0][1]
        prem = buy_pe[0][2]
        be = round(pe_strike - prem, 2)
        max_profit = unit * pe_strike * 0.20  # representative value
        return capital, round(max_profit, 2), max_loss, [be]

    # Fallback
    return capital, capital * 2.0, max_loss, [atm_strike]


def _pnl_credit(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],
    net_credit: float,
    net_debit: float,
    unit: int,
    atm_strike: float,
    spot: float,
) -> tuple[float, float, float, list[float]]:
    """P&L for credit strategies (spreads, iron condor, jade lizard, ratio backspreads)."""
    sell_ce = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type == "CE"
    ]
    buy_ce = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type == "CE"
    ]
    sell_pe = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type == "PE"
    ]
    buy_pe = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type == "PE"
    ]

    is_iron = bool(sell_ce and buy_ce and sell_pe and buy_pe)
    is_call_spread = bool(sell_ce and buy_ce and not sell_pe and not buy_pe)
    is_put_spread = bool(sell_pe and buy_pe and not sell_ce and not buy_ce)
    is_ratio = any(leg.lots_multiplier > 1 for leg, _, _ in resolved)

    if is_iron:
        call_width = abs(buy_ce[0][1] - sell_ce[0][1])
        put_width = abs(buy_pe[0][1] - sell_pe[0][1])
        wing = max(call_width, put_width)
        max_profit = net_credit * unit
        capital = (wing - net_credit) * unit
        max_loss = -(wing - net_credit) * unit
        be_up = round(sell_ce[0][1] + net_credit, 2)
        be_dn = round(sell_pe[0][1] - net_credit, 2)
        return capital, round(max_profit, 2), round(max_loss, 2), sorted([be_dn, be_up])

    if is_call_spread:
        # Bear call spread
        short_strike = sell_ce[0][1]
        long_strike = buy_ce[0][1]
        spread_width = abs(long_strike - short_strike)
        max_profit = net_credit * unit
        capital = (spread_width - net_credit) * unit
        max_loss = -capital
        be = round(short_strike + net_credit, 2)
        return capital, round(max_profit, 2), round(max_loss, 2), [be]

    if is_put_spread:
        # Bull put spread
        short_strike = sell_pe[0][1]
        long_strike = buy_pe[0][1]
        spread_width = abs(short_strike - long_strike)
        max_profit = net_credit * unit
        capital = (spread_width - net_credit) * unit
        max_loss = -capital
        be = round(short_strike - net_credit, 2)
        return capital, round(max_profit, 2), round(max_loss, 2), [be]

    if is_ratio:
        # Ratio backspread (sell 1 ATM, buy 2 OTM)
        # Net is usually a small credit or near-zero debit
        if net_credit >= 0:
            capital = max(0.0, spot * unit * 0.05)  # approximate margin for 1 short leg
        else:
            capital = abs(net_debit) * unit

        # Max loss is at the long strike (between short and long)
        if buy_ce:
            loss_zone = abs(buy_ce[0][1] - sell_ce[0][1]) if sell_ce else spot * 0.05
        elif buy_pe:
            loss_zone = abs(sell_pe[0][1] - buy_pe[0][1]) if sell_pe else spot * 0.05
        else:
            loss_zone = spot * 0.05

        max_loss = -(loss_zone - net_credit) * unit
        max_profit = unit * spot * 0.20  # large representative value
        return capital, round(max_profit, 2), round(max_loss, 2), [atm_strike]

    # Jade lizard / other mixed credit
    if sell_ce and sell_pe and buy_pe:
        # Jade lizard: short OTM call + short OTM put + long further OTM put
        put_spread_width = abs(buy_pe[0][1] - sell_pe[0][1])
        max_profit = net_credit * unit
        capital = max(0.0, (put_spread_width - net_credit) * unit)
        max_loss = -capital
        be = round(sell_pe[0][1] - net_credit, 2)
        return capital, round(max_profit, 2), round(max_loss, 2), [be]

    # Generic credit fallback
    capital = max(net_credit * unit * 2, unit * spot * 0.05)
    return capital, net_credit * unit, -capital, [atm_strike]


def _pnl_margin(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],
    net_credit: float,
    unit: int,
    spot: float,
) -> tuple[float, float, float, list[float]]:
    """P&L for naked sells (short straddle, short strangle, synthetic long/short)."""
    sell_ce = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type == "CE"
    ]
    buy_ce = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type == "CE"
    ]
    sell_pe = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type == "PE"
    ]
    buy_pe = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type == "PE"
    ]

    # Margin approximation: ~15% of notional per short leg
    short_count = len(sell_ce) + len(sell_pe)
    capital = round(spot * unit * 0.15 * short_count, 2)
    max_profit = net_credit * unit

    # Short straddle / strangle
    if sell_ce and sell_pe and not buy_ce and not buy_pe:
        be_up = round(sell_ce[0][1] + net_credit, 2)
        be_dn = round(sell_pe[0][1] - net_credit, 2)
        max_loss = -(spot * unit * 0.15)  # representative large loss
        return capital, round(max_profit, 2), round(max_loss, 2), sorted([be_dn, be_up])

    # Synthetic long (buy CE, sell PE)
    if buy_ce and sell_pe:
        be = round(buy_ce[0][1] - (sell_pe[0][2] - buy_ce[0][2]), 2)
        max_profit = unit * spot * 0.20
        max_loss = -(unit * spot * 0.20)
        return capital, round(max_profit, 2), round(max_loss, 2), [be]

    # Synthetic short (buy PE, sell CE)
    if buy_pe and sell_ce:
        be = round(buy_pe[0][1] + (sell_ce[0][2] - buy_pe[0][2]), 2)
        max_profit = unit * spot * 0.20
        max_loss = -(unit * spot * 0.20)
        return capital, round(max_profit, 2), round(max_loss, 2), [be]

    return capital, round(max_profit, 2), -(capital), [spot]


def _pnl_stock(
    template: StrategyTemplate,
    resolved: list[tuple[TemplateLeg, float, float]],
    net_credit: float,
    net_debit: float,
    unit: int,
    spot: float,
) -> tuple[float, float, float, list[float]]:
    """P&L for strategies involving a stock position (covered call, collar, etc.)."""
    sell_ce = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "SELL" and leg.option_type == "CE"
    ]
    buy_pe = [
        (leg, s, p) for leg, s, p in resolved if leg.action == "BUY" and leg.option_type == "PE"
    ]

    stock_cost = spot * unit
    option_net = (
        net_credit  # positive = net credit (covered call), negative = net debit (protective put)
    )

    # Capital = stock purchase minus any net credit from options
    capital = max(stock_cost - option_net * unit, stock_cost * 0.5)

    if sell_ce and not buy_pe:
        # Covered call
        call_strike = sell_ce[0][1]
        call_prem = sell_ce[0][2]
        max_profit_val = (call_strike - spot + call_prem) * unit
        # Max loss = stock falls to zero - premium received
        max_loss_val = -(spot - call_prem) * unit
        be = round(spot - call_prem, 2)
        return capital, round(max_profit_val, 2), round(max_loss_val, 2), [be]

    if buy_pe and sell_ce:
        # Collar
        put_strike = buy_pe[0][1]
        put_prem = buy_pe[0][2]
        call_strike = sell_ce[0][1]
        call_prem = sell_ce[0][2]
        net_opt = call_prem - put_prem  # net credit/debit on options
        max_profit_val = (call_strike - spot + net_opt) * unit
        max_loss_val = -(spot - put_strike - net_opt) * unit
        be = round(spot - net_opt, 2)
        return capital, round(max_profit_val, 2), round(max_loss_val, 2), [be]

    if buy_pe and not sell_ce:
        # Protective put / married put
        put_strike = buy_pe[0][1]
        put_prem = buy_pe[0][2]
        max_profit_val = spot * unit * 0.20  # large representative upside
        # Loss is capped at (stock price - put strike + put premium)
        max_loss_val = -(spot - put_strike + put_prem) * unit
        be = round(spot + put_prem, 2)
        return capital, round(max_profit_val, 2), round(max_loss_val, 2), [be]

    # Fallback
    return capital, capital * 0.15, -(capital * 0.85), [spot]
