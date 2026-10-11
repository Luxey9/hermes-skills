# Schema & Data Extraction from a PostgREST / Supabase API

Everything below is read-only HTTP against `https://<ref>.supabase.co`.
Requires the project's **service_role** key (anon returns 401 on the spec and is
RLS-filtered on data). Load it into a shell/python variable; never print it.

## 1. The OpenAPI spec is the schema

```bash
curl -s "$URL/rest/v1/" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" \
  -H "Accept: application/openapi+json" > openapi.json
```

- 200 with a large JSON body ⇒ parse it. Tables/views live under
  `definitions` (older PostgREST) or `components.schemas` (newer). Handle both:
  `defs = d.get("definitions") or d.get("components",{}).get("schemas",{})`.
- 401 `"Only the service_role API key can be used for this endpoint"` ⇒ wrong key.

## 2. Field mapping (per column)

For each `table`, `defs[table]["properties"][col]`:

| Spec field | Meaning |
|---|---|
| `format` | Postgres type (`character varying`, `text`, `integer`, `bigint`, `timestamp with time zone`, `uuid`, `jsonb`, `numeric`, `double precision`, `time without time zone`, …) |
| `maxLength` | varchar length, when present |
| `default` | column default expression |
| `description` | contains `<pk/>` for primary key and `<fk table='x' column='y'/>` for foreign keys — regex them out |
| NOT NULL | the column name appears in `defs[table]["required"]` |

`defs[table]` with no `properties` (or `type: object` only) is usually a view or
a table with no exposed columns.

Suggested outputs (all derived from the one spec fetch):
- `schema.csv` — columns: table, column, type, max_length, nullable, default, pk, fk
- `schema_report.txt` — human-readable, grouped per table with row counts
- `schema.json` — the raw `definitions` for later re-parsing

## 3. Row counts (exact, no row transfer)

```bash
curl -sI "$URL/rest/v1/$TABLE?select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" \
  -H "Prefer: count=exact" -H "Range: 0-0"
# read the Content-Range response header: 0-0/<count>
```

Parse `Content-Range` → `int(cr.split("/")[-1])`. A few seconds per table is
normal; a 94-table schema takes ~10s.

## 4. Dump data

```bash
curl -s "$URL/rest/v1/$TABLE?select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" \
  -H "Accept: application/json" -H "Range: 0-9999"
```

Loop the table list; write one CSV per non-empty table (union of keys as columns)
plus a combined `dump.json`. Print a `table → rows` summary sorted desc so the
user immediately sees which tables carry data and which are empty shells
(archives, backups, feature tables never used).

## 5. Output hygiene

- The dump holds PII (names, emails, phone, password hashes) and audit logs.
  Say so, and offer to strip sensitive columns or gitignore the dump.
- Keep raw spec (`openapi.json`) separate from derived (`schema.csv`,
  `dump.json`) so a re-parse needs no second network call.
- Report totals up front: `N tables/views · M columns · K rows`.
