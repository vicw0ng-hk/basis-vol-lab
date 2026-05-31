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
infra/docker          Docker Compose for local development
docs/analytics        Learn-page markdown
tests                 Pytest suite
```

## Tooling

- Use `uv` for Python dependency and environment management.
- Use `mise` for project tasks and non-Python tool versions.
- Use `bun` as the JavaScript runtime and package manager.
- Use `biome` for TypeScript/React formatting and linting.
- Use `asyncio` for network I/O.
- Use NumPy/Pandas vectorization for analytics work.
- Keep cloud choices inside free tiers.

Common commands:

```bash
uvx ruff format .
uvx ruff check . --fix
uvx ty check
uv run pytest
bun --cwd apps/web biome format --write src/
bun --cwd apps/web biome check --write src/
bun --cwd apps/web tsc -b
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

## Development Workflow

Follow trunk-based development with short-lived feature branches.

> **Never commit directly to `master`.** Always create a feature branch
> first — even for one-line fixes. This applies to both human and
> AI-assisted work.

1. **Branch** – Create a feature branch from `master` **before making any
   changes**: `git checkout -b feat/<short-description>` (or `fix/`,
   `chore/`, `docs/`).
2. **Commit** – Make small, atomic commits with conventional messages
   (`feat:`, `fix:`, `chore:`, `docs:`). Keep each commit buildable.
3. **Check** – Run the full check suite before pushing (see below).
4. **Push & PR** – Push the branch and open a pull request against `master`.
   PR title should match the conventional commit style.
   Include a brief description of *what* and *why*.
5. **Review** – Address feedback, keep the branch up to date with `master`
   via rebase.
6. **Merge** – Squash-merge into `master`; delete the branch.

## Before Finishing Code Changes

Run, in order:

1. `uvx ruff format .`
2. `uvx ruff check . --fix`
3. `uvx ty check`
4. `uv run pytest`
5. `bun --cwd apps/web biome check --write src/` (if web code changed)
6. `bun --cwd apps/web tsc -b` (if web code changed)

`mise run check` runs all of the above plus Terraform format and validation.
