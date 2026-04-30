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

  # Cloudflare Pages assigns `<project>.pages.dev` deterministically. We
  # depend on this string in CORS + Lambda env *without* taking a graph
  # edge on the Pages resource, because Pages itself depends on the API
  # Gateway URL (baked into the SPA at build time as VITE_API_URL) and
  # we'd otherwise get a cycle.
  pages_origin = "https://${var.project_name}.pages.dev"
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

  # Scope the build to `apps/web/`. Pages auto-detects build tooling at
  # `root_dir`, so this hides the workspace-root `pyproject.toml` from
  # the detector — that file is a uv workspace manifest, not a
  # setuptools project, and Pages would otherwise abort with
  # "Multiple top-level packages discovered in a flat-layout". The
  # `apps/web/pyproject.toml` left in scope only declares the workspace
  # member; it has no runtime deps and `pip install .` is a near-no-op.
  build_config = {
    build_caching   = true
    build_command   = "npm ci && npm run build"
    destination_dir = "dist"
    root_dir        = "apps/web"
  }

  # Belt-and-suspenders: tell Pages to skip its dependency-install step
  # entirely so we depend only on the explicit `npm ci` above.
  #
  # `VITE_API_URL` is baked into the SPA bundle at build time and points
  # at the API Gateway invoke URL provisioned below. The SPA calls it
  # cross-origin; CORS is opened on the Lambda side to the pages.dev
  # subdomain. While `var.lambda_image_pushed` is false (Phase C
  # bootstrap, before the first image is in ECR) the API Gateway does
  # not yet exist, so the env var is set to a harmless empty string and
  # the SPA's relative-path proxy + same-origin assumption still keeps
  # it functional from `localhost`.
  deployment_configs = {
    production = {
      env_vars = {
        SKIP_DEPENDENCY_INSTALL = {
          type  = "plain_text"
          value = "true"
        }
        VITE_API_URL = {
          type  = "plain_text"
          value = var.lambda_image_pushed ? aws_apigatewayv2_api.basis_api[0].api_endpoint : ""
        }
      }
    }
    preview = {
      env_vars = {
        SKIP_DEPENDENCY_INSTALL = {
          type  = "plain_text"
          value = "true"
        }
        VITE_API_URL = {
          type  = "plain_text"
          value = var.lambda_image_pushed ? aws_apigatewayv2_api.basis_api[0].api_endpoint : ""
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

# ── AWS Lambda + API Gateway (Phase C) ──────────────────────────────────
#
# Container-packaged FastAPI service. The Pages SPA calls the API
# Gateway invoke URL cross-origin; CORS is opened on the Lambda side to
# the pages.dev subdomain. The `image_uri` is bootstrapped to the latest
# tag in the project ECR repo, and `lifecycle.ignore_changes` keeps
# Terraform from fighting subsequent `aws lambda update-function-code`
# deploys driven by `mise run lambda:push`.

resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}/api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 7 days."
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-api-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project_name}-api"
  retention_in_days = 3
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "${var.project_name}-api-lambda-logs"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      Resource = "${aws_cloudwatch_log_group.api.arn}:*"
    }]
  })
}

resource "aws_lambda_function" "api" {
  count = var.lambda_image_pushed ? 1 : 0

  function_name = "${var.project_name}-api"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:latest"
  architectures = ["arm64"]
  memory_size   = 1024
  timeout       = 30

  ephemeral_storage {
    size = 1024
  }

  environment {
    variables = {
      BASIS_DATA_DIR         = "/tmp/data"
      BASIS_CORS_ORIGINS     = local.pages_origin
      BASIS_ARTIFACT_BACKEND = "local" # flips to "r2" in Phase D
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }

  depends_on = [
    aws_iam_role_policy.lambda_logs,
    aws_cloudwatch_log_group.api,
  ]
}

resource "aws_apigatewayv2_api" "basis_api" {
  count = var.lambda_image_pushed ? 1 : 0

  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [local.pages_origin]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "basis_api" {
  count = var.lambda_image_pushed ? 1 : 0

  api_id                 = aws_apigatewayv2_api.basis_api[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  count = var.lambda_image_pushed ? 1 : 0

  api_id    = aws_apigatewayv2_api.basis_api[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.basis_api[0].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  count = var.lambda_image_pushed ? 1 : 0

  api_id      = aws_apigatewayv2_api.basis_api[0].id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  count = var.lambda_image_pushed ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.basis_api[0].execution_arn}/*/*"
}
