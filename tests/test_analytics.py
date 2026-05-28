"""Tests for basis_analytics carry computation."""

import math
from datetime import UTC, datetime

import pandas as pd
import pytest
from basis_analytics import annualized_carry, annualized_funding, basis_curve


def test_annualized_carry_basic() -> None:
    # Future at 102k, spot at 100k, 30 days to expiry
    result = annualized_carry(spot=100_000, future=102_000, days_to_expiry=30)
    # (2000/100000) * (365/30) = 0.02 * 12.1667 ≈ 0.2433
    assert abs(result - 0.24333) < 0.001


def test_annualized_carry_contango() -> None:
    result = annualized_carry(spot=50_000, future=51_000, days_to_expiry=90)
    assert result > 0  # Contango → positive carry


def test_annualized_carry_backwardation() -> None:
    result = annualized_carry(spot=50_000, future=49_000, days_to_expiry=90)
    assert result < 0  # Backwardation → negative carry


def test_annualized_carry_invalid_spot() -> None:
    with pytest.raises(ValueError, match="spot must be positive"):
        annualized_carry(spot=0, future=100, days_to_expiry=30)


def test_annualized_carry_invalid_days() -> None:
    with pytest.raises(ValueError, match="days_to_expiry must be positive"):
        annualized_carry(spot=100, future=102, days_to_expiry=0)


def test_annualized_funding_compounds_correctly() -> None:
    s = pd.Series([0.0001, 0.0, -0.0001])
    out = annualized_funding(s)
    expected_first = (1.0 + 0.0001) ** (3 * 365) - 1
    assert math.isclose(float(out.iloc[0]), expected_first, rel_tol=1e-12)
    assert float(out.iloc[1]) == 0.0
    assert float(out.iloc[2]) < 0.0


def test_basis_curve_happy_path() -> None:
    asof = datetime(2025, 1, 1, tzinfo=UTC)
    expiries = [
        datetime(2025, 3, 28, tzinfo=UTC),
        datetime(2025, 6, 27, tzinfo=UTC),
        datetime(2024, 12, 31, tzinfo=UTC),  # past — excluded
    ]
    futures = [102_000.0, 105_000.0, 99_000.0]
    df = basis_curve(futures, expiries, spot=100_000.0, asof=asof)
    assert len(df) == 2
    # First expiry: ~86 days
    first = df.iloc[0]
    assert first["future"] == 102_000.0
    assert 80 < first["days"] < 90
    assert first["annualized_carry"] > 0
