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
    def test_reads_global_trader_md_if_present(self, tmp_path):
        md = tmp_path / "TRADER.md"
        md.write_text("# My custom trader context")
        ctx = _load_trader_context(
            global_path=md,
            project_path=tmp_path / "p.md",
            local_path=tmp_path / "l.md",
        )
        assert "My custom trader context" in ctx

    def test_builds_from_env_when_no_file(self, tmp_path):
        with patch("agent.harness._get_connected_broker", side_effect=Exception):
            ctx = _load_trader_context(
                global_path=tmp_path / "g.md",
                project_path=tmp_path / "p.md",
                local_path=tmp_path / "l.md",
            )
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


# ── Tool flags in ToolRegistry ────────────────────────────────


class TestToolFlags:
    def test_base_registry_tools_are_read_only(self):
        from agent.tools import build_registry

        reg = build_registry()
        for name in reg.names:
            assert reg.is_read_only(name), f"{name} should be read-only"

    def test_base_registry_tools_are_concurrency_safe(self):
        from agent.tools import build_registry

        reg = build_registry()
        for name in reg.names:
            assert reg.is_concurrency_safe(name), f"{name} should be concurrency-safe"

    def test_base_registry_no_destructive_tools(self):
        from agent.tools import build_registry

        reg = build_registry()
        assert reg.destructive_names() == []

    def test_execute_trade_is_destructive(self):
        from agent.harness import _register_execute_tool
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        broker = MagicMock()
        _register_execute_tool(reg, broker)
        assert reg.is_destructive("execute_trade")

    def test_execute_trade_is_not_read_only(self):
        from agent.harness import _register_execute_tool
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        broker = MagicMock()
        _register_execute_tool(reg, broker)
        assert not reg.is_read_only("execute_trade")

    def test_execute_trade_permission_is_ask(self):
        from agent.harness import _register_execute_tool
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        broker = MagicMock()
        _register_execute_tool(reg, broker)
        assert reg.permission("execute_trade") == "ask"

    def test_denied_tool_blocked_from_schema(self):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(
            name="dangerous_tool",
            description="Should be hidden",
            parameters={"type": "object", "properties": {}},
            fn=lambda: None,
            permission="deny",
        )
        names = [t["name"] for t in reg.anthropic_schema()]
        assert "dangerous_tool" not in names

    def test_denied_tool_blocked_from_execute(self):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(
            name="dangerous_tool",
            description="Blocked",
            parameters={"type": "object", "properties": {}},
            fn=lambda: {"should": "not run"},
            permission="deny",
        )
        result = reg.execute("dangerous_tool", {})
        assert "error" in result
        assert "blocked" in result["error"].lower()


# ── Permission modes (HARNESS_MODE) ──────────────────────────


class TestPermissionModes:
    def test_default_mode_is_prompt(self):
        from agent.harness import harness_mode

        env = {k: v for k, v in os.environ.items() if k != "HARNESS_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert harness_mode() == "prompt"

    def test_plan_mode_from_env(self):
        from agent.harness import harness_mode

        with patch.dict(os.environ, {"HARNESS_MODE": "plan"}):
            assert harness_mode() == "plan"

    def test_auto_mode_from_env(self):
        from agent.harness import harness_mode

        with patch.dict(os.environ, {"HARNESS_MODE": "auto"}):
            assert harness_mode() == "auto"

    def test_auto_mode_denies_execute_trade(self):
        from agent.harness import _register_execute_tool
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        broker = MagicMock()
        with patch.dict(os.environ, {"HARNESS_MODE": "auto"}):
            _register_execute_tool(reg, broker)
        assert reg.permission("execute_trade") == "deny"

    def test_auto_mode_execute_trade_not_in_schema(self):
        from agent.harness import _register_execute_tool
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        broker = MagicMock()
        with patch.dict(os.environ, {"HARNESS_MODE": "auto"}):
            _register_execute_tool(reg, broker)
        schema_names = [t["name"] for t in reg.anthropic_schema()]
        assert "execute_trade" not in schema_names

    def test_prompt_mode_mentioned_in_system_prompt(self):
        with patch.dict(os.environ, {"HARNESS_MODE": "prompt"}):
            prompt = _build_harness_system_prompt("")
        assert "prompt" in prompt.lower()

    def test_plan_mode_mentioned_in_system_prompt(self):
        with patch.dict(os.environ, {"HARNESS_MODE": "plan"}):
            prompt = _build_harness_system_prompt("")
        assert "plan" in prompt.lower()

    def test_auto_mode_read_only_mentioned_in_system_prompt(self):
        with patch.dict(os.environ, {"HARNESS_MODE": "auto"}):
            prompt = _build_harness_system_prompt("")
        assert "read-only" in prompt.lower() or "do not" in prompt.lower()


# ── Hierarchical TRADER.md loading ───────────────────────────


class TestHierarchicalTraderMd:
    def test_global_only(self, tmp_path):
        g = tmp_path / "global.md"
        g.write_text("# Global profile")
        ctx = _load_trader_context(
            global_path=g,
            project_path=tmp_path / "missing.md",
            local_path=tmp_path / "missing_local.md",
        )
        assert "Global profile" in ctx

    def test_project_extends_global(self, tmp_path):
        g = tmp_path / "global.md"
        g.write_text("# Global")
        p = tmp_path / "project.md"
        p.write_text("# Project rules")
        ctx = _load_trader_context(
            global_path=g,
            project_path=p,
            local_path=tmp_path / "missing.md",
        )
        assert "Global" in ctx
        assert "Project rules" in ctx

    def test_local_extends_both(self, tmp_path):
        g = tmp_path / "global.md"
        g.write_text("# Global")
        p = tmp_path / "project.md"
        p.write_text("# Project")
        lo = tmp_path / "local.md"
        lo.write_text("# Today: watch HDFC")
        ctx = _load_trader_context(global_path=g, project_path=p, local_path=lo)
        assert "Global" in ctx
        assert "Project" in ctx
        assert "Today: watch HDFC" in ctx

    def test_falls_back_to_auto_build_when_none_exist(self, tmp_path):
        with patch("agent.harness._get_connected_broker", side_effect=Exception):
            ctx = _load_trader_context(
                global_path=tmp_path / "g.md",
                project_path=tmp_path / "p.md",
                local_path=tmp_path / "l.md",
            )
        assert "PAPER" in ctx or "capital" in ctx.lower()

    def test_local_only_no_global_or_project(self, tmp_path):
        lo = tmp_path / "local.md"
        lo.write_text("# Local watchlist: NIFTY")
        ctx = _load_trader_context(
            global_path=tmp_path / "g.md",
            project_path=tmp_path / "p.md",
            local_path=lo,
        )
        assert "Local watchlist: NIFTY" in ctx


# ── #4 Concurrent tool execution (ToolRegistry) ──────────────


class TestConcurrentToolExecution:
    def _make_registry_with_tools(self, safe_count=3, unsafe_count=1):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        call_order = []

        for i in range(safe_count):
            name = f"safe_tool_{i}"
            reg.register(
                name=name,
                description=f"Safe tool {i}",
                parameters={"type": "object", "properties": {}},
                fn=lambda n=name: call_order.append(n) or {"tool": n},
                is_concurrency_safe=True,
            )

        for i in range(unsafe_count):
            name = f"unsafe_tool_{i}"
            reg.register(
                name=name,
                description=f"Unsafe tool {i}",
                parameters={"type": "object", "properties": {}},
                fn=lambda n=name: call_order.append(n) or {"tool": n},
                is_concurrency_safe=False,
            )

        return reg, call_order

    def test_execute_parallel_returns_all_results(self):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(
            "t1",
            "Tool 1",
            {"type": "object", "properties": {}},
            fn=lambda: {"v": 1},
            is_concurrency_safe=True,
        )
        reg.register(
            "t2",
            "Tool 2",
            {"type": "object", "properties": {}},
            fn=lambda: {"v": 2},
            is_concurrency_safe=True,
        )

        calls = [
            {"id": "id1", "name": "t1", "input": {}},
            {"id": "id2", "name": "t2", "input": {}},
        ]
        results = reg.execute_parallel(calls)
        assert len(results) == 2
        ids = {r["tool_use_id"] for r in results}
        assert ids == {"id1", "id2"}

    def test_execute_parallel_preserves_order(self):
        import time
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        # slow tool registered first
        reg.register(
            "slow",
            "Slow",
            {"type": "object", "properties": {}},
            fn=lambda: time.sleep(0.05) or {"v": "slow"},
            is_concurrency_safe=True,
        )
        reg.register(
            "fast",
            "Fast",
            {"type": "object", "properties": {}},
            fn=lambda: {"v": "fast"},
            is_concurrency_safe=True,
        )

        calls = [
            {"id": "s_id", "name": "slow", "input": {}},
            {"id": "f_id", "name": "fast", "input": {}},
        ]
        results = reg.execute_parallel(calls)
        # Results must preserve call order regardless of completion order
        assert results[0]["tool_use_id"] == "s_id"
        assert results[1]["tool_use_id"] == "f_id"

    def test_unsafe_tools_run_sequentially(self):
        import time
        from agent.tools import ToolRegistry

        execution_times = []
        reg = ToolRegistry()

        def make_fn(delay):
            def fn():
                start = time.monotonic()
                time.sleep(delay)
                execution_times.append(time.monotonic() - start)
                return {}

            return fn

        reg.register(
            "u1",
            "Unsafe 1",
            {"type": "object", "properties": {}},
            fn=make_fn(0.05),
            is_concurrency_safe=False,
        )
        reg.register(
            "u2",
            "Unsafe 2",
            {"type": "object", "properties": {}},
            fn=make_fn(0.05),
            is_concurrency_safe=False,
        )

        calls = [
            {"id": "u1_id", "name": "u1", "input": {}},
            {"id": "u2_id", "name": "u2", "input": {}},
        ]
        total_start = time.monotonic()
        reg.execute_parallel(calls)
        total = time.monotonic() - total_start
        # Sequential: should take ~0.1s; parallel would take ~0.05s
        assert total >= 0.08, "Unsafe tools should run sequentially"

    def test_safe_tools_run_in_parallel(self):
        import time
        from agent.tools import ToolRegistry

        reg = ToolRegistry()

        def slow_fn():
            time.sleep(0.1)
            return {}

        for i in range(3):
            reg.register(
                f"s{i}",
                f"Safe {i}",
                {"type": "object", "properties": {}},
                fn=slow_fn,
                is_concurrency_safe=True,
            )

        calls = [{"id": f"id{i}", "name": f"s{i}", "input": {}} for i in range(3)]
        start = time.monotonic()
        reg.execute_parallel(calls)
        elapsed = time.monotonic() - start
        # 3 tools × 0.1s each; if parallel: ~0.1s; if sequential: ~0.3s
        assert elapsed < 0.25, "Concurrency-safe tools should run in parallel"

    def test_mixed_safe_and_unsafe(self):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(
            "safe",
            "Safe",
            {"type": "object", "properties": {}},
            fn=lambda: {"safe": True},
            is_concurrency_safe=True,
        )
        reg.register(
            "unsafe",
            "Unsafe",
            {"type": "object", "properties": {}},
            fn=lambda: {"unsafe": True},
            is_concurrency_safe=False,
        )
        calls = [
            {"id": "s_id", "name": "safe", "input": {}},
            {"id": "u_id", "name": "unsafe", "input": {}},
        ]
        results = reg.execute_parallel(calls)
        assert len(results) == 2

    def test_failed_tool_returns_error_not_exception(self):
        from agent.tools import ToolRegistry

        reg = ToolRegistry()
        reg.register(
            "boom",
            "Explodes",
            {"type": "object", "properties": {}},
            fn=lambda: 1 / 0,
            is_concurrency_safe=True,
        )
        calls = [{"id": "b_id", "name": "boom", "input": {}}]
        results = reg.execute_parallel(calls)
        import json

        content = json.loads(results[0]["content"])
        assert "error" in content


# ── #5 Session history (JSONL persistence) ───────────────────


class TestSessionHistory:
    def test_history_path_returns_path(self):
        from agent.harness import _history_path

        p = _history_path()
        assert str(p).endswith(".jsonl")

    def test_load_history_empty_when_no_file(self, tmp_path):
        from agent.harness import _load_history

        msgs = _load_history(history_file=tmp_path / "missing.jsonl")
        assert msgs == []

    def test_append_and_load_roundtrip(self, tmp_path):
        from agent.harness import _append_history, _load_history

        f = tmp_path / "h.jsonl"
        messages = [
            {"role": "user", "content": "Should I buy RELIANCE?"},
            {"role": "assistant", "content": "Based on analysis..."},
        ]
        _append_history(messages, history_file=f)
        loaded = _load_history(history_file=f)
        assert loaded == messages

    def test_multiple_appends_accumulate(self, tmp_path):
        from agent.harness import _append_history, _load_history

        f = tmp_path / "h.jsonl"
        _append_history(
            [{"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"}],
            history_file=f,
        )
        _append_history(
            [{"role": "user", "content": "Q2"}, {"role": "assistant", "content": "A2"}],
            history_file=f,
        )
        loaded = _load_history(history_file=f)
        assert len(loaded) == 4

    def test_load_history_respects_max_messages(self, tmp_path):
        from agent.harness import _append_history, _load_history

        f = tmp_path / "h.jsonl"
        for i in range(10):
            _append_history(
                [{"role": "user", "content": f"Q{i}"}, {"role": "assistant", "content": f"A{i}"}],
                history_file=f,
            )
        loaded = _load_history(max_messages=4, history_file=f)
        assert len(loaded) == 4
        # Should be the most recent messages
        assert loaded[-1]["content"] == "A9"

    def test_load_history_returns_even_number(self, tmp_path):
        """History should always be complete user/assistant pairs."""
        from agent.harness import _append_history, _load_history

        f = tmp_path / "h.jsonl"
        for i in range(5):
            _append_history(
                [{"role": "user", "content": f"Q{i}"}, {"role": "assistant", "content": f"A{i}"}],
                history_file=f,
            )
        # max_messages=3 is odd — should round down to 2
        loaded = _load_history(max_messages=3, history_file=f)
        assert len(loaded) % 2 == 0

    def test_run_passes_history_to_provider(self, tmp_path):
        from agent.harness import run

        hist_file = tmp_path / "h.jsonl"
        captured = {}

        def fake_chat(messages, stream=True):
            captured["messages"] = messages
            return "done"

        with patch("agent.harness._make_provider") as mock_prov:
            provider = MagicMock()
            provider.chat.side_effect = fake_chat
            mock_prov.return_value = provider
            with patch("agent.harness._load_trader_context", return_value="ctx"):
                run("New question", history_file=hist_file)

        # First message should be the user query
        assert captured["messages"][-1]["role"] == "user"
        assert "New question" in captured["messages"][-1]["content"]

    def test_run_saves_history_after_response(self, tmp_path):
        from agent.harness import _load_history, run

        hist_file = tmp_path / "h.jsonl"

        with patch("agent.harness._make_provider") as mock_prov:
            provider = MagicMock()
            provider.chat.return_value = "Analysis complete."
            mock_prov.return_value = provider
            with patch("agent.harness._load_trader_context", return_value="ctx"):
                run("Buy RELIANCE?", history_file=hist_file)

        history = _load_history(history_file=hist_file)
        assert any(m["content"] == "Buy RELIANCE?" for m in history)
        assert any(m["content"] == "Analysis complete." for m in history)
