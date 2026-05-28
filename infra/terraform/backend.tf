terraform {
  required_version = ">= 1.5.0"

  cloud {
    organization = "vsh852"
    workspaces {
      name = "basis-vol-lab"
    }
  }

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.19"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
