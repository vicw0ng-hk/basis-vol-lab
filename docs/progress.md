# Progress

## Completed

- **Step 1** — repo scaffold, uv workspace, mise tooling, ruff/pyright/pytest pipeline. See [`docs/planning/2.step1-scaffold.md`](planning/2.step1-scaffold.md).
- **Step 2** — local data model (SQLite metadata + Parquet time-series). See [`docs/planning/3.step2-data-model.md`](planning/3.step2-data-model.md).
- **Step 3** — Deribit connector (REST instrument discovery + WebSocket ticker stream with heartbeats and reconnect). See [`docs/planning/4.step3-deribit-connector.md`](planning/4.step3-deribit-connector.md).
- **Step 4** — Binance connector (REST instrument discovery + funding/basis/OI backfills + mark-price WebSocket stream). See [`docs/planning/5.step4-binance-connector.md`](planning/5.step4-binance-connector.md).
- **Step 5** — Analytics package: Black-76 pricer + IV inversion (Brent) + analytic Greeks + realized-vol estimators + carry/funding helpers + smile/term-structure interpolation + the three headline signals + an IV-validation CLI. Live validation against Deribit shows p95 IV error < 0.005 vol points on liquid expiries (30D+). See [`docs/planning/6.step5-analytics.md`](planning/6.step5-analytics.md). Six-lecture markdown course under [`docs/analytics/`](analytics/README.md).
- **Step 6 — MVP product shell** — snapshot orchestrator (`basis_api.snapshot`) wires connectors → `TimeSeriesStore` and emits curated JSON artifacts; FastAPI service (`basis_api.main`) serves the artifacts and exposes `POST /api/refresh`; Vite/React/Tailwind v4 SPA with light/dark toggle and four pages (Overview, Volatility, Carry, Signals); Dockerfiles for both apps and a `compose.yaml` that runs end-to-end on **OrbStack**. See [`docs/planning/7.step6-product-shell.md`](planning/7.step6-product-shell.md). **This closes the local MVP.**
- **Step 7 (Phase A) — Terraform skeleton** — flat layout under [`infra/terraform/`](../infra/terraform/) (single HCP Terraform workspace `basis-vol-lab` in org `vsh852`, `cloudflare` + `aws` + `random` providers, AWS auth via OIDC dynamic credentials matching `~/dev/aws/bootstrap-oidc/`). `mise run tf:fmt` / `tf:validate` wired and `check` now depends on `tf:fmt`. New `.github/workflows/terraform.yml` runs `fmt -check` + `validate` on PRs touching `infra/terraform/**`. `terraform init -backend=false && terraform validate` passes locally. See [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).

## Abandoned

- **PySide6 desktop operator console** (originally `apps/desktop` + step 7 of the initial plan) — folder deleted, workspace member removed, all references purged. The web shell already exercises the same hiring signals (Python data stack, async IO, packaging) and the schedule is better spent on the validation report and deployed demo. Decision date: 2026-04-30.

## Deferred

- **Authenticated Deribit channels** (e.g. `ticker.*.raw`) — public `100ms` interval is sufficient for the MVP; revisit if/when we need raw-rate updates.
- **Always-on streaming snapshot loop** — MVP is one-shot snapshots via `mise run snapshot` or `POST /api/refresh`. A scheduled cron / background loop is a step-7 concern.
- **Binance COIN-margined futures, options, spot, user-data streams** — out of MVP scope.
- **Greek validation report** — step 5 validates IV only; once IV ties out, Greek mismatches against Deribit are unit conversions handled downstream. Add as a follow-on if useful.
- **SVI / SABR surface fits** — current MVP uses PCHIP smile interpolation; parametric fits are future research.
- **Backtests of the headline signals** — signals are interpretable on inspection; backtesting is deferred so we don't blow the schedule.
- **Rolling-percentile signals in `/api/signals`** — until the snapshot store has accumulated several weeks of history, the signals page surfaces the raw funding-vs-carry inputs and notes the limitation.
- **Historical replay page** — fifth page from the original plan; deferred behind cloud deployment.
- `mise run deploy` — wired when cloud deployment lands (step 7).

## Next

→ **Step 7 — Phase B (Cloudflare resources)**: provision the R2 bucket
(`basis-vol-lab-artifacts`, public access disabled, `parquet/**` lifecycle
rule), the D1 database (`basis-vol-lab-meta`, schema migrated from the
existing SQLite DDL via `wrangler d1 migrations`), and the Pages project
(`basis-vol-lab`, build `cd apps/web && npm ci && npm run build`, output
`apps/web/dist`, custom domain TBD, Pages Functions disabled, `_redirects`
rewrite to API Gateway). Phase A skeleton is in place; Phase B fills in
`infra/terraform/main.tf` + `outputs.tf`. Plan: [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).

## Notes

- **MVP is live locally.** `mise run snapshot && mise run api` (in one shell) plus `mise run web:dev` (in another) gives a fully functional dashboard at `http://localhost:5173`. `docker compose up --build` brings up the same stack on **OrbStack** (no extra config — OrbStack speaks the standard Docker socket; the bind mount on `./data` round-trips correctly via VirtIOFS).
- **Snapshot resilience** — `_safe_pull` wraps each Binance REST call so an IP rate-limit or 418 (`-1003 Way too many requests`) on `/futures/data/*` doesn't abort the whole snapshot; the affected card just renders empty and the next refresh recovers. Hit during step 6 dev when limit=288 tripped a temporary 30-hour ban; limits are now ≤100/period.

- **Production Binance WebSocket** — Initially hit silent timeouts from Hong Kong and assumed a geo-block. **Root cause was actually Binance's 2026-04-23 base-URL migration**: legacy `/ws` and `/stream` paths still accept connections and SUBSCRIBE ACKs but no longer deliver `/market` channels (markPrice, aggTrade, kline, ticker, forceOrder, etc.). Connector now uses `wss://fstream.binance.com/market/stream?streams=...` and works directly from HK with no VPN. Deployment caveat is just the formal Binance Futures restricted-country list (US, Canada, Netherlands, Cuba, Iran, North Korea, Crimea/Donetsk/Luhansk) — avoid AWS `us-east-1` / `us-west-2`; everything else (Tokyo, Singapore, Ireland, Frankfurt) is fine.
- **TickerSnapshot gained `expiry` and `strike` fields** in step 5 so option snapshots are self-describing for analytics. The Parquet schema (`TICKER_SCHEMA`) was extended to match; new files include both columns nullable.
- **Black-76 vs BSM** — Deribit's `mark_iv` is under Black-76 with `df = 1` (inverse-quoted premium). Our pricer matches to ~1e-3 vol points on liquid quotes. See [`docs/analytics/01-options-and-forward-pricing.md`](analytics/01-options-and-forward-pricing.md) for the full story.
