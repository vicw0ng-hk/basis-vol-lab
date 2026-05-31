"""Tests for `basis_analytics.signals`."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from basis_analytics import (
    carry_vol_divergence,
    percentile_rank,
    regime_change_alert,
    rolling_signals,
    skew_stress,
)


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")


def test_percentile_rank_at_extremes() -> None:
    n = 100
    s = pd.Series(np.arange(n, dtype=float), index=_idx(n))
    pct = percentile_rank(s, window="365D")
    # First valid value is the rank at position 0 → 1.0 (it's the only point so far)
    assert math.isclose(float(pct.iloc[0]), 1.0)
    # Last value: max in the window → 1.0
    assert math.isclose(float(pct.iloc[-1]), 1.0)


def test_percentile_rank_constant_series() -> None:
    s = pd.Series([5.0] * 30, index=_idx(30))
    pct = percentile_rank(s, window="30D")
    # Every observation equals the running max → all 1.0 (since "<=" includes self)
    assert (pct == 1.0).all()


def test_carry_vol_divergence_sign() -> None:
    idx = _idx(3)
    cp = pd.Series([0.9, 0.5, 0.1], index=idx)
    iv_rv = pd.Series([0.1, 0.5, 0.9], index=idx)
    out = carry_vol_divergence(cp, iv_rv)
    assert float(out.iloc[0]) > 0  # carry rich
    assert float(out.iloc[1]) == 0  # neutral
    assert float(out.iloc[2]) < 0  # carry cheap


def test_skew_stress_average() -> None:
    idx = _idx(2)
    rr = pd.Series([0.8, 0.2], index=idx)
    oi = pd.Series([0.6, 0.4], index=idx)
    out = skew_stress(rr, oi)
    assert math.isclose(float(out.iloc[0]), 0.7)
    assert math.isclose(float(out.iloc[1]), 0.3)


def test_regime_change_alert_threshold() -> None:
    idx = _idx(3)
    c = pd.Series([0.9, 0.9, 0.5], index=idx)
    s = pd.Series([0.85, 0.7, 0.9], index=idx)
    o = pd.Series([0.95, 0.95, 0.95], index=idx)
    fired = regime_change_alert(c, s, o, threshold=0.8)
    assert list(fired) == [True, False, False]


# ── rolling_signals tests ────────────────────────────────────────


def _make_history(n: int = 20) -> pd.DataFrame:
    """Build a synthetic long-format signal history DataFrame."""
    idx = _idx(n)
    rng = np.random.default_rng(42)
    rows = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        for ts in idx:
            rows.append(
                {
                    "symbol": sym,
                    "timestamp": ts.isoformat(),
                    "annualized_funding": 0.05 + 0.01 * rng.standard_normal(),
                    "average_dated_carry": 0.03 + 0.005 * rng.standard_normal(),
                    "atm_iv": 0.6 + 0.05 * rng.standard_normal(),
                    "open_interest": 1e9 + 1e8 * rng.standard_normal(),
                }
            )
    return pd.DataFrame(rows)


def test_rolling_signals_empty_history() -> None:
    result = rolling_signals(pd.DataFrame())
    assert result["as_of_snapshot"] is True
    assert result["summary"] == []


def test_rolling_signals_few_observations() -> None:
    """With fewer than MIN_HISTORY_FOR_ROLLING rows, percentiles should be None."""
    df = _make_history(n=3)
    result = rolling_signals(df)
    # 3 rows per symbol → below threshold → snapshot mode fallback
    assert result["as_of_snapshot"] is True


def test_rolling_signals_enough_observations() -> None:
    """With sufficient history, rolling percentiles should be computed."""
    df = _make_history(n=20)
    result = rolling_signals(df, window="30D")
    assert result["as_of_snapshot"] is False
    assert result["observations"] > 0
    assert len(result["summary"]) == 2  # BTCUSDT and ETHUSDT

    for entry in result["summary"]:
        assert "symbol" in entry
        assert "currency" in entry
        assert "funding_pctile" in entry
        assert "carry_pctile" in entry
        assert "carry_vol_divergence" in entry
        # With enough data, percentiles should be non-null
        assert entry["funding_pctile"] is not None
        assert entry["carry_pctile"] is not None
        # Percentiles are in [0, 1]
        assert 0.0 <= entry["funding_pctile"] <= 1.0
        assert 0.0 <= entry["carry_pctile"] <= 1.0


def test_rolling_signals_wide_format() -> None:
    """rolling_signals also accepts wide-format DataFrames."""
    n = 10
    idx = _idx(n)
    rng = np.random.default_rng(99)
    df = pd.DataFrame(
        {
            "BTCUSDT_annualized_funding": 0.05 + 0.01 * rng.standard_normal(n),
            "BTCUSDT_average_dated_carry": 0.03 + 0.005 * rng.standard_normal(n),
            "BTCUSDT_atm_iv": 0.6 + 0.05 * rng.standard_normal(n),
            "BTCUSDT_open_interest": 1e9 + 1e8 * rng.standard_normal(n),
        },
        index=idx,
    )
    result = rolling_signals(df, window="30D")
    assert result["as_of_snapshot"] is False
    assert len(result["summary"]) == 1
    assert result["summary"][0]["symbol"] == "BTCUSDT"
