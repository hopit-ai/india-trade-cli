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
except ImportError:
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


def mock_iv_rank(symbol: str) -> float:
    """Return a plausible IV rank for demo purposes."""
    seeds = {"NIFTY": 34, "BANKNIFTY": 41, "RELIANCE": 28, "INFY": 52, "TCS": 22}
    return seeds.get(symbol.upper(), 38.0)


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
