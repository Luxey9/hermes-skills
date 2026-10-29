# Bulk Inserts via Supabase SQL Editor

For loading user-supplied row lists (rosters, cohorts, seed data) into a Supabase
Postgres database when you have no direct database credential.

## Procedure

1. Confirm the target project first (same repo can deploy against several
   projects) and confirm the exact `kelas`/category names already in the DB so
   foreign keys resolve.
2. Read the entity/model definition for the target table and note: NOT NULL
   columns, unique indexes (for the conflict target), nullable columns, and the
   auth gate the app actually checks (e.g. a credential-presence function, not
a boolean flag) — every inserted row must satisfy that gate or logins silently fail.
3. Generate the password hash with the repo's own hashing tool (e.g. its
   `hasher` command), never hand-rolled bcrypt — cost parameters must match
   what the login path verifies.
4. Generate the SQL from the parsed row list with a script, never by hand:
   parse `NIM + name` per line, escape single quotes by doubling them, and
   verify the parsed row count against the source list before emitting.
5. Emit one statement per group: `INSERT INTO kelas ... ON CONFLICT DO NOTHING`,
   then `INSERT INTO users (...) SELECT ... FROM kelas WHERE nama_kelas = '...'
   UNION ALL ... ON CONFLICT (<unique_col>) DO NOTHING` so reruns skip existing
   rows instead of failing.
6. Append a verification `SELECT ... GROUP BY` at the end of the same script and
   have the user paste the whole thing into Dashboard > SQL Editor > Run, then
   report the verification counts back.

## Pitfalls

- Distinguish the service key from the database password before asking for
  credentials — the service key only speaks to the API/Auth/Storage surface and
  can never open a Postgres connection, so requesting it for a SQL insert
  wastes a round trip; ask for the Database password (or fall back to the SQL
  Editor paste path, which needs no credential at all).
- Never read another repo's `.env` uninvited when the credential is missing —
  state that no local credential exists and offer the explicit choice of
  pasting the connection string or using the SQL Editor path. An explicit user
  request to open or access the database counts as permission to search sibling
  repos' `.env` files for that project's service key — but never print the key
  itself; confirm only its length and a live probe result.
- Keep one-off bulk-load scripts out of the committed tree — generate the SQL,
  deliver it, and leave the generator in scratch; committing single-use loaders
  pollutes the repo's command surface.

## Verification via REST (service key)

When a `service_role` key for the target project is available, verify the load
directly through PostgREST instead of relying on user-reported counts: send
`apikey` plus `Authorization: Bearer` headers, then query the loaded groups.

- Count without fetching rows: `select=id&limit=1` with `Prefer: count=exact`
  and read the `Content-Range` header (`0-0/69` means 69 rows match).
- Spot-check the app's real login gate, not just row counts (e.g. credential
  columns non-null and consistent with the boolean flag), or inserts look
  successful while logins silently fail.
- Filter syntax: `in.(1,2,3)` takes parenthesized IDs with no spaces — build
  the list from a prior verified query, never hand-typed; `order=` is one
  parameter with comma-separated columns, not repeated `order=` params.
- Keep the key out of logs and transcripts: echo the project URL and key
  length only, and pass secrets via headers rather than inline command strings.
