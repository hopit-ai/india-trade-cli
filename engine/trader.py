"""
engine/trader.py
────────────────
Trader Agent — converts analysis verdicts into executable trade plans.

The missing link between "RELIANCE is a BUY" and actually placing an order.
Handles:
  - Position sizing (risk-based, not fixed %)
  - Entry type selection (market, limit, scale-in)
  - Dynamic stop-loss (ATR-based, support-based)
  - Profit targets (multiple targets with trailing)
  - Instrument selection (equity vs options vs spread)
  - Lot size handling for F&O
  - Risk checks before generating the plan

Usage:
    from engine.trader import TraderAgent, TradePlan

    trader = TraderAgent(capital=200000, risk_pct=2.0)
    plan = trader.generate_plan(
        symbol="RELIANCE",
        verdict="BUY",
        confidence=75,
        analyst_data={...},
    )
    plan.print_plan()

    # Or integrated with multi-agent pipeline
    plan = trader.generate_plan_from_analysis(symbol, reports, synthesis)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ── F&O Lot Sizes (as of 2026, update periodically) ──────────

LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "MIDCPNIFTY": 50,
    "RELIANCE": 250,
    "TCS": 150,
    "INFY": 300,
    "HDFCBANK": 550,
    "ICICIBANK": 700,
    "SBIN": 750,
    "BHARTIARTL": 475,
    "ITC": 1600,
    "KOTAKBANK": 400,
    "AXISBANK": 600,
    "LT": 150,
    "TATAMOTORS": 575,
    "MARUTI": 100,
    "BAJFINANCE": 125,
    "TITAN": 375,
    "WIPRO": 1500,
    "SUNPHARMA": 350,
    "HINDUNILVR": 300,
    "ASIANPAINT": 200,
    "TATASTEEL": 550,
    "M&M": 350,
    "ADANIENT": 250,
}

# Minimum margin requirement approximations (% of contract value)
MARGIN_PCT = {
    "equity": 100,  # full capital for delivery
    "intraday": 20,  # MIS margin
    "futures": 15,  # NRML F&O
    "options_buy": 100,  # premium-only for buying
    "options_sell": 20,  # margin for selling
}


# ── Risk Persona Profiles ────────────────────────────────────


@dataclass
class RiskProfile:
    """Configuration for a risk persona."""

    name: str  # "Aggressive" / "Neutral" / "Conservative"
    risk_pct: float  # % of capital to risk per trade
    sl_atr_mult: float  # ATR multiplier for stop-loss
    max_position_pct: float  # max % of capital in a single position
    target_rr: float  # minimum reward:risk ratio
    t1_rr: float  # R:R at which to take first partial profit
    t1_close_pct: str  # what to close at T1
    trail_trigger: float  # % gain to start trailing
    trail_step: float  # % trailing step
    prefer_options: bool  # prefer options over equity
    prefer_spreads: bool  # prefer spreads over naked options
    max_hold_swing: int  # max days for swing trades
    max_hold_pos: int  # max days for positional trades
    description: str = ""


RISK_PROFILES = {
    "aggressive": RiskProfile(
        name="Aggressive",
        risk_pct=3.0,
        sl_atr_mult=1.0,  # tight stop: 1x ATR
        max_position_pct=25.0,
        target_rr=3.0,  # aim for 3:1
        t1_rr=1.5,
        t1_close_pct="CLOSE_33%",  # take 1/3 at T1, let rest run
        trail_trigger=3.0,
        trail_step=1.0,
        prefer_options=True,
        prefer_spreads=False,  # ok with naked options
        max_hold_swing=15,
        max_hold_pos=60,
        description="High risk, high reward. Larger positions, tighter stops, "
        "prefers options for leverage. Suitable for experienced traders.",
    ),
    "neutral": RiskProfile(
        name="Neutral",
        risk_pct=2.0,
        sl_atr_mult=1.5,  # standard: 1.5x ATR
        max_position_pct=20.0,
        target_rr=2.0,  # aim for 2:1
        t1_rr=1.5,
        t1_close_pct="CLOSE_50%",  # take half at T1
        trail_trigger=2.0,
        trail_step=0.5,
        prefer_options=False,
        prefer_spreads=True,
        max_hold_swing=10,
        max_hold_pos=45,
        description="Balanced risk/reward. Standard position sizing, ATR-based stops, "
        "mix of equity and spreads. Default for most traders.",
    ),
    "conservative": RiskProfile(
        name="Conservative",
        risk_pct=1.0,
        sl_atr_mult=2.0,  # wide stop: 2x ATR (less likely to get stopped out)
        max_position_pct=15.0,
        target_rr=1.5,  # accept 1.5:1 (higher probability)
        t1_rr=1.0,
        t1_close_pct="CLOSE_50%",  # take half at 1:1
        trail_trigger=1.5,
        trail_step=0.5,
        prefer_options=False,
        prefer_spreads=True,  # always use defined-risk
        max_hold_swing=7,
        max_hold_pos=30,
        description="Capital preservation first. Smaller positions, wider stops, "
        "prefers equity delivery and spreads. Avoid naked options.",
    ),
}


# ── Data Models ──────────────────────────────────────────────


@dataclass
class OrderLeg:
    """A single order in the trade plan."""

    action: str  # "BUY" or "SELL"
    instrument: str  # "RELIANCE" or "RELIANCE 22500 CE APR"
    exchange: str  # "NSE" or "NFO"
    product: str  # "CNC" (delivery) / "MIS" (intraday) / "NRML" (F&O)
    order_type: str  # "MARKET" / "LIMIT" / "SL" / "SL-M"
    quantity: int
    price: Optional[float] = None  # for LIMIT orders
    trigger_price: Optional[float] = None  # for SL orders
    lot_size: int = 1
    lots: int = 1
    tag: str = ""  # tracking label


@dataclass
class ExitPlan:
    """When and how to exit the position."""

    stop_loss: float  # absolute price
    stop_loss_pct: float  # % from entry
    stop_loss_type: str  # "FIXED" / "TRAILING" / "ATR_BASED"

    target_1: float  # first profit target
    target_1_pct: float  # % from entry
    target_1_action: str = "CLOSE_50%"  # what to do at T1

    target_2: Optional[float] = None
    target_2_pct: Optional[float] = None
    target_2_action: str = "CLOSE_REMAINING"

    trail_trigger: Optional[float] = None  # start trailing after this %
    trail_step: Optional[float] = None  # trail SL by this %

    time_exit: str = ""  # "SAME_DAY" / "BEFORE_EXPIRY" / "AFTER_EARNINGS" / ""
    max_hold_days: Optional[int] = None


@dataclass
class TradePlan:
    """Complete executable trade plan."""

    # Identity
    symbol: str
    exchange: str
    timestamp: str

    # Strategy
    strategy_name: str  # "Delivery Buy", "Bull Call Spread", "Intraday Long"
    direction: str  # "LONG" / "SHORT" / "NEUTRAL"
    instrument_type: str  # "EQUITY" / "FUTURES" / "OPTIONS" / "SPREAD"
    timeframe: str  # "INTRADAY" / "SWING" (2-10 days) / "POSITIONAL" (>10 days)

    # Sizing
    capital_deployed: float  # INR
    capital_pct: float  # % of total capital
    max_risk: float  # INR max loss if SL hits
    risk_pct: float  # % of capital at risk
    reward_risk: float  # R:R ratio

    # Orders
    entry_orders: list[OrderLeg] = field(default_factory=list)
    exit_plan: Optional[ExitPlan] = None

    # Scaling
    scale_in: bool = False
    scale_logic: str = ""  # "50% now, 50% at support" / "All at market"

    # Context
    rationale: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    pre_conditions: list[str] = field(default_factory=list)  # conditions that must hold

    # Verdict that generated this plan
    verdict: str = ""  # from synthesis
    confidence: int = 0

    def print_plan(self) -> None:
        """Display the trade plan as a Rich panel."""
        dir_style = (
            "green"
            if self.direction == "LONG"
            else "red"
            if self.direction == "SHORT"
            else "yellow"
        )

        lines = [
            f"  [bold]{self.strategy_name}[/bold]  [{dir_style}]{self.direction}[/{dir_style}]",
            f"  {self.symbol} ({self.exchange}) | {self.instrument_type} | {self.timeframe}",
            f"  Verdict: {self.verdict} (confidence: {self.confidence}%)",
            "",
            "  [bold]Sizing[/bold]",
            f"  Capital    : {self.capital_deployed:,.0f} ({self.capital_pct:.1f}% of portfolio)",
            f"  Max Risk   : {self.max_risk:,.0f} ({self.risk_pct:.1f}% of capital)",
            f"  R:R Ratio  : {self.reward_risk:.1f}",
        ]

        if self.scale_in:
            lines.append(f"  Scaling    : {self.scale_logic}")

        lines.append("")
        lines.append("  [bold]Entry Orders[/bold]")
        for i, leg in enumerate(self.entry_orders, 1):
            price_str = f"@ {leg.price:,.2f}" if leg.price else "@ MARKET"
            lines.append(
                f"  [{i}] {leg.action} {leg.quantity} {leg.instrument} "
                f"({leg.product}) {leg.order_type} {price_str}"
            )

        if self.exit_plan:
            ep = self.exit_plan
            lines.extend(
                [
                    "",
                    "  [bold]Exit Plan[/bold]",
                    f"  Stop-Loss  : {ep.stop_loss:,.2f} ({ep.stop_loss_pct:+.1f}%) [{ep.stop_loss_type}]",
                    f"  Target 1   : {ep.target_1:,.2f} ({ep.target_1_pct:+.1f}%) → {ep.target_1_action}",
                ]
            )
            if ep.target_2:
                lines.append(
                    f"  Target 2   : {ep.target_2:,.2f} ({ep.target_2_pct:+.1f}%) → {ep.target_2_action}"
                )
            if ep.trail_trigger:
                lines.append(
                    f"  Trailing   : Start at +{ep.trail_trigger:.1f}%, step {ep.trail_step:.1f}%"
                )
            if ep.time_exit:
                lines.append(f"  Time Exit  : {ep.time_exit}")
            if ep.max_hold_days:
                lines.append(f"  Max Hold   : {ep.max_hold_days} days")

        if self.rationale:
            lines.append("")
            lines.append("  [bold]Rationale[/bold]")
            for r in self.rationale:
                lines.append(f"  - {r}")

        if self.risks:
            lines.append("")
            lines.append("  [bold]Risks[/bold]")
            for r in self.risks:
                lines.append(f"  - {r}")

        if self.pre_conditions:
            lines.append("")
            lines.append("  [bold]Pre-conditions[/bold]")
            for p in self.pre_conditions:
                lines.append(f"  - {p}")

        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]TRADE PLAN[/bold cyan]",
                border_style="cyan",
            )
        )


# ── Trader Agent ─────────────────────────────────────────────


class TraderAgent:
    """
    Converts analysis verdicts into executable trade plans.

    Supports 3 risk personas:
      - Aggressive: larger positions, tighter stops, prefers options
      - Neutral: balanced, ATR-based stops, mix of equity and spreads
      - Conservative: smaller positions, wider stops, equity delivery + spreads

    Takes into account:
      - Capital and risk parameters (per persona)
      - Current portfolio exposure
      - VIX regime (adjusts sizing)
      - ATR for dynamic stop-loss
      - Support/resistance for entry/exit levels
      - F&O lot sizes for options strategies
    """

    def __init__(
        self,
        capital: Optional[float] = None,
        risk_pct: Optional[float] = None,
        profile: Optional[str] = None,  # "aggressive" / "neutral" / "conservative"
    ) -> None:
        self.capital = capital or float(os.environ.get("TOTAL_CAPITAL", "200000"))
        self.risk_pct = risk_pct or float(os.environ.get("DEFAULT_RISK_PCT", "2"))
        self.profile = RISK_PROFILES.get(profile or "neutral", RISK_PROFILES["neutral"])

    def generate_plan(
        self,
        symbol: str,
        exchange: str = "NSE",
        verdict: str = "HOLD",
        confidence: int = 50,
        ltp: Optional[float] = None,
        atr: Optional[float] = None,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        vix: Optional[float] = None,
        rsi: Optional[float] = None,
        iv_rank: Optional[float] = None,
        strategy_hint: str = "",
        synthesis_text: str = "",
    ) -> Optional[TradePlan]:
        """
        Generate a concrete trade plan from analysis data.

        Returns None for HOLD verdicts (no action needed).
        """
        symbol = symbol.upper()
        verdict = verdict.upper()

        # No plan for HOLD
        if verdict == "HOLD":
            return None

        # Get current price if not provided
        if not ltp:
            ltp = self._get_ltp(symbol, exchange)
        if not ltp or ltp <= 0:
            return None

        # Get ATR for dynamic SL if not provided
        if not atr:
            atr = self._get_atr(symbol, exchange)

        # VIX adjustment factor
        vix_factor = self._vix_adjustment(vix)

        # Determine strategy
        strategy = self._select_strategy(
            symbol,
            verdict,
            confidence,
            ltp,
            atr,
            support,
            resistance,
            vix,
            rsi,
            iv_rank,
            strategy_hint,
        )

        # Position sizing
        sizing = self._calculate_sizing(
            ltp,
            atr,
            strategy,
            vix_factor,
            confidence,
        )

        # Entry orders
        entry_orders = self._build_entry_orders(
            symbol,
            exchange,
            strategy,
            ltp,
            sizing,
            support,
        )

        # Exit plan
        exit_plan = self._build_exit_plan(
            strategy,
            ltp,
            atr,
            sizing,
            support,
            resistance,
            vix_factor,
        )

        # Parse rationale from synthesis
        rationale = self._extract_rationale(synthesis_text) if synthesis_text else []
        risks = self._extract_risks(synthesis_text) if synthesis_text else []

        # Pre-conditions
        pre_conditions = self._check_preconditions(symbol, ltp, vix, confidence)

        return TradePlan(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            strategy_name=strategy["name"],
            direction=strategy["direction"],
            instrument_type=strategy["instrument"],
            timeframe=strategy["timeframe"],
            capital_deployed=sizing["capital_deployed"],
            capital_pct=sizing["capital_pct"],
            max_risk=sizing["max_risk"],
            risk_pct=self.risk_pct * vix_factor,
            reward_risk=sizing["reward_risk"],
            entry_orders=entry_orders,
            exit_plan=exit_plan,
            scale_in=strategy.get("scale_in", False),
            scale_logic=strategy.get("scale_logic", ""),
            rationale=rationale,
            risks=risks,
            pre_conditions=pre_conditions,
            verdict=verdict,
            confidence=confidence,
        )

    def generate_plan_from_reports(
        self,
        symbol: str,
        exchange: str,
        reports: list,
        synthesis: str,
    ) -> Optional[TradePlan]:
        """Generate plan directly from multi-agent pipeline output."""
        # Extract data from analyst reports
        ltp = None
        atr = None
        support = None
        resistance = None
        vix = None
        rsi = None
        iv_rank = None

        for r in reports:
            if not hasattr(r, "analyst") or r.error:
                continue
            data = r.data if hasattr(r, "data") else {}

            if r.analyst == "Technical":
                ltp = ltp or data.get("ltp")
                atr = data.get("atr")
                support = data.get("support")
                resistance = data.get("resistance")
                rsi = data.get("rsi")

            elif r.analyst == "Risk Manager":
                vix = data.get("vix")
                ltp = ltp or data.get("ltp")

            elif r.analyst == "Options":
                iv_rank = data.get("iv_rank")

        # Parse verdict from synthesis
        verdict, confidence, strategy_hint = _parse_synthesis_verdict(synthesis)

        return self.generate_plan(
            symbol=symbol,
            exchange=exchange,
            verdict=verdict,
            confidence=confidence,
            ltp=ltp,
            atr=atr,
            support=support,
            resistance=resistance,
            vix=vix,
            rsi=rsi,
            iv_rank=iv_rank,
            strategy_hint=strategy_hint,
            synthesis_text=synthesis,
        )

    # ── All 3 Risk Personas ────────────────────────────────────

    def generate_all_plans(
        self,
        symbol: str,
        exchange: str = "NSE",
        reports: Optional[list] = None,
        synthesis: str = "",
        **kwargs,
    ) -> dict[str, Optional["TradePlan"]]:
        """
        Generate trade plans for all 3 risk personas.
        Returns dict: {"aggressive": plan, "neutral": plan, "conservative": plan}
        """
        results = {}
        original_profile = self.profile

        for profile_name in ("aggressive", "neutral", "conservative"):
            self.profile = RISK_PROFILES[profile_name]
            if reports and synthesis:
                plan = self.generate_plan_from_reports(symbol, exchange, reports, synthesis)
            else:
                plan = self.generate_plan(symbol=symbol, exchange=exchange, **kwargs)
            results[profile_name] = plan

        self.profile = original_profile
        return results

    @staticmethod
    def print_all_plans(plans: dict[str, Optional["TradePlan"]]) -> None:
        """Display all 3 risk persona trade plans side by side."""
        console.print()
        console.rule("[bold cyan]Risk Management Team — 3 Perspectives[/bold cyan]", style="cyan")

        table = Table(show_header=True, header_style="bold", show_lines=True)
        table.add_column("", width=16, style="bold")
        table.add_column("[red]Aggressive[/red]", ratio=1)
        table.add_column("[yellow]Neutral[/yellow]", ratio=1)
        table.add_column("[green]Conservative[/green]", ratio=1)

        plans_list = [
            plans.get("aggressive"),
            plans.get("neutral"),
            plans.get("conservative"),
        ]

        def _val(plan, attr, fmt="{}", default="-"):
            if plan is None:
                return "NO TRADE"
            val = getattr(plan, attr, None)
            if val is None:
                return default
            return fmt.format(val)

        # Strategy
        table.add_row(
            "Strategy",
            _val(plans_list[0], "strategy_name"),
            _val(plans_list[1], "strategy_name"),
            _val(plans_list[2], "strategy_name"),
        )

        # Capital deployed
        table.add_row(
            "Capital",
            _val(plans_list[0], "capital_deployed", "{:,.0f}")
            + f" ({_val(plans_list[0], 'capital_pct', '{:.0f}')}%)",
            _val(plans_list[1], "capital_deployed", "{:,.0f}")
            + f" ({_val(plans_list[1], 'capital_pct', '{:.0f}')}%)",
            _val(plans_list[2], "capital_deployed", "{:,.0f}")
            + f" ({_val(plans_list[2], 'capital_pct', '{:.0f}')}%)",
        )

        # Max risk
        table.add_row(
            "Max Risk",
            _val(plans_list[0], "max_risk", "{:,.0f}"),
            _val(plans_list[1], "max_risk", "{:,.0f}"),
            _val(plans_list[2], "max_risk", "{:,.0f}"),
        )

        # Quantity
        def _qty(plan):
            if not plan or not plan.entry_orders:
                return "-"
            total = sum(o.quantity for o in plan.entry_orders)
            return str(total)

        table.add_row("Quantity", _qty(plans_list[0]), _qty(plans_list[1]), _qty(plans_list[2]))

        # Stop-loss
        def _sl(plan):
            if not plan or not plan.exit_plan:
                return "-"
            ep = plan.exit_plan
            return f"{ep.stop_loss:,.1f} ({ep.stop_loss_pct:+.1f}%)"

        table.add_row("Stop-Loss", _sl(plans_list[0]), _sl(plans_list[1]), _sl(plans_list[2]))

        # Target 1
        def _t1(plan):
            if not plan or not plan.exit_plan:
                return "-"
            ep = plan.exit_plan
            return f"{ep.target_1:,.1f} ({ep.target_1_pct:+.1f}%)\n→ {ep.target_1_action}"

        table.add_row("Target 1", _t1(plans_list[0]), _t1(plans_list[1]), _t1(plans_list[2]))

        # Target 2
        def _t2(plan):
            if not plan or not plan.exit_plan:
                return "-"
            ep = plan.exit_plan
            if ep.target_2:
                return f"{ep.target_2:,.1f} ({ep.target_2_pct:+.1f}%)"
            return "-"

        table.add_row("Target 2", _t2(plans_list[0]), _t2(plans_list[1]), _t2(plans_list[2]))

        # R:R
        table.add_row(
            "R:R Ratio",
            _val(plans_list[0], "reward_risk", "{:.1f}"),
            _val(plans_list[1], "reward_risk", "{:.1f}"),
            _val(plans_list[2], "reward_risk", "{:.1f}"),
        )

        # Max hold
        def _hold(plan):
            if not plan or not plan.exit_plan or not plan.exit_plan.max_hold_days:
                return "-"
            return f"{plan.exit_plan.max_hold_days}d"

        table.add_row("Max Hold", _hold(plans_list[0]), _hold(plans_list[1]), _hold(plans_list[2]))

        console.print(table)

        # Print profile descriptions
        for name, profile in RISK_PROFILES.items():
            style = {"aggressive": "red", "neutral": "yellow", "conservative": "green"}[name]
            console.print(f"  [{style}]{profile.name}[/{style}]: [dim]{profile.description}[/dim]")
        console.print()

    # ── Strategy Selection ───────────────────────────────────

    def _select_strategy(
        self,
        symbol,
        verdict,
        confidence,
        ltp,
        atr,
        support,
        resistance,
        vix,
        rsi,
        iv_rank,
        hint,
    ) -> dict:
        """
        Select the best strategy based on conditions.

        Returns dict with: name, direction, instrument, timeframe, scale_in, scale_logic
        """
        is_buy = verdict in ("BUY", "STRONG_BUY")
        is_sell = verdict in ("SELL", "STRONG_SELL")
        high_conviction = confidence >= 70
        has_options = symbol in LOT_SIZES

        # VIX regime
        high_vix = vix and vix > 18

        # ── High conviction buy ──────────────────────────────
        if is_buy and high_conviction:
            if high_vix and has_options:
                # High VIX: sell puts (get paid to buy at lower price)
                return {
                    "name": "Cash-Secured Put (High VIX)",
                    "direction": "LONG",
                    "instrument": "OPTIONS",
                    "timeframe": "SWING",
                    "scale_in": False,
                    "scale_logic": "",
                }

            if atr and support and ltp:
                # Scale in: 50% now, 50% at support
                return {
                    "name": "Delivery Buy (Scale-In)",
                    "direction": "LONG",
                    "instrument": "EQUITY",
                    "timeframe": "POSITIONAL",
                    "scale_in": True,
                    "scale_logic": f"50% at market, 50% limit at support ({support:,.0f})",
                }

            return {
                "name": "Delivery Buy",
                "direction": "LONG",
                "instrument": "EQUITY",
                "timeframe": "POSITIONAL",
                "scale_in": False,
                "scale_logic": "",
            }

        # ── Moderate conviction buy ──────────────────────────
        if is_buy and not high_conviction:
            if has_options and iv_rank and iv_rank < 40:
                return {
                    "name": "Call Option Buy (Low IV)",
                    "direction": "LONG",
                    "instrument": "OPTIONS",
                    "timeframe": "SWING",
                    "scale_in": False,
                    "scale_logic": "",
                }

            return {
                "name": "Delivery Buy (Small Position)",
                "direction": "LONG",
                "instrument": "EQUITY",
                "timeframe": "SWING",
                "scale_in": False,
                "scale_logic": "",
            }

        # ── Sell signals ─────────────────────────────────────
        if is_sell and high_conviction:
            if has_options:
                return {
                    "name": "Put Option Buy",
                    "direction": "SHORT",
                    "instrument": "OPTIONS",
                    "timeframe": "SWING",
                    "scale_in": False,
                    "scale_logic": "",
                }
            return {
                "name": "Exit / Reduce Position",
                "direction": "SHORT",
                "instrument": "EQUITY",
                "timeframe": "SWING",
                "scale_in": False,
                "scale_logic": "",
            }

        if is_sell:
            return {
                "name": "Hedge with Puts / Tighten SL",
                "direction": "SHORT",
                "instrument": "OPTIONS" if has_options else "EQUITY",
                "timeframe": "SWING",
                "scale_in": False,
                "scale_logic": "",
            }

        # Default: small delivery buy
        return {
            "name": "Delivery Buy",
            "direction": "LONG",
            "instrument": "EQUITY",
            "timeframe": "SWING",
            "scale_in": False,
            "scale_logic": "",
        }

    # ── Position Sizing ──────────────────────────────────────

    def _calculate_sizing(
        self,
        ltp,
        atr,
        strategy,
        vix_factor,
        confidence,
    ) -> dict:
        """
        Risk-based position sizing using the active risk profile.

        Method: Risk per trade = capital * profile.risk_pct * vix_adjustment
        Shares = risk_amount / (SL distance per share)
        """
        risk_pct = self.profile.risk_pct
        risk_amount = self.capital * (risk_pct / 100) * vix_factor

        # SL distance: use ATR * profile multiplier, else 3% default
        if atr and atr > 0:
            sl_distance = atr * self.profile.sl_atr_mult
        else:
            sl_distance = ltp * 0.03  # 3% default

        if sl_distance <= 0:
            sl_distance = ltp * 0.03

        # Shares from risk
        shares = int(risk_amount / sl_distance)
        if shares <= 0:
            shares = 1

        # Cap at profile's max position %
        max_capital = self.capital * (self.profile.max_position_pct / 100)
        max_shares = int(max_capital / ltp) if ltp > 0 else shares
        shares = min(shares, max_shares)

        # For F&O: round to lot size
        if strategy["instrument"] in ("OPTIONS", "FUTURES"):
            lot = LOT_SIZES.get(strategy.get("_symbol", ""), 1)
            if lot > 1:
                lots = max(1, shares // lot)
                shares = lots * lot

        capital_deployed = shares * ltp
        capital_pct = (capital_deployed / self.capital * 100) if self.capital else 0

        # R:R estimate
        target_distance = sl_distance * 2  # minimum 2:1 R:R target
        reward_risk = target_distance / sl_distance if sl_distance > 0 else 2.0

        return {
            "shares": shares,
            "capital_deployed": round(capital_deployed, 2),
            "capital_pct": round(capital_pct, 1),
            "max_risk": round(risk_amount, 2),
            "sl_distance": round(sl_distance, 2),
            "reward_risk": round(reward_risk, 1),
        }

    # ── Entry Orders ─────────────────────────────────────────

    def _build_entry_orders(
        self,
        symbol,
        exchange,
        strategy,
        ltp,
        sizing,
        support,
    ) -> list[OrderLeg]:
        """Build the actual order legs."""
        shares = sizing["shares"]
        orders = []

        if strategy["instrument"] == "EQUITY":
            product = "CNC" if strategy["timeframe"] == "POSITIONAL" else "MIS"

            if strategy.get("scale_in") and support and support < ltp:
                # Split: 50% market, 50% limit at support
                half = shares // 2
                orders.append(
                    OrderLeg(
                        action="BUY" if strategy["direction"] == "LONG" else "SELL",
                        instrument=symbol,
                        exchange=exchange,
                        product=product,
                        order_type="MARKET",
                        quantity=half or 1,
                        tag="ENTRY_1",
                    )
                )
                orders.append(
                    OrderLeg(
                        action="BUY" if strategy["direction"] == "LONG" else "SELL",
                        instrument=symbol,
                        exchange=exchange,
                        product=product,
                        order_type="LIMIT",
                        quantity=shares - half,
                        price=round(support, 2),
                        tag="ENTRY_2_SCALE",
                    )
                )
            else:
                orders.append(
                    OrderLeg(
                        action="BUY" if strategy["direction"] == "LONG" else "SELL",
                        instrument=symbol,
                        exchange=exchange,
                        product=product,
                        order_type="MARKET",
                        quantity=shares,
                        tag="ENTRY",
                    )
                )

        elif strategy["instrument"] == "OPTIONS":
            lot = LOT_SIZES.get(symbol, 1)
            lots = max(1, shares // lot) if lot > 1 else 1
            qty = lots * lot

            orders.append(
                OrderLeg(
                    action="BUY",
                    instrument=f"{symbol} ATM {'CE' if strategy['direction'] == 'LONG' else 'PE'}",
                    exchange="NFO",
                    product="NRML",
                    order_type="MARKET",
                    quantity=qty,
                    lot_size=lot,
                    lots=lots,
                    tag="ENTRY",
                )
            )

        return orders

    # ── Exit Plan ────────────────────────────────────────────

    def _build_exit_plan(
        self,
        strategy,
        ltp,
        atr,
        sizing,
        support,
        resistance,
        vix_factor,
    ) -> ExitPlan:
        """Build dynamic stop-loss and profit targets."""
        sl_distance = sizing["sl_distance"]
        is_long = strategy["direction"] == "LONG"

        # Stop-loss
        if is_long:
            sl_price = ltp - sl_distance
            # Don't set SL below strong support
            if support and sl_price < support * 0.98:
                sl_price = support * 0.98
        else:
            sl_price = ltp + sl_distance

        sl_pct = (sl_price - ltp) / ltp * 100

        # SL type
        sl_type = "ATR_BASED" if atr else "FIXED"

        # Target 1: profile's T1 R:R
        t1_distance = sl_distance * self.profile.t1_rr
        if is_long:
            t1 = ltp + t1_distance
            if resistance and t1 > resistance:
                t1 = resistance  # cap at resistance
        else:
            t1 = ltp - t1_distance

        t1_pct = (t1 - ltp) / ltp * 100

        # Target 2: profile's full target R:R
        t2_distance = sl_distance * self.profile.target_rr
        t2 = ltp + t2_distance if is_long else ltp - t2_distance
        t2_pct = (t2 - ltp) / ltp * 100

        # Trailing logic from profile
        trail_trigger = self.profile.trail_trigger
        trail_step = self.profile.trail_step

        # Timeframe-based exit from profile
        time_exit = ""
        max_hold = None
        if strategy["timeframe"] == "INTRADAY":
            time_exit = "SAME_DAY"
            max_hold = 1
        elif strategy["timeframe"] == "SWING":
            max_hold = self.profile.max_hold_swing
        elif strategy["timeframe"] == "POSITIONAL":
            max_hold = self.profile.max_hold_pos

        return ExitPlan(
            stop_loss=round(sl_price, 2),
            stop_loss_pct=round(sl_pct, 2),
            stop_loss_type=sl_type,
            target_1=round(t1, 2),
            target_1_pct=round(t1_pct, 2),
            target_1_action=self.profile.t1_close_pct,
            target_2=round(t2, 2),
            target_2_pct=round(t2_pct, 2),
            target_2_action="CLOSE_REMAINING",
            trail_trigger=trail_trigger,
            trail_step=trail_step,
            time_exit=time_exit,
            max_hold_days=max_hold,
        )

    # ── Helpers ──────────────────────────────────────────────

    def _get_ltp(self, symbol: str, exchange: str) -> float:
        """Get current price."""
        try:
            from market.quotes import get_ltp

            return get_ltp(f"{exchange}:{symbol}")
        except Exception:
            return 0.0

    def _get_atr(self, symbol: str, exchange: str) -> Optional[float]:
        """Get ATR from technical analysis."""
        try:
            from analysis.technical import analyse

            snap = analyse(symbol, exchange)
            return snap.atr if snap.atr > 0 else None
        except Exception:
            return None

    def _vix_adjustment(self, vix: Optional[float]) -> float:
        """
        Adjust risk based on VIX regime.
        High VIX = reduce size, Low VIX = normal size.
        """
        if vix is None:
            return 1.0
        if vix > 25:
            return 0.5  # halve position size
        if vix > 20:
            return 0.65
        if vix > 15:
            return 0.85
        return 1.0

    def _extract_rationale(self, text: str) -> list[str]:
        """Extract rationale bullets from synthesis text."""
        points = []
        in_rationale = False
        for line in text.splitlines():
            stripped = line.strip()
            if "RATIONALE" in stripped.upper() or "WHY" in stripped.upper():
                in_rationale = True
                continue
            if in_rationale and stripped.startswith("- "):
                points.append(stripped.lstrip("- ").strip())
            elif in_rationale and stripped and not stripped.startswith("-"):
                in_rationale = False
        return points[:5]

    def _extract_risks(self, text: str) -> list[str]:
        """Extract risk bullets from synthesis text."""
        points = []
        in_risks = False
        for line in text.splitlines():
            stripped = line.strip()
            if "RISK" in stripped.upper():
                in_risks = True
                continue
            if in_risks and stripped.startswith("- "):
                points.append(stripped.lstrip("- ").strip())
            elif in_risks and stripped and not stripped.startswith("-"):
                in_risks = False
        return points[:5]

    def _check_preconditions(
        self,
        symbol,
        ltp,
        vix,
        confidence,
    ) -> list[str]:
        """Check conditions that should hold before executing."""
        conditions = []

        if confidence < 50:
            conditions.append(f"LOW CONFIDENCE ({confidence}%) — consider paper trading first")

        if vix and vix > 20:
            conditions.append(
                f"VIX elevated ({vix:.1f}) — position size reduced, use defined-risk only"
            )

        # Check for upcoming events
        try:
            from engine.event_strategies import get_event_strategies

            events = get_event_strategies(symbols=[symbol], days_ahead=3)
            for ev in events:
                conditions.append(f"EVENT in {ev.days_away}d: {ev.event} — {ev.strategy[:50]}")
        except Exception:
            pass

        return conditions


# ── Helpers ──────────────────────────────────────────────────


def _parse_synthesis_verdict(text: str) -> tuple[str, int, str]:
    """Extract verdict, confidence, strategy from synthesis text."""
    verdict = "HOLD"
    confidence = 50
    strategy = ""

    for line in text.splitlines():
        upper = line.strip().upper()
        if upper.startswith("VERDICT:"):
            val = line.split(":", 1)[1].strip().upper()
            for v in ("STRONG_BUY", "STRONG_SELL", "BUY", "SELL", "HOLD"):
                if v in val:
                    verdict = v
                    break
        elif upper.startswith("CONFIDENCE:"):
            try:
                confidence = int(line.split(":", 1)[1].strip().rstrip("%"))
            except (ValueError, IndexError):
                pass
        elif upper.startswith("STRATEGY"):
            strategy = line.split(":", 1)[1].strip() if ":" in line else ""

    return verdict, confidence, strategy
