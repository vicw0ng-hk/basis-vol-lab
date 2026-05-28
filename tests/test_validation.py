"""Tests for `basis_analytics.validation`."""

from __future__ import annotations

from datetime import UTC, datetime

from basis_analytics import (
    black76_price,
    summarize_by_tenor,
    validate_iv,
)
from basis_contracts import AssetKind, Currency, TickerSnapshot, Venue


def _make_option_snapshot(
    strike: float,
    expiry: datetime,
    mark_iv: float,
    F: float,
    asof: datetime,
    *,
    is_call: bool,
) -> TickerSnapshot:
    T = (expiry - asof).total_seconds() / (365 * 86400)
    usd_price = float(black76_price(F, strike, T, mark_iv, is_call=is_call))
    suffix = "C" if is_call else "P"
    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=f"BTC-30JUN25-{int(strike)}-{suffix}",
        currency=Currency.BTC,
        asset_kind=AssetKind.OPTION,
        timestamp=asof,
        mark_price=usd_price / F,  # coin-denominated premium, Deribit convention
        mark_iv=mark_iv,
        expiry=expiry,
        strike=strike,
    )


def test_validate_iv_round_trip() -> None:
    expiry = datetime(2025, 6, 30, 8, tzinfo=UTC)
    asof = datetime(2025, 1, 1, tzinfo=UTC)
    F = 70_000.0
    snap = _make_option_snapshot(70_000.0, expiry, 0.60, F, asof, is_call=True)

    errors = validate_iv([snap], {expiry: F}, asof=asof)
    assert len(errors) == 1
    assert abs(float(errors["our_iv"].iloc[0]) - 0.60) < 1e-6
    assert float(errors["abs_err"].iloc[0]) < 1e-6


def test_validate_iv_skips_non_options() -> None:
    perp = TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol="BTC-PERPETUAL",
        currency=Currency.BTC,
        asset_kind=AssetKind.PERPETUAL,
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        mark_price=70_000.0,
    )
    out = validate_iv([perp], {}, asof=datetime(2025, 1, 1, tzinfo=UTC))
    assert out.empty


def test_summarize_by_tenor_aggregates() -> None:
    expiry = datetime(2025, 6, 30, 8, tzinfo=UTC)
    asof = datetime(2025, 1, 1, tzinfo=UTC)
    F = 70_000.0
    snaps = [
        _make_option_snapshot(70_000.0, expiry, 0.60, F, asof, is_call=True),
        _make_option_snapshot(75_000.0, expiry, 0.65, F, asof, is_call=True),
    ]
    errors = validate_iv(snaps, {expiry: F}, asof=asof)
    summary = summarize_by_tenor(errors)
    assert len(summary) == 1
    assert int(summary["count"].iloc[0]) == 2
    assert float(summary["max_abs_err"].iloc[0]) < 1e-6
