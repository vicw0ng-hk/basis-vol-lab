# basis-vol-lab

A cross-venue **crypto-derivatives regime monitor**. Ingests Deribit options
and Binance USD-margined futures/perpetuals, computes IV, skew, basis,
funding, and open-interest metrics, and surfaces three headline signals
designed to make a current market regime legible at a glance.

> **Live demo**: <https://basis.vsh852.com>
>
> **Status**: deployed. Cloudflare Pages serves the SPA; AWS Lambda + API
> Gateway serve `POST /api/refresh` and the curated read endpoints; R2
> stores artifacts; D1 holds metadata. Provisioned end-to-end with
> Terraform via HCP Terraform, with a `*/15 * * * *` GitHub Actions cron
> as a best-effort snapshot backstop. Tracked in
> [`docs/progress.md`](docs/progress.md). Implementation plan lives in
> [`docs/planning/`](docs/planning/), starting with
> [`1.initial-plan.md`](docs/planning/1.initial-plan.md).

## What it does

The dashboard is built around four pages and three headline signals:

**Pages**
- **Live overview** — Deribit option-chain summaries, perp funding, Binance basis, funding, OI concentrations.
- **Volatility & skew** — ATM term structure, smile nodes, realized-vs-implied panels.
- **Carry** — perp funding, quarterly basis, carry/vol divergence.
- **Historical replay** — percentile regimes and "what changed?" summaries.

**Signals**
- **Carry-vol divergence** — percentile-ranked annualized carry vs IV-minus-RV.
- **Skew stress** — front-end 25Δ risk-reversal extremes + OI concentration.
- **Regime-change alert** — composite threshold on carry / skew / OI percentile moves.

## Architecture

The codebase is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) monorepo. Each `packages/*` and `apps/*` directory is a workspace member with its own `pyproject.toml`.

```
basis-vol-lab/
  apps/
    web/          # Static front end (Cloudflare Pages)
    api/          # Thin dynamic endpoints (AWS Lambda)
  packages/
    connectors/   # Async WebSocket/REST collectors (Deribit, Binance)
    analytics/    # Pandas/NumPy/SciPy analytics & signal computation
    contracts/    # Data models, schemas, enums
    persistence/  # SQLite/D1 metadata, Parquet/R2 time-series
  infra/
    terraform/    # HCP Terraform, Cloudflare, AWS
  benchmarks/
  tests/
  docs/
  notebooks/
```

### Data flow

```
Deribit / Binance  ──(async WS + REST)──▶  connectors  ──▶  TickerSnapshot / *Row
                                                           │
                                                           ├─▶ TimeSeriesStore (Parquet → R2)
                                                           ├─▶ MetadataStore  (SQLite → D1)
                                                           └─▶ analytics → signals → static JSON artifacts
                                                                                          │
                                                                                          └─▶ web (Pages) + api (Lambda)
```

## Quick start

Prerequisites:

- [`uv`](https://docs.astral.sh/uv/) for Python project/dependency management.
- [`mise`](https://mise.jdx.dev/) for non-Python tool versions and project tasks.

```bash
# Install Python deps and create the .venv
uv sync

# Install pinned non-Python tools (node, terraform)
mise install

# Install pre-commit hooks
uv run pre-commit install

# Run all checks: format + lint + typecheck + test
mise run check

# Smoke-run the Deribit collector (BTC instruments + live tickers)
mise run collect

# Smoke-run the Binance collector (live prod fstream)
mise run collect:binance
```

## Running the dashboard locally

The MVP ships with a snapshot orchestrator, a FastAPI service, and a
Vite/React SPA. There are two equivalent ways to run it.

### Option A — host processes (fast iteration)

```bash
# 1) Pull one Deribit + Binance snapshot and write artifacts under data/
mise run snapshot

# 2) In one shell: serve the JSON artifacts on http://localhost:8000
mise run api

# 3) In another shell: open the SPA on http://localhost:5173
mise run web:install   # first time only
mise run web:dev
```

The SPA dev server proxies `/api` to `localhost:8000`, so the four pages
(**Overview**, **Volatility**, **Carry**, **Signals**) light up immediately.
The header **Refresh** button calls `POST /api/refresh`, which re-runs the
snapshot in-process.

### Option B — Docker Compose (matches deployment shape)

```bash
mise run compose:up           # docker compose up --build
# → http://localhost:5173 (web, nginx) and http://localhost:8000 (api)
```

This works on **OrbStack** without any extra configuration: OrbStack
exposes the standard Docker socket, and the bind mount on `./data`
round-trips between the host and containers via VirtIOFS, so a
`mise run snapshot` on the host is immediately visible to the API
container (and vice versa via `POST /api/refresh`).

### Theme toggle

The header has a sun/moon button that flips between light and dark themes.
Preference is persisted in `localStorage` and falls back to
`prefers-color-scheme` on first load.

## Tooling

| Concern                           | Tool                          |
| --------------------------------- | ----------------------------- |
| Python package/project management | `uv`                          |
| Python virtual environment        | managed by `uv` via `.venv`   |
| Non-Python tool versions          | `mise`                        |
| Project tasks                     | `mise` tasks or `uv run`      |
| Lint + format                     | `ruff`                        |
| Type checking                     | `pyright`                     |
| Testing                           | `pytest`                      |
| Pre-commit hooks                  | `pre-commit`                  |
| Containers (local dev)            | Docker Compose / OrbStack     |
| Web framework                     | Vite + React 18 + TypeScript  |
| Web styling                       | Tailwind CSS v4               |
| Web charts                        | Recharts                      |
| API framework                     | FastAPI + uvicorn (Mangum on Lambda) |
| CI                                | GitHub Actions                |
| IaC                               | Terraform (HCP Terraform)     |

### Common commands

```bash
uv run pytest                          # run all tests
uvx ruff format .                      # format
uvx ruff check . --fix                 # lint + autofix
uvx pyright                            # type-check
mise run check                         # all four, in order

# Deribit smoke test (public, no auth)
uv run python -m basis_connectors.deribit --currency BTC --kind option --limit 5

# Binance smoke test (live prod fstream)
uv run python -m basis_connectors.binance --symbols BTCUSDT --limit 5
```

## Storage layout

Local development uses SQLite for metadata and Parquet for time-series, mirroring the cloud target (Cloudflare D1 + R2):

```
data/                          # gitignored
  metadata.db                  # SQLite metadata (instruments, runs)
  timeseries/                  # Parquet files
    deribit/2026-04-30/tickers.parquet
    binance/2026-04-30/tickers.parquet
```

## Cloud target

The deployment is live at <https://basis.vsh852.com>.

| Component        | Service                              | Notes                                                       |
| ---------------- | ------------------------------------ | ----------------------------------------------------------- |
| Static front end | Cloudflare Pages (custom domain)     | Free unlimited static requests; zone-level Web Analytics    |
| Time-series      | Cloudflare R2                        | No egress fees, S3-compatible, 30-day Parquet lifecycle     |
| Metadata         | Cloudflare D1                        | SQLite-compatible; instruments + collection runs            |
| Analytics / API  | AWS Lambda (arm64 container) + APIGW | `POST /api/refresh`, curated read endpoints                 |
| IaC              | Terraform via HCP Terraform          | VCS-driven runs from `master` filtered to `infra/terraform` |
| Snapshot cron    | GitHub Actions (`*/15 * * * *`)      | Best-effort; live freshness comes from `POST /api/refresh`  |
| Uptime canary    | GitHub Actions (`17 * * * *`)        | Probes the SPA + `/healthz`; failure emails the repo owner  |

```
                       ┌──────────────────────────┐
   Browser ──▶           │  Cloudflare Pages          │  https://basis.vsh852.com
                       │  apps/web/dist             │  (static SPA, free unlimited)
                       └─────────┬────────────────┘
                                 │ fetch /api/* (CORS, cross-origin)
                                 ▼
                       ┌──────────────────────────┐
                       │  AWS API Gateway HTTP      │
                       │  + Lambda (container)      │  basis_api / Mangum / arm64
                       └────┬──────────┬──────────┘
                            │ read+write│ read+write
                            ▼           ▼
                       ┌────────┐  ┌────────────┐
                       │   R2   │  │     D1     │
                       │ JSON + │  │  metadata  │
                       │ parquet│  │  + runs    │
                       └────────┘  └────────────┘
                            ▲
                            │ snapshot writes
                       ┌──────────────────────────┐
                       │ GitHub Actions cron        │  best-effort, every 15 min
                       │ uv run snapshot → R2       │
                       └──────────────────────────┘
```

Cost rule: **everything stays inside free tiers** (R2 storage stays well
under 10 GB-month; D1 well under 100 k row writes/day; Lambda well under
400 k GB-s; Pages and GitHub Actions are free for public repos). The
AWS billing dashboard reads `$0.00`.

## Known limitations

### Binance futures jurisdictional restrictions

Binance restricts its futures product (and `fstream.binance.com` /
`fapi.binance.com`) in a small set of jurisdictions, per Binance's
[List of Prohibited Countries](https://www.binance.com/en/about-legal/list-of-prohibited-countries)
and the futures-specific notes summarized by
[Coinperps](https://www.coinperps.com/learn/binance-futures-restricted-countries):

- **Full block (no futures):** United States, Canada, Netherlands, Cuba,
  Iran, North Korea, Crimea / Donetsk / Luhansk.
- For deployment, **avoid `us-east-1` / `us-west-2`**. Any other AWS
  region works fine; `ap-northeast-1` (Tokyo), `ap-southeast-1`
  (Singapore), `eu-west-1` (Ireland), and `eu-central-1` (Frankfurt) are
  the natural picks for a free-tier Lambda or scheduled GitHub Actions
  runner.

### Binance WebSocket base-URL migration (2026-04-23)

On **2026-04-23** Binance split its futures WebSocket into three
dedicated paths — `wss://fstream.binance.com/{public,market,private}` —
and decommissioned the legacy `/ws` and `/stream` paths for everything
except `/public` channels (book ticker, depth). After that date, the
legacy paths still **accept connections and SUBSCRIBE ACKs**, but
silently deliver no frames for any `/market` channel (markPrice,
aggTrade, kline, ticker, forceOrder, etc.). See the upstream
[Important WebSocket Change Notice](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Important-WebSocket-Change-Notice).

This is what we initially mistook for a geo-block: TLS and the WS
upgrade succeed in ~120 ms, then nothing arrives, regardless of egress
(HK home network, JP commercial VPN, JP residential proxy — all
identical). The fix is purely a URL change: our `BinanceWsClient`
subscribes via `/market/stream?streams=...`. Verified end-to-end live
from Hong Kong.

### Other limitations

- **Deribit `raw`-rate ticker subscriptions require authentication**
  (`raw_subscriptions_not_available_for_unauthorized`). The connector
  defaults to the public `100ms` interval, which is sufficient for the MVP.
- **GitHub Actions cron is best-effort, not real-time.** Scheduled snapshot
  jobs use Actions; live freshness comes from cached on-demand endpoints.

## Project documentation

- [`docs/progress.md`](docs/progress.md) — current status, completed steps, deferred items, next step.
- [`docs/planning/1.initial-plan.md`](docs/planning/1.initial-plan.md) — full implementation plan and rationale.
- [`docs/planning/`](docs/planning/) — per-step planning notes.
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md) — conventions and tooling rules for AI-assisted development.

## License

See [`LICENSE`](LICENSE).
