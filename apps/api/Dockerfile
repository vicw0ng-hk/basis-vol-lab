# --------------------------------------------------------------------
# Builder stage: install deps with uv, sync the basis-api workspace
# --------------------------------------------------------------------
FROM python:3.14-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONDONTWRITEBYTECODE=1

# uv: official static binary
COPY --from=ghcr.io/astral-sh/uv:0.5.8 /uv /usr/local/bin/uv

WORKDIR /app

# Copy lockfile + workspace manifests first (better Docker cache)
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/persistence/pyproject.toml packages/persistence/pyproject.toml
COPY packages/connectors/pyproject.toml packages/connectors/pyproject.toml
COPY packages/analytics/pyproject.toml packages/analytics/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/web/pyproject.toml apps/web/pyproject.toml

# Source for workspace members the API depends on
COPY packages/contracts/src packages/contracts/src
COPY packages/persistence/src packages/persistence/src
COPY packages/connectors/src packages/connectors/src
COPY packages/analytics/src packages/analytics/src
COPY apps/api/src apps/api/src

RUN uv sync --frozen --package basis-api --no-dev

# --------------------------------------------------------------------
# Runtime stage
# --------------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    BASIS_DATA_DIR=/app/data

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 8000

CMD ["uvicorn", "basis_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
