"""Entry point for local development."""

from basis_contracts import Venue


def main() -> None:
    """Print supported venues."""
    for venue in Venue:
        print(f"Supported venue: {venue}")


if __name__ == "__main__":
    main()
