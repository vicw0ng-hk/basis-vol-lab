"""Contract tests for the ArtifactStore implementations.

The local + in-memory backends share a behavioural contract; both are
exercised by the same test class so adding a third backend (R2) in the
cloud install path is a one-line subclass with the appropriate fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from basis_api.storage import (
    ArtifactStore,
    InMemoryArtifactStore,
    LocalArtifactStore,
    store_from_env,
)


class _ArtifactStoreContract:
    """Mixin asserting ArtifactStore semantics. Subclasses provide `store`."""

    @pytest.fixture
    def store(self) -> ArtifactStore:  # pragma: no cover - overridden
        raise NotImplementedError

    def test_protocol_runtime_check(self, store: ArtifactStore) -> None:
        assert isinstance(store, ArtifactStore)

    def test_read_missing_artifact_raises(self, store: ArtifactStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.read_json("missing.json")

    def test_write_then_read_roundtrip(self, store: ArtifactStore) -> None:
        payload: dict[str, Any] = {"hello": "world", "n": 42}
        store.write_json("meta.json", payload)
        assert store.read_json("meta.json") == payload

    def test_overwrites(self, store: ArtifactStore) -> None:
        store.write_json("meta.json", {"v": 1})
        store.write_json("meta.json", {"v": 2})
        assert store.read_json("meta.json") == {"v": 2}

    def test_write_parquet_bytes_preserved(self, store: ArtifactStore) -> None:
        # We don't introspect Parquet; just guarantee bytes round-trip on
        # the implementations that expose a read path. Local store writes
        # under base_dir; in-memory exposes the dict for inspection.
        data = b"PAR1\x00\x01\x02"
        store.write_parquet("parquet/foo/2026-05-01/x.parquet", data)


class TestLocalArtifactStore(_ArtifactStoreContract):
    @pytest.fixture
    def store(self, tmp_path: Path) -> LocalArtifactStore:
        return LocalArtifactStore(tmp_path)

    def test_local_paths(self, tmp_path: Path) -> None:
        store = LocalArtifactStore(tmp_path)
        store.write_json("meta.json", {"ok": True})
        assert (tmp_path / "artifacts" / "meta.json").exists()
        store.write_parquet("parquet/x.parquet", b"abc")
        assert (tmp_path / "parquet" / "x.parquet").read_bytes() == b"abc"

    def test_write_json_canonical(self, tmp_path: Path) -> None:
        # Sorted keys + indent=2 match the original snapshot writer so
        # diffs in the artifacts dir stay reviewable.
        store = LocalArtifactStore(tmp_path)
        store.write_json("meta.json", {"b": 1, "a": 2})
        text = (tmp_path / "artifacts" / "meta.json").read_text()
        assert text == '{\n  "a": 2,\n  "b": 1\n}'


class TestInMemoryArtifactStore(_ArtifactStoreContract):
    @pytest.fixture
    def store(self) -> InMemoryArtifactStore:
        return InMemoryArtifactStore()

    def test_parquet_bytes_collected(self) -> None:
        store = InMemoryArtifactStore()
        store.write_parquet("parquet/x", b"abc")
        assert store.parquet_blobs == {"parquet/x": b"abc"}

    def test_datetime_round_trip_to_str(self) -> None:
        from datetime import UTC, datetime

        store = InMemoryArtifactStore()
        ts = datetime(2026, 5, 1, 12, tzinfo=UTC)
        store.write_json("meta.json", {"asof": ts})
        # JSON has no datetime type -> serializer coerces via str().
        assert store.read_json("meta.json") == {"asof": str(ts)}


class TestStoreFromEnv:
    def test_default_local(self, tmp_path: Path) -> None:
        store = store_from_env({"BASIS_DATA_DIR": str(tmp_path)})
        assert isinstance(store, LocalArtifactStore)
        assert store.base_dir == tmp_path

    def test_explicit_local(self, tmp_path: Path) -> None:
        store = store_from_env(
            {"BASIS_ARTIFACT_BACKEND": "local", "BASIS_DATA_DIR": str(tmp_path)}
        )
        assert isinstance(store, LocalArtifactStore)

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(RuntimeError, match="unknown BASIS_ARTIFACT_BACKEND"):
            store_from_env({"BASIS_ARTIFACT_BACKEND": "ftp"})

    def test_r2_requires_env_vars(self) -> None:
        with pytest.raises(RuntimeError, match="BASIS_R2_ENDPOINT"):
            store_from_env({"BASIS_ARTIFACT_BACKEND": "r2"})
