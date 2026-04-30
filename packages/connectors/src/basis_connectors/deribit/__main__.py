"""CLI smoke entrypoint: discover instruments and stream a few tickers.

Usage:
    uv run python -m basis_connectors.deribit --currency BTC --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from basis_contracts import AssetKind, Currency

from basis_connectors.deribit import DeribitRestClient, DeribitWsClient


async def _main(currency: Currency, limit: int, kind: AssetKind | None) -> None:
    async with DeribitRestClient() as rest:
        kinds = [kind] if kind is not None else None
        instruments = await rest.get_instruments(currency, kinds=kinds)

    print(f"discovered {len(instruments)} {currency.value} instruments")
    if not instruments:
        return

    # Pick a small subset: perpetual + first few options/futures.
    perps = [i for i in instruments if i.asset_kind == AssetKind.PERPETUAL]
    others = [i for i in instruments if i.asset_kind != AssetKind.PERPETUAL]
    sample = (perps + others)[:limit]
    symbols = [i.symbol for i in sample]
    print("subscribing to:", ", ".join(symbols))

    ws = DeribitWsClient()
    received = 0
    async for snap in ws.iter_tickers(symbols):
        print(
            f"{snap.timestamp.isoformat()} {snap.symbol} mark={snap.mark_price} "
            f"iv={snap.mark_iv} funding={snap.funding_rate}"
        )
        received += 1
        if received >= limit * 3:
            break


def main() -> None:
    """Run the CLI smoke entrypoint."""
    parser = argparse.ArgumentParser(description="Deribit collector smoke test")
    parser.add_argument(
        "--currency", choices=[c.value for c in Currency], default=Currency.BTC.value
    )
    parser.add_argument(
        "--kind",
        choices=[k.value for k in AssetKind],
        default=None,
        help="Restrict to a single asset kind.",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(
        _main(
            Currency(args.currency),
            args.limit,
            AssetKind(args.kind) if args.kind else None,
        )
    )


if __name__ == "__main__":
    main()
