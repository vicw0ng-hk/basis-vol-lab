"""Export pytest-benchmark JSON into a curated format for the web app.

Usage:
    uv run python scripts/export_benchmarks.py [--input FILE] [--output FILE]

Reads the raw pytest-benchmark JSON (default: runs benchmarks and captures
output) and writes a slim JSON file that the Vite build imports at compile
time.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Map test names to human-readable labels and categories.
BENCHMARK_META: dict[str, tuple[str, str]] = {
    # IV Inversion
    "test_iv_scalar_loop": ("Scalar loop (baseline)", "iv"),
    "test_iv_array": ("Vectorized (implied_vol_array)", "iv"),
    "test_iv_parallel": ("ProcessPoolExecutor (4 workers)", "iv"),
    # Greeks & Pricing
    "test_greeks_throughput": ("Vectorized Greeks", "greeks"),
    "test_pricing_throughput": ("Vectorized Black-76 pricing", "greeks"),
    "test_greeks_scalar_loop": ("Scalar loop Greeks (baseline)", "greeks"),
    "test_smile_interp_build": ("PCHIP smile build (50 strikes)", "greeks"),
    "test_smile_interp_eval": ("PCHIP smile eval (1k queries)", "greeks"),
    # Snapshot Pipeline
    "test_atm_term_structure": ("ATM term structure extraction", "snapshot"),
    "test_iv_solve_chain": ("IV solve (8 exp × 40 strikes)", "snapshot"),
    "test_close_to_close_rv": ("Close-to-close RV (2k bars)", "snapshot"),
    "test_parkinson_rv": ("Parkinson RV (2k bars)", "snapshot"),
    "test_basis_curve": ("Basis curve (8 futures)", "snapshot"),
    "test_annualized_funding": ("Annualize funding (2k rates)", "snapshot"),
    "test_snapshot_json_serialize": ("JSON serialize snapshot", "snapshot"),
}


def _strip_param(name: str) -> tuple[str, str | None]:
    """Split 'test_foo[n=1k]' into ('test_foo', 'n=1k')."""
    if "[" in name:
        base, param = name.rstrip("]").split("[", 1)
        return base, param
    return name, None


def run_benchmarks() -> dict:
    """Run pytest-benchmark and return the JSON output."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "benchmarks/",
            "--benchmark-only",
            "--benchmark-json=-",
            "--benchmark-sort=fullname",
            "-q",
            "-o",
            "addopts=",
            "-o",
            "python_files=bench_*.py",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Benchmarks failed (exit {result.returncode})")
    return json.loads(result.stdout)


def transform(raw: dict) -> dict:
    """Transform raw pytest-benchmark JSON into the web-friendly format."""
    machine = raw.get("machine_info", {})
    cpu_info = machine.get("cpu", {})

    hardware = {
        "cpu": cpu_info.get("brand_raw", "Unknown"),
        "arch": machine.get("machine", "unknown"),
        "cores": cpu_info.get("count", 0),
        "python": machine.get("python_version", "?"),
        "system": machine.get("system", "?"),
    }

    results: list[dict] = []
    for b in raw["benchmarks"]:
        base_name, param = _strip_param(b["name"])
        meta = BENCHMARK_META.get(base_name)
        if not meta:
            continue
        label, category = meta
        if param:
            label = f"{label} [{param}]"

        stats = b["stats"]
        results.append(
            {
                "name": b["name"],
                "label": label,
                "category": category,
                "param": param,
                "mean_ms": round(stats["mean"] * 1000, 3),
                "median_ms": round(stats["median"] * 1000, 3),
                "stddev_ms": round(stats["stddev"] * 1000, 3),
                "ops": round(stats["ops"], 1),
                "rounds": stats["rounds"],
            }
        )

    return {"hardware": hardware, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export benchmark data for the web app"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Read from existing pytest-benchmark JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "apps" / "web" / "src" / "data" / "benchmarks.json",
        help="Output path (default: apps/web/src/data/benchmarks.json)",
    )
    args = parser.parse_args()

    raw = json.loads(args.input.read_text()) if args.input else run_benchmarks()

    curated = transform(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(curated, indent=2) + "\n")
    n = len(curated["results"])
    print(f"Wrote {n} benchmarks to {args.output}")


if __name__ == "__main__":
    main()
