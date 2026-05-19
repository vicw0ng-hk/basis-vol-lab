# --------------------------------------------------------------------
# Build stage
#
# Build context is the repo root (see compose.yaml) so that we can copy
# the shared lecture markdown under `docs/analytics/` into the bundle —
# the Learn page imports those .md files at build time via Vite's
# `import.meta.glob('?raw')`.
# --------------------------------------------------------------------
FROM oven/bun:1.3-alpine AS builder
WORKDIR /app

COPY apps/web/package.json apps/web/bun.lock* ./
RUN bun install --frozen-lockfile

COPY apps/web/tsconfig.json apps/web/vite.config.ts apps/web/index.html ./
COPY apps/web/public ./public
COPY apps/web/src ./src
# Lecture content lives outside apps/web; mirror the repo layout under
# /app so the relative glob in src/lib/lectures.ts resolves identically
# in dev and in the container build.
COPY docs/analytics /docs/analytics

RUN bun run build

# --------------------------------------------------------------------
# Runtime stage: nginx serving static dist/
# --------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
