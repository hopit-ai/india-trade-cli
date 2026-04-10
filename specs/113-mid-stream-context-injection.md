# Spec: Smart Mid-Stream Context Injection (#113)

## Problem
User types context (e.g. "Focus on AI deals") while `analyze INFY` is streaming.
Currently this is queued as a post-analysis follow-up question — the 7 analysts, debate,
and synthesis never see it.

## Goal
Inject user context into the **synthesis prompt** if synthesis hasn't started yet.
Works across CLI, web app, and macOS app.

---

## Phase-Aware Behavior

| Current phase        | User types mid-stream     | Result                                    |
|---------------------|--------------------------|-------------------------------------------|
| `analysts` / `debate` | "Focus on AI deals"      | Injected into synthesis prompt            |
| `synthesis`          | "Focus on AI deals"      | Queued as follow-up (existing behavior)   |
| `done`              | "Focus on AI deals"      | Normal follow-up (existing behavior)      |

---

## API Contract

### SSE Events (modified/new)

**`started`** (modified — adds `stream_id`):
```json
{ "type": "started", "symbol": "INFY", "exchange": "NSE", "stream_id": "INFY_NSE_a1b2c3d4" }
```

**`hint_ack`** (new — confirms hint received):
```json
{ "type": "hint_ack", "hint": "Focus on AI deals" }
```

**`hint_applied`** (new — confirms hint was used in synthesis):
```json
{ "type": "hint_applied", "hint_text": "Focus on AI deals" }
```

### POST `/skills/analyze/hint` (new)

**Request:**
```json
{ "stream_id": "INFY_NSE_a1b2c3d4", "hint": "Focus on AI deals" }
```

**Response (analysis running):**
```json
{ "status": "queued" }
```

**Response (analysis finished):**
```json
{ "status": "expired" }
```

---

## Backend Changes

### `agent/multi_agent.py` — MultiAgentAnalyzer

**Constructor** — add:
```python
self.user_hints: queue.Queue = queue.Queue()
self._user_hint_text: str = ""
self._synthesis_started: bool = False
```

**`analyze()` method** — before synthesis phase:
```python
# Drain user hints
hints = []
while not self.user_hints.empty():
    try:
        hints.append(self.user_hints.get_nowait())
    except queue.Empty:
        break
self._user_hint_text = "\n".join(hints) if hints else ""
self._synthesis_started = True  # mark so late hints go to follow-up

if self._user_hint_text and self.progress_callback:
    self.progress_callback({"type": "hint_applied", "hint_text": self._user_hint_text})
```

**`_run_synthesis()` method** — after building `synthesis_prompt`:
```python
if self._user_hint_text:
    synthesis_prompt += (
        f"\n\n## USER CONTEXT (prioritize this)\n"
        f"The user specifically asked you to focus on:\n{self._user_hint_text}\n"
        f"Make sure your analysis directly addresses this request."
    )
```

### `web/skills.py` — Stream tracking + hint endpoint

**Module-level:**
```python
_active_streams: dict[str, "MultiAgentAnalyzer"] = {}
```

**`skill_analyze_stream`:**
- Generate `stream_id = f"{symbol}_{exchange}_{uuid4().hex[:8]}"`
- Register `_active_streams[stream_id] = analyzer` before `_run()`
- Include `stream_id` in `started` event
- `finally` block: `_active_streams.pop(stream_id, None)`

**New endpoint:**
```python
class HintRequest(BaseModel):
    stream_id: str
    hint: str

@router.post("/analyze/hint")
async def skill_analyze_hint(req: HintRequest):
    analyzer = _active_streams.get(req.stream_id)
    if not analyzer:
        return {"status": "expired"}
    if getattr(analyzer, "_synthesis_started", False):
        return {"status": "expired"}
    analyzer.user_hints.put(req.hint)
    if analyzer.progress_callback:
        analyzer.progress_callback({"type": "hint_ack", "hint": req.hint})
    return {"status": "queued"}
```

---

## Frontend Changes

### `chatStore.js`
- Add `activeStreamId: null`
- Add `setActiveStreamId: (id) => set({ activeStreamId: id })`
- Clear in `finalizeStreamingMessage`: `set({ isLoading: false, activeStreamId: null })`

### `InputBar.jsx` — submit() when isStreaming
```javascript
if (isStreaming) {
  setValue('')
  addUserMessage(text)
  if (activeStreamId) {
    fetch(`${getBaseUrl(port)}/skills/analyze/hint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream_id: activeStreamId, hint: text }),
    }).then(r => r.json()).then(res => {
      if (res.status === 'expired') setPendingContext(text)
    }).catch(() => setPendingContext(text))
  } else {
    setPendingContext(text)
  }
  return
}
```

### `StreamingAnalysisCard.jsx`
- Handle `hint_ack` event: store in card data, render pill "◆ Your context will shape the synthesis"
- Handle `hint_applied` event: update pill to "◆ Context applied"

### InputBar placeholder text
- During `analysts`/`debate`: `"Type to add context for synthesis..."`
- During `synthesis`: `"Analysis finishing — will be a follow-up..."`

---

## CLI Changes (`app/repl.py`)

Run analysis in background thread, accept stdin hints on main thread:
```python
import threading, select, sys

analyzer = MultiAgentAnalyzer(registry, provider, parallel=True, verbose=True)
result_holder = [None]

def _run():
    result_holder[0] = analyzer.analyze(symbol, exchange)

t = threading.Thread(target=_run, daemon=True)
t.start()

while t.is_alive():
    t.join(timeout=0.5)
    if t.is_alive() and select.select([sys.stdin], [], [], 0.1)[0]:
        hint = sys.stdin.readline().strip()
        if hint:
            analyzer.user_hints.put(hint)
            console.print(f"[dim]◆ Context queued for synthesis: {hint}[/dim]")

output = result_holder[0]
```

---

## Edge Cases

1. **Multiple hints**: All concatenated with newlines
2. **Empty/whitespace hint**: Ignored, no change to prompt
3. **Hint arrives after synthesis starts**: Returns `expired`, frontend falls back to `pendingContext` → follow-up
4. **Stream errors/cancellation**: `_active_streams` cleaned up in finally block
5. **Concurrent analyses**: Each has its own `stream_id` and queue — no cross-contamination
6. **CLI on Windows**: `select.select` doesn't work on stdin on Windows — guard with platform check, skip hint feature on Windows
