# Terraform

Production infrastructure for `basis-vol-lab`.

## Stack

- Cloudflare Pages for the static dashboard.
- Cloudflare R2 for JSON artifacts and Parquet snapshots.
- Cloudflare D1 for metadata.
- AWS ECR, Lambda, API Gateway, and CloudWatch Logs for the API.
- HCP Terraform remote state and VCS-driven plans.

## Layout

```text
backend.tf      HCP Terraform backend
providers.tf    Cloudflare, AWS, random
variables.tf    Input variables
main.tf         Resources
outputs.tf      Runtime outputs
```

The repo uses a flat production-only layout. Add modules or additional
environment directories only if a second environment becomes real.

## HCP Terraform Setup

Create a workspace named `basis-vol-lab` in the `vsh852` organization. Use the
version-control workflow with working directory `infra/terraform` and trigger
pattern `infra/terraform/**`.

Workspace variables:

- `TFC_AWS_PROVIDER_AUTH=true`
- `TFC_AWS_RUN_ROLE_ARN=<workspace AWS OIDC role ARN>`
- `cloudflare_api_token=<Cloudflare token>` marked sensitive
- `lambda_image_pushed=true` after the first Lambda image exists in ECR

R2 access keys are runtime credentials, not Terraform inputs. Put them in the
Lambda environment through Terraform variables and in GitHub Actions secrets
for the snapshot workflow.

## Local Checks

```bash
terraform -chdir=infra/terraform init -backend=false -input=false
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
```

`mise run tf:fmt` and `mise run tf:validate` wrap these commands. HCP
Terraform owns production plan/apply on merges to `master`.
