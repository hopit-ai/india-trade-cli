"""Tests for agent/core.py — provider selection, model defaults, message helpers."""

import pytest
from unittest.mock import patch, MagicMock

from agent.core import (
    _default_model,
    _user_msg,
    _assistant_msg,
    _auto_detect_provider,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
    PROVIDER_ANTHROPIC,
    PROVIDER_CLAUDE_CLI,
    PROVIDER_OLLAMA,
    PROVIDER_GEMINI_SUB,
    OPENAI_DEFAULT_MODEL,
    GEMINI_DEFAULT_MODEL,
    ANTHROPIC_DEFAULT_MODEL,
    OLLAMA_DEFAULT_MODEL,
    ClaudeCLIProvider,
    MAX_TOOL_ROUNDS,
    ALL_PROVIDERS,
    _print_tool_call,
)


# ── Default model selection ──────────────────────────────────


class TestDefaultModel:
    def test_openai(self):
        assert _default_model(PROVIDER_OPENAI) == OPENAI_DEFAULT_MODEL

    def test_gemini(self):
        assert _default_model(PROVIDER_GEMINI) == GEMINI_DEFAULT_MODEL

    def test_anthropic(self):
        assert _default_model(PROVIDER_ANTHROPIC) == ANTHROPIC_DEFAULT_MODEL

    def test_ollama(self):
        assert _default_model(PROVIDER_OLLAMA) == OLLAMA_DEFAULT_MODEL

    def test_unknown_falls_back_to_anthropic(self):
        assert _default_model("unknown") == ANTHROPIC_DEFAULT_MODEL

    def test_claude_cli_gets_anthropic_model(self):
        assert _default_model(PROVIDER_CLAUDE_CLI) == ANTHROPIC_DEFAULT_MODEL

    def test_gemini_sub(self):
        assert _default_model(PROVIDER_GEMINI_SUB) == GEMINI_DEFAULT_MODEL


# ── Auto-detect provider ────────────────────────────────────


class TestAutoDetectProvider:
    def test_openai_key_detected(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert _auto_detect_provider() == PROVIDER_OPENAI

    def test_anthropic_key_detected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert _auto_detect_provider() == PROVIDER_ANTHROPIC

    def test_gemini_key_detected(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "AIza-test")
        assert _auto_detect_provider() == PROVIDER_GEMINI


# ── Message helpers ──────────────────────────────────────────


class TestMessageHelpers:
    def test_user_msg(self):
        msg = _user_msg("hello")
        assert msg["role"] == "user"
        assert msg["content"] == "hello"

    def test_assistant_msg(self):
        msg = _assistant_msg("response")
        assert msg["role"] == "assistant"
        assert msg["content"] == "response"

    def test_user_msg_empty(self):
        msg = _user_msg("")
        assert msg["content"] == ""

    def test_assistant_msg_multiline(self):
        msg = _assistant_msg("line1\nline2")
        assert "\n" in msg["content"]


# ── Provider constants ───────────────────────────────────────


class TestProviderConstants:
    def test_all_providers_list(self):
        assert PROVIDER_ANTHROPIC in ALL_PROVIDERS
        assert PROVIDER_OPENAI in ALL_PROVIDERS
        assert PROVIDER_GEMINI in ALL_PROVIDERS
        assert PROVIDER_CLAUDE_CLI in ALL_PROVIDERS
        assert PROVIDER_OLLAMA in ALL_PROVIDERS

    def test_max_tool_rounds(self):
        assert MAX_TOOL_ROUNDS > 0
        assert isinstance(MAX_TOOL_ROUNDS, int)


# ── OpenAI provider (mocked) ────────────────────────────────


class TestOpenAIProvider:
    def test_construction_with_env_key(self, monkeypatch):
        """OpenAIProvider should construct when OPENAI_API_KEY is set."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock the openai import
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_sdk}):
            from agent.core import OpenAIProvider
            from agent.tools import build_registry

            reg = build_registry()
            p = OpenAIProvider(
                model="gpt-4o",
                registry=reg,
                system_prompt="test",
            )
            assert "OpenAI" in p.provider_name

    def test_custom_base_url_in_provider_name(self, monkeypatch):
        """Custom base URL should show in provider_name."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_sdk}):
            from agent.core import OpenAIProvider
            from agent.tools import build_registry

            reg = build_registry()
            p = OpenAIProvider(
                model="llama3",
                registry=reg,
                system_prompt="test",
                base_url="http://localhost:11434/v1",
            )
            assert "localhost" in p.provider_name


# ── Anthropic provider (mocked) ──────────────────────────────


class TestAnthropicProvider:
    def test_missing_key_raises(self, monkeypatch):
        """AnthropicProvider should raise when no API key available."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("_CLI_BATCH_MODE", "1")  # prevent interactive prompt
        mock_sdk = MagicMock()
        with (
            patch.dict("sys.modules", {"anthropic": mock_sdk}),
            patch("config.credentials._kr_get", return_value=None),
        ):
            from agent.core import AnthropicProvider
            from agent.tools import build_registry

            reg = build_registry()
            with pytest.raises(RuntimeError):
                AnthropicProvider(
                    model="claude-opus-4-5",
                    registry=reg,
                    system_prompt="test",
                )


# ── Claude CLI provider ─────────────────────────────────────


class TestClaudeCLIProvider:
    def test_missing_cli_raises(self, monkeypatch):
        """ClaudeCLIProvider should raise if claude CLI is not found."""
        import shutil

        with patch.object(shutil, "which", return_value=None):
            from agent.tools import build_registry

            reg = build_registry()
            with pytest.raises(RuntimeError, match="Claude CLI not found"):
                ClaudeCLIProvider(
                    model="claude-opus-4-5",
                    registry=reg,
                    system_prompt="test",
                )

    def test_provider_name(self, monkeypatch):
        """Provider name should mention subscription."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            from agent.tools import build_registry

            reg = build_registry()
            p = ClaudeCLIProvider(
                model="claude-opus-4-5",
                registry=reg,
                system_prompt="test",
            )
            assert "Subscription" in p.provider_name or "CLI" in p.provider_name


# ── Print tool call ──────────────────────────────────────────


class TestPrintToolCall:
    def test_does_not_raise(self):
        """_print_tool_call should not raise on any input."""
        _print_tool_call("get_quote", {"symbol": "RELIANCE"})
        _print_tool_call("unknown_tool", {})
        _print_tool_call("tool", {"a": 1, "b": [1, 2, 3]})
