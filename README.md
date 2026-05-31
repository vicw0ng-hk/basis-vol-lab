# basis-vol-lab

A cross-venue crypto-derivatives regime monitor for Deribit options and
Binance USD-margined futures/perpetuals. It turns IV, skew, basis, funding,
and open-interest data into a small set of readable market signals.

Live demo: <https://basis.vsh852.com>

## Dashboard

The app has five user-facing views:

- **Overview** - current Deribit option-chain summaries, perp funding,
  Binance basis, and open-interest concentration.
- **Volatility** - ATM term structure, smile nodes, and implied-vs-realized
  volatility context.
- **Carry** - perp funding, dated-futures basis, and carry/vol divergence.
- **Signals** - the current headline regime signals.
- **Learn** - short notes explaining the analytics behind the dashboard.

Headline signals:

- **Carry-vol divergence** - annualized carry versus the IV-minus-RV spread.
- **Skew stress** - 25-delta risk-reversal extremes plus OI concentration.
- **Regime-change alert** - a composite threshold across carry, skew, and OI.

## Architecture

This is a `uv` workspace monorepo.

```text
apps/web          Vite + React dashboard, deployed on Cloudflare Pages
apps/api          FastAPI + Mangum API, deployed on AWS Lambda
packages/connectors   Deribit and Binance REST/WebSocket clients
packages/analytics    Pricing, IV, Greeks, RV, carry, surface, signals
packages/contracts    Shared models and enums
packages/persistence  SQLite/D1 metadata and Parquet/R2 time series
infra/terraform       Cloudflare, AWS, and HCP Terraform config
infra/docker          Docker Compose for local development
docs/analytics        Markdown used by the Learn page
tests                 Pytest suite
```

Data flow:

```text
Deribit/Binance -> connectors -> contracts -> persistence
                                      |       |
                                      |       -> Parquet/R2 + SQLite/D1
                                      -> analytics -> JSON artifacts
                                                     -> API + web app
```

## Local Run

Prerequisites: [`uv`](https://docs.astral.sh/uv/) and
[`mise`](https://mise.jdx.dev/). Non-Python tools (`bun`, `terraform`)
are managed by `mise` and installed automatically via `mise install`.

```bash
uv sync
mise install
mise run check
```

Run the app with host processes:

```bash
mise run snapshot
mise run api
mise run web:install   # first time only
mise run web:dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to
`localhost:8000`, and the header Refresh button calls `POST /api/refresh`.

Run the same shape through Docker Compose (config lives in `infra/docker/`):

```bash
mise run compose:up
```

Web: <http://localhost:5173>. API: <http://localhost:8000>.

## Common Commands

```bash
uvx ruff format .
uvx ruff check . --fix
uvx ty check
uv run pytest
bun --cwd apps/web biome format --write src/
bun --cwd apps/web biome check --write src/
bun --cwd apps/web tsc -b
mise run check

uv run python -m basis_connectors.deribit --currency BTC --kind option --limit 5
uv run python -m basis_connectors.binance --symbols BTCUSDT --limit 5
uv run python -m basis_analytics.validate --currency BTC
```

## Storage

Local data is gitignored under `data/`.

```text
data/
  artifacts/              curated JSON for the API and web app
  metadata.db             local SQLite metadata
  parquet/<venue>/<date>/ tickers.parquet snapshots
```

Cloud storage mirrors this layout: Cloudflare R2 stores JSON and Parquet;
Cloudflare D1 stores metadata.

## Deployment

Production is deployed at <https://basis.vsh852.com>.

| Component | Service |
| --- | --- |
| Static app | Cloudflare Pages |
| API | AWS Lambda + API Gateway |
| Artifacts | Cloudflare R2 |
| Metadata | Cloudflare D1 |
| Infrastructure | Terraform via HCP Terraform |
| Freshness | `POST /api/refresh` plus a best-effort GitHub Actions cron (runs every 1–5 hours due to free-tier scheduling) |
| Uptime | Hourly GitHub Actions probe |

Cost rule: stay inside free tiers. Do not use D1 for raw market data, and do
not use paid always-on compute for this demo.

## Limits

- GitHub Actions scheduled workflows on free-tier repos run on a best-effort
  basis. The `*/15` cron schedule often fires once every 1–5 hours. The
  frontend shows a staleness indicator (⚠) when snapshot data is older than
  30 minutes.
- Binance Futures is geo-restricted in several jurisdictions, including the
  United States. The snapshot runner tries multiple connection strategies
  (proxy, proxy with extended timeout, direct) and falls back gracefully.
  A pre-flight connectivity check step in the workflow logs the runner region
  and reachability of each exchange.
- Binance futures WebSocket market streams use
  `wss://fstream.binance.com/market/stream?streams=...`; legacy `/ws` and
  `/stream` paths can ACK subscriptions without sending market frames.
- Deribit `raw` ticker channels require authentication. The public `100ms`
  interval is enough for this dashboard.
- Rolling percentile signals need enough accumulated history before they are
  statistically meaningful.

## Docs

- [docs/analytics/README.md](docs/analytics/README.md) - Learn-page content.
- [docs/progress.md](docs/progress.md) - current status and next work.
- [infra/terraform/README.md](infra/terraform/README.md) - deployment notes.
- [infra/docker/](infra/docker/) - Docker Compose for local development.
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - repo
  conventions for AI-assisted work.

## License

See [LICENSE](LICENSE).
