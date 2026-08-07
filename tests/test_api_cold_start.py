"""Lambda cold-start budget for `basis_api.main`.

Importing the handler module runs inside Lambda's INIT phase, which is
capped at 10 s for on-demand (non-provisioned) functions. When init
overruns that cap Lambda kills it and re-runs the whole initialisation
inside the invoke, which then burns the 30 s function timeout and the
caller gets nothing back — the uptime probe saw `curl (28)` with
`INIT_REPORT ... Phase: invoke Status: timeout` in CloudWatch.

The analytics stack (pandas, pyarrow, scipy) is the bulk of that init
cost and none of it is needed to answer `/healthz`, so it must stay out
of module scope and be imported by the endpoints that actually use it.
"""

from __future__ import annotations

import json
import subprocess
import sys

# Together these cost roughly 1.8 s of a 10 s init budget on Graviton at
# 1024 MB, and no request to `/healthz` touches any of them.
#
# `pyarrow` arrives indirectly: `main.py` never imports it, but
# `basis_persistence/__init__` re-exports `TimeSeriesStore` from
# `timeseries`, which imports it at module scope. That package re-exports
# it lazily (PEP 562) so pulling `metadata_store_from_env` at init does
# not drag Parquet in with it.
HEAVY_MODULES = ("pandas", "scipy", "httpx", "pyarrow")


def _modules_after_importing_main() -> set[str]:
    """Top-level module names loaded by `import basis_api.main`.

    Runs in a subprocess so the result reflects a fresh interpreter (a
    Lambda cold start) rather than whatever the test session already
    imported.
    """
    code = (
        "import sys, json; import basis_api.main; "
        "print(json.dumps(sorted({m.split('.')[0] for m in sys.modules})))"
    )
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(json.loads(proc.stdout))


class TestColdStartImports:
    def test_handler_import_skips_analytics_stack(self) -> None:
        loaded = _modules_after_importing_main()
        offenders = sorted(set(HEAVY_MODULES) & loaded)
        assert not offenders, (
            f"{offenders} imported during Lambda INIT; import them inside the "
            "endpoints that need them to stay under the 10 s init cap"
        )

    def test_healthz_still_served(self) -> None:
        """Deferring imports must not break the probed endpoint."""
        from basis_api.main import app
        from fastapi.testclient import TestClient

        r = TestClient(app).get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
