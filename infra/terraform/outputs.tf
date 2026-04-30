# Cloudflare zone — looked up by domain so account/zone IDs don't have to
# be set manually as workspace variables.
output "cloudflare_account_id" {
  description = "Cloudflare account ID owning the vsh852.com zone."
  value       = data.cloudflare_zone.this.account.id
}

output "cloudflare_zone_id" {
  description = "Cloudflare DNS zone ID for var.domain."
  value       = data.cloudflare_zone.this.id
}

# Resource outputs land alongside their resources in phases B–F.
