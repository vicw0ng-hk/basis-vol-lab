# basis-vol-lab

Cross-venue crypto-derivatives regime monitor ingesting Deribit options and Binance futures/perpetual data. Computes IV, skew, basis, funding, and regime metrics.

## Quick start

```bash
# Install dependencies
uv sync

# Run all checks (format, lint, typecheck, test)
mise run check

# Install pre-commit hooks
uv run pre-commit install
```

## Project structure

```
basis-vol-lab/
  apps/
    web/          # Static front end (Cloudflare Pages)
    api/          # Thin dynamic endpoints (AWS Lambda)
    desktop/      # Optional PySide6 operator console
  packages/
    connectors/   # Async WebSocket/REST collectors (Deribit, Binance)
    analytics/    # Pandas/NumPy/SciPy analytics & signal computation
    contracts/    # Data models, schemas, enums
    persistence/  # SQLite/D1 metadata, Parquet/R2 time-series
  infra/
    terraform/    # HCP Terraform, Cloudflare, AWS
  benchmarks/
  tests/
  docs/
  notebooks/
```

## Tooling

| Concern | Tool |
|---------|------|
| Python package/project management | `uv` |
| Non-Python tool versions | `mise` |
| Lint + format | `ruff` |
| Type checking | `pyright` |
| Testing | `pytest` |
| Pre-commit hooks | `pre-commit` |
| CI | GitHub Actions |
| IaC | Terraform (HCP Terraform) |
