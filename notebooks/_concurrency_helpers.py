"""Picklable helpers for the concurrency-patterns notebook.

ProcessPoolExecutor on macOS uses the *spawn* start method, so worker
functions must be importable from a real module — not ``__main__``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from basis_analytics import implied_vol_array
from numpy.typing import NDArray


def solve_chunk(args: tuple[Any, ...]) -> NDArray[np.float64]:
    """Solve IV for a single array slice."""
    prices, f, k, t, is_call = args  # noqa: N806
    return implied_vol_array(prices, f, k, t, is_call)
