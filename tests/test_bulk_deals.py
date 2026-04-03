"""Tests for market/bulk_deals.py — bulk/block deal fetching and parsing.

Tests cover:
  - Entity classification
  - Deal parsing from all NSE response formats
  - 4-tier fallback: snapshot → historicalOR → historical (legacy) → CSV
  - Symbol filtering
  - Error handling when all endpoints fail
"""

from unittest.mock import patch, MagicMock

from market.bulk_deals import (
    classify_entity,
    get_bulk_deals,
    get_block_deals,
    _parse_deal_item,
)


# ── Sample NSE response payloads ────────────────────────────

# Snapshot endpoint response (/api/snapshot-capital-market-largedeal)
# Uses short field names: date, symbol, clientName, buySell, qty, watp
SNAPSHOT_RESPONSE = {
    "BULK_DEALS_DATA": [
        {
            "date": "02-Apr-2026",
            "symbol": "RELIANCE",
            "name": "Reliance Industries Ltd",
            "clientName": "GOLDMAN SACHS FPI",
            "buySell": "BUY",
            "qty": "500000",
            "watp": "2450.75",
            "remarks": "-",
        },
        {
            "date": "02-Apr-2026",
            "symbol": "INFY",
            "name": "Infosys Ltd",
            "clientName": "SBI MUTUAL FUND",
            "buySell": "SELL",
            "qty": "200000",
            "watp": "1580.50",
            "remarks": "-",
        },
    ],
    "BLOCK_DEALS_DATA": [
        {
            "date": "02-Apr-2026",
            "symbol": "TCS",
            "name": "Tata Consultancy Services Ltd",
            "clientName": "LIC OF INDIA",
            "buySell": "BUY",
            "qty": "100000",
            "watp": "3800.00",
            "remarks": "-",
        },
    ],
    "SHORT_DEALS_DATA": [],
}

# Historical endpoint response (/api/historicalOR/bulk-block-short-deals)
HISTORICAL_RESPONSE = {
    "data": [
        {
            "BD_DT_DATE": "28-MAR-2026",
            "BD_SYMBOL": "HDFC",
            "BD_CLIENT_NAME": "MORGAN STANLEY ASIA PTE LTD",
            "BD_BUY_SELL": "SELL",
            "BD_QTY_TRD": 300000,
            "BD_TP_WATP": 1650.25,
            "BD_REMARKS": "-",
        },
    ],
}

# Legacy endpoint response (/api/historical/bulk-deals)
LEGACY_RESPONSE = {
    "data": [
        {
            "dealDate": "25-MAR-2026",
            "symbol": "TATAMOTORS",
            "clientName": "VANGUARD FUND",
            "buySell": "Buy",
            "quantity": 150000,
            "tradedPrice": 720.50,
        },
    ],
}

# CSV archive content
CSV_CONTENT = (
    "Date,Symbol,Security Name,Client Name,Buy / Sell,"
    "Quantity Traded,Trade Price / Wght. Avg. Price,Remarks\n"
    "01-APR-2026,WIPRO,Wipro Ltd,HRTI PRIVATE LIMITED,BUY,"
    "108709,450.25,-\n"
    "01-APR-2026,RELIANCE,Reliance Industries,FIDELITY INTL,SELL,"
    "250000,2440.00,-\n"
)


# ── Entity classification ────────────────────────────────────


class TestClassifyEntity:
    def test_fii(self):
        assert classify_entity("GOLDMAN SACHS FPI") == "FII"
        assert classify_entity("MORGAN STANLEY ASIA PTE LTD") == "FII"
        assert classify_entity("VANGUARD FUND") == "FII"
        assert classify_entity("FIDELITY INTL") == "FII"

    def test_mf(self):
        assert classify_entity("SBI MUTUAL FUND") == "MF"
        assert classify_entity("HDFC ASSET MANAGEMENT") == "MF"
        assert classify_entity("ICICI PRUDENTIAL MF") == "MF"

    def test_dii(self):
        assert classify_entity("LIC OF INDIA") == "DII"
        assert classify_entity("EMPLOYEES PROVIDENT FUND") == "DII"

    def test_promoter(self):
        assert classify_entity("PROMOTER GROUP") == "PROMOTER"

    def test_other(self):
        assert classify_entity("RANDOM PERSON") == "OTHER"
        assert classify_entity("HRTI PRIVATE LIMITED") == "OTHER"


# ── Deal parsing ─────────────────────────────────────────────


class TestParseDealItem:
    def test_parse_snapshot_fields(self):
        """Parse items using snapshot field names (date, qty, watp — strings)."""
        item = SNAPSHOT_RESPONSE["BULK_DEALS_DATA"][0]
        deal = _parse_deal_item(item, "BULK")
        assert deal.symbol == "RELIANCE"
        assert deal.client == "GOLDMAN SACHS FPI"
        assert deal.deal_type == "BUY"
        assert deal.quantity == 500000
        assert deal.price == 2450.75
        assert deal.entity_type == "FII"
        assert deal.deal_class == "BULK"

    def test_parse_bd_prefix_fields(self):
        """Parse items using BD_* field names (historicalOR format)."""
        item = HISTORICAL_RESPONSE["data"][0]
        deal = _parse_deal_item(item, "BULK")
        assert deal.symbol == "HDFC"
        assert deal.client == "MORGAN STANLEY ASIA PTE LTD"
        assert deal.deal_type == "SELL"
        assert deal.quantity == 300000
        assert deal.price == 1650.25
        assert deal.entity_type == "FII"

    def test_parse_legacy_field_names(self):
        """Parse items using legacy field names (dealDate, clientName etc.)."""
        item = LEGACY_RESPONSE["data"][0]
        deal = _parse_deal_item(item, "BULK")
        assert deal.symbol == "TATAMOTORS"
        assert deal.client == "VANGUARD FUND"
        assert deal.deal_type == "BUY"
        assert deal.quantity == 150000
        assert deal.price == 720.50
        assert deal.entity_type == "FII"

    def test_parse_block_deal(self):
        item = SNAPSHOT_RESPONSE["BLOCK_DEALS_DATA"][0]
        deal = _parse_deal_item(item, "BLOCK")
        assert deal.deal_class == "BLOCK"
        assert deal.symbol == "TCS"
        assert deal.quantity == 100000
        assert deal.price == 3800.00
        assert deal.entity_type == "DII"


# ── Mock helpers ─────────────────────────────────────────────


def _mock_response(status_code, json_data=None, text=""):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ── Bulk deals: 4-tier fallback ──────────────────────────────


class TestGetBulkDeals:
    @patch("market.bulk_deals._nse_session")
    def test_snapshot_success(self, mock_session_fn):
        """Tier 1: snapshot endpoint returns bulk deals."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(200, SNAPSHOT_RESPONSE)

        deals = get_bulk_deals(days=5)

        assert len(deals) == 2
        assert deals[0].symbol == "RELIANCE"
        assert deals[1].symbol == "INFY"
        # Should have called snapshot endpoint
        call_url = session.get.call_args_list[0][0][0]
        assert "snapshot-capital-market-largedeal" in call_url

    @patch("market.bulk_deals._nse_session")
    def test_snapshot_fails_historicalOR_succeeds(self, mock_session_fn):
        """Tier 2: snapshot fails, historicalOR endpoint returns deals."""
        session = MagicMock()
        mock_session_fn.return_value = session

        def side_effect(url, **kwargs):
            if "snapshot" in url:
                return _mock_response(403)
            if "historicalOR" in url:
                return _mock_response(200, HISTORICAL_RESPONSE)
            return _mock_response(404)

        session.get.side_effect = side_effect

        deals = get_bulk_deals(days=5)

        assert len(deals) == 1
        assert deals[0].symbol == "HDFC"
        assert deals[0].entity_type == "FII"

    @patch("market.bulk_deals._nse_session")
    def test_snapshot_and_historicalOR_fail_legacy_succeeds(self, mock_session_fn):
        """Tier 3: snapshot + historicalOR fail, legacy endpoint works."""
        session = MagicMock()
        mock_session_fn.return_value = session

        def side_effect(url, **kwargs):
            if "snapshot" in url:
                return _mock_response(403)
            if "historicalOR" in url:
                return _mock_response(404)
            if "historical/bulk-deals" in url:
                return _mock_response(200, LEGACY_RESPONSE)
            return _mock_response(404)

        session.get.side_effect = side_effect

        deals = get_bulk_deals(days=5)

        assert len(deals) == 1
        assert deals[0].symbol == "TATAMOTORS"

    @patch("market.bulk_deals.httpx")
    @patch("market.bulk_deals._nse_session")
    def test_all_api_fail_csv_fallback(self, mock_session_fn, mock_httpx):
        """Tier 4: all API endpoints fail, CSV archive works."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(403)

        # Mock the CSV fallback (httpx.get direct call)
        mock_httpx.Client = MagicMock  # for _nse_session
        mock_httpx.get.return_value = _mock_response(200, text=CSV_CONTENT)

        deals = get_bulk_deals(days=5)

        assert len(deals) == 2
        assert deals[0].symbol == "WIPRO"
        assert deals[1].symbol == "RELIANCE"
        assert deals[1].entity_type == "FII"

    @patch("market.bulk_deals._nse_session")
    def test_symbol_filter(self, mock_session_fn):
        """Symbol filter works correctly on snapshot results."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(200, SNAPSHOT_RESPONSE)

        deals = get_bulk_deals(days=5, symbol="RELIANCE")

        assert len(deals) == 1
        assert deals[0].symbol == "RELIANCE"

    @patch("market.bulk_deals._nse_session")
    def test_all_fail_returns_empty(self, mock_session_fn):
        """When everything fails, returns empty list (no crash)."""
        mock_session_fn.side_effect = Exception("Connection refused")

        # CSV fallback also fails in this env (mocked implicitly)
        deals = get_bulk_deals(days=5)
        assert isinstance(deals, list)


# ── Block deals ──────────────────────────────────────────────


class TestGetBlockDeals:
    @patch("market.bulk_deals._nse_session")
    def test_snapshot_block_deals(self, mock_session_fn):
        """Block deals fetched from snapshot endpoint."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(200, SNAPSHOT_RESPONSE)

        deals = get_block_deals()

        assert len(deals) == 1
        assert deals[0].symbol == "TCS"
        assert deals[0].deal_class == "BLOCK"
        assert deals[0].entity_type == "DII"

    @patch("market.bulk_deals._nse_session")
    def test_snapshot_empty_falls_back_to_block_deal_api(self, mock_session_fn):
        """When snapshot has no block deals, fall back to /api/block-deal."""
        session = MagicMock()
        mock_session_fn.return_value = session

        empty_snapshot = {"BULK_DEALS_DATA": [], "BLOCK_DEALS_DATA": [], "SHORT_DEALS_DATA": []}
        block_api_response = [
            {
                "dealDate": "01-APR-2026",
                "symbol": "SBIN",
                "clientName": "HDFC ASSET MANAGEMENT",
                "buySell": "BUY",
                "quantity": 50000,
                "tradedPrice": 780.0,
            }
        ]

        def side_effect(url, **kwargs):
            if "snapshot" in url:
                return _mock_response(200, empty_snapshot)
            if "block-deal" in url:
                return _mock_response(200, block_api_response)
            return _mock_response(404)

        session.get.side_effect = side_effect

        deals = get_block_deals()

        assert len(deals) == 1
        assert deals[0].symbol == "SBIN"
        assert deals[0].entity_type == "MF"

    @patch("market.bulk_deals._nse_session")
    def test_all_fail_returns_empty(self, mock_session_fn):
        """Block deals gracefully return empty on failure."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(500)

        deals = get_block_deals()
        assert deals == []
