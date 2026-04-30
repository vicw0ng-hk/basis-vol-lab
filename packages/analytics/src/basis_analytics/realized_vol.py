"""Close-to-close and Parkinson realized-volatility estimators."""

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
