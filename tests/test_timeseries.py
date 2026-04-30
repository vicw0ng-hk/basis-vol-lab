"""Tests for TimeSeriesStore (Parquet time-series layer)."""

from datetime import UTC, datetime
from pathlib import Path

from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue
from basis_persistence import TimeSeriesStore


def _make_snapshot(
    ts: datetime,
    venue: Venue = Venue.DERIBIT,
    symbol: str = "BTC-PERPETUAL",
    price: float = 95000.0,
) -> TickerSnapshot:
    return TickerSnapshot(
        venue=venue,
        symbol=symbol,
        currency=Currency.BTC,
        asset_kind=AssetKind.PERPETUAL,
        timestamp=ts,
        mark_price=price,
    )


class TestWriteAndRead:
    """Tests for basic write/read roundtrip."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        ts = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
        snapshots = [_make_snapshot(ts)]

        written = store.write_snapshots(snapshots)
        assert len(written) == 1
        assert written[0].exists()

        result = store.read_snapshots(Venue.DERIBIT, "2026-04-30")
        assert len(result) == 1
        assert result[0].mark_price == 95000.0
        assert result[0].venue == Venue.DERIBIT
        assert result[0].timestamp == ts

    def test_empty_write(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        written = store.write_snapshots([])
        assert written == []

    def test_read_missing_date(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        result = store.read_snapshots(Venue.DERIBIT, "2026-01-01")
        assert result == []

    def test_append_to_existing(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        ts1 = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
        ts2 = datetime(2026, 4, 30, 13, 0, tzinfo=UTC)

        store.write_snapshots([_make_snapshot(ts1)])
        store.write_snapshots([_make_snapshot(ts2, price=96000.0)])

        result = store.read_snapshots(Venue.DERIBIT, "2026-04-30")
        assert len(result) == 2
        prices = {s.mark_price for s in result}
        assert prices == {95000.0, 96000.0}

    def test_optional_fields_roundtrip(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        ts = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
        snap = TickerSnapshot(
            venue=Venue.DERIBIT,
            symbol="BTC-PERPETUAL",
            currency=Currency.BTC,
            asset_kind=AssetKind.PERPETUAL,
            timestamp=ts,
            mark_price=95000.0,
            bid=94990.0,
            ask=95010.0,
            mark_iv=0.65,
            open_interest=50000.0,
            funding_rate=0.0001,
        )
        store.write_snapshots([snap])

        result = store.read_snapshots(Venue.DERIBIT, "2026-04-30")
        assert len(result) == 1
        r = result[0]
        assert r.bid == 94990.0
        assert r.ask == 95010.0
        assert r.mark_iv == 0.65
        assert r.open_interest == 50000.0
        assert r.funding_rate == 0.0001


class TestPartitioning:
    """Tests for venue/date partitioning."""

    def test_multi_venue_partitioning(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        ts = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)

        store.write_snapshots(
            [
                _make_snapshot(ts, venue=Venue.DERIBIT),
                _make_snapshot(ts, venue=Venue.BINANCE, symbol="BTCUSDT"),
            ]
        )

        deribit = store.read_snapshots(Venue.DERIBIT, "2026-04-30")
        binance = store.read_snapshots(Venue.BINANCE, "2026-04-30")
        assert len(deribit) == 1
        assert len(binance) == 1
        assert deribit[0].venue == Venue.DERIBIT
        assert binance[0].venue == Venue.BINANCE

    def test_multi_date_partitioning(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        day1 = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
        day2 = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)

        store.write_snapshots([_make_snapshot(day1), _make_snapshot(day2)])

        r1 = store.read_snapshots(Venue.DERIBIT, "2026-04-29")
        r2 = store.read_snapshots(Venue.DERIBIT, "2026-04-30")
        assert len(r1) == 1
        assert len(r2) == 1

    def test_list_dates(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        store.write_snapshots(
            [
                _make_snapshot(datetime(2026, 4, 28, 12, 0, tzinfo=UTC)),
                _make_snapshot(datetime(2026, 4, 30, 12, 0, tzinfo=UTC)),
            ]
        )

        dates = store.list_dates(Venue.DERIBIT)
        assert dates == ["2026-04-28", "2026-04-30"]

    def test_list_dates_empty(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        assert store.list_dates(Venue.DERIBIT) == []

    def test_read_date_range(self, tmp_path: Path) -> None:
        store = TimeSeriesStore(tmp_path)
        for day in [28, 29, 30]:
            store.write_snapshots(
                [_make_snapshot(datetime(2026, 4, day, 12, 0, tzinfo=UTC))]
            )

        result = store.read_date_range(
            Venue.DERIBIT,
            start=datetime(2026, 4, 28, tzinfo=UTC),
            end=datetime(2026, 4, 29, tzinfo=UTC),
        )
        assert len(result) == 2
