"""Headline regime signals.

Three composite signals defined in the initial plan:

    * **Carry-vol divergence**: percentile-rank of annualized carry
      *minus* percentile-rank of (IV − RV). Positive = carry rich
      relative to vol; negative = carry cheap.
    * **Skew stress**: percentile-rank of front-end 25-delta
      risk-reversal extremes plus percentile-rank of OI concentration.
    * **Regime-change alert**: fires when the one-day moves in carry,
      skew, and OI percentiles all exceed a configurable threshold.

Each function takes pandas Series of *already-percentile-ranked* inputs
and returns a pandas Series of the same index. Keeping the percentile
rank as an explicit step makes the code easy to inspect and the
interview narrative ("non-magical, defensible") easy to tell.
"""

from __future__ import annotations

import pandas as pd


def percentile_rank(s: pd.Series, *, window: str = "365D") -> pd.Series:
    """Rolling percentile rank (in `[0, 1]`) over a time window.

    For each point `t`, returns the fraction of observations in the
    trailing window that are <= `s[t]`. Requires a `DatetimeIndex`.
    """
    if not isinstance(s.index, pd.DatetimeIndex):
        msg = "Series must have a DatetimeIndex"
        raise TypeError(msg)

    def _rank(window_values: pd.Series) -> float:
        if len(window_values) == 0:
            return float("nan")
        last = window_values.iloc[-1]
        return float((window_values <= last).mean())

    return s.rolling(window=window).apply(_rank, raw=False)  # type: ignore[return-value]


def carry_vol_divergence(
    carry_pctile: pd.Series, iv_minus_rv_pctile: pd.Series
) -> pd.Series:
    """Score in `[-1, 1]` where positive = carry rich vs vol."""
    return carry_pctile - iv_minus_rv_pctile


def skew_stress(
    rr_25d_pctile: pd.Series, oi_concentration_pctile: pd.Series
) -> pd.Series:
    """Score in `[0, 1]`: average of two stress dimensions.

    `rr_25d_pctile` is taken on the **absolute value** of the 25Δ
    risk-reversal so that both extreme call-skew and put-skew contribute
    to stress.
    """
    return (rr_25d_pctile + oi_concentration_pctile) / 2.0


def regime_change_alert(
    carry_pct: pd.Series,
    skew_pct: pd.Series,
    oi_pct: pd.Series,
    *,
    threshold: float = 0.8,
) -> pd.Series:
    """Boolean Series that is True when all three percentiles exceed `threshold`.

    The default `0.8` corresponds to "all three signals in their top 20 %
    of the trailing year".
    """
    return (carry_pct >= threshold) & (skew_pct >= threshold) & (oi_pct >= threshold)
