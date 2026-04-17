"""
Tests for OpenAI subscription provider deprecation (#82).
"""

from __future__ import annotations

import pytest


class TestOpenAISubscriptionDeprecated:
    def test_instantiation_raises_runtime_error(self, mocker):
        """OpenAISubscriptionProvider must raise immediately — no silent broken usage."""
        from agent.core import OpenAISubscriptionProvider, ToolRegistry

        registry = ToolRegistry()
        with pytest.raises(RuntimeError) as exc_info:
            OpenAISubscriptionProvider("gpt-4o", registry, "You are a trading assistant.")

        err = str(exc_info.value).lower()
        assert "deprecated" in err or "non-functional" in err or "no longer" in err

    def test_error_mentions_openrouter(self, mocker):
        """Error message must provide actionable alternative — OpenRouter."""
        from agent.core import OpenAISubscriptionProvider, ToolRegistry

        registry = ToolRegistry()
        with pytest.raises(RuntimeError) as exc_info:
            OpenAISubscriptionProvider("gpt-4o", registry, "system")

        err = str(exc_info.value).lower()
        assert "openrouter" in err or "open router" in err

    def test_error_mentions_openai_provider(self, mocker):
        """Error must tell user to use AI_PROVIDER=openai instead."""
        from agent.core import OpenAISubscriptionProvider, ToolRegistry

        registry = ToolRegistry()
        with pytest.raises(RuntimeError) as exc_info:
            OpenAISubscriptionProvider("gpt-4o", registry, "system")

        err = str(exc_info.value)
        assert "openai" in err.lower()
