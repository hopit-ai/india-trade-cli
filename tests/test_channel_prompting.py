"""
Tests for channel-aware prompting (#179).
"""

from __future__ import annotations



class TestGetChannelHint:
    def test_cli_returns_non_empty_string(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("cli")
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_electron_returns_non_empty_string(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("electron")
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_api_returns_non_empty_string(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("api")
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_whatsapp_returns_non_empty_string(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("whatsapp")
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_all_channels_return_output_format_prefix(self):
        from agent.prompts import get_channel_hint

        for channel in ("cli", "electron", "api", "whatsapp"):
            hint = get_channel_hint(channel)
            assert "OUTPUT FORMAT" in hint, f"Channel '{channel}' hint missing OUTPUT FORMAT"

    def test_unknown_channel_defaults_to_cli(self):
        from agent.prompts import get_channel_hint

        unknown = get_channel_hint("unknown_channel_xyz")
        cli_hint = get_channel_hint("cli")
        # Should fall back to cli format
        assert isinstance(unknown, str)
        assert len(unknown) > 0
        # Both should contain similar content (full verbosity)
        assert "full" in unknown.lower() or "full" in cli_hint.lower() or "OUTPUT FORMAT" in unknown

    def test_case_insensitive_channel(self):
        from agent.prompts import get_channel_hint

        lower = get_channel_hint("api")
        upper = get_channel_hint("API")
        assert lower == upper

    def test_whatsapp_hint_mentions_plain_text(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("whatsapp")
        # WhatsApp should discourage markdown
        hint_lower = hint.lower()
        assert "plain" in hint_lower or "no markdown" in hint_lower or "text" in hint_lower

    def test_api_hint_mentions_structured_data(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("api")
        hint_lower = hint.lower()
        assert "structured" in hint_lower or "concise" in hint_lower or "data" in hint_lower

    def test_whatsapp_hint_has_word_limit(self):
        from agent.prompts import get_channel_hint

        hint = get_channel_hint("whatsapp")
        # Should mention a word/character limit
        assert "200" in hint or "brief" in hint.lower() or "short" in hint.lower()


class TestChannelFormats:
    def test_all_four_channels_defined(self):
        from agent.prompts import CHANNEL_FORMATS

        for channel in ("cli", "electron", "api", "whatsapp"):
            assert channel in CHANNEL_FORMATS, f"'{channel}' missing from CHANNEL_FORMATS"

    def test_each_format_has_required_fields(self):
        from agent.prompts import CHANNEL_FORMATS

        required_fields = {"max_width", "use_emoji", "use_tables", "verbosity"}
        for channel, fmt in CHANNEL_FORMATS.items():
            missing = required_fields - set(fmt.keys())
            assert missing == set(), f"Channel '{channel}' missing format fields: {missing}"

    def test_api_has_no_width_limit(self):
        from agent.prompts import CHANNEL_FORMATS

        assert CHANNEL_FORMATS["api"]["max_width"] == 0

    def test_whatsapp_has_narrower_width_than_cli(self):
        from agent.prompts import CHANNEL_FORMATS

        wa_width = CHANNEL_FORMATS["whatsapp"]["max_width"]
        cli_width = CHANNEL_FORMATS["cli"]["max_width"]
        assert wa_width < cli_width

    def test_api_has_no_emoji(self):
        from agent.prompts import CHANNEL_FORMATS

        assert CHANNEL_FORMATS["api"]["use_emoji"] is False

    def test_whatsapp_has_no_tables(self):
        from agent.prompts import CHANNEL_FORMATS

        assert CHANNEL_FORMATS["whatsapp"]["use_tables"] is False


class TestAnalyzeRequestHasChannelField:
    def test_analyze_request_has_channel_field(self):
        """AnalyzeRequest pydantic model should have channel field."""
        from web.skills import AnalyzeRequest

        req = AnalyzeRequest(symbol="INFY")
        assert hasattr(req, "channel")
        assert req.channel == "api"  # default

    def test_analyze_request_accepts_custom_channel(self):
        from web.skills import AnalyzeRequest

        req = AnalyzeRequest(symbol="INFY", channel="whatsapp")
        assert req.channel == "whatsapp"
