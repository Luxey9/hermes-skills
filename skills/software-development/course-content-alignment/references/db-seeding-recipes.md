# Seeding / repairing Supabase content rows

Use when the task is "write these rows into the DB" (seed a level, sync a
curriculum file into `levels`/`modules`/`lessons`, repair a column, reset a
table) rather than "debug why the app is broken".

## Ground rules

- **Script it, don't click it.** Every change is an `npx tsx scratch/*.mts`
  script using the repo's own deps (`@supabase/supabase-js`, `dotenv`) and its
  `.env` service key. Keep scripts in `scratch/` and leave them untracked.
- **Idempotent by default.** `upsert(..., { onConflict: '<pk>' })` so a re-run
  repairs instead of duplicating. Never `insert()` in a loop without a conflict
  target when the script may be re-run.
- **Print a verification block in the same script**, not as a later step:
  per-parent child counts, orphan count, and a re-read of the rows just written.
  A seeding script that only prints "OK" is not done.
- **No DDL.** `ALTER TABLE`, `CREATE VIEW`, `CREATE TRIGGER`, `CREATE INDEX` need
  the Supabase SQL Editor — write the SQL to `docs/migration-*.sql`, hand it to
  the user, and verify the effect afterwards with a query. The `service_role` key
  is a PostgREST key: rows and RPCs, no DDL.
- **Never print secret values** — read keys from `.env` into a variable; print
  only presence or a prefix.

## Canonical script shape

```ts
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv'; dotenv.config();
const sv = createClient(process.env.VITE_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

// 1. before-state: counts, distinct values
// 2. the change (upsert / update / delete), collecting per-item errors
// 3. after-state + invariants: counts match expectation, zero orphans
```

Collect errors per item and continue — one bad row must not abort a 90-row sync.
Report the failed ids at the end.

## Ordering rules that avoid FK / progress damage

- **Rename a parent id:** insert new → re-point children → delete old. Never
  update-in-place, never delete first. Full recipe in
  `supabase-backend-debugging` Step 6d.
- **Move rows between parents:** `UPDATE child SET parent_id = new WHERE
  parent_id = old`, then delete the old parent. Grandchildren keyed on their own
  id are untouched.
- **Delete a lesson:** check `student_progress` for that lesson id first and
  report how many progress rows reference it.
- **Add a NOT NULL column value:** backfill before any writer starts using it.

## Cheap probes

- Row count without pulling rows: `select('id', { count: 'exact', head: true })`.
- Object kind (view vs table) when you have no SQL access: attempt a dummy
  `insert` — a VIEW errors `0A000 cannot insert into ... of view`, a TABLE fails
  with a permission/FK/NOT NULL code instead. Zero mutations. See
  `supabase-backend-debugging` Step 5b.
- Embed missing → `PGRST200` means no FK between the two tables; a shared value
  column is not enough. Confirm no orphans, then hand over the
  `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` DDL.

## Pitfalls

- **A blank page after seeding is usually a read-path object, not missing rows.**
  Count with BOTH the anon and service keys and against both the base table and
  the sanitised view before concluding the seed failed.
- **Don't leave test/seed accounts behind.** If you seeded per-role test users to
  verify, delete them (or list them in the final report) so a later audit does
  not treat them as real users.
- **A migration's DDL may silently not match reality** (e.g. a view defined in
  `setup-*.sql` that is actually a leftover table in the live DB). After any DDL
  the user runs, re-probe the live object rather than trusting the file.
