"""Tests for the history module (Parquet replay summaries and diffs)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from basis_api.history import (
    _build_date_summary,
    _safe_pct_change,
    build_diff,
    get_history_dates,
    get_history_snapshot,
)
from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue
from basis_persistence import TimeSeriesStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _option(
    ts: datetime,
    *,
    currency: Currency = Currency.BTC,
    strike: float = 100_000.0,
    mark_iv: float = 0.65,
    expiry: datetime | None = None,
) -> TickerSnapshot:
    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=f"{currency.value}-{strike:.0f}-C",
        currency=currency,
        asset_kind=AssetKind.OPTION,
        timestamp=ts,
        mark_price=0.05,
        mark_iv=mark_iv,
        strike=strike,
        expiry=expiry or datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        open_interest=100.0,
    )


def _future(
    ts: datetime,
    *,
    currency: Currency = Currency.BTC,
    mark_price: float = 95_000.0,
    expiry: datetime | None = None,
    oi: float = 5000.0,
) -> TickerSnapshot:
    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=f"{currency.value}-FUTURE",
        currency=currency,
        asset_kind=AssetKind.FUTURE,
        timestamp=ts,
        mark_price=mark_price,
        expiry=expiry or datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        open_interest=oi,
    )


def _perp(
    ts: datetime,
    *,
    currency: Currency = Currency.BTC,
    mark_price: float = 94_500.0,
    oi: float = 10_000.0,
) -> TickerSnapshot:
    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=f"{currency.value}-PERPETUAL",
        currency=currency,
        asset_kind=AssetKind.PERPETUAL,
        timestamp=ts,
        mark_price=mark_price,
        open_interest=oi,
    )


def _seed_store(tmp_path: Path, day: int, snaps: list[TickerSnapshot]) -> None:
    """Write snapshots to a TimeSeriesStore under tmp_path/parquet."""
    ts_store = TimeSeriesStore(tmp_path / "parquet")
    ts_store.write_snapshots(snaps)


# ---------------------------------------------------------------------------
# _safe_pct_change
# ---------------------------------------------------------------------------


class TestSafePctChange:
    def test_normal(self) -> None:
        assert _safe_pct_change(110.0, 100.0) == pytest.approx(0.1)

    def test_negative(self) -> None:
        assert _safe_pct_change(90.0, 100.0) == pytest.approx(-0.1)

    def test_none_inputs(self) -> None:
        assert _safe_pct_change(None, 100.0) is None
        assert _safe_pct_change(100.0, None) is None
        assert _safe_pct_change(None, None) is None

    def test_nan_inputs(self) -> None:
        assert _safe_pct_change(float("nan"), 100.0) is None
        assert _safe_pct_change(100.0, float("nan")) is None

    def test_zero_denominator(self) -> None:
        assert _safe_pct_change(100.0, 0.0) is None


# ---------------------------------------------------------------------------
# _build_date_summary
# ---------------------------------------------------------------------------


class TestBuildDateSummary:
    def test_futures_only(self) -> None:
        ts = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        snaps = [_future(ts, oi=5000.0), _perp(ts, oi=10_000.0)]
        result = _build_date_summary(snaps, "2026-05-15")

        assert result["date"] == "2026-05-15"
        assert result["option_count"] == 0
        assert result["future_count"] == 2
        assert result["total_open_interest"] == 15_000.0
        assert result["atm_term_structure"] == {}
        assert result["avg_atm_iv"] == {}

    def test_with_options_and_futures(self) -> None:
        ts = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        expiry = datetime(2026, 6, 27, 8, 0, tzinfo=UTC)
        snaps = [
            _future(ts, mark_price=95_000.0, expiry=expiry),
            _option(ts, strike=95_000.0, mark_iv=0.60, expiry=expiry),
            _option(ts, strike=100_000.0, mark_iv=0.70, expiry=expiry),
        ]
        result = _build_date_summary(snaps, "2026-05-15")

        assert result["option_count"] == 2
        assert result["future_count"] == 1
        assert "BTC" in result["atm_term_structure"]
        assert "BTC" in result["avg_atm_iv"]
        assert result["avg_atm_iv"]["BTC"] is not None

    def test_empty_snapshots(self) -> None:
        result = _build_date_summary([], "2026-05-15")
        assert result["option_count"] == 0
        assert result["future_count"] == 0
        assert result["timestamp"] is None

    def test_timestamp_from_first_snapshot(self) -> None:
        ts = datetime(2026, 5, 15, 14, 30, tzinfo=UTC)
        snaps = [_perp(ts)]
        result = _build_date_summary(snaps, "2026-05-15")
        assert result["timestamp"] == ts.isoformat()


# ---------------------------------------------------------------------------
# build_diff
# ---------------------------------------------------------------------------


class TestBuildDiff:
    def test_basic_diff(self) -> None:
        current = {
            "date": "2026-05-16",
            "option_count": 250,
            "future_count": 12,
            "total_open_interest": 15_000.0,
            "avg_atm_iv": {"BTC": 0.65},
        }
        previous = {
            "date": "2026-05-15",
            "option_count": 240,
            "future_count": 12,
            "total_open_interest": 14_000.0,
            "avg_atm_iv": {"BTC": 0.60},
        }
        diff = build_diff(current, previous)

        assert diff["previous_date"] == "2026-05-15"
        assert diff["option_count_delta"] == 10
        assert diff["future_count_delta"] == 0
        assert diff["oi_change"] == pytest.approx(1000.0 / 14_000.0)
        assert diff["atm_iv_changes"]["BTC"]["delta"] == pytest.approx(0.05)

    def test_missing_currency_in_one_side(self) -> None:
        current = {
            "date": "d2",
            "option_count": 5,
            "future_count": 2,
            "total_open_interest": 100,
            "avg_atm_iv": {"ETH": 0.7},
        }
        previous = {
            "date": "d1",
            "option_count": 5,
            "future_count": 2,
            "total_open_interest": 100,
            "avg_atm_iv": {"BTC": 0.5},
        }
        diff = build_diff(current, previous)

        assert diff["atm_iv_changes"]["ETH"]["delta"] is None
        assert diff["atm_iv_changes"]["BTC"]["delta"] is None


# ---------------------------------------------------------------------------
# get_history_dates / get_history_snapshot
# ---------------------------------------------------------------------------


class TestGetHistoryDates:
    def test_lists_dates(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        ts1 = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        ts2 = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        _seed_store(tmp_path, 14, [_perp(ts1)])
        _seed_store(tmp_path, 15, [_perp(ts2)])

        store = LocalArtifactStore(tmp_path)
        dates = get_history_dates(store)
        assert dates == ["2026-05-14", "2026-05-15"]

    def test_empty_store(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        store = LocalArtifactStore(tmp_path)
        assert get_history_dates(store) == []


class TestGetHistorySnapshot:
    def test_empty_date(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        store = LocalArtifactStore(tmp_path)
        result = get_history_snapshot(store, "2026-01-01")
        assert result["empty"] is True

    def test_returns_summary(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        ts = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        _seed_store(tmp_path, 15, [_perp(ts), _future(ts)])

        store = LocalArtifactStore(tmp_path)
        result = get_history_snapshot(store, "2026-05-15")
        assert result["empty"] is False
        assert result["date"] == "2026-05-15"
        assert result["future_count"] == 2
        assert result["diff"] is None  # no previous date

    def test_includes_diff_when_previous_exists(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        ts1 = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        ts2 = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        _seed_store(tmp_path, 14, [_perp(ts1, oi=8000.0)])
        _seed_store(tmp_path, 15, [_perp(ts2, oi=10_000.0)])

        store = LocalArtifactStore(tmp_path)
        result = get_history_snapshot(store, "2026-05-15")
        assert result["diff"] is not None
        assert result["diff"]["previous_date"] == "2026-05-14"

    def test_first_date_has_no_diff(self, tmp_path: Path) -> None:
        from basis_api.storage import LocalArtifactStore

        ts = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        _seed_store(tmp_path, 14, [_perp(ts)])

        store = LocalArtifactStore(tmp_path)
        result = get_history_snapshot(store, "2026-05-14")
        assert result["diff"] is None
