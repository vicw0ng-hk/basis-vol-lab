"""Tests for realized-vol estimators."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from basis_analytics import close_to_close_rv, parkinson_rv


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
