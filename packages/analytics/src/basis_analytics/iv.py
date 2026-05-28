"""Implied volatility inversion under Black-76.

We solve `black76_price(sigma) = market_price` for `sigma` via Brent's
method (`scipy.optimize.brentq`). Brent is the right tool here:

    * Black-76 price is a strictly increasing function of `sigma` for
      `sigma > 0` (positive vega), so the function is monotone — Brent
      converges quickly and reliably without needing derivatives.
    * Vectorizing Brent doesn't pay off; the bottleneck in our pipeline
      is network I/O, not IV solves. We expose a pure-Python loop wrapper
      `implied_vol_array` for batches.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq

from basis_analytics.pricing import black76_price


def implied_vol_black76(
    price: float,
    F: float,
    K: float,
    T: float,
    *,
    is_call: bool,
    df: float = 1.0,
    lo: float = 1e-4,
    hi: float = 5.0,
    tol: float = 1e-8,
) -> float:
    """Solve for Black-76 implied volatility.

    Returns `math.nan` if:
        * inputs violate no-arbitrage bounds (price below intrinsic or
          above the discounted forward),
        * `T <= 0` (no time, no volatility), or
        * the bracket `[lo, hi]` doesn't change sign (the target price is
          outside the volatility range we search).

    The default bracket `[1e-4, 5.0]` covers any IV ever seen on liquid
    crypto options.
    """
    if T <= 0 or price < 0 or F <= 0 or K <= 0:
        return math.nan

    intrinsic = max(F - K, 0.0) if is_call else max(K - F, 0.0)
    upper_bound = df * (F if is_call else K)
    if price < df * intrinsic - tol or price > upper_bound + tol:
        return math.nan

    def f(sigma: float) -> float:
        return float(black76_price(F, K, T, sigma, is_call=is_call, df=df)) - price

    f_lo = f(lo)
    f_hi = f(hi)
    if f_lo > 0 or f_hi < 0:
        # Target price unreachable in the search bracket.
        return math.nan

    try:
        result = brentq(f, lo, hi, xtol=tol, rtol=tol, maxiter=100)  # type: ignore[arg-type]
        return float(result)  # type: ignore[arg-type]
    except ValueError, RuntimeError:
        return math.nan


def implied_vol_array(
    prices: NDArray[np.float64],
    F: NDArray[np.float64],
    K: NDArray[np.float64],
    T: NDArray[np.float64],
    is_call: NDArray[np.bool_],
    *,
    df: float = 1.0,
) -> NDArray[np.float64]:
    """Vectorized implied-vol solve via element-wise Brent.

    Inputs are 1-D arrays of equal length; output is a 1-D float64 array
    with `nan` in any position where the solve failed.
    """
    n = len(prices)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = implied_vol_black76(
            float(prices[i]),
            float(F[i]),
            float(K[i]),
            float(T[i]),
            is_call=bool(is_call[i]),
            df=df,
        )
    return out
