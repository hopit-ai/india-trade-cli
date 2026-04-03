"""
analysis/options.py
───────────────────
Options analytics: Black-Scholes Greeks, IV, IV Rank, payoff, PCR.
Uses py_vollib for Black-Scholes calculations.

All prices in INR. Rates in decimals (0.065 = 6.5%).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing      import Optional

import numpy as np

try:
    from py_vollib.black_scholes          import black_scholes as bs_price
    from py_vollib.black_scholes.greeks.analytical import (
        delta as bs_delta,
        gamma as bs_gamma,
        theta as bs_theta,
        vega  as bs_vega,
        rho   as bs_rho,
    )
    from py_vollib.black_scholes.implied_volatility import implied_volatility as bs_iv
    PY_VOLLIB_AVAILABLE = True
except Exception:
    # Catch broad Exception: py_vollib depends on py_lets_be_rational/numba
    # which can crash (not just ImportError) on Python 3.13+ due to numba
    # cache/compilation issues. Graceful fallback to built-in BS formulas.
    PY_VOLLIB_AVAILABLE = False

from market.options import get_options_chain, get_pcr, get_max_pain


# ── Risk-free rate (RBI repo rate) ────────────────────────────
RISK_FREE_RATE = 0.065      # 6.5%


# ── Greeks dataclass ─────────────────────────────────────────

@dataclass
class Greeks:
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0     # per day in INR (divided by 365)
    vega:  float = 0.0     # for 1% change in IV
    rho:   float = 0.0
    iv:    float = 0.0     # implied volatility as decimal
    iv_pct:float = 0.0     # iv as percentage


@dataclass
class OptionAnalysis:
    symbol:     str
    underlying: str
    expiry:     str
    strike:     float
    option_type:str        # CE | PE
    spot:       float
    ltp:        float
    lot_size:   int
    dte:        int         # days to expiry

    greeks:     Greeks = field(default_factory=Greeks)

    # Derived
    breakeven:  float  = 0.0
    intrinsic:  float  = 0.0
    time_value: float  = 0.0
    moneyness:  str    = ""    # ITM | ATM | OTM
    max_loss:   float  = 0.0   # per lot (for buyer)


@dataclass
class PayoffLeg:
    option_type:    str     # CE | PE | STOCK
    transaction:    str     # BUY | SELL
    strike:         float
    premium:        float
    lot_size:       int
    lots:           int = 1


@dataclass
class PayoffPoint:
    spot:   float
    pnl:    float


@dataclass
class StrategyPayoff:
    legs:        list[PayoffLeg]
    max_profit:  float
    max_loss:    float
    breakevens:  list[float]
    payoff:      list[PayoffPoint]


# ── Black-Scholes helpers ─────────────────────────────────────

def _dte_years(expiry_str: str) -> float:
    """Days to expiry as fraction of year."""
    from datetime import datetime, date
    try:
        exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except ValueError:
        exp = date.fromisoformat(expiry_str[:10])
    dte_days = max(1, (exp - date.today()).days)
    return dte_days / 365.0


def _dte_days(expiry_str: str) -> int:
    from datetime import datetime, date
    try:
        exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except ValueError:
        exp = date.fromisoformat(expiry_str[:10])
    return max(1, (exp - date.today()).days)


def _flag(option_type: str) -> str:
    """py_vollib flag: 'c' for call, 'p' for put."""
    return "c" if option_type.upper() == "CE" else "p"


def compute_greeks(
    spot:        float,
    strike:      float,
    expiry:      str,
    option_type: str,
    ltp:         float,
    rate:        float = RISK_FREE_RATE,
) -> Greeks:
    """
    Compute full Greeks for a single options contract.
    Falls back to analytical approximations if py_vollib unavailable.
    """
    t    = _dte_years(expiry)
    flag = _flag(option_type)

    if PY_VOLLIB_AVAILABLE and ltp > 0.01:
        try:
            iv = bs_iv(ltp, spot, strike, t, rate, flag)
            return Greeks(
                delta  = bs_delta(flag, spot, strike, t, rate, iv),
                gamma  = bs_gamma(flag, spot, strike, t, rate, iv),
                theta  = bs_theta(flag, spot, strike, t, rate, iv) / 365,
                vega   = bs_vega(flag, spot, strike, t, rate, iv) / 100,
                rho    = bs_rho(flag, spot, strike, t, rate, iv),
                iv     = iv,
                iv_pct = round(iv * 100, 2),
            )
        except Exception:
            pass

    # ── Analytical fallback (own Black-Scholes) ───────────────
    return _bs_greeks_manual(spot, strike, t, rate, ltp, option_type)


def _bs_greeks_manual(
    S: float, K: float, T: float, r: float,
    price: float, option_type: str,
) -> Greeks:
    """Minimal Black-Scholes implementation as fallback."""
    from scipy.stats import norm

    # Estimate sigma from price via Newton-Raphson
    sigma = 0.20    # initial guess
    for _ in range(50):
        try:
            d1   = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2   = d1 - sigma * math.sqrt(T)
            if option_type.upper() == "CE":
                theo = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
                vega = S * norm.pdf(d1) * math.sqrt(T)
                delta = norm.cdf(d1)
            else:
                theo = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
                vega = S * norm.pdf(d1) * math.sqrt(T)
                delta = norm.cdf(d1) - 1

            if abs(vega) < 1e-10:
                break
            sigma -= (theo - price) / vega
            if sigma <= 0:
                sigma = 0.001
        except Exception:
            break

    try:
        d1  = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2  = d1 - sigma * math.sqrt(T)
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        theta_val = (-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2))
        return Greeks(
            delta  = round(delta, 4),
            gamma  = round(gamma, 6),
            theta  = round(theta_val / 365, 4),
            vega   = round(vega / 100, 4),
            iv     = round(sigma, 4),
            iv_pct = round(sigma * 100, 2),
        )
    except Exception:
        return Greeks(iv=sigma, iv_pct=round(sigma * 100, 2))


# ── IV Rank ───────────────────────────────────────────────────

def iv_rank(
    current_iv:  float,
    historical_ivs: list[float],
) -> float:
    """
    IV Rank = (current_iv - 52w_low) / (52w_high - 52w_low) × 100

    Returns 0–100.  >50 means IV is elevated relative to history.
    """
    if not historical_ivs:
        return 50.0
    iv_low  = min(historical_ivs)
    iv_high = max(historical_ivs)
    if iv_high == iv_low:
        return 50.0
    return round((current_iv - iv_low) / (iv_high - iv_low) * 100, 1)


def compute_iv_rank_from_history(symbol: str, period: str = "1y") -> Optional[float]:
    """
    Compute IV rank from historical realized volatility.

    Uses 30-day rolling annualized volatility as an IV proxy:
      IV Rank = (current_RV - 52w_low_RV) / (52w_high_RV - 52w_low_RV) * 100

    Returns 0-100 or None if data unavailable.
    """
    try:
        import yfinance as yf
        import numpy as np

        # Use proper symbol mapping (handles NIFTY → ^NSEI etc.)
        try:
            from market.yfinance_provider import _to_yf_symbol
            yf_sym = _to_yf_symbol(symbol)
        except ImportError:
            yf_sym = f"{symbol.upper()}.NS"

        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period=period)
        if hist.empty or len(hist) < 60:
            return None

        returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
        rolling_vol = (returns.rolling(30).std() * np.sqrt(252) * 100).dropna()

        if rolling_vol.empty or len(rolling_vol) < 30:
            return None

        current = rolling_vol.iloc[-1]
        lo = rolling_vol.min()
        hi = rolling_vol.max()

        if hi == lo:
            return 50.0

        return round((current - lo) / (hi - lo) * 100, 1)
    except Exception:
        return None


# ── Payoff calculator ─────────────────────────────────────────

def payoff(
    legs:       list[PayoffLeg],
    spot_range: Optional[tuple[float, float]] = None,
    steps:      int = 50,
) -> StrategyPayoff:
    """
    Calculate P&L payoff at expiry for a multi-leg options strategy.

    Args:
        legs:       List of PayoffLeg (CE/PE/STOCK + BUY/SELL + premium)
        spot_range: (min_spot, max_spot) — defaults to ±20% of avg strike
        steps:      Number of price points to evaluate

    Returns:
        StrategyPayoff with max_profit, max_loss, breakevens, payoff list
    """
    if not legs:
        return StrategyPayoff([], 0, 0, [], [])

    avg_strike = sum(l.strike for l in legs) / len(legs)
    lo = spot_range[0] if spot_range else avg_strike * 0.80
    hi = spot_range[1] if spot_range else avg_strike * 1.20
    spots = np.linspace(lo, hi, steps)

    def leg_pnl(leg: PayoffLeg, spot: float) -> float:
        qty = leg.lots * leg.lot_size
        sign = 1 if leg.transaction == "BUY" else -1
        if leg.option_type == "CE":
            intrinsic = max(0.0, spot - leg.strike)
        elif leg.option_type == "PE":
            intrinsic = max(0.0, leg.strike - spot)
        else:    # STOCK
            intrinsic = spot - leg.strike
        return sign * (intrinsic - leg.premium) * qty

    payoff_points = []
    pnls = []
    for spot in spots:
        total = sum(leg_pnl(l, float(spot)) for l in legs)
        payoff_points.append(PayoffPoint(round(float(spot), 2), round(total, 2)))
        pnls.append(total)

    pnls_arr = np.array(pnls)
    max_profit = float(np.max(pnls_arr))
    max_loss   = float(np.min(pnls_arr))

    # Breakevens: sign changes in P&L
    breakevens = []
    for i in range(len(pnls) - 1):
        if pnls[i] * pnls[i + 1] <= 0:
            # Linear interpolation
            be = spots[i] + (spots[i+1] - spots[i]) * (-pnls[i]) / (pnls[i+1] - pnls[i] + 1e-9)
            breakevens.append(round(float(be), 2))

    return StrategyPayoff(
        legs       = legs,
        max_profit = round(max_profit, 2),
        max_loss   = round(max_loss, 2),
        breakevens = breakevens,
        payoff     = payoff_points,
    )


# ── Full option analysis ──────────────────────────────────────

def analyse_option(
    underlying:  str,
    strike:      float,
    option_type: str,
    expiry:      str,
    spot:        float,
) -> OptionAnalysis:
    """Analyse a single option contract — Greeks, breakeven, moneyness."""
    chain = get_options_chain(underlying, expiry)
    contract = next(
        (c for c in chain if c.strike == strike and c.option_type.upper() == option_type.upper()),
        None,
    )
    ltp      = contract.last_price if contract else 0.0
    lot_size = contract.lot_size   if contract else 1

    greeks   = compute_greeks(spot, strike, expiry, option_type, ltp)
    dte      = _dte_days(expiry)

    intrinsic  = max(0.0, spot - strike) if option_type == "CE" else max(0.0, strike - spot)
    time_value = max(0.0, ltp - intrinsic)

    if option_type == "CE":
        breakeven = strike + ltp
        moneyness = "ITM" if spot > strike else "OTM" if spot < strike else "ATM"
    else:
        breakeven = strike - ltp
        moneyness = "ITM" if spot < strike else "OTM" if spot > strike else "ATM"

    return OptionAnalysis(
        symbol      = contract.symbol if contract else f"{underlying}{expiry}{option_type}{strike}",
        underlying  = underlying,
        expiry      = expiry,
        strike      = strike,
        option_type = option_type,
        spot        = spot,
        ltp         = ltp,
        lot_size    = lot_size,
        dte         = dte,
        greeks      = greeks,
        breakeven   = round(breakeven, 2),
        intrinsic   = round(intrinsic, 2),
        time_value  = round(time_value, 2),
        moneyness   = moneyness,
        max_loss    = round(ltp * lot_size, 2),
    )


# ── Advanced Strategy Builders ───────────────────────────────

def build_iron_condor(
    spot: float, lot_size: int,
    call_sell_strike: float, call_buy_strike: float,
    put_sell_strike: float, put_buy_strike: float,
    call_sell_prem: float, call_buy_prem: float,
    put_sell_prem: float, put_buy_prem: float,
) -> list[PayoffLeg]:
    """Build an iron condor — sell OTM call spread + sell OTM put spread."""
    return [
        PayoffLeg("CE", "SELL", call_sell_strike, call_sell_prem, lot_size),
        PayoffLeg("CE", "BUY",  call_buy_strike,  call_buy_prem,  lot_size),
        PayoffLeg("PE", "SELL", put_sell_strike,  put_sell_prem,  lot_size),
        PayoffLeg("PE", "BUY",  put_buy_strike,   put_buy_prem,   lot_size),
    ]


def build_butterfly(
    spot: float, lot_size: int,
    lower_strike: float, middle_strike: float, upper_strike: float,
    lower_prem: float, middle_prem: float, upper_prem: float,
    option_type: str = "CE",
) -> list[PayoffLeg]:
    """Build a butterfly spread — buy 1 lower, sell 2 middle, buy 1 upper."""
    return [
        PayoffLeg(option_type, "BUY",  lower_strike,  lower_prem,  lot_size, lots=1),
        PayoffLeg(option_type, "SELL", middle_strike, middle_prem, lot_size, lots=2),
        PayoffLeg(option_type, "BUY",  upper_strike,  upper_prem,  lot_size, lots=1),
    ]


def build_calendar_spread(
    strike: float, lot_size: int,
    near_prem: float, far_prem: float,
    option_type: str = "CE",
) -> list[PayoffLeg]:
    """
    Calendar spread — sell near-term, buy far-term at same strike.
    Profits from faster theta decay of near-term option.
    Note: payoff at near expiry only (far-term value estimated).
    """
    return [
        PayoffLeg(option_type, "SELL", strike, near_prem, lot_size, lots=1),
        PayoffLeg(option_type, "BUY",  strike, far_prem,  lot_size, lots=1),
    ]


def build_ratio_spread(
    lot_size: int,
    buy_strike: float, sell_strike: float,
    buy_prem: float, sell_prem: float,
    option_type: str = "CE",
    ratio: int = 2,
) -> list[PayoffLeg]:
    """
    Ratio spread — buy 1 option, sell N options at different strike.
    E.g. buy 1 ATM call, sell 2 OTM calls (1:2 ratio).
    High risk if stock moves beyond short strikes.
    """
    return [
        PayoffLeg(option_type, "BUY",  buy_strike,  buy_prem,  lot_size, lots=1),
        PayoffLeg(option_type, "SELL", sell_strike, sell_prem, lot_size, lots=ratio),
    ]


def build_diagonal_spread(
    lot_size: int,
    near_strike: float, far_strike: float,
    near_prem: float, far_prem: float,
    option_type: str = "CE",
) -> list[PayoffLeg]:
    """
    Diagonal spread — sell near-term at one strike, buy far-term at different strike.
    Combines calendar + vertical spread characteristics.
    """
    return [
        PayoffLeg(option_type, "SELL", near_strike, near_prem, lot_size, lots=1),
        PayoffLeg(option_type, "BUY",  far_strike,  far_prem,  lot_size, lots=1),
    ]


def suggest_earnings_straddle(
    underlying: str,
    spot: float,
    lot_size: int,
    atm_ce_prem: float,
    atm_pe_prem: float,
    avg_earnings_move: float = 3.0,
) -> dict:
    """
    Evaluate an earnings straddle — buy ATM call + ATM put before results.

    Returns profitability analysis:
    - Total cost of straddle
    - Required move to break even
    - Historical avg move vs breakeven
    - Verdict: FAVORABLE / UNFAVORABLE / MARGINAL
    """
    total_cost = (atm_ce_prem + atm_pe_prem) * lot_size
    breakeven_pct = (atm_ce_prem + atm_pe_prem) / spot * 100
    move_vs_be = avg_earnings_move / breakeven_pct if breakeven_pct > 0 else 0

    if move_vs_be > 1.3:
        verdict = "FAVORABLE"
        reason = f"Avg move ({avg_earnings_move:.1f}%) > breakeven ({breakeven_pct:.1f}%) by {(move_vs_be-1)*100:.0f}%"
    elif move_vs_be > 0.9:
        verdict = "MARGINAL"
        reason = f"Avg move ({avg_earnings_move:.1f}%) roughly equals breakeven ({breakeven_pct:.1f}%)"
    else:
        verdict = "UNFAVORABLE"
        reason = f"Avg move ({avg_earnings_move:.1f}%) < breakeven ({breakeven_pct:.1f}%) — straddle too expensive"

    return {
        "underlying": underlying,
        "spot": spot,
        "straddle_cost": round(total_cost, 2),
        "breakeven_pct": round(breakeven_pct, 2),
        "avg_earnings_move": avg_earnings_move,
        "move_vs_breakeven": round(move_vs_be, 2),
        "verdict": verdict,
        "reason": reason,
    }
