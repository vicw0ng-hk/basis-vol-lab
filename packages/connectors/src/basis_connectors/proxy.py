"""Proxy rotation utility for geo-blocked endpoints.

Reads a list of proxy URLs from the ``BASIS_PROXY_URLS`` environment variable
(newline- or comma-separated) and provides round-robin selection.
"""

from __future__ import annotations

import os
import random


def get_proxy_url() -> str | None:
    """Return a randomly-selected proxy URL from the environment, or None.

    The ``BASIS_PROXY_URLS`` variable may contain one or more proxy URLs
    separated by commas or newlines.  Each entry should be a full URL like
    ``http://user:pass@host:port``.
    """
    raw = os.environ.get("BASIS_PROXY_URLS", "").strip()
    if not raw:
        return None

    # Support both comma and newline separators.
    urls = [u.strip() for u in raw.replace(",", "\n").splitlines() if u.strip()]
    if not urls:
        return None

    return random.choice(urls)  # noqa: S311 – not security-sensitive
