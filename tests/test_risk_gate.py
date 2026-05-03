"""
Tests for deterministic risk gate (#174).

All tests are pure Python — no LLM, no network.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def temp_risk_db(tmp_path, monkeypatch):
    """Each test gets an isolated in-memory risk DB."""
    monkeypatch.setenv("RISK_DB_PATH", str(tmp_path / "risk_limits.db"))
    # Ensure capital env is predictable
    monkeypatch.setenv("TOTAL_CAPITAL", "200000")
    yield


# ── AllowedAction dataclass ───────────────────────────────────


class TestAllowedActionDataclass:
    def test_has_required_fields(self):
        from engine.risk_gate import AllowedAction

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BUY_ONLY",
            max_qty=100,
            max_capital=140000.0,
            flags=[],
        )
        assert a.symbol == "INFY"
        assert a.allowed is True
        assert a.direction == "BUY_ONLY"
        assert a.max_qty == 100
        assert a.max_capital == 140000.0
        assert a.flags == []

    def test_default_block_reason_is_empty(self):
        from engine.risk_gate import AllowedAction

        a = AllowedAction(
            symbol="TCS",
            allowed=True,
            direction="BOTH",
            max_qty=50,
            max_capital=175000.0,
            flags=[],
        )
        assert a.block_reason == ""

    def test_default_warnings_is_empty_list(self):
        from engine.risk_gate import AllowedAction

        a = AllowedAction(
            symbol="RELIANCE",
            allowed=True,
            direction="BOTH",
            max_qty=50,
            max_capital=100000.0,
            flags=[],
        )
        assert a.warnings == []

    def test_blocked_action_fields(self):
        from engine.risk_gate import AllowedAction

        a = AllowedAction(
            symbol="SBIN",
            allowed=False,
            direction="NONE",
            max_qty=0,
            max_capital=0.0,
            flags=[],
            block_reason="Daily loss cap reached",
        )
        assert a.allowed is False
        assert a.direction == "NONE"
        assert a.max_qty == 0
        assert a.block_reason == "Daily loss cap reached"

    def test_flags_and_warnings_are_separate_lists(self):
        from engine.risk_gate import AllowedAction

        a = AllowedAction(
            symbol="HDFCBANK",
            allowed=True,
            direction="BOTH",
            max_qty=20,
            max_capital=30000.0,
            flags=["EARNINGS_PROXIMITY"],
            warnings=["High IV rank (72)"],
        )
        assert "EARNINGS_PROXIMITY" in a.flags
        assert "High IV rank (72)" in a.warnings
        assert a.flags is not a.warnings


# ── compute_allowed_actions — happy path ─────────────────────


class TestComputeAllowedActionsHappyPath:
    def test_returns_allowed_action_instance(self):
        from engine.risk_gate import compute_allowed_actions, AllowedAction

        result = compute_allowed_actions("INFY", "NSE")
        assert isinstance(result, AllowedAction)

    def test_allowed_when_no_limits_hit(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        assert result.allowed is True

    def test_symbol_is_uppercased(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions("infy", "nse")
        assert result.symbol == "INFY"

    def test_max_qty_positive_when_allowed(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        assert result.max_qty > 0

    def test_max_capital_positive_when_allowed(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        assert result.max_capital > 0.0


# ── Daily loss cap blocks ─────────────────────────────────────


class TestDailyLossCapBlocks:
    def test_allowed_false_when_loss_cap_hit(self, monkeypatch):
        """When daily loss cap is hit, compute_allowed_actions returns allowed=False."""
        from engine.risk_limits import RiskLimits
        import engine.risk_gate as rg_mod

        # Create a fresh RiskLimits with a small cap and record a loss
        monkeypatch.setenv("MAX_DAILY_LOSS", "500")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-600.0)

        # Patch the singleton used inside risk_gate
        monkeypatch.setattr(rg_mod, "_get_risk_limits", lambda: rl)

        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions("TCS", "NSE", capital=200000.0)
        assert result.allowed is False
        assert result.direction == "NONE"
        assert result.max_qty == 0

    def test_block_reason_non_empty_when_blocked(self, monkeypatch):
        from engine.risk_limits import RiskLimits
        import engine.risk_gate as rg_mod

        monkeypatch.setenv("MAX_DAILY_LOSS", "500")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-600.0)
        monkeypatch.setattr(rg_mod, "_get_risk_limits", lambda: rl)

        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions("TCS", "NSE", capital=200000.0)
        assert result.block_reason != ""

    def test_max_capital_zero_when_blocked(self, monkeypatch):
        from engine.risk_limits import RiskLimits
        import engine.risk_gate as rg_mod

        monkeypatch.setenv("MAX_DAILY_LOSS", "500")
        rl = RiskLimits()
        rl.record_trade("INFY", "BUY", 10, 1400.0, pnl=-600.0)
        monkeypatch.setattr(rg_mod, "_get_risk_limits", lambda: rl)

        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions("TCS", "NSE", capital=200000.0)
        assert result.max_capital == 0.0


# ── Earnings proximity ────────────────────────────────────────


class TestEarningsProximity:
    def test_flag_set_when_earnings_within_3_days(self):
        from datetime import date, timedelta
        from engine.risk_gate import compute_allowed_actions

        today = date.today()
        upcoming = today + timedelta(days=2)  # 2 days away — within 3

        # Inject a portfolio that has an upcoming earnings event
        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            upcoming_events={"INFY": upcoming.isoformat()},
        )
        assert "EARNINGS_PROXIMITY" in result.flags

    def test_max_qty_halved_when_earnings_within_3_days(self):
        from datetime import date, timedelta
        from engine.risk_gate import compute_allowed_actions

        today = date.today()
        upcoming = today + timedelta(days=1)

        result_no_event = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        result_with_event = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            upcoming_events={"INFY": upcoming.isoformat()},
        )
        # qty should be halved (or at most equal if already 0 or 1)
        assert result_with_event.max_qty <= result_no_event.max_qty // 2 + 1

    def test_flag_not_set_when_earnings_beyond_3_days(self):
        from datetime import date, timedelta
        from engine.risk_gate import compute_allowed_actions

        today = date.today()
        far_away = today + timedelta(days=10)

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            upcoming_events={"INFY": far_away.isoformat()},
        )
        assert "EARNINGS_PROXIMITY" not in result.flags

    def test_flag_set_when_earnings_on_same_day(self):
        from datetime import date
        from engine.risk_gate import compute_allowed_actions

        today = date.today()

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            upcoming_events={"INFY": today.isoformat()},
        )
        assert "EARNINGS_PROXIMITY" in result.flags


# ── Position limit ────────────────────────────────────────────


class TestPositionLimit:
    def test_max_qty_reduced_when_position_near_10pct(self):
        """If existing position + new order > 10% of capital, max_qty is reduced."""
        from engine.risk_gate import compute_allowed_actions

        # Capital = 200000; 10% = 20000
        # Existing INFY position = 10 shares @ 1400 = 14000 (7%)
        # If we can buy at most (20000 - 14000) / 1400 = 4 shares
        portfolio = {"INFY": {"qty": 10, "avg_price": 1400.0, "current_price": 1400.0}}
        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            portfolio=portfolio,
            prices={"INFY": 1400.0},
        )
        # position limit: (20000 - 14000) / 1400 ≈ 4 shares
        assert result.max_qty <= 5  # allow some rounding tolerance

    def test_max_qty_not_reduced_when_position_small(self):
        """If existing position is tiny, the full position limit applies."""
        from engine.risk_gate import compute_allowed_actions

        # Capital = 200000; 10% = 20000
        # Existing INFY position = 1 share @ 1400 = 1400 (0.7%)
        portfolio = {"INFY": {"qty": 1, "avg_price": 1400.0, "current_price": 1400.0}}
        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            portfolio=portfolio,
            prices={"INFY": 1400.0},
        )
        # (20000 - 1400) / 1400 ≈ 13 shares
        assert result.max_qty >= 10

    def test_position_limit_flag_set_when_reduced(self):
        from engine.risk_gate import compute_allowed_actions

        portfolio = {"INFY": {"qty": 10, "avg_price": 1400.0, "current_price": 1400.0}}
        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            portfolio=portfolio,
            prices={"INFY": 1400.0},
        )
        # Position is at 7%; adding more moves it close to 10% — flag should be set
        assert "POSITION_LIMIT" in result.flags

    def test_no_existing_position_uses_full_limit(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            portfolio={},
            prices={"INFY": 1400.0},
        )
        # 10% of 200000 = 20000; 20000 / 1400 = 14 shares
        assert result.max_qty >= 14


# ── Cash check ────────────────────────────────────────────────


class TestCashCheck:
    def test_allowed_false_when_capital_less_than_one_share(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=500.0,  # can't afford 1 share @ 1400
            prices={"INFY": 1400.0},
        )
        assert result.allowed is False

    def test_low_cash_flag_when_capital_less_than_five_shares(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=4000.0,  # can afford 2 shares @ 1400, not 5
            prices={"INFY": 1400.0},
        )
        assert "LOW_CASH" in result.flags

    def test_no_low_cash_flag_when_capital_sufficient(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        assert "LOW_CASH" not in result.flags


# ── VIX regime ────────────────────────────────────────────────


class TestVixRegime:
    def test_high_volatility_flag_when_vix_above_20(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            vix=25.0,
        )
        assert "HIGH_VOLATILITY" in result.flags

    def test_max_qty_halved_when_vix_above_20(self):
        from engine.risk_gate import compute_allowed_actions

        result_normal = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            vix=15.0,
        )
        result_high_vix = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            vix=25.0,
        )
        assert result_high_vix.max_qty <= result_normal.max_qty // 2 + 1

    def test_no_flag_when_vix_below_20(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            vix=18.0,
        )
        assert "HIGH_VOLATILITY" not in result.flags

    def test_no_flag_when_vix_not_provided(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
        )
        assert "HIGH_VOLATILITY" not in result.flags


# ── format_risk_gate_for_llm ──────────────────────────────────


class TestFormatRiskGateForLLM:
    def test_output_contains_risk_gate(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BUY_ONLY",
            max_qty=44,
            max_capital=60000.0,
            flags=["EARNINGS_PROXIMITY"],
        )
        output = format_risk_gate_for_llm(a)
        assert "RISK GATE" in output

    def test_output_contains_hard_constraints(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BUY_ONLY",
            max_qty=44,
            max_capital=60000.0,
            flags=[],
        )
        output = format_risk_gate_for_llm(a)
        assert "HARD CONSTRAINTS" in output

    def test_allowed_status_shows_allowed(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BOTH",
            max_qty=20,
            max_capital=28000.0,
            flags=[],
        )
        output = format_risk_gate_for_llm(a)
        assert "ALLOWED" in output

    def test_blocked_status_shows_blocked(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=False,
            direction="NONE",
            max_qty=0,
            max_capital=0.0,
            flags=[],
            block_reason="Daily loss cap reached",
        )
        output = format_risk_gate_for_llm(a)
        assert "BLOCKED" in output

    def test_block_reason_included_in_output(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        reason = "Daily loss cap reached"
        a = AllowedAction(
            symbol="INFY",
            allowed=False,
            direction="NONE",
            max_qty=0,
            max_capital=0.0,
            flags=[],
            block_reason=reason,
        )
        output = format_risk_gate_for_llm(a)
        assert reason in output

    def test_max_qty_shown_in_output(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BUY_ONLY",
            max_qty=44,
            max_capital=61600.0,
            flags=[],
        )
        output = format_risk_gate_for_llm(a)
        assert "44" in output

    def test_flags_shown_in_output(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="INFY",
            allowed=True,
            direction="BUY_ONLY",
            max_qty=22,
            max_capital=30800.0,
            flags=["EARNINGS_PROXIMITY", "HIGH_VOLATILITY"],
        )
        output = format_risk_gate_for_llm(a)
        assert "EARNINGS_PROXIMITY" in output
        assert "HIGH_VOLATILITY" in output

    def test_returns_string(self):
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm

        a = AllowedAction(
            symbol="TCS",
            allowed=True,
            direction="BOTH",
            max_qty=10,
            max_capital=35000.0,
            flags=[],
        )
        result = format_risk_gate_for_llm(a)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_network_or_llm_calls(self):
        """format_risk_gate_for_llm must be pure — no external calls."""
        from engine.risk_gate import AllowedAction
        from engine.risk_gate_context import format_risk_gate_for_llm
        import socket

        original_connect = socket.socket.connect

        def blocked_connect(*args, **kwargs):
            raise RuntimeError("Network call detected in format_risk_gate_for_llm!")

        socket.socket.connect = blocked_connect
        try:
            a = AllowedAction(
                symbol="INFY",
                allowed=True,
                direction="BOTH",
                max_qty=10,
                max_capital=14000.0,
                flags=[],
            )
            output = format_risk_gate_for_llm(a)
            assert "RISK GATE" in output
        finally:
            socket.socket.connect = original_connect


# ── Edge cases ────────────────────────────────────────────────


class TestEdgeCases:
    def test_unknown_symbol_returns_allowed_action(self):
        """Even for an unknown symbol, we get back an AllowedAction."""
        from engine.risk_gate import compute_allowed_actions, AllowedAction

        result = compute_allowed_actions("UNKNOWNSYM", "NSE")
        assert isinstance(result, AllowedAction)

    def test_zero_capital_blocks_trade(self):
        from engine.risk_gate import compute_allowed_actions

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=0.0,
            prices={"INFY": 1400.0},
        )
        assert result.allowed is False

    def test_multiple_flags_can_coexist(self):
        from datetime import date, timedelta
        from engine.risk_gate import compute_allowed_actions

        today = date.today()
        upcoming = today + timedelta(days=1)

        result = compute_allowed_actions(
            "INFY",
            "NSE",
            capital=200000.0,
            prices={"INFY": 1400.0},
            upcoming_events={"INFY": upcoming.isoformat()},
            vix=25.0,
        )
        assert "EARNINGS_PROXIMITY" in result.flags
        assert "HIGH_VOLATILITY" in result.flags

    def test_compute_does_not_call_network(self):
        """compute_allowed_actions must be deterministic — no network calls."""
        import socket
        from engine.risk_gate import compute_allowed_actions

        original_connect = socket.socket.connect

        def blocked_connect(*args, **kwargs):
            raise RuntimeError("Network call detected in compute_allowed_actions!")

        socket.socket.connect = blocked_connect
        try:
            result = compute_allowed_actions(
                "INFY",
                "NSE",
                capital=200000.0,
                prices={"INFY": 1400.0},
            )
            assert result is not None
        finally:
            socket.socket.connect = original_connect
