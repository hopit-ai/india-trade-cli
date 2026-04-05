"""
engine/backtest_cache.py
────────────────────────
Lightweight JSON cache for backtest results, keyed by strategy ID.

Stores the most-recent run for each strategy so ``strategy learn`` can
display historical performance without re-running the backtest.

Cache file: ~/.trading_platform/backtest_cache.json

Schema (one entry per strategy key):
    {
        "supertrend": {
            "symbol":       "NIFTY",
            "period":       "1y",
            "run_date":     "2026-04-05",
            "start_date":   "2025-04-07",
            "end_date":     "2026-04-02",
            "total_return": -1.13,
            "cagr":         -1.15,
            "sharpe":       -0.06,
            "max_drawdown": -12.03,
            "win_rate":     50.0,
            "total_trades": 2,
            "profit_factor": 0.85,
            "avg_hold":     51.0
        },
        ...
    }
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

_CACHE_PATH = Path.home() / ".trading_platform" / "backtest_cache.json"


def _load() -> dict[str, Any]:
    """Read the entire cache file; return empty dict on first run or corrupt file."""
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text())
    except Exception:
        pass
    return {}


def _save(data: dict[str, Any]) -> None:
    """Persist the cache atomically."""
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(data, indent=2))


def save_result(strategy_key: str, result, symbol: str, period: str) -> None:
    """
    Persist a BacktestResult for *strategy_key*.

    Parameters
    ----------
    strategy_key : str
        The key used in STRATEGIES registry (e.g. ``"supertrend"``).
    result :
        A ``BacktestResult`` instance (duck-typed: reads the public fields).
    symbol : str
        The symbol that was backtested (e.g. ``"NIFTY"``).
    period : str
        The period string (e.g. ``"1y"``).
    """
    cache = _load()
    cache[strategy_key] = {
        "symbol": symbol,
        "period": period,
        "run_date": str(date.today()),
        "start_date": getattr(result, "start_date", ""),
        "end_date": getattr(result, "end_date", ""),
        "total_return": round(getattr(result, "total_return", 0.0), 2),
        "cagr": round(getattr(result, "cagr", 0.0), 2),
        "sharpe": round(getattr(result, "sharpe_ratio", 0.0), 2),
        "max_drawdown": round(getattr(result, "max_drawdown", 0.0), 2),
        "win_rate": round(getattr(result, "win_rate", 0.0), 1),
        "total_trades": getattr(result, "total_trades", 0),
        "profit_factor": round(getattr(result, "profit_factor", 0.0), 2),
        "avg_hold": round(getattr(result, "avg_hold_days", 0.0), 1),
    }
    _save(cache)


def load_result(strategy_key: str) -> dict[str, Any] | None:
    """
    Return the cached result dict for *strategy_key*, or ``None`` if not found.
    """
    return _load().get(strategy_key)
