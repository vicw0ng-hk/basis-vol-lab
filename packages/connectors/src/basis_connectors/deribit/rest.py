"""Async REST client for Deribit public endpoints."""

from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType
from typing import Any, Self

import httpx
from basis_contracts import AssetKind, Currency, Instrument

from basis_connectors.deribit.parsers import parse_instrument

DEFAULT_BASE_URL = "https://www.deribit.com/api/v2"

_KIND_TO_DERIBIT: dict[AssetKind, str] = {
    AssetKind.OPTION: "option",
    AssetKind.FUTURE: "future",
    AssetKind.PERPETUAL: "future",  # Deribit perps live under kind=future
}


class DeribitRestClient:
    """Thin async client for Deribit public REST endpoints.

    Use as an async context manager so the underlying ``httpx.AsyncClient`` is
    always closed:

    ```python
    async with DeribitRestClient() as client:
        instruments = await client.get_instruments(Currency.BTC)
    ```
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_instruments(
        self,
        currency: Currency,
        *,
        kinds: Iterable[AssetKind] | None = None,
        expired: bool = False,
    ) -> list[Instrument]:
        """Fetch active (or expired) instruments for ``currency``.

        Args:
            currency: Underlying currency (BTC or ETH).
            kinds: Optional restriction on Deribit ``kind``. Defaults to all
                supported kinds (option, future, perpetual).
            expired: If True, fetch expired instruments instead of active ones.
        """
        kinds = list(kinds) if kinds is not None else list(_KIND_TO_DERIBIT.keys())
        deribit_kinds = {_KIND_TO_DERIBIT[k] for k in kinds}

        results: list[Instrument] = []
        for deribit_kind in sorted(deribit_kinds):
            payload = await self._get(
                "/public/get_instruments",
                params={
                    "currency": currency.value,
                    "kind": deribit_kind,
                    "expired": "true" if expired else "false",
                },
            )
            for raw in payload.get("result", []):
                inst = parse_instrument(raw)
                if inst is None:
                    continue
                if inst.asset_kind not in kinds:
                    continue
                results.append(inst)
        return results

    async def _get(self, path: str, *, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data
