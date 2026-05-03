"""
skills/example_skill.py
────────────────────────
EXAMPLE: How to write a custom skill plugin for india-trade-cli.

This file is intentionally prefixed with "example_" so it is NOT
auto-loaded at startup. Rename or copy it (without the "example_" prefix)
to a new file in this directory to register it automatically.

Steps:
1. Copy this file:   cp skills/example_skill.py skills/my_skill.py
2. Edit SKILL dict:  update name, description, parameters, fn
3. Restart the CLI:  the skill will be auto-discovered and registered.
"""

from __future__ import annotations


def _get_sector_news(symbol: str, count: int = 3) -> dict:
    """
    Example implementation: return placeholder sector news.
    Replace with your own data source or API call.
    """
    return {
        "symbol": symbol.upper(),
        "headlines": [f"[Placeholder] Headline {i + 1} for {symbol.upper()}" for i in range(count)],
        "count": count,
    }


# ── SKILL descriptor ──────────────��──────────────────────────
# This is the only export that skill_loader.py looks for.

SKILL = {
    "name": "example_sector_news",
    "description": "Fetch the latest sector news headlines for a symbol (example plugin).",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "NSE/BSE ticker symbol, e.g. INFY",
            },
            "count": {
                "type": "integer",
                "description": "Number of headlines to return (default: 3)",
                "default": 3,
            },
        },
        "required": ["symbol"],
    },
    "fn": _get_sector_news,
    "is_read_only": True,
    "is_destructive": False,
}
