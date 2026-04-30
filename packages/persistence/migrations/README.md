# D1 Migrations

SQL schema for the Cloudflare D1 metadata database. The schema mirrors the
SQLite tables used by `MetadataStore`.

Apply migrations with:

```bash
export CLOUDFLARE_API_TOKEN=<token-with-D1:Edit-scope>
mise run d1:migrate
```

Migration files are idempotent. Terraform provisions the database; this task
applies the schema.
