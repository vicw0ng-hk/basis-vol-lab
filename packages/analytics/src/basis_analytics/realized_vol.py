"""Close-to-close, Parkinson, and Yang-Zhang realized-volatility estimators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def close_to_close_rv(
    prices: pd.Series,
    *,
    window: str = "30D",
    annualize: float = 365.0,
) -> pd.Series:
    """Return annualized close-to-close RV."""
    if not isinstance(prices.index, pd.DatetimeIndex):
        msg = "prices must have a DatetimeIndex"
        raise TypeError(msg)

    log_returns = np.log(prices / prices.shift(1))
    median_dt_seconds = float(
        prices.index.to_series().diff().dropna().dt.total_seconds().median() or 86400.0
    )
    bars_per_day = 86400.0 / median_dt_seconds
    annualization_factor = annualize * bars_per_day

    var = log_returns.rolling(window=window).var()
    return np.sqrt(var * annualization_factor)


def parkinson_rv(
    highs: pd.Series,
    lows: pd.Series,
    *,
    window: str = "30D",
    annualize: float = 365.0,
) -> pd.Series:
    """Return annualized Parkinson RV from high/low ranges."""
    if not isinstance(highs.index, pd.DatetimeIndex):
        msg = "highs must have a DatetimeIndex"
        raise TypeError(msg)
    if not highs.index.equals(lows.index):
        msg = "highs and lows must share the same index"
        raise ValueError(msg)

    log_hl = np.log(highs / lows)
    bar_var = (log_hl * log_hl) / (4.0 * np.log(2.0))

    median_dt_seconds = float(
        highs.index.to_series().diff().dropna().dt.total_seconds().median() or 86400.0
    )
    bars_per_day = 86400.0 / median_dt_seconds
    annualization_factor = annualize * bars_per_day

    mean_var = bar_var.rolling(window=window).mean()
    return np.sqrt(mean_var * annualization_factor)


def yang_zhang_rv(
    opens: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    *,
    window: str = "30D",
    annualize: float = 365.0,
) -> pd.Series:
    """Return annualized Yang-Zhang RV from OHLC bars.

    The Yang-Zhang (2000) estimator combines overnight (close-to-open),
    open-to-close, and Rogers-Satchell components to produce an unbiased
    estimator that is independent of drift and opening jumps.

    Args:
        opens: Opening prices with a ``DatetimeIndex``.
        highs: High prices (same index).
        lows: Low prices (same index).
        closes: Closing prices (same index).
        window: Rolling window specification (e.g. ``"30D"``).
        annualize: Trading days per year for annualization.

    Returns:
        Annualized Yang-Zhang RV as a ``pd.Series``.
    """
    if not isinstance(opens.index, pd.DatetimeIndex):
        msg = "opens must have a DatetimeIndex"
        raise TypeError(msg)
    for name, s in [("highs", highs), ("lows", lows), ("closes", closes)]:
        if not opens.index.equals(s.index):
            msg = f"{name} must share the same index as opens"
            raise ValueError(msg)

    median_dt_seconds = float(
        opens.index.to_series().diff().dropna().dt.total_seconds().median() or 86400.0
    )
    bars_per_day = 86400.0 / median_dt_seconds
    annualization_factor = annualize * bars_per_day

    # Overnight return: log(open_t / close_{t-1})
    log_oc = np.log(opens / closes.shift(1))
    # Open-to-close return
    log_co = np.log(closes / opens)

    # Rogers-Satchell per-bar variance
    log_ho = np.log(highs / opens)
    log_lo = np.log(lows / opens)
    log_hc = np.log(highs / closes)
    log_lc = np.log(lows / closes)
    rs_var = log_ho * log_hc + log_lo * log_lc

    # Rolling components
    overnight_var = log_oc.rolling(window=window).var()
    close_var = log_co.rolling(window=window).var()
    rs_mean = rs_var.rolling(window=window).mean()

    # Optimal weight k minimises estimator variance
    n = log_oc.rolling(window=window).count()
    k = 0.34 / (1.34 + (n + 1) / (n - 1))

    yz_var = overnight_var + k * close_var + (1.0 - k) * rs_mean
    return np.sqrt(yz_var * annualization_factor)
