"""
engine/options_backtest.py
──────────────────────────
Options-specific backtester — test straddles, iron condors, covered calls,
and protective puts on historical data.

Uses Black-Scholes to estimate option premiums from historical spot price
and India VIX (or realized volatility as IV proxy).

Usage:
    backtest NIFTY straddle --period 1y
    backtest NIFTY iron-condor --delta 0.20
    backtest NIFTY protective-put --period 2y
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from rich.console import Console
from rich.panel import Panel

console = Console()

RISK_FREE_RATE = 0.065  # 6.5% RBI repo rate


# ── Black-Scholes Premium ────────────────────────────────────


def bs_premium(
    spot: float,
    strike: float,
    dte: int,
    iv: float,
    option_type: str,
    rate: float = RISK_FREE_RATE,
) -> float:
    """
    Compute Black-Scholes option premium.

    Args:
        spot: current underlying price
        strike: option strike price
        dte: days to expiry (0 = expiry day)
        iv: implied volatility as decimal (e.g., 0.20 for 20%)
        option_type: "CE" or "PE"
        rate: risk-free rate

    Returns:
        Option premium (always >= 0).
    """
    if dte <= 0:
        # At expiry: intrinsic value only
        if option_type.upper() == "CE":
            return max(0.0, spot - strike)
        return max(0.0, strike - spot)

    if iv <= 0 or spot <= 0 or strike <= 0:
        return 0.0

    try:
        from scipy.stats import norm

        T = dte / 365.0
        d1 = (math.log(spot / strike) + (rate + 0.5 * iv**2) * T) / (iv * math.sqrt(T))
        d2 = d1 - iv * math.sqrt(T)

        if option_type.upper() == "CE":
            return max(0.0, spot * norm.cdf(d1) - strike * math.exp(-rate * T) * norm.cdf(d2))
        else:
            return max(0.0, strike * math.exp(-rate * T) * norm.cdf(-d2) - spot * norm.cdf(-d1))
    except Exception:
        # Fallback: intrinsic + rough time value
        if option_type.upper() == "CE":
            intrinsic = max(0.0, spot - strike)
        else:
            intrinsic = max(0.0, strike - spot)
        time_value = spot * iv * math.sqrt(dte / 365.0) * 0.4
        return intrinsic + time_value


# ── Data Models ──────────────────────────────────────────────


@dataclass
class OptionsLeg:
    """One leg of an options trade."""

    option_type: str  # "CE" or "PE"
    transaction: str  # "BUY" or "SELL"
    strike: float
    entry_premium: float
    exit_premium: float = 0.0
    lot_size: int = 1
    lots: int = 1
    pnl: float = 0.0


@dataclass
class OptionsTrade:
    """A complete options trade (entry + exit, potentially multi-leg)."""

    entry_date: str
    exit_date: str
    underlying_entry: float
    underlying_exit: float
    legs: list[OptionsLeg]
    combined_pnl: float
    combined_pnl_pct: float  # % return on margin/premium deployed
    hold_days: int
    strategy_name: str = ""


@dataclass
class OptionsBacktestResult:
    """Complete options backtest output."""

    underlying: str
    strategy_name: str
    period: str
    start_date: str
    end_date: str

    total_return: float = 0.0
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_hold_days: float = 0.0
    trades: list[OptionsTrade] = field(default_factory=list)

    def print_summary(self) -> None:
        ret_style = "green" if self.total_pnl >= 0 else "red"
        lines = [
            f"  Strategy       : [bold]{self.strategy_name}[/bold]",
            f"  Underlying     : {self.underlying}",
            f"  Period         : {self.start_date} → {self.end_date}",
            "",
            "  [bold]Returns[/bold]",
            f"  Total P&L      : [{ret_style}]₹{self.total_pnl:,.0f}[/{ret_style}]",
            f"  Total Return   : [{ret_style}]{self.total_return:+.2f}%[/{ret_style}]",
            "",
            "  [bold]Risk[/bold]",
            f"  Sharpe Ratio   : {self.sharpe_ratio:.2f}",
            f"  Max Drawdown   : [red]{self.max_drawdown:.2f}%[/red]",
            "",
            "  [bold]Trades[/bold]",
            f"  Total          : {self.total_trades}",
            f"  Win Rate       : {self.win_rate:.1f}%",
            f"  Avg Win        : [green]₹{self.avg_win:,.0f}[/green]",
            f"  Avg Loss       : [red]₹{self.avg_loss:,.0f}[/red]",
            f"  Avg Hold       : {self.avg_hold_days:.1f} days",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold cyan]Options Backtest: {self.strategy_name} on {self.underlying}[/bold cyan]",
                border_style="cyan",
            )
        )

    def print_trades(self, n: int = 20) -> None:
        trades = self.trades[-n:]
        if not trades:
            console.print("[dim]No trades executed.[/dim]")
            return

        for i, t in enumerate(trades, 1):
            pnl_style = "green" if t.combined_pnl >= 0 else "red"
            console.print(
                f"\n  [bold]Trade #{i}[/bold]: {t.entry_date} → {t.exit_date} "
                f"({t.hold_days}d)  "
                f"P&L: [{pnl_style}]₹{t.combined_pnl:,.0f} ({t.combined_pnl_pct:+.1f}%)[/{pnl_style}]"
            )
            console.print(f"    Underlying: ₹{t.underlying_entry:,.0f} → ₹{t.underlying_exit:,.0f}")
            for leg in t.legs:
                dir_color = "green" if leg.transaction == "BUY" else "red"
                leg_pnl_style = "green" if leg.pnl >= 0 else "red"
                console.print(
                    f"    [{dir_color}]{leg.transaction:4s}[/{dir_color}] "
                    f"{leg.option_type} {leg.strike:>8,.0f}  "
                    f"₹{leg.entry_premium:>7,.1f} → ₹{leg.exit_premium:>7,.1f}  "
                    f"[{leg_pnl_style}]₹{leg.pnl:>+8,.0f}[/{leg_pnl_style}]"
                )
        console.print()


# ── Options Strategy Interface ───────────────────────────────


class OptionsStrategy(ABC):
    """Base class for options-specific strategies."""

    name: str = "Base"

    @abstractmethod
    def should_enter(
        self,
        dt: date,
        spot: float,
        iv: float,
        dte: int,
        vix: float,
    ) -> Optional[list[dict]]:
        """
        Return list of legs to enter, or None to skip.

        Each leg dict: {
            "type": "CE" or "PE",
            "transaction": "BUY" or "SELL",
            "strike_offset": int  (0 = ATM, +100 = OTM call, -100 = OTM put)
        }
        """

    @abstractmethod
    def should_exit(
        self,
        dt: date,
        spot: float,
        iv: float,
        dte: int,
        entry_spot: float,
        days_held: int,
        unrealised_pnl: float,
    ) -> bool:
        """Return True to close all legs."""


# ── Built-in Strategies ──────────────────────────────────────


class StraddleStrategy(OptionsStrategy):
    """
    Buy ATM Straddle — long CE + long PE at same strike.

    Entry: N days before expiry.
    Exit: On expiry, or stop-loss/profit-target hit.
    """

    name = "Straddle"

    def __init__(
        self,
        entry_dte: int = 3,
        stop_loss_pct: float = 50.0,
        profit_target_pct: float = 100.0,
    ):
        self.entry_dte = entry_dte
        self.stop_loss_pct = stop_loss_pct
        self.profit_target_pct = profit_target_pct

    def should_enter(self, dt, spot, iv, dte, vix):
        if dte <= self.entry_dte and dte > 0:
            return [
                {"type": "CE", "transaction": "BUY", "strike_offset": 0},
                {"type": "PE", "transaction": "BUY", "strike_offset": 0},
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        if dte <= 0:
            return True
        if unrealised_pnl <= -self.stop_loss_pct:
            return True
        if unrealised_pnl >= self.profit_target_pct:
            return True
        return False


class IronCondorStrategy(OptionsStrategy):
    """
    Sell Iron Condor — sell OTM CE + PE, buy further OTM for protection.

    Entry: At start of series (DTE >= min_dte), VIX below threshold.
    Exit: On expiry, stop-loss, or profit target.
    """

    name = "Iron Condor"

    def __init__(
        self,
        short_offset: int = 200,
        wing_width: int = 100,
        min_dte: int = 3,
        max_dte: int = 8,
        max_vix: float = 25.0,
        stop_loss_pct: float = 100.0,
        profit_target_pct: float = 50.0,
    ):
        self.short_offset = short_offset
        self.wing_width = wing_width
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.max_vix = max_vix
        self.stop_loss_pct = stop_loss_pct
        self.profit_target_pct = profit_target_pct

    def should_enter(self, dt, spot, iv, dte, vix):
        if vix > self.max_vix:
            return None
        if self.min_dte <= dte <= self.max_dte:
            return [
                {"type": "CE", "transaction": "SELL", "strike_offset": self.short_offset},
                {
                    "type": "CE",
                    "transaction": "BUY",
                    "strike_offset": self.short_offset + self.wing_width,
                },
                {"type": "PE", "transaction": "SELL", "strike_offset": -self.short_offset},
                {
                    "type": "PE",
                    "transaction": "BUY",
                    "strike_offset": -(self.short_offset + self.wing_width),
                },
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        if dte <= 0:
            return True
        if unrealised_pnl <= -self.stop_loss_pct:
            return True
        if unrealised_pnl >= self.profit_target_pct:
            return True
        return False


class CoveredCallStrategy(OptionsStrategy):
    """Sell OTM call monthly against holdings."""

    name = "Covered Call"

    def __init__(self, call_offset: int = 200, min_dte: int = 20, max_dte: int = 35):
        self.call_offset = call_offset
        self.min_dte = min_dte
        self.max_dte = max_dte

    def should_enter(self, dt, spot, iv, dte, vix):
        if self.min_dte <= dte <= self.max_dte:
            return [
                {"type": "CE", "transaction": "SELL", "strike_offset": self.call_offset},
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        return dte <= 0


class ProtectivePutStrategy(OptionsStrategy):
    """Buy OTM put for portfolio protection when VIX is low."""

    name = "Protective Put"

    def __init__(self, put_offset: int = -300, max_vix_entry: float = 15.0, min_dte: int = 20):
        self.put_offset = put_offset
        self.max_vix_entry = max_vix_entry
        self.min_dte = min_dte

    def should_enter(self, dt, spot, iv, dte, vix):
        if vix <= self.max_vix_entry and dte >= self.min_dte:
            return [
                {"type": "PE", "transaction": "BUY", "strike_offset": self.put_offset},
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        if dte <= 0:
            return True
        if unrealised_pnl >= 200:  # 3x premium
            return True
        return False


class ShortStraddleStrategy(OptionsStrategy):
    """
    Sell ATM Straddle — sell CE + sell PE at same strike.

    Entry: on expiry day (DTE = entry_dte, default 0).
    Adjustment: if spot moves >= adjust_points from entry, re-center.
    Exit: on expiry, stop-loss, or profit target.
    """

    name = "Short Straddle"

    def __init__(
        self,
        entry_dte: int = 0,
        adjust_points: int = 50,
        max_loss_pct: float = 100.0,
        profit_target_pct: float = 50.0,
    ):
        self.entry_dte = entry_dte
        self.adjust_points = adjust_points
        self.max_loss_pct = max_loss_pct
        self.profit_target_pct = profit_target_pct

    def should_enter(self, dt, spot, iv, dte, vix):
        if dte <= self.entry_dte:
            return [
                {"type": "CE", "transaction": "SELL", "strike_offset": 0},
                {"type": "PE", "transaction": "SELL", "strike_offset": 0},
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        if dte <= 0 and days_held > 0:
            return True
        if unrealised_pnl <= -self.max_loss_pct:
            return True
        if unrealised_pnl >= self.profit_target_pct:
            return True
        return False

    def should_adjust(self, spot: float, entry_spot: float, adjust_points: int) -> bool:
        """Check if spot has moved enough to warrant re-centering the straddle."""
        return abs(spot - entry_spot) >= adjust_points


class ShortStrangleStrategy(OptionsStrategy):
    """
    Sell OTM Strangle — sell OTM CE + sell OTM PE.

    Entry: on expiry day (DTE = entry_dte).
    Wider breakevens than straddle, lower premium collected.
    """

    name = "Short Strangle"

    def __init__(
        self,
        otm_offset: int = 100,
        entry_dte: int = 0,
        adjust_points: int = 75,
        max_loss_pct: float = 100.0,
        profit_target_pct: float = 50.0,
    ):
        self.otm_offset = otm_offset
        self.entry_dte = entry_dte
        self.adjust_points = adjust_points
        self.max_loss_pct = max_loss_pct
        self.profit_target_pct = profit_target_pct

    def should_enter(self, dt, spot, iv, dte, vix):
        if dte <= self.entry_dte:
            return [
                {"type": "CE", "transaction": "SELL", "strike_offset": self.otm_offset},
                {"type": "PE", "transaction": "SELL", "strike_offset": -self.otm_offset},
            ]
        return None

    def should_exit(self, dt, spot, iv, dte, entry_spot, days_held, unrealised_pnl):
        if dte <= 0 and days_held > 0:
            return True
        if unrealised_pnl <= -self.max_loss_pct:
            return True
        if unrealised_pnl >= self.profit_target_pct:
            return True
        return False

    def should_adjust(self, spot: float, entry_spot: float, adjust_points: int) -> bool:
        return abs(spot - entry_spot) >= adjust_points


# ── Expiry Calendar ──────────────────────────────────────────


def _get_weekly_expiries(start: date, end: date) -> list[date]:
    """Generate Thursday expiry dates (NSE weekly expiry = Thursday)."""
    expiries = []
    current = start
    while current <= end:
        if current.weekday() == 3:  # Thursday
            expiries.append(current)
        current += timedelta(days=1)
    return expiries


def _nearest_expiry(dt: date, expiries: list[date]) -> Optional[date]:
    """Find the nearest future expiry on or after dt."""
    for exp in expiries:
        if exp >= dt:
            return exp
    return None


def _round_strike(spot: float, step: float = 50.0) -> float:
    """Round to nearest strike step (NIFTY=50, BANKNIFTY=100)."""
    return round(spot / step) * step


# ── Options Backtester ───────────────────────────────────────

# Default lot sizes for popular Indian underlyings
LOT_SIZES = {
    "NIFTY": 25,
    "NIFTY50": 25,
    "NIFTY 50": 25,
    "BANKNIFTY": 15,
    "NIFTY BANK": 15,
    "FINNIFTY": 25,
    "MIDCPNIFTY": 50,
}

STRIKE_STEPS = {
    "NIFTY": 50,
    "NIFTY50": 50,
    "NIFTY 50": 50,
    "BANKNIFTY": 100,
    "NIFTY BANK": 100,
    "FINNIFTY": 50,
}


class OptionsBacktester:
    """
    Backtest options strategies on historical data.

    Uses historical spot price + VIX (as IV proxy) to estimate
    option premiums via Black-Scholes at each point in time.
    """

    def __init__(
        self,
        underlying: str,
        period: str = "1y",
        capital: float = 100000,
        lot_size: Optional[int] = None,
        strike_step: Optional[float] = None,
    ) -> None:
        self.underlying = underlying.upper()
        self.period = period
        self.initial_capital = capital
        self.lot_size = lot_size or LOT_SIZES.get(self.underlying, 25)
        self.strike_step = strike_step or STRIKE_STEPS.get(self.underlying, 50)
        self._spot_data: Optional[pd.DataFrame] = None
        self._vix_data: Optional[pd.DataFrame] = None

    def _load_data(self) -> None:
        """Load historical spot + VIX data."""
        if self._spot_data is not None:
            return

        from market.history import get_ohlcv

        period_days = {
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "3y": 1095,
            "5y": 1825,
        }
        days = period_days.get(self.period, 365)

        # Spot data
        self._spot_data = get_ohlcv(self.underlying, days=days)
        if self._spot_data.empty:
            raise RuntimeError(f"No historical data for {self.underlying}")

        # VIX data (India VIX from yfinance)
        try:
            self._vix_data = get_ohlcv("INDIA VIX", days=days)
        except Exception:
            pass

        if self._vix_data is None or self._vix_data.empty:
            # Fallback: compute realized vol as IV proxy
            returns = np.log(self._spot_data["close"] / self._spot_data["close"].shift(1)).dropna()
            rv = (returns.rolling(30).std() * math.sqrt(252)).dropna()
            self._vix_data = pd.DataFrame({"close": rv * 100}, index=rv.index)

    def _get_iv(self, dt) -> float:
        """Get IV (from VIX) for a given date. Returns decimal (e.g., 0.20)."""
        if self._vix_data is not None and dt in self._vix_data.index:
            return float(self._vix_data.loc[dt, "close"]) / 100.0
        # Fallback: use 20% default
        return 0.20

    def run(self, strategy: OptionsStrategy) -> OptionsBacktestResult:
        """Execute the options backtest."""
        self._load_data()

        spot_df = self._spot_data
        dates = spot_df.index
        expiries = _get_weekly_expiries(
            dates[0].date() if hasattr(dates[0], "date") else dates[0],
            dates[-1].date() if hasattr(dates[-1], "date") else dates[-1],
        )

        capital = self.initial_capital
        trades: list[OptionsTrade] = []
        equity = [capital]

        # Position state
        in_position = False
        entry_date = None
        entry_spot = 0.0
        entry_premium_total = 0.0
        active_legs: list[dict] = []  # leg specs from strategy

        for i in range(len(dates)):
            dt = dates[i]
            dt_date = dt.date() if hasattr(dt, "date") else dt
            spot = float(spot_df.iloc[i]["close"])
            iv = self._get_iv(dt)
            vix = iv * 100  # convert back to VIX scale for strategy

            # Find nearest expiry
            nearest_exp = _nearest_expiry(dt_date, expiries)
            dte = (nearest_exp - dt_date).days if nearest_exp else 30

            if not in_position:
                # Check entry
                legs_spec = strategy.should_enter(dt_date, spot, iv, dte, vix)
                if legs_spec:
                    # Calculate premiums for each leg
                    active_legs = []
                    entry_premium_total = 0.0
                    atm_strike = _round_strike(spot, self.strike_step)

                    for spec in legs_spec:
                        strike = atm_strike + spec["strike_offset"]
                        premium = bs_premium(spot, strike, dte, iv, spec["type"])
                        sign = 1 if spec["transaction"] == "BUY" else -1
                        entry_premium_total += sign * premium * self.lot_size

                        active_legs.append(
                            {
                                **spec,
                                "strike": strike,
                                "entry_premium": premium,
                            }
                        )

                    in_position = True
                    entry_date = str(dt_date)
                    entry_spot = spot
            else:
                # Calculate unrealised P&L
                unrealised = 0.0
                for leg in active_legs:
                    current_prem = bs_premium(spot, leg["strike"], max(dte, 0), iv, leg["type"])
                    sign = 1 if leg["transaction"] == "BUY" else -1
                    pnl_per_unit = sign * (current_prem - leg["entry_premium"])
                    unrealised += pnl_per_unit * self.lot_size

                # unrealised_pnl as % of premium deployed
                premium_deployed = abs(entry_premium_total) if entry_premium_total != 0 else 1
                unrealised_pct = (unrealised / premium_deployed) * 100

                days_held = (dt_date - date.fromisoformat(entry_date)).days if entry_date else 0

                # Check exit
                if strategy.should_exit(
                    dt_date, spot, iv, dte, entry_spot, days_held, unrealised_pct
                ):
                    # Close all legs
                    trade_legs = []
                    combined_pnl = 0.0
                    for leg in active_legs:
                        exit_prem = bs_premium(spot, leg["strike"], max(dte, 0), iv, leg["type"])
                        sign = 1 if leg["transaction"] == "BUY" else -1
                        leg_pnl = sign * (exit_prem - leg["entry_premium"]) * self.lot_size

                        trade_legs.append(
                            OptionsLeg(
                                option_type=leg["type"],
                                transaction=leg["transaction"],
                                strike=leg["strike"],
                                entry_premium=round(leg["entry_premium"], 2),
                                exit_premium=round(exit_prem, 2),
                                lot_size=self.lot_size,
                                pnl=round(leg_pnl, 2),
                            )
                        )
                        combined_pnl += leg_pnl

                    capital += combined_pnl
                    pnl_pct = (combined_pnl / premium_deployed) * 100 if premium_deployed else 0

                    trades.append(
                        OptionsTrade(
                            entry_date=entry_date,
                            exit_date=str(dt_date),
                            underlying_entry=round(entry_spot, 2),
                            underlying_exit=round(spot, 2),
                            legs=trade_legs,
                            combined_pnl=round(combined_pnl, 2),
                            combined_pnl_pct=round(pnl_pct, 1),
                            hold_days=days_held,
                            strategy_name=strategy.name,
                        )
                    )

                    in_position = False
                    active_legs = []

            equity.append(capital)

        # ── Metrics ──────────────────────────────────────────
        total_pnl = capital - self.initial_capital
        total_return = (total_pnl / self.initial_capital) * 100

        winners = [t for t in trades if t.combined_pnl > 0]
        losers = [t for t in trades if t.combined_pnl < 0]
        win_rate = len(winners) / len(trades) * 100 if trades else 0
        avg_win = sum(t.combined_pnl for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.combined_pnl for t in losers) / len(losers) if losers else 0
        avg_hold = sum(t.hold_days for t in trades) / len(trades) if trades else 0

        # Sharpe
        eq = pd.Series(equity)
        daily_ret = eq.pct_change(fill_method=None).dropna()
        sharpe = 0.0
        if len(daily_ret) > 1 and daily_ret.std() > 0:
            sharpe = (daily_ret.mean() / daily_ret.std()) * math.sqrt(252)

        # Max drawdown
        peak = eq.expanding().max()
        dd = (eq - peak) / peak * 100
        max_dd = float(dd.min()) if not dd.empty else 0

        return OptionsBacktestResult(
            underlying=self.underlying,
            strategy_name=strategy.name,
            period=self.period,
            start_date=str(dates[0])[:10] if len(dates) > 0 else "",
            end_date=str(dates[-1])[:10] if len(dates) > 0 else "",
            total_return=round(total_return, 2),
            total_pnl=round(total_pnl, 2),
            total_trades=len(trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            max_drawdown=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 2),
            avg_hold_days=round(avg_hold, 1),
            trades=trades,
        )


# ── Strategy Registry ────────────────────────────────────────

OPTIONS_STRATEGIES = {
    "straddle": lambda args: StraddleStrategy(
        entry_dte=int(args[0]) if args else 3,
    ),
    "short-straddle": lambda args: ShortStraddleStrategy(
        entry_dte=int(args[0]) if args else 0,
        adjust_points=int(args[1]) if len(args) > 1 else 50,
    ),
    "short-strangle": lambda args: ShortStrangleStrategy(
        otm_offset=int(args[0]) if args else 100,
        entry_dte=int(args[1]) if len(args) > 1 else 0,
    ),
    "iron-condor": lambda args: IronCondorStrategy(
        short_offset=int(args[0]) if args else 200,
        wing_width=int(args[1]) if len(args) > 1 else 100,
    ),
    "covered-call": lambda args: CoveredCallStrategy(
        call_offset=int(args[0]) if args else 200,
    ),
    "protective-put": lambda args: ProtectivePutStrategy(),
}


def run_options_backtest(
    underlying: str,
    strategy_name: str = "straddle",
    strategy_args: Optional[list[str]] = None,
    period: str = "1y",
    capital: float = 100000,
    lot_size: Optional[int] = None,
) -> OptionsBacktestResult:
    """Convenience function for running a named options strategy."""
    factory = OPTIONS_STRATEGIES.get(strategy_name.lower())
    if not factory:
        raise ValueError(
            f"Unknown options strategy: {strategy_name}. "
            f"Available: {', '.join(OPTIONS_STRATEGIES.keys())}"
        )

    strategy = factory(strategy_args or [])
    bt = OptionsBacktester(underlying, period=period, capital=capital, lot_size=lot_size)
    return bt.run(strategy)
