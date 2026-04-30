# Copilot Instructions - Basis & Vol Lab

## Project

Crypto-derivatives regime monitor for Deribit options and Binance
USD-margined futures/perpetuals. The deployed stack is Cloudflare Pages/R2/D1
plus AWS Lambda/API Gateway, managed with Terraform through HCP Terraform.

Read [docs/progress.md](../docs/progress.md) before choosing follow-up work.

## Repo Shape

```text
apps/web          Vite + React dashboard
apps/api          FastAPI + Mangum API
packages/connectors   Deribit/Binance async clients
packages/analytics    Pricing, IV, Greeks, RV, carry, surface, signals
packages/contracts    Shared models and enums
packages/persistence  SQLite/D1 metadata and Parquet/R2 storage
infra/terraform       Cloudflare and AWS infrastructure
docs/analytics        Learn-page markdown
tests                 Pytest suite
```

## Tooling

- Use `uv` for Python dependency and environment management.
- Use `mise` for project tasks and non-Python tool versions.
- Use `asyncio` for network I/O.
- Use NumPy/Pandas vectorization for analytics work.
- Keep cloud choices inside free tiers.

Common commands:

```bash
uvx ruff format .
uvx ruff check . --fix
uvx pyright
uv run pytest
mise run check
```

## Coding Standards

- Keep changes small and consistent with the surrounding package.
- Type all public function signatures.
- Keep public Python docstrings concise and useful.
- Prefer existing helpers, models, and package boundaries.
- Add or update tests for behavior changes.
- Do not use D1 as a raw market-data sink.
- Do not add paid always-on infrastructure.

## Documentation

- Keep README and Learn content user-facing.
- Keep [docs/progress.md](../docs/progress.md) short: current status, known
  limits, and next candidates only.
- Remove build-history notes once they are no longer needed for operation.

## Before Finishing Code Changes

Run, in order:

1. `uvx ruff format .`
2. `uvx ruff check . --fix`
3. `uvx pyright`
4. `uv run pytest`

`mise run check` runs the same project-level checks plus Terraform format and
validation.
