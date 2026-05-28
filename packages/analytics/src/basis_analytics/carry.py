"""Carry, basis, and funding analytics."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import numpy as np
import pandas as pd


def annualized_carry(
    spot: float,
    future: float,
    days_to_expiry: float,
) -> float:
    """Compute annualized carry (basis) between spot and a future.

    Args:
        spot: Current spot price.
        future: Current futures price.
        days_to_expiry: Days until futures expiry.

    Returns:
        Annualized carry as a decimal (e.g. 0.12 for 12%).

    Raises:
        ValueError: If spot is non-positive or days_to_expiry is non-positive.
    """
    if spot <= 0:
        msg = "spot must be positive"
        raise ValueError(msg)
    if days_to_expiry <= 0:
        msg = "days_to_expiry must be positive"
        raise ValueError(msg)
    basis = (future - spot) / spot
    return basis * (365.0 / days_to_expiry)


def annualized_funding(funding_rate_8h: pd.Series) -> pd.Series:
    """Annualize an 8-hour funding-rate series.

    Binance and Deribit perpetuals settle funding every 8 hours, i.e.
    3 times per day or 1095 times per year. Compounding the realized
    8-hour rate gives:

        annualized = (1 + r_8h) ** (3 * 365) - 1

    Returns a Series aligned to `funding_rate_8h`.
    """
    return (1.0 + funding_rate_8h) ** (3.0 * 365.0) - 1.0


def basis_curve(
    futures_prices: Iterable[float],
    expiries: Iterable[datetime],
    *,
    spot: float,
    asof: datetime,
) -> pd.DataFrame:
    """Annualized-carry curve across a set of futures.

    Args:
        futures_prices: Prices of futures contracts.
        expiries: Expiry datetimes (UTC) in the same order as prices.
        spot: Reference spot/index price at `asof`.
        asof: Timestamp at which the curve is evaluated.

    Returns:
        DataFrame indexed by expiry with columns
        `[future, days, annualized_carry]`. Sorted by ascending expiry.
        Excludes any expiry on or before `asof`.
    """
    if spot <= 0:
        msg = "spot must be positive"
        raise ValueError(msg)
    fut = np.asarray(list(futures_prices), dtype=np.float64)
    exp = pd.to_datetime(list(expiries), utc=True)

    asof_ts = pd.Timestamp(asof)
    if asof_ts.tzinfo is None:
        asof_ts = asof_ts.tz_localize("UTC")
    days = (exp - asof_ts).total_seconds().to_numpy() / 86400.0

    df = pd.DataFrame({"future": fut, "days": days}, index=exp)
    df = df.loc[df["days"] > 0].sort_index()
    df["annualized_carry"] = (df["future"] - spot) / spot * (365.0 / df["days"])
    return df
