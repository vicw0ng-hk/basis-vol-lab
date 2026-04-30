"""Analytic Greeks under Black-76.

All Greeks are vectorized with NumPy broadcasting. We return them as a
`Greeks` dataclass so callers can pull individual fields without juggling
positional ordering.

Conventions (forward-style, **not** Deribit's coin-quoted convention):

    * `delta`     ∂price / ∂F            (call: positive in `[0, df]`,
                                          put: negative in `[-df, 0]`)
    * `gamma`     ∂²price / ∂F²
    * `vega`      ∂price / ∂σ            (per 1.00 vol, not per 1 %)
    * `theta`     ∂price / ∂T            (per year; negate for "decay
                                          per day" by dividing by 365)
    * `rho`       ∂price / ∂r            (zero under our `df = 1.0`
                                          convention; included for API
                                          completeness)

To compare against Deribit's published Greeks (which are quoted in coin
terms per 1 unit of underlying), multiply forward delta by `df` (≈ 1)
and convert via the inverse-options scaling. The validation script
handles that translation.
"""

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
    """Compute forward-style Greeks for a Black-76 option.

    Degenerate cases (`T <= 0` or `sigma <= 0`) return zeros across all
    Greeks; callers that care about expiry-day risk should special-case
    those instruments themselves.
    """
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

    # Forward delta: call = df * N(d1), put = df * (N(d1) - 1) = -df * N(-d1)
    delta = np.where(call_b, df_b * norm.cdf(d1), -df_b * norm.cdf(-d1))

    # Gamma: same for call and put
    gamma = df_b * pdf_d1 / (F_b * safe_sig * sqrt_t)

    # Vega (per 1.00 of vol): same for call and put
    vega = df_b * F_b * pdf_d1 * sqrt_t

    # Theta (∂P/∂T, per year). Under Black-76 with constant df:
    #   call_theta  =  df * F * φ(d1) * σ / (2√T)
    #   put_theta   =  df * F * φ(d1) * σ / (2√T)
    # (both signs the same up to df = constant; with df = 1 the carry term
    # vanishes). We return d/dT, not -d/dT, so callers see the natural
    # mathematical sign and can multiply by -1/365 for "per-calendar-day
    # decay".
    theta_common = df_b * F_b * pdf_d1 * safe_sig / (2.0 * sqrt_t)
    theta = theta_common  # same for call and put under df = const

    # Rho is zero in our zero-rate / constant-df convention but kept for
    # API completeness so downstream code can store it uniformly.
    rho = np.zeros_like(F_b)

    zero = np.zeros_like(F_b)
    return Greeks(
        delta=np.where(degenerate, zero, delta),
        gamma=np.where(degenerate, zero, gamma),
        vega=np.where(degenerate, zero, vega),
        theta=np.where(degenerate, zero, theta),
        rho=rho,
    )
