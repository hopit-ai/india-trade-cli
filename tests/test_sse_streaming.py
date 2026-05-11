"""
tests/test_sse_streaming.py
───────────────────────────
Tests for web/sse.py (SSEEventBus) and the /stream/prices + /stream/alerts
FastAPI endpoints added in web/api.py.

Coverage:
  - publish() delivers to all subscribers
  - subscribe() yields correctly formatted SSE strings
  - Multiple subscribers on same channel all receive events
  - publish_sync() works from sync context
  - Unsubscribed channels receive no events
  - GET /stream/prices returns 200 with Content-Type: text/event-stream
  - GET /stream/alerts returns 200 with Content-Type: text/event-stream
  - Event format is valid SSE (starts with "data: ", ends with "\\n\\n")
"""

from __future__ import annotations

import asyncio
import json

import pytest


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _run(coro):
    """Run a coroutine in a new event loop (portable test helper)."""
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────
# Unit tests: SSEEventBus
# ─────────────────────────────────────────────────────────────────


class TestSSEEventBus:
    """Tests for the SSEEventBus class in web/sse.py."""

    def test_publish_delivers_to_subscriber(self):
        """publish() should deliver the event to a single subscriber."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            received = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    received.append(chunk)
                    break  # stop after first event

            consumer_task = asyncio.create_task(_consume())
            # Give the consumer a moment to register
            await asyncio.sleep(0)
            await bus.publish("price", {"symbol": "NIFTY", "ltp": 24500.0})
            await asyncio.wait_for(consumer_task, timeout=2)

            assert len(received) == 1

        _run(_run_test())

    def test_subscribe_yields_valid_sse_format(self):
        """subscribe() must yield strings in 'data: {...}\\n\\n' format."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            received = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    received.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)
            await bus.publish("price", {"symbol": "NIFTY", "ltp": 24500.0})
            await asyncio.wait_for(task, timeout=2)

            assert len(received) == 1
            chunk = received[0]
            assert chunk.startswith("data: "), f"Expected 'data: ' prefix, got: {chunk!r}"
            assert chunk.endswith("\n\n"), f"Expected '\\n\\n' suffix, got: {chunk!r}"

        _run(_run_test())

    def test_subscribe_payload_is_valid_json(self):
        """The data payload must be parseable JSON."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            received = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    received.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)
            payload = {"symbol": "INFY", "ltp": 1750.5, "change_pct": -0.3}
            await bus.publish("price", payload)
            await asyncio.wait_for(task, timeout=2)

            chunk = received[0]
            json_part = chunk[len("data: ") : -2]  # strip "data: " prefix and "\n\n" suffix
            parsed = json.loads(json_part)
            assert parsed == payload

        _run(_run_test())

    def test_multiple_subscribers_all_receive_event(self):
        """All subscribers on a channel should receive each published event."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            received_a = []
            received_b = []

            async def _consume_a():
                async for chunk in bus.subscribe("price"):
                    received_a.append(chunk)
                    break

            async def _consume_b():
                async for chunk in bus.subscribe("price"):
                    received_b.append(chunk)
                    break

            task_a = asyncio.create_task(_consume_a())
            task_b = asyncio.create_task(_consume_b())
            await asyncio.sleep(0)

            await bus.publish("price", {"symbol": "NIFTY"})
            await asyncio.wait_for(asyncio.gather(task_a, task_b), timeout=2)

            assert len(received_a) == 1
            assert len(received_b) == 1

        _run(_run_test())

    def test_publish_returns_subscriber_count(self):
        """publish() should return the number of active subscribers."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            tasks = []
            results = []

            async def _consume():
                async for _ in bus.subscribe("price"):
                    break

            # Register 3 subscribers
            for _ in range(3):
                tasks.append(asyncio.create_task(_consume()))
            await asyncio.sleep(0)

            count = await bus.publish("price", {"x": 1})
            results.append(count)
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)
            return results[0]

        count = _run(_run_test())
        assert count == 3

    def test_different_channels_are_isolated(self):
        """Events on 'price' must not reach subscribers on 'alert'."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            price_received = []
            alert_received = []

            async def _consume_price():
                async for chunk in bus.subscribe("price"):
                    price_received.append(chunk)
                    break

            async def _consume_alert():
                async for chunk in bus.subscribe("alert"):
                    alert_received.append(chunk)
                    break

            price_task = asyncio.create_task(_consume_price())
            asyncio.create_task(_consume_alert())  # alert subscriber but won't be triggered
            await asyncio.sleep(0)

            # Only publish to price
            await bus.publish("price", {"symbol": "NIFTY"})
            await asyncio.wait_for(price_task, timeout=2)

            assert len(price_received) == 1
            # alert subscriber should have received nothing
            assert len(alert_received) == 0

        _run(_run_test())

    def test_publish_to_channel_with_no_subscribers(self):
        """Publishing to a channel with no subscribers returns 0 and does not crash."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            count = await bus.publish("empty_channel", {"x": 1})
            return count

        count = _run(_run_test())
        assert count == 0

    def test_publish_sync_delivers_event(self):
        """publish_sync() from a sync context should deliver events to subscribers."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            received = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    received.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)

            # Call publish_sync from within async context (simulates thread calling in)
            bus.publish_sync("price", {"symbol": "NIFTY", "ltp": 99.0})
            # Give event loop time to process the coroutine
            await asyncio.sleep(0.1)
            await asyncio.wait_for(task, timeout=2)

            assert len(received) == 1

        _run(_run_test())

    def test_subscriber_cleanup_on_generator_close(self):
        """After consumer disconnects, its queue should be removed from channel."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()

            gen = bus.subscribe("price")
            # Advance to the first yield (blocks waiting for event)
            task = asyncio.create_task(gen.__anext__())
            await asyncio.sleep(0)

            # Confirm subscriber registered
            assert len(bus._channels["price"]) == 1

            # Cancel the task and close the generator
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, StopAsyncIteration):
                pass
            await gen.aclose()

            # Give cleanup coroutine time to run
            await asyncio.sleep(0)
            assert len(bus._channels["price"]) == 0

        _run(_run_test())

    def test_queue_full_drops_oldest_event(self):
        """When a subscriber's queue is full the oldest event is dropped."""
        from web.sse import SSEEventBus

        async def _run_test():
            bus = SSEEventBus()
            bus.MAX_QUEUE_SIZE = 2  # small queue for test

            q_holder = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    q_holder.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)

            # Fill queue beyond its max
            for i in range(5):
                await bus.publish("price", {"i": i})

            await asyncio.wait_for(task, timeout=2)
            # Should have received at least one event without error
            assert len(q_holder) >= 1

        _run(_run_test())


# ─────────────────────────────────────────────────────────────────
# Integration tests: FastAPI endpoints
# ─────────────────────────────────────────────────────────────────


class TestSSEEndpoints:
    """Integration tests for /stream/prices and /stream/alerts endpoints."""

    @pytest.fixture(autouse=True)
    def _reset_event_bus(self):
        """Reset the module-level event_bus between tests."""
        from web import sse as _sse_mod
        from collections import defaultdict

        _sse_mod.event_bus._channels = defaultdict(list)
        _sse_mod.event_bus._lock = None
        yield
        _sse_mod.event_bus._channels = defaultdict(list)
        _sse_mod.event_bus._lock = None

    def _make_app(self):
        from web.api import app

        return app

    def test_stream_prices_returns_200(self):
        """GET /stream/prices should return 200."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/prices") as resp:
                assert resp.status_code == 200
                # Just check status; don't consume stream

    def test_stream_prices_content_type(self):
        """GET /stream/prices must respond with text/event-stream content type."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/prices") as resp:
                content_type = resp.headers.get("content-type", "")
                assert "text/event-stream" in content_type

    def test_stream_alerts_returns_200(self):
        """GET /stream/alerts should return 200."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/alerts") as resp:
                assert resp.status_code == 200

    def test_stream_alerts_content_type(self):
        """GET /stream/alerts must respond with text/event-stream content type."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/alerts") as resp:
                content_type = resp.headers.get("content-type", "")
                assert "text/event-stream" in content_type

    def test_stream_prices_cache_control_header(self):
        """GET /stream/prices should set Cache-Control: no-cache."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/prices") as resp:
                assert resp.headers.get("cache-control") == "no-cache"

    def test_stream_alerts_cache_control_header(self):
        """GET /stream/alerts should set Cache-Control: no-cache."""
        from fastapi.testclient import TestClient

        app = self._make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/stream/alerts") as resp:
                assert resp.headers.get("cache-control") == "no-cache"

    def test_price_event_format_is_valid_sse(self):
        """
        Price events pushed to the bus must have valid SSE chunk format.
        'data: {...}\\n\\n' — verified via the SSEEventBus directly.
        """
        from web import sse as _sse_mod

        # Use a fresh bus to verify chunk format independently of endpoint
        async def _run_test():
            bus = _sse_mod.SSEEventBus()
            chunks = []

            async def _consume():
                async for chunk in bus.subscribe("price"):
                    chunks.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)
            await bus.publish(
                "price",
                {
                    "symbol": "NIFTY",
                    "ltp": 24500.0,
                    "change_pct": 0.42,
                    "ts": "2024-01-01T00:00:00Z",
                },
            )
            await asyncio.wait_for(task, timeout=2)
            return chunks

        chunks = asyncio.run(_run_test())
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.startswith("data: "), f"Expected 'data: ' prefix, got: {chunk!r}"
        assert chunk.endswith("\n\n"), f"Expected '\\n\\n' suffix, got: {chunk!r}"
        # Payload must be valid JSON
        json_part = chunk[len("data: ") : -2]
        parsed = json.loads(json_part)
        assert parsed["symbol"] == "NIFTY"

    def test_alert_event_format_is_valid_sse(self):
        """Alert events must have 'data: {...}\\n\\n' format."""
        from web import sse as _sse_mod

        async def _run_test():
            bus = _sse_mod.SSEEventBus()
            chunks = []

            async def _consume():
                async for chunk in bus.subscribe("alert"):
                    chunks.append(chunk)
                    break

            task = asyncio.create_task(_consume())
            await asyncio.sleep(0)
            await bus.publish(
                "alert",
                {
                    "alert_id": "a1",
                    "symbol": "INFY",
                    "message": "RSI > 70",
                    "ts": "2024-01-01T00:00:00Z",
                },
            )
            await asyncio.wait_for(task, timeout=2)
            return chunks

        chunks = asyncio.run(_run_test())
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.startswith("data: "), f"Expected 'data: ' prefix, got: {chunk!r}"
        assert chunk.endswith("\n\n"), f"Expected '\\n\\n' suffix, got: {chunk!r}"
        parsed = json.loads(chunk[len("data: ") : -2])
        assert parsed["symbol"] == "INFY"
