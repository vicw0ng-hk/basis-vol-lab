# Project Status

## Current

The dashboard is deployed at <https://basis.vsh852.com>. Cloudflare Pages
serves the React app, AWS Lambda serves the FastAPI endpoints, R2 stores
curated artifacts and Parquet snapshots, and D1 is provisioned for metadata.

## Complete

- `uv` workspace with `mise` tasks, Ruff, Pyright, pytest, and CI.
- Shared contracts for instruments, ticker snapshots, venues, and asset kinds.
- Deribit and Binance public REST/WebSocket connectors.
- Analytics for Black-76 pricing, IV inversion, Greeks, realized volatility,
  carry/funding, smile interpolation, term structure, and headline signals.
- Local persistence through SQLite metadata and Parquet time series.
- Snapshot orchestrator that emits `meta`, `overview`, `vol`, `carry`, and
  `signals` JSON artifacts.
- FastAPI service with read endpoints and `POST /api/refresh`.
- Vite/React/Tailwind dashboard with light/dark theme support.
- Biome formatting and linting for TypeScript/React (`mise run web:lint`).
- Auto-bootstrap: the frontend retries indefinitely and triggers a refresh
  when the API has no cached artifacts.
- Terraform-managed Cloudflare Pages/R2/D1 plus AWS Lambda/API Gateway.
- GitHub Actions CI, snapshot cron, and uptime probe.

## Known Limits

- GitHub-hosted runners are US-based, so Binance Futures pulls can return
  HTTP 451 without a proxy. Set the `BASIS_PROXY_URLS` secret to route
  Binance traffic through an allowed region (e.g. Japan).
- Rolling-percentile signals need more accumulated history before replacing
  the current snapshot-level signal view.
- Historical replay, Greek validation reporting, and D1-backed run metadata
  are useful follow-ups but not required for the deployed demo.

## Next Candidates

1. Record each refresh as a `CollectionRun` in local SQLite and cloud D1.
2. Replace snapshot-level signals with rolling percentiles once enough R2
   history exists.
3. Add a historical replay page backed by the accumulated Parquet snapshots.

## Interview-Readiness Gap Analysis

### Already Demonstrable (CV-ready)

| Skill Signal | Evidence |
|---|---|
| Python data stack (Pandas, NumPy, SciPy) | `basis_analytics` — vectorized Black-76, IV via Brent's, Greeks, RV estimators, PCHIP surface interpolation |
| Async I/O & concurrency | Dual-exchange WebSocket/REST collectors with heartbeat and reconnect |
| Cloud & IaC | Terraform-managed Cloudflare Pages/R2/D1 + AWS Lambda/API Gateway |
| CI/CD | GitHub Actions lint → typecheck → test → deploy pipeline (Python + TypeScript) |
| Testing | 44+ pytest cases covering pricing, edge cases, vectorization, parsing |
| Data engineering | Parquet time-series store, 15-min cron snapshots, curated JSON artifacts |
| Trader-facing product | 5-page React dashboard: overview, vol surface, carry, signals, learn |

### Missing — High Priority

The items below are the strongest remaining ways to turn the repo into
interview evidence. They demonstrate rigour, performance awareness, and the
ability to communicate quantitative work — all recurring signals in Hong Kong
quant-dev JDs.

#### 1. Validation Report Notebook

**Why:** Shows you can compare your own pricer outputs against a live venue,
quantify error, and discuss numerical choices (convergence tolerance, edge
cases near expiry).

- `notebooks/01_iv_greek_validation.ipynb` — pull a Deribit snapshot, run
  `validate_iv`, plot error distributions by tenor bucket and moneyness.
- Surface the rendered notebook on the website under `/learn/validation`.

#### 2. Performance Benchmarks

**Why:** Hong Kong roles explicitly mention multithreading, performance, and
systems knowledge. Benchmarks prove you understand where time goes and can
reason about vectorization vs. scalar code.

- `benchmarks/bench_iv.py` — time `implied_vol_array` at various chain sizes
  (100, 1 000, 10 000 options), compare scalar loop vs. NumPy vectorized vs.
  `ProcessPoolExecutor` for CPU-heavy batches.
- `benchmarks/bench_greeks.py` — vectorized Greeks throughput.
- `benchmarks/bench_snapshot.py` — end-to-end snapshot latency breakdown
  (network I/O vs. compute vs. serialization).
- Publish a summary table and charts on the website under `/benchmarks`.

#### 3. Exploratory Analytics Notebooks

**Why:** Pandas mastery and the ability to present quantitative analysis
interactively — exactly what "data skills" means on JDs.

- `notebooks/02_carry_regime_explorer.ipynb` — load accumulated Parquet
  history, compute rolling carry/vol divergence, visualize regime transitions.
- `notebooks/03_surface_dynamics.ipynb` — animate IV surface evolution over
  time, show term-structure slope changes and smile shape shifts.
- `notebooks/04_rv_estimators_comparison.ipynb` — compare close-to-close vs.
  Parkinson vs. Yang-Zhang estimators on real BTC data.
- Render key notebook outputs (charts, tables) as static assets served on the
  website's Learn section.

#### 4. Website Integration for Notebooks & Benchmarks

- Add a `/benchmarks` page showing performance tables, throughput charts, and
  hardware context (CPU, Python version).
- Extend `/learn` with rendered notebook outputs (exported HTML or static
  chart images) so interviewers see the analysis without needing Jupyter.
- Add an "Engineering" section in the README linking to benchmarks and
  validation results.

### Missing — Medium Priority

#### 5. Collection-Run Metadata in D1

Record `CollectionRun` rows (start, end, status, artifact count) in D1 so
the dashboard can show operational health and uptime history. Demonstrates
production-awareness and observability thinking.

#### 6. Rolling-Percentile Signals

Replace snapshot-level signal approximations with true rolling percentiles
over accumulated R2 history. This makes the signals page meaningful and
shows time-series engineering with Pandas `rolling()`.

#### 7. Historical Replay Page

Load Parquet snapshots by date, show "what changed?" summaries, and let users
scrub through time. Exercises DuckDB/PyArrow query patterns and frontend
state management.

#### 8. Concurrency Deep-Dive Notebook

`notebooks/05_concurrency_patterns.ipynb` — demonstrate asyncio event loop
for I/O, threading for mixed workloads, ProcessPoolExecutor for CPU batches,
and GIL behaviour. Directly addresses "multithreading/multiprocessing" JD
requirements.

### Implementation Order (Recommended)

1. Validation notebook (quick win, reuses existing `validate.py`)
2. Performance benchmarks (pytest-benchmark or simple `time.perf_counter`)
3. Carry/surface notebooks using accumulated Parquet data
4. Website pages for benchmarks and notebook outputs
5. Collection-run metadata and rolling signals
6. Historical replay page
