"""
market/disk_cache.py
────────────────────
Simple JSON disk cache for market data (holdings, positions, OHLCV).

Used as a last-resort fallback when all live data sources fail.
Cache files are stored in ~/.trading_platform/cache/.

Usage:
    from market.disk_cache import save_cache, load_cache

    save_cache("holdings", [{"symbol": "INFY", "qty": 10}])
    data, cached_at = load_cache("holdings")
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_CACHE_DIR = Path.home() / ".trading_platform" / "cache"


def _cache_file(key: str, cache_dir: Path) -> Path:
    return cache_dir / f"{key}.json"


def save_cache(key: str, data: list, cache_dir: Optional[Path] = None) -> None:
    """
    Save data to disk cache.

    Args:
        key:       Cache key (e.g. "holdings", "positions", "ohlcv_INFY")
        data:      List of dicts to cache
        cache_dir: Override default cache directory (for testing)
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "saved_at": datetime.now().isoformat(),
        "data": data,
    }
    try:
        _cache_file(key, cache_dir).write_text(json.dumps(payload, default=str))
    except Exception:
        pass  # Cache write failure is never fatal


def load_cache(key: str, cache_dir: Optional[Path] = None) -> tuple[list, Optional[datetime]]:
    """
    Load data from disk cache.

    Returns:
        (data, cached_at) — cached_at is None if no cache exists or is corrupt.
        Returns ([], None) when cache is missing or unreadable.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    path = _cache_file(key, cache_dir)

    if not path.exists():
        return [], None

    try:
        payload = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(payload["saved_at"])
        return payload["data"], cached_at
    except Exception:
        return [], None
