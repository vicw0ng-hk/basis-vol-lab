"""Pluggable artifact store for curated snapshot outputs.

The MVP wrote curated JSON artifacts (`meta.json`, `overview.json`, …)
to a local directory and read them back from the same path. Phase D of
the cloud rollout introduces the :class:`ArtifactStore` protocol so the
same orchestration code can run on a developer laptop (writing under
``data/``) or inside an AWS Lambda container (writing/reading against a
Cloudflare R2 bucket via the S3-compatible API).

Three concrete implementations live here:

* :class:`LocalArtifactStore` — current behaviour. Writes JSON under
  ``base_dir / "artifacts" / name`` and Parquet under
  ``base_dir / key`` (so ``key="parquet/deribit/.../tickers.parquet"``
  lands at the same location as :class:`basis_persistence.TimeSeriesStore`
  expects). Used by the CLI and ``mise run snapshot``.
* :class:`R2ArtifactStore` — boto3 against the R2 S3-compatible
  endpoint. JSON keyed at ``{prefix}artifacts/{name}``, Parquet keyed at
  ``{prefix}{key}``. Used inside Lambda when
  ``BASIS_ARTIFACT_BACKEND=r2``.
* :class:`InMemoryArtifactStore` — round-tripping JSON via the standard
  library so tests stay hermetic without spinning up moto. The contract
  test in ``tests/test_storage.py`` exercises both this and the local
  store.

The :func:`store_from_env` factory inspects the same env vars Terraform
writes to the Lambda function (`BASIS_ARTIFACT_BACKEND`, `BASIS_DATA_DIR`,
`BASIS_R2_*`) and is the only entry point used by ``basis_api.main``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping


@runtime_checkable
class ArtifactStore(Protocol):
    """Read/write curated JSON artifacts and Parquet rollups.

    Two namespaces:

    * ``read_json``/``write_json`` operate on short JSON artifacts
      identified by a bare filename (e.g. ``"meta.json"``). The store
      decides where to put them.
    * ``write_parquet`` accepts a relative key (e.g.
      ``"parquet/deribit/2026-05-01/tickers.parquet"``) so the snapshot
      orchestrator can hand off bytes already produced by
      :class:`basis_persistence.TimeSeriesStore`.
    """

    def read_json(self, name: str) -> dict[str, Any]: ...

    def write_json(self, name: str, payload: Any) -> None: ...

    def write_parquet(self, key: str, data: bytes) -> None: ...


def _dump_json(payload: Any) -> str:
    """Canonical JSON serialisation shared by every backend."""
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


class LocalArtifactStore:
    """Filesystem-backed implementation. Mirrors the MVP layout."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)

    @property
    def base_dir(self) -> Path:
        return self._base

    @property
    def artifacts_dir(self) -> Path:
        return self._base / "artifacts"

    @property
    def parquet_dir(self) -> Path:
        return self._base / "parquet"

    def read_json(self, name: str) -> dict[str, Any]:
        path = self.artifacts_dir / name
        if not path.exists():
            raise FileNotFoundError(f"artifact {name!r} not found at {path}")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def write_json(self, name: str, payload: Any) -> None:
        path = self.artifacts_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump_json(payload), encoding="utf-8")

    def write_parquet(self, key: str, data: bytes) -> None:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def __repr__(self) -> str:
        return f"LocalArtifactStore({self._base})"


class InMemoryArtifactStore:
    """Hermetic test double — round-trips JSON exactly like a real store."""

    def __init__(self) -> None:
        self.json_blobs: dict[str, dict[str, Any]] = {}
        self.parquet_blobs: dict[str, bytes] = {}

    def read_json(self, name: str) -> dict[str, Any]:
        if name not in self.json_blobs:
            raise FileNotFoundError(f"artifact {name!r} not found in memory store")
        return self.json_blobs[name]

    def write_json(self, name: str, payload: Any) -> None:
        # Round-trip through the canonical serializer so callers see the
        # same coercions (datetime -> str, etc.) they'd get from disk.
        self.json_blobs[name] = json.loads(_dump_json(payload))

    def write_parquet(self, key: str, data: bytes) -> None:
        self.parquet_blobs[key] = bytes(data)


class R2ArtifactStore:
    """Cloudflare R2 backend over the S3-compatible API.

    R2 charges nothing for egress and is region-pinned to ``apac`` for
    this project (see ``infra/terraform/main.tf``). We rely on the
    standard botocore S3 client with a custom ``endpoint_url`` instead
    of taking a dependency on ``rclone``/``wrangler``.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret: str,
        prefix: str = "",
        region: str = "auto",
    ) -> None:
        # Lazy import keeps boto3 out of the local-dev install path; the
        # Lambda image installs the `cloud` extra explicitly.
        try:
            import boto3  # type: ignore[import-not-found]
            from botocore.config import Config  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised in cloud only
            raise ImportError(
                "R2ArtifactStore requires boto3. Install with "
                "`uv pip install 'basis-api[cloud]'`."
            ) from exc

        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret,
            region_name=region,
            # R2 wants SigV4 + path-style addressing.
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def _full_key(self, suffix: str) -> str:
        if self._prefix:
            return f"{self._prefix}/{suffix}"
        return suffix

    def read_json(self, name: str) -> dict[str, Any]:
        key = self._full_key(f"artifacts/{name}")
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except self._client.exceptions.NoSuchKey as exc:
            raise FileNotFoundError(
                f"artifact {name!r} not found at s3://{self._bucket}/{key}"
            ) from exc
        return json.loads(obj["Body"].read())

    def write_json(self, name: str, payload: Any) -> None:
        key = self._full_key(f"artifacts/{name}")
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=_dump_json(payload).encode("utf-8"),
            ContentType="application/json",
            CacheControl="public, max-age=30",
        )

    def write_parquet(self, key: str, data: bytes) -> None:
        s3_key = self._full_key(key)
        self._client.put_object(
            Bucket=self._bucket,
            Key=s3_key,
            Body=bytes(data),
            ContentType="application/octet-stream",
        )

    def __repr__(self) -> str:
        return f"R2ArtifactStore(s3://{self._bucket}/{self._prefix or ''})"


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise RuntimeError(
            f"BASIS_ARTIFACT_BACKEND=r2 requires environment variable {name}"
        )
    return value


def store_from_env(env: Mapping[str, str] | None = None) -> ArtifactStore:
    """Build the artifact store implied by environment configuration.

    Recognises:

    * ``BASIS_ARTIFACT_BACKEND`` — ``local`` (default) or ``r2``.
    * ``BASIS_DATA_DIR`` — local base directory (default ``data``).
    * ``BASIS_R2_ENDPOINT``, ``BASIS_R2_BUCKET``,
      ``BASIS_R2_ACCESS_KEY_ID``, ``BASIS_R2_SECRET_ACCESS_KEY`` — R2
      credentials. Optional ``BASIS_R2_PREFIX`` segments artifacts inside
      a shared bucket.
    """
    e = os.environ if env is None else env
    backend = e.get("BASIS_ARTIFACT_BACKEND", "local").lower()
    if backend == "local":
        return LocalArtifactStore(Path(e.get("BASIS_DATA_DIR", "data")))
    if backend == "r2":
        return R2ArtifactStore(
            endpoint=_require(e, "BASIS_R2_ENDPOINT"),
            bucket=_require(e, "BASIS_R2_BUCKET"),
            access_key=_require(e, "BASIS_R2_ACCESS_KEY_ID"),
            secret=_require(e, "BASIS_R2_SECRET_ACCESS_KEY"),
            prefix=e.get("BASIS_R2_PREFIX", ""),
        )
    raise RuntimeError(f"unknown BASIS_ARTIFACT_BACKEND={backend!r}")
