# PostgREST Bulk Ops (DML via REST, DDL via SQL Editor)

Use when doing bulk data work against a Supabase/Postgres backend through
PostgREST: bulk inserts, verification reads, and schema changes.

## Procedure

1. Confirm the REAL backend first: the project ref in the REST URL must match
   the intended project before any write. A service_role key is only valid
   for one project — decode/check the URL, never assume.
2. DML goes through REST (`apikey` + `Authorization: Bearer` headers);
   DDL never goes through REST. `code 42703 / column X does not exist` means
   the migration has not been applied — run the `ALTER TABLE` in the SQL
   Editor, then record the version in `schema_migrations`.
3. Check the version column type before recording: if it is text, insert
   `'030'`, not `30`, with `ON CONFLICT DO NOTHING`.
4. Write bulk inserts idempotent from the start: seed parents with
   `ON CONFLICT DO NOTHING`, insert children via `SELECT ... FROM parent
   WHERE ... UNION ALL ...`, and finish with `ON CONFLICT (unique_col)
   DO NOTHING` plus a closing `SELECT ... GROUP BY` count query.
5. Verify by reading back before claiming success: row counts per group
   (`Prefer: count=exact`, read `Content-Range`) or the closing count query.
   A successful write call is not a successful task.
6. Generate password hashes with the repo's own hasher (same bcrypt cost the
   login path verifies against) — never hand-write a hash string.
7. If the user redirects the approach mid-run (e.g. "do it here instead of
   via the external API"), kill the superseded background process first,
   then start the new direction. Do not leave stale jobs running.

## Pitfalls

- PostgREST `in` filters need parens: `id=in.(1,4,7)` — a bare `in.1,4,7`
  fails to parse, because the parser expects the parenthesised list.
- Keep `order=` to a single plain field; compound `order=a,order=b` strings
  fail parsing, because only one ordering expression is accepted.
- Store generated code/text columns raw, never through the app's HTML
  sanitizer — sanitizing mangles `<stdio.h>`, `&&`, and quotes, because it
  treats code as markup.
- On Windows git-bash, paths with spaces break inline command quoting —
  write helper scripts to a file with the file tool and invoke with a
  single-quoted path, because re-quoting inline always loses.
- Regenerating mocks requires the `--all` flag on the mockery invocation —
  without it mockery exits asking for `--name`/`--all` and writes nothing.
