"""Tests for Deribit parsers (pure functions, no network)."""

from datetime import UTC, datetime

from basis_connectors.deribit import (
    parse_instrument,
    parse_instrument_name,
    parse_ticker,
)
from basis_contracts import AssetKind, Currency, Venue


class TestParseInstrumentName:
    """Decode Deribit instrument-name strings to (currency, kind, expiry, strike)."""

    def test_perpetual(self) -> None:
        result = parse_instrument_name("BTC-PERPETUAL")
        assert result is not None
        currency, kind, expiry, strike = result
        assert currency == Currency.BTC
        assert kind == AssetKind.PERPETUAL
        assert expiry is None
        assert strike is None

    def test_future(self) -> None:
        result = parse_instrument_name("BTC-26JUN26")
        assert result is not None
        currency, kind, expiry, strike = result
        assert currency == Currency.BTC
        assert kind == AssetKind.FUTURE
        assert expiry == datetime(2026, 6, 26, 8, 0, tzinfo=UTC)
        assert strike is None

    def test_option_call(self) -> None:
        result = parse_instrument_name("BTC-26JUN26-100000-C")
        assert result is not None
        currency, kind, expiry, strike = result
        assert currency == Currency.BTC
        assert kind == AssetKind.OPTION
        assert expiry == datetime(2026, 6, 26, 8, 0, tzinfo=UTC)
        assert strike == 100000.0

    def test_option_put_eth(self) -> None:
        result = parse_instrument_name("ETH-30MAY26-3000-P")
        assert result is not None
        currency, kind, expiry, strike = result
        assert currency == Currency.ETH
        assert kind == AssetKind.OPTION
        assert strike == 3000.0

    def test_unsupported_currency(self) -> None:
        assert parse_instrument_name("SOL-PERPETUAL") is None

    def test_garbage(self) -> None:
        assert parse_instrument_name("not-a-real-name") is None


class TestParseInstrument:
    """Map Deribit `/public/get_instruments` rows to `Instrument`s."""

    def test_perpetual(self) -> None:
        raw = {
            "instrument_name": "BTC-PERPETUAL",
            "base_currency": "BTC",
            "kind": "future",
            "settlement_period": "perpetual",
            "is_active": True,
            "expiration_timestamp": 32503680000000,
            "strike": None,
        }
        inst = parse_instrument(raw)
        assert inst is not None
        assert inst.venue == Venue.DERIBIT
        assert inst.symbol == "BTC-PERPETUAL"
        assert inst.currency == Currency.BTC
        assert inst.asset_kind == AssetKind.PERPETUAL
        assert inst.expiry is None
        assert inst.is_active is True

    def test_future(self) -> None:
        expiry = datetime(2026, 6, 26, 8, 0, tzinfo=UTC)
        raw = {
            "instrument_name": "BTC-26JUN26",
            "base_currency": "BTC",
            "kind": "future",
            "settlement_period": "month",
            "is_active": True,
            "expiration_timestamp": int(expiry.timestamp() * 1000),
            "strike": None,
        }
        inst = parse_instrument(raw)
        assert inst is not None
        assert inst.asset_kind == AssetKind.FUTURE
        assert inst.expiry == datetime(2026, 6, 26, 8, 0, tzinfo=UTC)
        assert inst.strike is None

    def test_option(self) -> None:
        expiry = datetime(2026, 5, 30, 8, 0, tzinfo=UTC)
        raw = {
            "instrument_name": "ETH-30MAY26-3000-P",
            "base_currency": "ETH",
            "kind": "option",
            "settlement_period": "week",
            "is_active": True,
            "expiration_timestamp": int(expiry.timestamp() * 1000),
            "strike": 3000.0,
        }
        inst = parse_instrument(raw)
        assert inst is not None
        assert inst.currency == Currency.ETH
        assert inst.asset_kind == AssetKind.OPTION
        assert inst.strike == 3000.0
        assert inst.expiry == datetime(2026, 5, 30, 8, 0, tzinfo=UTC)

    def test_unsupported_currency_skipped(self) -> None:
        raw = {
            "instrument_name": "SOL-PERPETUAL",
            "base_currency": "SOL",
            "kind": "future",
            "settlement_period": "perpetual",
            "is_active": True,
            "expiration_timestamp": 32503680000000,
            "strike": None,
        }
        assert parse_instrument(raw) is None


class TestParseTicker:
    """Map Deribit ticker payloads to `TickerSnapshot`s."""

    def test_option(self) -> None:
        raw = {
            "instrument_name": "BTC-26JUN26-100000-C",
            "timestamp": int(datetime(2026, 4, 30, tzinfo=UTC).timestamp() * 1000),
            "mark_price": 0.05,
            "best_bid_price": 0.0498,
            "best_ask_price": 0.0502,
            "mark_iv": 65.5,  # percent, per Deribit
            "open_interest": 1234.5,
        }
        snap = parse_ticker(raw)
        assert snap.venue == Venue.DERIBIT
        assert snap.symbol == "BTC-26JUN26-100000-C"
        assert snap.currency == Currency.BTC
        assert snap.asset_kind == AssetKind.OPTION
        assert snap.timestamp == datetime(2026, 4, 30, tzinfo=UTC)
        assert snap.mark_price == 0.05
        assert snap.bid == 0.0498
        assert snap.ask == 0.0502
        # mark_iv is converted from percent to decimal.
        assert snap.mark_iv is not None
        assert abs(snap.mark_iv - 0.655) < 1e-9
        assert snap.open_interest == 1234.5
        assert snap.funding_rate is None

    def test_perpetual(self) -> None:
        raw = {
            "instrument_name": "BTC-PERPETUAL",
            "timestamp": int(datetime(2026, 4, 30, tzinfo=UTC).timestamp() * 1000),
            "mark_price": 95000.0,
            "best_bid_price": 94999.5,
            "best_ask_price": 95000.5,
            "open_interest": 50000.0,
            "funding_8h": 0.00012,
        }
        snap = parse_ticker(raw)
        assert snap.asset_kind == AssetKind.PERPETUAL
        assert snap.funding_rate == 0.00012
        assert snap.mark_iv is None

    def test_future(self) -> None:
        raw = {
            "instrument_name": "BTC-26JUN26",
            "timestamp": int(datetime(2026, 4, 30, tzinfo=UTC).timestamp() * 1000),
            "mark_price": 96000.0,
            "best_bid_price": 95999.0,
            "best_ask_price": 96001.0,
            "open_interest": 12345.0,
        }
        snap = parse_ticker(raw)
        assert snap.asset_kind == AssetKind.FUTURE
        assert snap.funding_rate is None
        assert snap.mark_iv is None
