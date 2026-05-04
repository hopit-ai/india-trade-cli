"""
engine/simulator.py
───────────────────
What-If Portfolio Simulator — stress test your portfolio against scenarios.

"If NIFTY drops 3% tomorrow, what happens to my portfolio?"
"What if VIX spikes to 25?"
"What's my max loss if RELIANCE drops 10%?"

Uses current holdings/positions + Greeks (for F&O) to project P&L.

Usage:
    from engine.simulator import Simulator

    sim = Simulator()
    result = sim.scenario_market_move(nifty_change_pct=-3.0)
    result = sim.scenario_stock_move("RELIANCE", change_pct=-10.0)
    result = sim.scenario_vix_spike(new_vix=25.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class ScenarioResult:
    """Output of a what-if simulation."""

    scenario_name: str
    description: str

    # Portfolio impact
    current_value: float = 0.0
    projected_value: float = 0.0
    projected_pnl: float = 0.0
    projected_pnl_pct: float = 0.0

    # Per-holding breakdown
    impacts: list[dict] = field(default_factory=list)

    def print_summary(self) -> None:
        pnl_style = "green" if self.projected_pnl >= 0 else "red"
        lines = [
            f"  Scenario     : [bold]{self.scenario_name}[/bold]",
            f"  {self.description}",
            "",
            f"  Current Value  : [white]{self.current_value:,.0f}[/white]",
            f"  Projected      : [{pnl_style}]{self.projected_value:,.0f}[/{pnl_style}]",
            f"  Impact         : [{pnl_style}]{self.projected_pnl:+,.0f} ({self.projected_pnl_pct:+.2f}%)[/{pnl_style}]",
        ]

        console.print(
            Panel(
                "\n".join(lines),
                title="[bold yellow]What-If Scenario[/bold yellow]",
                border_style="yellow",
            )
        )

        if self.impacts:
            table = Table(title="Position-wise Impact", show_lines=False)
            table.add_column("Symbol", style="bold", width=14)
            table.add_column("Qty", justify="right", width=8)
            table.add_column("Current", justify="right", width=10)
            table.add_column("Projected", justify="right", width=10)
            table.add_column("P&L", justify="right", width=12)

            for imp in self.impacts:
                pnl = imp.get("pnl", 0)
                style = "green" if pnl >= 0 else "red"
                table.add_row(
                    imp.get("symbol", ""),
                    str(imp.get("quantity", 0)),
                    f"{imp.get('current_price', 0):,.1f}",
                    f"{imp.get('projected_price', 0):,.1f}",
                    f"[{style}]{pnl:+,.0f}[/{style}]",
                )
            console.print(table)


class Simulator:
    """Portfolio stress testing and what-if analysis."""

    def __init__(self) -> None:
        self._holdings = []
        self._positions = []
        self._loaded = False
        self._beta_cache: dict[str, float] = {}

    def _load_portfolio(self) -> None:
        """Load current holdings and positions from broker."""
        if self._loaded:
            return
        try:
            from brokers.session import get_execution_broker

            broker = get_execution_broker()
            self._holdings = broker.get_holdings()
            self._positions = broker.get_positions()
        except Exception:
            self._holdings = []
            self._positions = []
        self._loaded = True

    def _get_beta(self, symbol: str) -> float:
        """
        Calculate stock beta relative to NIFTY 50 from historical data.
        Beta = covariance(stock, NIFTY) / variance(NIFTY)
        Uses 1 year of daily returns. Caches results.
        """
        if symbol in self._beta_cache:
            return self._beta_cache[symbol]

        try:
            from market.yfinance_provider import yf_get_ohlcv
            import numpy as np

            stock_data = yf_get_ohlcv(symbol, period="1y")
            nifty_data = yf_get_ohlcv("NIFTY 50", period="1y")

            if not stock_data or not nifty_data or len(stock_data) < 30:
                self._beta_cache[symbol] = 1.0
                return 1.0

            # Align by date
            stock_closes = {str(d["date"])[:10]: d["close"] for d in stock_data}
            nifty_closes = {str(d["date"])[:10]: d["close"] for d in nifty_data}

            common_dates = sorted(set(stock_closes) & set(nifty_closes))
            if len(common_dates) < 30:
                self._beta_cache[symbol] = 1.0
                return 1.0

            s_prices = [stock_closes[d] for d in common_dates]
            n_prices = [nifty_closes[d] for d in common_dates]

            s_returns = np.diff(s_prices) / s_prices[:-1]
            n_returns = np.diff(n_prices) / n_prices[:-1]

            cov = np.cov(s_returns, n_returns)[0][1]
            var = np.var(n_returns)
            beta = float(cov / var) if var > 0 else 1.0

            # Clamp to reasonable range
            beta = max(0.1, min(beta, 3.0))
            self._beta_cache[symbol] = round(beta, 2)
            return self._beta_cache[symbol]
        except Exception:
            self._beta_cache[symbol] = 1.0
            return 1.0

    def scenario_market_move(self, nifty_change_pct: float) -> ScenarioResult:
        """
        Simulate a broad market move.
        Each stock moves by NIFTY change * its beta (calculated from historical data).
        """
        self._load_portfolio()
        change = nifty_change_pct / 100

        impacts = []
        current_total = 0.0
        projected_total = 0.0

        for h in self._holdings:
            current_val = h.last_price * h.quantity
            beta = self._get_beta(h.symbol)
            projected_price = h.last_price * (1 + change * beta)
            projected_val = projected_price * h.quantity
            pnl = projected_val - current_val

            current_total += current_val
            projected_total += projected_val

            impacts.append(
                {
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "current_price": h.last_price,
                    "projected_price": round(projected_price, 2),
                    "pnl": round(pnl, 2),
                    "beta": beta,
                }
            )

        for p in self._positions:
            current_val = p.last_price * abs(p.quantity)
            multiplier = 1 if p.quantity > 0 else -1
            projected_price = p.last_price * (1 + change * multiplier)
            projected_val = projected_price * abs(p.quantity)
            pnl = (projected_val - current_val) * multiplier

            current_total += current_val * multiplier
            projected_total += projected_val * multiplier

            impacts.append(
                {
                    "symbol": f"{p.symbol} ({p.product})",
                    "quantity": p.quantity,
                    "current_price": p.last_price,
                    "projected_price": round(projected_price, 2),
                    "pnl": round(pnl, 2),
                }
            )

        projected_pnl = projected_total - current_total
        pnl_pct = (projected_pnl / current_total * 100) if current_total else 0

        direction = "drops" if nifty_change_pct < 0 else "rallies"
        return ScenarioResult(
            scenario_name=f"NIFTY {direction} {abs(nifty_change_pct):.1f}%",
            description=f"All positions move proportionally to a {nifty_change_pct:+.1f}% NIFTY move.",
            current_value=round(current_total, 2),
            projected_value=round(projected_total, 2),
            projected_pnl=round(projected_pnl, 2),
            projected_pnl_pct=round(pnl_pct, 2),
            impacts=impacts,
        )

    def scenario_stock_move(self, symbol: str, change_pct: float) -> ScenarioResult:
        """Simulate a single stock moving by a given percentage."""
        self._load_portfolio()
        symbol = symbol.upper()
        change = change_pct / 100

        impacts = []
        current_total = 0.0
        projected_total = 0.0

        all_positions = []
        for h in self._holdings:
            all_positions.append(
                {
                    "symbol": h.symbol,
                    "qty": h.quantity,
                    "price": h.last_price,
                    "label": h.symbol,
                }
            )
        for p in self._positions:
            all_positions.append(
                {
                    "symbol": p.symbol,
                    "qty": p.quantity,
                    "price": p.last_price,
                    "label": f"{p.symbol} ({p.product})",
                }
            )

        for pos in all_positions:
            current_val = pos["price"] * abs(pos["qty"])
            is_target = symbol in pos["symbol"].upper()

            if is_target:
                projected_price = pos["price"] * (1 + change)
            else:
                projected_price = pos["price"]

            projected_val = projected_price * abs(pos["qty"])
            multiplier = 1 if pos["qty"] > 0 else -1
            pnl = (projected_val - current_val) * multiplier

            current_total += current_val * multiplier
            projected_total += projected_val * multiplier

            if is_target or pnl != 0:
                impacts.append(
                    {
                        "symbol": pos["label"],
                        "quantity": pos["qty"],
                        "current_price": pos["price"],
                        "projected_price": round(projected_price, 2),
                        "pnl": round(pnl, 2),
                    }
                )

        projected_pnl = projected_total - current_total
        pnl_pct = (projected_pnl / current_total * 100) if current_total else 0

        direction = "drops" if change_pct < 0 else "rallies"
        return ScenarioResult(
            scenario_name=f"{symbol} {direction} {abs(change_pct):.1f}%",
            description=f"Only {symbol} moves by {change_pct:+.1f}%. Other positions unchanged.",
            current_value=round(current_total, 2),
            projected_value=round(projected_total, 2),
            projected_pnl=round(projected_pnl, 2),
            projected_pnl_pct=round(pnl_pct, 2),
            impacts=impacts,
        )

    def scenario_custom(self, moves: dict[str, float]) -> ScenarioResult:
        """
        Custom scenario with multiple stocks moving differently.
        moves: {"RELIANCE": -5.0, "HDFCBANK": 3.0, "TCS": -2.0}
        """
        self._load_portfolio()

        impacts = []
        current_total = 0.0
        projected_total = 0.0

        all_positions = []
        for h in self._holdings:
            all_positions.append(
                {
                    "symbol": h.symbol,
                    "qty": h.quantity,
                    "price": h.last_price,
                    "label": h.symbol,
                }
            )
        for p in self._positions:
            all_positions.append(
                {
                    "symbol": p.symbol,
                    "qty": p.quantity,
                    "price": p.last_price,
                    "label": f"{p.symbol} ({p.product})",
                }
            )

        for pos in all_positions:
            current_val = pos["price"] * abs(pos["qty"])
            change_pct = 0.0

            for sym, pct in moves.items():
                if sym.upper() in pos["symbol"].upper():
                    change_pct = pct
                    break

            projected_price = pos["price"] * (1 + change_pct / 100)
            projected_val = projected_price * abs(pos["qty"])
            multiplier = 1 if pos["qty"] > 0 else -1
            pnl = (projected_val - current_val) * multiplier

            current_total += current_val * multiplier
            projected_total += projected_val * multiplier

            if change_pct != 0:
                impacts.append(
                    {
                        "symbol": pos["label"],
                        "quantity": pos["qty"],
                        "current_price": pos["price"],
                        "projected_price": round(projected_price, 2),
                        "pnl": round(pnl, 2),
                    }
                )

        projected_pnl = projected_total - current_total
        pnl_pct = (projected_pnl / current_total * 100) if current_total else 0

        move_desc = ", ".join(f"{s} {p:+.1f}%" for s, p in moves.items())
        return ScenarioResult(
            scenario_name="Custom Scenario",
            description=f"Moves: {move_desc}",
            current_value=round(current_total, 2),
            projected_value=round(projected_total, 2),
            projected_pnl=round(projected_pnl, 2),
            projected_pnl_pct=round(pnl_pct, 2),
            impacts=impacts,
        )
