"""
Tests for data source fallback chains (#184).

Verifies that each data type gracefully degrades to the next tier when the
primary source fails, and that source tracking + warnings work correctly.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

from brokers.base import OptionsContract


# ── Helpers ──────────────────────────────────────────────────────


def _make_contract(strike: float, opt_type: str = "CE") -> OptionsContract:
    return OptionsContract(
        symbol=f"NIFTY{int(strike)}{opt_type}",
        underlying="NIFTY",
        strike=strike,
        option_type=opt_type,
        expiry="2026-05-29",
        last_price=100.0,
        oi=50000,
        oi_change=0,
        volume=10000,
        iv=15.0,
    )


# ── Source tracker ────────────────────────────────────────────────


class TestSourceTracker:
    def test_record_and_get(self):
        from market.source_tracker import record_source, get_last_source

        record_source("options", "broker")
        assert get_last_source("options") == "broker"

    def test_get_unknown_returns_none(self):
        from market.source_tracker import get_last_source

        assert get_last_source("nonexistent_type_xyz") == "none"

    def test_record_overwrite(self):
        from market.source_tracker import record_source, get_last_source

        record_source("quotes", "broker")
        record_source("quotes", "yfinance")
        assert get_last_source("quotes") == "yfinance"

    def test_warn_fallback_does_not_raise(self, capsys):
        from market.source_tracker import warn_fallback

        # Should never crash regardless of message content
        warn_fallback("options", "token expired", "nse_scraper")


# ── NSE scraper ───────────────────────────────────────────────────


class TestNseScraper:
    def test_nse_available_returns_bool(self):
        from market.nse_scraper import nse_available

        result = nse_available()
        assert isinstance(result, bool)

    def test_nse_get_options_chain_returns_list(self, monkeypatch):
        """When NSE API returns valid data, parse into OptionsContract list."""
        from market.nse_scraper import nse_get_options_chain

        sample_nse_response = {
            "records": {
                "expiryDates": ["29-May-2026"],
                "data": [
                    {
                        "strikePrice": 22000,
                        "expiryDate": "29-May-2026",
                        "CE": {
                            "lastPrice": 120.5,
                            "openInterest": 50000,
                            "totalTradedVolume": 12000,
                            "impliedVolatility": 14.5,
                            "delta": 0.55,
                            "gamma": 0.01,
                            "theta": -4.5,
                            "vega": 9.8,
                        },
                        "PE": {
                            "lastPrice": 80.0,
                            "openInterest": 40000,
                            "totalTradedVolume": 8000,
                            "impliedVolatility": 14.0,
                            "delta": -0.45,
                            "gamma": 0.01,
                            "theta": -4.0,
                            "vega": 9.2,
                        },
                    }
                ],
            }
        }

        import market.nse_scraper as nse_mod

        monkeypatch.setattr(nse_mod, "_fetch_nse_chain", lambda u, i: sample_nse_response)

        result = nse_get_options_chain("NIFTY")
        assert isinstance(result, list)
        assert len(result) == 2  # one CE + one PE
        types = {c.option_type for c in result}
        assert "CE" in types
        assert "PE" in types

    def test_nse_get_options_chain_filters_by_expiry(self, monkeypatch):
        """When expiry is specified, only return contracts for that expiry."""
        from market.nse_scraper import nse_get_options_chain

        sample = {
            "records": {
                "expiryDates": ["29-May-2026", "26-Jun-2026"],
                "data": [
                    {
                        "strikePrice": 22000,
                        "expiryDate": "29-May-2026",
                        "CE": {"lastPrice": 100.0, "openInterest": 1000,
                               "totalTradedVolume": 500, "impliedVolatility": 14.0,
                               "delta": 0.5, "gamma": 0.01, "theta": -4.0, "vega": 9.0},
                    },
                    {
                        "strikePrice": 22000,
                        "expiryDate": "26-Jun-2026",
                        "CE": {"lastPrice": 150.0, "openInterest": 2000,
                               "totalTradedVolume": 800, "impliedVolatility": 15.0,
                               "delta": 0.55, "gamma": 0.01, "theta": -3.5, "vega": 10.0},
                    },
                ],
            }
        }

        import market.nse_scraper as nse_mod

        monkeypatch.setattr(nse_mod, "_fetch_nse_chain", lambda u, i: sample)

        result = nse_get_options_chain("NIFTY", expiry="2026-05-29")
        assert all(c.expiry == "2026-05-29" for c in result)

    def test_nse_get_options_chain_returns_empty_on_network_error(self, monkeypatch):
        """Network error → returns empty list, does not raise."""
        from market.nse_scraper import nse_get_options_chain

        import market.nse_scraper as nse_mod

        def raise_error(u, i):
            raise ConnectionError("Network unreachable")

        monkeypatch.setattr(nse_mod, "_fetch_nse_chain", raise_error)

        result = nse_get_options_chain("NIFTY")
        assert result == []

    def test_index_vs_equity_routing(self, monkeypatch):
        """NIFTY/BANKNIFTY route to index endpoint; RELIANCE to equity endpoint."""
        from market.nse_scraper import _is_index_underlying

        assert _is_index_underlying("NIFTY") is True
        assert _is_index_underlying("BANKNIFTY") is True
        assert _is_index_underlying("FINNIFTY") is True
        assert _is_index_underlying("RELIANCE") is False
        assert _is_index_underlying("INFY") is False


# ── Options chain fallback ────────────────────────────────────────


class TestOptionsChainFallback:
    def test_uses_broker_when_available(self, monkeypatch):
        """Happy path: broker works → returns broker data, source=broker."""
        from market import options as options_mod
        from market.source_tracker import get_last_source

        contracts = [_make_contract(22000, "CE")]
        mock_broker = MagicMock()
        mock_broker.get_options_chain.return_value = contracts
        monkeypatch.setattr("market.options.get_data_broker", lambda: mock_broker)

        result = options_mod.get_options_chain("NIFTY")
        assert result == contracts
        assert get_last_source("options") == "broker"

    def test_falls_back_to_nse_when_broker_raises(self, monkeypatch):
        """Broker raises → NSE scraper used, source=nse_scraper."""
        from market import options as options_mod
        from market.source_tracker import get_last_source

        mock_broker = MagicMock()
        mock_broker.get_options_chain.side_effect = RuntimeError("token expired")
        monkeypatch.setattr("market.options.get_data_broker", lambda: mock_broker)

        nse_contracts = [_make_contract(22000, "CE"), _make_contract(22000, "PE")]
        monkeypatch.setattr("market.options.nse_get_options_chain", lambda u, e=None: nse_contracts)

        result = options_mod.get_options_chain("NIFTY")
        assert result == nse_contracts
        assert get_last_source("options") == "nse_scraper"

    def test_returns_empty_when_both_fail(self, monkeypatch):
        """Both broker and NSE fail → returns [], does not raise."""
        from market import options as options_mod

        mock_broker = MagicMock()
        mock_broker.get_options_chain.side_effect = RuntimeError("broker down")
        monkeypatch.setattr("market.options.get_data_broker", lambda: mock_broker)
        monkeypatch.setattr("market.options.nse_get_options_chain", lambda u, e=None: [])

        result = options_mod.get_options_chain("NIFTY")
        assert result == []

    def test_no_broker_falls_back_to_nse(self, monkeypatch):
        """RuntimeError from get_data_broker (no broker) → NSE scraper."""
        from market import options as options_mod
        from market.source_tracker import get_last_source

        def _raise():
            raise RuntimeError("no broker")

        monkeypatch.setattr("market.options.get_data_broker", _raise)

        nse_contracts = [_make_contract(22000, "CE")]
        monkeypatch.setattr("market.options.nse_get_options_chain", lambda u, e=None: nse_contracts)

        result = options_mod.get_options_chain("NIFTY")
        assert result == nse_contracts
        assert get_last_source("options") == "nse_scraper"


# ── Holdings / positions disk cache ──────────────────────────────


class TestHoldingsCache:
    def test_save_and_load_cache(self, tmp_path):
        """Saved holdings can be loaded back correctly."""
        from market.disk_cache import save_cache, load_cache

        data = [{"symbol": "INFY", "quantity": 10, "avg_price": 1400.0}]
        save_cache("holdings", data, cache_dir=tmp_path)

        loaded, cached_at = load_cache("holdings", cache_dir=tmp_path)
        assert loaded == data
        assert isinstance(cached_at, datetime)

    def test_load_cache_returns_none_when_missing(self, tmp_path):
        """No cache file → returns ([], None)."""
        from market.disk_cache import load_cache

        data, cached_at = load_cache("holdings", cache_dir=tmp_path)
        assert data == []
        assert cached_at is None

    def test_cache_is_valid_json(self, tmp_path):
        """Cache file is valid JSON parseable independently."""
        from market.disk_cache import save_cache

        data = [{"symbol": "RELIANCE", "quantity": 5}]
        save_cache("positions", data, cache_dir=tmp_path)

        cache_file = tmp_path / "positions.json"
        assert cache_file.exists()
        parsed = json.loads(cache_file.read_text())
        assert isinstance(parsed, dict)
        assert "data" in parsed
        assert "saved_at" in parsed

    def test_load_cache_handles_corrupt_file(self, tmp_path):
        """Corrupt cache file → returns ([], None), does not raise."""
        from market.disk_cache import load_cache

        bad_file = tmp_path / "holdings.json"
        bad_file.write_text("not valid json{{{{")

        data, cached_at = load_cache("holdings", cache_dir=tmp_path)
        assert data == []
        assert cached_at is None


# ── OHLCV disk cache ─────────────────────────────────────────────


class TestOhlcvCache:
    def test_history_falls_back_to_yfinance(self, monkeypatch):
        """When broker raises, yfinance is tried."""
        from market import history as hist_mod

        def _raise_broker():
            raise RuntimeError("no broker")

        monkeypatch.setattr("brokers.session.get_broker", _raise_broker)
        monkeypatch.setattr("market.history._yfinance_fallback", lambda *a, **kw: [
            {"date": datetime(2026, 1, 1), "open": 100.0, "high": 110.0,
             "low": 95.0, "close": 105.0, "volume": 1000}
        ])
        monkeypatch.setattr("market.history.save_ohlcv_cache", lambda *a, **kw: None)

        result = hist_mod.get_ohlcv("INFY", interval="day", days=30)
        assert not result.empty
        assert "close" in result.columns

    def test_history_saves_to_disk_cache(self, monkeypatch):
        """Successful yfinance fetch saves data to disk cache."""
        from market import history as hist_mod

        def _raise_broker():
            raise RuntimeError("no broker")

        monkeypatch.setattr("brokers.session.get_broker", _raise_broker)
        monkeypatch.setattr("market.history._yfinance_fallback", lambda *a, **kw: [
            {"date": datetime(2026, 1, 1), "open": 100.0, "high": 110.0,
             "low": 95.0, "close": 105.0, "volume": 1000}
        ])

        saved = {}

        def fake_save(key, data):
            saved[key] = data

        monkeypatch.setattr("market.history.save_ohlcv_cache", fake_save)

        hist_mod.get_ohlcv("INFY", interval="day", days=30)
        assert any("INFY" in k for k in saved)

    def test_history_loads_disk_cache_when_all_fail(self, monkeypatch):
        """When broker AND yfinance both fail, disk cache is used."""
        from market import history as hist_mod

        def _raise_broker():
            raise RuntimeError("no broker")

        monkeypatch.setattr("brokers.session.get_broker", _raise_broker)
        monkeypatch.setattr("market.history._yfinance_fallback", lambda *a, **kw: [])

        cached_rows = [
            {"date": "2026-01-01T00:00:00", "open": 100.0, "high": 110.0,
             "low": 95.0, "close": 105.0, "volume": 1000}
        ]

        monkeypatch.setattr(
            "market.history.load_ohlcv_cache",
            lambda key: (cached_rows, datetime(2026, 1, 1)),
        )

        result = hist_mod.get_ohlcv("INFY", interval="day", days=30)
        assert not result.empty
