# Phase B — Cloudflare resources (R2 artifact bucket, D1 metadata DB,
# Pages project for the static SPA). See docs/planning/8.cloud-plan.md.
#
# All three sit on Cloudflare's free tier:
#   • R2: 10 GB-month storage, 1M Class A / 10M Class B ops/month, 0 egress.
#   • D1: 100 k row writes/day, 5 M row reads/day. Metadata only — never
#         a sink for raw market data.
#   • Pages: unlimited static-asset requests, free preview deploys.
#
# AWS resources (Lambda, API Gateway, ECR) land in Phase C.

locals {
  account_id = data.cloudflare_zone.this.account.id
  zone_id    = data.cloudflare_zone.this.id
}

# ── R2 artifact bucket ──────────────────────────────────────────────────
#
# Holds curated JSON snapshots (`artifacts/*.json`) plus optional Parquet
# rollups under `parquet/`. Public access is disabled — the SPA reads via
# the Pages → API Gateway rewrite, never directly from r2.dev.

resource "cloudflare_r2_bucket" "basis_artifacts" {
  account_id    = local.account_id
  name          = "${var.project_name}-artifacts"
  location      = "apac"
  storage_class = "Standard"
}

# Parquet rollups age out after 30 days; JSON artifacts are overwritten in
# place by each snapshot run and never accumulate, so no rule for them.
resource "cloudflare_r2_bucket_lifecycle" "basis_artifacts" {
  account_id  = local.account_id
  bucket_name = cloudflare_r2_bucket.basis_artifacts.name

  rules = [
    {
      id      = "expire-parquet-after-30d"
      enabled = true
      conditions = {
        prefix = "parquet/"
      }
      delete_objects_transition = {
        condition = {
          type    = "Age"
          max_age = 30 * 24 * 60 * 60
        }
      }
      abort_multipart_uploads_transition = {
        condition = {
          type    = "Age"
          max_age = 24 * 60 * 60
        }
      }
    },
  ]
}

# ── D1 metadata database ────────────────────────────────────────────────
#
# Holds the same `instruments` and `collection_runs` tables that
# `MetadataStore` produces locally (D1 is SQLite under the hood). Schema
# migrations are applied separately via `wrangler d1 migrations apply`
# from `packages/persistence/migrations/` once that directory exists.

resource "cloudflare_d1_database" "basis_meta" {
  account_id            = local.account_id
  name                  = "${var.project_name}-meta"
  primary_location_hint = "apac"
  read_replication = {
    mode = "disabled"
  }
}

# ── Pages project ───────────────────────────────────────────────────────
#
# Builds the Vite/React/Tailwind SPA from `apps/web/` on every push to the
# production branch and on pull requests. Pages Functions are not
# configured — all dynamic traffic is rewritten to the Lambda + API
# Gateway via a static `_redirects` rule shipped inside `apps/web/dist/`.
#
# Requires that the operator has connected the GitHub account
# `vicw0ng-hk` to Cloudflare Pages once via the dashboard — Terraform
# cannot bootstrap that link.

resource "cloudflare_pages_project" "basis_web" {
  account_id        = local.account_id
  name              = var.project_name
  production_branch = "master"

  build_config = {
    build_caching   = true
    build_command   = "cd apps/web && npm ci && npm run build"
    destination_dir = "apps/web/dist"
    root_dir        = "/"
  }

  # Cloudflare Pages auto-detects build tooling at the repo root and
  # otherwise tries `pip install .` against the top-level pyproject.toml,
  # which fails because the uv workspace root is not a setuptools project.
  # `SKIP_DEPENDENCY_INSTALL` short-circuits that auto-install — `npm ci`
  # in the build command is the only dependency step we need.
  deployment_configs = {
    production = {
      env_vars = {
        SKIP_DEPENDENCY_INSTALL = {
          type  = "plain_text"
          value = "true"
        }
      }
    }
    preview = {
      env_vars = {
        SKIP_DEPENDENCY_INSTALL = {
          type  = "plain_text"
          value = "true"
        }
      }
    }
  }

  source = {
    type = "github"
    config = {
      owner                          = "vicw0ng-hk"
      repo_name                      = var.project_name
      production_branch              = "master"
      production_deployments_enabled = true
      pr_comments_enabled            = true
      preview_deployment_setting     = "all"
    }
  }
}
