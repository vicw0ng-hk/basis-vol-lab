"""Tests for the FastAPI endpoints in basis_api.main."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from basis_api.storage import InMemoryArtifactStore
from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue
from basis_persistence import TimeSeriesStore
from fastapi.testclient import TestClient


@pytest.fixture
def mem_store() -> InMemoryArtifactStore:
    return InMemoryArtifactStore()


@pytest.fixture
def client(mem_store: InMemoryArtifactStore) -> Generator[TestClient]:
    """TestClient with an in-memory artifact store."""
    with (
        patch("basis_api.main._store", mem_store),
        patch("basis_api.main._meta_store", None),
    ):
        from basis_api.main import app

        yield TestClient(app, raise_server_exceptions=False)


def _seed_artifacts(store: InMemoryArtifactStore) -> None:
    """Write minimal valid artifacts to the store."""
    store.write_json(
        "meta.json",
        {
            "generated_at": "2026-05-31T12:00:00+00:00",
            "deribit_options": 200,
            "deribit_futures": 10,
            "binance_symbols": ["BTCUSDT"],
            "binance_funding_rows": 50,
        },
    )
    store.write_json("overview.json", {"venues": {}})
    store.write_json("vol.json", {"by_currency": {}})
    store.write_json("carry.json", {"cards": {}})
    store.write_json("signals.json", {"as_of_snapshot": True, "summary": []})


def _perp(ts: datetime) -> TickerSnapshot:
    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol="BTC-PERPETUAL",
        currency=Currency.BTC,
        asset_kind=AssetKind.PERPETUAL,
        timestamp=ts,
        mark_price=94_500.0,
        open_interest=10_000.0,
    )


# ---------------------------------------------------------------------------
# Healthz
# ---------------------------------------------------------------------------


class TestHealthz:
    def test_healthz(self, client: TestClient) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Artifact endpoints (meta, overview, vol, carry, signals)
# ---------------------------------------------------------------------------


class TestArtifactEndpoints:
    def test_meta_missing_returns_503(self, client: TestClient) -> None:
        r = client.get("/api/meta")
        assert r.status_code == 503

    def test_meta_returns_artifact(
        self, client: TestClient, mem_store: InMemoryArtifactStore
    ) -> None:
        _seed_artifacts(mem_store)
        r = client.get("/api/meta")
        assert r.status_code == 200
        data = r.json()
        assert data["deribit_options"] == 200

    def test_overview_returns_artifact(
        self, client: TestClient, mem_store: InMemoryArtifactStore
    ) -> None:
        _seed_artifacts(mem_store)
        r = client.get("/api/overview")
        assert r.status_code == 200
        assert "venues" in r.json()

    def test_vol_returns_artifact(
        self, client: TestClient, mem_store: InMemoryArtifactStore
    ) -> None:
        _seed_artifacts(mem_store)
        r = client.get("/api/vol")
        assert r.status_code == 200
        assert "by_currency" in r.json()

    def test_carry_returns_artifact(
        self, client: TestClient, mem_store: InMemoryArtifactStore
    ) -> None:
        _seed_artifacts(mem_store)
        r = client.get("/api/carry")
        assert r.status_code == 200
        assert "cards" in r.json()

    def test_signals_returns_artifact(
        self, client: TestClient, mem_store: InMemoryArtifactStore
    ) -> None:
        _seed_artifacts(mem_store)
        r = client.get("/api/signals")
        assert r.status_code == 200
        assert "summary" in r.json()


# ---------------------------------------------------------------------------
# Runs endpoint
# ---------------------------------------------------------------------------


class TestRunsEndpoint:
    def test_runs_no_meta_store(self, client: TestClient) -> None:
        r = client.get("/api/runs")
        assert r.status_code == 200
        data = r.json()
        assert data["runs"] == []
        assert "note" in data


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------


class TestHistoryDatesEndpoint:
    def test_returns_dates(
        self, tmp_path: Path, mem_store: InMemoryArtifactStore
    ) -> None:
        from basis_api.storage import LocalArtifactStore

        ts = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        ts_store = TimeSeriesStore(tmp_path / "parquet")
        ts_store.write_snapshots([_perp(ts)])
        local_store = LocalArtifactStore(tmp_path)

        with (
            patch("basis_api.main._store", local_store),
            patch("basis_api.main._meta_store", None),
        ):
            from basis_api.main import app

            client = TestClient(app)
            r = client.get("/api/history/dates")

        assert r.status_code == 200
        assert "2026-05-15" in r.json()["dates"]

    def test_empty_store(
        self, tmp_path: Path, mem_store: InMemoryArtifactStore
    ) -> None:
        from basis_api.storage import LocalArtifactStore

        local_store = LocalArtifactStore(tmp_path)

        with (
            patch("basis_api.main._store", local_store),
            patch("basis_api.main._meta_store", None),
        ):
            from basis_api.main import app

            client = TestClient(app)
            r = client.get("/api/history/dates")

        assert r.status_code == 200
        assert r.json()["dates"] == []


class TestHistorySnapshotEndpoint:
    def test_invalid_date_format(self, client: TestClient) -> None:
        r = client.get("/api/history/not-a-date")
        assert r.status_code == 400

    def test_missing_date_returns_404(
        self, tmp_path: Path, mem_store: InMemoryArtifactStore
    ) -> None:
        from basis_api.storage import LocalArtifactStore

        local_store = LocalArtifactStore(tmp_path)

        with (
            patch("basis_api.main._store", local_store),
            patch("basis_api.main._meta_store", None),
        ):
            from basis_api.main import app

            client = TestClient(app)
            r = client.get("/api/history/2026-01-01")

        assert r.status_code == 404

    def test_valid_date_returns_summary(
        self, tmp_path: Path, mem_store: InMemoryArtifactStore
    ) -> None:
        from basis_api.storage import LocalArtifactStore

        ts = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        ts_store = TimeSeriesStore(tmp_path / "parquet")
        ts_store.write_snapshots([_perp(ts)])
        local_store = LocalArtifactStore(tmp_path)

        with (
            patch("basis_api.main._store", local_store),
            patch("basis_api.main._meta_store", None),
        ):
            from basis_api.main import app

            client = TestClient(app)
            r = client.get("/api/history/2026-05-15")

        assert r.status_code == 200
        data = r.json()
        assert data["date"] == "2026-05-15"
        assert data["future_count"] == 1
        assert data["empty"] is False
