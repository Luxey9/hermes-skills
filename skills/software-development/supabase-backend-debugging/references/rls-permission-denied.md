# RLS `permission denied` and "progress reset to 0"

Use when Postgres logs show `permission denied for table X` with SQLSTATE
`42501`, or a user reports progress/percentages that suddenly read zero.

Start with the discriminator: **a wall of `401`s means no identity was attached
at all (fix the token/host secret, not a policy); a single `42501` means the
identity resolved but lacked POLICY (fix the policy/GRANT).** Section order below
follows that split.

## 401 everywhere before any 42501 — the token was never attached

A `42501` means an identity resolved but lacked POLICY. **A wall of `401`s means
the request carried no usable identity at all** — check this FIRST when a
*logged-in* user's progress reads zero and the console shows every REST call
failing. PostgREST answers `401` (not `403`/`42501`) when the `Authorization`
header is absent, malformed, or signed by a key it cannot verify.

The chain to look for: the login route mints a replacement JWT only when its own
signing secret env (`SUPABASE_JWT_SECRET`) is set; without it the route returns the
**upstream/backend token**, which a different service signed. The client's token
installer then checks the decoded claims, refuses a payload that is not the
Supabase-issued shape, nulls its stored token, and every later REST call silently
falls back to the anon key.

Discriminators that identify this without reading source:

- `401` on tables that should be readable by anyone (a settings/config table) —
  a role problem would be `403`/`42501` on a table the role may not touch, not a
  blanket `401` including public tables.
- `401` on a request for the user's OWN row (`nim=eq.<their own nim>`), which the
  per-owner policy would have allowed.
- A server log hint naming `anon` (`GRANT ... TO anon`, "permission denied") while
  the browser session is authenticated.
- A client console warning that the token was rejected/ignored.

Diagnose from the TOKEN, not from the DB — the data is fine:

```js
// browser console, on the affected session
JSON.parse(atob(sessionStorage.getItem('<token key>').split('.')[1]))
```

Read `iss`, `role`, and the identity claim (`nim`/`sub`). A payload with the wrong
`iss` (or `role: anon`) is the entire cause. Confirm the host side with the
handler's own requirements — `rg -o "process\.env\.[A-Z_]+" api/<route>.ts api/auth.ts
| sort -u` — and check that the signing secret is present for the environment that
is failing.

Fix: host-side setup only — add the signing secret to the host, **redeploy** (env
changes apply on the next deploy), then log in again. A policy or GRANT edit cannot
fix it, because an anon request never reaches row evaluation. After redeploy,
re-probe: the failure is byte-identical until the new build is serving.

Do NOT let this read as damage from a schema migration that shipped the same day.
Additive migrations (new columns, new tables) do not invalidate tokens. What
surfaces it is usually a session re-login — a fresh token from the fallback path
replaces a previously-working stored one — so the timing is coincidental, and
rolling back migrations will not restore the symptom. Also confirm the data before
proposing any repair: a token problem always leaves the rows fully intact.

## The 42501 signal
`permission denied for table X` (42501) is raised by **table-level GRANT or a
missing RLS policy for the requesting role**. Read which of the two before
writing any fix:

- `auth_user: null` in the same log row signals the request arrived with no
  usable identity (anon key, an expired/foreign token, or a JWT PostgREST
  could not verify). Policies scoped `TO authenticated` then do not apply at
  all.
- A non-null `auth_user` means the identity resolved fine and it is the
  table's own policy/GRANT that is missing for that role.

Distinguish it from RLS **filtering** a row: a filtered row returns zero rows
with no error. An error means the statement never got to row evaluation.

## Procedure

1. Get the real error source before guessing: read the table name and
   `auth_user` from the log, then list the live policies for every table the
   failing query touches.

   ```sql
   select tablename, policyname, roles, cmd
   from pg_policies
   where tablename in ('users','student_progress','game_history','lessons')
   order by tablename, cmd;
   ```

   List the tables of the whole query, not just the table named in the error:
   a join against an unreadable table reports that table's name, which sends
   you to the wrong file.
2. Check column-level GRANTs separately from policies. A policy can be
   permissive while the role still lacks `SELECT` on the columns the query
   selects — PostgREST rejects the **entire** statement when any selected
   column is ungranted, so one missing column reads as a whole-table denial.

   ```sql
   select grantee, privilege_type, column_name
   from information_schema.column_privileges
   where table_name = 'users' and grantee in ('anon','authenticated');
   ```

   Grant only what the client actually reads/writes rather than the whole
   table.
3. Separate "data gone" from "data unreadable" before touching anything:

   ```sql
   select nim, count(*) from student_progress where completed group by nim;
   select lesson_id, completed, completed_at
   from student_progress where nim = '<affected nim>' limit 20;
   ```

   Rows present + UI showing zero = a read/RLS problem. Rows genuinely gone =
   a delete path ran, which is a different investigation entirely.
4. Fix the read path for the roles that need it, keeping writes tight. When a
   public board must read other users' rows, grant SELECT on the aggregate
   columns only; INSERT/UPDATE/DELETE stay scoped to the owner.
5. Verify by executing the query **as the failing role**, not as owner or
   service_role — owner bypasses RLS and will always look healthy.

## Rolling out a fix the user runs by hand

DDL never goes through PostgREST, so policy/GRANT fixes are executed by the
user in the Supabase SQL Editor. Make that handoff work:

1. Name the target project and hand over the file path or paste the full
   script, plus the exact order when several migrations are involved.
2. State prerequisite checks as runnable SQL before the main script — the
   curriculum tables an RPC reads, or columns an earlier migration must have
   added. A script that assumes an absent prerequisite fails mid-way and
   leaves partial DDL behind.
3. Hand over the tracked path, never a scratch copy — a divergence between the
   `docs/` script and a `scratch/` copy is invisible in the filename, and the
   stale one gets run.
4. After the user reports success, verify from the data side rather than
   trusting the report: row counts, a `select` for one affected row, and a
   student-role read path. A migration that ran clean can leave the symptom
   intact.
5. Separate the artefacts in the handoff: schema/infrastructure SQL versus
   behaviour that lives in application code and ships via deploy. Users
   conflate them and hunt for a migration that does not exist — say which of
   the two each requested change is.

## Pitfalls

- Fix the policy named in the error while the join's other table is the one
  denied — read `pg_policies` for every table in the statement before editing.
- A client loader shaped `if (!error && data) setState(...)` leaves the UI at
  0% on any read error with nothing logged to the user: when a whole course
  reads as 0% for one role, suspect a silently swallowed read failure, not
  wiped rows. Check the fetch wrapper's error branch before believing a reset.
- Grant the fix with `TO authenticated` while requests arrive as `anon` — the
  policy never applies. Confirm the token's `role` claim first, because a
  foreign/expired token silently downgrades the request to anon.
- Treat a denial that only affects one role as a data bug: staff see every row
  through their own policy, so a students-only failure is almost always a
  missing per-owner SELECT policy, not corrupt data.
- Downstream symptom of the above is a board that reads as empty for students
  while the source tables are full — test the student role path, not just the
  staff path, before declaring the feature done.
