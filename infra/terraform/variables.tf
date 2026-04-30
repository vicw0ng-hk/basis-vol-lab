variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token. Scopes: Pages:Edit, R2:Edit, D1:Edit, Workers:Edit, Zone:DNS:Edit on the vsh852.com zone."
  sensitive   = true
}

variable "domain" {
  type        = string
  description = "Public custom domain for the Pages site. Lookup key for the cloudflare_zone data source."
  default     = "vsh852.com"
}

variable "subdomain" {
  type        = string
  description = "Subdomain hosting the deployed demo (e.g. basis.vsh852.com)."
  default     = "basis"
}

variable "aws_region" {
  type        = string
  description = "AWS region for Lambda + ECR."
  default     = "ap-east-1"
}

variable "project_name" {
  type        = string
  description = "Short project slug used as a prefix for cloud resources."
  default     = "basis-vol-lab"
}

variable "lambda_image_pushed" {
  type        = bool
  description = <<-EOT
    Phase C bootstrap gate. While `false`, Terraform provisions ECR + IAM
    + the log group only. After running `mise run lambda:push` to publish
    the first image to ECR, flip this to `true` (set the variable in the
    HCP Terraform workspace UI and queue a new plan) so the Lambda + API
    Gateway + Pages `VITE_API_URL` resources can be created against the
    image that now exists.
  EOT
  default     = false
}
