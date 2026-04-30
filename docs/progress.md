# Progress

## Completed

- **Step 1** — repo scaffold, uv workspace, mise tooling, ruff/pyright/pytest pipeline.
- **Step 2** — local data model (SQLite metadata + Parquet time-series).
- **Step 3** — Deribit connector (REST instrument discovery + WebSocket ticker stream with heartbeats and reconnect).
- **Step 4** — Binance connector (REST instrument discovery + funding/basis/OI backfills + mark-price WebSocket stream).
- **Step 5** — Analytics package: Black-76 pricer + IV inversion (Brent) + analytic Greeks + realized-vol estimators + carry/funding helpers + smile/term-structure interpolation + the three headline signals + an IV-validation CLI. Live validation against Deribit shows p95 IV error < 0.005 vol points on liquid expiries (30D+). Six-lecture markdown course under [`docs/analytics/`](analytics/README.md).
- **Step 6 — MVP product shell** — snapshot orchestrator (`basis_api.snapshot`) wires connectors → `TimeSeriesStore` and emits curated JSON artifacts; FastAPI service (`basis_api.main`) serves the artifacts and exposes `POST /api/refresh`; Vite/React/Tailwind v4 SPA with light/dark toggle and four pages (Overview, Volatility, Carry, Signals); Dockerfiles for both apps and a `compose.yaml` that runs end-to-end on **OrbStack**. **This closes the local MVP.**
- **Step 7 (Phase A) — Terraform skeleton** — flat layout under [`infra/terraform/`](../infra/terraform/) (single HCP Terraform workspace `basis-vol-lab` in org `vsh852`, `cloudflare` + `aws` + `random` providers, AWS auth via OIDC dynamic credentials matching `~/dev/aws/bootstrap-oidc/`, Cloudflare account/zone IDs discovered at plan time via `data "cloudflare_zone"` keyed on `var.domain` (`vsh852.com`)). `mise run tf:fmt` / `tf:validate` wired and `check` now depends on `tf:fmt`. CI consolidated into a single [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) with a `terraform-fmt-validate` job (action versions bumped to current latest: `actions/checkout@v6`, `astral-sh/setup-uv@v8`, `hashicorp/setup-terraform@v4`). TFC workspace and OIDC role configured by the operator; first remote plan succeeds. See [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).
- **Step 7 (Phase B) — Cloudflare resources** — [`infra/terraform/main.tf`](../infra/terraform/main.tf) defines `cloudflare_r2_bucket.basis_artifacts` (`basis-vol-lab-artifacts`, apac, public access disabled), `cloudflare_r2_bucket_lifecycle.basis_artifacts` (deletes `parquet/` objects after 30 days, aborts dangling multipart uploads after 24 h), `cloudflare_d1_database.basis_meta` (`basis-vol-lab-meta`, apac primary), and `cloudflare_pages_project.basis_web` (`basis-vol-lab`, GitHub source `vicw0ng-hk/basis-vol-lab`, prod branch `master`, `root_dir=apps/web`, build `npm ci && npm run build` → `dist`, Pages Functions disabled, `SKIP_DEPENDENCY_INSTALL=true` env var on prod+preview deploy configs). First production deploy is live at `https://basis-vol-lab.pages.dev/`. See [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).
- **Step 7 (Phase C) — AWS Lambda + API Gateway** — [`infra/terraform/main.tf`](../infra/terraform/main.tf) defines `aws_ecr_repository.api` (`basis-vol-lab/api`, mutable, scan-on-push, untagged-after-7-days lifecycle), `aws_iam_role.lambda_exec` with a least-privilege inline policy for CloudWatch Logs only, `aws_cloudwatch_log_group.api` (`/aws/lambda/basis-vol-lab-api`, 3-day retention), `aws_lambda_function.api` (container `package_type=Image`, `arm64`, 1024 MB / 30 s / 1 GB ephemeral, `lifecycle.ignore_changes=[image_uri]`), and an `aws_apigatewayv2_api` (HTTP API, `$default` route → Lambda integration, CORS pinned to `https://basis-vol-lab.pages.dev`). The Lambda + APIGW + Pages `VITE_API_URL` env var are gated on a TFC workspace variable `lambda_image_pushed` (default `false`) — the HCP Terraform workspace is VCS-driven so `terraform apply -target=...` from the laptop isn't available; the gate expresses the two-phase apply that ECR bootstrap demands. Bootstrap completed 2026-05-01: (1) PR with `lambda_image_pushed=false` merged → TFC created ECR + IAM + log group, (2) `mise run lambda:push` built and pushed the first arm64 image, (3) flipped `lambda_image_pushed=true` in the TFC UI → TFC created Lambda + APIGW and updated the Pages env var. Smoke test (`curl $API_URL/healthz`, `POST /api/refresh`, `GET /api/overview`) green against the live `https://<api-id>.execute-api.ap-east-1.amazonaws.com` invoke URL. New [`apps/api/Dockerfile.lambda`](../apps/api/Dockerfile.lambda) (uv-managed builder + `awslambdaric` on `python:3.14-slim`). New mise tasks `lambda:build` / `lambda:push` / `lambda:update` derive ECR URL + login from `aws sts get-caller-identity`. See [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).

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
- **D1 schema migrations directory (`packages/persistence/migrations/`).** Generated from the SQLite DDL once the `D1MetadataStore` sibling lands in Phase D; until then the local SQLite path is the only live MetadataStore implementation.
- **R2 artifact backend in `basis_api`.** Lambda is live (Phase C
  done) but still reads/writes local `/tmp/data`, so a single warm
  container is required for a refresh + read round trip. Phase D
  switches `_load`/`run_snapshot` to an `ArtifactStore` protocol with
  `LocalArtifactStore` + `R2ArtifactStore` implementations and adds
  the `D1MetadataStore` sibling.
- **Pages `_redirects` rewrite for `/api/*`.** Replaced by a `VITE_API_URL` env var in the Pages deployment config — the SPA calls API Gateway cross-origin and CORS is open to the pages.dev subdomain. No `_redirects` file is shipped.

## Next

→ **Step 7 — Phase D (R2/D1 wiring)**. Lambda is live but still
reads/writes `/tmp/data`, so each cold start sees an empty artifacts
dir until the first `POST /api/refresh` repopulates it. Phase D:
introduce an `ArtifactStore` protocol in `basis_api.storage` with
`LocalArtifactStore` + `R2ArtifactStore` (boto3 against the R2
S3-compatible endpoint) implementations, switch
`snapshot.run_snapshot` and `_load` to it, add the `D1MetadataStore`
sibling in `basis_persistence`, ship the
`packages/persistence/migrations/` directory, set
`BASIS_ARTIFACT_BACKEND=r2` + `R2_*` env vars on the Lambda, and
add the GitHub Actions `*/15` snapshot cron (Phase E in the cloud
plan). Plan: [`docs/planning/8.cloud-plan.md`](planning/8.cloud-plan.md).

## Notes

- **MVP is live locally.** `mise run snapshot && mise run api` (in one shell) plus `mise run web:dev` (in another) gives a fully functional dashboard at `http://localhost:5173`. `docker compose up --build` brings up the same stack on **OrbStack** (no extra config — OrbStack speaks the standard Docker socket; the bind mount on `./data` round-trips correctly via VirtIOFS).
- **Snapshot resilience** — `_safe_pull` wraps each Binance REST call so an IP rate-limit or 418 (`-1003 Way too many requests`) on `/futures/data/*` doesn't abort the whole snapshot; the affected card just renders empty and the next refresh recovers. Hit during step 6 dev when limit=288 tripped a temporary 30-hour ban; limits are now ≤100/period.

- **Production Binance WebSocket** — Initially hit silent timeouts from Hong Kong and assumed a geo-block. **Root cause was actually Binance's 2026-04-23 base-URL migration**: legacy `/ws` and `/stream` paths still accept connections and SUBSCRIBE ACKs but no longer deliver `/market` channels (markPrice, aggTrade, kline, ticker, forceOrder, etc.). Connector now uses `wss://fstream.binance.com/market/stream?streams=...` and works directly from HK with no VPN. Deployment caveat is just the formal Binance Futures restricted-country list (US, Canada, Netherlands, Cuba, Iran, North Korea, Crimea/Donetsk/Luhansk) — avoid AWS `us-east-1` / `us-west-2`; everything else (Tokyo, Singapore, Ireland, Frankfurt) is fine.
- **TickerSnapshot gained `expiry` and `strike` fields** in step 5 so option snapshots are self-describing for analytics. The Parquet schema (`TICKER_SCHEMA`) was extended to match; new files include both columns nullable.
- **Black-76 vs BSM** — Deribit's `mark_iv` is under Black-76 with `df = 1` (inverse-quoted premium). Our pricer matches to ~1e-3 vol points on liquid quotes. See [`docs/analytics/01-options-and-forward-pricing.md`](analytics/01-options-and-forward-pricing.md) for the full story.
- **Phase B Pages cutover gotchas (2026-05-01).** Three things bit on the first deploy: (1) Cloudflare Pages auto-detected Python at the repo root and ran `pip install .` against the workspace `pyproject.toml`, which failed setuptools' flat-layout check — fixed by setting `root_dir = "apps/web"` so the detector only sees the web project's manifest, plus an explicit `[tool.setuptools] packages=[]` in `apps/web/pyproject.toml` and `SKIP_DEPENDENCY_INSTALL=true` as belt-and-suspenders. (2) The `cloudflare_pages_project` resource doesn't accept `deployments_enabled` (deprecated) — drop it. (3) The repo's root `.gitignore` had a generic `lib/` rule (Python build artefact) that was also matching `apps/web/src/lib/`, so four front-end utility modules (`api.ts`, `format.ts`, `lectures.ts`, `theme.tsx`) were never committed and the Pages tsc step exploded with `TS2307: Cannot find module '../lib/api'`. Fix: anchor the rule to `/lib/` (and `/lib64/`).
- **Phase B end-state.** Pages site renders at `https://basis-vol-lab.pages.dev/` and shows "Failed to load data — Unexpected token '<'" on every page. This is expected: `/api/*` falls through to the Pages 404 HTML until Phase C wires the `_redirects` rule + Lambda + R2. Local dashboards still work via `mise run snapshot && mise run api && mise run web:dev`.
