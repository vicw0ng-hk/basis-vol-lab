"""Snapshot orchestration: pull live data, persist, emit curated JSON.

This is the engine of the MVP product shell. One call to
:func:`run_snapshot` does the following:

1. Pull a single Deribit options + futures book summary (live REST).
2. Pull a single Binance funding-rate + basis + open-interest backfill.
3. Persist the union of ticker snapshots through `TimeSeriesStore`.
4. Compute curated artifacts (overview, vol, carry, signals) and write
   them as JSON under ``data/artifacts/``.

The script is deliberately self-contained and synchronous-feeling at the
top level (``asyncio.run``) so it can be invoked equally well from the
CLI (``python -m basis_api.snapshot``), from a FastAPI endpoint
(``POST /api/refresh``), or from a Lambda handler.
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from basis_analytics.carry import annualized_carry, annualized_funding
from basis_analytics.surface import atm_term_structure
from basis_connectors.binance import BinanceRestClient
from basis_connectors.deribit.parsers import parse_instrument_name
from basis_contracts import (
    AssetKind,
    TickerSnapshot,
    Venue,
)
from basis_persistence import TimeSeriesStore

_DERIBIT_BASE = "https://www.deribit.com/api/v2"

DEFAULT_DATA_DIR = Path("data")


def _years_between(start: datetime, end: datetime) -> float:
    """Year fraction between two UTC datetimes (ACT/365)."""
    return (end - start).total_seconds() / (365.0 * 86400.0)


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    """Summary of a single snapshot run."""

    generated_at: datetime
    deribit_tickers: int
    binance_funding_rows: int
    artifacts_dir: Path
    parquet_paths: list[Path]


# ---------------------------------------------------------------------------
# Deribit pull (REST book-summary; same shape as basis_analytics.validate)
# ---------------------------------------------------------------------------


async def _deribit_book_summary(
    client: httpx.AsyncClient, currency: str, kind: str
) -> list[dict[str, Any]]:
    r = await client.get(
        f"{_DERIBIT_BASE}/public/get_book_summary_by_currency",
        params={"currency": currency, "kind": kind},
    )
    r.raise_for_status()
    return list(r.json().get("result", []))


def _deribit_row_to_snapshot(
    row: dict[str, Any], asof: datetime
) -> TickerSnapshot | None:
    name = row.get("instrument_name")
    if not isinstance(name, str):
        return None
    decoded = parse_instrument_name(name)
    if decoded is None:
        return None
    currency, kind, expiry, strike = decoded

    mark_price = row.get("mark_price")
    if mark_price is None:
        return None

    mark_iv_raw = row.get("mark_iv")
    mark_iv = float(mark_iv_raw) / 100.0 if mark_iv_raw is not None else None

    bid_raw = row.get("bid_price")
    ask_raw = row.get("ask_price")
    oi_raw = row.get("open_interest")
    funding_raw = row.get("funding_8h")

    return TickerSnapshot(
        venue=Venue.DERIBIT,
        symbol=name,
        currency=currency,
        asset_kind=kind,
        timestamp=asof,
        mark_price=float(mark_price),
        bid=float(bid_raw) if bid_raw is not None else None,
        ask=float(ask_raw) if ask_raw is not None else None,
        mark_iv=mark_iv,
        open_interest=float(oi_raw) if oi_raw is not None else None,
        funding_rate=float(funding_raw) if funding_raw is not None else None,
        expiry=expiry,
        strike=strike,
    )


async def _pull_deribit(
    currency: str, asof: datetime
) -> tuple[list[TickerSnapshot], list[TickerSnapshot]]:
    """Return (options, futures+perps) snapshots for `currency`."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        opts_raw, futs_raw = await asyncio.gather(
            _deribit_book_summary(client, currency, "option"),
            _deribit_book_summary(client, currency, "future"),
        )
    options = [
        s
        for s in (_deribit_row_to_snapshot(r, asof) for r in opts_raw)
        if s is not None
    ]
    futures = [
        s
        for s in (_deribit_row_to_snapshot(r, asof) for r in futs_raw)
        if s is not None
    ]
    return options, futures


# ---------------------------------------------------------------------------
# Binance pull (REST: funding + basis + OI)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _BinanceData:
    funding: dict[str, list[dict[str, Any]]]  # symbol -> rows
    basis: dict[str, list[dict[str, Any]]]  # pair -> rows
    oi: dict[str, list[dict[str, Any]]]  # symbol -> rows


async def _pull_binance(symbols: Iterable[str]) -> _BinanceData:
    funding: dict[str, list[dict[str, Any]]] = {}
    basis: dict[str, list[dict[str, Any]]] = {}
    oi: dict[str, list[dict[str, Any]]] = {}

    async with BinanceRestClient() as client:
        for sym in symbols:
            pair = sym  # USDT-M: pair == symbol.

            # Each pull is wrapped: Binance rate-limit responses (HTTP 418
            # / -1003) on /futures/data/* should not abort the whole
            # snapshot. Missing series degrade gracefully in the UI.
            funding[sym] = await _safe_pull(
                _pull_funding(client, sym),
                f"funding/{sym}",
            )
            basis[pair] = await _safe_pull(
                _pull_basis(client, pair),
                f"basis/{pair}",
            )
            oi[sym] = await _safe_pull(
                _pull_oi(client, sym),
                f"oi/{sym}",
            )
    return _BinanceData(funding=funding, basis=basis, oi=oi)


async def _pull_funding(client: BinanceRestClient, sym: str) -> list[dict[str, Any]]:
    rows = await client.get_funding_rate_history(sym, limit=100)
    return [
        {
            "funding_time": row.funding_time.isoformat(),
            "funding_rate": row.funding_rate,
            "mark_price": row.mark_price,
        }
        for row in rows
    ]


async def _pull_basis(client: BinanceRestClient, pair: str) -> list[dict[str, Any]]:
    rows = await client.get_basis(
        pair, contract_type="PERPETUAL", period="5m", limit=100
    )
    return [
        {
            "timestamp": row.timestamp.isoformat(),
            "basis": row.basis,
            "basis_rate": row.basis_rate,
            "futures_price": row.futures_price,
            "index_price": row.index_price,
        }
        for row in rows
    ]


async def _pull_oi(client: BinanceRestClient, sym: str) -> list[dict[str, Any]]:
    rows = await client.get_open_interest_hist(sym, period="5m", limit=100)
    return [
        {
            "timestamp": row.timestamp.isoformat(),
            "sum_open_interest": row.sum_open_interest,
            "sum_open_interest_value": row.sum_open_interest_value,
        }
        for row in rows
    ]


async def _safe_pull(coro: Any, label: str) -> list[dict[str, Any]]:
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any pull failure
        print(f"[snapshot] warn: {label} failed: {exc}")  # noqa: T201
        return []


# ---------------------------------------------------------------------------
# Curated artifact builders
# ---------------------------------------------------------------------------


def _build_overview(
    binance: _BinanceData,
    deribit_futures: list[TickerSnapshot],
) -> dict[str, Any]:
    venues: dict[str, dict[str, Any]] = {}

    # Binance: latest funding, latest basis, latest OI per symbol.
    for sym, rows in binance.funding.items():
        latest_funding = rows[-1] if rows else None
        basis_rows = binance.basis.get(sym, [])
        latest_basis = basis_rows[-1] if basis_rows else None
        oi_rows = binance.oi.get(sym, [])
        latest_oi = oi_rows[-1] if oi_rows else None

        ann_fund = None
        if latest_funding is not None:
            ann_fund = float(
                annualized_funding(pd.Series([latest_funding["funding_rate"]])).iloc[0]
            )

        venues.setdefault("binance", {})[sym] = {
            "funding_rate_8h": (
                latest_funding["funding_rate"] if latest_funding else None
            ),
            "annualized_funding": ann_fund,
            "basis_rate": latest_basis["basis_rate"] if latest_basis else None,
            "futures_price": (latest_basis["futures_price"] if latest_basis else None),
            "index_price": latest_basis["index_price"] if latest_basis else None,
            "open_interest_usd": (
                latest_oi["sum_open_interest_value"] if latest_oi else None
            ),
        }

    # Deribit: futures + perp snapshot per currency.
    by_ccy: dict[str, list[dict[str, Any]]] = {}
    for f in deribit_futures:
        ccy = f.currency.value
        by_ccy.setdefault(ccy, []).append(
            {
                "symbol": f.symbol,
                "kind": f.asset_kind.value,
                "expiry": f.expiry.isoformat() if f.expiry else None,
                "mark_price": f.mark_price,
                "open_interest": f.open_interest,
                "funding_rate_8h": f.funding_rate,
            }
        )
    if by_ccy:
        venues["deribit"] = by_ccy

    return {"venues": venues}


def _build_vol(
    deribit_options: list[TickerSnapshot],
    deribit_futures: list[TickerSnapshot],
    asof: datetime,
) -> dict[str, Any]:
    # Build the same DataFrame validate_iv expects, then derive the ATM
    # term structure and a smile for the nearest expiry.
    forwards: dict[tuple[str, datetime], float] = {}
    for f in deribit_futures:
        if f.asset_kind is AssetKind.FUTURE and f.expiry is not None:
            forwards[(f.currency.value, f.expiry)] = f.mark_price

    rows: list[dict[str, Any]] = []
    for opt in deribit_options:
        if (
            opt.asset_kind is not AssetKind.OPTION
            or opt.expiry is None
            or opt.strike is None
            or opt.mark_iv is None
        ):
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
                "tte_years": _years_between(asof, opt.expiry),
            }
        )

    out: dict[str, Any] = {"by_currency": {}}
    if not rows:
        return out

    df = pd.DataFrame(rows)
    for ccy, sub_obj in df.groupby("currency"):
        sub = pd.DataFrame(sub_obj)
        atm = atm_term_structure(sub).reset_index()
        atm_records: list[dict[str, Any]] = []
        for rec in atm.to_dict(orient="records"):
            expiry_ts = pd.Timestamp(rec["expiry"])
            if pd.isna(expiry_ts):
                continue
            expiry_val = expiry_ts.to_pydatetime()
            assert isinstance(expiry_val, datetime)
            atm_records.append(
                {
                    "expiry": expiry_val.isoformat(),
                    "strike": float(rec["strike"]),
                    "forward": float(rec["forward"]),
                    "mark_iv": float(rec["mark_iv"]),
                    "tte_years": float(_years_between(asof, expiry_val)),
                }
            )
        # Smile for the nearest non-degenerate expiry.
        nearest_expiry_val = sub["expiry"].min()
        nearest_ts = pd.Timestamp(nearest_expiry_val)  # type: ignore[arg-type]
        nearest_dt = nearest_ts.to_pydatetime()
        assert isinstance(nearest_dt, datetime)
        smile_df = sub.loc[sub["expiry"] == nearest_expiry_val].sort_values(by="strike")
        smile_records: list[dict[str, Any]] = []
        for rec in smile_df.to_dict(orient="records"):
            strike = float(rec["strike"])
            forward = float(rec["forward"])
            smile_records.append(
                {
                    "strike": strike,
                    "moneyness": strike / forward,
                    "mark_iv": float(rec["mark_iv"]),
                }
            )
        out["by_currency"][str(ccy)] = {
            "atm_term_structure": atm_records,
            "smile": {
                "expiry": nearest_dt.isoformat(),
                "points": smile_records,
            },
        }
    return out


def _build_carry(
    binance: _BinanceData,
    deribit_futures: list[TickerSnapshot],
    asof: datetime,
) -> dict[str, Any]:
    cards: dict[str, dict[str, Any]] = {}

    # For each binance symbol, derive: spot (≈ index), perp funding
    # annualized, dated futures carry annualized.
    for sym, basis_rows in binance.basis.items():
        if not basis_rows:
            continue
        latest = basis_rows[-1]
        index_price = latest["index_price"]
        ccy = sym.replace("USDT", "")  # BTCUSDT -> BTC

        funding_rows = binance.funding.get(sym, [])
        fund_8h = funding_rows[-1]["funding_rate"] if funding_rows else None
        ann_fund = (
            float(annualized_funding(pd.Series([fund_8h])).iloc[0])
            if fund_8h is not None
            else None
        )

        # Funding history series (last 200 rows, annualized).
        history = []
        if funding_rows:
            f_series = pd.Series([row["funding_rate"] for row in funding_rows])
            ann_series = annualized_funding(f_series)
            for row, ann in zip(funding_rows, ann_series, strict=False):
                history.append(
                    {
                        "ts": row["funding_time"],
                        "annualized_funding": float(ann),
                    }
                )

        # Dated futures carry from Deribit (closest to spot we have).
        dated_carries = []
        for f in deribit_futures:
            if (
                f.asset_kind is AssetKind.FUTURE
                and f.currency.value == ccy
                and f.expiry is not None
            ):
                days = max((f.expiry - asof).total_seconds() / 86400.0, 1.0)
                try:
                    carry = annualized_carry(index_price, f.mark_price, days)
                except ValueError:
                    continue
                dated_carries.append(
                    {
                        "expiry": f.expiry.isoformat(),
                        "days_to_expiry": days,
                        "future_price": f.mark_price,
                        "annualized_carry": carry,
                    }
                )

        cards[sym] = {
            "currency": ccy,
            "index_price": index_price,
            "perp_annualized_funding": ann_fund,
            "perp_funding_history": history,
            "dated_carry": dated_carries,
        }

    return {"cards": cards}


def _build_signals(carry: dict[str, Any]) -> dict[str, Any]:
    """Compute current snapshot of the three headline signals.

    Without a long history we cannot compute true rolling percentile
    ranks, so the snapshot mode reports the *raw* inputs and a simple
    z-score-style normalization where possible. This is a known MVP
    limitation; the full percentile ranks light up once the snapshot
    has been running for a few weeks.
    """
    cards = carry.get("cards", {})
    summary: list[dict[str, Any]] = []
    for sym, card in cards.items():
        ann_fund = card.get("perp_annualized_funding")
        dated = card.get("dated_carry") or []
        avg_dated_carry = (
            sum(d["annualized_carry"] for d in dated) / len(dated) if dated else None
        )
        summary.append(
            {
                "symbol": sym,
                "currency": card.get("currency"),
                "perp_annualized_funding": ann_fund,
                "average_dated_carry": avg_dated_carry,
                "carry_vol_divergence": (
                    _safe_diff(ann_fund, avg_dated_carry)
                    if ann_fund is not None and avg_dated_carry is not None
                    else None
                ),
            }
        )

    return {
        "as_of_snapshot": True,
        "note": (
            "MVP snapshot mode: full rolling-percentile signals unlock once "
            "the historical snapshot store has accumulated several weeks of "
            "data."
        ),
        "summary": summary,
    }


def _safe_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    if math.isnan(a) or math.isnan(b):
        return None
    return float(a - b)


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=str)


async def _run_snapshot_async(data_dir: Path) -> SnapshotResult:
    asof = datetime.now(tz=UTC)

    # 1) Live pulls in parallel.
    btc_task = asyncio.create_task(_pull_deribit("BTC", asof))
    eth_task = asyncio.create_task(_pull_deribit("ETH", asof))
    binance_task = asyncio.create_task(_pull_binance(["BTCUSDT", "ETHUSDT"]))
    (btc_opts, btc_futs), (eth_opts, eth_futs), binance = await asyncio.gather(
        btc_task, eth_task, binance_task
    )

    deribit_options = btc_opts + eth_opts
    deribit_futures = btc_futs + eth_futs

    # 2) Persist tickers via TimeSeriesStore (Parquet).
    parquet_dir = data_dir / "parquet"
    store = TimeSeriesStore(parquet_dir)
    parquet_paths = store.write_snapshots(deribit_options + deribit_futures)

    # 3) Build artifacts.
    overview = _build_overview(binance, deribit_futures)
    vol = _build_vol(deribit_options, deribit_futures, asof)
    carry = _build_carry(binance, deribit_futures, asof)
    signals = _build_signals(carry)
    meta = {
        "generated_at": asof.isoformat(),
        "deribit_options": len(deribit_options),
        "deribit_futures": len(deribit_futures),
        "binance_symbols": sorted(binance.funding.keys()),
        "binance_funding_rows": sum(len(v) for v in binance.funding.values()),
    }

    artifacts = data_dir / "artifacts"
    _write_json(artifacts / "meta.json", meta)
    _write_json(artifacts / "overview.json", overview)
    _write_json(artifacts / "vol.json", vol)
    _write_json(artifacts / "carry.json", carry)
    _write_json(artifacts / "signals.json", signals)

    return SnapshotResult(
        generated_at=asof,
        deribit_tickers=len(deribit_options) + len(deribit_futures),
        binance_funding_rows=meta["binance_funding_rows"],
        artifacts_dir=artifacts,
        parquet_paths=parquet_paths,
    )


def run_snapshot(data_dir: Path | str = DEFAULT_DATA_DIR) -> SnapshotResult:
    """Synchronous entry point. Runs one snapshot end-to-end."""
    return asyncio.run(_run_snapshot_async(Path(data_dir)))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory under which artifacts/ and parquet/ are written.",
    )
    args = parser.parse_args()
    result = run_snapshot(args.data_dir)
    print(  # noqa: T201
        f"snapshot ok: {result.deribit_tickers} deribit tickers, "
        f"{result.binance_funding_rows} binance funding rows -> "
        f"{result.artifacts_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
