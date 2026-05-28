"""Vectorized Black-76 forward-option pricer."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm


def _d1_d2(
    F: NDArray[np.float64],
    K: NDArray[np.float64],
    T: NDArray[np.float64],
    sigma: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    sqrt_t = np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return d1, d2


def black76_price(
    F: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    sigma: ArrayLike,
    *,
    is_call: bool | ArrayLike,
    df: ArrayLike = 1.0,
) -> NDArray[np.float64]:
    """Return Black-76 prices with NumPy broadcasting."""
    F_a = np.asarray(F, dtype=np.float64)
    K_a = np.asarray(K, dtype=np.float64)
    T_a = np.asarray(T, dtype=np.float64)
    sig_a = np.asarray(sigma, dtype=np.float64)
    df_a = np.asarray(df, dtype=np.float64)
    call_a = np.asarray(is_call, dtype=bool)

    F_b, K_b, T_b, sig_b, df_b, call_b = np.broadcast_arrays(
        F_a, K_a, T_a, sig_a, df_a, call_a
    )

    intrinsic = np.where(call_b, np.maximum(F_b - K_b, 0.0), np.maximum(K_b - F_b, 0.0))
    degenerate = (T_b <= 0.0) | (sig_b <= 0.0)

    # Avoid divide-by-zero before masking degenerate rows back to intrinsic.
    safe_T = np.where(degenerate, 1.0, T_b)
    safe_sig = np.where(degenerate, 1.0, sig_b)
    d1, d2 = _d1_d2(F_b, K_b, safe_T, safe_sig)

    call_price = df_b * (F_b * norm.cdf(d1) - K_b * norm.cdf(d2))
    put_price = df_b * (K_b * norm.cdf(-d2) - F_b * norm.cdf(-d1))
    bs_price = np.where(call_b, call_price, put_price)

    return np.where(degenerate, df_b * intrinsic, bs_price)
