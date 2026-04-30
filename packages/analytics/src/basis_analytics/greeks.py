"""Vectorized Black-76 forward Greeks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm

from basis_analytics.pricing import _d1_d2


@dataclass(frozen=True, slots=True)
class Greeks:
    """Black-76 forward Greeks, vectorized."""

    delta: NDArray[np.float64]
    gamma: NDArray[np.float64]
    vega: NDArray[np.float64]
    theta: NDArray[np.float64]
    rho: NDArray[np.float64]


def black76_greeks(
    F: ArrayLike,
    K: ArrayLike,
    T: ArrayLike,
    sigma: ArrayLike,
    *,
    is_call: bool | ArrayLike,
    df: ArrayLike = 1.0,
) -> Greeks:
    """Compute forward-style Greeks; degenerate rows return zero."""
    F_a = np.asarray(F, dtype=np.float64)
    K_a = np.asarray(K, dtype=np.float64)
    T_a = np.asarray(T, dtype=np.float64)
    sig_a = np.asarray(sigma, dtype=np.float64)
    df_a = np.asarray(df, dtype=np.float64)
    call_a = np.asarray(is_call, dtype=bool)

    F_b, K_b, T_b, sig_b, df_b, call_b = np.broadcast_arrays(
        F_a, K_a, T_a, sig_a, df_a, call_a
    )

    degenerate = (T_b <= 0.0) | (sig_b <= 0.0)
    safe_T = np.where(degenerate, 1.0, T_b)
    safe_sig = np.where(degenerate, 1.0, sig_b)

    d1, d2 = _d1_d2(F_b, K_b, safe_T, safe_sig)
    sqrt_t = np.sqrt(safe_T)
    pdf_d1 = norm.pdf(d1)

    delta = np.where(call_b, df_b * norm.cdf(d1), -df_b * norm.cdf(-d1))
    gamma = df_b * pdf_d1 / (F_b * safe_sig * sqrt_t)
    vega = df_b * F_b * pdf_d1 * sqrt_t
    theta_common = df_b * F_b * pdf_d1 * safe_sig / (2.0 * sqrt_t)
    theta = theta_common
    rho = np.zeros_like(F_b)

    zero = np.zeros_like(F_b)
    return Greeks(
        delta=np.where(degenerate, zero, delta),
        gamma=np.where(degenerate, zero, gamma),
        vega=np.where(degenerate, zero, vega),
        theta=np.where(degenerate, zero, theta),
        rho=rho,
    )
