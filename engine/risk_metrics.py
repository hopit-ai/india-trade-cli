"""
engine/risk_metrics.py
──────────────────────
Portfolio risk metrics: Value-at-Risk (VaR), Conditional VaR (CVaR),
correlation matrix, and concentration analysis.

VaR: "With 95% confidence, you won't lose more than ₹X in one day."
CVaR: "If the worst 5% of days happen, your avg loss would be ₹X."

Usage:
    from engine.risk_metrics import compute_var, compute_portfolio_risk, print_risk_report

    # Single stock
    var = compute_var("RELIANCE", confidence=0.95, days=1)

    # Full portfolio
    report = compute_portfolio_risk()
    report.print_report()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class VaRResult:
    """Value-at-Risk calculation result for a single holding."""
    symbol:       str
    position_value: float       # current market value
    var_95:       float          # 1-day 95% VaR (INR)
    var_99:       float          # 1-day 99% VaR (INR)
    cvar_95:      float          # Conditional VaR at 95% (INR)
    volatility:   float          # annualized volatility %
    daily_vol:    float          # daily volatility %


@dataclass
class PortfolioRiskReport:
    """Comprehensive portfolio risk report."""
    # Portfolio-level VaR
    portfolio_value:    float
    portfolio_var_95:   float       # 1-day 95% VaR (INR)
    portfolio_var_99:   float
    portfolio_cvar_95:  float
    portfolio_volatility: float     # annualized %

    # Per-holding breakdown
    holding_vars:       list[VaRResult] = field(default_factory=list)

    # Correlation
    correlation_matrix: Optional[dict] = None   # symbol → symbol → corr
    high_correlations:  list[str] = field(default_factory=list)

    # Concentration
    top_concentration:  list[dict] = field(default_factory=list)  # [{symbol, pct}]
    hhi:                float = 0.0  # Herfindahl-Hirschman Index (0-1)
    concentration_risk: str = "LOW"  # LOW / MEDIUM / HIGH

    def print_report(self) -> None:
        """Display risk report as Rich panels + tables."""
        # Portfolio summary
        var_pct = (self.portfolio_var_95 / self.portfolio_value * 100
                   if self.portfolio_value else 0)
        lines = [
            f"  Portfolio Value    : {self.portfolio_value:,.0f}",
            f"  Annual Volatility  : {self.portfolio_volatility:.1f}%",
            "",
            "  [bold]Value-at-Risk (1-day)[/bold]",
            f"  VaR 95%  : [red]{self.portfolio_var_95:,.0f}[/red] ({var_pct:.2f}%)",
            f"  VaR 99%  : [red]{self.portfolio_var_99:,.0f}[/red]",
            f"  CVaR 95% : [red]{self.portfolio_cvar_95:,.0f}[/red]  (avg loss in worst 5% of days)",
            "",
            "  [bold]Concentration[/bold]",
            f"  HHI Index : {self.hhi:.3f}  ({self.concentration_risk})",
        ]

        console.print(Panel(
            "\n".join(lines),
            title="[bold cyan]Portfolio Risk Report[/bold cyan]",
            border_style="cyan",
        ))

        # Per-holding VaR
        if self.holding_vars:
            table = Table(title="Per-Holding VaR (1-day)", show_lines=False)
            table.add_column("Symbol", style="bold", width=14)
            table.add_column("Value", justify="right", width=12)
            table.add_column("Vol (ann)", justify="right", width=10)
            table.add_column("VaR 95%", justify="right", width=12)
            table.add_column("CVaR 95%", justify="right", width=12)

            for v in sorted(self.holding_vars, key=lambda x: -x.var_95):
                table.add_row(
                    v.symbol,
                    f"{v.position_value:,.0f}",
                    f"{v.volatility:.1f}%",
                    f"[red]{v.var_95:,.0f}[/red]",
                    f"[red]{v.cvar_95:,.0f}[/red]",
                )
            console.print(table)

        # High correlations
        if self.high_correlations:
            console.print("\n[bold yellow]High Correlations (>0.7):[/bold yellow]")
            for hc in self.high_correlations:
                console.print(f"  {hc}")

        # Concentration
        if self.top_concentration:
            console.print("\n[bold]Top Concentration:[/bold]")
            for c in self.top_concentration[:5]:
                console.print(f"  {c['symbol']:12s} {c['pct']:.1f}%")


# ── VaR Calculations ─────────────────────────────────────────

def compute_var(
    symbol: str,
    position_value: float = 100000,
    confidence: float = 0.95,
    days: int = 1,
    lookback_days: int = 252,
) -> VaRResult:
    """
    Compute VaR for a single stock using historical simulation.

    Method: sort historical daily returns, VaR = percentile loss.
    """
    returns = _get_daily_returns(symbol, lookback_days)
    if returns is None or len(returns) < 30:
        # Fallback: assume 2% daily vol
        daily_vol = 0.02
        ann_vol = daily_vol * math.sqrt(252) * 100
        var_95 = position_value * daily_vol * 1.645 * math.sqrt(days)
        var_99 = position_value * daily_vol * 2.326 * math.sqrt(days)
        return VaRResult(
            symbol=symbol, position_value=position_value,
            var_95=round(var_95, 2), var_99=round(var_99, 2),
            cvar_95=round(var_95 * 1.2, 2),
            volatility=round(ann_vol, 1), daily_vol=round(daily_vol * 100, 2),
        )

    daily_vol = float(np.std(returns))
    ann_vol = daily_vol * math.sqrt(252)

    # Historical VaR
    sorted_returns = np.sort(returns)
    var_95_pct = float(np.percentile(sorted_returns, (1 - 0.95) * 100))
    var_99_pct = float(np.percentile(sorted_returns, (1 - 0.99) * 100))

    # Scale for multi-day
    var_95 = abs(var_95_pct) * position_value * math.sqrt(days)
    var_99 = abs(var_99_pct) * position_value * math.sqrt(days)

    # CVaR (Expected Shortfall): average of returns below VaR
    tail_returns = sorted_returns[sorted_returns <= var_95_pct]
    cvar_95_pct = float(np.mean(tail_returns)) if len(tail_returns) > 0 else var_95_pct
    cvar_95 = abs(cvar_95_pct) * position_value * math.sqrt(days)

    return VaRResult(
        symbol=symbol,
        position_value=position_value,
        var_95=round(var_95, 2),
        var_99=round(var_99, 2),
        cvar_95=round(cvar_95, 2),
        volatility=round(ann_vol * 100, 1),
        daily_vol=round(daily_vol * 100, 2),
    )


def compute_portfolio_risk() -> PortfolioRiskReport:
    """
    Compute portfolio-level risk metrics from current holdings.
    Uses correlation-adjusted VaR (not just sum of individual VaRs).
    """
    # Load holdings
    holdings = _get_holdings()
    if not holdings:
        return PortfolioRiskReport(
            portfolio_value=0, portfolio_var_95=0, portfolio_var_99=0,
            portfolio_cvar_95=0, portfolio_volatility=0,
        )

    symbols = [h["symbol"] for h in holdings]
    values = [h["value"] for h in holdings]
    total_value = sum(values)

    # Per-holding VaR
    holding_vars = []
    all_returns = {}

    for h in holdings:
        var = compute_var(h["symbol"], h["value"])
        holding_vars.append(var)
        returns = _get_daily_returns(h["symbol"])
        if returns is not None:
            all_returns[h["symbol"]] = returns

    # Correlation matrix
    corr_matrix = {}
    high_corrs = []

    if len(all_returns) >= 2:
        # Align returns by length
        min_len = min(len(r) for r in all_returns.values())
        aligned = {s: r[-min_len:] for s, r in all_returns.items() if len(r) >= min_len}

        if len(aligned) >= 2:
            df = pd.DataFrame(aligned)
            corr = df.corr()
            corr_matrix = corr.to_dict()

            # Find high correlations
            syms = list(aligned.keys())
            for i in range(len(syms)):
                for j in range(i + 1, len(syms)):
                    c = float(corr.iloc[i, j])
                    if abs(c) > 0.7:
                        high_corrs.append(f"{syms[i]} ↔ {syms[j]}: {c:.2f}")

    # Portfolio VaR (correlation-adjusted)
    if len(all_returns) >= 2 and corr_matrix:
        # Weighted portfolio return
        weights = np.array([v / total_value for v in values if total_value > 0])
        syms_with_returns = [s for s in symbols if s in all_returns]
        if len(syms_with_returns) == len(weights):
            min_len = min(len(all_returns[s]) for s in syms_with_returns)
            ret_matrix = np.column_stack([all_returns[s][-min_len:] for s in syms_with_returns])
            port_returns = ret_matrix @ weights[:len(syms_with_returns)]

            port_vol = float(np.std(port_returns)) * math.sqrt(252)
            sorted_port = np.sort(port_returns)
            p_var_95 = abs(float(np.percentile(sorted_port, 5))) * total_value
            p_var_99 = abs(float(np.percentile(sorted_port, 1))) * total_value
            tail = sorted_port[sorted_port <= np.percentile(sorted_port, 5)]
            p_cvar = abs(float(np.mean(tail))) * total_value if len(tail) > 0 else p_var_95 * 1.2
        else:
            # Fallback: sum of individual VaRs (conservative)
            p_var_95 = sum(v.var_95 for v in holding_vars)
            p_var_99 = sum(v.var_99 for v in holding_vars)
            p_cvar = sum(v.cvar_95 for v in holding_vars)
            port_vol = sum(v.volatility * (values[i] / total_value)
                          for i, v in enumerate(holding_vars)) / 100
    else:
        p_var_95 = sum(v.var_95 for v in holding_vars)
        p_var_99 = sum(v.var_99 for v in holding_vars)
        p_cvar = sum(v.cvar_95 for v in holding_vars)
        port_vol = sum(v.volatility * (values[i] / total_value)
                      for i, v in enumerate(holding_vars)) / 100 if holding_vars else 0

    # Concentration analysis
    top_conc = sorted(
        [{"symbol": h["symbol"], "pct": h["value"] / total_value * 100} for h in holdings],
        key=lambda x: -x["pct"],
    )

    # HHI (0 = perfectly diversified, 1 = single stock)
    hhi = sum((v / total_value) ** 2 for v in values) if total_value > 0 else 0
    conc_risk = "HIGH" if hhi > 0.25 else "MEDIUM" if hhi > 0.15 else "LOW"

    return PortfolioRiskReport(
        portfolio_value=round(total_value, 2),
        portfolio_var_95=round(p_var_95, 2),
        portfolio_var_99=round(p_var_99, 2),
        portfolio_cvar_95=round(p_cvar, 2),
        portfolio_volatility=round(port_vol * 100 if port_vol < 1 else port_vol, 1),
        holding_vars=holding_vars,
        correlation_matrix=corr_matrix or None,
        high_correlations=high_corrs,
        top_concentration=top_conc,
        hhi=round(hhi, 3),
        concentration_risk=conc_risk,
    )


# ── Helpers ──────────────────────────────────────────────────

def _get_daily_returns(symbol: str, days: int = 252) -> Optional[np.ndarray]:
    """Fetch daily returns from yfinance."""
    try:
        from market.yfinance_provider import yf_get_ohlcv
        data = yf_get_ohlcv(symbol, period="1y")
        if not data or len(data) < 30:
            return None
        closes = np.array([d["close"] for d in data if d["close"] and d["close"] > 0])
        returns = np.diff(closes) / closes[:-1]
        return returns
    except Exception:
        return None


def _get_holdings() -> list[dict]:
    """Get current holdings from broker or return empty list."""
    try:
        from brokers.session import get_broker
        broker = get_broker()
        holdings = broker.get_holdings()
        return [
            {"symbol": h.symbol, "value": h.last_price * h.quantity, "qty": h.quantity}
            for h in holdings if h.quantity > 0
        ]
    except Exception:
        return []


def print_risk_report() -> None:
    """Display full portfolio risk report."""
    report = compute_portfolio_risk()
    report.print_report()
