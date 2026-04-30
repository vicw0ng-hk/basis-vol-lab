# `infra/terraform/` — Phase A skeleton

Provisions the cost-aware deployment for `basis-vol-lab`:
Cloudflare Pages + R2 + D1 and AWS Lambda + API Gateway. Plan lives in
[`docs/planning/8.cloud-plan.md`](../../docs/planning/8.cloud-plan.md).

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
   Pages:Edit, R2:Edit, D1:Edit, Workers:Edit, Zone:DNS:Edit on the demo
   zone, then set workspace **terraform** variables:

   - `cloudflare_api_token` (sensitive)
   - `cloudflare_account_id`
   - `cloudflare_zone_id` (only once a custom domain is chosen)
   - `domain` (only once a custom domain is chosen)

R2 S3-compatible access keys (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`)
are consumed by the Lambda runtime and GitHub Actions, **not** by
Terraform. They are added in Phase B once the bucket exists.

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
