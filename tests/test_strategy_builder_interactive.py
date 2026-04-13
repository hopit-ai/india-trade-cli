"""
Tests for interactive strategy builder session (#44).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestStrategyBuilderSessionExists:
    def test_class_importable(self):
        from engine.strategy_builder import StrategyBuilderSession

        assert StrategyBuilderSession is not None

    def test_strategy_spec_importable(self):
        from engine.strategy_builder import StrategySpec

        assert StrategySpec is not None


class TestStrategyBuilderSession:
    def test_start_returns_questions(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        questions = session.start("Buy NIFTY when RSI drops below 30")
        assert isinstance(questions, list)
        assert len(questions) > 0

    def test_questions_are_strings(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        questions = session.start("Buy when MACD crosses above signal line")
        assert all(isinstance(q, str) for q in questions)

    def test_has_session_id(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        session.start("Buy RELIANCE on RSI oversold")
        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_answer_records_response(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        questions = session.start("Buy INFY on RSI < 30")
        q_key = "entry_conditions"
        session.answer(q_key, "RSI 14 below 30")
        assert session.answers.get(q_key) == "RSI 14 below 30"

    def test_finalize_returns_strategy_spec(self):
        from engine.strategy_builder import StrategyBuilderSession, StrategySpec

        session = StrategyBuilderSession()
        session.start("Buy NIFTY when RSI below 30, sell at +3% or -1.5%")
        spec = session.finalize()
        assert isinstance(spec, StrategySpec)

    def test_spec_has_required_fields(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        session.start("Buy on RSI oversold with 1% stop loss and 2% target")
        spec = session.finalize()
        assert spec.name
        assert spec.description
        assert spec.stop_loss_pct >= 0
        assert spec.target_pct >= 0

    def test_spec_parses_stop_loss_from_description(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        session.start("Entry on RSI oversold, stop 2% below entry, target 4%")
        spec = session.finalize()
        assert spec.stop_loss_pct > 0

    def test_spec_generated_code_is_string(self):
        from engine.strategy_builder import StrategyBuilderSession

        session = StrategyBuilderSession()
        session.start("Buy when MACD crosses bullish")
        spec = session.finalize()
        # generated_code may be empty for rule-based, that's ok
        assert isinstance(spec.generated_code, str)


class TestStrategySpecDataclass:
    def test_fields_exist(self):
        from engine.strategy_builder import StrategySpec

        spec = StrategySpec(
            name="test",
            description="test strategy",
            entry_conditions=["RSI < 30"],
            exit_conditions=["RSI > 70"],
            stop_loss_pct=1.5,
            target_pct=3.0,
            max_hold_days=15,
            position_size_pct=2.0,
            generated_code="",
        )
        assert spec.stop_loss_pct == 1.5
        assert spec.target_pct == 3.0
        assert spec.max_hold_days == 15
