"""Benchmark implied-volatility inversion at various chain sizes.

Compares the element-wise Brent loop (`implied_vol_array`) against a
scalar baseline and a multiprocessing variant to quantify the cost of
the Python loop and potential speed-up from parallelism.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
from basis_analytics import black76_price, implied_vol_array, implied_vol_black76
from numpy.typing import NDArray
from pytest_benchmark.fixture import BenchmarkFixture


def _make_prices(chain: dict[str, NDArray[np.float64]]) -> NDArray[np.float64]:
    """Generate market prices from the synthetic chain for IV round-trip."""
    return black76_price(
        chain["F"],
        chain["K"],
        chain["T"],
        chain["sigma"],
        is_call=chain["is_call"],
    )


# -- scalar loop (baseline) --------------------------------------------------


def _scalar_loop(
    prices: NDArray[np.float64],
    F: NDArray[np.float64],
    K: NDArray[np.float64],
    T: NDArray[np.float64],
    is_call: NDArray[np.float64],
) -> NDArray[np.float64]:
    n = len(prices)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        out[i] = implied_vol_black76(
            float(prices[i]),
            float(F[i]),
            float(K[i]),
            float(T[i]),
            is_call=bool(is_call[i]),
        )
    return out


def test_iv_scalar_loop(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    prices = _make_prices(option_chain)
    benchmark(
        _scalar_loop,
        prices,
        option_chain["F"],
        option_chain["K"],
        option_chain["T"],
        option_chain["is_call"],
    )


# -- implied_vol_array (current vectorized wrapper) ---------------------------


def test_iv_array(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    prices = _make_prices(option_chain)
    benchmark(
        implied_vol_array,
        prices,
        option_chain["F"],
        option_chain["K"],
        option_chain["T"],
        option_chain["is_call"],
    )


# -- ProcessPoolExecutor (CPU-parallel) --------------------------------------


def _solve_chunk(args: tuple[Any, ...]) -> NDArray[np.float64]:
    prices, F, K, T, is_call = args
    return implied_vol_array(prices, F, K, T, is_call)


def _parallel_iv(
    prices: NDArray[np.float64],
    F: NDArray[np.float64],
    K: NDArray[np.float64],
    T: NDArray[np.float64],
    is_call: NDArray[np.bool_],
    *,
    workers: int = 4,
) -> NDArray[np.float64]:
    n = len(prices)
    chunk_size = max(1, n // workers)
    chunks = []
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunks.append(
            (
                prices[start:end],
                F[start:end],
                K[start:end],
                T[start:end],
                is_call[start:end],
            )
        )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_solve_chunk, chunks))
    return np.concatenate(results)


def test_iv_parallel(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    prices = _make_prices(option_chain)
    benchmark(
        _parallel_iv,
        prices,
        option_chain["F"],
        option_chain["K"],
        option_chain["T"],
        option_chain["is_call"],
    )
