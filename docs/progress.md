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
