"""
tests/test_morning_brief_personal.py
──────────────────────────────────────
Tests for Morning Brief personalisation (#121).

Covers:
  - _print_memory_watchlist: reads TradeMemory, deduplicates by symbol
  - _print_actionable_agenda: generates action items from FII/breadth data
  - Edge cases: empty memory, no FII data, exceptions handled gracefully
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── Helper builders ───────────────────────────────────────────────


def _make_record(
    symbol: str,
    verdict: str = "BULLISH",
    confidence: int = 70,
    days_ago: int = 1,
    stop_loss: float = None,
    target_price: float = None,
) -> MagicMock:
    rec = MagicMock()
    rec.symbol = symbol
    rec.verdict = verdict
    rec.confidence = confidence
    rec.stop_loss = stop_loss
    rec.target_price = target_price
    ts = datetime.now() - timedelta(days=days_ago)
    rec.timestamp = ts.isoformat()
    return rec


def _make_fii(net: float) -> MagicMock:
    f = MagicMock()
    f.fii_net = net
    f.dii_net = 100.0
    return f


def _make_breadth(verdict: str, ratio: float) -> MagicMock:
    b = MagicMock()
    b.verdict = verdict
    b.ad_ratio = ratio
    b.advances = 300
    b.declines = 100
    return b


# ── _print_memory_watchlist ───────────────────────────────────────


class TestPrintMemoryWatchlist:
    def test_no_output_on_empty_memory(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        with patch("engine.memory.TradeMemory") as MockMem:
            MockMem.return_value.query.return_value = []
            _print_memory_watchlist()

        # Nothing should be printed for empty memory
        captured = capsys.readouterr()
        assert "Watchlist" not in captured.out

    def test_shows_watchlist_when_records_present(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        records = [
            _make_record("INFY", "BULLISH", 75, days_ago=2),
            _make_record("RELIANCE", "BEARISH", 60, days_ago=1),
        ]
        with patch("engine.memory.TradeMemory") as MockMem:
            MockMem.return_value.query.return_value = records
            _print_memory_watchlist()

        captured = capsys.readouterr()
        assert "INFY" in captured.out
        assert "RELIANCE" in captured.out

    def test_deduplicates_same_symbol(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        # INFY appears three times — should show only once
        records = [
            _make_record("INFY", "BULLISH", 70, days_ago=1),
            _make_record("INFY", "NEUTRAL", 50, days_ago=3),
            _make_record("INFY", "BEARISH", 40, days_ago=7),
        ]
        with patch("engine.memory.TradeMemory") as MockMem:
            MockMem.return_value.query.return_value = records
            _print_memory_watchlist()

        captured = capsys.readouterr()
        assert captured.out.count("INFY") == 1

    def test_verdict_shown_in_output(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        records = [_make_record("HDFC", "BEARISH", 65, days_ago=0)]
        with patch("engine.memory.TradeMemory") as MockMem:
            MockMem.return_value.query.return_value = records
            _print_memory_watchlist()

        captured = capsys.readouterr()
        assert "BEARISH" in captured.out

    def test_max_8_symbols_displayed(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        records = [_make_record(f"SYM{i}", "BULLISH", 70, days_ago=i) for i in range(15)]
        with patch("engine.memory.TradeMemory") as MockMem:
            MockMem.return_value.query.return_value = records
            _print_memory_watchlist()

        captured = capsys.readouterr()
        # Should not show more than 8 symbols
        displayed = sum(1 for i in range(15) if f"SYM{i}" in captured.out)
        assert displayed <= 8

    def test_graceful_on_exception(self, capsys):
        from app.commands.morning_brief import _print_memory_watchlist

        with patch("engine.memory.TradeMemory", side_effect=Exception("DB error")):
            # Should not raise
            try:
                _print_memory_watchlist()
            except Exception:
                pytest.fail("_print_memory_watchlist raised instead of handling exception")


# ── _print_actionable_agenda ──────────────────────────────────────


class TestPrintActionableAgenda:
    def test_no_output_on_no_inputs(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        _print_actionable_agenda(None, None)
        captured = capsys.readouterr()
        # May or may not have day-of-week item, but no FII/breadth items
        assert "FII sold" not in captured.out
        assert "decline" not in captured.out

    def test_fii_selling_streak_3_days(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        fii = [_make_fii(-1500), _make_fii(-2000), _make_fii(-800)]  # 3 days selling
        _print_actionable_agenda(fii, None)
        captured = capsys.readouterr()
        assert "FII sold" in captured.out or "FII" in captured.out

    def test_fii_buying_streak_3_days(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        fii = [_make_fii(2000), _make_fii(3000), _make_fii(1500)]  # 3 days buying
        _print_actionable_agenda(fii, None)
        captured = capsys.readouterr()
        assert "FII" in captured.out

    def test_no_streak_on_2_days_selling(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        fii = [_make_fii(-1500), _make_fii(-2000)]  # only 2 days — below threshold
        _print_actionable_agenda(fii, None)
        captured = capsys.readouterr()
        assert "consecutive" not in captured.out

    def test_broad_decline_agenda_item(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        breadth = _make_breadth("BROAD_DECLINE", 0.3)
        _print_actionable_agenda(None, breadth)
        captured = capsys.readouterr()
        assert "decline" in captured.out.lower() or "Broad" in captured.out

    def test_broad_rally_agenda_item(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        breadth = _make_breadth("BROAD_RALLY", 3.5)
        _print_actionable_agenda(None, breadth)
        captured = capsys.readouterr()
        assert "rally" in captured.out.lower() or "bull" in captured.out.lower()

    def test_max_5_agenda_items(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        fii = [_make_fii(-2000)] * 5  # 5 days selling
        breadth = _make_breadth("BROAD_DECLINE", 0.2)
        _print_actionable_agenda(fii, breadth)
        captured = capsys.readouterr()
        # Count bullet icons
        icons = captured.out.count("⚠️") + captured.out.count("✅") + captured.out.count("📋") + captured.out.count("📍")
        assert icons <= 5

    def test_handles_empty_fii_list(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        _print_actionable_agenda([], None)
        captured = capsys.readouterr()
        # Should not crash and should not show FII agenda items
        assert "FII sold" not in captured.out

    def test_agenda_title_shown_when_items_exist(self, capsys):
        from app.commands.morning_brief import _print_actionable_agenda

        fii = [_make_fii(-2000), _make_fii(-1500), _make_fii(-3000)]
        _print_actionable_agenda(fii, None)
        captured = capsys.readouterr()
        assert "Agenda" in captured.out
