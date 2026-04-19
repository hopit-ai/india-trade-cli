"""
Tests for strategy marketplace export/import (#161).
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch


class TestStrategyExport:
    def test_strategy_store_has_export(self):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore.__new__(StrategyStore)
        assert hasattr(store, "export_strategy")

    def test_export_creates_json_file(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path)
        # Write a fake strategy metadata
        meta = {
            "name": "test_rsi",
            "description": "Test RSI strategy",
            "created_at": "2026-04-11",
        }
        (tmp_path / "test_rsi.json").write_text(json.dumps(meta))
        (tmp_path / "test_rsi.py").write_text(
            "from engine.backtest import Strategy\nclass TestRsi(Strategy): pass\n"
        )

        out_path = tmp_path / "exported.json"
        store.export_strategy("test_rsi", str(out_path))
        assert out_path.exists()

    def test_exported_json_has_required_fields(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path)
        meta = {"name": "myStrategy", "description": "My strategy"}
        (tmp_path / "myStrategy.json").write_text(json.dumps(meta))
        (tmp_path / "myStrategy.py").write_text(
            "from engine.backtest import Strategy\nclass MyStrategy(Strategy): pass\n"
        )

        out_path = tmp_path / "pkg.json"
        store.export_strategy("myStrategy", str(out_path))

        pkg = json.loads(out_path.read_text())
        assert "version" in pkg
        assert "name" in pkg
        assert "code" in pkg
        assert "description" in pkg

    def test_export_includes_version(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path)
        meta = {"name": "s", "description": "desc"}
        (tmp_path / "s.json").write_text(json.dumps(meta))
        (tmp_path / "s.py").write_text("class S: pass\n")

        out_path = tmp_path / "pkg.json"
        store.export_strategy("s", str(out_path))

        pkg = json.loads(out_path.read_text())
        assert pkg["version"] == "1.0"


class TestStrategyImport:
    def test_strategy_store_has_import(self):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore.__new__(StrategyStore)
        assert hasattr(store, "import_strategy")

    def test_import_from_local_file(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path / "strategies")
        store.base_dir.mkdir(parents=True, exist_ok=True)

        # Create a valid package file
        pkg = {
            "version": "1.0",
            "name": "imported_strat",
            "description": "An imported strategy",
            "code": "from engine.backtest import Strategy\nclass ImportedStrat(Strategy): pass\n",
            "created_at": "2026-04-10",
        }
        pkg_path = tmp_path / "imported_strat.json"
        pkg_path.write_text(json.dumps(pkg))

        result = store.import_strategy(str(pkg_path))
        assert result["name"] == "imported_strat"

    def test_import_saves_code_file(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        strategies_dir = tmp_path / "strategies"
        strategies_dir.mkdir(parents=True, exist_ok=True)
        store = StrategyStore(base_dir=strategies_dir)

        pkg = {
            "version": "1.0",
            "name": "new_strat",
            "description": "New strategy",
            "code": "class NS: pass\n",
        }
        pkg_path = tmp_path / "new_strat.json"
        pkg_path.write_text(json.dumps(pkg))

        store.import_strategy(str(pkg_path))

        assert (strategies_dir / "new_strat.py").exists()
        assert (strategies_dir / "new_strat.json").exists()

    def test_import_missing_fields_raises(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path)
        pkg = {"version": "1.0"}  # missing name and code
        pkg_path = tmp_path / "bad.json"
        pkg_path.write_text(json.dumps(pkg))

        with pytest.raises((ValueError, KeyError)):
            store.import_strategy(str(pkg_path))

    def test_import_from_url(self, tmp_path):
        from engine.strategy_builder import StrategyStore

        store = StrategyStore(base_dir=tmp_path)

        pkg = {
            "version": "1.0",
            "name": "url_strat",
            "description": "From URL",
            "code": "class UrlStrat: pass\n",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = pkg
        mock_resp.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_resp):
            result = store.import_strategy("https://example.com/strategy.json")

        assert result["name"] == "url_strat"
