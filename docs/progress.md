# Project Status

## Current

The dashboard is deployed at <https://basis.vsh852.com>. Cloudflare Pages
serves the React app, AWS Lambda serves the FastAPI endpoints, R2 stores
curated artifacts and Parquet snapshots, and D1 is provisioned for metadata.

## Complete

- `uv` workspace with `mise` tasks, Ruff, Pyright, pytest, and CI.
- Shared contracts for instruments, ticker snapshots, venues, and asset kinds.
- Deribit and Binance public REST/WebSocket connectors.
- Analytics for Black-76 pricing, IV inversion, Greeks, realized volatility
  (close-to-close, Parkinson, Yang-Zhang), carry/funding, smile
  interpolation, term structure, and headline signals.
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
- Docker Compose local development stack (`infra/docker/`).
- Binance connection retry/fallback (proxy → proxy+extended timeout → direct)
  with diagnostic logging and pre-flight connectivity checks.
- Frontend staleness indicator for irregular snapshot scheduling.

## Known Limits

- GitHub Actions free-tier cron is best-effort; `*/15` typically runs every
  1–5 hours. The frontend displays a staleness warning when data is older
  than 30 minutes.
- GitHub-hosted runners are US-based, so Binance Futures may be geo-blocked.
  The snapshot runner now tries proxy, proxy with extended timeout, then
  direct connection, falling back gracefully. Set `BASIS_PROXY_URLS` to
  route through an allowed region if direct access fails.
- Rolling-percentile signals need more accumulated history before replacing
  the current snapshot-level signal view.
- Historical replay, Greek validation reporting, and D1-backed run metadata
  are useful follow-ups but not required for the deployed demo.

## Gap Analysis

### Already Demonstrable

| Skill Signal | Evidence |
|---|---|
| Python data stack (Pandas, NumPy, SciPy) | `basis_analytics` — vectorized Black-76, IV via Brent's, Greeks, RV estimators, PCHIP surface interpolation |
| Async I/O & concurrency | Dual-exchange WebSocket/REST collectors with heartbeat and reconnect |
| Cloud & IaC | Terraform-managed Cloudflare Pages/R2/D1 + AWS Lambda/API Gateway |
| CI/CD | GitHub Actions lint → typecheck → test → deploy pipeline (Python + TypeScript) |
| Testing | 110 pytest cases covering pricing, edge cases, vectorization, parsing |
| Data engineering | Parquet time-series store, 15-min cron snapshots, curated JSON artifacts |
| Trader-facing product | 5-page React dashboard: overview, vol surface, carry, signals, learn |

### Missing — High Priority

The items below are the strongest remaining ways to turn the repo into
interview evidence. They demonstrate rigour, performance awareness, and the
ability to communicate quantitative work — all recurring signals in Hong Kong
quant-dev JDs.

#### ~~1. Validation Report Notebook~~ ✓

- `notebooks/01_iv_greek_validation.ipynb` — pulls a Deribit snapshot,
  runs `validate_iv`, plots error distributions by tenor bucket and
  moneyness, and cross-checks vectorized Greeks.
- Learn page: `docs/analytics/07-iv-validation.md` served at
  `/learn/07-iv-validation`.

#### ~~2. Performance Benchmarks~~ ✓

- `benchmarks/bench_iv.py` — `implied_vol_array` at 100 / 1k / 10k chain
  sizes, scalar loop vs. array wrapper vs. `ProcessPoolExecutor`.
- `benchmarks/bench_greeks.py` — vectorized Greeks & pricing throughput,
  scalar loop baseline, PCHIP smile build + eval.
- `benchmarks/bench_snapshot.py` — compute-only snapshot pipeline: ATM term
  structure, IV solve, RV estimators, basis curve, funding, JSON serialize.
- Run with `mise run bench`.

#### ~~3. Exploratory Analytics Notebooks~~ ✓

- `notebooks/02_carry_regime_explorer.ipynb` — loads accumulated Parquet
  history, computes rolling carry/vol divergence, visualizes regime
  transitions with percentile-rank signals.
- `notebooks/03_surface_dynamics.ipynb` — 3-D IV surface, ATM term-structure
  evolution, smile shape shifts, skew/butterfly metrics over time.
- `notebooks/04_rv_estimators_comparison.ipynb` — compares close-to-close vs.
  Parkinson vs. Yang-Zhang estimators on Binance OHLC and Deribit snapshot
  data.
- Yang-Zhang estimator added to `basis_analytics.realized_vol`.
- Render key notebook outputs (charts, tables) as static assets served on the
  website's Learn section.

#### ~~4. Website Integration for Notebooks & Benchmarks~~ ✓

- `/benchmarks` page with hardware context, grouped performance tables,
  and throughput bar charts — data generated from pytest-benchmark JSON
  via `scripts/export_benchmarks.py`.
- `/learn/08-notebooks` lecture summarising all four notebooks with key
  findings, auto-discovered by the existing Learn page glob.
- "Engineering" section added to README linking to benchmarks and notebooks.

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

1. ~~Validation notebook~~ ✓
2. ~~Performance benchmarks~~ ✓
3. ~~Carry/surface notebooks using accumulated Parquet data~~ ✓
4. ~~Website pages for benchmarks and notebook outputs~~ ✓
5. Collection-run metadata and rolling signals
6. Historical replay page
