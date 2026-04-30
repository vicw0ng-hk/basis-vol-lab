"""Pure parser functions for Binance USD-margined futures payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from basis_contracts import (
    AssetKind,
    Currency,
    Instrument,
    TickerSnapshot,
    Venue,
)

from basis_connectors.binance.types import BasisRow, FundingRateRow, OpenInterestRow

# Only USDT-quoted, BTC/ETH-based futures are in scope.
_SUPPORTED_QUOTES = {"USDT"}
_CONTRACT_TYPE_TO_KIND: dict[str, AssetKind] = {
    "PERPETUAL": AssetKind.PERPETUAL,
    "CURRENT_QUARTER": AssetKind.FUTURE,
    "NEXT_QUARTER": AssetKind.FUTURE,
    "CURRENT_QUARTER_DELIVERING": AssetKind.FUTURE,
    "NEXT_QUARTER_DELIVERING": AssetKind.FUTURE,
}


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _parse_currency(token: str) -> Currency | None:
    try:
        return Currency(token)
    except ValueError:
        return None


def parse_exchange_info_symbol(raw: dict[str, Any]) -> Instrument | None:
    """Map a `/fapi/v1/exchangeInfo.symbols[i]` row to an `Instrument`.

    Returns ``None`` for symbols outside our scope (non-USDT, non-BTC/ETH,
    unknown contract type).
    """
    quote = raw.get("quoteAsset")
    if quote not in _SUPPORTED_QUOTES:
        return None

    base = raw.get("baseAsset")
    if not isinstance(base, str):
        return None
    currency = _parse_currency(base)
    if currency is None:
        return None

    contract_type = raw.get("contractType")
    if not isinstance(contract_type, str):
        return None
    kind = _CONTRACT_TYPE_TO_KIND.get(contract_type)
    if kind is None:
        return None

    symbol = raw.get("symbol")
    if not isinstance(symbol, str):
        return None

    expiry: datetime | None = None
    if kind is AssetKind.FUTURE:
        delivery = raw.get("deliveryDate")
        if isinstance(delivery, int) and delivery > 0:
            expiry = _ms_to_dt(delivery)

    is_active = raw.get("status") == "TRADING"

    return Instrument(
        venue=Venue.BINANCE,
        symbol=symbol,
        currency=currency,
        asset_kind=kind,
        expiry=expiry,
        strike=None,
        is_active=is_active,
    )


def _classify_symbol(symbol: str) -> tuple[Currency, AssetKind] | None:
    """Decode a Binance futures symbol into ``(currency, kind)``.

    Symbols look like ``BTCUSDT`` (perp) or ``BTCUSDT_260626`` (delivery).
    """
    base_symbol = symbol.split("_", 1)[0]
    if not base_symbol.endswith("USDT"):
        return None
    base = base_symbol[: -len("USDT")]
    currency = _parse_currency(base)
    if currency is None:
        return None
    kind = AssetKind.PERPETUAL if "_" not in symbol else AssetKind.FUTURE
    return currency, kind


def parse_mark_price_event(raw: dict[str, Any]) -> TickerSnapshot | None:
    """Map a `markPriceUpdate` event to a `TickerSnapshot`.

    Returns ``None`` for symbols outside our scope.
    """
    symbol = raw.get("s")
    if not isinstance(symbol, str):
        return None
    classified = _classify_symbol(symbol)
    if classified is None:
        return None
    currency, kind = classified

    event_time = raw.get("E")
    if not isinstance(event_time, int):
        return None

    funding_raw = raw.get("r")
    if isinstance(funding_raw, str) and funding_raw.strip():
        funding_rate: float | None = float(funding_raw)
    else:
        funding_rate = None

    return TickerSnapshot(
        venue=Venue.BINANCE,
        symbol=symbol,
        currency=currency,
        asset_kind=kind,
        timestamp=_ms_to_dt(event_time),
        mark_price=float(raw["p"]),
        bid=None,
        ask=None,
        mark_iv=None,
        open_interest=None,
        funding_rate=funding_rate,
    )


def parse_funding_rate_row(raw: dict[str, Any]) -> FundingRateRow:
    """Parse a row from `/fapi/v1/fundingRate`."""
    mark_raw = raw.get("markPrice")
    mark_price = (
        float(mark_raw)
        if isinstance(mark_raw, str | int | float) and str(mark_raw) != ""
        else None
    )
    return FundingRateRow(
        symbol=str(raw["symbol"]),
        funding_time=_ms_to_dt(int(raw["fundingTime"])),
        funding_rate=float(raw["fundingRate"]),
        mark_price=mark_price,
    )


def parse_basis_row(raw: dict[str, Any]) -> BasisRow:
    """Parse a row from `/futures/data/basis`."""
    return BasisRow(
        pair=str(raw["pair"]),
        contract_type=str(raw["contractType"]),
        timestamp=_ms_to_dt(int(raw["timestamp"])),
        basis=float(raw["basis"]),
        basis_rate=float(raw["basisRate"]),
        futures_price=float(raw["futuresPrice"]),
        index_price=float(raw["indexPrice"]),
    )


def parse_oi_row(raw: dict[str, Any]) -> OpenInterestRow:
    """Parse a row from `/futures/data/openInterestHist`."""
    return OpenInterestRow(
        symbol=str(raw["symbol"]),
        timestamp=_ms_to_dt(int(raw["timestamp"])),
        sum_open_interest=float(raw["sumOpenInterest"]),
        sum_open_interest_value=float(raw["sumOpenInterestValue"]),
    )
