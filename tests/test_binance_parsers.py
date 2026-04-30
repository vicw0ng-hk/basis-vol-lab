"""Tests for Binance parsers (pure functions, no network)."""

from datetime import UTC, datetime

from basis_connectors.binance import (
    BasisRow,
    FundingRateRow,
    OpenInterestRow,
    parse_basis_row,
    parse_exchange_info_symbol,
    parse_funding_rate_row,
    parse_mark_price_event,
    parse_oi_row,
)
from basis_contracts import AssetKind, Currency, Venue


class TestParseExchangeInfoSymbol:
    def test_perpetual(self) -> None:
        raw = {
            "symbol": "BTCUSDT",
            "pair": "BTCUSDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "deliveryDate": 4133404800000,
        }
        inst = parse_exchange_info_symbol(raw)
        assert inst is not None
        assert inst.venue == Venue.BINANCE
        assert inst.symbol == "BTCUSDT"
        assert inst.currency == Currency.BTC
        assert inst.asset_kind == AssetKind.PERPETUAL
        assert inst.expiry is None
        assert inst.is_active is True

    def test_quarterly_future(self) -> None:
        delivery = datetime(2026, 6, 26, 8, 0, tzinfo=UTC)
        raw = {
            "symbol": "BTCUSDT_260626",
            "pair": "BTCUSDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "contractType": "CURRENT_QUARTER",
            "status": "TRADING",
            "deliveryDate": int(delivery.timestamp() * 1000),
        }
        inst = parse_exchange_info_symbol(raw)
        assert inst is not None
        assert inst.asset_kind == AssetKind.FUTURE
        assert inst.expiry == delivery
        assert inst.symbol == "BTCUSDT_260626"

    def test_eth_perpetual(self) -> None:
        raw = {
            "symbol": "ETHUSDT",
            "pair": "ETHUSDT",
            "baseAsset": "ETH",
            "quoteAsset": "USDT",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "deliveryDate": 4133404800000,
        }
        inst = parse_exchange_info_symbol(raw)
        assert inst is not None
        assert inst.currency == Currency.ETH

    def test_unsupported_currency_skipped(self) -> None:
        raw = {
            "symbol": "SOLUSDT",
            "pair": "SOLUSDT",
            "baseAsset": "SOL",
            "quoteAsset": "USDT",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "deliveryDate": 4133404800000,
        }
        assert parse_exchange_info_symbol(raw) is None

    def test_unsupported_quote_skipped(self) -> None:
        raw = {
            "symbol": "BTCBUSD",
            "pair": "BTCBUSD",
            "baseAsset": "BTC",
            "quoteAsset": "BUSD",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "deliveryDate": 4133404800000,
        }
        assert parse_exchange_info_symbol(raw) is None

    def test_halted_marks_inactive(self) -> None:
        raw = {
            "symbol": "BTCUSDT",
            "pair": "BTCUSDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "contractType": "PERPETUAL",
            "status": "HALT",
            "deliveryDate": 4133404800000,
        }
        inst = parse_exchange_info_symbol(raw)
        assert inst is not None
        assert inst.is_active is False


class TestParseMarkPriceEvent:
    def test_perpetual(self) -> None:
        ts = datetime(2026, 4, 30, tzinfo=UTC)
        raw = {
            "e": "markPriceUpdate",
            "E": int(ts.timestamp() * 1000),
            "s": "BTCUSDT",
            "p": "76500.00",
            "i": "76498.50",
            "P": "0.00",
            "r": "0.00012000",
            "T": 1745988000000,
        }
        snap = parse_mark_price_event(raw)
        assert snap is not None
        assert snap.venue == Venue.BINANCE
        assert snap.symbol == "BTCUSDT"
        assert snap.currency == Currency.BTC
        assert snap.asset_kind == AssetKind.PERPETUAL
        assert snap.timestamp == ts
        assert snap.mark_price == 76500.0
        assert snap.funding_rate == 0.00012

    def test_future_no_funding(self) -> None:
        ts = datetime(2026, 4, 30, tzinfo=UTC)
        raw = {
            "e": "markPriceUpdate",
            "E": int(ts.timestamp() * 1000),
            "s": "BTCUSDT_260626",
            "p": "76600.00",
            "i": "76498.50",
            "P": "76600.00",
            "r": "",
            "T": 0,
        }
        snap = parse_mark_price_event(raw)
        assert snap is not None
        assert snap.asset_kind == AssetKind.FUTURE
        assert snap.funding_rate is None

    def test_unsupported_symbol_skipped(self) -> None:
        raw = {
            "e": "markPriceUpdate",
            "E": 1745971200000,
            "s": "SOLUSDT",
            "p": "150.00",
            "i": "149.5",
            "P": "0",
            "r": "0.0001",
            "T": 1745988000000,
        }
        assert parse_mark_price_event(raw) is None


class TestParseFundingRateRow:
    def test_basic(self) -> None:
        ts = datetime(2026, 4, 30, tzinfo=UTC)
        raw = {
            "symbol": "BTCUSDT",
            "fundingTime": int(ts.timestamp() * 1000),
            "fundingRate": "0.00010000",
            "markPrice": "76500.00",
        }
        row = parse_funding_rate_row(raw)
        assert row == FundingRateRow(
            symbol="BTCUSDT",
            funding_time=ts,
            funding_rate=0.0001,
            mark_price=76500.0,
        )


class TestParseBasisRow:
    def test_basic(self) -> None:
        ts = datetime(2026, 4, 30, tzinfo=UTC)
        raw = {
            "pair": "BTCUSDT",
            "contractType": "PERPETUAL",
            "futuresPrice": "76600.00",
            "indexPrice": "76500.00",
            "basis": "100.0",
            "basisRate": "0.0013",
            "timestamp": int(ts.timestamp() * 1000),
        }
        row = parse_basis_row(raw)
        assert row == BasisRow(
            pair="BTCUSDT",
            contract_type="PERPETUAL",
            timestamp=ts,
            basis=100.0,
            basis_rate=0.0013,
            futures_price=76600.0,
            index_price=76500.0,
        )


class TestParseOpenInterestRow:
    def test_basic(self) -> None:
        ts = datetime(2026, 4, 30, tzinfo=UTC)
        raw = {
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100000.123",
            "sumOpenInterestValue": "7650000000.0",
            "timestamp": int(ts.timestamp() * 1000),
        }
        row = parse_oi_row(raw)
        assert row == OpenInterestRow(
            symbol="BTCUSDT",
            timestamp=ts,
            sum_open_interest=100000.123,
            sum_open_interest_value=7650000000.0,
        )
