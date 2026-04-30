"""Async WebSocket client for Binance futures `markPrice@arr` streams.

Yields parsed `TickerSnapshot`s for BTC/ETH USDT perps and quarterly futures.

Operational notes:

* Binance closes individual connections after 24h; we reconnect with
  exponential backoff and resume the same combined stream.
* The `websockets` library handles control-frame ping/pong automatically; no
  custom keepalive is required.
* Since the 2026-04-23 base-URL migration, regular market data streams
  (markPrice, aggTrade, kline, ticker, etc.) live under the ``/market``
  path. Subscribing to them on the legacy ``/stream`` or ``/ws`` paths
  silently delivers no frames. See ``docs/planning/5.step4-binance-connector.md``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Iterable
from typing import Any

import websockets
from basis_contracts import TickerSnapshot

from basis_connectors.binance.parsers import parse_mark_price_event

DEFAULT_BASE_URL = "wss://fstream.binance.com"

_LOG = logging.getLogger(__name__)
_DONE: object = object()


class BinanceWsClient:
    """Public WebSocket client for Binance futures mark-price streams."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_backoff: float = 30.0,
        queue_size: int = 1024,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: WebSocket base URL.
            max_backoff: Cap for reconnect exponential backoff.
            queue_size: Maximum buffered tickers between the receive loop and
                the consumer.
        """
        self._base_url = base_url.rstrip("/")
        self._max_backoff = max_backoff
        self._queue_size = queue_size

    async def iter_mark_prices(
        self, symbols: Iterable[str] | None = None
    ) -> AsyncIterator[TickerSnapshot]:
        """Yield mark-price ticker snapshots.

        The Binance stream broadcasts **all** futures symbols every second;
        we parse each tick and filter to ``symbols`` if provided. If
        ``symbols`` is ``None``, every BTC/ETH USDT contract is yielded.
        """
        symbol_filter: set[str] | None = (
            {s.upper() for s in symbols} if symbols is not None else None
        )

        queue: asyncio.Queue[TickerSnapshot | object] = asyncio.Queue(
            maxsize=self._queue_size
        )
        receiver = asyncio.create_task(self._receive_loop(symbol_filter, queue))
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
        symbol_filter: set[str] | None,
        queue: asyncio.Queue[TickerSnapshot | object],
    ) -> None:
        url = f"{self._base_url}/market/stream?streams=!markPrice@arr@1s"
        backoff = 1.0
        try:
            while True:
                try:
                    async with websockets.connect(url) as ws:
                        backoff = 1.0
                        await self._consume(ws, symbol_filter, queue)
                except (TimeoutError, websockets.ConnectionClosed, OSError) as exc:
                    _LOG.warning(
                        "Binance WS disconnected: %s; reconnecting in %.1fs",
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
        ws: Any,
        symbol_filter: set[str] | None,
        queue: asyncio.Queue[TickerSnapshot | object],
    ) -> None:
        async for raw in ws:
            if isinstance(raw, bytes):
                raw = raw.decode()
            envelope = json.loads(raw)
            data = envelope.get("data")
            if not isinstance(data, list):
                continue
            for event in data:
                if symbol_filter is not None and event.get("s") not in symbol_filter:
                    continue
                try:
                    snap = parse_mark_price_event(event)
                except (KeyError, ValueError) as exc:
                    _LOG.warning("dropping malformed mark-price event: %s", exc)
                    continue
                if snap is None:
                    continue
                await queue.put(snap)
