"""Tests for basis_analytics carry computation."""

import pytest
from basis_analytics import annualized_carry


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
