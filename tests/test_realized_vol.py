"""Tests for realized-vol estimators."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from basis_analytics import close_to_close_rv, parkinson_rv, yang_zhang_rv


def _daily_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")


def test_close_to_close_constant_return() -> None:
    # Daily log-return = ln(1.01); window = 30D
    n = 60
    idx = _daily_index(n)
    prices = pd.Series(100.0 * (1.01 ** np.arange(n)), index=idx)
    rv = close_to_close_rv(prices, window="30D")
    # Constant returns → variance ≈ 0 → RV ≈ 0
    assert rv.iloc[-1] < 1e-9


def test_close_to_close_iid_known_vol() -> None:
    rng = np.random.default_rng(seed=42)
    sigma = 0.50  # 50% annualized
    n = 365 * 2
    daily_sigma = sigma / math.sqrt(365)
    log_returns = rng.normal(0.0, daily_sigma, size=n)
    prices = pd.Series(100.0 * np.exp(np.cumsum(log_returns)), index=_daily_index(n))
    rv = close_to_close_rv(prices, window="365D")
    # Allow generous tolerance due to sampling noise
    assert abs(rv.iloc[-1] - sigma) < 0.05


def test_parkinson_basic() -> None:
    n = 60
    idx = _daily_index(n)
    # Synthetic OHLC where high/low ratio is constant
    highs = pd.Series(101.0, index=idx)
    lows = pd.Series(99.0, index=idx)
    rv = parkinson_rv(highs, lows, window="30D")
    # Closed form: sqrt((ln(101/99))^2 / (4 ln 2) * 365)
    expected = math.sqrt((math.log(101 / 99) ** 2) / (4 * math.log(2)) * 365)
    assert math.isclose(float(rv.iloc[-1]), expected, rel_tol=1e-9)


def test_close_to_close_requires_datetime_index() -> None:
    s = pd.Series([1.0, 2.0, 3.0])
    try:
        close_to_close_rv(s)
    except TypeError:
        return
    msg = "expected TypeError"
    raise AssertionError(msg)


def test_yang_zhang_constant_price() -> None:
    n = 60
    idx = _daily_index(n)
    flat = pd.Series(100.0, index=idx)
    rv = yang_zhang_rv(flat, flat, flat, flat, window="30D")
    # Constant price → zero vol
    assert rv.iloc[-1] < 1e-9


def test_yang_zhang_known_vol() -> None:
    rng = np.random.default_rng(seed=42)
    sigma = 0.50
    n = 365 * 2
    daily_sigma = sigma / math.sqrt(365)
    idx = _daily_index(n)
    # Simulate OHLC from GBM-like process
    closes = [100.0]
    for _i in range(1, n):
        closes.append(closes[-1] * math.exp(rng.normal(0, daily_sigma)))
    closes_s = pd.Series(closes, index=idx)
    opens_s = pd.Series(closes_s.shift(1).bfill().to_numpy(), index=idx)
    intra_spread = closes_s * daily_sigma * 0.5
    highs_s = pd.concat([opens_s, closes_s], axis=1).max(axis=1) + intra_spread.abs()
    lows_s = pd.concat([opens_s, closes_s], axis=1).min(axis=1) - intra_spread.abs()
    rv = yang_zhang_rv(opens_s, highs_s, lows_s, closes_s, window="365D")
    # Should be in the ballpark of true vol (generous tolerance for synthetic data)
    assert abs(rv.iloc[-1] - sigma) < 0.15


def test_yang_zhang_requires_datetime_index() -> None:
    s = pd.Series([1.0, 2.0, 3.0])
    try:
        yang_zhang_rv(s, s, s, s)
    except TypeError:
        return
    msg = "expected TypeError"
    raise AssertionError(msg)


def test_yang_zhang_mismatched_index() -> None:
    idx1 = _daily_index(5)
    idx2 = pd.date_range("2025-02-01", periods=5, freq="D", tz="UTC")
    s1 = pd.Series(100.0, index=idx1)
    s2 = pd.Series(100.0, index=idx2)
    try:
        yang_zhang_rv(s1, s2, s1, s1)
    except ValueError:
        return
    msg = "expected ValueError"
    raise AssertionError(msg)
