"""FastAPI service exposing curated artifacts as JSON.

Lambda-friendly: the module-level ``app`` object is wrapped by
:class:`mangum.Mangum` so the same code can run under ``uvicorn`` locally
or as an AWS Lambda handler in production. The handler is exposed as
``handler`` for that purpose.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from basis_api.snapshot import DEFAULT_DATA_DIR, run_snapshot

DATA_DIR = Path(os.environ.get("BASIS_DATA_DIR", str(DEFAULT_DATA_DIR)))
ARTIFACTS_DIR = DATA_DIR / "artifacts"

app = FastAPI(title="Basis & Vol Lab API", version="0.1.0")

# Permissive CORS for local dev. Tighten via BASIS_CORS_ORIGINS in prod.
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
    path = ARTIFACTS_DIR / name
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"artifact '{name}' not found under {ARTIFACTS_DIR}. "
                "Run the snapshot first (POST /api/refresh or "
                "`mise run snapshot`)."
            ),
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


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
    """Re-run the snapshot synchronously and return the new meta."""
    result = run_snapshot(DATA_DIR)
    return {
        "generated_at": result.generated_at.isoformat(),
        "deribit_tickers": result.deribit_tickers,
        "binance_funding_rows": result.binance_funding_rows,
    }


# Lambda entry point. Imported lazily so the dependency is optional in dev.
try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:  # pragma: no cover - mangum not installed in dev
    handler = None
