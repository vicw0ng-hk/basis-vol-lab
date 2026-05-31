"""Benchmark compute-only portions of the snapshot pipeline.

Network I/O is excluded — we benchmark the DataFrame construction,
analytics computations, and JSON serialization that happen after data
is fetched from the exchanges.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from basis_analytics import (
    atm_term_structure,
    close_to_close_rv,
    implied_vol_array,
    parkinson_rv,
)
from basis_analytics.carry import annualized_funding, basis_curve
from basis_analytics.pricing import black76_price
from pytest_benchmark.fixture import BenchmarkFixture

# -- Synthetic data generators ------------------------------------------------


def _make_option_df(n_expiries: int = 8, strikes_per_expiry: int = 40) -> pd.DataFrame:
    """Simulate a Deribit-like option snapshot DataFrame."""
    rng = np.random.default_rng(42)
    rows = []
    now = datetime.now(UTC)
    for i in range(n_expiries):
        expiry = now + timedelta(days=7 * (i + 1))
        forward = 70_000.0 + rng.normal(0, 500)
        for j in range(strikes_per_expiry):
            strike = 40_000.0 + j * 2_000.0
            iv = 0.5 + 0.15 * ((strike - forward) / 30_000) ** 2 + rng.normal(0, 0.02)
            rows.append(
                {
                    "expiry": expiry,
                    "strike": strike,
                    "forward": forward,
                    "mark_iv": max(iv, 0.05),
                    "is_call": j % 2 == 0,
                }
            )
    return pd.DataFrame(rows)


def _make_price_series(n: int = 2_000) -> pd.Series:
    """Simulate a BTC price series at 15-min intervals."""
    rng = np.random.default_rng(42)
    index = pd.date_range(end=datetime.now(UTC), periods=n, freq="15min", tz="UTC")
    log_returns = rng.normal(0, 0.002, size=n)
    prices = 70_000.0 * np.exp(np.cumsum(log_returns))
    return pd.Series(prices, index=index, name="close")


def _make_hl_series(
    n: int = 2_000,
) -> tuple[pd.Series, pd.Series]:
    """Simulate high/low series for Parkinson RV."""
    rng = np.random.default_rng(42)
    index = pd.date_range(end=datetime.now(UTC), periods=n, freq="15min", tz="UTC")
    base = 70_000.0 * np.exp(np.cumsum(rng.normal(0, 0.002, size=n)))
    spread = base * rng.uniform(0.001, 0.005, size=n)
    highs = pd.Series(base + spread, index=index, name="high")
    lows = pd.Series(base - spread, index=index, name="low")
    return highs, lows


# -- Benchmarks ---------------------------------------------------------------


def test_atm_term_structure(benchmark: BenchmarkFixture) -> None:
    """Extract ATM term structure from option snapshot."""
    df = _make_option_df()
    benchmark(atm_term_structure, df)


def test_iv_solve_chain(benchmark: BenchmarkFixture) -> None:
    """IV inversion on a full chain (8 expiries × 40 strikes = 320 options)."""
    df = _make_option_df()
    prices = black76_price(
        df["forward"].to_numpy(),
        df["strike"].to_numpy(),
        np.full(len(df), 0.25),
        df["mark_iv"].to_numpy(),
        is_call=df["is_call"].to_numpy(),
    )
    F = df["forward"].to_numpy()
    K = df["strike"].to_numpy()
    T = np.full(len(df), 0.25)
    is_call = df["is_call"].to_numpy()

    benchmark(implied_vol_array, prices, F, K, T, is_call)


def test_close_to_close_rv(benchmark: BenchmarkFixture) -> None:
    """Rolling close-to-close realized vol on 2000-bar series."""
    prices = _make_price_series()
    benchmark(close_to_close_rv, prices)


def test_parkinson_rv(benchmark: BenchmarkFixture) -> None:
    """Rolling Parkinson realized vol on 2000-bar high/low series."""
    highs, lows = _make_hl_series()
    benchmark(parkinson_rv, highs, lows)


def test_basis_curve(benchmark: BenchmarkFixture) -> None:
    """Basis curve computation for 8 futures."""
    rng = np.random.default_rng(42)
    now = datetime.now(UTC)
    spot = 70_000.0
    prices = [spot * (1 + rng.uniform(0.001, 0.05)) for _ in range(8)]
    expiries = [now + timedelta(days=7 * (i + 1)) for i in range(8)]
    benchmark(basis_curve, prices, expiries, spot=spot, asof=now)


def test_annualized_funding(benchmark: BenchmarkFixture) -> None:
    """Annualize 2000 8-hour funding rates."""
    rng = np.random.default_rng(42)
    rates = pd.Series(rng.normal(0.0001, 0.0005, size=2_000))
    benchmark(annualized_funding, rates)


def test_snapshot_json_serialize(benchmark: BenchmarkFixture) -> None:
    """JSON serialization of a typical snapshot artifact payload."""
    df = _make_option_df()
    atm = atm_term_structure(df)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "atm_term_structure": atm.reset_index().to_dict(orient="records"),
        "chain_size": len(df),
        "expiry_count": df["expiry"].nunique(),
    }

    def _serialize() -> str:
        return json.dumps(payload, default=str)

    benchmark(_serialize)
