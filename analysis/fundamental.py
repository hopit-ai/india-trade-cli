"""
analysis/fundamental.py
───────────────────────
Fundamental analysis — fetches data from Screener.in (free, no auth needed)
and scores it against quality thresholds for Indian equities.

Screener.in API:
    GET https://www.screener.in/api/company/{symbol}/
    Returns JSON with financial data (no auth for basic fields).

Main entry point: analyse(symbol) → FundamentalSnapshot
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing      import Optional

import httpx


# ── Result dataclass ─────────────────────────────────────────

@dataclass
class FundamentalFlag:
    metric:  str
    value:   float | str
    verdict: str           # "GOOD" | "WARN" | "BAD"
    detail:  str = ""


@dataclass
class FundamentalSnapshot:
    symbol: str
    name:   str = ""

    # Valuation
    pe:         Optional[float] = None    # Price / Earnings
    pb:         Optional[float] = None    # Price / Book
    ev_ebitda:  Optional[float] = None

    # Profitability
    roe:        Optional[float] = None    # Return on Equity %
    roce:       Optional[float] = None    # Return on Capital Employed %
    npm:        Optional[float] = None    # Net Profit Margin %

    # Growth (3Y CAGR)
    sales_growth:  Optional[float] = None
    profit_growth: Optional[float] = None

    # Health
    debt_equity:      Optional[float] = None
    current_ratio:    Optional[float] = None
    promoter_holding: Optional[float] = None   # % holding
    pledged_pct:      Optional[float] = None   # % pledged

    # Dividend
    dividend_yield: Optional[float] = None

    # Score and verdict
    flags:   list[FundamentalFlag] = field(default_factory=list)
    score:   int  = 0                 # 0–100
    verdict: str  = "NEUTRAL"         # STRONG | GOOD | NEUTRAL | WEAK | AVOID
    summary: str  = ""


# ── Screener.in fetch ────────────────────────────────────────

SCREENER_URL = "https://www.screener.in/api/company/{}/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TradingPlatform/1.0)",
    "Accept":     "application/json",
}


def _fetch_screener(symbol: str) -> dict:
    """Fetch raw JSON from Screener.in for a BSE/NSE symbol."""
    url = SCREENER_URL.format(symbol.upper())
    r   = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
    if r.status_code == 404:
        # Try with consolidated suffix
        r = httpx.get(SCREENER_URL.format(symbol.upper() + "C"),
                      headers=HEADERS, timeout=10, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def _safe_float(data: dict, *keys: str) -> Optional[float]:
    """Try multiple keys, return first non-None float found."""
    for key in keys:
        val = data.get(key)
        if val is not None:
            try:
                cleaned = re.sub(r"[^\d.\-]", "", str(val))
                return float(cleaned) if cleaned else None
            except (ValueError, TypeError):
                continue
    return None


def _parse_screener(raw: dict) -> dict:
    """
    Map Screener.in JSON keys to our flat field names.
    Keys vary slightly between companies — we try multiple variants.
    """
    ratios = raw.get("ratios", {})

    return {
        "name":             raw.get("name", ""),
        "pe":               _safe_float(ratios, "Stock P/E", "PE"),
        "pb":               _safe_float(ratios, "Price to Book value", "PB"),
        "roe":              _safe_float(ratios, "Return on equity", "ROE"),
        "roce":             _safe_float(ratios, "ROCE", "Return on capital employed"),
        "npm":              _safe_float(ratios, "Net profit margin", "NPM"),
        "sales_growth":     _safe_float(ratios, "Compounded Sales Growth", "Revenue Growth"),
        "profit_growth":    _safe_float(ratios, "Compounded Profit Growth"),
        "debt_equity":      _safe_float(ratios, "Debt to equity", "D/E"),
        "current_ratio":    _safe_float(ratios, "Current ratio"),
        "promoter_holding": _safe_float(ratios, "Promoter holding", "Promoter Holding"),
        "pledged_pct":      _safe_float(ratios, "Pledged percentage"),
        "dividend_yield":   _safe_float(ratios, "Dividend Yield"),
        "ev_ebitda":        _safe_float(ratios, "EV/EBITDA"),
    }


# ── Mock fallback ────────────────────────────────────────────

MOCK_FUNDAMENTALS: dict[str, dict] = {
    "RELIANCE": dict(name="Reliance Industries", pe=27.4, pb=2.1, roe=14.2, roce=12.8,
                     npm=7.4, sales_growth=11.2, profit_growth=16.3, debt_equity=0.38,
                     current_ratio=1.4, promoter_holding=50.3, pledged_pct=0.0, dividend_yield=0.4),
    "HDFCBANK": dict(name="HDFC Bank", pe=19.2, pb=2.9, roe=17.4, roce=None,
                     npm=26.1, sales_growth=17.8, profit_growth=22.1, debt_equity=None,
                     current_ratio=None, promoter_holding=0.0, pledged_pct=0.0, dividend_yield=1.1),
    "INFY":     dict(name="Infosys", pe=24.6, pb=7.2, roe=32.1, roce=39.4,
                     npm=17.3, sales_growth=8.4, profit_growth=9.2, debt_equity=0.03,
                     current_ratio=2.6, promoter_holding=14.9, pledged_pct=0.0, dividend_yield=3.1),
    "TCS":      dict(name="TCS", pe=28.9, pb=12.4, roe=50.3, roce=60.1,
                     npm=19.4, sales_growth=9.1, profit_growth=10.2, debt_equity=0.01,
                     current_ratio=3.2, promoter_holding=72.4, pledged_pct=0.0, dividend_yield=1.6),
    "ICICIBANK":dict(name="ICICI Bank", pe=18.7, pb=3.2, roe=18.2, roce=None,
                     npm=24.6, sales_growth=21.3, profit_growth=31.2, debt_equity=None,
                     current_ratio=None, promoter_holding=0.0, pledged_pct=0.0, dividend_yield=0.8),
    "SBIN":     dict(name="State Bank of India", pe=10.1, pb=1.7, roe=14.3, roce=None,
                     npm=15.2, sales_growth=14.2, profit_growth=45.1, debt_equity=None,
                     current_ratio=None, promoter_holding=57.5, pledged_pct=0.0, dividend_yield=1.9),
}


def _mock_parse(symbol: str) -> dict:
    key  = symbol.upper()
    data = MOCK_FUNDAMENTALS.get(key, {})
    if not data:
        # Generic fallback for unknown symbols
        data = dict(name=symbol, pe=22.0, pb=3.0, roe=15.0, roce=18.0,
                    npm=12.0, sales_growth=10.0, profit_growth=12.0, debt_equity=0.5,
                    current_ratio=1.5, promoter_holding=40.0, pledged_pct=2.0, dividend_yield=1.0)
    return data


# ── Scoring logic ────────────────────────────────────────────

def _score(parsed: dict) -> tuple[int, list[FundamentalFlag]]:
    """
    Score fundamentals 0–100 using quality thresholds for Indian equities.
    Returns (score, flags_list).
    """
    score  = 50    # start neutral
    flags: list[FundamentalFlag] = []

    def flag(metric, value, good_cond, bad_cond, good_pts, bad_pts, good_msg, bad_msg):
        nonlocal score
        if value is None:
            return
        if good_cond(value):
            flags.append(FundamentalFlag(metric, round(value, 2), "GOOD", good_msg))
            score += good_pts
        elif bad_cond(value):
            flags.append(FundamentalFlag(metric, round(value, 2), "BAD", bad_msg))
            score -= bad_pts
        else:
            flags.append(FundamentalFlag(metric, round(value, 2), "WARN",
                                         f"{metric} is acceptable but not strong"))

    # PE Ratio (lower is cheaper, but negative = loss-making)
    pe = parsed.get("pe")
    if pe and pe > 0:
        if pe < 15:
            flags.append(FundamentalFlag("P/E", round(pe, 1), "GOOD", "Undervalued (<15)"))
            score += 10
        elif pe < 25:
            flags.append(FundamentalFlag("P/E", round(pe, 1), "WARN", "Fairly valued (15–25)"))
        elif pe < 40:
            flags.append(FundamentalFlag("P/E", round(pe, 1), "WARN", "Slightly expensive (25–40)"))
            score -= 5
        else:
            flags.append(FundamentalFlag("P/E", round(pe, 1), "BAD", "Expensive (>40)"))
            score -= 10
    elif pe and pe < 0:
        flags.append(FundamentalFlag("P/E", round(pe, 1), "BAD", "Negative — company making losses"))
        score -= 20

    flag("ROE %",  parsed.get("roe"),
         lambda v: v >= 15, lambda v: v < 8,
         12, 12, "Strong ROE (≥15%)", "Weak ROE (<8%)")

    flag("ROCE %", parsed.get("roce"),
         lambda v: v >= 15, lambda v: v < 10,
         10, 10, "Strong ROCE (≥15%)", "Weak ROCE (<10%)")

    flag("Revenue Growth (3Y)", parsed.get("sales_growth"),
         lambda v: v >= 10, lambda v: v < 0,
         8, 12, "Good revenue growth (≥10% CAGR)", "Negative revenue growth")

    flag("Profit Growth (3Y)", parsed.get("profit_growth"),
         lambda v: v >= 12, lambda v: v < 0,
         10, 15, "Strong profit growth (≥12% CAGR)", "Declining profits")

    flag("Debt/Equity", parsed.get("debt_equity"),
         lambda v: v <= 0.3, lambda v: v > 1.5,
         8, 12, "Low debt (D/E ≤0.3)", "High debt (D/E >1.5)")

    flag("Current Ratio", parsed.get("current_ratio"),
         lambda v: v >= 1.5, lambda v: v < 1.0,
         5, 8, "Healthy liquidity (≥1.5)", "Poor liquidity (<1.0)")

    # Promoter holding
    ph = parsed.get("promoter_holding")
    if ph is not None:
        if ph >= 50:
            flags.append(FundamentalFlag("Promoter Holding", f"{ph:.1f}%", "GOOD",
                                         "High promoter confidence"))
            score += 8
        elif ph >= 35:
            flags.append(FundamentalFlag("Promoter Holding", f"{ph:.1f}%", "WARN",
                                         "Moderate promoter holding"))
        else:
            flags.append(FundamentalFlag("Promoter Holding", f"{ph:.1f}%", "WARN",
                                         "Low promoter holding (institutional heavy)"))

    # Pledged %
    pledged = parsed.get("pledged_pct")
    if pledged is not None and pledged > 0:
        if pledged > 25:
            flags.append(FundamentalFlag("Pledged %", f"{pledged:.1f}%", "BAD",
                                         "High pledge — risk of forced selling"))
            score -= 15
        elif pledged > 5:
            flags.append(FundamentalFlag("Pledged %", f"{pledged:.1f}%", "WARN",
                                         "Some promoter shares pledged"))
            score -= 5

    return max(0, min(100, score)), flags


# ── Main entry point ─────────────────────────────────────────

def analyse(symbol: str, use_mock: bool = False) -> FundamentalSnapshot:
    """
    Full fundamental analysis for a stock symbol.

    Tries Screener.in first; falls back to mock data on failure.

    Args:
        symbol:   NSE/BSE trading symbol e.g. "RELIANCE", "HDFCBANK"
        use_mock: Force mock data (useful for demo/testing)
    """
    if use_mock:
        parsed = _mock_parse(symbol)
    else:
        try:
            raw    = _fetch_screener(symbol)
            parsed = _parse_screener(raw)
        except Exception:
            parsed = _mock_parse(symbol)

    score, flags = _score(parsed)

    if score >= 75:
        verdict = "STRONG"
    elif score >= 60:
        verdict = "GOOD"
    elif score >= 45:
        verdict = "NEUTRAL"
    elif score >= 30:
        verdict = "WEAK"
    else:
        verdict = "AVOID"

    good_count = sum(1 for f in flags if f.verdict == "GOOD")
    bad_count  = sum(1 for f in flags if f.verdict == "BAD")
    summary    = (
        f"{good_count} positives / {bad_count} concerns | "
        f"Score: {score}/100 | "
        f"PE={parsed.get('pe') or 'N/A'} | "
        f"ROE={parsed.get('roe') or 'N/A'}%"
    )

    return FundamentalSnapshot(
        symbol          = symbol.upper(),
        name            = parsed.get("name", symbol),
        pe              = parsed.get("pe"),
        pb              = parsed.get("pb"),
        roe             = parsed.get("roe"),
        roce            = parsed.get("roce"),
        npm             = parsed.get("npm"),
        sales_growth    = parsed.get("sales_growth"),
        profit_growth   = parsed.get("profit_growth"),
        debt_equity     = parsed.get("debt_equity"),
        current_ratio   = parsed.get("current_ratio"),
        promoter_holding= parsed.get("promoter_holding"),
        pledged_pct     = parsed.get("pledged_pct"),
        dividend_yield  = parsed.get("dividend_yield"),
        ev_ebitda       = parsed.get("ev_ebitda"),
        flags           = flags,
        score           = score,
        verdict         = verdict,
        summary         = summary,
    )
