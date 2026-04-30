# `infra/terraform/` — Phase B

Provisions the cost-aware deployment for `basis-vol-lab`:
Cloudflare Pages + R2 + D1 and AWS Lambda + API Gateway. Plan lives in
[`docs/planning/8.cloud-plan.md`](../../docs/planning/8.cloud-plan.md).

Phase A wired the skeleton (providers, HCP Terraform backend, zone
lookup). Phase B adds the Cloudflare resources:

- `cloudflare_r2_bucket.artifacts` — `basis-vol-lab-artifacts`, `apac`,
  `Standard` storage class, public access disabled.
- `cloudflare_r2_bucket_lifecycle.artifacts` — single rule that deletes
  objects under `parquet/` after 30 days and aborts dangling multipart
  uploads after 24 h.
- `cloudflare_d1_database.meta` — `basis-vol-lab-meta`, primary location
  hint `apac`. Schema is migrated separately (see "Open follow-ups").
- `cloudflare_pages_project.web` — `basis-vol-lab` Pages project, GitHub
  source `vicw0ng-hk/basis-vol-lab`, production branch `master`, build
  command `cd apps/web && npm ci && npm run build`, output
  `apps/web/dist`. Pages Functions are not configured — dynamic traffic
  goes to Lambda via a `_redirects` rule shipped with the static bundle
  (added in Phase C).

## Layout

```
infra/terraform/
  backend.tf      # HCP Terraform cloud block (org=vsh852, workspace=basis-vol-lab)
  providers.tf    # cloudflare, aws (OIDC), random
  variables.tf    # input variables
  main.tf         # resources (added in phases B–F)
  outputs.tf      # outputs  (added in phases B–F)
```

We deviated from the plan's `environments/prod/` + `modules/` nesting in
favour of a flat layout — prod is the only environment, and the project
fits comfortably in one workspace. If we ever need staging, we add a
parallel directory or use TFC workspace tagging.

## HCP Terraform workspace setup (one-time)

Owner of the AWS / Cloudflare accounts performs these manually:

1. Create workspace `basis-vol-lab` in the `vsh852` organization with the
   **Version control workflow** pointing at this repo, working directory
   `infra/terraform`, and trigger pattern `infra/terraform/**`.
2. **AWS auth — OIDC dynamic credentials** (preferred). Follow
   `~/dev/aws/bootstrap-oidc/` to create an IAM OIDC provider + run role
   for this workspace, then set workspace **env** variables:

   - `TFC_AWS_PROVIDER_AUTH=true`
   - `TFC_AWS_RUN_ROLE_ARN=<arn from bootstrap-oidc>`

3. **Cloudflare auth — API token**. Create a token scoped to
   Pages:Edit, R2:Edit, D1:Edit, Workers:Edit, Zone:DNS:Edit on
   `vsh852.com`, then set the workspace **terraform** variable:

   - `cloudflare_api_token` (sensitive)

   Account and zone IDs are discovered at plan time via a
   `data "cloudflare_zone"` block keyed on `var.domain` (default
   `vsh852.com`) — no need to copy them into TFC.

R2 S3-compatible access keys (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`)
are consumed by the Lambda runtime and GitHub Actions, **not** by
Terraform. They are provisioned manually in the Cloudflare dashboard
(R2 → "Manage API tokens") once the bucket exists, then mirrored into
the Lambda env (Phase C) and the GitHub Actions secrets store
(Phase E).

## Open follow-ups (Phase B leftovers)

- **D1 schema migrations.** A `packages/persistence/migrations/` folder
  with the `instruments` + `collection_runs` DDL extracted from
  `MetadataStore` is still TODO; it will be applied via
  `wrangler d1 migrations apply ${var.project_name}-meta` once the
  `D1MetadataStore` sibling lands in Phase D.
- **Pages → GitHub link.** The `cloudflare_pages_project.web` resource
  assumes the Cloudflare account already has the
  `vicw0ng-hk/basis-vol-lab` GitHub installation authorised for Pages.
  This must be done once via the dashboard before `terraform apply`.
- **Custom domain (`basis.vsh852.com`).** Wired in Phase F together
  with the API Gateway DNS record.

## Local checks

`terraform validate` runs against the skeleton without contacting HCP
Terraform — backend init is skipped:

```bash
cd infra/terraform
terraform init -backend=false
terraform validate
terraform fmt -check -recursive
```

`mise run tf:fmt` and `mise run tf:validate` wrap the above. CI runs
`fmt -check` + `validate` on every PR; HCP Terraform owns plan/apply
on merges to `main`.
