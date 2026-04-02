"""Tests for agent/tools.py — registry, schema, serialization."""

import pytest
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import date, datetime


class TestToolRegistry:
    def test_build_registry_has_tools(self):
        """build_registry should register 30+ tools."""
        from agent.tools import build_registry
        reg = build_registry()
        assert len(reg.names) >= 30, f"Only {len(reg.names)} tools registered"

    def test_known_tools_present(self):
        from agent.tools import build_registry
        reg = build_registry()
        expected = [
            "get_quote", "technical_analyse", "fundamental_analyse",
            "get_vix", "get_market_snapshot", "get_iv_rank",
        ]
        for name in expected:
            assert name in reg.names, f"Tool '{name}' missing from registry"

    def test_anthropic_schema_structure(self):
        """Anthropic schema should produce list of dicts with name/description/input_schema."""
        from agent.tools import build_registry
        reg = build_registry()
        schema = reg.anthropic_schema()
        assert isinstance(schema, list)
        assert len(schema) > 0
        for tool in schema:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_openai_schema_structure(self):
        """OpenAI schema should produce list of dicts with type=function."""
        from agent.tools import build_registry
        reg = build_registry()
        schema = reg.openai_schema()
        assert isinstance(schema, list)
        for tool in schema:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]


class TestSerialization:
    def test_dataclass_serialized(self):
        from agent.tools import _serialise

        @dataclass
        class Foo:
            x: int = 1
            y: str = "hello"

        result = _serialise(Foo())
        assert isinstance(result, dict)
        assert result["x"] == 1
        assert result["y"] == "hello"

    def test_dataframe_serialized(self):
        from agent.tools import _serialise
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = _serialise(df)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_nan_becomes_none(self):
        from agent.tools import _serialise
        assert _serialise(float("nan")) is None

    def test_date_becomes_string(self):
        from agent.tools import _serialise
        d = date(2025, 4, 1)
        result = _serialise(d)
        assert isinstance(result, str)
        assert "2025" in result

    def test_nested_structures(self):
        from agent.tools import _serialise
        data = {"items": [{"val": float("nan")}, {"val": 42}]}
        result = _serialise(data)
        assert result["items"][0]["val"] is None
        assert result["items"][1]["val"] == 42
