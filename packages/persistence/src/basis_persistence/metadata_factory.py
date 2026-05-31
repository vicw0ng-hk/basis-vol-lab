"""Factory for metadata stores based on environment configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from basis_persistence.d1 import D1MetadataStore
from basis_persistence.metadata import MetadataStore


class MetadataStoreProtocol(Protocol):
    """Common interface for MetadataStore and D1MetadataStore."""

    def insert_run(self, run: object) -> None: ...
    def finish_run(
        self, run_id: str, *, ended_at: object, status: str, records_collected: int
    ) -> None: ...
    def get_runs(self, venue: object | None = None) -> list[object]: ...
    def close(self) -> None: ...


def metadata_store_from_env(
    env: Mapping[str, str] | None = None,
) -> MetadataStore | D1MetadataStore:
    """Build a metadata store from environment variables.

    When ``BASIS_METADATA_BACKEND=d1``, returns a :class:`D1MetadataStore`
    configured from ``CF_ACCOUNT_ID``, ``CF_D1_DATABASE_ID``, and
    ``CF_API_TOKEN``.  Otherwise returns a local :class:`MetadataStore`
    backed by SQLite.
    """
    e: Mapping[str, str] = os.environ if env is None else env
    backend = e.get("BASIS_METADATA_BACKEND", "local").lower()

    if backend == "d1":
        account_id = e.get("CF_ACCOUNT_ID", "")
        database_id = e.get("CF_D1_DATABASE_ID", "")
        api_token = e.get("CF_API_TOKEN", "")
        if not all([account_id, database_id, api_token]):
            raise RuntimeError(
                "BASIS_METADATA_BACKEND=d1 requires CF_ACCOUNT_ID, "
                "CF_D1_DATABASE_ID, and CF_API_TOKEN environment variables."
            )
        return D1MetadataStore(
            account_id=account_id,
            database_id=database_id,
            api_token=api_token,
        )

    # Default: local SQLite
    data_dir = Path(e.get("BASIS_DATA_DIR", "data"))
    db_path = data_dir / "metadata.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return MetadataStore(db_path)
