"""
analysis/dcf.py
───────────────
Discounted Cash Flow (DCF) valuation model.

Computes intrinsic value per share using a 2-stage DCF:
  Stage 1: High-growth period (5 years, user-specified growth rate)
  Stage 2: Terminal value (Gordon Growth Model with terminal_growth rate)

The growth rate is the key assumption — the LLM analyst picks it
based on sector, competitive position, and management guidance.

Usage:
    dcf RELIANCE
    dcf RELIANCE --growth 15 --wacc 12
    ai what is the DCF valuation of TCS?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def _is_nan_val(val) -> bool:
    """Check if a value is NaN."""
    try:
        import math
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


# ── India-specific defaults ──────────────────────────────────

RISK_FREE_RATE = 7.0    # India 10Y G-Sec yield (%)
EQUITY_RISK_PREMIUM = 6.5  # India ERP (%)
TERMINAL_GROWTH = 4.0   # Nominal GDP growth (%)
CORPORATE_TAX = 25.17   # India corporate tax rate (%)
COST_OF_DEBT = 9.0      # Average corporate borrowing rate (%)
PROJECTION_YEARS = 5


# ── WACC ─────────────────────────────────────────────────────

def compute_wacc(
    beta: float,
    debt_equity: float = 0.0,
    risk_free: float = RISK_FREE_RATE,
    erp: float = EQUITY_RISK_PREMIUM,
    cost_of_debt: float = COST_OF_DEBT,
    tax_rate: float = CORPORATE_TAX,
) -> float:
    """
    Weighted Average Cost of Capital.

    WACC = Ke × (E/(E+D)) + Kd × (1-t) × (D/(E+D))
    where Ke = Rf + Beta × ERP
    """
    cost_of_equity = risk_free + beta * erp

    if debt_equity <= 0:
        return cost_of_equity

    # Weight of equity and debt
    equity_weight = 1 / (1 + debt_equity)
    debt_weight = debt_equity / (1 + debt_equity)

    after_tax_debt = cost_of_debt * (1 - tax_rate / 100)

    return cost_of_equity * equity_weight + after_tax_debt * debt_weight


# ── DCF Model ────────────────────────────────────────────────

@dataclass
class DCFResult:
    intrinsic_value:  float     # per share
    enterprise_value: float     # total (crores)
    equity_value:     float     # total (crores)
    margin_of_safety: float     # % (positive = undervalued)
    current_price:    float
    wacc:            float
    growth_rate:     float
    terminal_growth: float
    fcf_projections: list[dict]  # [{year, fcf, pv}]
    terminal_value:  float
    sensitivity:     list[dict]  # [{growth, wacc, intrinsic_value}]


def compute_dcf(
    fcf_cr: float,
    growth_rate: float,
    wacc: float,
    shares_outstanding: int,
    net_debt_cr: float = 0.0,
    terminal_growth: float = TERMINAL_GROWTH,
    current_price: float = 0.0,
    projection_years: int = PROJECTION_YEARS,
) -> DCFResult:
    """
    2-stage DCF valuation.

    Args:
        fcf_cr: current free cash flow in crores
        growth_rate: expected FCF growth rate (%)
        wacc: weighted average cost of capital (%)
        shares_outstanding: total shares
        net_debt_cr: net debt (total debt - cash) in crores
        terminal_growth: perpetual growth rate (%)
        current_price: current share price (for margin of safety)
        projection_years: years of high growth

    Returns:
        DCFResult with intrinsic value, sensitivity, projections.
    """
    if fcf_cr <= 0:
        return DCFResult(
            intrinsic_value=0, enterprise_value=0, equity_value=0,
            margin_of_safety=-100 if current_price > 0 else 0,
            current_price=current_price, wacc=wacc, growth_rate=growth_rate,
            terminal_growth=terminal_growth, fcf_projections=[],
            terminal_value=0, sensitivity=[],
        )

    wacc_dec = wacc / 100
    growth_dec = growth_rate / 100
    term_dec = terminal_growth / 100

    # Stage 1: Project FCFs
    projections = []
    pv_fcfs = 0.0
    fcf = fcf_cr
    for year in range(1, projection_years + 1):
        fcf = fcf * (1 + growth_dec)
        pv = fcf / (1 + wacc_dec) ** year
        pv_fcfs += pv
        projections.append({"year": year, "fcf": round(fcf, 1), "pv": round(pv, 1)})

    # Stage 2: Terminal value
    if wacc_dec > term_dec:
        terminal_fcf = fcf * (1 + term_dec)
        terminal_value = terminal_fcf / (wacc_dec - term_dec)
        pv_terminal = terminal_value / (1 + wacc_dec) ** projection_years
    else:
        terminal_value = 0
        pv_terminal = 0

    # Enterprise value
    enterprise_value = pv_fcfs + pv_terminal

    # Equity value
    equity_value = enterprise_value - net_debt_cr

    # Per share
    intrinsic_value = (equity_value * 1e7) / shares_outstanding if shares_outstanding > 0 else 0

    # Margin of safety
    margin = ((intrinsic_value - current_price) / current_price * 100) if current_price > 0 else 0

    # Sensitivity table: growth rate vs WACC
    sensitivity = []
    growth_range = [max(0, growth_rate - 10), max(0, growth_rate - 5), growth_rate,
                    growth_rate + 5, growth_rate + 10]
    wacc_range = [max(8, wacc - 2), wacc, wacc + 2, wacc + 4]

    for g in growth_range:
        for w in wacc_range:
            w_dec = w / 100
            g_dec = g / 100
            t_dec = term_dec
            if w_dec <= t_dec:
                continue
            pv = 0
            f = fcf_cr
            for y in range(1, projection_years + 1):
                f = f * (1 + g_dec)
                pv += f / (1 + w_dec) ** y
            tv = f * (1 + t_dec) / (w_dec - t_dec)
            pv += tv / (1 + w_dec) ** projection_years
            eq = pv - net_debt_cr
            iv = (eq * 1e7) / shares_outstanding if shares_outstanding > 0 else 0
            sensitivity.append({
                "growth": round(g, 1),
                "wacc": round(w, 1),
                "intrinsic_value": round(iv, 2),
            })

    return DCFResult(
        intrinsic_value=round(intrinsic_value, 2),
        enterprise_value=round(enterprise_value, 1),
        equity_value=round(equity_value, 1),
        margin_of_safety=round(margin, 1),
        current_price=current_price,
        wacc=wacc,
        growth_rate=growth_rate,
        terminal_growth=terminal_growth,
        fcf_projections=projections,
        terminal_value=round(terminal_value, 1),
        sensitivity=sensitivity,
    )


# ── Convenience: DCF from symbol ─────────────────────────────

def dcf_for_symbol(
    symbol: str,
    growth_rate: Optional[float] = None,
    wacc: Optional[float] = None,
) -> dict:
    """
    Compute DCF for a stock symbol using yfinance data.

    Auto-detects FCF, growth, beta, debt from yfinance.
    Returns dict with intrinsic_value, margin_of_safety, etc.
    """
    _INDEX_KEYWORDS = {"NIFTY", "BANKNIFTY", "SENSEX", "VIX", "FINNIFTY",
                       "MIDCAP", "NIFTY BANK", "NIFTY 50", "INDIA VIX"}
    if symbol.upper() in _INDEX_KEYWORDS:
        return {"error": f"{symbol} is an index — DCF requires company financials"}

    try:
        from analysis.fundamental import analyse

        snap = analyse(symbol)

        # Get FCF
        fcf = snap.free_cash_flow
        if not fcf or fcf <= 0:
            return {"error": f"No positive FCF available for {symbol} — DCF not applicable"}

        # Get shares outstanding from yfinance
        shares = None
        try:
            import yfinance as yf
            from market.yfinance_provider import _to_yf_symbol
            t = yf.Ticker(_to_yf_symbol(symbol))
            shares = t.info.get("sharesOutstanding")
        except Exception:
            pass

        if not shares:
            return {"error": f"Shares outstanding unavailable for {symbol}"}

        # Auto-detect growth rate — use best available forward estimate
        growth_source = "user-specified"
        if growth_rate is None:
            info = {}
            try:
                info = t.info if t else {}
            except Exception:
                pass

            # Collect all available growth signals
            trailing_pe = info.get("trailingPE")
            forward_pe = info.get("forwardPE")
            trailing_eps = info.get("trailingEps")
            forward_eps = info.get("forwardEps")
            revenue_growth = info.get("revenueGrowth")  # decimal

            candidates = []

            # 1. Analyst consensus growth estimates (best — forward-looking)
            try:
                ge = t.growth_estimates
                if ge is not None and not ge.empty:
                    # Current year estimate
                    cy = ge.loc["0y", "stockTrend"] if "0y" in ge.index else None
                    # Next year estimate
                    ny = ge.loc["+1y", "stockTrend"] if "+1y" in ge.index else None

                    if cy and not _is_nan_val(cy) and cy > 0.02:
                        cy_pct = round(float(cy) * 100, 1)
                        candidates.append((cy_pct, f"analyst consensus: current year EPS growth {cy_pct:.1f}% ({info.get('numberOfAnalystOpinions', '?')} analysts)"))
                    if ny and not _is_nan_val(ny) and ny > 0.02:
                        ny_pct = round(float(ny) * 100, 1)
                        candidates.append((ny_pct, f"analyst consensus: next year EPS growth {ny_pct:.1f}%"))
            except Exception:
                pass

            # 2. Forward EPS implied growth (from trailing vs forward EPS)
            if trailing_eps and forward_eps and trailing_eps > 0 and forward_eps > 0:
                implied = round((forward_eps / trailing_eps - 1) * 100, 1)
                if implied > 2:
                    candidates.append((implied, f"forward EPS ₹{forward_eps:.1f} vs trailing ₹{trailing_eps:.1f} = {implied:.1f}% implied"))

            # 3. Revenue growth (stable, hard to manipulate)
            if revenue_growth and revenue_growth > 0.02:
                rg_pct = round(revenue_growth * 100, 1)
                candidates.append((rg_pct, f"yfinance TTM revenue growth ({rg_pct:.1f}%)"))

            if candidates:
                # Pick the median candidate (not the most extreme)
                candidates.sort(key=lambda x: x[0])
                mid = len(candidates) // 2
                growth_rate = min(candidates[mid][0], 25.0)
                growth_source = candidates[mid][1]
                if len(candidates) > 1:
                    all_rates = [f"{c[0]:.0f}%" for c in candidates]
                    growth_source += f" [all signals: {', '.join(all_rates)}]"
            else:
                growth_rate = 10.0
                growth_source = "default 10% (no analyst estimates or growth data found)"

        # Compute WACC — floor beta at 0.5 for conglomerates with low reported beta
        raw_beta = snap.beta if snap.beta and snap.beta > 0 else 1.0
        beta = max(raw_beta, 0.5)  # beta < 0.5 is likely misleading for large-caps
        de = snap.debt_equity if snap.debt_equity and snap.debt_equity > 0 else 0.0
        computed_wacc = wacc or compute_wacc(beta=beta, debt_equity=de)

        # Net debt
        total_debt = snap.total_debt_cr or 0
        total_cash = snap.total_cash_cr or 0
        net_debt = total_debt - total_cash

        # Current price
        ltp = 0.0
        try:
            from market.quotes import get_ltp
            ltp = get_ltp(f"NSE:{symbol}")
        except Exception:
            pass

        result = compute_dcf(
            fcf_cr=fcf,
            growth_rate=growth_rate,
            wacc=computed_wacc,
            shares_outstanding=shares,
            net_debt_cr=net_debt,
            current_price=ltp,
        )

        # Track assumption sources for transparency
        sources = {
            "fcf": f"yfinance annual cash flow statement (TTM: ₹{fcf:,.0f} Cr)",
            "growth": growth_source,
            "beta": f"yfinance ({raw_beta:.2f}, floored to {beta:.2f})" if raw_beta < 0.5 else f"yfinance ({beta:.2f})",
            "wacc": f"CAPM: Rf {RISK_FREE_RATE}% + β {beta:.1f} × ERP {EQUITY_RISK_PREMIUM}% = Ke {RISK_FREE_RATE + beta * EQUITY_RISK_PREMIUM:.1f}%, D/E {de:.2f}",
            "net_debt": f"yfinance: total debt ₹{total_debt:,.0f} Cr - cash ₹{total_cash:,.0f} Cr",
            "terminal_growth": f"{TERMINAL_GROWTH}% (India nominal GDP growth assumption)",
            "shares": f"yfinance: {shares:,} shares outstanding",
        }

        # Commentary on assumptions
        commentary = []
        if growth_rate < 5:
            commentary.append(f"⚠ Growth rate {growth_rate:.1f}% is very low — may be using trailing data. Consider analyst estimates or revenue growth.")
        if growth_rate > 20:
            commentary.append(f"⚠ Growth rate {growth_rate:.1f}% is aggressive — sustainable for how long?")
        if beta < 0.5:
            commentary.append(f"⚠ Raw beta {raw_beta:.2f} is unusually low — floored to 0.5 for WACC. May understate risk.")
        if net_debt > fcf * 5:
            commentary.append(f"⚠ Net debt (₹{net_debt:,.0f} Cr) is {net_debt/fcf:.1f}× FCF — heavy leverage reduces equity value significantly.")
        if result.margin_of_safety < -50:
            commentary.append("⚠ Stock trades at >2× DCF value. Either market expects much higher growth or DCF assumptions are too conservative.")
        if result.margin_of_safety > 50:
            commentary.append("✓ Large margin of safety. But verify: is FCF sustainable? Any one-time items?")
        if computed_wacc - TERMINAL_GROWTH < 3:
            commentary.append(f"⚠ WACC ({computed_wacc:.1f}%) - terminal growth ({TERMINAL_GROWTH}%) = {computed_wacc - TERMINAL_GROWTH:.1f}% spread. Small spread makes terminal value very sensitive.")

        return {
            "symbol": symbol.upper(),
            "intrinsic_value": result.intrinsic_value,
            "current_price": result.current_price,
            "margin_of_safety": result.margin_of_safety,
            "verdict": "UNDERVALUED" if result.margin_of_safety > 15 else
                       "OVERVALUED" if result.margin_of_safety < -15 else "FAIRLY_VALUED",
            "enterprise_value_cr": result.enterprise_value,
            "wacc": result.wacc,
            "growth_rate": result.growth_rate,
            "terminal_growth": result.terminal_growth,
            "fcf_cr": fcf,
            "beta": beta,
            "raw_beta": raw_beta,
            "net_debt_cr": net_debt,
            "sensitivity": result.sensitivity,
            "sources": sources,
            "commentary": commentary,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Display ──────────────────────────────────────────────────

def print_dcf(symbol: str, growth_rate: Optional[float] = None, wacc: Optional[float] = None) -> None:
    """Display DCF valuation with sensitivity table."""
    data = dcf_for_symbol(symbol, growth_rate, wacc)

    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    iv = data["intrinsic_value"]
    cmp = data["current_price"]
    mos = data["margin_of_safety"]
    verdict = data["verdict"]

    verdict_color = {"UNDERVALUED": "green", "OVERVALUED": "red", "FAIRLY_VALUED": "yellow"}
    vc = verdict_color.get(verdict, "white")

    lines = [
        f"  [bold]Intrinsic Value: ₹{iv:,.2f}[/bold]  vs  CMP: ₹{cmp:,.2f}",
        f"  Margin of Safety: [{vc}]{mos:+.1f}%[/{vc}]  →  [{vc}][bold]{verdict}[/bold][/{vc}]",
        "",
        f"  [bold]Assumptions:[/bold]",
        f"  FCF:       ₹{data['fcf_cr']:,.0f} Cr",
        f"  Growth:    {data['growth_rate']:.1f}%",
        f"  WACC:      {data['wacc']:.1f}%",
        f"  Terminal:   {data['terminal_growth']:.1f}%",
        f"  Beta:      {data.get('beta', 1.0):.2f}",
        f"  Net Debt:  ₹{data['net_debt_cr']:,.0f} Cr",
    ]

    # Sources
    sources = data.get("sources", {})
    if sources:
        lines.append("")
        lines.append("  [bold]Data Sources:[/bold]")
        for key, src in sources.items():
            lines.append(f"  [dim]{key:12s} → {src}[/dim]")

    # Commentary / warnings
    commentary = data.get("commentary", [])
    if commentary:
        lines.append("")
        lines.append("  [bold]Commentary:[/bold]")
        for c in commentary:
            lines.append(f"  [yellow]{c}[/yellow]")

    console.print(Panel("\n".join(lines),
                        title=f"[bold cyan]DCF Valuation — {symbol}[/bold cyan]",
                        border_style="cyan"))

    # Sensitivity table
    if data.get("sensitivity"):
        table = Table(title="Sensitivity: Intrinsic Value (Growth × WACC)")

        # Get unique WACC values for columns
        wacc_vals = sorted(set(s["wacc"] for s in data["sensitivity"]))
        growth_vals = sorted(set(s["growth"] for s in data["sensitivity"]))

        table.add_column("Growth ↓ / WACC →", style="bold")
        for w in wacc_vals:
            table.add_column(f"{w:.0f}%", justify="right")

        lookup = {(s["growth"], s["wacc"]): s["intrinsic_value"] for s in data["sensitivity"]}

        for g in growth_vals:
            row = [f"{g:.0f}%"]
            for w in wacc_vals:
                val = lookup.get((g, w), 0)
                style = "green" if val > cmp * 1.15 else "red" if val < cmp * 0.85 else ""
                row.append(f"[{style}]₹{val:,.0f}[/{style}]" if style else f"₹{val:,.0f}")
            table.add_row(*row)

        console.print(table)
