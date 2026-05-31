"""SQLite metadata store for instruments and collection runs.

Uses pure SQLite with D1-compatible semantics (no extensions, no WAL
assumptions beyond what D1 supports). All timestamps stored as ISO-8601
TEXT to match D1's lack of native datetime type.
"""

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from basis_contracts.enums import AssetKind, Currency, Venue
from basis_contracts.models import CollectionRun, Instrument

_SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    venue       TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    currency    TEXT NOT NULL,
    asset_kind  TEXT NOT NULL,
    expiry      TEXT,
    strike      REAL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (venue, symbol)
);

CREATE TABLE IF NOT EXISTS collection_runs (
    run_id             TEXT PRIMARY KEY,
    venue              TEXT NOT NULL,
    started_at         TEXT NOT NULL,
    ended_at           TEXT,
    status             TEXT NOT NULL DEFAULT 'running',
    records_collected  INTEGER NOT NULL DEFAULT 0
);
"""


def _ts_to_text(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _text_to_ts(text: str | None) -> datetime | None:
    if text is None:
        return None
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class MetadataStore:
    """Thin wrapper around a SQLite database for metadata.

    Args:
        db_path: Path to the SQLite file. Use ":memory:" for tests.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        # check_same_thread=False allows the connection to be used across
        # threads (FastAPI dispatches sync endpoints to a threadpool, and
        # Lambda may reuse a warm container across requests handled by
        # different worker threads). A lock serializes access.
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    # ── instruments ──────────────────────────────────────────────

    def upsert_instrument(self, inst: Instrument) -> None:
        """Insert or update an instrument."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO instruments
                    (venue, symbol, currency, asset_kind,
                     expiry, strike, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(venue, symbol) DO UPDATE SET
                    currency   = excluded.currency,
                    asset_kind = excluded.asset_kind,
                    expiry     = excluded.expiry,
                    strike     = excluded.strike,
                    is_active  = excluded.is_active
                """,
                (
                    inst.venue.value,
                    inst.symbol,
                    inst.currency.value,
                    inst.asset_kind.value,
                    _ts_to_text(inst.expiry),
                    inst.strike,
                    int(inst.is_active),
                ),
            )
            self._conn.commit()

    def get_instruments(
        self,
        venue: Venue | None = None,
        currency: Currency | None = None,
        asset_kind: AssetKind | None = None,
        active_only: bool = True,
    ) -> list[Instrument]:
        """Query instruments with optional filters."""
        clauses: list[str] = []
        params: list[str | int] = []
        if venue is not None:
            clauses.append("venue = ?")
            params.append(venue.value)
        if currency is not None:
            clauses.append("currency = ?")
            params.append(currency.value)
        if asset_kind is not None:
            clauses.append("asset_kind = ?")
            params.append(asset_kind.value)
        if active_only:
            clauses.append("is_active = 1")

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        cols = "venue, symbol, currency, asset_kind, expiry, strike, is_active"
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {cols} FROM instruments{where}",  # noqa: S608
                params,
            ).fetchall()

        return [
            Instrument(
                venue=Venue(r[0]),
                symbol=r[1],
                currency=Currency(r[2]),
                asset_kind=AssetKind(r[3]),
                expiry=_text_to_ts(r[4]),
                strike=r[5],
                is_active=bool(r[6]),
            )
            for r in rows
        ]

    # ── collection runs ──────────────────────────────────────────

    def insert_run(self, run: CollectionRun) -> None:
        """Record a new collection run."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO collection_runs
                    (run_id, venue, started_at, ended_at,
                     status, records_collected)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.venue.value,
                    _ts_to_text(run.started_at),
                    _ts_to_text(run.ended_at),
                    run.status,
                    run.records_collected,
                ),
            )
            self._conn.commit()

    def finish_run(
        self,
        run_id: str,
        *,
        ended_at: datetime,
        status: str = "completed",
        records_collected: int = 0,
    ) -> None:
        """Mark a collection run as finished."""
        with self._lock:
            self._conn.execute(
                """
                UPDATE collection_runs
                SET ended_at = ?, status = ?, records_collected = ?
                WHERE run_id = ?
                """,
                (_ts_to_text(ended_at), status, records_collected, run_id),
            )
            self._conn.commit()

    def get_runs(self, venue: Venue | None = None) -> list[CollectionRun]:
        """List collection runs, optionally filtered by venue."""
        cols = "run_id, venue, started_at, ended_at, status, records_collected"
        with self._lock:
            if venue is not None:
                rows = self._conn.execute(
                    f"SELECT {cols} FROM collection_runs "  # noqa: S608
                    "WHERE venue = ? ORDER BY started_at DESC",
                    (venue.value,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    f"SELECT {cols} FROM collection_runs "  # noqa: S608
                    "ORDER BY started_at DESC",
                ).fetchall()

        return [
            CollectionRun(
                run_id=r[0],
                venue=Venue(r[1]),
                started_at=_text_to_ts(r[2]),  # type: ignore[ty:invalid-argument-type]
                ended_at=_text_to_ts(r[3]),
                status=r[4],
                records_collected=r[5],
            )
            for r in rows
        ]

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()
