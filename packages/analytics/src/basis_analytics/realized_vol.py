"""Realized-volatility estimators on pandas time series.

We provide two complementary estimators:

    * **Close-to-close** — the classic estimator, simple and unbiased
      under iid log-returns. High variance for small windows.
    * **Parkinson (1980)** — uses each bar's high/low range, ~5x more
      efficient than close-to-close for the same number of bars but
      assumes geometric Brownian motion with no jumps and continuous
      observation. Good for crypto where we have decent OHLC.

Both estimators expect a `DatetimeIndex` (UTC) on the input series and
return an annualized RV in decimal form (`0.55` = 55 %).

Annualization factor defaults to **365** because crypto trades 24/7.
For traditional markets pass `annualize=252`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def close_to_close_rv(
    prices: pd.Series,
    *,
    window: str = "30D",
    annualize: float = 365.0,
) -> pd.Series:
    """Annualized close-to-close realized volatility.

    Args:
        prices: Series of close prices indexed by UTC `DatetimeIndex`.
            Values are mark/close prices, not log-returns.
        window: Rolling-window size, e.g. `"30D"`, `"7D"`, `"24h"`.
        annualize: Number of bars per year, when each bar is one day.
            For crypto (24/7) the default 365.0 is correct.

    Returns:
        Series of the same index as `prices` (with `NaN` for points
        before the window is full), holding annualized RV in decimal.

    Raises:
        TypeError: If `prices.index` is not a `DatetimeIndex`.
    """
    if not isinstance(prices.index, pd.DatetimeIndex):
        msg = "prices must have a DatetimeIndex"
        raise TypeError(msg)

    log_returns = np.log(prices / prices.shift(1))
    # Average sampling frequency in days (median over the input).
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
    """Annualized Parkinson realized volatility from high/low ranges.

    Parkinson's estimator on each bar:

        var_bar = (1 / (4 ln 2)) * (ln(high / low))²

    This is then averaged over the rolling window.

    Args:
        highs: Series of bar highs, UTC `DatetimeIndex`.
        lows: Series of bar lows, aligned to `highs`.
        window: Rolling window (e.g. `"30D"`).
        annualize: Bars per year for daily bars (default 365 for crypto).

    Returns:
        Annualized RV in decimal form.
    """
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
