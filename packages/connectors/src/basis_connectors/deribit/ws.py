"""Async WebSocket client for Deribit public ticker streams.

Implements the operational basics required for an MVP collector:

* JSON-RPC subscribe over ``wss://www.deribit.com/ws/api/v2``.
* Heartbeat (``public/set_heartbeat``) with replies to ``test_request``.
* Reconnect with exponential backoff on disconnect, replaying the live
  subscription set.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Iterable
from itertools import count
from typing import Any

import websockets
from basis_contracts import TickerSnapshot
from websockets.asyncio.client import ClientConnection

from basis_connectors.deribit.parsers import parse_ticker

DEFAULT_WS_URL = "wss://www.deribit.com/ws/api/v2"

_LOG = logging.getLogger(__name__)

# Sentinel pushed into the queue to signal end-of-stream.
_DONE: object = object()


class DeribitWsClient:
    """Public WebSocket client for Deribit ticker channels."""

    def __init__(
        self,
        *,
        url: str = DEFAULT_WS_URL,
        heartbeat_interval: int = 30,
        max_backoff: float = 30.0,
        ticker_interval: str = "100ms",
        queue_size: int = 1024,
    ) -> None:
        """Initialize the client.

        Args:
            url: WebSocket endpoint.
            heartbeat_interval: Seconds between server heartbeats.
            max_backoff: Cap for reconnect exponential backoff.
            ticker_interval: Deribit ticker interval (``100ms``, ``agg2``,
                ``1000ms``, or ``raw``). ``raw`` requires authentication.
            queue_size: Maximum buffered tickers between the receive loop and
                the consumer.
        """
        self._url = url
        self._heartbeat_interval = heartbeat_interval
        self._max_backoff = max_backoff
        self._ticker_interval = ticker_interval
        self._queue_size = queue_size
        self._id_counter = count(1)

    def _next_id(self) -> int:
        return next(self._id_counter)

    async def iter_tickers(
        self, symbols: Iterable[str]
    ) -> AsyncIterator[TickerSnapshot]:
        """Yield parsed tickers for the given Deribit instrument symbols.

        The receive loop runs as a background task and reconnects with
        exponential backoff, resubscribing the full channel set on each new
        connection. The iterator stops only when the consumer breaks out or
        when the receive loop exits with an unhandled error.
        """
        channels = [f"ticker.{s}.{self._ticker_interval}" for s in symbols]
        if not channels:
            return

        queue: asyncio.Queue[TickerSnapshot | object] = asyncio.Queue(
            maxsize=self._queue_size
        )
        receiver = asyncio.create_task(self._receive_loop(channels, queue))
        try:
            while True:
                item = await queue.get()
                if item is _DONE:
                    break
                assert isinstance(item, TickerSnapshot)
                yield item
        finally:
            receiver.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver

    async def _receive_loop(
        self,
        channels: list[str],
        queue: asyncio.Queue[TickerSnapshot | object],
    ) -> None:
        backoff = 1.0
        try:
            while True:
                try:
                    async with websockets.connect(self._url) as ws:
                        await self._set_heartbeat(ws)
                        await self._subscribe(ws, channels)
                        backoff = 1.0
                        await self._consume(ws, queue)
                except (TimeoutError, websockets.ConnectionClosed, OSError) as exc:
                    _LOG.warning(
                        "Deribit WS disconnected: %s; reconnecting in %.1fs",
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self._max_backoff)
        finally:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(_DONE)

    async def _consume(
        self,
        ws: ClientConnection,
        queue: asyncio.Queue[TickerSnapshot | object],
    ) -> None:
        async for raw in ws:
            if isinstance(raw, bytes):
                raw = raw.decode()
            msg = json.loads(raw)

            method = msg.get("method")
            if method == "heartbeat":
                params = msg.get("params") or {}
                if params.get("type") == "test_request":
                    await self._send(ws, "public/test", {})
                continue

            if method == "subscription":
                params = msg.get("params") or {}
                data = params.get("data")
                channel = params.get("channel", "")
                if isinstance(data, dict) and channel.startswith("ticker."):
                    try:
                        snap = parse_ticker(data)
                    except (KeyError, ValueError) as exc:
                        _LOG.warning("dropping malformed ticker: %s", exc)
                        continue
                    await queue.put(snap)
                continue

            if "error" in msg:
                _LOG.error("deribit error response: %s", msg["error"])

    async def _set_heartbeat(self, ws: ClientConnection) -> None:
        await self._send(
            ws,
            "public/set_heartbeat",
            {"interval": self._heartbeat_interval},
        )

    async def _subscribe(self, ws: ClientConnection, channels: list[str]) -> None:
        await self._send(ws, "public/subscribe", {"channels": channels})

    async def _send(
        self,
        ws: ClientConnection,
        method: str,
        params: dict[str, Any],
    ) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        await ws.send(json.dumps(payload))
