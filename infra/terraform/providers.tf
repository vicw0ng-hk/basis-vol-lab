provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# AWS auth comes from HCP Terraform dynamic credentials (OIDC).
# The workspace must define env vars TFC_AWS_PROVIDER_AUTH=true and
# TFC_AWS_RUN_ROLE_ARN=<role arn>. See infra/terraform/README.md.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "basis-vol-lab"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}
