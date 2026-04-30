# Progress

## Completed

- **Step 1** — repo scaffold, uv workspace, mise tooling, ruff/pyright/pytest pipeline. See [`docs/planning/2.step1-scaffold.md`](planning/2.step1-scaffold.md).
- **Step 2** — local data model (SQLite metadata + Parquet time-series). See [`docs/planning/3.step2-data-model.md`](planning/3.step2-data-model.md).
- **Step 3** — Deribit connector (REST instrument discovery + WebSocket ticker stream with heartbeats and reconnect). See [`docs/planning/4.step3-deribit-connector.md`](planning/4.step3-deribit-connector.md).
- **Step 4** — Binance connector (REST instrument discovery + funding/basis/OI backfills + mark-price WebSocket stream). See [`docs/planning/5.step4-binance-connector.md`](planning/5.step4-binance-connector.md).

## Deferred

- **Authenticated Deribit channels** (e.g. `ticker.*.raw`) — public `100ms` interval is sufficient for the MVP; revisit if/when we need raw-rate updates.
- **Persisting connector output to `MetadataStore` / `TimeSeriesStore`** — connectors emit domain objects; wiring to storage is a later concern (step 5+).
- **Production Binance WebSocket** — Initially hit silent timeouts from Hong Kong and assumed a geo-block. **Root cause was actually Binance's 2026-04-23 base-URL migration**: legacy `/ws` and `/stream` paths still accept connections and SUBSCRIBE ACKs but no longer deliver `/market` channels (markPrice, aggTrade, kline, ticker, forceOrder, etc.). Connector now uses `wss://fstream.binance.com/market/stream?streams=...` and works directly from HK with no VPN. Deployment caveat is just the formal Binance Futures restricted-country list (US, Canada, Netherlands, Cuba, Iran, North Korea, Crimea/Donetsk/Luhansk) — avoid AWS `us-east-1` / `us-west-2`; everything else (Tokyo, Singapore, Ireland, Frankfurt) is fine.
- **Binance COIN-margined futures, options, spot, user-data streams** — out of MVP scope.
- `mise run backfill` — to be wired when we add a scheduled historical-collection job.
- `mise run build:web` — wired when the static front end exists (step 6).
- `mise run deploy` — wired when cloud deployment lands (step 6+).

## Next

→ **Step 5** — Analytics package: pandas/NumPy/SciPy normalization, IV/Greeks pricer with validation against Deribit-published values, and the three headline signals (carry-vol divergence, skew stress, regime-change alert).
