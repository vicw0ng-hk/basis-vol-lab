"""Benchmark vectorized Black-76 Greeks throughput."""

from __future__ import annotations

from typing import Any

import numpy as np
from basis_analytics import black76_greeks
from basis_analytics.pricing import black76_price
from numpy.typing import NDArray
from pytest_benchmark.fixture import BenchmarkFixture


def test_greeks_throughput(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    """Vectorized Greeks computation at chain_size scale."""
    benchmark(
        black76_greeks,
        option_chain["F"],
        option_chain["K"],
        option_chain["T"],
        option_chain["sigma"],
        is_call=option_chain["is_call"],
    )


def test_pricing_throughput(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    """Vectorized Black-76 pricing at chain_size scale."""
    benchmark(
        black76_price,
        option_chain["F"],
        option_chain["K"],
        option_chain["T"],
        option_chain["sigma"],
        is_call=option_chain["is_call"],
    )


def test_greeks_scalar_loop(
    benchmark: BenchmarkFixture,
    option_chain: dict[str, Any],
) -> None:
    """Scalar loop baseline for Greek computation."""
    F = option_chain["F"]
    K = option_chain["K"]
    T = option_chain["T"]
    sigma = option_chain["sigma"]
    is_call = option_chain["is_call"]

    def _loop() -> None:
        for i in range(len(F)):
            black76_greeks(
                float(F[i]),
                float(K[i]),
                float(T[i]),
                float(sigma[i]),
                is_call=bool(is_call[i]),
            )

    benchmark(_loop)


# -- Smile interpolation throughput -------------------------------------------


def _build_smile() -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    strikes = np.linspace(40_000, 120_000, 50)
    ivs = 0.6 + 0.1 * ((strikes - 70_000) / 30_000) ** 2
    return strikes, ivs


def test_smile_interp_build(benchmark: BenchmarkFixture) -> None:
    """Build PCHIP smile interpolator from 50 strikes."""
    from basis_analytics import smile_interp

    strikes, ivs = _build_smile()
    benchmark(smile_interp, strikes, ivs)


def test_smile_interp_eval(benchmark: BenchmarkFixture) -> None:
    """Evaluate PCHIP smile at 1000 query strikes."""
    from basis_analytics import smile_interp

    strikes, ivs = _build_smile()
    interp = smile_interp(strikes, ivs)
    query = np.linspace(35_000, 125_000, 1_000)
    benchmark(interp, query)
