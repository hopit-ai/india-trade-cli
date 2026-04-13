"""
Tests for multi-strategy HTML backtest report generation (#156).
"""

from __future__ import annotations

import pytest


def _make_result(symbol="INFY", strategy="RSI", total_return=15.0, sharpe=1.2):
    """Build a minimal BacktestResult for testing."""
    from engine.backtest import BacktestResult

    return BacktestResult(
        symbol=symbol,
        strategy_name=strategy,
        period="1y",
        start_date="2025-01-01",
        end_date="2026-01-01",
        total_return=total_return,
        cagr=total_return * 0.9,
        sharpe_ratio=sharpe,
        max_drawdown=-8.5,
        total_trades=20,
        winning_trades=13,
        losing_trades=7,
        win_rate=65.0,
        avg_win=2.1,
        avg_loss=-1.2,
        profit_factor=1.8,
        avg_hold_days=5.2,
        buy_hold_return=12.0,
        equity_curve=[100.0, 102.0, 105.0, 103.0, 115.0],
    )


class TestGenerateHtmlReport:
    def test_module_exists(self):
        from engine.backtest_report import generate_html_report

        assert callable(generate_html_report)

    def test_returns_path_string(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result()
        path = generate_html_report([result], output_path=str(tmp_path / "test_report.html"))
        assert isinstance(path, str)
        assert path.endswith(".html")

    def test_file_is_created(self, tmp_path):
        from engine.backtest_report import generate_html_report
        import os

        result = _make_result()
        path = generate_html_report([result], output_path=str(tmp_path / "report.html"))
        assert os.path.exists(path)

    def test_html_contains_strategy_name(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result(strategy="BollingerBands")
        path = generate_html_report([result], output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        assert "BollingerBands" in content

    def test_html_contains_symbol(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result(symbol="RELIANCE")
        path = generate_html_report([result], output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        assert "RELIANCE" in content

    def test_html_has_basic_structure(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result()
        path = generate_html_report([result], output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        assert "<html" in content
        assert "</html>" in content

    def test_multiple_strategies_all_appear(self, tmp_path):
        from engine.backtest_report import generate_html_report

        results = [
            _make_result(strategy="RSI", total_return=15.0),
            _make_result(strategy="MACD", total_return=10.0),
            _make_result(strategy="Bollinger", total_return=18.0),
        ]
        path = generate_html_report(results, output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        assert "RSI" in content
        assert "MACD" in content
        assert "Bollinger" in content

    def test_equity_curve_data_embedded(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result(strategy="RSI")
        result.equity_curve = [100, 110, 108, 120, 125]
        path = generate_html_report([result], output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        # The equity curve data should appear somewhere in the HTML
        assert "100" in content and "125" in content

    def test_empty_results_raises(self):
        from engine.backtest_report import generate_html_report

        with pytest.raises((ValueError, IndexError)):
            generate_html_report([])

    def test_return_percentages_in_report(self, tmp_path):
        from engine.backtest_report import generate_html_report

        result = _make_result(total_return=22.5)
        path = generate_html_report([result], output_path=str(tmp_path / "r.html"))
        content = open(path).read()
        assert "22" in content  # Return % appears

    def test_default_output_path_is_desktop(self, tmp_path, monkeypatch):
        """When no output_path given, saves to Desktop."""
        from engine.backtest_report import generate_html_report
        import engine.backtest_report as br_mod

        # Patch the PDF_OUTPUT_DIR equivalent
        monkeypatch.setattr(br_mod, "REPORT_OUTPUT_DIR", tmp_path)

        result = _make_result()
        path = generate_html_report([result])
        assert path.startswith(str(tmp_path))
        import os

        assert os.path.exists(path)
