"""Black-76 forward-option pricer.

Black-76 prices a European option on a *forward* (or future) `F` struck at
`K`, with time-to-expiry `T` and lognormal forward volatility `sigma`. We
use it because Deribit's `mark_iv` is quoted under exactly this convention
(forward = mark price of the matching future, no discounting in the
inverse-quoted premium).

All functions are NumPy-vectorized: every numeric argument may be a scalar
or an array, and standard broadcasting applies.
"""

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
    """Black-76 forward-option price.

    Args:
        F: Forward (or future mark) price.
        K: Strike.
        T: Time to expiry in years (ACT/365 elsewhere in this package).
        sigma: Lognormal forward volatility (e.g. 0.65 = 65 %).
        is_call: True for call, False for put. May be an array.
        df: Discount factor applied to the forward expectation. Defaults
            to 1.0 (no discounting), which matches Deribit's inverse
            premium quoting.

    Returns:
        Option price as a NumPy array (or 0-d array for scalar inputs).

    The function degenerates gracefully:
        * `T <= 0` returns the intrinsic value `max(F - K, 0)` /
          `max(K - F, 0)`, scaled by `df`.
        * `sigma <= 0` with `T > 0` also returns intrinsic value.
    """
    F_a = np.asarray(F, dtype=np.float64)
    K_a = np.asarray(K, dtype=np.float64)
    T_a = np.asarray(T, dtype=np.float64)
    sig_a = np.asarray(sigma, dtype=np.float64)
    df_a = np.asarray(df, dtype=np.float64)
    call_a = np.asarray(is_call, dtype=bool)

    # Broadcast everything to a common shape so we can mask.
    F_b, K_b, T_b, sig_b, df_b, call_b = np.broadcast_arrays(
        F_a, K_a, T_a, sig_a, df_a, call_a
    )

    intrinsic = np.where(call_b, np.maximum(F_b - K_b, 0.0), np.maximum(K_b - F_b, 0.0))
    degenerate = (T_b <= 0.0) | (sig_b <= 0.0)

    # Avoid divide-by-zero in d1/d2 on the degenerate branch by substituting
    # safe placeholders; we'll mask the result back to intrinsic value.
    safe_T = np.where(degenerate, 1.0, T_b)
    safe_sig = np.where(degenerate, 1.0, sig_b)
    d1, d2 = _d1_d2(F_b, K_b, safe_T, safe_sig)

    call_price = df_b * (F_b * norm.cdf(d1) - K_b * norm.cdf(d2))
    put_price = df_b * (K_b * norm.cdf(-d2) - F_b * norm.cdf(-d1))
    bs_price = np.where(call_b, call_price, put_price)

    return np.where(degenerate, df_b * intrinsic, bs_price)
