variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token. Scopes: Pages:Edit, R2:Edit, D1:Edit, Workers:Edit, Zone:DNS:Edit on the demo zone."
  sensitive   = true
}

variable "cloudflare_account_id" {
  type        = string
  description = "Cloudflare account ID owning the Pages project, R2 bucket, and D1 database."
}

variable "cloudflare_zone_id" {
  type        = string
  description = "Cloudflare DNS zone ID used for the public custom domain."
  default     = ""
}

variable "domain" {
  type        = string
  description = "Public custom domain for the Pages site (e.g. basis.example.dev). Empty means use the generated *.pages.dev URL."
  default     = ""
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
