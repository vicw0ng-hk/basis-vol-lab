"""Compare our Black-76 IV against Deribit's `mark_iv`.

Deribit publishes `mark_iv` on every option ticker. By solving our own
Black-76 IV from the option's mark **price** and the matching future's
mark price, we can produce a per-instrument error series that:

    * proves our pricer is implemented correctly (errors should be on
      the order of `1e-3` vol points or smaller for liquid quotes),
    * makes price/Greeks reproducible offline from stored snapshots, and
    * gives us a quality-control signal when an exchange feed is
      misbehaving (sudden spike in error → upstream issue).

This module is **pure**: no network I/O. The CLI in `__main__.py` is the
thin wrapper that pulls a live snapshot via the existing Deribit
connector.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd
from basis_contracts import AssetKind, TickerSnapshot

from basis_analytics.iv import implied_vol_black76


@dataclass(frozen=True, slots=True)
class IVValidationRow:
    """One row of the IV-error table."""

    instrument: str
    expiry: datetime
    strike: float
    is_call: bool
    forward: float
    mark_price_coin: float
    mark_price_usd: float
    deribit_mark_iv: float
    our_iv: float
    abs_err: float


def validate_iv(
    snapshots: Iterable[TickerSnapshot],
    forwards_by_expiry: Mapping[datetime, float],
    *,
    asof: datetime,
) -> pd.DataFrame:
    """Compute our IV for each option snapshot and compare to `mark_iv`.

    Args:
        snapshots: Option `TickerSnapshot`s. Non-options are ignored.
        forwards_by_expiry: Forward (matching-future mark) price keyed by
            expiry. Options whose expiry is missing here are skipped.
        asof: Reference timestamp for time-to-expiry.

    Returns:
        DataFrame with columns matching `IVValidationRow`. NaNs in
        `our_iv` indicate snapshots where the IV solve failed (typically
        deep OTM options where the bid/ask straddles intrinsic value).
    """
    rows: list[IVValidationRow] = []
    asof_ts = pd.Timestamp(asof)
    if asof_ts.tzinfo is None:
        asof_ts = asof_ts.tz_localize("UTC")

    for s in snapshots:
        if s.asset_kind is not AssetKind.OPTION:
            continue
        if s.expiry is None or s.strike is None or s.mark_iv is None:
            continue
        if s.mark_price <= 0:
            continue
        F = forwards_by_expiry.get(s.expiry)
        if F is None or F <= 0:
            continue

        # Deribit option mark_price is in coin terms (BTC/ETH); the
        # USD-denominated premium needed for Black-76 is mark * F.
        usd_price = s.mark_price * F

        T = (pd.Timestamp(s.expiry) - asof_ts).total_seconds() / (365.0 * 86400.0)
        if T <= 0:
            continue

        is_call = s.symbol.endswith("-C")
        our = implied_vol_black76(usd_price, F, s.strike, T, is_call=is_call)
        abs_err = float("nan") if our != our else abs(our - s.mark_iv)

        rows.append(
            IVValidationRow(
                instrument=s.symbol,
                expiry=s.expiry,
                strike=s.strike,
                is_call=is_call,
                forward=F,
                mark_price_coin=s.mark_price,
                mark_price_usd=usd_price,
                deribit_mark_iv=s.mark_iv,
                our_iv=our,
                abs_err=abs_err,
            )
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "instrument",
                "expiry",
                "strike",
                "is_call",
                "forward",
                "mark_price_coin",
                "mark_price_usd",
                "deribit_mark_iv",
                "our_iv",
                "abs_err",
            ]
        )
    return pd.DataFrame([asdict(row) for row in rows])


def summarize_by_tenor(errors: pd.DataFrame) -> pd.DataFrame:
    """Per-expiry summary of IV errors.

    Returns a DataFrame indexed by expiry with columns
    `[count, mean_abs_err, p95_abs_err, max_abs_err]`. Rows where
    `our_iv` is NaN are excluded from the aggregates.
    """
    if errors.empty:
        return pd.DataFrame(
            columns=["count", "mean_abs_err", "p95_abs_err", "max_abs_err"]
        )
    clean = errors.dropna(subset=["our_iv"])

    def _p95(s: pd.Series) -> float:
        return float(s.quantile(0.95))

    grouped = clean.groupby("expiry")["abs_err"]
    return pd.DataFrame(
        {
            "count": grouped.count(),
            "mean_abs_err": grouped.mean(),
            "p95_abs_err": grouped.apply(_p95),
            "max_abs_err": grouped.max(),
        }
    ).sort_index()
