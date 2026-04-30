"""Connector-local dataclasses for Binance backfill responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FundingRateRow:
    """A single row from `/fapi/v1/fundingRate`."""

    symbol: str
    funding_time: datetime
    funding_rate: float
    mark_price: float | None


@dataclass(frozen=True, slots=True)
class BasisRow:
    """A single row from `/futures/data/basis`."""

    pair: str
    contract_type: str
    timestamp: datetime
    basis: float
    basis_rate: float
    futures_price: float
    index_price: float


@dataclass(frozen=True, slots=True)
class OpenInterestRow:
    """A single row from `/futures/data/openInterestHist`."""

    symbol: str
    timestamp: datetime
    sum_open_interest: float
    sum_open_interest_value: float
