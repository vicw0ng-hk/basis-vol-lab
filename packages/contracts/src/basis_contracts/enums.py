"""Enumeration types for venues and asset classes."""

from enum import StrEnum


class Venue(StrEnum):
    """Supported exchange venues."""

    DERIBIT = "deribit"
    BINANCE = "binance"


class AssetKind(StrEnum):
    """Derivative asset types."""

    OPTION = "option"
    FUTURE = "future"
    PERPETUAL = "perpetual"


class Currency(StrEnum):
    """Supported underlying currencies."""

    BTC = "BTC"
    ETH = "ETH"
