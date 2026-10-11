# Anon-Key Data Exposure Audit

The Supabase anon key is published in every client bundle — treat it as public.
Any table the anon role can read is readable by anyone with DevTools. Audit it,
then close it **without breaking the apps that legitimately read it client-side**.

## 0. Views are how these DBs leak — check them FIRST, and separately from tables

A view is the highest-yield object in this audit and it breaks every assumption
the table probes make:

- **A table-level grant on a view is what exposes the rows, not a grant on the
  base table.** The base table can be perfectly locked (anon reads it as
  `401 42501 permission denied`) while the view answers `200` with every row. The
  view runs with its OWNER's rights, and the owner owns the base table, so the
  base table's RLS does not apply. Measured on one live DB: every anon grant in
  the schema was on two views while no anon table grant existed at all.
- **A plain single-table view is AUTO-UPDATABLE, which turns a read leak into a
  destructive one.** `DELETE`/`PATCH`/`INSERT` addressed to the view are rewritten
  against the base table, so an anon key that cannot even read the base table can
  erase rows through the view (`204`, real row gone — prove it with §3c). Detect it
  non-destructively with the duplicate-row `POST` probe: `0A000 cannot insert into
  column "X" of view "V"` proves it is a view (vs a synonym/table); `23505` proves
  RLS admitted an insert into the base table.
- **The sanitising expression is what tells you whether the view matches its repo
  migration.** Read the live column types through the OpenAPI spec — `materi.kuis`
  `jsonb` vs `lessons.quiz` `text` — and compare with the repo's `CREATE VIEW`:
  `(quiz - 'correctAnswer')` cannot be `CREATE`d against a `text` column, so a
  live view that exists and works was built from a *different* statement (usually
  by hand in the SQL Editor). Never "fix" it by re-running the repo's file.
- **A sanitising view can be sanitising the WRONG table.** Two near-identical
  tables in one schema (`materi` / `materi_mahasiswa`, `lessons` / `student_lessons`)
  mean one view may be hand-rolled and stale while the other app reads the *duplicate*
  it was actually written for. Verify per-object: the sanitised view's protection
  (`quiz` stripped of `correctAnswer`) does not transfer to its sibling. Read the
  field the students must not see for real — an answer key present in the rows is
  the finding regardless of how clean the other view looks.
- **Which tables exist at all in a table-vs-view probe matters:**
  `information_schema.columns` lists both, so it cannot tell them apart. Use
  `pg_class.relkind` when the user has SQL, or the `0A000` insert probe when they
  do not.

## 1. Find what anon can actually read

The schema lists ~all tables; only some are exposed. Probe each with the anon key
and read the exact count from `Content-Range` (a `*/0` or `*/N` still means the
request was *accepted* — check whether rows come back, not just the status):

```python
# HEAD each table with the anon key; 200 + rows = exposed
req = Request(f"{URL}/rest/v1/{t}?select=*", method="HEAD", headers={
    "apikey": ANON, "Authorization": f"Bearer {ANON}",
    "Prefer": "count=exact", "Range": "0-0"})
# -> Content-Range: 0-0/322   == 322 rows readable by anon
```

Also try `select=*` on the worst candidates (`users`, session/audit tables) and
inspect which **columns** come back — a leaked `password_hash` / `*_salt` /
token column is the real finding, not merely the row count.

**A 200 is not a leak — compare the count against `service_role`.** An
RLS-protected table answers `200` with `[]`; only the row count separates
"exposed" from "protected". Fetch each table's count with the anon key **and**
with the service key, then classify: `anon == svc > 0` ⇒ leaked;
`anon == 0 && svc > 0` ⇒ RLS already protects it; `anon == 0 && svc == 0` ⇒ empty,
no verdict. Reading the HTTP status alone once produced a list of "18 exposed
tables" of which only 13 held any row — report the count, never the status.

**Measure the existing exposure before designing the remediation.** In one audit,
74 tables were slated for lockdown; 73 of them were *already* protected, so the
plan would have spent the user's time to protect a single table. Run the
classification above first and scope the fix to what actually leaks.

## 2. Before you block: find legitimate client-side readers

The anon key exists because *some* client code reads the DB directly. Blocking a
table that a sibling app depends on silently breaks it. Grep every deployed
bundle for direct reads, not just the one you started in:

```python
# per bundle: which tables does the client hit directly?
re.findall(r'\.from\(["\']([a-z_]+)["\']\)', bundle_js)
# and: does this app proxy through its own /api/rpc, or read Supabase directly?
'/api/rpc' in bundle_js
```

An app that reads `users` straight from the browser (`from("users").select("*")`)
will break under a table-level `USING (false)` policy.

Two further greps decide *what* you may close, and both are easy to miss:

```python
# (a) does the client SELECT "*"?  -> column-level REVOKE is UNSAFE (see §3)
re.findall(r"\.from\(['\"]users['\"]\)\s*\.select\(([^)]*)\)", bundle_js)
# (b) does the client WRITE the table?  -> a write REVOKE breaks the app
re.findall(r"\.from\(['\"](\w+)['\"]\)\s*\.(insert|update|upsert|delete)\(", bundle_js)
```

A client that calls `.update()` / `.delete()` on a table needs `INSERT`/`UPDATE`/
`DELETE` granted to `anon`, so a blanket `REVOKE INSERT, UPDATE, DELETE ON ALL
TABLES` silently breaks it. Classify every table first: **read-only client**,
**read+write client**, or **no client reader** — the fix differs for each.

### (c) `api/` is not automatically safe — server code often falls back to anon

A table written only by "the server" is **not** therefore safe to revoke. Server
handlers commonly initialise their client with a fallback chain:

```ts
const key = process.env.SUPABASE_SERVICE_ROLE_KEY
         || process.env.VITE_SUPABASE_ANON_KEY || '';   // <-- falls back to anon
```

Whenever `SUPABASE_SERVICE_ROLE_KEY` is unset in that deployment, those writes go
out **with the anon key** and a revoke breaks them. Grep the API tree for the
fallback and add its write targets to the must-stay-writable set:

```python
for f in api_files:
    if re.search(r"SERVICE_ROLE_KEY\s*\|\|", src):          # fallback present
        writes += re.findall(r'\.from\(["\'](\w+)["\']\)\s*\.(insert|update|upsert|delete)', src)
```

One audit missed `elearning_progress` and `assessment_attempts` this way — both
written only from `api/`, both behind a `|| ANON_KEY` fallback, so revoking them
would have silently killed progress-saving and auto-grading. **When the API is
deployed to a different host than the repo (a `vercel.json` that proxies `/api/*`
to another domain), you cannot read that deployment's env from the repo — assume
the fallback is live and keep the table writable.** Grant back one table at a time
if a feature breaks; it is a one-line rollback (`GRANT ... TO anon`).

## 3. Close it — and do NOT trust column-level REVOKE while `select("*")` exists

**Column-level `REVOKE` does NOT leave `select("*")` working.** PostgREST expands
`*` into an explicit list of every column; if the role lacks `SELECT` on *any one*
of them the whole request fails with `42501 permission denied` — the client gets
**no rows at all**, not "the revoked columns disappear". A client doing
`.from("users").select("*")` therefore breaks the moment you revoke a column.

Correct order:

1. **First** change the client to an explicit column list
   (`select("id, nim, nama, role, xp, level, ...")`) in *every* call site — grep
   for `.select("*")` / `.select('*')`; there are usually only a handful.
2. **Then** revoke the sensitive columns. The explicit lists no longer ask for
   them, so nothing breaks:

```sql
REVOKE SELECT (password_hash, fb_password_hash, fb_password_salt)
  ON public.users FROM anon, authenticated;

-- keep the columns the app actually uses
GRANT SELECT (id, nim, nama, kelas, jurusan, role, email, xp, level, streak,
              last_active, created_at, updated_at)
  ON public.users TO anon, authenticated;
```

If you cannot change the client (a sibling app you don't control), **leave the
columns alone** and close everything else — a broken login is worse than a leaked
hash you have already scheduled to rotate. Say so plainly instead of shipping the
REVOKE.

For tables with **no** legitimate client reader, a full RLS block is correct:

```sql
ALTER TABLE public.active_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow anon select" ON public.active_sessions;
CREATE POLICY "rls_active_sessions_block_anon" ON public.active_sessions
  FOR ALL TO anon USING (false) WITH CHECK (false);
```

Verify with `information_schema.column_privileges` (expect 0 rows for the revoked
columns) and re-run the step-1 probe.

## 3a. Grants are PER-COLUMN in both directions — a missing column grant is not a missing table grant

§3 covers revoking a column; the same mechanism bites on the way in, and it is the
more common live state:

- **One ungranted column fails the WHOLE statement.** PostgREST expands both
  `select="*"` and an explicit list into per-column privilege checks, and a `PATCH`
  body naming an ungranted column fails entirely — so an app feature that batches a
  guarded column with a normal one breaks while its sibling call succeeds. Measured
  on one live `users`: `select=<15 granted cols>` → `200`, the same list **plus** one
  ungranted column → `403 42501`, that column alone → `403`; and `PATCH {role}` →
  `204` while `PATCH {role, app_role_flag}` → `403`.
- **Expect a lopsided table, so measure each operation separately.** Same table:
  22 of 43 columns readable, 0 of 43 updatable. Reads therefore worked while every
  write failed, and a report that only checked the operation in the error message
  would have missed the other half. Run `scripts/column_grant_sweep.py` for both.
- **The hint `GRANT SELECT/UPDATE ON public.<t> TO <role>` is not the fix.** It
  over-grants the whole table; the scoped form is
  `GRANT SELECT (col) ON public.t TO authenticated;` (and `GRANT UPDATE (c1, c2) ...`).
  Column privileges are invisible over PostgREST — the OpenAPI spec carries types
  but no grants — so the per-column sweep IS the measurement, not a fallback.
- **Temporarily REMOVE the ungranted column from the client's select list to get
  the feature working while the user applies the SQL** — it costs one line, ships
  immediately, and de-risks the grant step. Re-add it in the same breath as the
  GRANT, otherwise the improvement silently disappears.

## 3b. Probe WRITE exposure without mutating anything

Read exposure is only half the audit. An anon key that can `INSERT`/`UPDATE`/
`DELETE` is far worse — anyone can wipe the DB. Test it **without changing data**:

- `PATCH` / `DELETE` with a filter that matches **no rows** — `?id=eq.-999999`.
  Safe: nothing is modified. But the body must carry at least one real column with
  a type-valid value (`{"some_col": "x"}`); an empty `{}` body returns `400` from
  PostgREST and tells you nothing.
- **The error CODE decides the verdict, not the HTTP status.** Only `42501` (or
  "row-level security") means *blocked*; `200`/`204` means *admitted*. Every other
  `400` is your probe's fault and proves **nothing** — and this is the trap, because
  a malformed probe looks like a denial:

  | Response | Meaning |
  |---|---|
  | `204` / `200` | RLS admitted the write (grant alone is letting anon through) |
  | `42501` / "row-level security" | RLS blocked it — correct finding |
  | `23505` (unique) | **checked AFTER RLS** → the write is OPEN |
  | `23503` (FK) | checked AFTER RLS → write open |
  | `22P02` (type), `23502` (NOT NULL), `42703`/`PGRST204` (no such column), `PGRST` arity | **checked BEFORE RLS** → inconclusive, fix the probe |

  The mechanism: NOT NULL and type checks run while the tuple is formed, *before*
  RLS `WITH CHECK`; unique/FK checks run at insert time, *after*. So a type error or
  a missing-column error on every table in a sweep is not "all tables protected" —
  it is a broken probe. One sweep produced `400` on twelve tables and read as
  "locked"; every one was a wrong column name or a uuid/integer mismatch.
- **Never probe `POST` (insert) casually — but a duplicate-key `POST` is
  non-mutating and the only way to test `INSERT` directly.** Fill every NOT NULL
  column and duplicate an existing PK/unique value: the unique violation aborts the
  insert, so no row is created. `23505` ⇒ write open; `42501` ⇒ blocked;
  `23502` ⇒ you left a NOT NULL column out, add it and retry. A plain "try an
  insert" with a placeholder value is different — it can succeed and WILL create a
  row. If you do insert by mistake, capture the returned id, `DELETE` it
  immediately, re-count the table, and tell the user.
- **To test INSERT on an RLS-protected table, fetch the row with `service_role`
  first.** Anon cannot read the row to duplicate it, so a duplicate-PK probe is
  impossible from the anon side alone. Fetch one row with the service key, POST
  that exact row back with the **anon** key, and read the code: `23505` ⇒ RLS
  admitted the insert (write open); `42501` ⇒ blocked. This is the only probe that
  yields a verdict on tables where an anon read returns nothing, and it mutates
  nothing. Without it, a write sweep silently skips every locked table and reads as
  "all protected".

Interpretation: a `204` on the no-match `PATCH` means the table has **no RLS
policy for writes** (or one that is `USING (true)`) — the grant alone is letting
anon through. That is the finding worth reporting.

## 3c. Confirming the hole is destructive (self-cleaning seed/delete proof)

`204` is ambiguous: PostgREST returns it for any successful `DELETE` without
`Prefer: return=representation`, so "admitted but matched nothing" and "a real row
was destroyed" look identical. When the finding is *destructive* — not merely
readable — do not report it from a status code. Prove it, then put the database
back exactly as it was:

```python
PROBE_ID = 'zz-probe-anon-delete-0001'
before   = count('materi', SVC)                       # baseline, print it
row      = GET('/rest/v1/materi?select=*&limit=1', SVC)[0]   # a REAL row
row['id'] = PROBE_ID; row['judul'] = 'PROBE (auto-deleted)'
POST('/rest/v1/materi', SVC, row)                     # 1. seed, svc: 201 + count+1
GET('/rest/v1/materi?id=eq.'+PROBE_ID, SVC)           # 2. assert it exists
DELETE('/rest/v1/materi_mahasiswa?id=eq.'+PROBE_ID, ANON)    # 3. the attack, via the VIEW
GET('/rest/v1/materi?id=eq.'+PROBE_ID, SVC)           # 4. '[]' -> row destroyed
DELETE('/rest/v1/materi?id=eq.'+PROBE_ID, SVC)        # 5. safety-net cleanup
print(count('materi', SVC), 'vs baseline', before)    # 6. must equal
```

Rules that make this safe and trustworthy:

- **Seed by copying a real row, never by hand-writing fields.** A partial/placeholder
  row fails `23502 NOT NULL`, nothing is created, the later `DELETE ... === []`
  then *looks* like a successful destructive proof. Assert the seed succeeded and
  the count went up by exactly one before you run the delete. (`23502` on the seed
  is the tell that the probe is invalid, not that the table is protected.)
- **Use an unmistakable id** (`zz-probe-…`) and always finish by deleting it with
  `service_role`, printing the final count next to the baseline. A probe row left
  behind is indistinguishable from user data later.
- **Report the verdict as the count, not the status**: "anon `DELETE` via the view
  removed a real row (96 → 97 → 96)". A `42501` means the object is not
  auto-updatable — that is a *negative* result for the write probe only; the read
  leak may still be fully open, so report the two separately.

## 3d. Audit VIEWS separately — they carry the caller's write rights to the base table

A read+write sweep that only lists tables misses the usual remaining hole: a
**view owned by a privileged role with no `security_invoker`**. Plain views run
with the OWNER's rights, so base-table RLS and revoked base-table grants are both
bypassed. `pg_policies` shows nothing for a view (`jml_policy=0`), and
`relrowsecurity=false`, which reads as "not applicable" — but the grant rows on
the view decide access, and if `anon` holds `INSERT,UPDATE,DELETE` there, anon can
write the base table through it.

```sql
SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) AS owner,
       COALESCE((SELECT option_value FROM pg_options_to_table(c.reloptions)
                  WHERE option_name='security_invoker'),'ABSEN -> hak OWNER') AS invoker
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='v';
```

Then classify the view, because the three cases need different fixes:

| probe (anon, non-mutating) | means | fix |
|---|---|---|
| `DELETE ?col=eq.<tak-ada>` → `204`, `PATCH` → `200 []` | auto-updatable → writes land on the base table | revoke anon, grant `authenticated` only |
| `POST` dup row → `23505 duplicate key ... "<BASE>_pkey"` | auto-updatable, error names the BASE table (proof of the link) | same |
| `POST` dup row → `0A000 cannot insert into column "X" of view` | NOT auto-updatable (derived column) → INSERT blocked, but DELETE/UPDATE of plain columns still reach the base | `REVOKE INSERT,UPDATE,DELETE ON <view> FROM anon` |

A no-match `DELETE` through a view tells you nothing on its own — `204` is
returned whether zero or N rows matched (see §3c for the self-cleaning proof).

**A view that is not auto-updatable cannot be locked against writes without
also killing reads** — `REVOKE SELECT` takes the read away, dropping/recreating
it as a table does too. Sanitise first (`col - 'key'` for jsonb), and if the old
name must stay readable, roll out a new view name in two phases (create new →
deploy code reading it → drop old). Also verify the DEPLOYED view definition
against the repo: when the base column type differs from what the migration
assumes (`lessons.quiz` is `text`, so `quiz - 'correctAnswer'` would raise
`operator does not exist: text - unknown`), the live view was created by hand and
no repo file describes it.

## 4. Then rotate

A key that was exposed must be considered compromised: tell the user to rotate the
**anon key and the `service_role` key** (Supabase → Project Settings → API), and
consider forcing a password reset if password hashes were readable. Locking the
table does not un-leak what was already served.

## Pitfalls

- **Don't equate "RLS enabled" with "safe".** A policy `FOR ALL TO anon USING
  (true)` leaks as effectively as no policy. Read the policies, don't assume.
- **Don't let the absence of an anon *table* grant end the audit.** Anon's reach
  comes from table-level grants, and in these schemas the grants are usually on
  **views**. Enumerate `information_schema.role_table_grants WHERE grantee='anon'`
  across the whole schema — views appear there too — and treat every hit as a
  finding until proven otherwise.
- **Don't close a view in a way that kills the feature it exists for.**
  `security_invoker = true` makes the view obey the CALLER's RLS; when the base
  table's policy is staff-only, students then read an empty view — the read leak
  becomes a total content outage. `REVOKE ALL FROM anon` + `GRANT SELECT TO
  authenticated` is the fix. Roll this out only after the client actually
  authenticates per user (see the SKILL.md pitfall on proving the JWT injection).
- **An orphan view is dead code you can drop — but verify it is orphaned from the
  DEPLOYED bundle.** Grep every served bundle (main chunk *and* every lazily
  imported chunk, and the dynamic `import()` map) for the object's name; zero hits
  across all of them plus zero hits in `src/` and `api/` means nothing reads it.
  Then check the duplicate before dropping: if a live sibling object holds the same
  rows and the code reads *that* one, the drop is safe. Prefer the two-phase
  rename (create the corrected name → deploy code that reads it → drop the old)
  when anything does read it: a view's write side cannot be disabled
  independently of its read side.
- **`service_role` bypasses RLS by design** — an exposed `service_role` key is far
  worse than an exposed anon key (full read *and* write). Check which key each
  bundle actually inlines.
- **Audit the whole schema, not just the table in front of you.** The leak is
  usually a handful of tables the lockdown migration simply forgot.
- **`REVOKE SELECT (col)` breaks `select("*")`.** PostgREST expands `*` to every
  column; one revoked column fails the whole query with `42501`. Change the
  client's column list *before* revoking — see §3.
- **Read-only audit ≠ write-safe.** A table can be readable *and* writable by
  anon; the write capability is the more serious finding. Probe both (§3b).
- **A per-role probe is only per-role if the `apikey` header carries the
  non-privileged key.** PostgREST authorises on the `Authorization` JWT while the
  `apikey` header only has to be valid for the project, so send
  `apikey: <anon>` + `Authorization: Bearer <caller token>`. Reusing the
  `service_role` key for BOTH — the obvious thing when a probe helper takes a
  single `key` argument and uses it for both headers — makes every request run as
  `service_role`, and the sweep then reports "everything granted" for a role that
  is denied everywhere. A sweep that declares a broken role healthy is worth
  re-running before you tell the user their schema is fine.
- **An anon-only sweep CANNOT see a broad policy written for `authenticated`, so
  "already protected" does not survive the client starting to send a per-user
  JWT.** A table whose only policy is `FOR SELECT TO authenticated USING (true)`
  answers `401 42501` to anon (no grant) and reads as protected — then returns
  every row, answer key included, the moment the app injects a user token. A
  `SELECT USING (true)` policy on a content table is therefore *invisible* to the
  whole §1 classification. Whenever you enable or repair per-user JWT injection in
  a client, re-run the read **and** write probes carrying that role's token before
  declaring the schema clean — the interesting table is usually one users already
  considered safe.
- **A login/session token can be signed with a key you do not have locally, and
  the wrong key is not a permissions error.** `SUPABASE_JWT_SECRET` is a server-side
  secret that is routinely absent from a repo while a different `JWT_SECRET` (the
  app backend's own) sits in `.env`. Minting with the wrong one compiles and
  produces a well-formed token that PostgREST rejects on **every** request with
  `PGRST301 No suitable key or wrong key type` — signing succeeded, verification
  failed. Read that code as "wrong signing key", never as "blocked"; and when the
  right secret is genuinely unavailable, obtain a real token through the app's own
  pipeline (its SSO handoff endpoint, `POST /api/login`) or hand the user a console
  probe — do not keep re-minting and calling it an access failure.
