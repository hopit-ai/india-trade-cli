"""
engine/strategy.py
──────────────────
Strategy recommendation engine.

Given a view (BULLISH / BEARISH / NEUTRAL) on a stock/index, evaluates
and ranks candidate strategies by their risk-reward profile.

Strategies evaluated:
  1. Buy stock (delivery CNC)
  2. Buy Call Option (CE)
  3. Buy Put Option (PE)
  4. Bull Call Spread
  5. Bear Put Spread
  6. Iron Condor (if neutral/range-bound)
  7. Sell Cash-Secured Put

Each strategy is scored on:
  - Max profit potential
  - Max loss / capital at risk
  - Breakeven distance from spot
  - Capital efficiency (profit / margin ratio)
  - Fit with the stated view and DTE

Output: ranked list of StrategyResult dataclasses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from analysis.options import PayoffLeg, payoff as calc_payoff, StrategyPayoff


# ── Result dataclasses ────────────────────────────────────────


@dataclass
class StrategyResult:
    name: str
    description: str
    legs: list[dict]  # human-readable leg descriptions
    capital_needed: float  # upfront cash / margin required
    max_profit: float  # positive = capped, inf-like = uncapped
    max_loss: float  # negative = max downside
    breakeven: list[float]  # breakeven spot price(s)
    rr_ratio: float  # reward/risk ratio (0 if unlimited loss)
    fit_score: int  # 0–100 how well it fits the view
    best_for: str  # one-line "this works when..."
    risks: str  # one-line risk statement
    payoff: Optional[StrategyPayoff] = None


@dataclass
class StrategyReport:
    symbol: str
    spot: float
    view: str  # BULLISH | BEARISH | NEUTRAL
    dte: int
    capital: float
    risk_pct: float
    max_risk_inr: float
    strategies: list[StrategyResult]  # sorted best → worst
    top: StrategyResult = None  # field set after sort


# ── Main entry point ──────────────────────────────────────────


def recommend(
    symbol: str,
    view: str,
    spot: float,
    dte: int = 30,
    capital: float | None = None,
    risk_pct: float | None = None,
) -> StrategyReport:
    """
    Evaluate and rank strategies for a given symbol and market view.

    Args:
        symbol:   NSE symbol (e.g. "NIFTY", "RELIANCE")
        view:     "BULLISH" | "BEARISH" | "NEUTRAL"
        spot:     Current spot price
        dte:      Days to expiry (for options strategies)
        capital:  Available capital (defaults to TOTAL_CAPITAL env)
        risk_pct: Max risk per trade as % of capital (defaults to DEFAULT_RISK_PCT env)

    Returns:
        StrategyReport with ranked strategies
    """
    cap = capital or float(os.environ.get("TOTAL_CAPITAL", 200_000))
    rsk = risk_pct or float(os.environ.get("DEFAULT_RISK_PCT", 2))
    max_risk = cap * rsk / 100
    view_up = view.upper()

    # Get ATM options data for the symbol
    atm_ce_premium, atm_pe_premium, atm_strike, lot_size = _get_atm_data(symbol, spot)

    results: list[StrategyResult] = []

    # ── 1. Buy Stock (CNC delivery) ───────────────────────────
    if view_up == "BULLISH":
        shares = max(1, int(max_risk / spot))  # size to max_risk on a 5% stop
        stop_loss = round(spot * 0.95, 2)
        target = round(spot * 1.15, 2)
        results.append(
            StrategyResult(
                name="Buy Stock (Delivery)",
                description=f"Buy {shares} shares at ₹{spot:,.0f}",
                legs=[{"action": "BUY", "instrument": symbol, "qty": shares, "price": spot}],
                capital_needed=round(spot * shares, 2),
                max_profit=round((target - spot) * shares, 2),
                max_loss=round((stop_loss - spot) * shares, 2),
                breakeven=[spot],
                rr_ratio=3.0,  # 15% target / 5% stop = 3:1
                fit_score=80 if view_up == "BULLISH" else 10,
                best_for="Strong conviction, 1–6 month horizon, no expiry pressure",
                risks="Full downside if stock falls; no leverage",
            )
        )

    # ── 2. Buy Call Option ────────────────────────────────────
    if view_up == "BULLISH" and atm_ce_premium:
        cost = atm_ce_premium * lot_size
        be = round(atm_strike + atm_ce_premium, 2)
        results.append(
            StrategyResult(
                name="Buy Call (CE)",
                description=f"Buy 1 lot {symbol} {atm_strike:.0f}CE @ ₹{atm_ce_premium:.0f}",
                legs=[
                    {
                        "action": "BUY",
                        "type": "CE",
                        "strike": atm_strike,
                        "premium": atm_ce_premium,
                        "lots": 1,
                    }
                ],
                capital_needed=round(cost, 2),
                max_profit=round((spot * 1.10 - atm_strike - atm_ce_premium) * lot_size, 2),
                max_loss=round(-cost, 2),
                breakeven=[be],
                rr_ratio=round(max(0, (spot * 1.10 - be)) / atm_ce_premium, 2),
                fit_score=85 if view_up == "BULLISH" and dte <= 30 else 60,
                best_for="Short-term directional move; defined risk, leveraged gains",
                risks="Full premium lost if stock doesn't move enough; theta decay",
            )
        )

    # ── 3. Buy Put Option ─────────────────────────────────────
    if view_up == "BEARISH" and atm_pe_premium:
        cost = atm_pe_premium * lot_size
        be = round(atm_strike - atm_pe_premium, 2)
        results.append(
            StrategyResult(
                name="Buy Put (PE)",
                description=f"Buy 1 lot {symbol} {atm_strike:.0f}PE @ ₹{atm_pe_premium:.0f}",
                legs=[
                    {
                        "action": "BUY",
                        "type": "PE",
                        "strike": atm_strike,
                        "premium": atm_pe_premium,
                        "lots": 1,
                    }
                ],
                capital_needed=round(cost, 2),
                max_profit=round((atm_strike - spot * 0.90 - atm_pe_premium) * lot_size, 2),
                max_loss=round(-cost, 2),
                breakeven=[be],
                rr_ratio=round(max(0, (be - spot * 0.90)) / atm_pe_premium, 2),
                fit_score=85 if view_up == "BEARISH" and dte <= 30 else 60,
                best_for="Short-term bearish move; defined risk, leveraged downside play",
                risks="Full premium lost if stock holds or rises; rapid theta decay",
            )
        )

    # ── 4. Bull Call Spread ───────────────────────────────────
    if view_up == "BULLISH" and atm_ce_premium:
        otm_strike = round(atm_strike + spot * 0.03, -2)  # ~3% OTM
        otm_premium = max(1.0, atm_ce_premium * 0.45)  # OTM is cheaper
        net_debit = round(atm_ce_premium - otm_premium, 2)
        max_p = round((otm_strike - atm_strike - net_debit) * lot_size, 2)
        max_l = round(-net_debit * lot_size, 2)
        be = round(atm_strike + net_debit, 2)

        legs_payoff = [
            PayoffLeg("CE", "BUY", atm_strike, atm_ce_premium, lot_size),
            PayoffLeg("CE", "SELL", otm_strike, otm_premium, lot_size),
        ]
        pf = calc_payoff(legs_payoff, (spot * 0.85, spot * 1.20))

        results.append(
            StrategyResult(
                name="Bull Call Spread",
                description=(
                    f"Buy {atm_strike:.0f}CE @ ₹{atm_ce_premium:.0f} + "
                    f"Sell {otm_strike:.0f}CE @ ₹{otm_premium:.0f}"
                ),
                legs=[
                    {
                        "action": "BUY",
                        "type": "CE",
                        "strike": atm_strike,
                        "premium": atm_ce_premium,
                    },
                    {"action": "SELL", "type": "CE", "strike": otm_strike, "premium": otm_premium},
                ],
                capital_needed=round(net_debit * lot_size, 2),
                max_profit=max_p,
                max_loss=max_l,
                breakeven=[be],
                rr_ratio=round(max_p / abs(max_l), 2) if max_l else 0,
                fit_score=80 if view_up == "BULLISH" else 20,
                best_for="Moderately bullish; defined risk, lower cost than outright call",
                risks="Profits capped at short strike; stock must move above breakeven",
                payoff=pf,
            )
        )

    # ── 5. Bear Put Spread ────────────────────────────────────
    if view_up == "BEARISH" and atm_pe_premium:
        otm_put_strike = round(atm_strike - spot * 0.03, -2)
        otm_put_prem = max(1.0, atm_pe_premium * 0.45)
        net_debit = round(atm_pe_premium - otm_put_prem, 2)
        max_p = round((atm_strike - otm_put_strike - net_debit) * lot_size, 2)
        max_l = round(-net_debit * lot_size, 2)
        be = round(atm_strike - net_debit, 2)

        legs_payoff = [
            PayoffLeg("PE", "BUY", atm_strike, atm_pe_premium, lot_size),
            PayoffLeg("PE", "SELL", otm_put_strike, otm_put_prem, lot_size),
        ]
        pf = calc_payoff(legs_payoff, (spot * 0.80, spot * 1.15))

        results.append(
            StrategyResult(
                name="Bear Put Spread",
                description=(
                    f"Buy {atm_strike:.0f}PE @ ₹{atm_pe_premium:.0f} + "
                    f"Sell {otm_put_strike:.0f}PE @ ₹{otm_put_prem:.0f}"
                ),
                legs=[
                    {
                        "action": "BUY",
                        "type": "PE",
                        "strike": atm_strike,
                        "premium": atm_pe_premium,
                    },
                    {
                        "action": "SELL",
                        "type": "PE",
                        "strike": otm_put_strike,
                        "premium": otm_put_prem,
                    },
                ],
                capital_needed=round(net_debit * lot_size, 2),
                max_profit=max_p,
                max_loss=max_l,
                breakeven=[be],
                rr_ratio=round(max_p / abs(max_l), 2) if max_l else 0,
                fit_score=80 if view_up == "BEARISH" else 20,
                best_for="Moderately bearish; cheaper than outright put",
                risks="Loss capped if stock falls sharply below short strike",
                payoff=pf,
            )
        )

    # ── 6. Iron Condor (neutral / range-bound) ────────────────
    if view_up == "NEUTRAL" and atm_ce_premium and atm_pe_premium:
        wing = spot * 0.03
        sc = round(atm_strike + wing, -2)  # short call
        lc = round(sc + wing, -2)  # long call (wing)
        sp = round(atm_strike - wing, -2)  # short put
        lp = round(sp - wing, -2)  # long put (wing)

        sc_p, lc_p = atm_ce_premium * 0.55, atm_ce_premium * 0.30
        sp_p, lp_p = atm_pe_premium * 0.55, atm_pe_premium * 0.30
        net_credit = round((sc_p + sp_p) - (lc_p + lp_p), 2)
        max_l = round(-(wing / spot * spot - net_credit) * lot_size, 2)
        max_p = round(net_credit * lot_size, 2)

        legs_payoff = [
            PayoffLeg("CE", "SELL", sc, sc_p, lot_size),
            PayoffLeg("CE", "BUY", lc, lc_p, lot_size),
            PayoffLeg("PE", "SELL", sp, sp_p, lot_size),
            PayoffLeg("PE", "BUY", lp, lp_p, lot_size),
        ]
        pf = calc_payoff(legs_payoff, (lp * 0.95, lc * 1.05))

        results.append(
            StrategyResult(
                name="Iron Condor",
                description=(
                    f"Sell {sp:.0f}P/{sc:.0f}C, Buy {lp:.0f}P/{lc:.0f}C | Credit ₹{net_credit:.0f}"
                ),
                legs=[
                    {"action": "SELL", "type": "CE", "strike": sc, "premium": sc_p},
                    {"action": "BUY", "type": "CE", "strike": lc, "premium": lc_p},
                    {"action": "SELL", "type": "PE", "strike": sp, "premium": sp_p},
                    {"action": "BUY", "type": "PE", "strike": lp, "premium": lp_p},
                ],
                capital_needed=abs(max_l),
                max_profit=max_p,
                max_loss=max_l,
                breakeven=[round(sp - net_credit, 2), round(sc + net_credit, 2)],
                rr_ratio=round(max_p / abs(max_l), 2) if max_l else 0,
                fit_score=85 if view_up == "NEUTRAL" else 30,
                best_for="Range-bound market with high IV; earn theta decay",
                risks="Full wing-width loss if stock breaks out of range",
                payoff=pf,
            )
        )

    # ── 7. Sell Cash-Secured Put ──────────────────────────────
    if view_up in ("BULLISH", "NEUTRAL") and atm_pe_premium:
        otm_put = round(spot * 0.97, -1)
        premium = atm_pe_premium * 0.65  # OTM put is cheaper
        margin_r = round(otm_put * lot_size * 0.10, 2)  # ~10% margin for CSP
        max_p = round(premium * lot_size, 2)
        max_l = round(-otm_put * lot_size, 2)

        results.append(
            StrategyResult(
                name="Sell Cash-Secured Put",
                description=f"Sell {otm_put:.0f}PE @ ₹{premium:.0f} | Margin ≈ ₹{margin_r:,.0f}",
                legs=[{"action": "SELL", "type": "PE", "strike": otm_put, "premium": premium}],
                capital_needed=margin_r,
                max_profit=max_p,
                max_loss=max_l,
                breakeven=[round(otm_put - premium, 2)],
                rr_ratio=round(max_p / margin_r * 100, 1),  # % return on margin
                fit_score=75 if view_up == "BULLISH" else 65,
                best_for="Happy to buy stock at lower price; earn premium while waiting",
                risks="Obligated to buy at strike if assigned — full downside of stock",
            )
        )

    # ── Sort by fit_score DESC ────────────────────────────────
    results.sort(key=lambda r: r.fit_score, reverse=True)

    report = StrategyReport(
        symbol=symbol,
        spot=spot,
        view=view_up,
        dte=dte,
        capital=cap,
        risk_pct=rsk,
        max_risk_inr=max_risk,
        strategies=results,
    )
    if results:
        report.top = results[0]

    return report


# ── Market data helpers ───────────────────────────────────────


def _get_atm_data(symbol: str, spot: float) -> tuple[float, float, float, int]:
    """
    Fetch ATM CE/PE premiums and lot size from the options chain.
    Returns (ce_premium, pe_premium, atm_strike, lot_size).
    Falls back to IV-based approximation on failure.
    """
    try:
        from market.options import get_options_chain, get_atm_strike

        chain = get_options_chain(symbol)
        atm = get_atm_strike(symbol, spot)
        lot = chain[0].lot_size if chain else 1

        ce_prem = next(
            (c.last_price for c in chain if c.strike == atm and c.option_type.upper() == "CE"),
            None,
        )
        pe_prem = next(
            (c.last_price for c in chain if c.strike == atm and c.option_type.upper() == "PE"),
            None,
        )
        if ce_prem and pe_prem:
            return ce_prem, pe_prem, atm, lot
    except Exception:
        pass

    # Fallback: approximate from spot and assumed 15% IV / 30 DTE
    import math

    iv = 0.15
    t = 30 / 365
    atm = round(spot, -2)
    approx = spot * iv * math.sqrt(t) * 0.4  # rough ATM premium estimate
    lot = _default_lot(symbol)
    return round(approx, 2), round(approx, 2), atm, lot


def _default_lot(symbol: str) -> int:
    lots = {"NIFTY": 75, "BANKNIFTY": 15, "FINNIFTY": 40, "MIDCPNIFTY": 75}
    return lots.get(symbol.upper(), 1)
