"""Tests for D1MetadataStore.

We don't speak to a live D1 — the assertions verify the SQL/params we
emit on the HTTP wire. ``httpx.MockTransport`` lets us assert the
exact request body shapes without a network round-trip.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from basis_contracts import AssetKind, CollectionRun, Currency, Instrument, Venue
from basis_persistence import D1MetadataStore


def _envelope(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "result": [
            {
                "results": rows or [],
                "success": True,
                "meta": {"duration": 0.1},
            }
        ],
        "errors": [],
        "messages": [],
    }


@pytest.fixture
def captured() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def store(captured: list[dict[str, Any]]) -> D1MetadataStore:
    pending: list[list[dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured.append(body)
        rows = pending.pop(0) if pending else []
        return httpx.Response(200, json=_envelope(rows))

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://api.cloudflare.com")
    store = D1MetadataStore(
        account_id="acct123",
        database_id="db456",
        api_token="token-xyz",
        client=client,
    )
    store._pending = pending  # type: ignore[attr-defined]
    return store


class TestUpsertInstrument:
    def test_emits_expected_sql_and_params(
        self, store: D1MetadataStore, captured: list[dict[str, Any]]
    ) -> None:
        inst = Instrument(
            venue=Venue.DERIBIT,
            symbol="BTC-PERPETUAL",
            currency=Currency.BTC,
            asset_kind=AssetKind.PERPETUAL,
        )
        store.upsert_instrument(inst)
        assert len(captured) == 1
        sent = captured[0]
        assert "INSERT INTO instruments" in sent["sql"]
        assert "ON CONFLICT(venue, symbol)" in sent["sql"]
        assert sent["params"] == [
            "deribit",
            "BTC-PERPETUAL",
            "BTC",
            "perpetual",
            None,
            None,
            1,
        ]


class TestGetInstruments:
    def test_filters_compose_to_where_clause(
        self, store: D1MetadataStore, captured: list[dict[str, Any]]
    ) -> None:
        store._pending.append(  # type: ignore[attr-defined]
            [
                {
                    "venue": "deribit",
                    "symbol": "ETH-28JUN26-4000-C",
                    "currency": "ETH",
                    "asset_kind": "option",
                    "expiry": "2026-06-28T00:00:00+00:00",
                    "strike": 4000.0,
                    "is_active": 1,
                }
            ]
        )
        results = store.get_instruments(
            venue=Venue.DERIBIT,
            currency=Currency.ETH,
            asset_kind=AssetKind.OPTION,
        )
        assert len(results) == 1
        assert results[0].strike == 4000.0
        assert results[0].expiry == datetime(2026, 6, 28, tzinfo=UTC)

        sent = captured[0]
        assert "venue = ?" in sent["sql"]
        assert "currency = ?" in sent["sql"]
        assert "asset_kind = ?" in sent["sql"]
        assert "is_active = 1" in sent["sql"]
        assert sent["params"] == ["deribit", "ETH", "option"]

    def test_no_filters_no_where_clause(
        self, store: D1MetadataStore, captured: list[dict[str, Any]]
    ) -> None:
        store.get_instruments(active_only=False)
        assert "WHERE" not in captured[0]["sql"]


class TestRuns:
    def test_insert_and_finish_roundtrip(
        self, store: D1MetadataStore, captured: list[dict[str, Any]]
    ) -> None:
        run = CollectionRun(
            run_id="run-001",
            venue=Venue.BINANCE,
            started_at=datetime(2026, 5, 1, 12, tzinfo=UTC),
        )
        store.insert_run(run)
        store.finish_run(
            "run-001",
            ended_at=datetime(2026, 5, 1, 12, 5, tzinfo=UTC),
            status="completed",
            records_collected=42,
        )
        assert len(captured) == 2
        assert "INSERT INTO collection_runs" in captured[0]["sql"]
        assert captured[0]["params"][0] == "run-001"
        assert "UPDATE collection_runs" in captured[1]["sql"]
        assert captured[1]["params"] == [
            "2026-05-01T12:05:00+00:00",
            "completed",
            42,
            "run-001",
        ]


class TestErrors:
    def test_failure_envelope_raises(self, captured: list[dict[str, Any]]) -> None:
        del captured  # unused; we replace transport entirely

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "success": False,
                    "errors": [{"code": 7500, "message": "boom"}],
                    "result": [],
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        store = D1MetadataStore(
            account_id="a", database_id="b", api_token="t", client=client
        )
        with pytest.raises(RuntimeError, match="D1 query failed"):
            store.get_instruments()

    def test_authorization_header_set(self) -> None:
        sniffed: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            sniffed.update(request.headers)
            return httpx.Response(200, json=_envelope())

        client = httpx.Client(transport=httpx.MockTransport(handler))
        store = D1MetadataStore(
            account_id="a", database_id="b", api_token="my-token", client=client
        )
        store.get_instruments()
        assert sniffed["authorization"] == "Bearer my-token"
