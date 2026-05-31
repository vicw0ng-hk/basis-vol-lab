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
- Collection-run metadata tracked in SQLite/D1: start/end, status, record
  count. `GET /api/runs` endpoint and Overview page health table.
- Rolling-percentile regime signals: accumulated `signal_history.json`,
  per-symbol percentile ranks (funding, carry, ATM IV, OI), adaptive
  frontend (snapshot mode vs rolling mode).
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
- Concurrency deep-dive notebook: asyncio I/O, GIL behaviour, threading vs
  multiprocessing for CPU-bound work, producer–consumer queues, and scaling
  analysis with the IV solver.

## Known Limits

- GitHub Actions free-tier cron is best-effort; `*/15` typically runs every
  1–5 hours. The frontend displays a staleness warning when data is older
  than 30 minutes.
- GitHub-hosted runners are US-based, so Binance Futures may be geo-blocked.
  The snapshot runner now tries proxy, proxy with extended timeout, then
  direct connection, falling back gracefully. Set `BASIS_PROXY_URLS` to
  route through an allowed region if direct access fails.
- Rolling-percentile signals need more accumulated history before the
  percentile ranks become statistically meaningful (≥ 5 observations per
  symbol triggers rolling mode, but 30+ is ideal).
- Historical replay and Greek validation reporting are useful follow-ups but
  not required for the deployed demo.
