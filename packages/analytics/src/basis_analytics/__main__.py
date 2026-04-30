"""``python -m basis_analytics`` entry point.

Runs the IV-validation report against live Deribit. See
``basis_analytics.validate`` for details.
"""

from basis_analytics.validate import main

if __name__ == "__main__":
    raise SystemExit(main())
