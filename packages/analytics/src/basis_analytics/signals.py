"""Headline regime-signal formulas built from percentile-ranked series."""

from __future__ import annotations

from typing import Any

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


# ---------------------------------------------------------------------------
# Rolling signals from accumulated snapshot history
# ---------------------------------------------------------------------------

_METRIC_COLS = [
    "annualized_funding",
    "average_dated_carry",
    "atm_iv",
    "open_interest",
]

# Minimum observations before we consider percentile ranks meaningful.
MIN_HISTORY_FOR_ROLLING = 5


def rolling_signals(
    history: pd.DataFrame,
    *,
    window: str = "365D",
) -> dict[str, Any]:
    """Compute rolling-percentile regime signals from accumulated history.

    Args:
        history: DataFrame with a ``DatetimeIndex`` and columns per symbol:
            ``{symbol}_annualized_funding``, ``{symbol}_average_dated_carry``,
            ``{symbol}_atm_iv``, ``{symbol}_open_interest``.
            Also accepts a flat format with columns ``symbol``, ``timestamp``,
            and the four metric columns (will be pivoted internally).
        window: Pandas offset string for the percentile rank lookback.

    Returns:
        A dict with ``as_of_snapshot: False``, ``observations: int``, and
        ``summary: [...]`` containing per-symbol percentile ranks and
        composite scores.
    """
    if history.empty:
        return _empty_result()

    # If the DataFrame is in long format (has a "symbol" column), pivot.
    if "symbol" in history.columns:
        history = _pivot_long_to_wide(history)

    if not isinstance(history.index, pd.DatetimeIndex):
        msg = "history must have a DatetimeIndex"
        raise TypeError(msg)

    symbols = _detect_symbols(history)
    if not symbols:
        return _empty_result()

    n_obs = len(history)
    summary: list[dict[str, Any]] = []

    for sym in symbols:
        entry = _compute_symbol_signals(history, sym, window, n_obs)
        if entry is not None:
            summary.append(entry)

    is_snapshot = n_obs < MIN_HISTORY_FOR_ROLLING

    result: dict[str, Any] = {
        "as_of_snapshot": is_snapshot,
        "observations": n_obs,
        "window": window,
        "summary": summary,
    }
    if is_snapshot:
        result["note"] = (
            "Rolling-percentile signals appear once the historical snapshot "
            "store has enough observations."
        )
    return result


def _empty_result() -> dict[str, Any]:
    return {
        "as_of_snapshot": True,
        "observations": 0,
        "window": "365D",
        "note": (
            "Rolling-percentile signals appear once the historical snapshot "
            "store has enough observations."
        ),
        "summary": [],
    }


def _pivot_long_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot long-format history into wide format with DatetimeIndex."""
    if "timestamp" not in df.columns:
        msg = "Long-format history must have a 'timestamp' column"
        raise ValueError(msg)

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()

    symbols = df["symbol"].unique()
    frames: list[pd.DataFrame] = []
    for sym in symbols:
        sub = df.loc[df["symbol"] == sym, _METRIC_COLS].copy()
        sub.columns = [f"{sym}_{col}" for col in _METRIC_COLS]
        frames.append(sub)

    if not frames:
        return pd.DataFrame()

    wide = frames[0]
    for f in frames[1:]:
        wide = wide.join(f, how="outer")
    return wide


def _detect_symbols(df: pd.DataFrame) -> list[str]:
    """Extract unique symbol prefixes from wide-format column names."""
    symbols: list[str] = []
    suffix = f"_{_METRIC_COLS[0]}"
    for col in df.columns:
        if col.endswith(suffix):
            sym = col[: -len(suffix)]
            symbols.append(sym)
    return sorted(set(symbols))


def _safe_float(val: object) -> float | None:
    """Convert to float, returning None for NaN/missing."""
    if val is None:
        return None
    try:
        f = float(val)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    except TypeError, ValueError:
        return None
    if pd.isna(f):
        return None
    return f


def _compute_symbol_signals(
    df: pd.DataFrame,
    sym: str,
    window: str,
    n_obs: int,
) -> dict[str, Any] | None:
    """Compute percentile-ranked signals for one symbol."""
    col_funding = f"{sym}_annualized_funding"
    col_carry = f"{sym}_average_dated_carry"
    col_iv = f"{sym}_atm_iv"
    col_oi = f"{sym}_open_interest"

    needed = [col_funding, col_carry]
    if not all(c in df.columns for c in needed):
        return None

    result: dict[str, Any] = {
        "symbol": sym,
        "currency": sym.replace("USDT", ""),
    }

    has_enough = n_obs >= MIN_HISTORY_FOR_ROLLING

    # Current (latest) raw values
    result["perp_annualized_funding"] = _safe_float(
        df[col_funding].iloc[-1] if col_funding in df.columns else None
    )
    result["average_dated_carry"] = _safe_float(
        df[col_carry].iloc[-1] if col_carry in df.columns else None
    )
    result["atm_iv"] = _safe_float(
        df[col_iv].iloc[-1] if col_iv in df.columns else None
    )
    result["open_interest"] = _safe_float(
        df[col_oi].iloc[-1] if col_oi in df.columns else None
    )

    if not has_enough:
        # Fall back to snapshot-level diff
        fund = result["perp_annualized_funding"]
        carry = result["average_dated_carry"]
        result["carry_vol_divergence"] = (
            float(fund - carry) if fund is not None and carry is not None else None
        )
        result["funding_pctile"] = None
        result["carry_pctile"] = None
        result["iv_pctile"] = None
        result["oi_pctile"] = None
        return result

    # Rolling percentile ranks
    def _pctile(col: str) -> float | None:
        if col not in df.columns:
            return None
        s = df[col].dropna()
        if len(s) < MIN_HISTORY_FOR_ROLLING:
            return None
        ranked = percentile_rank(s, window=window)
        return _safe_float(ranked.iloc[-1])

    result["funding_pctile"] = _pctile(col_funding)
    result["carry_pctile"] = _pctile(col_carry)
    result["iv_pctile"] = _pctile(col_iv)
    result["oi_pctile"] = _pctile(col_oi)

    # Carry-vol divergence from percentiles
    fp = result["funding_pctile"]
    cp = result["carry_pctile"]
    if fp is not None and cp is not None:
        result["carry_vol_divergence"] = float(fp - cp)
    else:
        fund = result["perp_annualized_funding"]
        carry = result["average_dated_carry"]
        result["carry_vol_divergence"] = (
            float(fund - carry) if fund is not None and carry is not None else None
        )

    return result
