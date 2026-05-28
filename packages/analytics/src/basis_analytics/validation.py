"""Compare solved Black-76 IV against Deribit's `mark_iv`."""

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
    """Return one IV-error row per valid option snapshot."""
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

        # Deribit option marks are coin-denominated.
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
    """Summarize IV errors by expiry."""
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
