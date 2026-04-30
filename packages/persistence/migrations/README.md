# D1 migrations

Schema for the Cloudflare D1 database that backs `D1MetadataStore` in
production. Mirrors the SQLite DDL embedded in
[`metadata.py`](../src/basis_persistence/metadata.py).

Apply with
[`wrangler`](https://developers.cloudflare.com/workers/wrangler/commands/#d1-migrations-apply):

```bash
# one-time: bind a wrangler.toml to the Terraform-provisioned database
wrangler d1 migrations apply basis-vol-lab-meta --remote
```

The Terraform stack (`infra/terraform/main.tf`) provisions
`cloudflare_d1_database.basis_meta` but does **not** apply migrations —
schema changes are intentionally a manual `wrangler` step so
`terraform apply` never blocks on them.
