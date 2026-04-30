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

# ── Phase B — Cloudflare resources ──────────────────────────────────────

output "r2_bucket_name" {
  description = "R2 bucket holding curated JSON artifacts and Parquet rollups."
  value       = cloudflare_r2_bucket.basis_artifacts.name
}

output "r2_endpoint_url" {
  description = "S3-compatible endpoint for the R2 bucket. Used by Lambda + GitHub Actions."
  value       = "https://${data.cloudflare_zone.this.account.id}.r2.cloudflarestorage.com"
}

output "d1_database_id" {
  description = "UUID of the D1 metadata database. Wire into wrangler.toml + Lambda env."
  value       = cloudflare_d1_database.basis_meta.id
}

output "d1_database_name" {
  description = "Name of the D1 metadata database."
  value       = cloudflare_d1_database.basis_meta.name
}

output "pages_project_name" {
  description = "Cloudflare Pages project name."
  value       = cloudflare_pages_project.basis_web.name
}

output "pages_subdomain" {
  description = "Default <project>.pages.dev hostname assigned by Cloudflare."
  value       = cloudflare_pages_project.basis_web.subdomain
}
