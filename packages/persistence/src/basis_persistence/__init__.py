"""SQLite/D1 metadata and Parquet/R2 time-series storage."""

from typing import TYPE_CHECKING, Any

from basis_persistence.d1 import D1MetadataStore
from basis_persistence.metadata import MetadataStore
from basis_persistence.metadata_factory import metadata_store_from_env

# `TICKER_SCHEMA` and `TimeSeriesStore` live in `timeseries`, which imports
# pyarrow at module scope and builds the Arrow schema at import time — about
# 0.45 s on Graviton at 1024 MB. Re-exporting them eagerly meant that any
# consumer touching only the metadata stores paid for Parquet too: in Lambda
# that put pyarrow in the INIT phase, which is capped at 10 s, purely because
# `basis_api.main` needs `metadata_store_from_env`.
#
# PEP 562 keeps the public surface identical while making that cost arrive
# only for callers that actually reference a Parquet name.
if TYPE_CHECKING:
    from basis_persistence.timeseries import TICKER_SCHEMA, TimeSeriesStore

_LAZY = {"TICKER_SCHEMA", "TimeSeriesStore"}

__all__ = [
    "D1MetadataStore",
    "MetadataStore",
    "TICKER_SCHEMA",
    "TimeSeriesStore",
    "metadata_store_from_env",
]


def __getattr__(name: str) -> Any:
    """Resolve the Parquet re-exports on first access (PEP 562)."""
    if name in _LAZY:
        from basis_persistence import timeseries

        return getattr(timeseries, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    # `__getattr__` is invisible to the default `dir()`, which would
    # otherwise omit the lazy names and break tab-completion.
    return sorted(__all__)
