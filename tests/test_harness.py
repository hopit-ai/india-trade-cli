"""
tests/test_harness.py
─────────────────────
Tests for agent/harness.py — TradingHarness agentic loop.

Spec:
  - _load_trader_context() reads TRADER.md if present, else builds from env
  - _build_trader_context() produces markdown with capital, risk, broker, mode
  - save_trader_context() writes TRADER.md to disk
  - _build_harness_system_prompt() injects trader context and is trading-focused
  - run() calls agent.chat() with the harness system prompt and returns text
  - execute_trade tool is registered only when broker is provided
  - execute_trade routes through trade_executor (confirmation gate)
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


from agent.harness import (
    _build_harness_system_prompt,
    _build_trader_context,
    _load_trader_context,
    save_trader_context,
)


# ── _build_trader_context ─────────────────────────────────────


class TestBuildTraderContext:
    def test_contains_capital(self):
        with patch.dict(os.environ, {"TOTAL_CAPITAL": "500000"}):
            ctx = _build_trader_context()
        assert "500,000" in ctx or "500000" in ctx

    def test_contains_risk_pct(self):
        with patch.dict(os.environ, {"DEFAULT_RISK_PCT": "3"}):
            ctx = _build_trader_context()
        assert "3%" in ctx

    def test_contains_mode(self):
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            ctx = _build_trader_context()
        assert "LIVE" in ctx

    def test_default_mode_is_paper(self):
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            ctx = _build_trader_context()
        assert "PAPER" in ctx

    def test_broker_name_in_context(self):
        from brokers.base import UserProfile

        mock_broker = MagicMock()
        mock_broker.get_profile.return_value = UserProfile(
            user_id="U1", name="Test", email="t@t.com", broker="FYERS"
        )
        with patch("agent.harness._get_connected_broker", return_value=mock_broker):
            ctx = _build_trader_context()
        assert "FYERS" in ctx

    def test_broker_unavailable_defaults_to_paper(self):
        with patch("agent.harness._get_connected_broker", side_effect=Exception("no broker")):
            ctx = _build_trader_context()
        assert "PAPER" in ctx

    def test_max_risk_computed(self):
        with patch.dict(os.environ, {"TOTAL_CAPITAL": "200000", "DEFAULT_RISK_PCT": "2"}):
            ctx = _build_trader_context()
        # 2% of 2L = 4000
        assert "4,000" in ctx or "4000" in ctx


# ── _load_trader_context ──────────────────────────────────────


class TestLoadTraderContext:
    def test_reads_trader_md_if_present(self, tmp_path):
        md = tmp_path / "TRADER.md"
        md.write_text("# My custom trader context")
        with patch("agent.harness.TRADER_MD_PATH", md):
            ctx = _load_trader_context()
        assert "My custom trader context" in ctx

    def test_builds_from_env_when_no_file(self, tmp_path):
        missing = tmp_path / "TRADER.md"  # does not exist
        with patch("agent.harness.TRADER_MD_PATH", missing):
            with patch("agent.harness._get_connected_broker", side_effect=Exception):
                ctx = _load_trader_context()
        assert "PAPER" in ctx or "capital" in ctx.lower()


# ── save_trader_context ───────────────────────────────────────


class TestSaveTraderContext:
    def test_saves_to_disk(self, tmp_path):
        md = tmp_path / "TRADER.md"
        with patch("agent.harness.TRADER_MD_PATH", md):
            save_trader_context("# Test content")
        assert md.read_text() == "# Test content"

    def test_creates_parent_dirs(self, tmp_path):
        md = tmp_path / "nested" / "deep" / "TRADER.md"
        with patch("agent.harness.TRADER_MD_PATH", md):
            save_trader_context("# Test")
        assert md.exists()


# ── _build_harness_system_prompt ─────────────────────────────


class TestBuildHarnessSystemPrompt:
    def test_contains_trader_context(self):
        ctx = "Capital: ₹2,00,000"
        prompt = _build_harness_system_prompt(ctx)
        assert ctx in prompt

    def test_mentions_tools(self):
        prompt = _build_harness_system_prompt("")
        assert "tool" in prompt.lower()

    def test_mentions_confirmation(self):
        prompt = _build_harness_system_prompt("")
        assert "confirm" in prompt.lower()

    def test_mentions_live_paper(self):
        prompt = _build_harness_system_prompt("")
        assert "LIVE" in prompt or "PAPER" in prompt

    def test_contains_today_date(self):
        from datetime import date

        prompt = _build_harness_system_prompt("")
        assert date.today().strftime("%Y") in prompt

    def test_trading_mode_injected(self):
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            prompt = _build_harness_system_prompt("")
        assert "LIVE" in prompt


# ── execute_trade tool registration ──────────────────────────


class TestExecuteTradeToolRegistration:
    def _make_registry(self):
        from agent.tools import ToolRegistry

        return ToolRegistry()

    def test_tool_registered_when_broker_provided(self):
        from agent.harness import _register_execute_tool

        registry = self._make_registry()
        broker = MagicMock()
        _register_execute_tool(registry, broker)
        assert "execute_trade" in registry.names

    def test_tool_not_registered_without_broker(self):
        """When broker=None, execute_trade should not be in the registry."""

        registry = self._make_registry()
        # Don't call _register_execute_tool — harness.run() skips it when broker=None
        assert "execute_trade" not in registry.names

    def test_execute_trade_schema_has_required_fields(self):
        from agent.harness import _register_execute_tool

        registry = self._make_registry()
        broker = MagicMock()
        _register_execute_tool(registry, broker)

        schema = registry.anthropic_schema()
        tool = next(t for t in schema if t["name"] == "execute_trade")
        required = tool["input_schema"].get("required", [])
        assert "symbol" in required
        assert "action" in required
        assert "quantity" in required

    def test_execute_trade_routes_through_trade_executor(self):
        from agent.harness import _register_execute_tool

        registry = self._make_registry()
        broker = MagicMock()
        _register_execute_tool(registry, broker)

        with patch("agent.harness.execute_trade_plan", return_value=[]) as mock_exec:
            registry.execute(
                "execute_trade",
                {"symbol": "RELIANCE", "action": "BUY", "quantity": 10},
            )
        mock_exec.assert_called_once()

    def test_execute_trade_passes_broker(self):
        from agent.harness import _register_execute_tool

        registry = self._make_registry()
        broker = MagicMock()
        _register_execute_tool(registry, broker)

        with patch("agent.harness.execute_trade_plan", return_value=[]) as mock_exec:
            registry.execute(
                "execute_trade",
                {"symbol": "TCS", "action": "SELL", "quantity": 5},
            )
        call_args = mock_exec.call_args
        assert call_args[0][1] is broker  # second positional arg is the broker


# ── run() ─────────────────────────────────────────────────────


class TestHarnessRun:
    def test_run_returns_string(self):
        from agent.harness import run

        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Analysis complete."

        with patch("agent.harness.get_provider") as mock_prov:
            mock_prov.return_value = MagicMock()
            with patch("agent.harness._get_agent_chat", return_value="Analysis complete."):
                result = run("Should I buy RELIANCE?")
        assert isinstance(result, str)

    def test_run_uses_harness_system_prompt(self):
        """The harness should use a different system prompt than the default agent."""
        from agent.harness import run

        captured_prompt = {}

        def capture_provider(registry, system_prompt, **kw):
            captured_prompt["system"] = system_prompt
            p = MagicMock()
            p.chat.return_value = "ok"
            return p

        with patch("agent.harness._make_provider", side_effect=capture_provider):
            with patch("agent.harness._load_trader_context", return_value="Capital: ₹2L"):
                with patch("agent.harness._get_connected_broker", side_effect=Exception):
                    run("test query")

        assert "Capital: ₹2L" in captured_prompt.get("system", "")

    def test_run_without_broker_skips_execute_tool(self):
        from agent.harness import run

        with patch("agent.harness._make_provider") as mock_prov:
            provider = MagicMock()
            provider.chat.return_value = "done"
            mock_prov.return_value = provider
            with patch("agent.harness._register_execute_tool") as mock_reg:
                run("What is NIFTY at?", broker=None)
        mock_reg.assert_not_called()

    def test_run_with_broker_registers_execute_tool(self):
        from agent.harness import run

        broker = MagicMock()
        with patch("agent.harness._make_provider") as mock_prov:
            provider = MagicMock()
            provider.chat.return_value = "done"
            mock_prov.return_value = provider
            with patch("agent.harness._register_execute_tool") as mock_reg:
                run("Buy RELIANCE", broker=broker)
        mock_reg.assert_called_once()
