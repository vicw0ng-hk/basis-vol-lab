"""Volatility surface helpers for ATM term structure and smile interpolation."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import PchipInterpolator


def atm_term_structure(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    """Pick the closest-to-forward option per expiry.

    Args:
        snapshot_df: A DataFrame with at least the columns
            `[expiry, strike, forward, mark_iv]`. One row per option.

    Returns:
        DataFrame indexed by expiry with columns
        `[strike, forward, mark_iv, moneyness]` where `moneyness` is
        `strike / forward`. Sorted by expiry.
    """
    required = {"expiry", "strike", "forward", "mark_iv"}
    missing = required - set(snapshot_df.columns)
    if missing:
        msg = f"snapshot_df missing columns: {sorted(missing)}"
        raise ValueError(msg)

    df = snapshot_df.copy()
    df["abs_log_moneyness"] = np.abs(np.log(df["strike"] / df["forward"]))
    idx = df.groupby("expiry")["abs_log_moneyness"].idxmin()
    atm = df.loc[idx, ["expiry", "strike", "forward", "mark_iv"]].copy()
    atm["moneyness"] = atm["strike"] / atm["forward"]
    return atm.set_index("expiry").sort_index()


def smile_interp(
    strikes: ArrayLike,
    ivs: ArrayLike,
) -> Callable[[ArrayLike], NDArray[np.float64]]:
    """Build a strike-IV interpolator for a single expiry.

    Returns a callable that maps strikes (scalar or array) to IV values.
    Uses PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) so the
    smile stays monotone where the input is monotone — no spurious
    overshoot between observed strikes.

    Outside the input strike range we extrapolate flat: IV at the
    nearest observed strike.
    """
    K = np.asarray(strikes, dtype=np.float64)
    V = np.asarray(ivs, dtype=np.float64)
    if K.shape != V.shape or K.ndim != 1 or len(K) < 2:
        msg = "strikes and ivs must be 1-D arrays of equal length >= 2"
        raise ValueError(msg)

    order = np.argsort(K)
    K = K[order]
    V = V[order]
    pchip = PchipInterpolator(K, V, extrapolate=False)

    def interp(K_query: ArrayLike) -> NDArray[np.float64]:
        q = np.asarray(K_query, dtype=np.float64)
        out = pchip(q)
        out = np.where(q <= K[0], V[0], out)
        out = np.where(q >= K[-1], V[-1], out)
        return out

    return interp
