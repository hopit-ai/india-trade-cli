"""Tests for agent/core.py — provider selection, model defaults, message helpers."""

import os
import pytest

from agent.core import (
    _default_model, _user_msg, _assistant_msg, _auto_detect_provider,
    PROVIDER_OPENAI, PROVIDER_GEMINI, PROVIDER_ANTHROPIC,
    PROVIDER_CLAUDE_CLI, OpenAIProvider,
    OPENAI_DEFAULT_MODEL, GEMINI_DEFAULT_MODEL, ANTHROPIC_DEFAULT_MODEL,
)

# Ollama constants may not exist on main yet
PROVIDER_OLLAMA = getattr(__import__("agent.core", fromlist=["PROVIDER_OLLAMA"]), "PROVIDER_OLLAMA", None)
OLLAMA_DEFAULT_MODEL = getattr(__import__("agent.core", fromlist=["OLLAMA_DEFAULT_MODEL"]), "OLLAMA_DEFAULT_MODEL", None)


class TestDefaultModel:
    def test_openai(self):
        assert _default_model(PROVIDER_OPENAI) == OPENAI_DEFAULT_MODEL

    def test_gemini(self):
        assert _default_model(PROVIDER_GEMINI) == GEMINI_DEFAULT_MODEL

    def test_anthropic(self):
        assert _default_model(PROVIDER_ANTHROPIC) == ANTHROPIC_DEFAULT_MODEL

    @pytest.mark.skipif(PROVIDER_OLLAMA is None, reason="Ollama not in this branch")
    def test_ollama(self):
        assert _default_model(PROVIDER_OLLAMA) == OLLAMA_DEFAULT_MODEL

    def test_unknown_falls_back_to_anthropic(self):
        assert _default_model("unknown") == ANTHROPIC_DEFAULT_MODEL


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


class TestMessageHelpers:
    def test_user_msg(self):
        msg = _user_msg("hello")
        assert msg["role"] == "user"
        assert msg["content"] == "hello"

    def test_assistant_msg(self):
        msg = _assistant_msg("response")
        assert msg["role"] == "assistant"
        assert msg["content"] == "response"


class TestOpenAIProvider:
    def test_construction_with_env_key(self, monkeypatch):
        """OpenAIProvider should construct when OPENAI_API_KEY is set."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        from agent.tools import build_registry

        reg = build_registry()
        p = OpenAIProvider(
            model="gpt-4o",
            registry=reg,
            system_prompt="test",
        )
        assert "OpenAI" in p.provider_name
