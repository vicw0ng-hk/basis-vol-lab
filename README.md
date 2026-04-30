# basis-vol-lab

A cross-venue **crypto-derivatives regime monitor**. Ingests Deribit options
and Binance USD-margined futures/perpetuals, computes IV, skew, basis,
funding, and open-interest metrics, and surfaces three headline signals
designed to make a current market regime legible at a glance.

> **Status**: MVP under active construction. Tracked in [`docs/progress.md`](docs/progress.md).
> The implementation plan lives in [`docs/planning/`](docs/planning/), starting with [`1.initial-plan.md`](docs/planning/1.initial-plan.md).

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
    desktop/      # Optional PySide6 operator console
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

# Install pinned non-Python tools (node, terraform, wrangler)
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
| Containers (local dev)            | Docker Compose                |
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

| Component        | Target                          | Why                                        |
| ---------------- | ------------------------------- | ------------------------------------------ |
| Static front end | Cloudflare Pages                | Free unlimited static requests             |
| Time-series      | Cloudflare R2                   | No egress fees, S3-compatible              |
| Metadata         | Cloudflare D1                   | SQLite-compatible, sufficient for run logs |
| Analytics        | AWS Lambda (container images)   | Free tier, easy SciPy packaging            |
| IaC              | Terraform via HCP Terraform     | Free remote state + VCS-driven runs        |

Cost rule: **everything stays inside free tiers**.

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
