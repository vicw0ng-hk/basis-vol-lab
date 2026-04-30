provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

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
