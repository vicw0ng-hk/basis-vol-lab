"""FastAPI service for curated dashboard artifacts."""

from __future__ import annotations

import contextlib
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from basis_api.history import get_history_dates, get_history_snapshot
from basis_api.snapshot import run_snapshot
from basis_api.storage import LocalArtifactStore, store_from_env

_store = store_from_env()

# Optional metadata store for collection-run tracking.
_meta_store: Any = None
with contextlib.suppress(Exception):
    from basis_persistence import metadata_store_from_env

    _meta_store = metadata_store_from_env()

app = FastAPI(title="Basis & Vol Lab API", version="0.1.0")

_origins_raw = os.environ.get("BASIS_CORS_ORIGINS", "*")
_allow_origins = (
    ["*"]
    if _origins_raw.strip() == "*"
    else [o.strip() for o in _origins_raw.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load(name: str) -> dict[str, Any]:
    try:
        return _store.read_json(name)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"artifact {name!r} not found in {_store!r}. "
                "Run the snapshot first (POST /api/refresh or "
                "`mise run snapshot`)."
            ),
        ) from exc


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return _load("meta.json")


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    return _load("overview.json")


@app.get("/api/vol")
def vol() -> dict[str, Any]:
    return _load("vol.json")


@app.get("/api/carry")
def carry() -> dict[str, Any]:
    return _load("carry.json")


@app.get("/api/signals")
def signals() -> dict[str, Any]:
    return _load("signals.json")


@app.post("/api/refresh")
def refresh() -> dict[str, Any]:
    """Run one refresh and return its summary."""
    result = run_snapshot(_store, meta_store=_meta_store)
    return {
        "generated_at": result.generated_at.isoformat(),
        "deribit_tickers": result.deribit_tickers,
        "binance_funding_rows": result.binance_funding_rows,
        "store": result.store_repr,
    }


@app.get("/api/runs")
def runs() -> dict[str, Any]:
    """Return recent collection runs for operational health monitoring."""
    if _meta_store is None:
        return {"runs": [], "note": "Metadata store not configured."}
    raw_runs = _meta_store.get_runs()
    return {
        "runs": [
            {
                "run_id": r.run_id,
                "venue": r.venue.value if hasattr(r.venue, "value") else str(r.venue),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "status": r.status,
                "records_collected": r.records_collected,
            }
            for r in raw_runs[:50]
        ],
    }


def _data_dir() -> Path:
    """Resolve the data directory from the artifact store or env."""
    if isinstance(_store, LocalArtifactStore):
        return _store.base_dir
    return Path(os.environ.get("BASIS_DATA_DIR", "data"))


@app.get("/api/history/dates")
def history_dates() -> dict[str, Any]:
    """List available historical snapshot dates."""
    dates = get_history_dates(_data_dir())
    return {"dates": dates}


@app.get("/api/history/{date}")
def history_snapshot(date: str) -> dict[str, Any]:
    """Load a historical snapshot by date (YYYY-MM-DD)."""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(
            status_code=400, detail="Invalid date format, expected YYYY-MM-DD"
        )
    result = get_history_snapshot(_data_dir(), date)
    if result.get("empty"):
        raise HTTPException(status_code=404, detail=f"No snapshot data for {date}")
    return result


try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:  # pragma: no cover - mangum not installed in dev
    handler = None
