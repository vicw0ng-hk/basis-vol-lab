"""CLI smoke entrypoint: discover Binance instruments and stream mark prices.

Usage:
    uv run python -m basis_connectors.binance --symbols BTCUSDT --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from basis_connectors.binance import BinanceRestClient, BinanceWsClient

_PROD_REST = "https://fapi.binance.com"
_PROD_WS = "wss://fstream.binance.com"
_TESTNET_REST = "https://testnet.binancefuture.com"
_TESTNET_WS = "wss://stream.binancefuture.com"


async def _main(symbols: list[str], limit: int, rest_url: str, ws_url: str) -> None:
    async with BinanceRestClient(base_url=rest_url) as rest:
        instruments = await rest.get_exchange_info()
    print(f"discovered {len(instruments)} instruments")
    for inst in instruments:
        print(f"  {inst.symbol:<20} {inst.asset_kind.value:<10} {inst.currency.value}")

    if not symbols:
        symbols = ["BTCUSDT", "ETHUSDT"]

    print(f"\nstreaming mark prices for: {', '.join(symbols)}")
    ws = BinanceWsClient(base_url=ws_url)
    received = 0
    async for snap in ws.iter_mark_prices(symbols):
        print(
            f"{snap.timestamp.isoformat()} {snap.symbol} "
            f"mark={snap.mark_price} funding={snap.funding_rate}"
        )
        received += 1
        if received >= limit:
            break


def main() -> None:
    """Run the CLI smoke entrypoint."""
    parser = argparse.ArgumentParser(description="Binance collector smoke test")
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=["BTCUSDT", "ETHUSDT"],
        help="Binance futures symbols to filter to.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use Binance futures testnet (useful when prod is geo-blocked).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    rest_url = _TESTNET_REST if args.testnet else _PROD_REST
    ws_url = _TESTNET_WS if args.testnet else _PROD_WS

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(_main(args.symbols, args.limit, rest_url, ws_url))


if __name__ == "__main__":
    main()
