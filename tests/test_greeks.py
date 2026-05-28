"""Tests for `basis_analytics.greeks` (Black-76 Greeks)."""

from __future__ import annotations

import math

import numpy as np
from basis_analytics import black76_greeks, black76_price


def _fd(f, x, h):  # central finite difference
    return (f(x + h) - f(x - h)) / (2 * h)


def test_delta_matches_finite_difference_call() -> None:
    F, K, T, sigma = 70_000.0, 70_000.0, 0.25, 0.60
    g = black76_greeks(F, K, T, sigma, is_call=True)

    def price_at(F_) -> float:
        return float(black76_price(F_, K, T, sigma, is_call=True))

    fd = _fd(price_at, F, 1.0)
    assert math.isclose(float(g.delta), fd, rel_tol=1e-4)


def test_delta_call_minus_put_equals_df() -> None:
    F, K, T, sigma = 70_000.0, 80_000.0, 0.5, 0.55
    gc = black76_greeks(F, K, T, sigma, is_call=True)
    gp = black76_greeks(F, K, T, sigma, is_call=False)
    # Forward delta parity under df = 1: delta_call - delta_put = 1
    assert math.isclose(float(gc.delta) - float(gp.delta), 1.0, rel_tol=1e-9)


def test_gamma_matches_finite_difference() -> None:
    F, K, T, sigma = 70_000.0, 70_000.0, 0.25, 0.60
    g = black76_greeks(F, K, T, sigma, is_call=True)

    def price_at(F_) -> float:
        return float(black76_price(F_, K, T, sigma, is_call=True))

    h = 10.0
    fd_gamma = (price_at(F + h) - 2 * price_at(F) + price_at(F - h)) / (h * h)
    assert math.isclose(float(g.gamma), fd_gamma, rel_tol=1e-3)


def test_vega_matches_finite_difference() -> None:
    F, K, T, sigma = 70_000.0, 75_000.0, 0.5, 0.55
    g = black76_greeks(F, K, T, sigma, is_call=True)

    def price_at(s) -> float:
        return float(black76_price(F, K, T, s, is_call=True))

    fd = _fd(price_at, sigma, 1e-4)
    assert math.isclose(float(g.vega), fd, rel_tol=1e-4)


def test_greeks_vectorized() -> None:
    F = np.array([100.0, 100.0])
    K = np.array([90.0, 110.0])
    T = 1.0
    sigma = 0.3
    g = black76_greeks(F, K, T, sigma, is_call=True)
    assert g.delta.shape == (2,)
    assert g.delta[0] > g.delta[1]  # ITM call has higher delta


def test_degenerate_returns_zeros() -> None:
    g = black76_greeks(100.0, 110.0, 0.0, 0.5, is_call=True)
    assert float(g.delta) == 0.0
    assert float(g.gamma) == 0.0
    assert float(g.vega) == 0.0
