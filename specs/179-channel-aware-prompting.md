# Spec: Channel-aware prompting (#179)

## Problem
CLI, Electron, API, and WhatsApp channels need different output formats.
The agent currently produces one format regardless of where output goes.

## Solution
Add `CHANNEL_FORMATS` dict and `get_channel_hint()` to `agent/prompts.py`.

Channels:
- `cli` — 80 char width, emoji, tables, full verbosity
- `electron` — 120 char width, markdown UI hint
- `api` — no width limit, no emoji, concise, structured
- `whatsapp` — 60 char, plain text, no markdown, <200 words

In `web/skills.py`:
- `AnalyzeRequest` gains `channel: str = "api"` field
- Before calling `analyzer.analyze()`, inject `get_channel_hint(channel)` via `user_hints`

## Tests
`tests/test_channel_prompting.py`
