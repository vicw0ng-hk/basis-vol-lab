# Progress

## Completed

- **Step 1** — repo scaffold, uv workspace, mise tooling, ruff/pyright/pytest pipeline. See [`docs/planning/2.step1-scaffold.md`](planning/2.step1-scaffold.md).
- **Step 2** — local data model (SQLite metadata + Parquet time-series). See [`docs/planning/3.step2-data-model.md`](planning/3.step2-data-model.md).
- **Step 3** — Deribit connector (REST instrument discovery + WebSocket ticker stream with heartbeats and reconnect). See [`docs/planning/4.step3-deribit-connector.md`](planning/4.step3-deribit-connector.md).

### Step 3 highlights

- `basis_connectors.deribit` package: `parsers.py` (pure), `rest.py` (`DeribitRestClient`), `ws.py` (`DeribitWsClient`), `__main__.py` smoke CLI.
- 13 fixture-based parser tests; 39 tests pass overall.
- Defaults to the `100ms` ticker channel since `.raw` requires authentication.
- `mise run collect` wired to the smoke CLI.
- Live smoke verified against `wss://www.deribit.com/ws/api/v2`: BTC perp/future tickers stream with mark/funding; option tickers stream with `mark_iv` (decimal).

## Deferred mise tasks

The following mise tasks are planned but deferred until the corresponding features exist:

- `backfill` — fetch historical data from REST endpoints (step 4)
- `build:web` — build the static front end (step 6)
- `deploy` — push to cloud (step 6+)

## Next

→ **Step 4** — Binance connector (mark-price WS streams + REST backfills for funding history, basis, OI). Start by writing a planning doc at `docs/planning/5.step4-binance-connector.md`.
