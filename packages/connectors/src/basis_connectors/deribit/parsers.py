"""Pure parser functions for Deribit market-data payloads.

These functions are deliberately decoupled from network I/O so they can be
unit-tested against fixture JSON.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from basis_contracts import (
    AssetKind,
    Currency,
    Instrument,
    TickerSnapshot,
    Venue,
)

# Deribit instrument names look like:
#   BTC-PERPETUAL
#   BTC-26JUN26                       (future)
#   BTC-26JUN26-100000-C              (option call)
#   ETH-30MAY26-3000-P                (option put)
_PERP_RE = re.compile(r"^(?P<ccy>[A-Z]+)-PERPETUAL$")
_FUTURE_RE = re.compile(r"^(?P<ccy>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})$")
_OPTION_RE = re.compile(
    r"^(?P<ccy>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})-"
    r"(?P<strike>\d+(?:\.\d+)?)-(?P<right>[CP])$"
)

# Deribit option/future settlement: 08:00 UTC on the expiry date.
_DERIBIT_SETTLEMENT_HOUR = 8


def _parse_expiry(token: str) -> datetime | None:
    """Parse a Deribit expiry token like ``26JUN26`` to a UTC datetime."""
    try:
        # ``%y`` accepts 2-digit years; Deribit always uses YY form here.
        d = datetime.strptime(token, "%d%b%y")
    except ValueError:
        return None
    return d.replace(hour=_DERIBIT_SETTLEMENT_HOUR, tzinfo=UTC)


def _parse_currency(token: str) -> Currency | None:
    try:
        return Currency(token)
    except ValueError:
        return None


def parse_instrument_name(
    name: str,
) -> tuple[Currency, AssetKind, datetime | None, float | None] | None:
    """Decode a Deribit instrument-name to (currency, kind, expiry, strike).

    Returns ``None`` for unsupported currencies or malformed names.
    """
    m = _PERP_RE.match(name)
    if m:
        ccy = _parse_currency(m["ccy"])
        if ccy is None:
            return None
        return (ccy, AssetKind.PERPETUAL, None, None)

    m = _OPTION_RE.match(name)
    if m:
        ccy = _parse_currency(m["ccy"])
        expiry = _parse_expiry(m["expiry"])
        if ccy is None or expiry is None:
            return None
        return (ccy, AssetKind.OPTION, expiry, float(m["strike"]))

    m = _FUTURE_RE.match(name)
    if m:
        ccy = _parse_currency(m["ccy"])
        expiry = _parse_expiry(m["expiry"])
        if ccy is None or expiry is None:
            return None
        return (ccy, AssetKind.FUTURE, expiry, None)

    return None


def parse_instrument(raw: dict[str, Any]) -> Instrument | None:
    """Map a Deribit ``/public/get_instruments`` row to an `Instrument`.

    Returns ``None`` for instruments outside our supported scope (non-BTC/ETH,
    unsupported kind, or unparseable name).
    """
    name = raw.get("instrument_name")
    if not isinstance(name, str):
        return None

    decoded = parse_instrument_name(name)
    if decoded is None:
        return None
    currency, kind, expiry, strike = decoded

    # Prefer the API-provided strike/expiry when present, but fall back to the
    # name-derived values.
    raw_strike = raw.get("strike")
    if raw_strike is not None:
        strike = float(raw_strike)

    if kind is not AssetKind.PERPETUAL:
        raw_expiry = raw.get("expiration_timestamp")
        if isinstance(raw_expiry, int):
            expiry = datetime.fromtimestamp(raw_expiry / 1000, tz=UTC)

    is_active = bool(raw.get("is_active", True))

    return Instrument(
        venue=Venue.DERIBIT,
        symbol=name,
        currency=currency,
        asset_kind=kind,
        expiry=expiry if kind is not AssetKind.PERPETUAL else None,
        strike=strike if kind is AssetKind.OPTION else None,
        is_active=is_active,
    )


def parse_ticker(raw: dict[str, Any]) -> TickerSnapshot:
    """Map a Deribit ticker payload to a `TickerSnapshot`.

    Raises ``ValueError`` if the instrument name cannot be decoded — tickers
    we don't recognise should never reach this function.
    """
    name = raw["instrument_name"]
    decoded = parse_instrument_name(name)
    if decoded is None:
        raise ValueError(f"unsupported Deribit instrument name: {name!r}")
    currency, kind, _expiry, _strike = decoded

    ts_ms = int(raw["timestamp"])
    timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)

    mark_iv_raw = raw.get("mark_iv")
    mark_iv = float(mark_iv_raw) / 100.0 if mark_iv_raw is not None else None

    funding_raw = raw.get("funding_8h") if kind is AssetKind.PERPETUAL else None
    funding_rate = float(funding_raw) if funding_raw is not None else None

    bid_raw = raw.get("best_bid_price")
    ask_raw = raw.get("best_ask_price")
    oi_raw = raw.get("open_interest")

    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=name,
        currency=currency,
        asset_kind=kind,
        timestamp=timestamp,
        mark_price=float(raw["mark_price"]),
        bid=float(bid_raw) if bid_raw is not None else None,
        ask=float(ask_raw) if ask_raw is not None else None,
        mark_iv=mark_iv,
        open_interest=float(oi_raw) if oi_raw is not None else None,
        funding_rate=funding_rate,
    )
