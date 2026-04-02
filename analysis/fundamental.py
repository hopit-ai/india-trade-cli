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

    # Growth (3Y CAGR or TTM)
    sales_growth:  Optional[float] = None
    profit_growth: Optional[float] = None

    # Health
    debt_equity:         Optional[float] = None
    current_ratio:       Optional[float] = None
    interest_coverage:   Optional[float] = None   # EBIT / Interest Expense
    free_cash_flow:      Optional[float] = None   # in crores
    promoter_holding:    Optional[float] = None   # % holding
    institutional_holding: Optional[float] = None  # % FII+DII
    pledged_pct:         Optional[float] = None   # % pledged

    # Dividend
    dividend_yield: Optional[float] = None

    # Price context
    market_cap:      Optional[float] = None   # in crores
    week52_high:     Optional[float] = None
    week52_low:      Optional[float] = None
    pct_from_52w_high: Optional[float] = None  # how far below 52w high (negative %)
    avg_50d:         Optional[float] = None
    avg_200d:        Optional[float] = None
    beta:            Optional[float] = None

    # Analyst consensus
    analyst_count:       Optional[int]   = None
    analyst_rating:      Optional[str]   = None   # "strong_buy", "buy", "hold", "sell"
    target_price_mean:   Optional[float] = None
    target_price_high:   Optional[float] = None
    target_price_low:    Optional[float] = None
    target_upside_pct:   Optional[float] = None   # % upside to mean target

    # Sector & Industry (59a)
    sector:          Optional[str] = None    # e.g. "Consumer Cyclical"
    industry:        Optional[str] = None    # e.g. "Luxury Goods"

    # Forward estimates (59f)
    forward_pe:          Optional[float] = None
    next_earnings_date:  Optional[str]   = None    # "YYYY-MM-DD"
    earnings_estimate:   Optional[float] = None    # consensus EPS

    # Governance risk (59e) — ISS scores 1-10 (10 = highest risk)
    overall_risk:    Optional[int] = None
    audit_risk:      Optional[int] = None
    board_risk:      Optional[int] = None

    # Margins (59h)
    operating_margin:  Optional[float] = None   # %
    gross_margin:      Optional[float] = None   # %
    ebitda_margin:     Optional[float] = None   # %

    # Cash & debt (59i)
    total_cash_cr:   Optional[float] = None
    total_debt_cr:   Optional[float] = None

    # Valuation multiples (59k)
    price_to_sales:  Optional[float] = None
    ev_to_revenue:   Optional[float] = None

    # Dividend (59j)
    payout_ratio:           Optional[float] = None
    five_yr_avg_div_yield:  Optional[float] = None

    # Insider transactions (59g)
    insider_transactions:  list = field(default_factory=list)  # [{"date", "insider", "transaction", "shares", "value"}]

    # Quarterly trend (last 4 quarters, most recent first)
    quarterly_revenue:   list = field(default_factory=list)

    # Recent corporate announcements
    announcements:       list = field(default_factory=list)

    # Score and verdict
    flags:   list[FundamentalFlag] = field(default_factory=list)
    score:   int  = 0
    verdict: str  = "NEUTRAL"
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


# ── Unavailable fallback ─────────────────────────────────────

def _unavailable(symbol: str) -> dict:
    """Return None values when all real data sources fail.

    Never returns fake numbers — prevents LLM hallucination.
    """
    return dict(
        name=symbol, pe=None, pb=None, roe=None, roce=None,
        npm=None, sales_growth=None, profit_growth=None, debt_equity=None,
        current_ratio=None, promoter_holding=None, pledged_pct=None, dividend_yield=None,
        _data_source="UNAVAILABLE — all data sources failed (Screener.in + yfinance)",
    )


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

    # ── Governance risk (59e) ────────────────────────────────
    overall_risk = parsed.get("overall_risk")
    if overall_risk is not None:
        if overall_risk >= 8:
            score -= 5
            flags.append(FundamentalFlag("Governance Risk", f"{overall_risk}/10", "WARN",
                                         f"High governance risk (audit={parsed.get('audit_risk')}, board={parsed.get('board_risk')})"))
        elif overall_risk <= 3:
            score += 3
            flags.append(FundamentalFlag("Governance Risk", f"{overall_risk}/10", "GOOD",
                                         "Low governance risk — strong corporate governance"))

    # ── Earnings proximity (59f) ──────────────────────────────
    next_earnings = parsed.get("next_earnings_date")
    if next_earnings:
        try:
            from datetime import date as _date
            earn_dt = _date.fromisoformat(str(next_earnings)[:10])
            days_to_earnings = (earn_dt - _date.today()).days
            if 0 <= days_to_earnings <= 7:
                flags.append(FundamentalFlag("Earnings Soon", f"{days_to_earnings}d away",
                                             "WARN" if days_to_earnings <= 3 else "GOOD",
                                             f"Earnings on {next_earnings} — expect volatility"))
        except (ValueError, TypeError):
            pass

    # ── Payout ratio (59j) ────────────────────────────────────
    payout = parsed.get("payout_ratio")
    if payout is not None:
        if payout > 0.80:
            score -= 3
            flags.append(FundamentalFlag("Payout Ratio", f"{payout*100:.0f}%", "WARN",
                                         "Payout > 80% — may be unsustainable"))
        elif 0 < payout < 0.30:
            flags.append(FundamentalFlag("Payout Ratio", f"{payout*100:.0f}%", "GOOD",
                                         "Conservative payout — retains earnings for growth"))

    # ── Insider activity (59g) ────────────────────────────────
    insider_net = parsed.get("insider_net_shares", 0)
    if insider_net and insider_net < -100000:
        score -= 3
        flags.append(FundamentalFlag("Insider Activity", f"Net sell {abs(insider_net):,.0f} shares", "WARN",
                                     parsed.get("insider_summary", "Recent insider selling detected")))

    return max(0, min(100, score)), flags


# ── Main entry point ─────────────────────────────────────────

def _fetch_yfinance(symbol: str) -> dict:
    """
    Fetch fundamental data from yfinance as fallback.

    yfinance provides real PE, PB, D/E, margins, growth, dividend yield
    for any NSE-listed stock via Yahoo Finance.
    """
    # Indices don't have fundamentals (no P/E, ROE, etc.)
    _INDEX_KEYWORDS = {"NIFTY", "BANKNIFTY", "SENSEX", "VIX", "FINNIFTY",
                       "MIDCAP", "NIFTY BANK", "NIFTY 50", "INDIA VIX"}
    if symbol.upper() in _INDEX_KEYWORDS:
        return {}

    try:
        import yfinance as yf

        # Use yfinance_provider's symbol mapping if available
        try:
            from market.yfinance_provider import _to_yf_symbol
            yf_sym = _to_yf_symbol(symbol)
        except ImportError:
            yf_sym = f"{symbol.upper()}.NS"

        ticker = yf.Ticker(yf_sym)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            # Try BSE suffix
            ticker = yf.Ticker(f"{symbol.upper()}.BO")
            info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {}

        # Map yfinance keys to our field names
        roe_raw = info.get("returnOnEquity")
        npm_raw = info.get("profitMargins")
        rev_growth_raw = info.get("revenueGrowth")
        earn_growth_raw = info.get("earningsGrowth")
        div_yield_raw = info.get("dividendYield")

        # Compute ROE and ROCE from annual financial statements
        # yfinance's info.returnOnEquity is often None for Indian stocks,
        # but we can compute it from balance sheet + income statement
        roe_computed = None
        roce_computed = None
        try:
            bs = ticker.balance_sheet
            inc = ticker.income_stmt
            if not bs.empty and not inc.empty:
                net_income = inc.loc['Net Income Common Stockholders'].iloc[0]
                equity = bs.loc['Stockholders Equity'].iloc[0]
                if equity and equity > 0 and not _is_nan(net_income):
                    roe_computed = round((net_income / equity) * 100, 1)

                ebit = inc.loc['EBIT'].iloc[0] if 'EBIT' in inc.index else None
                total_assets = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else None
                current_liab = bs.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bs.index else None
                current_assets = bs.loc['Current Assets'].iloc[0] if 'Current Assets' in bs.index else None

                if ebit and total_assets and current_liab and not _is_nan(ebit):
                    capital_employed = total_assets - current_liab
                    if capital_employed > 0:
                        roce_computed = round((ebit / capital_employed) * 100, 1)

                # Current ratio: Current Assets / Current Liabilities
                if current_assets and current_liab and not _is_nan(current_assets) and current_liab > 0:
                    current_ratio_computed = round(current_assets / current_liab, 2)

                # Interest coverage: EBIT / Interest Expense
                if ebit and not _is_nan(ebit):
                    for idx_name in inc.index:
                        if 'interest' in str(idx_name).lower() and 'expense' in str(idx_name).lower() and 'non' not in str(idx_name).lower():
                            int_exp = abs(inc.loc[idx_name].iloc[0])
                            if int_exp and not _is_nan(int_exp) and int_exp > 0:
                                interest_coverage_computed = round(ebit / int_exp, 1)
                            break
        except Exception:
            pass

        # Prefer computed ROE over info.returnOnEquity (more reliable for Indian stocks)
        roe_final = roe_computed or (round(roe_raw * 100, 1) if roe_raw else None)

        # Current ratio: prefer computed from balance sheet (info often returns None for Indian stocks)
        cr = locals().get('current_ratio_computed') or info.get("currentRatio")

        # Promoter / institutional holding
        insider_pct = info.get("heldPercentInsiders")
        inst_pct = info.get("heldPercentInstitutions")
        promoter = round(insider_pct * 100, 1) if insider_pct else None
        institutional = round(inst_pct * 100, 1) if inst_pct else None

        # ── Price context ────────────────────────────────────
        ltp = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        w52_high = info.get("fiftyTwoWeekHigh")
        w52_low = info.get("fiftyTwoWeekLow")
        pct_from_high = round((ltp - w52_high) / w52_high * 100, 1) if w52_high and ltp else None
        mcap = info.get("marketCap")
        mcap_cr = round(mcap / 1e7, 0) if mcap else None  # convert to crores

        # ── Free cash flow ───────────────────────────────────
        fcf = None
        try:
            cf = ticker.cashflow
            if not cf.empty and 'Free Cash Flow' in cf.index:
                fcf_raw = cf.loc['Free Cash Flow'].iloc[0]
                if fcf_raw and not _is_nan(fcf_raw):
                    fcf = round(fcf_raw / 1e7, 1)  # in crores
        except Exception:
            pass

        # ── Analyst consensus ────────────────────────────────
        analyst_count = info.get("numberOfAnalystOpinions")
        analyst_rating = info.get("recommendationKey")  # "strong_buy", "buy", "hold", etc.
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        target_upside = round((target_mean - ltp) / ltp * 100, 1) if target_mean and ltp else None

        # ── Quarterly results (last 4) ───────────────────────
        quarterly = []
        try:
            q_inc = ticker.quarterly_income_stmt
            if not q_inc.empty:
                for col in q_inc.columns[:4]:
                    q_date = str(col)[:10]
                    rev = q_inc.loc['Total Revenue'].get(col) if 'Total Revenue' in q_inc.index else None
                    ni = q_inc.loc['Net Income Common Stockholders'].get(col) if 'Net Income Common Stockholders' in q_inc.index else None
                    entry = {"quarter": q_date}
                    if rev and not _is_nan(rev):
                        entry["revenue_cr"] = round(rev / 1e7, 1)
                    if ni and not _is_nan(ni):
                        entry["profit_cr"] = round(ni / 1e7, 1)
                    if len(entry) > 1:
                        quarterly.append(entry)
        except Exception:
            pass

        return {
            "name": info.get("longName") or info.get("shortName") or symbol,
            "pe": info.get("trailingPE"),
            "pb": info.get("priceToBook"),
            "roe": roe_final,
            "roce": roce_computed,
            "npm": round(npm_raw * 100, 1) if npm_raw else None,
            "sales_growth": round(rev_growth_raw * 100, 1) if rev_growth_raw else None,
            "profit_growth": round(earn_growth_raw * 100, 1) if earn_growth_raw else None,
            "debt_equity": round(info.get("debtToEquity", 0) / 100, 2) if info.get("debtToEquity") else None,
            "current_ratio": cr,
            "interest_coverage": locals().get('interest_coverage_computed'),
            "free_cash_flow": fcf,
            "promoter_holding": promoter,
            "institutional_holding": institutional,
            "pledged_pct": None,
            "dividend_yield": round(div_yield_raw * 100, 1) if div_yield_raw else None,
            "ev_ebitda": info.get("enterpriseToEbitda"),
            # Price context
            "market_cap": mcap_cr,
            "week52_high": w52_high,
            "week52_low": w52_low,
            "pct_from_52w_high": pct_from_high,
            "avg_50d": info.get("fiftyDayAverage"),
            "avg_200d": info.get("twoHundredDayAverage"),
            "beta": info.get("beta"),
            # Analyst consensus
            "analyst_count": analyst_count,
            "analyst_rating": analyst_rating,
            "target_price_mean": target_mean,
            "target_price_high": target_high,
            "target_price_low": target_low,
            "target_upside_pct": target_upside,
            # 59a: Sector/Industry
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            # 59f: Forward estimates
            "forward_pe": info.get("forwardPE"),
            "next_earnings_date": _extract_earnings_date(ticker),
            "earnings_estimate": info.get("earningsAverage") if hasattr(info, 'get') else None,
            # 59e: Governance risk (ISS scores 1-10)
            "overall_risk": info.get("overallRisk"),
            "audit_risk": info.get("auditRisk"),
            "board_risk": info.get("boardRisk"),
            # 59h: Margins
            "operating_margin": round(info["operatingMargins"] * 100, 1) if info.get("operatingMargins") else None,
            "gross_margin": round(info["grossMargins"] * 100, 1) if info.get("grossMargins") else None,
            "ebitda_margin": round(info["ebitdaMargins"] * 100, 1) if info.get("ebitdaMargins") else None,
            # 59i: Cash & debt
            "total_cash_cr": round(info["totalCash"] / 1e7, 0) if info.get("totalCash") else None,
            "total_debt_cr": round(info["totalDebt"] / 1e7, 0) if info.get("totalDebt") else None,
            # 59k: Valuation multiples
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "ev_to_revenue": info.get("enterpriseToRevenue"),
            # 59j: Dividend
            "payout_ratio": info.get("payoutRatio"),
            "five_yr_avg_div_yield": info.get("fiveYearAvgDividendYield"),
            # 59g: Insider transactions
            "insider_transactions": _extract_insider_txns(ticker),
            # Quarterly trend
            "quarterly_revenue": quarterly,
            "_data_source": "yfinance",
        }
    except Exception:
        return {}


def _extract_earnings_date(ticker) -> Optional[str]:
    """Extract next earnings date from yfinance ticker."""
    try:
        cal = ticker.calendar
        if cal and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if isinstance(dates, list) and dates:
                return str(dates[0])
            return str(dates) if dates else None
    except Exception:
        pass
    return None


def _extract_insider_txns(ticker, limit: int = 5) -> list[dict]:
    """Extract recent insider transactions from yfinance."""
    try:
        ins = ticker.insider_transactions
        if ins is None or ins.empty:
            return []
        results = []
        for _, row in ins.head(limit).iterrows():
            results.append({
                "insider": str(row.get("Insider", "")),
                "position": str(row.get("Position", "")),
                "transaction": str(row.get("Transaction", "")),
                "shares": int(row.get("Shares", 0)),
                "value": float(row.get("Value", 0)),
                "date": str(row.get("Start Date", ""))[:10],
            })
        return results
    except Exception:
        return []


def _is_nan(val) -> bool:
    """Check if a value is NaN (works for float and numpy)."""
    try:
        import math
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def _fetch_nse_announcements(symbol: str, limit: int = 5) -> list[dict]:
    """Fetch recent corporate announcements from NSE."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(
            f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol.upper()}",
            headers=headers, timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        if isinstance(data, list):
            for item in data[:limit]:
                results.append({
                    "date": item.get("an_dt", "")[:20],
                    "desc": item.get("desc", ""),
                    "subject": item.get("attchmntText", item.get("desc", ""))[:100],
                })
        return results
    except Exception:
        return []


def analyse(symbol: str, **_kwargs) -> FundamentalSnapshot:
    """
    Full fundamental analysis for a stock symbol.

    Data cascade (real data only, no mocks):
      1. Screener.in (best: PE, PB, ROE, ROCE, promoter holding, pledging)
      2. yfinance / Yahoo Finance (good: PE, PB, D/E, margins, growth)
      3. None values if both fail (prevents hallucinated analysis)

    Args:
        symbol:   NSE/BSE trading symbol e.g. "RELIANCE", "HDFCBANK"
    """
    parsed = None

    # 1. Screener.in (best: PE, PB, ROE, ROCE, promoter holding, pledging)
    try:
        raw    = _fetch_screener(symbol)
        parsed = _parse_screener(raw)
    except Exception:
        pass

    # 2. yfinance — either primary source or supplement for missing Screener fields
    yf_data = _fetch_yfinance(symbol)

    if not parsed:
        # Screener.in failed entirely — use yfinance as primary
        parsed = yf_data or _unavailable(symbol)
    elif yf_data:
        # Screener.in worked but may have gaps — fill from yfinance
        for key, val in yf_data.items():
            if key.startswith("_"):
                continue  # skip _data_source etc.
            if val is not None and parsed.get(key) is None:
                parsed[key] = val

    # 3. No fake data — return None values so LLM knows data is unavailable
    if not parsed:
        parsed = _unavailable(symbol)

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

    # ── Analyst consensus scoring ────────────────────────────
    analyst_rating = parsed.get("analyst_rating")
    target_upside = parsed.get("target_upside_pct")
    if analyst_rating in ("strong_buy", "buy") and target_upside and target_upside > 20:
        score += 8
        flags.append(FundamentalFlag("Analyst Consensus", f"{analyst_rating} (↑{target_upside:.0f}%)", "GOOD",
                                     f"{parsed.get('analyst_count', '?')} analysts, target upside {target_upside:.0f}%"))
    elif analyst_rating in ("sell", "strong_sell"):
        score -= 8
        flags.append(FundamentalFlag("Analyst Consensus", analyst_rating, "BAD",
                                     "Analysts recommend selling"))

    # ── Free cash flow scoring ────────────────────────────────
    fcf = parsed.get("free_cash_flow")
    if fcf is not None:
        if fcf > 0:
            score += 5
            flags.append(FundamentalFlag("Free Cash Flow", f"₹{fcf:.0f} Cr", "GOOD",
                                         "Positive FCF — earnings are real, not just accounting"))
        elif fcf < 0:
            score -= 5
            flags.append(FundamentalFlag("Free Cash Flow", f"₹{fcf:.0f} Cr", "WARN",
                                         "Negative FCF — burning cash despite reported profits"))

    # Note: governance, earnings, payout, insider scoring is now in _score()

    # ── Fetch announcements (best-effort, non-blocking) ──────
    announcements = _fetch_nse_announcements(symbol)

    good_count = sum(1 for f in flags if f.verdict == "GOOD")
    bad_count  = sum(1 for f in flags if f.verdict == "BAD")
    summary    = (
        f"{good_count} positives / {bad_count} concerns | "
        f"Score: {score}/100 | "
        f"PE={parsed.get('pe') or 'N/A'} | "
        f"ROE={parsed.get('roe') or 'N/A'}%"
    )
    if analyst_rating:
        summary += f" | Analysts: {analyst_rating}"
    if target_upside:
        summary += f" (↑{target_upside:.0f}%)"

    return FundamentalSnapshot(
        symbol               = symbol.upper(),
        name                 = parsed.get("name", symbol),
        pe                   = parsed.get("pe"),
        pb                   = parsed.get("pb"),
        roe                  = parsed.get("roe"),
        roce                 = parsed.get("roce"),
        npm                  = parsed.get("npm"),
        sales_growth         = parsed.get("sales_growth"),
        profit_growth        = parsed.get("profit_growth"),
        debt_equity          = parsed.get("debt_equity"),
        current_ratio        = parsed.get("current_ratio"),
        interest_coverage    = parsed.get("interest_coverage"),
        free_cash_flow       = parsed.get("free_cash_flow"),
        promoter_holding     = parsed.get("promoter_holding"),
        institutional_holding= parsed.get("institutional_holding"),
        pledged_pct          = parsed.get("pledged_pct"),
        dividend_yield       = parsed.get("dividend_yield"),
        ev_ebitda            = parsed.get("ev_ebitda"),
        # Price context
        market_cap           = parsed.get("market_cap"),
        week52_high          = parsed.get("week52_high"),
        week52_low           = parsed.get("week52_low"),
        pct_from_52w_high    = parsed.get("pct_from_52w_high"),
        avg_50d              = parsed.get("avg_50d"),
        avg_200d             = parsed.get("avg_200d"),
        beta                 = parsed.get("beta"),
        # Analyst consensus
        analyst_count        = parsed.get("analyst_count"),
        analyst_rating       = analyst_rating,
        target_price_mean    = parsed.get("target_price_mean"),
        target_price_high    = parsed.get("target_price_high"),
        target_price_low     = parsed.get("target_price_low"),
        target_upside_pct    = target_upside,
        # 59a: Sector/Industry
        sector               = parsed.get("sector"),
        industry             = parsed.get("industry"),
        # 59f: Forward estimates
        forward_pe           = parsed.get("forward_pe"),
        next_earnings_date   = parsed.get("next_earnings_date"),
        earnings_estimate    = parsed.get("earnings_estimate"),
        # 59e: Governance
        overall_risk         = parsed.get("overall_risk"),
        audit_risk           = parsed.get("audit_risk"),
        board_risk           = parsed.get("board_risk"),
        # 59h: Margins
        operating_margin     = parsed.get("operating_margin"),
        gross_margin         = parsed.get("gross_margin"),
        ebitda_margin        = parsed.get("ebitda_margin"),
        # 59i: Cash/Debt
        total_cash_cr        = parsed.get("total_cash_cr"),
        total_debt_cr        = parsed.get("total_debt_cr"),
        # 59k: Valuation multiples
        price_to_sales       = parsed.get("price_to_sales"),
        ev_to_revenue        = parsed.get("ev_to_revenue"),
        # 59j: Dividend
        payout_ratio         = parsed.get("payout_ratio"),
        five_yr_avg_div_yield= parsed.get("five_yr_avg_div_yield"),
        # 59g: Insider transactions
        insider_transactions = parsed.get("insider_transactions", []),
        # Quarterly + announcements
        quarterly_revenue    = parsed.get("quarterly_revenue", []),
        announcements        = announcements,
        flags                = flags,
        score                = score,
        verdict              = verdict,
        summary              = summary,
    )
