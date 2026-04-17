# Spec: OpenAlgo Broker Reference Spike (#155)

## Context
OpenAlgo (github.com/marketcalls/openalgo) has 32 Indian broker implementations.
This spike references their auth flows and API mappings to build our own implementations
against `BrokerAPI`. No runtime dependency on OpenAlgo.

## Priority Brokers

### Dhan (HIGH — popular, good API)
- **Auth**: Client ID + Access Token (no OAuth redirect needed)
  - Token generated via Dhan trader portal
  - No TOTP, no PIN — simpler than Zerodha
- **Base URL**: `https://api.dhan.co`
- **Key endpoints**:
  - `POST /orders` — place order
  - `GET /orders` — order list
  - `GET /portfolio/holdings` — holdings
  - `GET /portfolio/positions` — positions
  - `GET /fundlimit` — available balance
  - `GET /charts/historical` — OHLCV data
- **Exchange codes**: `NSE_EQ`, `BSE_EQ`, `NSE_FNO`, `BSE_FNO`, `MCX_COMM`
- **Product types**: `CNC` (delivery), `INTRADAY` (MIS), `MARGIN` (NRML)
- **Order types**: `MARKET`, `LIMIT`, `STOP_LOSS`, `STOP_LOSS_MARKET`

### Shoonya/Finvasia (MEDIUM — free API)
- **Auth**: API key + password + TOTP (similar to Angel One)
- **Base URL**: websocket + REST `https://api.shoonya.com/NorenWClientTP/`
- **Key difference**: NorenAPI format (not REST-standard)
- Products: `C` (CNC), `I` (MIS), `M` (NRML), `H` (cover order)

## Dhan Broker Scaffold
Created `brokers/dhan.py` with:
- Full `BrokerAPI` implementation for Dhan
- Auth via `DHAN_CLIENT_ID` + `DHAN_ACCESS_TOKEN` env vars
- Exchange segment mapping (our `NSE`→`NSE_EQ`, etc.)
- Product type mapping (our `CNC`→`CNC`, `MIS`→`INTRADAY`, `NRML`→`MARGIN`)

## Files
- `brokers/dhan.py` — Dhan broker implementation (scaffold)
- `tests/test_dhan_broker.py` — interface compliance tests

## Notes
- Dhan does NOT require OAuth — any client with a valid access token can use the API
- Historical data is available via `/charts/historical` (same as Fyers style)
- WebSocket: `wss://api-order-update.dhan.co` (not same as Fyers)
