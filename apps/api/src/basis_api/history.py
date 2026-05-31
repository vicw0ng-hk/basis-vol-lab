"""Historical replay: load Parquet snapshots by date and compute summaries."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from basis_analytics.surface import atm_term_structure
from basis_contracts import AssetKind, TickerSnapshot, Venue
from basis_persistence import TimeSeriesStore


def _years_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / (365.0 * 86400.0)


def _build_date_summary(snapshots: list[TickerSnapshot], date: str) -> dict[str, Any]:
    """Build a summary dict from Deribit snapshots for a single date."""
    options = [s for s in snapshots if s.asset_kind is AssetKind.OPTION]
    futures = [
        s for s in snapshots if s.asset_kind in (AssetKind.FUTURE, AssetKind.PERPETUAL)
    ]

    # Extract ATM IVs per currency.
    atm_ivs: dict[str, list[dict[str, Any]]] = {}
    if options:
        asof_ts = options[0].timestamp
        forwards: dict[tuple[str, datetime], float] = {}
        for f in futures:
            if f.asset_kind is AssetKind.FUTURE and f.expiry is not None:
                forwards[(f.currency.value, f.expiry)] = f.mark_price

        rows: list[dict[str, Any]] = []
        for opt in options:
            if opt.expiry is None or opt.strike is None or opt.mark_iv is None:
                continue
            fwd = forwards.get((opt.currency.value, opt.expiry))
            if fwd is None:
                continue
            rows.append(
                {
                    "currency": opt.currency.value,
                    "expiry": opt.expiry,
                    "strike": opt.strike,
                    "forward": fwd,
                    "mark_iv": opt.mark_iv,
                    "tte_years": _years_between(asof_ts, opt.expiry),
                }
            )

        if rows:
            df = pd.DataFrame(rows)
            for ccy, sub_obj in df.groupby("currency"):
                sub = pd.DataFrame(sub_obj)
                atm = atm_term_structure(sub).reset_index()
                points: list[dict[str, Any]] = []
                for rec in atm.to_dict(orient="records"):
                    expiry_ts = pd.Timestamp(rec["expiry"])
                    if pd.isna(expiry_ts):
                        continue
                    expiry_val = expiry_ts.to_pydatetime()
                    assert isinstance(expiry_val, datetime)
                    points.append(
                        {
                            "expiry": expiry_val.isoformat(),
                            "strike": float(rec["strike"]),
                            "forward": float(rec["forward"]),
                            "mark_iv": float(rec["mark_iv"]),
                            "tte_years": float(_years_between(asof_ts, expiry_val)),
                        }
                    )
                atm_ivs[str(ccy)] = points

    # Futures marks per currency.
    futures_data: dict[str, list[dict[str, Any]]] = {}
    for f in futures:
        ccy = f.currency.value
        futures_data.setdefault(ccy, []).append(
            {
                "symbol": f.symbol,
                "kind": f.asset_kind.value,
                "expiry": f.expiry.isoformat() if f.expiry else None,
                "mark_price": f.mark_price,
                "open_interest": f.open_interest,
            }
        )

    # Aggregate stats.
    total_oi = sum(f.open_interest for f in futures if f.open_interest is not None)
    avg_atm_iv: dict[str, float | None] = {}
    for ccy, points in atm_ivs.items():
        ivs = [p["mark_iv"] for p in points if p.get("mark_iv") is not None]
        avg_atm_iv[ccy] = sum(ivs) / len(ivs) if ivs else None

    timestamp = snapshots[0].timestamp.isoformat() if snapshots else None

    return {
        "date": date,
        "timestamp": timestamp,
        "option_count": len(options),
        "future_count": len(futures),
        "total_open_interest": total_oi,
        "avg_atm_iv": avg_atm_iv,
        "atm_term_structure": atm_ivs,
        "futures": futures_data,
    }


def _safe_pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None:
        return None
    if math.isnan(new) or math.isnan(old) or old == 0:
        return None
    return (new - old) / abs(old)


def build_diff(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Compute 'what changed?' between two date summaries."""
    changes: dict[str, Any] = {
        "previous_date": previous["date"],
        "option_count_delta": current["option_count"] - previous["option_count"],
        "future_count_delta": current["future_count"] - previous["future_count"],
        "oi_change": _safe_pct_change(
            current["total_open_interest"], previous["total_open_interest"]
        ),
    }

    # ATM IV changes per currency.
    iv_changes: dict[str, dict[str, float | None]] = {}
    all_ccys = set(current.get("avg_atm_iv", {}).keys()) | set(
        previous.get("avg_atm_iv", {}).keys()
    )
    for ccy in sorted(all_ccys):
        curr_iv = current.get("avg_atm_iv", {}).get(ccy)
        prev_iv = previous.get("avg_atm_iv", {}).get(ccy)
        iv_changes[ccy] = {
            "current": curr_iv,
            "previous": prev_iv,
            "delta": (
                float(curr_iv - prev_iv)
                if curr_iv is not None and prev_iv is not None
                else None
            ),
        }
    changes["atm_iv_changes"] = iv_changes
    return changes


def get_history_dates(data_dir: Path) -> list[str]:
    """List available Deribit snapshot dates."""
    ts_store = TimeSeriesStore(data_dir / "parquet")
    return ts_store.list_dates(Venue.DERIBIT)


def get_history_snapshot(data_dir: Path, date: str) -> dict[str, Any]:
    """Load and summarise a historical snapshot for a date."""
    ts_store = TimeSeriesStore(data_dir / "parquet")
    snapshots = ts_store.read_snapshots(Venue.DERIBIT, date)
    if not snapshots:
        return {"date": date, "empty": True}

    summary = _build_date_summary(snapshots, date)

    # Try to compute diff with previous date.
    dates = ts_store.list_dates(Venue.DERIBIT)
    try:
        idx = dates.index(date)
    except ValueError:
        idx = -1

    diff: dict[str, Any] | None = None
    if idx > 0:
        prev_date = dates[idx - 1]
        prev_snaps = ts_store.read_snapshots(Venue.DERIBIT, prev_date)
        if prev_snaps:
            prev_summary = _build_date_summary(prev_snaps, prev_date)
            diff = build_diff(summary, prev_summary)

    return {**summary, "diff": diff, "empty": False}
