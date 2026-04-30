data "cloudflare_zone" "this" {
  filter = {
    name = var.domain
  }
}
