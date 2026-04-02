"""Tests for engine/output.py — flag parsing, markup stripping, filenames."""

import pytest

from engine.output import parse_output_flags, _strip_rich_markup


class TestParseOutputFlags:
    def test_pdf_flag(self):
        args, pdf, explain, explain_save = parse_output_flags(["RELIANCE", "--pdf"])
        assert args == ["RELIANCE"]
        assert pdf is True
        assert explain is False
        assert explain_save is False

    def test_explain_flag(self):
        args, pdf, explain, explain_save = parse_output_flags(["RELIANCE", "--explain"])
        assert args == ["RELIANCE"]
        assert pdf is False
        assert explain is True

    def test_explain_save_enables_both(self):
        args, pdf, explain, explain_save = parse_output_flags(["SYM", "--explain-save"])
        assert args == ["SYM"]
        assert pdf is True
        assert explain is True
        assert explain_save is True

    def test_no_flags(self):
        args, pdf, explain, explain_save = parse_output_flags(["RELIANCE"])
        assert args == ["RELIANCE"]
        assert pdf is False
        assert explain is False

    def test_multiple_flags(self):
        args, pdf, explain, _ = parse_output_flags(["SYM", "--pdf", "--explain"])
        assert args == ["SYM"]
        assert pdf is True
        assert explain is True

    def test_empty_args(self):
        args, pdf, explain, _ = parse_output_flags([])
        assert args == []
        assert pdf is False


class TestStripRichMarkup:
    def test_bold(self):
        assert _strip_rich_markup("[bold]hello[/bold]") == "hello"

    def test_color(self):
        assert _strip_rich_markup("[red]error[/red]") == "error"

    def test_nested(self):
        result = _strip_rich_markup("[bold cyan]title[/bold cyan] text")
        assert "title" in result
        assert "text" in result
        assert "[" not in result

    def test_plain_text_unchanged(self):
        assert _strip_rich_markup("plain text") == "plain text"
