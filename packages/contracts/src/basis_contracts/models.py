"""Core data models for market data snapshots."""

from dataclasses import dataclass
from datetime import datetime

from basis_contracts.enums import AssetKind, Currency, Venue


@dataclass(frozen=True, slots=True)
class TickerSnapshot:
    """A point-in-time ticker snapshot from an exchange."""

    venue: Venue
    symbol: str
    currency: Currency
    asset_kind: AssetKind
    timestamp: datetime
    mark_price: float
    bid: float | None = None
    ask: float | None = None
    mark_iv: float | None = None
    open_interest: float | None = None
    funding_rate: float | None = None
