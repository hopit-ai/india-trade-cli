"""
web/sse.py
──────────
Server-Sent Events bus for real-time price and alert streaming.

Usage:
    from web.sse import event_bus

    event_bus.publish("price", {"symbol": "NIFTY", "ltp": 24500.0})
    event_bus.publish("alert", {"symbol": "INFY", "message": "RSI > 70"})

    # In FastAPI endpoint:
    async for chunk in event_bus.subscribe("price"):
        yield chunk
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator


class SSEEventBus:
    """
    Simple pub/sub bus for SSE streams.

    Each channel (e.g. "price", "alert") has a list of subscriber queues.
    Publishers push events; subscribers receive them via async generators.

    Max queue size: 100 events per subscriber (oldest dropped if full).
    Heartbeat: sends ": heartbeat\\n\\n" every 15s to keep connections alive.
    """

    HEARTBEAT_INTERVAL = 15  # seconds
    MAX_QUEUE_SIZE = 100

    def __init__(self) -> None:
        self._channels: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily create lock so it's always on the running event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def publish(self, channel: str, data: dict) -> int:
        """Publish to all subscribers on channel. Returns subscriber count."""
        async with self._get_lock():
            queues = list(self._channels[channel])

        count = 0
        for q in queues:
            try:
                q.put_nowait(data)
                count += 1
            except asyncio.QueueFull:
                # Drop oldest event to make room
                try:
                    q.get_nowait()
                    q.put_nowait(data)
                    count += 1
                except Exception:
                    pass
        return count

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings: 'data: {...}\\n\\n'"""
        q: asyncio.Queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)

        async with self._get_lock():
            self._channels[channel].append(q)

        try:
            while True:
                try:
                    # Wait for next event with heartbeat timeout
                    data = await asyncio.wait_for(q.get(), timeout=self.HEARTBEAT_INTERVAL)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        finally:
            async with self._get_lock():
                try:
                    self._channels[channel].remove(q)
                except ValueError:
                    pass

    def publish_sync(self, channel: str, data: dict) -> None:
        """Thread-safe publish from sync code (e.g. polling threads)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.publish(channel, data), loop)
            else:
                loop.run_until_complete(self.publish(channel, data))
        except RuntimeError:
            # No event loop available — best-effort: push directly to queues
            for q in self._channels.get(channel, []):
                try:
                    q.put_nowait(data)
                except (asyncio.QueueFull, Exception):
                    pass


event_bus = SSEEventBus()  # module-level singleton
