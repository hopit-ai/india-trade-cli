"""
Tests for Dhan broker scaffold (#155).
Verifies interface compliance and field mappings without live API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestDhanBrokerExists:
    def test_module_importable(self):
        from brokers.dhan import DhanBroker

        assert DhanBroker is not None

    def test_implements_broker_api(self):
        from brokers.dhan import DhanBroker
        from brokers.base import BrokerAPI

        assert issubclass(DhanBroker, BrokerAPI)

    def test_has_required_methods(self):
        from brokers.dhan import DhanBroker

        required = [
            "get_login_url",
            "complete_login",
            "is_authenticated",
            "logout",
            "get_profile",
            "get_funds",
            "get_holdings",
            "get_positions",
            "get_quote",
            "get_options_chain",
            "place_order",
            "get_orders",
            "cancel_order",
        ]
        for method in required:
            assert hasattr(DhanBroker, method), f"DhanBroker missing method: {method}"


class TestDhanExchangeMapping:
    def test_exchange_mapping_nse(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_exchange("NSE") == "NSE_EQ"

    def test_exchange_mapping_bse(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_exchange("BSE") == "BSE_EQ"

    def test_exchange_mapping_nfo(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_exchange("NFO") == "NSE_FNO"


class TestDhanProductMapping:
    def test_product_cnc(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_product("CNC") == "CNC"

    def test_product_mis_to_intraday(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_product("MIS") == "INTRADAY"

    def test_product_nrml_to_margin(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        assert broker._map_product("NRML") == "MARGIN"


class TestDhanAuthConfig:
    def test_not_authenticated_when_no_token(self, monkeypatch):
        monkeypatch.delenv("DHAN_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)

        from brokers.dhan import DhanBroker

        broker = DhanBroker()
        assert not broker.is_authenticated()

    def test_authenticated_when_token_set(self, monkeypatch):
        monkeypatch.setenv("DHAN_ACCESS_TOKEN", "test-token-123")
        monkeypatch.setenv("DHAN_CLIENT_ID", "client-456")

        from brokers.dhan import DhanBroker

        broker = DhanBroker()
        assert broker.is_authenticated()

    def test_get_login_url_returns_string(self):
        from brokers.dhan import DhanBroker

        broker = DhanBroker.__new__(DhanBroker)
        url = broker.get_login_url()
        assert isinstance(url, str)
        assert url.startswith("http")


class TestDhanOrderPlacement:
    def test_place_order_builds_correct_payload(self, monkeypatch):
        monkeypatch.setenv("DHAN_ACCESS_TOKEN", "token-abc")
        monkeypatch.setenv("DHAN_CLIENT_ID", "client-123")

        from brokers.dhan import DhanBroker
        from brokers.base import OrderRequest, OrderResponse

        broker = DhanBroker()

        # Mock the requests.post call
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "orderId": "ORD123",
            "orderStatus": "PENDING",
        }

        req = OrderRequest(
            symbol="RELIANCE",
            exchange="NSE",
            transaction_type="BUY",
            quantity=10,
            order_type="MARKET",
            product="CNC",
        )
        # Mock the session's post method directly
        broker._session.post = MagicMock(return_value=mock_resp)

        result = broker.place_order(req)

        assert result is not None
        assert isinstance(result, OrderResponse)
        broker._session.post.assert_called_once()
        # Verify the payload used Dhan's field names
        call_kwargs = broker._session.post.call_args
        payload = call_kwargs.kwargs.get(
            "json", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
        )
        assert payload.get("exchangeSegment") == "NSE_EQ"
        assert payload.get("productType") == "CNC"
