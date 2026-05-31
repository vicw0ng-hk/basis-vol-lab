"""Shared fixtures for performance benchmarks."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray


@pytest.fixture(params=[100, 1_000, 10_000], ids=["n=100", "n=1k", "n=10k"])
def chain_size(request: pytest.FixtureRequest) -> int:
    return request.param


@pytest.fixture()
def option_chain(chain_size: int) -> dict[str, NDArray[np.float64]]:
    """Synthetic option chain with realistic BTC parameters."""
    rng = np.random.default_rng(42)
    F = np.full(chain_size, 70_000.0)
    K = rng.uniform(40_000.0, 120_000.0, size=chain_size)
    T = rng.uniform(0.02, 1.0, size=chain_size)
    sigma = rng.uniform(0.3, 1.2, size=chain_size)
    is_call = rng.choice([True, False], size=chain_size)
    return {"F": F, "K": K, "T": T, "sigma": sigma, "is_call": is_call}
