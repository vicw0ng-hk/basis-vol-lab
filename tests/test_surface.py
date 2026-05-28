"""Tests for `basis_analytics.surface`."""

from __future__ import annotations

import numpy as np
import pandas as pd
from basis_analytics import atm_term_structure, smile_interp


def test_atm_picks_closest_to_forward() -> None:
    df = pd.DataFrame(
        {
            "expiry": pd.to_datetime(
                ["2025-06-30", "2025-06-30", "2025-06-30", "2025-09-30"], utc=True
            ),
            "strike": [60_000, 70_000, 80_000, 70_000],
            "forward": [70_500, 70_500, 70_500, 75_000],
            "mark_iv": [0.70, 0.55, 0.60, 0.50],
        }
    )
    atm = atm_term_structure(df)
    assert len(atm) == 2
    jun = atm.loc[pd.Timestamp("2025-06-30", tz="UTC")]
    assert int(jun["strike"]) == 70_000
    sep = atm.loc[pd.Timestamp("2025-09-30", tz="UTC")]
    assert int(sep["strike"]) == 70_000


def test_smile_interp_monotone_passthrough() -> None:
    strikes = np.array([60_000.0, 70_000.0, 80_000.0])
    ivs = np.array([0.80, 0.60, 0.55])
    f = smile_interp(strikes, ivs)
    # At input nodes returns input values
    np.testing.assert_allclose(f(strikes), ivs)
    # Between nodes IV stays in [min, max] of neighbours
    mid = float(f(65_000.0))
    assert 0.60 <= mid <= 0.80


def test_smile_interp_extrapolates_flat() -> None:
    strikes = np.array([60_000.0, 70_000.0, 80_000.0])
    ivs = np.array([0.80, 0.60, 0.55])
    f = smile_interp(strikes, ivs)
    assert float(f(50_000.0)) == 0.80
    assert float(f(90_000.0)) == 0.55
