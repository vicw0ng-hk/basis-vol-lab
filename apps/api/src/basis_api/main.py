"""FastAPI service for curated dashboard artifacts."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from basis_api.snapshot import run_snapshot
from basis_api.storage import store_from_env

_store = store_from_env()

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
    result = run_snapshot(_store)
    return {
        "generated_at": result.generated_at.isoformat(),
        "deribit_tickers": result.deribit_tickers,
        "binance_funding_rows": result.binance_funding_rows,
        "store": result.store_repr,
    }


try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:  # pragma: no cover - mangum not installed in dev
    handler = None
