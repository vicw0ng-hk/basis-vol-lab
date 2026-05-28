"""Tests for `basis_analytics.iv` (Brent IV inversion)."""

from __future__ import annotations

import math

import numpy as np
from basis_analytics import black76_price, implied_vol_array, implied_vol_black76


def test_iv_round_trip() -> None:
    F, K, T, sigma = 70_000.0, 75_000.0, 0.25, 0.65
    price = float(black76_price(F, K, T, sigma, is_call=True))
    recovered = implied_vol_black76(price, F, K, T, is_call=True)
    assert math.isclose(recovered, sigma, abs_tol=1e-7)


def test_iv_round_trip_put() -> None:
    F, K, T, sigma = 70_000.0, 60_000.0, 0.10, 0.95
    price = float(black76_price(F, K, T, sigma, is_call=False))
    recovered = implied_vol_black76(price, F, K, T, is_call=False)
    assert math.isclose(recovered, sigma, abs_tol=1e-7)


def test_iv_negative_time_returns_nan() -> None:
    assert math.isnan(implied_vol_black76(5.0, 100.0, 100.0, -1.0, is_call=True))


def test_iv_above_arb_bound_returns_nan() -> None:
    # Call price > F is impossible (with df = 1).
    assert math.isnan(implied_vol_black76(101.0, 100.0, 90.0, 1.0, is_call=True))


def test_iv_below_intrinsic_returns_nan() -> None:
    F, K, T = 100.0, 90.0, 1.0
    intrinsic = F - K  # 10
    assert math.isnan(implied_vol_black76(intrinsic - 1.0, F, K, T, is_call=True))


def test_iv_array_round_trip() -> None:
    F = np.full(3, 70_000.0)
    K = np.array([60_000.0, 70_000.0, 80_000.0])
    T = np.full(3, 0.25)
    sigma = np.array([0.55, 0.60, 0.70])
    is_call = np.array([False, True, True])
    prices = np.array(
        [
            float(black76_price(F[i], K[i], T[i], sigma[i], is_call=is_call[i]))
            for i in range(3)
        ]
    )
    out = implied_vol_array(prices, F, K, T, is_call)
    np.testing.assert_allclose(out, sigma, atol=1e-7)
