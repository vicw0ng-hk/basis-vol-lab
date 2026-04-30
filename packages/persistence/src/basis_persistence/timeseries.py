"""Parquet-based time-series store for ticker snapshots.

Writes partitioned Parquet files organised by venue and date.
Designed for local use and later migration to Cloudflare R2.
"""

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from basis_contracts.enums import AssetKind, Currency, Venue
from basis_contracts.models import TickerSnapshot

TICKER_SCHEMA = pa.schema(
    [
        pa.field("venue", pa.string(), nullable=False),
        pa.field("symbol", pa.string(), nullable=False),
        pa.field("currency", pa.string(), nullable=False),
        pa.field("asset_kind", pa.string(), nullable=False),
        pa.field("timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("mark_price", pa.float64(), nullable=False),
        pa.field("bid", pa.float64(), nullable=True),
        pa.field("ask", pa.float64(), nullable=True),
        pa.field("mark_iv", pa.float64(), nullable=True),
        pa.field("open_interest", pa.float64(), nullable=True),
        pa.field("funding_rate", pa.float64(), nullable=True),
    ]
)


def _snapshots_to_table(snapshots: list[TickerSnapshot]) -> pa.Table:
    """Convert a list of TickerSnapshot to a PyArrow Table."""
    return pa.table(
        {
            "venue": [s.venue.value for s in snapshots],
            "symbol": [s.symbol for s in snapshots],
            "currency": [s.currency.value for s in snapshots],
            "asset_kind": [s.asset_kind.value for s in snapshots],
            "timestamp": [s.timestamp for s in snapshots],
            "mark_price": [s.mark_price for s in snapshots],
            "bid": [s.bid for s in snapshots],
            "ask": [s.ask for s in snapshots],
            "mark_iv": [s.mark_iv for s in snapshots],
            "open_interest": [s.open_interest for s in snapshots],
            "funding_rate": [s.funding_rate for s in snapshots],
        },
        schema=TICKER_SCHEMA,
    )


def _table_to_snapshots(table: pa.Table) -> list[TickerSnapshot]:
    """Convert a PyArrow Table back to a list of TickerSnapshot."""
    snapshots: list[TickerSnapshot] = []
    for batch in table.to_batches():
        for i in range(batch.num_rows):
            ts_val = batch.column("timestamp")[i].as_py()
            if ts_val.tzinfo is None:
                ts_val = ts_val.replace(tzinfo=UTC)
            snapshots.append(
                TickerSnapshot(
                    venue=Venue(batch.column("venue")[i].as_py()),
                    symbol=batch.column("symbol")[i].as_py(),
                    currency=Currency(batch.column("currency")[i].as_py()),
                    asset_kind=AssetKind(batch.column("asset_kind")[i].as_py()),
                    timestamp=ts_val,
                    mark_price=batch.column("mark_price")[i].as_py(),
                    bid=batch.column("bid")[i].as_py(),
                    ask=batch.column("ask")[i].as_py(),
                    mark_iv=batch.column("mark_iv")[i].as_py(),
                    open_interest=batch.column("open_interest")[i].as_py(),
                    funding_rate=batch.column("funding_rate")[i].as_py(),
                )
            )
    return snapshots


class TimeSeriesStore:
    """Read/write ticker snapshots as Parquet files.

    Files are organised as:
        {base_dir}/{venue}/{YYYY-MM-DD}/tickers.parquet

    Args:
        base_dir: Root directory for Parquet storage.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)

    def _partition_path(self, venue: Venue, date: str) -> Path:
        return self._base_dir / venue.value / date / "tickers.parquet"

    def write_snapshots(self, snapshots: list[TickerSnapshot]) -> list[Path]:
        """Write snapshots, partitioned by venue and date.

        Returns the list of Parquet file paths written.
        """
        if not snapshots:
            return []

        # Group by (venue, date)
        groups: dict[tuple[Venue, str], list[TickerSnapshot]] = {}
        for s in snapshots:
            key = (s.venue, s.timestamp.strftime("%Y-%m-%d"))
            groups.setdefault(key, []).append(s)

        written: list[Path] = []
        for (venue, date), group in groups.items():
            table = _snapshots_to_table(group)
            path = self._partition_path(venue, date)
            path.parent.mkdir(parents=True, exist_ok=True)

            if path.exists():
                existing = pq.read_table(path, schema=TICKER_SCHEMA)
                table = pa.concat_tables([existing, table])

            pq.write_table(table, path)
            written.append(path)

        return written

    def read_snapshots(
        self,
        venue: Venue,
        date: str,
    ) -> list[TickerSnapshot]:
        """Read all snapshots for a given venue and date.

        Args:
            venue: Exchange venue.
            date: Date string in YYYY-MM-DD format.

        Returns:
            List of TickerSnapshot, empty if no data exists.
        """
        path = self._partition_path(venue, date)
        if not path.exists():
            return []
        table = pq.read_table(path, schema=TICKER_SCHEMA)
        return _table_to_snapshots(table)

    def list_dates(self, venue: Venue) -> list[str]:
        """List available dates for a venue, sorted ascending."""
        venue_dir = self._base_dir / venue.value
        if not venue_dir.exists():
            return []
        dates = sorted(
            d.name
            for d in venue_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        return dates

    def read_date_range(
        self,
        venue: Venue,
        start: datetime,
        end: datetime,
    ) -> list[TickerSnapshot]:
        """Read all snapshots for a venue within a date range (inclusive).

        Args:
            venue: Exchange venue.
            start: Start datetime (inclusive, date portion used).
            end: End datetime (inclusive, date portion used).

        Returns:
            List of TickerSnapshot within the range.
        """
        all_dates = self.list_dates(venue)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        result: list[TickerSnapshot] = []
        for d in all_dates:
            if start_str <= d <= end_str:
                result.extend(self.read_snapshots(venue, d))
        return result
