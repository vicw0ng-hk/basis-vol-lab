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
  description = "AWS region for Lambda + ECR. Tokyo by default — outside Binance's restricted-country list and close to HK."
  default     = "ap-northeast-1"
}

variable "project_name" {
  type        = string
  description = "Short project slug used as a prefix for cloud resources."
  default     = "basis-vol-lab"
}
