# Spec: OpenClaw Manifest — Add Missing Skills (#125)

## Problem
`/.well-known/openclaw.json` is missing 13 skills added after the initial manifest was written.
External agents discovering the platform via OpenClaw cannot access these capabilities.

## Scope
Update `web/openclaw.py` — the `MANIFEST` dict — to include all skill endpoints
currently implemented in `web/skills.py`.

## Missing Skills

| Skill | Endpoint | Description |
|-------|----------|-------------|
| IV Smile | POST /skills/iv_smile | Implied volatility smile curve across strikes |
| GEX | POST /skills/gex | Gamma Exposure heatmap for NIFTY/BANKNIFTY |
| Risk Report | POST /skills/risk_report | Full portfolio risk analysis |
| Strategy | POST /skills/strategy | Options strategy builder and evaluator |
| What-If | POST /skills/whatif | Scenario analysis — what if price moves X% |
| Greeks | POST /skills/greeks | Options Greeks for a specific contract |
| OI Analysis | POST /skills/oi | Open interest profile and key levels |
| Scan | POST /skills/scan | Market scanner — filter stocks by conditions |
| Patterns | POST /skills/patterns | Chart pattern recognition |
| Delta Hedge | POST /skills/delta_hedge | Delta hedging recommendations |
| Drift | POST /skills/drift | Portfolio drift analysis vs target allocation |
| Memory | POST /skills/memory | Trade memory — store/recall past analyses |
| Memory Query | POST /skills/memory/query | Query trade memory by symbol, verdict, etc. |

## Also missing (broker/portfolio endpoints worth documenting)
| Holdings | POST /skills/holdings | Portfolio holdings |
| Positions | POST /skills/positions | Open intraday positions |
| Profile | POST /skills/profile | Broker profile and margin info |
| Funds | POST /skills/funds | Available funds |
| Orders | POST /skills/orders | Order history |

## Schema Requirements
Each entry must have:
- `name` — unique slug matching the endpoint path
- `path` — full URL path e.g. `/skills/iv_smile`
- `method` — `"POST"`
- `description` — what it does, expected latency if slow
- `input_schema` — JSON Schema with `properties` and `required`
- `output_description` — what the response contains

## Acceptance Criteria
- All 13 missing skills appear in the manifest
- `/.well-known/openclaw.json` validates as valid JSON
- Each skill entry has all 5 required fields
- Existing skills unchanged
