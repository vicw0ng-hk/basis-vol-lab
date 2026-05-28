"""Cloudflare D1 metadata store.

D1 is SQLite-compatible behind a REST API. This sibling of
:class:`MetadataStore` exposes the same surface — instrument upserts /
queries and collection-run tracking — but talks to the D1 HTTP endpoint
instead of an on-disk SQLite database.

Used by ``basis_api`` when it runs inside Lambda
(``BASIS_METADATA_BACKEND=d1``). Local development keeps using
:class:`MetadataStore`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from basis_contracts.enums import AssetKind, Currency, Venue
from basis_contracts.models import CollectionRun, Instrument

if TYPE_CHECKING:
    import httpx


def _ts_to_text(dt: datetime | None) -> str | None:
    return None if dt is None else dt.isoformat()


def _text_to_ts(text: str | None) -> datetime | None:
    if text is None:
        return None
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class D1MetadataStore:
    """REST-backed metadata store against a Cloudflare D1 database.

    Args:
        account_id: Cloudflare account ID.
        database_id: D1 database UUID (``cloudflare_d1_database.id`` in
            Terraform).
        api_token: API token with the ``D1:Edit`` scope.
        client: Optional pre-built ``httpx.Client`` for tests / connection
            reuse. The store does **not** close clients it didn't create.
    """

    _ENDPOINT_TEMPLATE = (
        "https://api.cloudflare.com/client/v4/accounts/{account_id}"
        "/d1/database/{database_id}/query"
    )

    def __init__(
        self,
        *,
        account_id: str,
        database_id: str,
        api_token: str,
        client: httpx.Client | None = None,
    ) -> None:
        try:
            import httpx as _httpx  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - cloud-only path
            raise ImportError(
                "D1MetadataStore requires httpx. Install with "
                "`uv pip install 'basis-persistence[cloud]'`."
            ) from exc

        self._endpoint = self._ENDPOINT_TEMPLATE.format(
            account_id=account_id, database_id=database_id
        )
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        self._owns_client = client is None
        self._client = client if client is not None else _httpx.Client(timeout=15.0)

    # ── HTTP helpers ─────────────────────────────────────────────

    def _query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute a single SQL statement and return its result rows.

        D1's ``/query`` endpoint returns
        ``{"result": [{"results": [...rows...], "success": true, ...}]}``.
        """
        body = {"sql": sql, "params": params or []}
        response = self._client.post(self._endpoint, headers=self._headers, json=body)
        response.raise_for_status()
        envelope = response.json()
        if not envelope.get("success"):
            raise RuntimeError(f"D1 query failed: {envelope.get('errors')}")
        results = envelope.get("result") or []
        if not results:
            return []
        first = results[0]
        if not first.get("success", True):
            raise RuntimeError(f"D1 statement failed: {first}")
        rows = first.get("results") or []
        return list(rows)

    # ── instruments ──────────────────────────────────────────────

    def upsert_instrument(self, inst: Instrument) -> None:
        self._query(
            """
            INSERT INTO instruments
                (venue, symbol, currency, asset_kind,
                 expiry, strike, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(venue, symbol) DO UPDATE SET
                currency   = excluded.currency,
                asset_kind = excluded.asset_kind,
                expiry     = excluded.expiry,
                strike     = excluded.strike,
                is_active  = excluded.is_active
            """,
            [
                inst.venue.value,
                inst.symbol,
                inst.currency.value,
                inst.asset_kind.value,
                _ts_to_text(inst.expiry),
                inst.strike,
                int(inst.is_active),
            ],
        )

    def get_instruments(
        self,
        venue: Venue | None = None,
        currency: Currency | None = None,
        asset_kind: AssetKind | None = None,
        active_only: bool = True,
    ) -> list[Instrument]:
        clauses: list[str] = []
        params: list[Any] = []
        if venue is not None:
            clauses.append("venue = ?")
            params.append(venue.value)
        if currency is not None:
            clauses.append("currency = ?")
            params.append(currency.value)
        if asset_kind is not None:
            clauses.append("asset_kind = ?")
            params.append(asset_kind.value)
        if active_only:
            clauses.append("is_active = 1")

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._query(
            "SELECT venue, symbol, currency, asset_kind, expiry, strike, is_active "
            f"FROM instruments{where}",
            params,
        )
        return [
            Instrument(
                venue=Venue(r["venue"]),
                symbol=r["symbol"],
                currency=Currency(r["currency"]),
                asset_kind=AssetKind(r["asset_kind"]),
                expiry=_text_to_ts(r["expiry"]),
                strike=r["strike"],
                is_active=bool(r["is_active"]),
            )
            for r in rows
        ]

    # ── collection runs ──────────────────────────────────────────

    def insert_run(self, run: CollectionRun) -> None:
        self._query(
            """
            INSERT INTO collection_runs
                (run_id, venue, started_at, ended_at,
                 status, records_collected)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                run.run_id,
                run.venue.value,
                _ts_to_text(run.started_at),
                _ts_to_text(run.ended_at),
                run.status,
                run.records_collected,
            ],
        )

    def finish_run(
        self,
        run_id: str,
        *,
        ended_at: datetime,
        status: str = "completed",
        records_collected: int = 0,
    ) -> None:
        self._query(
            """
            UPDATE collection_runs
            SET ended_at = ?, status = ?, records_collected = ?
            WHERE run_id = ?
            """,
            [_ts_to_text(ended_at), status, records_collected, run_id],
        )

    def get_runs(self, venue: Venue | None = None) -> list[CollectionRun]:
        if venue is not None:
            rows = self._query(
                "SELECT run_id, venue, started_at, ended_at, status, "
                "records_collected FROM collection_runs WHERE venue = ? "
                "ORDER BY started_at DESC",
                [venue.value],
            )
        else:
            rows = self._query(
                "SELECT run_id, venue, started_at, ended_at, status, "
                "records_collected FROM collection_runs ORDER BY started_at DESC"
            )
        return [
            CollectionRun(
                run_id=r["run_id"],
                venue=Venue(r["venue"]),
                started_at=_text_to_ts(r["started_at"]),  # type: ignore[ty:invalid-argument-type]
                ended_at=_text_to_ts(r["ended_at"]),
                status=r["status"],
                records_collected=r["records_collected"],
            )
            for r in rows
        ]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
