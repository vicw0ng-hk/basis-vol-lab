"""Annualized carry computation."""


def annualized_carry(
    spot: float,
    future: float,
    days_to_expiry: float,
) -> float:
    """Compute annualized carry (basis) between spot and a future.

    Args:
        spot: Current spot price.
        future: Current futures price.
        days_to_expiry: Days until futures expiry.

    Returns:
        Annualized carry as a decimal (e.g. 0.12 for 12%).

    Raises:
        ValueError: If spot is non-positive or days_to_expiry is non-positive.
    """
    if spot <= 0:
        msg = "spot must be positive"
        raise ValueError(msg)
    if days_to_expiry <= 0:
        msg = "days_to_expiry must be positive"
        raise ValueError(msg)
    basis = (future - spot) / spot
    return basis * (365.0 / days_to_expiry)
