"""Tests for basis_contracts models and enums."""

from datetime import UTC, datetime

from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue


def test_venue_enum_values() -> None:
    assert Venue.DERIBIT == "deribit"
    assert Venue.BINANCE == "binance"


def test_asset_kind_enum_values() -> None:
    assert AssetKind.OPTION == "option"
    assert AssetKind.FUTURE == "future"
    assert AssetKind.PERPETUAL == "perpetual"


def test_currency_enum_values() -> None:
    assert Currency.BTC == "BTC"
    assert Currency.ETH == "ETH"


def test_ticker_snapshot_creation() -> None:
    ts = TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol="BTC-PERPETUAL",
        currency=Currency.BTC,
        asset_kind=AssetKind.PERPETUAL,
        timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        mark_price=95000.0,
        funding_rate=0.0001,
    )
    assert ts.venue == Venue.DERIBIT
    assert ts.mark_price == 95000.0
    assert ts.mark_iv is None
    assert ts.funding_rate == 0.0001
