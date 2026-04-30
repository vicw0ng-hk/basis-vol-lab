# D1 migrations

Schema for the Cloudflare D1 database that backs `D1MetadataStore` in
production. Mirrors the SQLite DDL embedded in
[`metadata.py`](../src/basis_persistence/metadata.py).

Apply with the project's mise task — it loops every `*.sql` file in this
directory through the D1 REST API, no `wrangler` / `wrangler.toml` /
Node.js needed:

```bash
export CLOUDFLARE_API_TOKEN=<token-with-D1:Edit-scope>
mise run d1:migrate
```

The DDL is intentionally idempotent (`CREATE TABLE IF NOT EXISTS`,
`CREATE INDEX IF NOT EXISTS`), so re-running the task is safe.

The Terraform stack ([`infra/terraform/main.tf`](../../../infra/terraform/main.tf))
provisions `cloudflare_d1_database.basis_meta` but does **not** apply
migrations — schema changes are intentionally a manual step so
`terraform apply` never blocks on them.
