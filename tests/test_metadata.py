"""Tests for MetadataStore (SQLite metadata layer)."""

from datetime import UTC, datetime

from basis_contracts import AssetKind, CollectionRun, Currency, Instrument, Venue
from basis_persistence import MetadataStore


class TestInstruments:
    """Tests for instrument CRUD."""

    def test_upsert_and_query(self) -> None:
        store = MetadataStore(":memory:")
        inst = Instrument(
            venue=Venue.DERIBIT,
            symbol="BTC-PERPETUAL",
            currency=Currency.BTC,
            asset_kind=AssetKind.PERPETUAL,
        )
        store.upsert_instrument(inst)
        results = store.get_instruments()
        assert len(results) == 1
        assert results[0].symbol == "BTC-PERPETUAL"
        assert results[0].venue == Venue.DERIBIT
        store.close()

    def test_upsert_overwrites(self) -> None:
        store = MetadataStore(":memory:")
        inst = Instrument(
            venue=Venue.DERIBIT,
            symbol="BTC-PERPETUAL",
            currency=Currency.BTC,
            asset_kind=AssetKind.PERPETUAL,
            is_active=True,
        )
        store.upsert_instrument(inst)

        updated = Instrument(
            venue=Venue.DERIBIT,
            symbol="BTC-PERPETUAL",
            currency=Currency.BTC,
            asset_kind=AssetKind.PERPETUAL,
            is_active=False,
        )
        store.upsert_instrument(updated)

        results = store.get_instruments(active_only=False)
        assert len(results) == 1
        assert results[0].is_active is False
        store.close()

    def test_filter_by_venue(self) -> None:
        store = MetadataStore(":memory:")
        store.upsert_instrument(
            Instrument(
                venue=Venue.DERIBIT,
                symbol="BTC-PERPETUAL",
                currency=Currency.BTC,
                asset_kind=AssetKind.PERPETUAL,
            )
        )
        store.upsert_instrument(
            Instrument(
                venue=Venue.BINANCE,
                symbol="BTCUSDT",
                currency=Currency.BTC,
                asset_kind=AssetKind.PERPETUAL,
            )
        )

        deribit = store.get_instruments(venue=Venue.DERIBIT)
        assert len(deribit) == 1
        assert deribit[0].venue == Venue.DERIBIT

        binance = store.get_instruments(venue=Venue.BINANCE)
        assert len(binance) == 1
        assert binance[0].venue == Venue.BINANCE
        store.close()

    def test_filter_by_currency_and_kind(self) -> None:
        store = MetadataStore(":memory:")
        store.upsert_instrument(
            Instrument(
                venue=Venue.DERIBIT,
                symbol="BTC-PERPETUAL",
                currency=Currency.BTC,
                asset_kind=AssetKind.PERPETUAL,
            )
        )
        store.upsert_instrument(
            Instrument(
                venue=Venue.DERIBIT,
                symbol="ETH-28JUN26-4000-C",
                currency=Currency.ETH,
                asset_kind=AssetKind.OPTION,
                expiry=datetime(2026, 6, 28, tzinfo=UTC),
                strike=4000.0,
            )
        )

        eth_options = store.get_instruments(
            currency=Currency.ETH, asset_kind=AssetKind.OPTION
        )
        assert len(eth_options) == 1
        assert eth_options[0].symbol == "ETH-28JUN26-4000-C"
        assert eth_options[0].strike == 4000.0
        store.close()

    def test_active_filter(self) -> None:
        store = MetadataStore(":memory:")
        store.upsert_instrument(
            Instrument(
                venue=Venue.DERIBIT,
                symbol="BTC-PERPETUAL",
                currency=Currency.BTC,
                asset_kind=AssetKind.PERPETUAL,
                is_active=True,
            )
        )
        store.upsert_instrument(
            Instrument(
                venue=Venue.DERIBIT,
                symbol="BTC-EXPIRED",
                currency=Currency.BTC,
                asset_kind=AssetKind.FUTURE,
                is_active=False,
            )
        )

        active = store.get_instruments(active_only=True)
        assert len(active) == 1
        all_insts = store.get_instruments(active_only=False)
        assert len(all_insts) == 2
        store.close()


class TestCollectionRuns:
    """Tests for collection run tracking."""

    def test_insert_and_finish(self) -> None:
        store = MetadataStore(":memory:")
        run = CollectionRun(
            run_id="run-001",
            venue=Venue.DERIBIT,
            started_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        )
        store.insert_run(run)

        runs = store.get_runs()
        assert len(runs) == 1
        assert runs[0].status == "running"
        assert runs[0].ended_at is None

        store.finish_run(
            "run-001",
            ended_at=datetime(2026, 4, 30, 12, 5, tzinfo=UTC),
            status="completed",
            records_collected=150,
        )

        runs = store.get_runs()
        assert runs[0].status == "completed"
        assert runs[0].records_collected == 150
        assert runs[0].ended_at is not None
        store.close()

    def test_filter_runs_by_venue(self) -> None:
        store = MetadataStore(":memory:")
        store.insert_run(
            CollectionRun(
                run_id="run-d",
                venue=Venue.DERIBIT,
                started_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            )
        )
        store.insert_run(
            CollectionRun(
                run_id="run-b",
                venue=Venue.BINANCE,
                started_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            )
        )

        deribit_runs = store.get_runs(venue=Venue.DERIBIT)
        assert len(deribit_runs) == 1
        assert deribit_runs[0].run_id == "run-d"
        store.close()
