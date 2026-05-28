"""Tests for `basis_analytics.pricing` (Black-76)."""

from __future__ import annotations

import math

import numpy as np
from basis_analytics import black76_price


def test_black76_atm_known_value() -> None:
    # At F = K, Black-76 reduces to F * (2N(σ√T/2) - 1) for both call and put.
    F, K, T, sigma = 100.0, 100.0, 1.0, 0.20
    expected = F * (2 * 0.5398278372770290 - 1)  # N(0.1) = 0.5398...
    call = float(black76_price(F, K, T, sigma, is_call=True))
    put = float(black76_price(F, K, T, sigma, is_call=False))
    assert math.isclose(call, expected, rel_tol=1e-6)
    assert math.isclose(put, expected, rel_tol=1e-6)


def test_black76_put_call_parity() -> None:
    # Call - Put = df * (F - K)
    F, K, T, sigma = 70_000.0, 65_000.0, 0.25, 0.55
    call = float(black76_price(F, K, T, sigma, is_call=True))
    put = float(black76_price(F, K, T, sigma, is_call=False))
    assert math.isclose(call - put, F - K, rel_tol=1e-9)


def test_black76_intrinsic_at_expiry() -> None:
    # T = 0 → intrinsic value
    F, K, sigma = 70_000.0, 65_000.0, 0.55
    call = float(black76_price(F, K, 0.0, sigma, is_call=True))
    put = float(black76_price(F, K, 0.0, sigma, is_call=False))
    assert call == 5_000.0
    assert put == 0.0


def test_black76_zero_vol_returns_intrinsic() -> None:
    F, K, T = 100.0, 110.0, 0.5
    call = float(black76_price(F, K, T, 0.0, is_call=True))
    put = float(black76_price(F, K, T, 0.0, is_call=False))
    assert call == 0.0
    assert put == 10.0


def test_black76_vectorized_broadcasting() -> None:
    F = np.array([100.0, 100.0, 100.0])
    K = np.array([90.0, 100.0, 110.0])
    T = 1.0
    sigma = 0.30
    prices = black76_price(F, K, T, sigma, is_call=True)
    assert prices.shape == (3,)
    # Monotone-decreasing in strike for calls.
    assert prices[0] > prices[1] > prices[2]


def test_black76_discount_factor_scales_price() -> None:
    F, K, T, sigma = 100.0, 100.0, 1.0, 0.20
    p1 = float(black76_price(F, K, T, sigma, is_call=True, df=1.0))
    p_half = float(black76_price(F, K, T, sigma, is_call=True, df=0.5))
    assert math.isclose(p_half, 0.5 * p1, rel_tol=1e-12)
