"""
market/source_tracker.py
────────────────────────
Tracks which data source served each request and emits fallback warnings.

Usage:
    from market.source_tracker import record_source, get_last_source, warn_fallback

    record_source("options", "nse_scraper")
    get_last_source("options")          # → "nse_scraper"
    warn_fallback("options", "token expired", "nse_scraper")
"""

from __future__ import annotations

_last_source: dict[str, str] = {}


def record_source(data_type: str, source: str) -> None:
    """Record which source served the most recent request for data_type."""
    _last_source[data_type] = source


def get_last_source(data_type: str) -> str:
    """
    Return the source that served the most recent request for data_type.
    Returns "none" if no request has been recorded yet.
    """
    return _last_source.get(data_type, "none")


def warn_fallback(data_type: str, reason: str, source: str) -> None:
    """
    Print a visible warning when the primary source failed and a fallback is used.

    Args:
        data_type: Human-readable label ("options", "quotes", "holdings", etc.)
        reason:    Why the primary failed (exception message or short description)
        source:    The fallback source being used ("nse_scraper", "yfinance", etc.)
    """
    try:
        from rich.console import Console

        _console = Console(stderr=True)
        _console.print(
            f"  [yellow]⚠[/yellow] {data_type}: primary failed ({reason[:80]}) "
            f"— using [dim]{source}[/dim] (may be delayed)"
        )
    except Exception:
        # Rich not available — plain print
        print(f"⚠ {data_type}: primary failed ({reason[:80]}) — using {source}")
