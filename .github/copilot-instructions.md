# Copilot Instructions — Basis & Vol Lab

## Project Overview

A cross-venue crypto-derivatives regime monitor ingesting Deribit options and Binance futures/perpetual data. Computes IV, skew, basis, funding, and regime metrics. Targets a deployed, cost-aware serverless stack (Cloudflare Pages/R2/D1 + AWS Lambda) provisioned with Terraform.

> **Current status**: see [`docs/progress.md`](../docs/progress.md) for the latest completed steps and the active next step. Planning details for each step live under `docs/planning/`. Always consult `docs/progress.md` at the start of a session before deciding what to work on.

### Core Signals

- **Carry-vol divergence score** — percentile-ranked annualized carry vs IV-minus-RV spread.
- **Skew stress score** — front-end 25Δ risk-reversal extremes + OI concentration.
- **Regime-change alert** — composite threshold on carry/skew/OI percentile moves.

### Architecture

```
basis-vol-lab/
  apps/
    web/          # static front end (Cloudflare Pages)
    api/          # thin dynamic endpoints (AWS Lambda)
  packages/
    connectors/   # async WebSocket/REST collectors (Deribit, Binance)
    analytics/    # pandas/numpy/scipy analytics & signal computation
    contracts/    # data models, schemas, enums
    persistence/  # SQLite/D1 metadata, Parquet/R2 time-series
  infra/
    terraform/    # HCP Terraform, Cloudflare, AWS
  benchmarks/
  tests/
  docs/
  notebooks/
```

This is a uv workspace monorepo. Each `packages/*` and `apps/*` directory is a workspace member with its own `pyproject.toml`.

---

## Runtime & Tooling

| Concern | Tool |
|---------|------|
| Python package/project management | `uv` (always) |
| Python virtual environment | managed by `uv` via `.venv` |
| Non-Python tool versions | `mise` (node, terraform, awscli, etc.) |
| Project tasks (lint, test, build) | `mise` tasks or `uv run` |
| Web framework | Vite + React 18 + TypeScript |
| Web styling | Tailwind CSS v4 (CSS-variables, `.dark` class) |
| Web charts | Recharts |
| API framework | FastAPI + uvicorn (Mangum on Lambda) |
| Containers (local dev) | Docker Compose (`compose.yaml`), OrbStack-tested |
| CI/CD | GitHub Actions |
| IaC | Terraform (HCP Terraform remote state) |

### Commands

```bash
# Run a Python script or module
uv run python <script>

# Run tests
uv run pytest

# Lint
uvx ruff check .

# Format
uvx ruff format .

# Type check
uvx pyright
```

---

## Python Standards

- **Style**: PEP 8, enforced by Black-compatible formatting via `ruff format`.
- **Linting**: Ruff (with rules including `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `N`).
- **Type hints**: Required on all function signatures. Use `pyright` for static checking.
- **Docstrings**: Google-style on all public modules, classes, and functions.
- **Testing**: `pytest`. Write the **test first**, then the implementation (TDD).
- **Imports**: Sort with Ruff (`I` rules). Absolute imports within packages.

### After Writing Code

Always run in this order:

1. `uvx ruff format .`
2. `uvx ruff check . --fix`
3. `uvx pyright`
4. `uv run pytest`

Or equivalently: `mise run check`

Confirm all four pass before considering a task complete.

---

## TDD Workflow

1. Write a failing test in `tests/` (or the package's own test directory).
2. Run `uv run pytest` — confirm it fails for the right reason.
3. Write the minimal implementation to make it pass.
4. Refactor if needed, re-run formatter/linter/tests.

---

## Concurrency Model

- **`asyncio`** for all network I/O (exchange WebSocket/REST).
- **NumPy/Pandas vectorization** for bulk math (avoid Python loops over arrays).
- **`ProcessPoolExecutor`** for CPU-heavy work (calibration, replay batches).
- Never use threads for CPU-bound work (GIL constraint).

---

## Data & Storage

| Layer | Local | Cloud |
|-------|-------|-------|
| Metadata | SQLite (`MetadataStore`) | Cloudflare D1 |
| Time-series | Parquet files (`TimeSeriesStore`) | Cloudflare R2 |
| Ad-hoc queries | DuckDB over Parquet | DuckDB over S3/R2 |

### Persistence package (`packages/persistence`)

- **`MetadataStore`** — SQLite wrapper for `instruments` and `collection_runs` tables. Timestamps as ISO-8601 TEXT (D1 compatible). Uses `ON CONFLICT ... DO UPDATE` for upserts.
- **`TimeSeriesStore`** — Parquet writer/reader for `TickerSnapshot`. Files partitioned as `{base_dir}/{venue}/{YYYY-MM-DD}/tickers.parquet`. Appends to existing files.
- **`TICKER_SCHEMA`** — PyArrow schema with microsecond UTC timestamps.
- Local data lives in `data/` (gitignored).

### Storage rules

- Store 5–15 min summary metrics continuously; full-chain snapshots hourly/daily.
- Keep D1 writes under 100k rows/day and reads under 5M rows/day (free tier).
- Never use R2 `r2.dev` subdomain for production traffic.

---

## Exchange Connectors

### Deribit

- WebSocket subscriptions preferred over REST polling.
- Subscribe to ticker channels for BTC/ETH options + perps.
- Implement heartbeat handling and reconnect/resubscribe on disconnect.
- Fields: bid/ask/mark IV, Greeks, OI, mark price, funding.

### Binance

- WebSocket mark-price streams for current funding/mark data.
- REST backfills for funding history, basis, open-interest history.
- Connections expire after 24h; handle ping/pong.
- Respect per-connection stream limits and message rate limits.

---

## Analytics

- **pandas**: normalize timestamps, resample bars, align series.
- **NumPy**: vectorized calculations, broadcasting over arrays.
- **SciPy**: IV root solving (Brent/Newton), surface interpolation.
- **PyArrow/Parquet**: compact serialization of curated outputs.
- **Validation**: compare own IV/Greeks against Deribit's published values; persist error summaries.

---

## Cloud & Deployment

- **Cloudflare Pages** for static web front end (free unlimited requests).
- **Cloudflare R2** for artifact storage (no egress fees).
- **Cloudflare D1** for metadata only (not raw market data).
- **AWS Lambda** for on-demand analytics refresh (container images OK).
- **Terraform** manages all infra; remote state in HCP Terraform.
- **GitHub Actions** for CI/CD and scheduled snapshot jobs (not real-time collection).

---

## Cost Rules

- Never pay for anything. Stay within free tiers at all times.
- Do not use D1 as a raw market-data sink.
- Do not use Workers for heavy analytics.
- GitHub Actions cron is best-effort; use cached on-demand endpoints for live views.

---

## Scope Priorities (cut order if schedule is tight)

1. ✂️ Always-on streaming (cut first)
2. ✂️ Fancy UI polish
3. 🔒 Core analytics package (never cut)
4. 🔒 Validation report (never cut)
5. 🔒 Test suite (never cut)
6. 🔒 Deployed demo (never cut)
7. 🔒 Benchmark notes (never cut)

---

## Session Hygiene

- At the end of each working session, review whether this instructions file needs updating (new packages, changed conventions, new tools, etc.) and update it if so. 
- Update `docs/progress.md` for what steps have been done and what step is next.
- For any task in the initial plan that we decide not to do or to do in a different way, update `docs/planning/1.initial-plan.md` and `docs/planning/` step files to reflect what was actually done.
- For any task that was deferred, make sure it's clearly marked as deferred in `docs/progress.md`.
