"""Tests for metadata_store_from_env factory."""

from __future__ import annotations

import pytest
from basis_persistence import MetadataStore, metadata_store_from_env


class TestMetadataStoreFromEnv:
    def test_default_returns_local_sqlite(self, tmp_path: object) -> None:
        from pathlib import Path

        data_dir = Path(str(tmp_path)) / "data"
        store = metadata_store_from_env({"BASIS_DATA_DIR": str(data_dir)})
        assert isinstance(store, MetadataStore)
        store.close()

    def test_local_backend_explicit(self, tmp_path: object) -> None:
        from pathlib import Path

        data_dir = Path(str(tmp_path)) / "data"
        store = metadata_store_from_env(
            {"BASIS_METADATA_BACKEND": "local", "BASIS_DATA_DIR": str(data_dir)}
        )
        assert isinstance(store, MetadataStore)
        store.close()

    def test_d1_missing_credentials_raises(self) -> None:
        with pytest.raises(RuntimeError, match="CF_ACCOUNT_ID"):
            metadata_store_from_env({"BASIS_METADATA_BACKEND": "d1"})

    def test_d1_with_all_credentials(self) -> None:
        from basis_persistence import D1MetadataStore

        store = metadata_store_from_env(
            {
                "BASIS_METADATA_BACKEND": "d1",
                "CF_ACCOUNT_ID": "acct",
                "CF_D1_DATABASE_ID": "db",
                "CF_API_TOKEN": "token",
            }
        )
        assert isinstance(store, D1MetadataStore)
        store.close()
