-- 0001_init.sql
-- Initial schema for the basis-vol-lab D1 metadata database.
-- Mirrors the SQLite DDL in basis_persistence.metadata so the same
-- model serialisation works against either backend.

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

CREATE INDEX IF NOT EXISTS idx_instruments_venue_kind
    ON instruments (venue, asset_kind);

CREATE INDEX IF NOT EXISTS idx_collection_runs_started
    ON collection_runs (started_at DESC);
