# Progress

## Completed

- **Step 1** — repo scaffold, uv workspace, mise tooling, ruff/pyright/pytest pipeline. See [`docs/planning/2.step1-scaffold.md`](planning/2.step1-scaffold.md).
- **Step 2** — local data model (SQLite metadata + Parquet time-series). See [`docs/planning/3.step2-data-model.md`](planning/3.step2-data-model.md).
- **Step 3** — Deribit connector (REST instrument discovery + WebSocket ticker stream with heartbeats and reconnect). See [`docs/planning/4.step3-deribit-connector.md`](planning/4.step3-deribit-connector.md).
- **Step 4** — Binance connector (REST instrument discovery + funding/basis/OI backfills + mark-price WebSocket stream). See [`docs/planning/5.step4-binance-connector.md`](planning/5.step4-binance-connector.md).
- **Step 5** — Analytics package: Black-76 pricer + IV inversion (Brent) + analytic Greeks + realized-vol estimators + carry/funding helpers + smile/term-structure interpolation + the three headline signals + an IV-validation CLI. Live validation against Deribit shows p95 IV error < 0.005 vol points on liquid expiries (30D+). See [`docs/planning/6.step5-analytics.md`](planning/6.step5-analytics.md). Six-lecture markdown course under [`docs/analytics/`](analytics/README.md).

## Abandoned

- **PySide6 desktop operator console** (originally `apps/desktop` + step 7 of the initial plan) — folder deleted, workspace member removed, all references purged. The web shell already exercises the same hiring signals (Python data stack, async IO, packaging) and the schedule is better spent on the validation report and deployed demo. Decision date: 2026-04-30.

## Deferred

- **Authenticated Deribit channels** (e.g. `ticker.*.raw`) — public `100ms` interval is sufficient for the MVP; revisit if/when we need raw-rate updates.
- **Persisting connector output to `MetadataStore` / `TimeSeriesStore`** — connectors emit domain objects; wiring to storage is the next step's concern (step 6).
- **Binance COIN-margined futures, options, spot, user-data streams** — out of MVP scope.
- **Greek validation report** — step 5 validates IV only; once IV ties out, Greek mismatches against Deribit are unit conversions handled downstream. Add as a follow-on if useful.
- **SVI / SABR surface fits** — current MVP uses PCHIP smile interpolation; parametric fits are future research.
- **Backtests of the headline signals** — signals are interpretable on inspection; backtesting is deferred so we don't blow the schedule.
- `mise run backfill` — to be wired when we add a scheduled historical-collection job.
- `mise run build:web` — wired when the static front end exists (step 6).
- `mise run deploy` — wired when cloud deployment lands (step 6+).

## Next

→ **Step 6** — Product shell: thin API endpoints (FastAPI in a Lambda-friendly shape) + static web front end, both reading curated artifacts. Wire connectors → `TimeSeriesStore` and run a scheduled snapshot. Compose locally with Docker.

## Notes

- **Production Binance WebSocket** — Initially hit silent timeouts from Hong Kong and assumed a geo-block. **Root cause was actually Binance's 2026-04-23 base-URL migration**: legacy `/ws` and `/stream` paths still accept connections and SUBSCRIBE ACKs but no longer deliver `/market` channels (markPrice, aggTrade, kline, ticker, forceOrder, etc.). Connector now uses `wss://fstream.binance.com/market/stream?streams=...` and works directly from HK with no VPN. Deployment caveat is just the formal Binance Futures restricted-country list (US, Canada, Netherlands, Cuba, Iran, North Korea, Crimea/Donetsk/Luhansk) — avoid AWS `us-east-1` / `us-west-2`; everything else (Tokyo, Singapore, Ireland, Frankfurt) is fine.
- **TickerSnapshot gained `expiry` and `strike` fields** in step 5 so option snapshots are self-describing for analytics. The Parquet schema (`TICKER_SCHEMA`) was extended to match; new files include both columns nullable.
- **Black-76 vs BSM** — Deribit's `mark_iv` is under Black-76 with `df = 1` (inverse-quoted premium). Our pricer matches to ~1e-3 vol points on liquid quotes. See [`docs/analytics/01-options-and-forward-pricing.md`](analytics/01-options-and-forward-pricing.md) for the full story.
