"""Validate our Black-76 IV against Deribit's `mark_iv` on a live snapshot.

Usage::

    uv run python -m basis_analytics.validate --currency BTC

Pulls one snapshot of every active BTC (or ETH) option plus the matching
futures/perp from Deribit's public REST API, then computes our IV from
the mark price and prints a per-tenor error table.

This script is intentionally self-contained: it does not import the
WebSocket connector, and it makes a single REST call that completes in a
few hundred milliseconds. No API credentials required.
"""

from __future__ import annotations

import argparse
import asyncio
import re
from datetime import UTC, datetime
from typing import Any

import httpx
import pandas as pd
from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue

from basis_analytics.validation import summarize_by_tenor, validate_iv

_DERIBIT_BASE = "https://www.deribit.com/api/v2"

# Deribit instrument name patterns (kept here to avoid coupling the
# analytics package to the connectors package; matches the connector's
# own parser).
_OPTION_RE = re.compile(
    r"^(?P<ccy>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})-"
    r"(?P<strike>\d+(?:\.\d+)?)-(?P<right>[CP])$"
)
_FUTURE_RE = re.compile(r"^(?P<ccy>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})$")
_PERP_RE = re.compile(r"^(?P<ccy>[A-Z]+)-PERPETUAL$")


def _decode_name(
    name: str,
) -> tuple[Currency, AssetKind, datetime | None, float | None] | None:
    if m := _PERP_RE.match(name):
        try:
            return Currency(m["ccy"]), AssetKind.PERPETUAL, None, None
        except ValueError:
            return None
    if m := _OPTION_RE.match(name):
        try:
            ccy = Currency(m["ccy"])
            expiry = datetime.strptime(m["expiry"], "%d%b%y").replace(
                hour=8, tzinfo=UTC
            )
        except ValueError:
            return None
        return ccy, AssetKind.OPTION, expiry, float(m["strike"])
    if m := _FUTURE_RE.match(name):
        try:
            ccy = Currency(m["ccy"])
            expiry = datetime.strptime(m["expiry"], "%d%b%y").replace(
                hour=8, tzinfo=UTC
            )
        except ValueError:
            return None
        return ccy, AssetKind.FUTURE, expiry, None
    return None


async def _book_summary(
    client: httpx.AsyncClient, currency: str, kind: str
) -> list[dict[str, Any]]:
    r = await client.get(
        f"{_DERIBIT_BASE}/public/get_book_summary_by_currency",
        params={"currency": currency, "kind": kind},
    )
    r.raise_for_status()
    return list(r.json().get("result", []))


def _row_to_snapshot(row: dict[str, Any]) -> TickerSnapshot | None:
    name = row.get("instrument_name")
    if not isinstance(name, str):
        return None
    decoded = _decode_name(name)
    if decoded is None:
        return None
    currency, kind, expiry, strike = decoded

    mark_price = row.get("mark_price")
    if mark_price is None:
        return None

    mark_iv_raw = row.get("mark_iv")
    mark_iv = float(mark_iv_raw) / 100.0 if mark_iv_raw is not None else None

    bid_raw = row.get("bid_price")
    ask_raw = row.get("ask_price")
    oi_raw = row.get("open_interest")

    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=name,
        currency=currency,
        asset_kind=kind,
        timestamp=datetime.now(tz=UTC),
        mark_price=float(mark_price),
        bid=float(bid_raw) if bid_raw is not None else None,
        ask=float(ask_raw) if ask_raw is not None else None,
        mark_iv=mark_iv,
        open_interest=float(oi_raw) if oi_raw is not None else None,
        funding_rate=None,
        expiry=expiry,
        strike=strike,
    )


async def _async_main(currency: str) -> int:
    async with httpx.AsyncClient(timeout=15.0) as client:
        options_raw, futures_raw = await asyncio.gather(
            _book_summary(client, currency, "option"),
            _book_summary(client, currency, "future"),
        )

    options = [s for s in (_row_to_snapshot(r) for r in options_raw) if s is not None]
    futures = [s for s in (_row_to_snapshot(r) for r in futures_raw) if s is not None]

    forwards: dict[datetime, float] = {}
    for f in futures:
        if f.asset_kind is AssetKind.FUTURE and f.expiry is not None:
            forwards[f.expiry] = f.mark_price

    print(  # noqa: T201
        f"snapshot: {len(options)} options, "
        f"{len(forwards)} dated futures for {currency}"
    )

    asof = datetime.now(tz=UTC)
    errors = validate_iv(options, forwards, asof=asof)
    if errors.empty:
        print("no errors computed (no overlapping expiries?)")  # noqa: T201
        return 1

    summary = summarize_by_tenor(errors)
    pd.set_option("display.float_format", "{:.5f}".format)
    print()  # noqa: T201
    print(summary.to_string())  # noqa: T201

    p95_overall = errors["abs_err"].dropna().quantile(0.95)
    print(f"\noverall p95 |error|: {p95_overall:.5f} vol points")  # noqa: T201
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--currency", choices=["BTC", "ETH"], default="BTC")
    args = parser.parse_args()
    Currency(args.currency)  # validate
    return asyncio.run(_async_main(args.currency))


if __name__ == "__main__":
    raise SystemExit(main())
