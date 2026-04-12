"""
Tests for hard risk limits (#154).
"""

from __future__ import annotations

import os
import pytest
from datetime import date


@pytest.fixture(autouse=True)
def temp_risk_db(tmp_path, monkeypatch):
    """Each test gets an isolated in-memory risk DB."""
    monkeypatch.setenv("RISK_DB_PATH", str(tmp_path / "risk_limits.db"))
    yield


def _fresh_limits(**env_overrides):
    """Create a fresh RiskLimits instance with optional env overrides."""
    import importlib
    import engine.risk_limits as rl_mod

    # Patch env before importing
    for k, v in env_overrides.items():
        os.environ[k] = str(v)

    # Re-create instance to pick up new env
    return rl_mod.RiskLimits()


class TestDailyLossCap:
    def test_blocks_when_loss_exceeds_cap(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.setenv("MAX_DAILY_LOSS", "1000")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-1200.0)

        with pytest.raises(RiskLimitError, match="daily loss"):
            rl.check("INFY", "BUY", 1, 1400.0)

    def test_allows_when_within_cap(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        monkeypatch.setenv("MAX_DAILY_LOSS", "5000")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-2000.0)

        rl.check("INFY", "BUY", 1, 1400.0)  # should not raise

    def test_default_cap_is_20000(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.delenv("MAX_DAILY_LOSS", raising=False)
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-21000.0)

        with pytest.raises(RiskLimitError):
            rl.check("INFY", "BUY", 1, 1400.0)

    def test_error_message_includes_amounts(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.setenv("MAX_DAILY_LOSS", "1000")
        rl = RiskLimits()
        rl.record_trade("INFY", "SELL", 10, 1400.0, pnl=-1500.0)

        with pytest.raises(RiskLimitError) as exc_info:
            rl.check("INFY", "BUY", 1, 1400.0)

        assert "1,500" in str(exc_info.value) or "1500" in str(exc_info.value)


class TestMaxDailyTrades:
    def test_blocks_after_max_trades(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.setenv("MAX_DAILY_TRADES", "3")
        rl = RiskLimits()
        for i in range(3):
            rl.record_trade(f"STOCK{i}", "BUY", 1, 100.0)

        with pytest.raises(RiskLimitError, match="daily.*trade|trade.*limit"):
            rl.check("NEWSTOCK", "BUY", 1, 100.0)

    def test_allows_at_max_trades(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        monkeypatch.setenv("MAX_DAILY_TRADES", "3")
        rl = RiskLimits()
        for i in range(2):
            rl.record_trade(f"STOCK{i}", "BUY", 1, 100.0)

        rl.check("STOCK2", "BUY", 1, 100.0)  # should not raise (2 recorded, checking 3rd)

    def test_default_max_trades_is_20(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.delenv("MAX_DAILY_TRADES", raising=False)
        rl = RiskLimits()
        for i in range(20):
            rl.record_trade(f"S{i}", "BUY", 1, 100.0)

        with pytest.raises(RiskLimitError):
            rl.check("S21", "BUY", 1, 100.0)


class TestMaxTradesPerSymbol:
    def test_blocks_after_symbol_limit(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        monkeypatch.setenv("MAX_TRADES_PER_SYMBOL", "2")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 5, 1400.0)
        rl.record_trade("INFY", "SELL", 5, 1410.0)

        with pytest.raises(RiskLimitError, match="INFY|symbol"):
            rl.check("INFY", "BUY", 1, 1400.0)

    def test_allows_different_symbols(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        monkeypatch.setenv("MAX_TRADES_PER_SYMBOL", "2")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 5, 1400.0)
        rl.record_trade("INFY", "SELL", 5, 1410.0)

        rl.check("TCS", "BUY", 1, 3500.0)  # different symbol — should not raise


class TestStatusReport:
    def test_get_status_returns_dict(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        rl = RiskLimits()
        status = rl.get_status()

        assert "daily_loss" in status
        assert "trades_today" in status
        assert "max_daily_loss" in status
        assert "max_daily_trades" in status

    def test_status_reflects_recorded_trades(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-500.0)
        rl.record_trade("TCS", "BUY", 5, 3500.0, pnl=-200.0)

        status = rl.get_status()
        assert status["trades_today"] == 2
        assert status["daily_loss"] == pytest.approx(-700.0)


class TestNoPyramiding:
    def test_blocks_buying_into_losing_long(self, monkeypatch):
        from engine.risk_limits import RiskLimits, RiskLimitError

        rl = RiskLimits()
        # Simulate: held INFY avg 1400, current price is 1300 (losing)
        # Trying to add more INFY = pyramiding into loser
        with pytest.raises(RiskLimitError, match="pyramid|losing"):
            rl.check(
                "INFY", "BUY", 10, 1300.0,
                current_position={"avg_price": 1400.0, "quantity": 50}
            )

    def test_allows_buying_into_winning_long(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        rl = RiskLimits()
        # Held INFY avg 1200, current price 1400 (winning) — ok to add more
        rl.check(
            "INFY", "BUY", 10, 1400.0,
            current_position={"avg_price": 1200.0, "quantity": 50}
        )  # should not raise

    def test_allows_closing_losing_position(self, monkeypatch):
        from engine.risk_limits import RiskLimits

        rl = RiskLimits()
        # SELL of a losing long = closing/reducing, not pyramiding — should be allowed
        rl.check(
            "INFY", "SELL", 10, 1300.0,
            current_position={"avg_price": 1400.0, "quantity": 50}
        )  # should not raise

    def test_no_position_allows_new_buy(self):
        from engine.risk_limits import RiskLimits

        rl = RiskLimits()
        rl.check("INFY", "BUY", 10, 1400.0, current_position=None)  # no position = ok
