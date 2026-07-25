terraform {
  required_version = ">= 1.15.0"

  cloud {
    organization = "vsh852"
    workspaces {
      name = "basis-vol-lab"
    }
  }

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.22"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.56"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
  }
}
