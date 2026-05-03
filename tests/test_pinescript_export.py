"""
Tests for Pine Script export (#185).
"""

from __future__ import annotations



class TestStrategyToPinescript:
    def test_returns_string(self):
        from engine.export.pinescript import strategy_to_pinescript

        result = strategy_to_pinescript("test_strategy")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_version5_header(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript("my_strat")
        assert "//@version=5" in pine

    def test_contains_strategy_title(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript("macd_crossover")
        assert "macd_crossover" in pine

    def test_contains_strategy_function(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript("test")
        assert "strategy(" in pine

    def test_contains_entry_exit_logic(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript("test")
        assert "strategy.entry" in pine
        assert "strategy.close" in pine

    def test_macd_code_detects_macd_indicator(self):
        from engine.export.pinescript import strategy_to_pinescript

        python_code = """
class MACDStrategy(Strategy):
    def generate_signals(self, df):
        macd_val = df['close'].ewm(12).mean() - df['close'].ewm(26).mean()
        return pd.Series(...)
"""
        pine = strategy_to_pinescript("macd_strat", python_code=python_code)
        assert "ta.macd" in pine

    def test_rsi_code_detects_rsi_indicator(self):
        from engine.export.pinescript import strategy_to_pinescript

        python_code = """
class RSIStrategy(Strategy):
    def generate_signals(self, df):
        rsi_vals = rsi(df['close'], 14)
        signals[rsi_vals < 30] = 1
"""
        pine = strategy_to_pinescript("rsi_strat", python_code=python_code)
        assert "ta.rsi" in pine

    def test_bollinger_code_detects_bollinger(self):
        from engine.export.pinescript import strategy_to_pinescript

        python_code = """
class BollingerStrategy(Strategy):
    def generate_signals(self, df):
        upper, lower = bollinger_bands(df['close'], 20, 2.0)
"""
        pine = strategy_to_pinescript("bb_strat", python_code=python_code)
        assert "ta.bb" in pine

    def test_ema_code_detects_ema(self):
        from engine.export.pinescript import strategy_to_pinescript

        python_code = """
class EMAStrategy(Strategy):
    def generate_signals(self, df):
        fast_ema = df['close'].ewm(span=9).mean()
        slow_ema = df['close'].ewm(span=21).mean()
"""
        pine = strategy_to_pinescript("ema_strat", python_code=python_code)
        assert "ta.ema" in pine

    def test_unknown_code_falls_back_to_sma(self):
        from engine.export.pinescript import strategy_to_pinescript

        python_code = "# some custom logic without known indicators"
        pine = strategy_to_pinescript("custom_strat", python_code=python_code)
        assert "ta.sma" in pine

    def test_description_in_comment(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript(
            "test",
            metadata={"description": "My awesome momentum strategy"},
        )
        assert "My awesome momentum strategy" in pine

    def test_contains_visual_markers(self):
        from engine.export.pinescript import strategy_to_pinescript

        pine = strategy_to_pinescript("test")
        assert "plotshape" in pine


class TestExportBacktestResultToPinescript:
    def _make_result(self, **kwargs):
        """Create a minimal BacktestResult-like stub."""

        class FakeResult:
            strategy_name = "test_strategy"
            symbol = "INFY"
            period = "1y"
            total_return = 15.5
            sharpe_ratio = 1.2
            win_rate = 60.0
            max_drawdown = -8.3
            trades = []

        r = FakeResult()
        for k, v in kwargs.items():
            setattr(r, k, v)
        return r

    def test_returns_string(self):
        from engine.export.pinescript import export_backtest_result_to_pinescript

        result = self._make_result()
        pine = export_backtest_result_to_pinescript(result)
        assert isinstance(pine, str)
        assert len(pine) > 0

    def test_contains_version5_header(self):
        from engine.export.pinescript import export_backtest_result_to_pinescript

        pine = export_backtest_result_to_pinescript(self._make_result())
        assert "//@version=5" in pine

    def test_contains_backtest_metrics(self):
        from engine.export.pinescript import export_backtest_result_to_pinescript

        result = self._make_result(total_return=22.5, win_rate=65.0, sharpe_ratio=1.5)
        pine = export_backtest_result_to_pinescript(result)
        assert "22.5" in pine or "+22.50" in pine
        assert "65.0" in pine

    def test_contains_symbol(self):
        from engine.export.pinescript import export_backtest_result_to_pinescript

        result = self._make_result(symbol="RELIANCE")
        pine = export_backtest_result_to_pinescript(result)
        assert "RELIANCE" in pine

    def test_contains_trade_count(self):
        from engine.export.pinescript import export_backtest_result_to_pinescript

        class FakeTrade:
            pass

        result = self._make_result(trades=[FakeTrade(), FakeTrade(), FakeTrade()])
        pine = export_backtest_result_to_pinescript(result)
        assert "3" in pine


class TestSavePinescript:
    def test_writes_file(self, tmp_path):
        from engine.export.pinescript import save_pinescript

        path = tmp_path / "test.pine"
        save_pinescript("test pine content", path)
        assert path.exists()
        assert path.read_text() == "test pine content"

    def test_creates_parent_directory(self, tmp_path):
        from engine.export.pinescript import save_pinescript

        path = tmp_path / "subdir" / "nested" / "test.pine"
        save_pinescript("//@version=5\nstrategy('test', overlay=true)", path)
        assert path.exists()
