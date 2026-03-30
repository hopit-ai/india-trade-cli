"""
engine/portfolio.py
───────────────────
Portfolio tracker — unified live view of holdings + positions + Greeks.

Provides:
  get_portfolio_summary()        → single-broker full P&L snapshot
  get_multi_broker_summary()     → aggregated view across all connected brokers
  get_position_greeks()          → net Delta, Theta, Vega across all F&O positions
  risk_meter()                   → capital deployed %, max loss, R:R

Works with any BrokerAPI implementation (real or paper).
Multi-broker mode aggregates holdings, positions, and funds from all
simultaneously connected brokers (e.g. Zerodha + Groww).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing      import Optional
import re

from brokers.session import get_broker
from brokers.base    import Holding, Position, Funds


# ── Result dataclasses ────────────────────────────────────────

@dataclass
class HoldingRow:
    symbol:     str
    qty:        int
    avg_price:  float
    ltp:        float
    value:      float
    pnl:        float
    pnl_pct:    float
    product:    str
    broker:     str = ""    # e.g. "zerodha" | "groww" | "mock"


@dataclass
class PositionRow:
    symbol:     str
    qty:        int
    avg_price:  float
    ltp:        float
    pnl:        float
    product:    str
    # Greeks (None for non-options)
    delta:      Optional[float] = None
    theta:      Optional[float] = None
    vega:       Optional[float] = None
    broker:     str = ""    # e.g. "zerodha" | "groww" | "mock"


@dataclass
class PortfolioGreeks:
    net_delta:  float = 0.0    # sum of position delta × qty
    net_theta:  float = 0.0    # daily theta decay in INR
    net_vega:   float = 0.0    # vega exposure for 1% IV move
    net_gamma:  float = 0.0    # gamma exposure
    positions_with_greeks: list[dict] = field(default_factory=list)
    by_underlying: dict = field(default_factory=dict)  # Greeks grouped by underlying


@dataclass
class RiskMeter:
    total_capital:     float
    deployed_cash:     float    # CNC holdings value
    used_margin:       float    # F&O / intraday margin
    free_cash:         float
    deployment_pct:    float    # % of capital deployed
    unrealised_pnl:    float    # total open P&L
    max_loss_estimate: float    # worst-case loss (holdings to zero + margin lost)
    risk_rating:       str      # LOW / MEDIUM / HIGH / DANGER


@dataclass
class PortfolioSummary:
    holdings:        list[HoldingRow]
    positions:       list[PositionRow]
    funds:           object          # Funds dataclass from broker (or aggregate)
    greeks:          PortfolioGreeks
    risk:            RiskMeter
    total_value:     float
    total_pnl:       float
    day_pnl:         float           # approximate — positions P&L
    multi_broker:    bool = False    # True when aggregated from multiple brokers
    brokers:         list[str] = field(default_factory=list)  # names of contributing brokers


# ── Main entry points ─────────────────────────────────────────

def get_portfolio_summary() -> PortfolioSummary:
    """
    Full live portfolio snapshot from the primary broker.
    Fetches holdings, positions, funds, computes Greeks for options positions.
    """
    broker   = get_broker()
    funds    = broker.get_funds()
    holdings = broker.get_holdings()
    positions= broker.get_positions()

    # Determine broker name from profile
    try:
        broker_name = broker.get_profile().broker.lower()
    except Exception:
        broker_name = ""

    holding_rows  = _build_holding_rows(holdings, broker_name=broker_name)
    position_rows = _build_position_rows(positions, broker_name=broker_name)
    greeks        = _compute_net_greeks(position_rows)
    risk          = _compute_risk(funds, holding_rows, position_rows)

    total_value = funds.total_balance
    total_pnl   = sum(r.pnl for r in holding_rows) + sum(r.pnl for r in position_rows)
    day_pnl     = sum(r.pnl for r in position_rows)

    return PortfolioSummary(
        holdings     = holding_rows,
        positions    = position_rows,
        funds        = funds,
        greeks       = greeks,
        risk         = risk,
        total_value  = round(total_value, 2),
        total_pnl    = round(total_pnl, 2),
        day_pnl      = round(day_pnl, 2),
        multi_broker = False,
        brokers      = [broker_name] if broker_name else [],
    )


def get_multi_broker_summary() -> PortfolioSummary:
    """
    Aggregate portfolio from ALL connected brokers (e.g. Zerodha + Groww).

    Holdings, positions, and Greeks are combined into a single view.
    Each row carries a `broker` field so the caller can still separate them.
    Funds (cash, margin, balance) are summed across all brokers.

    Falls back to get_portfolio_summary() if only one broker is connected.
    """
    from brokers.session import get_all_brokers, is_multi_broker

    all_brokers = get_all_brokers()

    if not all_brokers:
        raise RuntimeError("No brokers connected. Run login() first.")

    if len(all_brokers) == 1:
        return get_portfolio_summary()

    all_holding_rows:  list[HoldingRow]  = []
    all_position_rows: list[PositionRow] = []
    total_cash    = 0.0
    total_margin  = 0.0
    total_balance = 0.0
    connected_brokers: list[str] = []
    errors: list[str] = []

    for broker_key, broker in all_brokers.items():
        try:
            profile = broker.get_profile()
            broker_name = profile.broker.lower()
        except Exception:
            broker_name = broker_key

        connected_brokers.append(broker_name)

        try:
            funds = broker.get_funds()
            total_cash    += funds.available_cash
            total_margin  += funds.used_margin
            total_balance += funds.total_balance
        except Exception as e:
            errors.append(f"{broker_name}: funds error — {e}")

        try:
            holdings  = broker.get_holdings()
            h_rows    = _build_holding_rows(holdings, broker_name=broker_name)
            all_holding_rows.extend(h_rows)
        except Exception as e:
            errors.append(f"{broker_name}: holdings error — {e}")

        try:
            positions = broker.get_positions()
            p_rows    = _build_position_rows(positions, broker_name=broker_name)
            all_position_rows.extend(p_rows)
        except Exception as e:
            errors.append(f"{broker_name}: positions error — {e}")

    # Build synthetic aggregate Funds object
    agg_funds = Funds(
        available_cash = total_cash,
        used_margin    = total_margin,
        total_balance  = total_balance,
    )

    greeks    = _compute_net_greeks(all_position_rows)
    risk      = _compute_risk(agg_funds, all_holding_rows, all_position_rows)
    total_pnl = (
        sum(r.pnl for r in all_holding_rows)
        + sum(r.pnl for r in all_position_rows)
    )
    day_pnl = sum(r.pnl for r in all_position_rows)

    return PortfolioSummary(
        holdings     = all_holding_rows,
        positions    = all_position_rows,
        funds        = agg_funds,
        greeks       = greeks,
        risk         = risk,
        total_value  = round(total_balance, 2),
        total_pnl    = round(total_pnl, 2),
        day_pnl      = round(day_pnl, 2),
        multi_broker = True,
        brokers      = connected_brokers,
    )


def get_position_greeks() -> PortfolioGreeks:
    """Compute net Greeks across all F&O positions (primary broker)."""
    broker    = get_broker()
    positions = broker.get_positions()
    rows      = _build_position_rows(positions)
    return _compute_net_greeks(rows)


def risk_meter() -> RiskMeter:
    """Capital deployment and risk assessment (primary broker)."""
    broker    = get_broker()
    funds     = broker.get_funds()
    holdings  = broker.get_holdings()
    positions = broker.get_positions()

    h_rows = _build_holding_rows(holdings)
    p_rows = _build_position_rows(positions)
    return _compute_risk(funds, h_rows, p_rows)


# ── Internal builders ─────────────────────────────────────────

def _build_holding_rows(
    holdings: list[Holding],
    broker_name: str = "",
) -> list[HoldingRow]:
    return [
        HoldingRow(
            symbol    = h.symbol,
            qty       = h.quantity,
            avg_price = h.avg_price,
            ltp       = h.last_price,
            value     = round(h.last_price * h.quantity, 2),
            pnl       = h.pnl,
            pnl_pct   = h.pnl_pct,
            product   = "CNC",          # Holdings are always CNC delivery
            broker    = broker_name,
        )
        for h in holdings
    ]


def _build_position_rows(
    positions: list[Position],
    broker_name: str = "",
) -> list[PositionRow]:
    """Build position rows and attach Greeks for options contracts."""
    rows = []
    for p in positions:
        delta = theta = vega = None

        # Try to compute Greeks for options positions
        # Options symbol pattern: underlying + expiry + type + strike (e.g. NIFTY2451523000CE)
        parsed = _parse_option_symbol(p.symbol)
        if parsed:
            try:
                from analysis.options import compute_greeks
                from market.quotes    import get_ltp
                spot = get_ltp(f"NSE:{parsed['underlying']}")
                g = compute_greeks(
                    spot        = spot,
                    strike      = parsed["strike"],
                    expiry      = parsed["expiry"],
                    option_type = parsed["option_type"],
                    ltp         = p.last_price,
                )
                delta = g.delta * p.quantity
                theta = g.theta * p.quantity
                vega  = g.vega  * p.quantity
            except Exception:
                pass

        rows.append(PositionRow(
            symbol    = p.symbol,
            qty       = p.quantity,
            avg_price = p.avg_price,
            ltp       = p.last_price,
            pnl       = p.pnl,
            product   = p.product,
            delta     = round(delta, 4) if delta is not None else None,
            theta     = round(theta, 2) if theta is not None else None,
            vega      = round(vega, 2)  if vega  is not None else None,
            broker    = broker_name,
        ))
    return rows


def _parse_option_symbol(symbol: str) -> dict | None:
    """
    Parse NSE F&O symbol into components.
    Format: NIFTY25APR23000CE  or  RELIANCE25APR3200PE
    Returns {underlying, expiry, strike, option_type} or None.
    """
    # Pattern: letters (underlying) + 2-digit year + 3-letter month + strike + CE/PE
    m = re.match(
        r"^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$",
        symbol.upper(),
    )
    if not m:
        return None
    underlying, yy, mon_str, strike_str, opt_type = m.groups()
    month_map = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    }
    mon = month_map.get(mon_str)
    if not mon:
        return None
    # Use last Thursday of that month as approximate expiry
    return {
        "underlying":  underlying,
        "expiry":      f"20{yy}-{mon}-28",   # approximate; real expiry from chain
        "strike":      float(strike_str),
        "option_type": opt_type,
    }


def _compute_net_greeks(rows: list[PositionRow]) -> PortfolioGreeks:
    """Sum Greeks across all positions, grouped by underlying."""
    net_delta = 0.0
    net_theta = 0.0
    net_vega  = 0.0
    net_gamma = 0.0
    by_underlying: dict[str, dict] = {}

    with_greeks = []
    for r in rows:
        if not any(x is not None for x in (r.delta, r.theta, r.vega)):
            continue

        d = r.delta or 0.0
        t = r.theta or 0.0
        v = r.vega or 0.0
        g = getattr(r, 'gamma', None) or 0.0

        net_delta += d
        net_theta += t
        net_vega += v
        net_gamma += g

        # Group by underlying
        parsed = _parse_option_symbol(r.symbol)
        underlying = parsed["underlying"] if parsed else r.symbol
        if underlying not in by_underlying:
            by_underlying[underlying] = {"delta": 0.0, "theta": 0.0, "vega": 0.0, "gamma": 0.0, "positions": 0}
        by_underlying[underlying]["delta"] += d
        by_underlying[underlying]["theta"] += t
        by_underlying[underlying]["vega"] += v
        by_underlying[underlying]["gamma"] += g
        by_underlying[underlying]["positions"] += 1

        with_greeks.append({
            "symbol": r.symbol,
            "qty":    r.qty,
            "delta":  r.delta,
            "theta":  r.theta,
            "vega":   r.vega,
            "underlying": underlying,
            "broker": r.broker,
        })

    # Round the by_underlying values
    for u in by_underlying:
        for k in ("delta", "theta", "vega", "gamma"):
            by_underlying[u][k] = round(by_underlying[u][k], 4)

    return PortfolioGreeks(
        net_delta             = round(net_delta, 4),
        net_theta             = round(net_theta, 2),
        net_vega              = round(net_vega, 2),
        net_gamma             = round(net_gamma, 4),
        positions_with_greeks = with_greeks,
        by_underlying         = by_underlying,
    )


def _compute_risk(
    funds,
    holding_rows: list[HoldingRow],
    position_rows: list[PositionRow],
) -> RiskMeter:
    """Assess portfolio risk level."""
    deployed_cash = sum(r.value for r in holding_rows)
    used_margin   = funds.used_margin
    free_cash     = funds.available_cash
    total_capital = funds.total_balance

    deployment_pct = (
        (deployed_cash + used_margin) / total_capital * 100
        if total_capital > 0 else 0.0
    )

    unrealised_pnl = (
        sum(r.pnl for r in holding_rows)
        + sum(r.pnl for r in position_rows)
    )

    # Worst-case max loss: holdings lose 30% + all margin wiped
    max_loss_estimate = deployed_cash * 0.30 + used_margin

    if deployment_pct >= 90 or max_loss_estimate > total_capital * 0.20:
        rating = "DANGER"
    elif deployment_pct >= 70 or max_loss_estimate > total_capital * 0.10:
        rating = "HIGH"
    elif deployment_pct >= 50:
        rating = "MEDIUM"
    else:
        rating = "LOW"

    return RiskMeter(
        total_capital      = round(total_capital, 2),
        deployed_cash      = round(deployed_cash, 2),
        used_margin        = round(used_margin, 2),
        free_cash          = round(free_cash, 2),
        deployment_pct     = round(deployment_pct, 1),
        unrealised_pnl     = round(unrealised_pnl, 2),
        max_loss_estimate  = round(max_loss_estimate, 2),
        risk_rating        = rating,
    )


# ── Display functions ────────────────────────────────────────

def print_portfolio_greeks() -> None:
    """Display aggregated portfolio Greeks as a Rich table."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    try:
        greeks = get_position_greeks()
    except Exception as e:
        console.print(f"[red]Could not compute Greeks: {e}[/red]")
        return

    if not greeks.positions_with_greeks:
        console.print("[dim]No F&O positions with Greeks found.[/dim]")
        return

    # Net Greeks summary
    delta_style = "green" if greeks.net_delta >= 0 else "red"
    theta_style = "red" if greeks.net_theta < 0 else "green"

    lines = [
        f"  [bold]Net Portfolio Greeks[/bold]",
        f"  Delta : [{delta_style}]{greeks.net_delta:+.2f}[/{delta_style}]"
        f"  {'(net long)' if greeks.net_delta > 0 else '(net short)' if greeks.net_delta < 0 else '(delta neutral)'}",
        f"  Gamma : {greeks.net_gamma:+.4f}",
        f"  Theta : [{theta_style}]{greeks.net_theta:+.2f}[/{theta_style}] /day",
        f"  Vega  : {greeks.net_vega:+.2f}",
    ]

    console.print(Panel("\n".join(lines), title="[bold cyan]Portfolio Greeks[/bold cyan]", border_style="cyan"))

    # By underlying
    if greeks.by_underlying:
        table = Table(title="Greeks by Underlying", show_lines=False)
        table.add_column("Underlying", style="bold", width=14)
        table.add_column("Positions", justify="right", width=10)
        table.add_column("Delta", justify="right", width=10)
        table.add_column("Theta", justify="right", width=10)
        table.add_column("Vega", justify="right", width=10)

        for underlying, g in greeks.by_underlying.items():
            d_style = "green" if g["delta"] >= 0 else "red"
            t_style = "red" if g["theta"] < 0 else "green"
            table.add_row(
                underlying,
                str(g["positions"]),
                f"[{d_style}]{g['delta']:+.2f}[/{d_style}]",
                f"[{t_style}]{g['theta']:+.2f}[/{t_style}]",
                f"{g['vega']:+.2f}",
            )

        console.print(table)

    # Per-position detail
    table2 = Table(title="Position Greeks Detail", show_lines=False)
    table2.add_column("Symbol", style="bold", width=22)
    table2.add_column("Qty", justify="right", width=8)
    table2.add_column("Delta", justify="right", width=10)
    table2.add_column("Theta", justify="right", width=10)
    table2.add_column("Vega", justify="right", width=10)

    for p in greeks.positions_with_greeks:
        d = p.get("delta", 0) or 0
        t = p.get("theta", 0) or 0
        v = p.get("vega", 0) or 0
        d_style = "green" if d >= 0 else "red"
        table2.add_row(
            p["symbol"],
            str(p["qty"]),
            f"[{d_style}]{d:+.4f}[/{d_style}]",
            f"{t:+.2f}",
            f"{v:+.2f}",
        )

    console.print(table2)
