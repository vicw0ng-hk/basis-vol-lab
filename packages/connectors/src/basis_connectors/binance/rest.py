"""Async REST client for Binance USD-margined futures public endpoints."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx
from basis_contracts import Instrument

from basis_connectors.binance.parsers import (
    parse_basis_row,
    parse_exchange_info_symbol,
    parse_funding_rate_row,
    parse_oi_row,
)
from basis_connectors.binance.types import BasisRow, FundingRateRow, OpenInterestRow

DEFAULT_BASE_URL = "https://fapi.binance.com"

# Per Binance docs.
_FUNDING_LIMIT_MAX = 1000
_BASIS_LIMIT_MAX = 500
_OI_LIMIT_MAX = 500


class BinanceRestClient:
    """Thin async client for Binance futures public REST endpoints.

    Use as an async context manager so the underlying ``httpx.AsyncClient`` is
    always closed.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        proxy: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout, proxy=proxy)

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

    async def get_exchange_info(self) -> list[Instrument]:
        """Fetch supported instruments (BTC/ETH USDT perps + quarterlies)."""
        payload = await self._get("/fapi/v1/exchangeInfo", params={})
        symbols = payload.get("symbols", [])
        results: list[Instrument] = []
        for raw in symbols:
            inst = parse_exchange_info_symbol(raw)
            if inst is not None:
                results.append(inst)
        return results

    async def get_funding_rate_history(
        self,
        symbol: str,
        *,
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int = 100,
    ) -> list[FundingRateRow]:
        """Fetch historical funding-rate rows for ``symbol``."""
        params: dict[str, str] = {
            "symbol": symbol,
            "limit": str(min(limit, _FUNDING_LIMIT_MAX)),
        }
        if start_ms is not None:
            params["startTime"] = str(start_ms)
        if end_ms is not None:
            params["endTime"] = str(end_ms)
        rows = await self._get_list("/fapi/v1/fundingRate", params=params)
        return [parse_funding_rate_row(r) for r in rows]

    async def get_basis(
        self,
        pair: str,
        contract_type: str,
        *,
        period: str = "5m",
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int = 100,
    ) -> list[BasisRow]:
        """Fetch basis rows for ``pair`` + ``contract_type``."""
        params: dict[str, str] = {
            "pair": pair,
            "contractType": contract_type,
            "period": period,
            "limit": str(min(limit, _BASIS_LIMIT_MAX)),
        }
        if start_ms is not None:
            params["startTime"] = str(start_ms)
        if end_ms is not None:
            params["endTime"] = str(end_ms)
        rows = await self._get_list("/futures/data/basis", params=params)
        return [parse_basis_row(r) for r in rows]

    async def get_open_interest_hist(
        self,
        symbol: str,
        *,
        period: str = "5m",
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int = 100,
    ) -> list[OpenInterestRow]:
        """Fetch open-interest history rows for ``symbol``."""
        params: dict[str, str] = {
            "symbol": symbol,
            "period": period,
            "limit": str(min(limit, _OI_LIMIT_MAX)),
        }
        if start_ms is not None:
            params["startTime"] = str(start_ms)
        if end_ms is not None:
            params["endTime"] = str(end_ms)
        rows = await self._get_list("/futures/data/openInterestHist", params=params)
        return [parse_oi_row(r) for r in rows]

    async def _get(self, path: str, *, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def _get_list(
        self, path: str, *, params: dict[str, str]
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}{path}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        return data
