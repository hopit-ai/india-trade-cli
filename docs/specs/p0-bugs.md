# Spec: P0 Bug Fixes

## #114 — Follow-up routes through TradingAgent
**Root cause:** `/skills/analyze/followup` creates a TradingAgent which has tool-calling. Keywords like "AI" trigger get_quote instead of answering about the analysis.
**Fix:** Replace `agent.chat()` with direct LLM call using primed context. No tool routing.
**File:** `web/skills.py:1303`

## #124 — Telegram markdown not rendering
**Root cause:** All `reply_text()` calls in `bot/telegram_bot.py` missing `parse_mode`.
**Fix:** Add `_md_to_html()` helper to convert markdown → HTML. Add `parse_mode="HTML"` to all reply_text calls.
**File:** `bot/telegram_bot.py` (~20 locations)

## #105 — Chat markdown not rendered in app
**Root cause:** MarkdownCard.jsx handles markdown but escaped newlines (`\\n`) from the API may not be properly converted.
**Fix:** Verify `\\n` → `\n` conversion in MarkdownCard. Ensure `/skills/chat` returns raw markdown.
**File:** `macos-app/src/renderer/src/components/Cards/MarkdownCard.jsx`

## #142 — FII/DII today = 5-day
**Root cause:** `market/sentiment.py:89` takes `by_date.items()[:days]` without sorting by date. Insertion order may not be newest-first.
**Fix:** Sort `by_date` by date descending before taking first N days.
**File:** `market/sentiment.py:89`

## #107 — AI silently pivots on data gaps
**Root cause:** System prompt says "say so explicitly" but is too weak. LLM rationalises pivoting.
**Fix:** Add strict "don't pivot" guardrail to system prompt with examples.
**File:** `agent/prompts.py:52-54`

## #133 — Broker primary silently overwritten
**Root cause:** `register_broker(primary=True)` default. Every broker registered becomes primary. Last one wins.
**Fix:** Change default to `primary=False`. First broker stays primary via `not _primary_key` fallback.
**File:** `brokers/session.py:103`

## #137 — Broker shows green when token expired
**Root cause:** `is_authenticated()` checks if token FILE exists, not if token is VALID. Kite tokens expire daily.
**Fix:** Make is_authenticated() attempt a lightweight API call. Return false if it fails.
**File:** `brokers/zerodha.py`, `brokers/fyers.py` — is_authenticated()

## #116 — IV Smile PE IV solver fails for deep ITM
**Root cause:** Newton-Raphson IV solver diverges for deep ITM options. Sigma goes negative, clamped to 0.001 → reported as 0.1%.
**Fix:** Add adaptive step dampening (max 0.05 per iteration) + better bounds [0.001, 5.0] + convergence check.
**File:** `analysis/options.py:180-199`
