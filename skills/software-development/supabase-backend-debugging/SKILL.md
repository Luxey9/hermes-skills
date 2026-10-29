---
name: supabase-backend-debugging
description: "Debug Supabase apps: schema, RPC/RBAC probes, SSO."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [supabase, postgrest, database, rbac, sso, debugging, introspection]
    related_skills: [systematic-debugging, dogfood]
---

# Supabase / PostgREST Backend Debugging

## Overview

See `references/leaderboard-scope-filter.md`, `references/weekly-leaderboard.md`, `references/prestige-reset.md`, and `references/postgrest-bulk-ops.md` for leaderboard scoping, weekly boards, prestige resets, and bulk ops. Data extraction: `references/postgrest-data-extraction.md`. Denied reads / 42501 / "progress shows 0": `references/rls-permission-denied.md`.

A Supabase backend exposes everything you need over plain HTTP: schema, data,
and every RPC. This skill is the fast path for two recurring requests:

1. **"Extract the tables / columns / types (and data) from this database."**
2. **"Why can't role X do Y / reach Z?"** (login, SSO redirect, menu, RPC).

Both are answered with the same three moves: identify the *real* backend, get a
credential that can read it, then probe it directly instead of reasoning from source.

A fourth move resolves the "it says Invalid API key" dead end: **decode the
credential instead of asking for it.** A key is only valid for one project, and a
JWT carries the proof — decode the payload and compare its `ref` claim with the
ref in the configured URL, and its `role` claim with the role you need. Also
parse the newer non-JWT formats (`sb_secret_` = service role, `sb_publishable_` =
public) so a project that only exposes one style is not mistaken for a bad key.
See `references/credential-claims-and-targeting.md`. For user-supplied bulk row loads with no DB credential, see `references/bulk-inserts-via-sql-editor.md`.

## When to use

- The answer depends on *which* deployment/project is live: the same repo can be
  deployed twice against two different projects. Prove the target by fetching the
  live client bundle and grepping `https://[a-z0-9]+\.supabase\.co` — a repo
  `.env` only describes local builds. See `references/deployment-target-identification.md`.
- User points at a `https://<ref>.supabase.co` URL and asks for its schema or data.
- A change depends on a migration that the user says they already ran — verify it
  against the live project before building on it: `references/migration-verification.md`
  (creditless probes, `42703` = column missing, `PGRST202` hint = live signature).
- A role-gated feature works for some accounts and not others (auth, RBAC, SSO handoff, menu visibility).
- The user asks how to **run the app locally** or why a local run cannot read the
  DB — see `references/local-dev-and-db-connection.md` (Vite dev API mocks, env
  loading, proving the DB link in one probe).
- You need ground truth about what a deployed app actually talks to.

## Iron rules

1. **The deployed artifact is authoritative, not the repo.** The repo may be
   ahead, behind, or a *different deployment* of the same product. When a live
   symptom is reported, fetch and read the actually-served JS bundle and compare
   it to the source before trusting either. A local `.env` can point at a
   completely different Supabase project than production.
2. **Probe, don't infer.** A per-role HTTP probe (200 vs 403) settles in seconds
   what static reading debates for an hour. See `references/rbac-sso-debugging.md`.
3. **Never print secret values.** Read keys from env files into a variable; print
   only `len()` / a prefix, never the value. Never commit dumps that contain PII.
4. **For a view or a function, the LIVE definition is the only truth — a repo
   migration is a hypothesis.** Objects created or replaced by hand in the SQL
   Editor drift silently from every file in the repo, so probe the live object
   (its columns, its behaviour) instead of reading the SQL that was *meant* to
   create it. A type mismatch between the repo's `CREATE VIEW` and the live
   column types is the tell: `(jsonb_col - 'key')` cannot exist against a `text`
   column, so a live view that works proves it was built from something else.
5. **A TABLE's column set — and the migration files themselves — are hypotheses
   too.** `supabase/migrations/` is a wish list: a hotfix migration can be written
   and never applied because the app compensates elsewhere, and code written
   against a column that only exists in the migration fails at runtime with
   `42703 column X does not exist`. Read the live column set
   (`/rest/v1/<table>?select=*&limit=1` with the service key) before writing code
   against it, and before telling the user a fix needs no DB change.

## Step 1 — Identify the real backend

The ref is in the served bundle, not necessarily in the local repo's `.env`.

```bash
# Which Supabase project does the DEPLOYED app actually use?
curl -s https://app.example.com/ | grep -o 'src="[^"]*\.js"'   # find the asset
curl -s https://app.example.com/assets/<file>.js | grep -oE 'https://[a-z0-9]{20}\.supabase\.co'
```

When several domains serve the same product, match each bundle's ref to find the
one that corresponds to the reported symptom. A JWT's payload carries a `ref`
claim — base64-decode the middle segment and compare it to the target ref to
confirm a key belongs to that project.

**The frontend host is usually NOT the API host — read the API base out of the
served HTML before posting to it.** A static/SSR frontend answers `404` (or its
catch-all) to every `/api/...` path, so a probe against the app domain reads as
"no such endpoint" and sends you hunting through routes that are fine. The base
URL is inlined into the SSR payload:

```bash
curl -s https://app.example.com/ | grep -o '"PUBLIC_API_BASE_URL":"[^"]*"'   # -> https://api.app.example.com
```

Then probe the **API host** (`api.<domain>`, or a separate service), and treat a
`sibling app's .env` as the place to find the service key for a project whose own
repo ships no `.env` at all (only `.env.example`).

## Step 2 — Get a credential that can read it

The **anon key cannot read the schema** and is filtered by RLS. You need the
**`service_role` key** for the *target* project:

- `GET /rest/v1/` with an anon key returns `401 {"message":"Invalid API key",
  "hint":"Only the `service_role` API key can be used for this endpoint."}`
- Reading a **table** with the anon key returning `401 {"code":"42501",
  "message":"permission denied for table X","hint":"Grant the required
  privileges ... GRANT SELECT ON public.X TO anon;"}` is a **missing
  table-level GRANT**, not RLS. An RLS denial answers `200` with `[]`; PostgREST
  emits the exact `GRANT` statement to run in the hint. Re-probe the same table
  with `service_role`: `200` proves URL/ref/table name are all correct and only
  the privilege is missing — so do not go hunting for a wrong project or a
  renamed table. `42501` on *every* table while RPCs work means the grant block
  never ran on this project; the repo's own `docs/*permissions*.sql` is usually
  the script waiting to be applied.
- The right key is often in a **sibling repo's** `.env`
  (`SUPABASE_SERVICE_ROLE_KEY`), not the repo you started in. Scan nearby project
  directories for env files whose Supabase ref matches the target.

## Step 3 — Extract schema (tables, columns, types)

PostgREST publishes an OpenAPI spec. Fetch it once, then parse locally.

```bash
curl -s "$URL/rest/v1/" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" \
  -H "Accept: application/openapi+json" > openapi.json
```

Each `definitions[<table>].properties[<col>]` gives the Postgres type
(`format`), `maxLength`, `default`, and its `description` embeds `<pk/>` and
`<fk table='..' column='..'/>`; `definitions[<table>].required` is the NOT NULL
set. Turn this into a CSV/report — recipe and full field mapping in
`references/schema-extraction.md`.

## Step 4 — Extract data and row counts

```bash
# exact count without pulling rows
curl -sI "$URL/rest/v1/$TABLE?select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" \
  -H "Prefer: count=exact" -H "Range: 0-0"        # -> Content-Range: 0-0/1234

# pull rows (service_role bypasses RLS)
curl -s "$URL/rest/v1/$TABLE?select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" -H "Range: 0-9999"
```

For "dump everything", loop the table list from the spec, write one CSV per
non-empty table plus a combined JSON, and print a table→rowcount summary so the
user sees what actually holds data. Warn the user the dump contains PII and
should be gitignored.

## Step 5 — Probe auth / RBAC per role

Call any RPC directly with the service key to read its logic outcome, and mint a
short-lived HS256 JWT per role (from the app's `JWT_SECRET`) to exercise the
app's own RBAC path. Full recipes and the failure-meaning table are in
`references/rbac-sso-debugging.md`.

## Step 5b — Empty content for one role: check role-split read paths

Symptom: a page/section loads fine for staff but renders empty for
praktikan/mahasiswa. Do not jump to RLS — first grep the data-loading code for a
**role-conditional table/view pick**:

```bash
rg -n "isStaff|isAdmin\?|'student_'|'lessons' :" src/   # e.g. isStaff ? 'lessons' : 'student_lessons'
```

This pattern reads a SANITISED VIEW (solution / answer-key columns stripped) for
students and the base table for staff. Two distinct failure shapes:

1. **The view exists but returns 0 rows for students** — plain views run with
   the VIEW OWNER's rights, not the caller's, so base-table RLS alone does NOT
   empty the view. Zero rows usually means the view's own GRANT is missing, the
   owner is unprivileged, or the object isn't actually a view (see 2). Confirm
   before fixing: `select count(*)` with both keys; then either keep the base
   table locked and rely on the owner's rights (default), or if the view must
   inherit caller RLS, set `security_invoker = true` (Postgres 15+) and grant
   the base table `SELECT TO authenticated`.
2. **The object is a leftover TABLE, not the view the migrations define** —
   `information_schema.columns` lists both tables and views, so a schema dump
   will not tell them apart. A migration creating the view fails (or someone
   once materialised a copy), the table stays empty, staff reads the base table
   fine, students get zero rows. Distinguish before fixing:

   ```sql
   select relkind from pg_class where relname = 'student_lessons';  -- 'v'=view, 'r'=table
   ```

   **Without SQL access, probe the object kind through PostgREST**: an
   `INSERT` attempt against a VIEW errors `0A000 cannot insert into ... of view
   "<name>"`, while a TABLE insert fails with a permission/FK/NOT NULL code
   instead (or succeeds). One dummy insert with the service key settles
   view-vs-table with zero mutations. The same probe class surfaces type
   mismatches in the view definition itself: a migration written as
   `(jsonb_col - 'key')` fails with `operator does not exist: text - unknown`
   when the column is actually `text` — fix with `col::jsonb - 'key'`, but only
   after confirming every row parses (`col ~ '^\s*[\{\[]'` guard for junk data).

   **`CREATE OR REPLACE VIEW` can only APPEND columns — reordering or renaming
   even one is refused with `42P16 cannot change name of view column "X" to
   "Y"`.** The check is POSITIONAL: the new SELECT's Nth column must carry the
   same name as the old Nth column, so merely listing an existing column in a
   different spot (e.g. `xp_reward` before `sort_order`) reads as a rename and
   fails. Read the live order before rewriting — the key order of
   `definitions.<view>.properties` from the OpenAPI spec, or a `select=*`
   response — copy it verbatim, and put every new column at the END. This is a
   different failure from the type-cast one above and the two commonly surface
   on the same migration, so fix both before handing SQL over.

   Fix: `DROP TABLE IF EXISTS ...; CREATE OR REPLACE VIEW ...` from the repo's
   migration SQL, then `GRANT SELECT` to `authenticated` and verify row count
   matches the base table. Count rows with BOTH anon and service keys — a view
   that is fine for service but empty for anon is RLS on the base table, not a
   missing view.
3. **The view is intact but UNPROTECTED — an anon `GRANT` turns the sanitised
   view into a read AND write path.** A view can carry a table-level grant while
   the base table is fully locked (base table answers `401 42501`, the view
   answers `200` with every row), because the view runs with its OWNER's rights
   and the owner owns the base table. Worse, a plain single-table view is
   **auto-updatable**, so `DELETE`/`PATCH`/`INSERT` sent to the *view* are
   rewritten into statements against the base table — the anon key gets
   write access to a table it cannot even read. Close it with
   `REVOKE ALL ON public.<view> FROM anon;` plus `GRANT SELECT ON public.<view> TO
   authenticated;` — never by trying to make the view non-updatable (a
   `GROUP BY`/`LIMIT` wrapper still leaves the read leak open). Do NOT add
   `security_invoker = true`: that makes the view inherit the *caller's* RLS, and
   the base table's policy (staff-only) then empties the view for every student.

   **A `DROP` + `CREATE` of the view WIPES its grants — re-grant in the same
   script**, including the `anon` grant you deliberately kept during a staged
   migration; otherwise the next probe reports a "locked" view that is actually a
   broken one. `CREATE OR REPLACE` is only safe while the column list is unchanged
   or appended at the end (a mid-list rewrite raises `42P16 cannot change name of
   view column`), which is why dropping is usually required.

   **Verify the exposed VALUES, never the DDL's success.** Re-creating the view
   without the cast the live one had (`((col)::jsonb - 'key')` vs plain `col`) can
   run cleanly and still restore the sanitisation you just removed: the statement
   succeeds, PostgREST reports the new definition, and `correctAnswer`/`solution`
   is live again. Probe with the anon key (`?select=col&limit=3`) and read the JSON
   KEYS (`['options','question']` = clean; `correctAnswer` present = re-exposed).
   A view reporting `jsonb` while its base column is `text` is the fingerprint of
   a hand-made definition no repo migration describes — and an app that falls back
   `typeof x === 'number' ? x : 0` turns a MISSING key into "option 0 is correct",
   so the symptom surfaces as "the right answer is marked wrong", not as an error.

   **A view that lists its columns EXPLICITLY makes every base-table column
   addition a two-part change.** `CREATE OR REPLACE VIEW ... SELECT a, b, c` does
   not grow when you `ALTER TABLE ... ADD COLUMN`: the new column never reaches
   whoever reads the view. In the role-split pattern that is the worst shape —
   staff read the base table and see it, students read the view and silently do
   not — so the feature that needs the column looks like a client bug. Re-issue
   the view with the new column appended (order rule above), then re-`GRANT
   SELECT`. Adding the columns to the base table and calling it done is the
   failure mode; probe the VIEW for the new column name, not the table.

Quick live probe (runs with the repo's own deps; `npx tsx probe.mts`):

```ts
const { error, count } = await c.from(t).select('id', { count: 'exact', head: true });
// for t in [baseTable, studentView] x key in [anon, service_role]
```

## Step 5b-bis — Prove a deploy with an object only the new build could serve — and read its body

Establishing that a deployment is live needs an artifact-introduced file, and the
proof is its **Content-Type plus body**, never a status code:

```bash
curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}\n' "$APP/<path-of-a-static-file-added-in-the-same-commit>"
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "$APP/<same-dir>/no-such-file-xyz"   # control
```

Fetch the CONTROL in the same sweep: a catch-all route (`"src": "/(.*)"` →
`/index.html`, standard in these repos) answers `200 text/html` to every path
that does not exist, so a `200` alone is indistinguishable from a miss. A
measured example: a newly added `.../flowchart-dasar.svg` answered
`200 text/html` with a `<!doctype html>` body, identical to a deliberately
invented path — the asset was NOT live, and the same probe had already been read
once as "deploy works". Reversed after the real deploy: same URL, `200
image/svg+xml`. Report which of the two you measured; "the asset is served" and
"the catch-all answered" are different conclusions and only the first is a
verification.

Also note in this shape: a stale `Age:` header is not proof of a stale deploy —
the HTML entry and its hashed bundle sit behind a cache while the deployment
itself can be fresh. Distinguish *artifact live but bundle cached* from *deploy
never triggered*; the asset probe above is what separates them.

## Step 5b-bis — Prove a host/SQL-Editor object exists before handing over DDL

Before telling the user "the fix needs no DB change" — or after handing them a
migration to run by hand — check whether a **SQL-execution RPC** already exists
in the project. PostgREST CALLS these like any other function, so a project that
has one (commonly `exec_sql`, `run_sql`, `sql_exec`) lets you apply and verify
your own DDL instead of round-tripping through the user:

```bash
curl -s -X POST "$URL/rest/v1/rpc/exec_sql" -H "apikey: $SVC" \
  -H "Authorization: Bearer $SVC" -H 'Content-Type: application/json' \
  -d '{"query":"select 1"}'
# PGRST202 "Could not find the function public.exec_sql" => no such RPC (the normal,
# hardened case). Anything else => you just found a DDL path; use it read-only first.
```

Generalise this: **to probe a function's existence, call it and to probe a
column's existence, select it** — PostgREST answers `PGRST202` for a missing
function and `42703` for a missing column, both cheap and mutation-free. The
OpenAPI spec (`GET /rest/v1/` with the service key) also lists every RPC a
project exposes, which is the cheap way to discover sibling-app helpers.

**Read the response CODE, not just the failure, to learn whether the object
exists at all** — the four answers mean four different things and only the first
is "missing":

| response | meaning |
| --- | --- |
| `404 PGRST202` | function genuinely absent from the schema cache |
| `401 42501 permission denied for function` | function EXISTS, role lacks EXECUTE |
| `400 P0001 <custom RAISE message>` | function EXISTS and its body ran |
| `200` | exists and callable |

So a `42501` on a function you are about to hand over as DDL is a *pass*: stop
looking for the migration and say the object is already live. Guard a RPC probe
against mutating anything by picking arguments whose first check rejects —
`p_caller_id: 0` on a function starting `IF p_caller_id IS NULL OR p_caller_id = 0
THEN RAISE 'Akses ditolak.'` exercises the body and writes nothing.

**Probe GRID:** the platform rate-limits by connection, so a wide `xargs -P`
sweep returns a wave of empty results that reads as "nothing found" — verify the
sweep actually ran (one known-hit id in the range, or the same range at `-P 4`)
before concluding the object does not exist. A hit is impossible to miss when
you print the payload: sweep for a NON-EMPTY answer, not a `true`/`200`, and the
hit prints itself. `seq 1 6000 | xargs -P 32` located a live row id, but the
same sweep at a higher parallelism returned `0 found` with no error at all.

**When you have no service key for the target project, the ANON key from the
deployed bundle (`/assets/index-*.js`) is enough for a probe GRID: the OpenAPI
spec is `401` for anon, but anon-granted RPCs still answer.** That is a real read
path, not a theory — it located a live row id (`p_viewer_id` sweep over `1..6000`
with `xargs -P 32`) that was needed to prove a migration had been applied.

**Prove a REPLACED function is live by its new BEHAVIOUR, not by re-reading the
DDL.** An existence probe cannot see a rewritten body, and the repo file is a
hypothesis either way. Pick an argument pair that only the new definition answers
differently and compare the two counts — e.g. the new body calls a helper that
did not exist before (`public.classes_match(...)`, which would fail the whole call
if absent) *and* branches on `p_schedule_id`, so `p_schedule_id: <real> -> 7 rows`
versus `p_schedule_id: null -> 33 rows` proves both the helper and the widened
scope at once. A `200` plus the WRONG count (33 in both) reads exactly like a pass
if you only check the status.

**Confirm which of the two halves is deployed before reporting a frontend fix.**
Widened SQL without the frontend shows every classmate; the frontend without the
widened SQL shows the caller alone. Count the rows — do not infer, and do not ask
which side "should" already be out.

**Never re-probe the ORIGINAL symptom to decide whether the user ran your SQL —
pick an object independently known to need that same migration.** A widened
student-scoped RPC answers `[]` for a user id swept out of a DIFFERENT project,
so it proves nothing either way and reads as "not applied" when the migration
may be live. Same for an existence probe on a helper you just created if the id
you probe with does not exist over there. Establish the target project's live
state first (a helper that only your migration defines, probed with arguments it
answers regardless of data), then judge the rest against it.
**Before you judge the user's paste-back, prove YOUR OWN probe reads the SAME project their SQL Editor is pointed at — a session holding keys for two projects mixes them without noticing.** Decode the `ref` claim out of every key in play (print only `ref`/`role`/`iss`, never the key value) and label each probe with the project it came from. A table read driven by a local `.env` `SUPABASE_URL` while the RPC probes use an anon key parsed out of the deployed bundle are TWO different databases, and reporting the first as "production's state" is the error: the project you READ must be the project the symptom lives in.
**When the user pastes back a verification result, diff it against YOUR OWN live
query of that same table, not against the expectation you stated.** A paste-back
showing one casing with N menus for a row set that still holds both casings means
it ran against another project — and a menu COUNT that exceeds both sets' sizes
(`5` where the two sets hold 4 and 3, and a `DELETE` cannot add rows) is
arithmetically impossible from the script you handed over, so say that instead of
accepting the number. The most common cause of "I already ran all of them" is a
second Supabase project open in the SQL Editor; each JWT carries a project `ref`
claim, so decode the payload of every key in play (print only `ref`/`role`/`iss`,
never the key) and state which project each belongs to.

When no such RPC exists (and no `DATABASE_URL`), do not stall and do not invent
one — a DDL-executing RPC shipped for convenience is a far larger hole than the
one you are fixing. Write the migration file into `supabase/migrations/` with the
repo's own naming (`YYYYMMDDHHMMSS_description.sql`), commit it as the audit
trail, and tell the user plainly that **the SQL still has to run in production**,
with the exact route (SQL Editor, `supabase db push`) and what access that needs.
Say "migration written, not applied" — never "fixed" — and name what the user
must do before the symptom changes.

## Step 5c — "Not found" from a server route: separate a missing row from a missing credential

When an app route reports the record does not exist, do NOT accept that as the
verdict — first prove the route is executing with the credentials it needs. The
cheap discriminator is a **deliberately incomplete request**: send an empty body
and one missing-field call. A live handler answers `400 Missing required fields`
and an unauthenticated call answers `401`; if both come back as expected, the
handler is running and only the DB read failed.

```bash
# handler alive?          -> 400 (validation ran)
curl -s -X POST "$APP/api/validate-quiz" -H 'Content-Type: application/json' -d '{}'
# auth layer alive?       -> 401
curl -s -o /dev/null -w '%{http_code}' -X POST "$APP/api/validate-quiz" \
  -H 'Content-Type: application/json' -d '{"lessonId":"<real id>","selectedOption":0}'
# then with a real token: 404 on an id you KNOW exists == misconfiguration, not a missing row
```

Mint the token with the app's own secret so the probe exercises the real path
rather than a bypass:

```ts
const token = await new SignJWT({ nim: '<real nim>', role: '<role>' })
  .setProtectedHeader({ alg: 'HS256' }).setIssuedAt()
  .setExpirationTime('10m').sign(new TextEncoder().encode(process.env.JWT_SECRET!));
```

**A server route that swallows its DB error into one generic 404 hides a missing
environment variable behind a data-shaped message.** Collapsing `error || !row`
into `404 Not Found` means an unset `VITE_SUPABASE_URL` /
`SUPABASE_SERVICE_ROLE_KEY` in the host is indistinguishable from a row that does
not exist, and the user chases content instead of configuration. Split the
branches: return `404` only for the no-rows code (`PGRST116`), and `500` plus the
Postgres code for everything else — the diagnostic IS the fix here, because the
next probe then names the cause.

- **A "not configured" message from a server route usually means the handler
  never parsed the column.** After the env is fixed and the route starts reading
  the DB, the next failure in the same class appears: a route that reads a JSON
  column and immediately tests `typeof row.col.someKey` against a column that is
  **`text` holding JSON** (see Iron rule 4) — `PostgREST` returns a STRING, the
  key reads `undefined`, and every row is reported as unconfigured
  (`400 Lesson does not have a quiz configured` for all 81 lessons). The route's
  own SELECT list proves nothing; check the column type in the OpenAPI spec
  (`properties.<col>.format`) and add `JSON.parse` with a guarded branch
  (`try { JSON.parse } catch { 500 data-rusak }`) rather than defaulting to an
  empty object. Diagnose in this order when a route reports missing data that
  exists: env/credentials → row actually fetched → column parsed.
- **Server-side reasoning does not extend to client env vars — they are inlined
  at BUILD time, so there is nothing to verify at runtime.** For the serverless
  handler the bullet below applies. For the bundle the opposite holds:
  `import.meta.env.VITE_*` is replaced by a literal during the build, so a
  deployment built without the value cannot be repaired afterwards — the variable
  must exist for that environment *before* the build. Scope is per-environment: a
  value set for Production is invisible to Preview, and a Preview build with the
  variable unset throws at module load (`Uncaught Error: supabaseUrl is required`)
  even though Production is fine. Enumerate what the frontend actually needs with
  `rg -o 'import\.meta\.env\.[A-Z_0-9]+' src/ | sort -u`, and when the affected
  environment is one the user does not use, say so plainly instead of proposing a
  fix — do not let a Preview-only failure read as a production defect.
- **The env key name differs between client and server.** These repos ship
  `VITE_SUPABASE_URL` in `.env` for the bundle, while the serverless handler reads
  `process.env.VITE_SUPABASE_URL` with no `VITE_` fallback — so the value exists
  locally and is still absent in the host's environment. List the handler's own
  requirements before blaming code:
  `rg -o "process\.env\.[A-Z_]+" api/<route>.ts api/auth.ts | sort -u`.
  Fixing this is a host-side setup step (add the variables, redeploy), never a code
  change; hand the user the exact key names and scope.
- **A route that only PROXIES the backend proves nothing about host env.** A
  sibling route returning a clean `400` for bad input shows the function is
  deployed, not that Supabase credentials are configured — `api/login.ts` may just
  forward to another service. Test the specific route whose credentials you doubt.
- **After handing over the env setup, RE-PROBE — an unchanged response means the
  running deployment never received the values.** A host applies environment
  changes only on the next deploy, and the resulting failure is byte-identical to
  the original, so re-running the probe *is* the verification step; there is
  nothing else to check in the code. When it is still broken, walk the setup, not
  the handler: values saved under the wrong scope (a Preview-scope entry is
  invisible to Production), a mistyped key name (`SUPABASE_URL` instead of the
  `VITE_`-prefixed name the handler reads), a value pasted with quotes or a
  trailing space, or a deploy that was never re-triggered. Ask the user for the key
  NAMES and scope, never the values, and treat "I already changed it" as
  unverified until the probe agrees. If the client half of the fix depends on this
  route, do not ship that half while the route is still failing — it converts a
  wrong-answer bug into a cannot-answer one.
- **A new deployment does NOT mean the browser sees new code — probe an
  artifact-introduced ASSET, not the page.** The HTML entry and its hashed bundle
  are served through a cache (an `Age:` header in the tens of thousands of seconds
  is normal), so after a verified push + deploy the served bundle hash can be
  byte-identical to the pre-deploy one while the deployment itself is live. The
  freshness probe with zero ambiguity is a file that only the new build could
  produce — a static asset added in the same commit: request it and read the
  status (`200` = the new deployment is serving, `404` = still the old build).
  Distinguish the two conclusions before acting: *artifact live but bundle cached*
  is a different situation from *deploy never triggered*, and only the second
  means the host is misconfigured. Name both in the report rather than reading a
  cached hash as "the deploy did not happen".
- **Never verify a deployment against a DIFFERENT object than the one you made
  the claim about.** Two proxy checks are invalid and they both look like passes:
  a health endpoint (a route that 404s in both builds because the file returns 404
  by design, or that a catch-all rewrites) and a sibling API route (see the proxy
  bullet above). Fetch the exact asset or the exact route your change touched.
  When asked to confirm a deploy, and when the code claim is about a specific page,
  state what you measured on that object — do not upgrade a pass on another
  endpoint into "deployed correctly".

## Step 5d — A single account locked out of a registration-gated login flow

Symptom: one NIM/email "belum terdaftar" (or cannot log in) while its roster row
exists and everything works for peers. Do not read the resolver's message as the
verdict — it is derived from a column, and the column can disagree with the row.
Probe in this order, cheapest first:

```bash
# 1. the app's own public step-1 endpoint (the page's first XHR) — read the WHOLE body:
#    a response carrying `is_registered: true` AND a message saying the account is
#    NOT registered is self-contradictory, and that contradiction IS the bug.
curl -s -X POST "$API/api/auth/cek-nim" -H 'Content-Type: application/json' -d '{"nim":"<nim>"}'
# 2. the row itself (service key) — list the credential columns explicitly, never `select=*`,
#    so a NULL is as visible as a set value:
curl -s "$URL/rest/v1/users?select=id,nim,nama,is_registered,password_hash,fb_password_hash,supabase_user_id,email,updated_at&nim=eq.<nim>" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC"
# 3. the audit trail, for the WRITER that produced this state:
curl -s "$URL/rest/v1/audit_logs?select=action,nim,description,ip_address,created_at&order=created_at.desc&limit=40" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC"
```

Step 3 is what names the cause: an audit table of `action`/`description`/`ip_address`/
`user_agent`/`created_at` lets you reconstruct the exact admin action sequence
(`RESET_PASSWORD` then `UPDATE_USER` on the same id) and confirm it against the
row's `updated_at`, instead of guessing from source. Then prove the blast radius is
scoped before touching anything — count the pattern, not the anecdote:

```bash
# every row that cannot log in and cannot re-register
curl -s "$URL/rest/v1/users?select=id&is_registered=is.true&password_hash=is.null&supabase_user_id=is.null" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" -H "Prefer: count=exact" -H "Range: 0-0"
```

Fix the row (a single `PATCH` of the flag needs no DDL and takes effect
immediately), then harden the gate so the class cannot recur. Both halves: see the
boolean-drift pitfall below.

**Verify the repair through the app's OWN login endpoint with the real credential,
not by reading the row back — and SPACE the probes.** The login route is typically
rate-limited per IP (10/min in these apps), so a burst of candidate-password
attempts answers `401`/`429` for the later ones and reads as "wrong password" when
the credential is fine; sleep a few seconds between attempts and accept only a
`200` carrying a token as proof. When the user asks you to give the locked-out
account a known default password, generate the hash with the BACKEND's own hasher
(`go run ./cmd/hasher <pw>`, or match the `$2a$`/`$2b$` prefix and cost of an
existing row) so it satisfies that verifier, then `PATCH` `password_hash` and the
flag in ONE request and log in once to confirm the account can then change it.

## Step 5e — Reproduce a client-interaction bug against BOTH bundles

For defects with no error to read ("one item got skipped", "the step advanced on its
own"), script the flow in a real browser against the DEPLOYED bundle and against
`localhost`, diff the two transcripts, and report the pair. Full workflow — token
minting, state clearing between runs, the CLI's stdin/base64 escaping and timeout
limits, assertable state, and a worked example — in
`references/browser-flow-reproduction.md`.

A checked-in bug writeup (`STATUS-*.md`) is a hypothesis, not a status: re-probe
the live route before acting on it.

## Step 6 — Compare role vocabularies

The highest-yield bug class in these apps: **the database stores one set of role
strings and the app's hardcoded whitelist expects another.** Pull the distinct
values and compare:

```bash
curl -s "$URL/rest/v1/users?select=role" -H "apikey: $SVC" -H "Authorization: Bearer $SVC"
```

Then search the API/route/sidebar code (`search_files`) for the whitelist it
actually checks. A mismatch (e.g. DB `mahasiswa` vs whitelist `praktikan`)
rejects the majority of users at the first gated call — before any redirect ever runs.
The same mismatch hides *inside* DB functions: a role literal compared inline
(`role = 'koordinator'`) rejects an alias role (`kordas`) that the app-level map
already accepts, so the feature fails only for those accounts. Sweep every
function definition, not just the named helpers — see
`references/rbac-sso-debugging.md` §4.

**The client half is worse, because it fails silently with no error and no
403.** Once a normaliser runs at the auth boundary
(`role: canonRole(dbUser.role)` at profile load / `login()`), `user.role` is the
CANONICAL value everywhere downstream — so every page that still compares the
RAW DB string takes the wrong branch forever:

```bash
# run this on any app whose auth layer normalises the role
rg -n "role === 'mahasiswa'|role === \"mahasiswa\"|'mahasiswa'|'peminjam'" src/
```

Measured blast radius in one app: a student's dashboard rendered **nothing**
(the canonical `praktikan` branch never matched, and the `!role` fallback did not
fire either), the schedule page showed the staff layout, and the attendance
class roster came back empty — three unrelated-looking symptoms, one cause. Grep
for EVERY raw literal of the old vocabulary (including the write side: form
defaults, `<SelectItem value=…>`, `key:`/`roles:` arrays in nav config, route
`allowedRoles`) and either replace them with the canonical strings or wrap them
in the same normaliser. A vocabulary migration is not done while a raw literal
survives anywhere in the client.

**A route guard and a nav allowlist are TWO independent lists, so a feature can be hidden-but-reachable or visible-but-refused — check both before diagnosing.** The route carries its own gate (`requiredMenuKey`, `allowedRoles`) and the sidebar filters a separate items array with its own predicate; a page that "cannot be opened" may be refused by the route while the nav still lists it, or missing from the nav while the URL works. Grep for both (`rg -n "requiredMenuKey|RESTRICTED_MENUS|allowedRoles|allowedPaths" src/`) and read them together. When the two disagree, extract the shared predicate into ONE exported constant rather than editing both by hand.
**A menu gated by a `division_access` row is invisible to every division not listed in it** — so "works for K3 but not for BENDAHARA" is usually not a permission bug to fix in the DB, it is a menu that was never granted to that division. When the user asks for a page to open for *every* member of a role regardless of division, the fix is an EXEMPTION list (basic work tools, not per-division privileges) exported as ONE constant from the roles module and consumed by BOTH the sidebar filter and the route guard. Widen the DB grant instead only if the page genuinely is a per-division privilege — and say which of the two you chose, because it changes who gets access.

## Step 6b — Role fix breaks a sibling app: one column, several vocabularies

Symptom: after a role change in app A, the account loses access in app B. When
several apps share one `users.role` column, each may define its own role enum
(e.g. one accepts `mahasiswa/asisten/koordinator`, another
`praktikan/asisten/kordas/admin`). A writer in one app can then store a value
that is invalid for another — a distinct failure shape from a read-side
whitelist mismatch: the DB row itself has become unrecognisable.

Diagnose: list every app's role enum (backend constants/enum file, frontend
guards, DB functions) and the distinct values actually in the column; the
victims are the rows whose value is in only one enum.

Fix without a big refactor:

1. Restore the broken rows to the canonical value immediately (data fix first).
2. Find every WRITER of the column across all apps (`rg "update\(\{[^}]*\brole\b"
   src/ api/`); it is often a single admin UI handler.
3. Add a `toCanonicalRole()` map at that write boundary (app role → shared
   canonical value) and keep the existing read-side `normalizeRole()` for
   display, so UX is unchanged.
4. Add a DB guardrail so future writers cannot reintroduce the bug: a
   `BEFORE INSERT OR UPDATE OF role` trigger that normalises non-canonical
   values, plus a one-time `UPDATE` to clean legacy rows. Hand the SQL to the
   user (service_role cannot run DDL — Step 7.5).
5. **If the user wants the app-specific role to SURVIVE (not collapse into a
   canonical one), store it in a shadow column** (e.g. `elearning_role`) owned
   by that app: the shared `role` column keeps canonical values for all apps,
   the app reads its effective role via `resolveAppRole(role, shadow_role)` at
   profile load, and its admin UI writes `role = toCanonicalRole(x), shadow =
   x`. Verify no other app selects `*` and chokes on the extra column first
   (PostgREST just returns it; most readers ignore unknown keys).
6. **Audit every trigger that rewrites `role` — a `BEFORE INSERT OR UPDATE OF
   role` normaliser is a silent ESCALATION channel, not housekeeping.** One live
   trigger mapped `admin -> koordinator`, so any writer storing the app-local
   value in the shared column silently GRANTED coordinator rights; it also mapped
   `kordas -> koordinator`, so `is_admin('kordas')` checks never saw what the app
   wrote. Make such a trigger leave unknown values UNTOUCHED instead of mapping
   them, and read the live body with `pg_get_functiondef` — the repo's migration
   may define an already-fixed version while the DB still runs the old one, so
the installed trigger is what governs.
7. **The shadow column has two more touch points besides the resolver, and
either one silently voids the flag.** (a) **Every SELECT list that feeds the
resolver must name the column.** An explicit
`select('id,nim,...,role,...')` that omits the shadow column makes the resolver's
second argument `undefined` for every row, so `resolveAppRole(role, undefined)`
returns the lower role and the account renders exactly like a normal one — no
error, no 403, no console warning. Grading the resolver's own source reads as
correct, so grep every profile/row query in the client for the shadow column and
diff the lists against EACH OTHER: in a multi-page app one page's list gets
updated while the app-wide one is forgotten, which is why the admin screen shows
the flag and the rest of the app does not. (b) **A profile-sync routine must not
write the token's role over a stored role that ranks higher.** The token minted by
the sender predates any promotion made in this app, so a routine that writes the
token's value whenever it differs from the stored one DEMOTES a promoted account
on its very next login — and the same line, mirrored, UNDOES a demotion (the
stale token still carries the old higher role, so the write restores it). Guard by
HIERARCHY rather than equality: never write a role that ranks below the stored
one, and treat a stored role above the token's as the deliberate admin action it
is.

## Step 6c — Seed one test account per role to exercise gates end-to-end

Role bugs are only proven with a real account of each role. Seed throwaway
users directly (service key) and log in through the app's own login endpoint:

```ts
// hash must match the BACKEND's verifier — check an existing row's prefix
// ($2a$/$2b$ = bcrypt; Firebase-migrated rows may use scrypt in a separate column)
import bcrypt from 'bcryptjs';            // add --no-save if the repo lacks it
await sv.from('users').upsert({ nim: '999900001', nama: 'TEST Praktikan',
  role: 'mahasiswa', password_hash: bcrypt.hashSync(PW, 10),
  is_registered: true /* + NOT NULL cols */ }, { onConflict: 'nim' });
// then: POST <app>/api/login {identifier, password} -> use the returned token
// with createClient(url, anon, { global: { headers: { Authorization: Bearer ... }}})
```

Use obviously-fake IDs (e.g. `9999000xx`), delete them when done, and name them
`TEST <role>` so a later audit doesn't mistake them for real users.

## Step 6d — Rename a parent key that children FK to (relabel safely)

Renaming a level/category id that child rows FK to (e.g. curriculum levels
whose `modules.level_id` references them) must go **insert-new → re-point →
delete-old**, never update-in-place or delete-first:

```sql
INSERT INTO levels (id, ...) VALUES ('level-1', ...);      -- new parent exists first
UPDATE modules SET level_id = 'level-1' WHERE level_id = 'c-level-1';  -- re-point children
DELETE FROM levels WHERE id = 'c-level-1';                 -- only now remove old parent
```

PostgREST can run all three steps with the service key (no DDL needed). Check
BEFORE choosing this over a plain `UPDATE levels SET id=...`: if any FK to the
parent lacks `ON UPDATE CASCADE`, the in-place update fails mid-way; the
three-step order never violates a FK. Student progress that references the
*grandchild* ids (lesson ids) is untouched as long as only the parent id
changes — verify with a per-level module/lesson count before and after, and a
zero-orphan query (`children whose parent_id is not in the new id set`).

**After the rename, sweep the frontend for code that matches the OLD id SHAPE,
not just literal old ids.** Changing `c-level-1`/`py-level-5` to `level-1..6`
leaves every prefix/segment filter silently returning the empty set — the page
renders blank with no error, which reads like a data problem but is a
string-matching one:

```bash
rg -n "startsWith\('|endsWith\('|split\('-'\)|slice\(.*\)\.includes|findIndex\(.*\.id" src/
```

A filter like `curriculum.filter(l => l.id.startsWith('c-'))` (and its `p-`
sibling) yields 0 rows for every level once ids lose that prefix, so the whole
level grid and its per-language progress bars vanish. Re-key such filters to a
stable field (the new id, `sort_order`, or an explicit `language`/`kind` column)
instead of the id's shape, and re-check any `id.split('-')`-style parser.

## Step 6e — Two apps, one metric: reproduce BOTH computations from raw rows

Symptom: "the progress here doesn't match what the other app shows." Do not read
both code paths and compare them — replicate each side's number from raw rows
with one script, print numerator/denominator/ratio for the SAME user, and let the
numbers name the cause. The causes, in the order they actually occur:

1. **Denominator/scope mismatch** — the displaying app divides by a gated subset
   (only unlocked levels, only visible items) while the handler divides by the
   whole set. Read the DISPLAYING app's formula and reimplement its gating in the
   handler, keeping the numerator's scope identical to the denominator's.
2. **Arithmetic** — recompute by hand; a scaling constant plus a clamp
   (`(a/b) * 105` then `* 100`) reports percent-of-percent and saturates early.
3. **Broken data path** — a nested embed that returns 0 leaves totals zero and
   looks like "no data". `select=*&limit=1` on the child table to learn its real
   columns, then use a two-step join or add the missing FK.
4. **Identity mismatch** — the token/row key the handler uses is not the key the
   other app stores. Enumerate every candidate key column per table and probe one
   known user against each.
5. **Wrong DB** — the two sides are not reading the same project at all. A
   denominator that is CONSTANT across every user (same `total_lessons` for the
   best and worst account) is the signature: the handler is reading a DB you have
   not probed. Check this BEFORE the four above — it invalidates all of them.

Full recipes (probe snippets, the identity-key inventory, the anon "must be `[]`"
negative probe, how to prove both sides share one project before you change
anything, and how to lock the agreed numbers in a test) are in
`references/cross-app-data-consistency.md`. Decide the target number WITH the user
before editing either side, and when you clean up existing rows, recompute from
the source DB — report any key that does not exist over there instead of inventing
a value for it.

## Step 7 — Apply the fix safely, then verify it shipped
Once the gate is localised, the fix is usually a small boundary change (an alias
map, a helper function, a grant row). Land it so you can *prove* it regressed nothing:

1. **Follow the repo's flow; don't branch unprompted.** On a repo with a review
   flow, land the change on a branch and open a PR. On the user's own solo repo
   that auto-deploys its default branch, they often want it committed straight to
   `main` — an unexplained branch reads as a detour ("why not main?"). Ask, or
   follow the convention the repo already shows. Land the message via a **file**
   (`git commit -F <path>`); an inline `<<'EOF'` heredoc is refused by the
   terminal wrapper on these Windows runs. **Read `git diff --cached` before you
   write the body.** A patch you wrote and then reverted mid-session (scope
   creep, a second concern you decided to leave for later) leaves the commit
   message asserting a fix the diff does not contain, and the message is what
   the next reader — including you — trusts instead of re-reading the one-line
diff. Count the changed files in `git show --stat` against the claims in the
   message; when they disagree, either restore the change or cut the claim.
   **`git fetch` BEFORE committing, every time — a teammate pushes to the same
   default branch while you work.** Compare against `origin/<branch>` and count
   both sides (`git rev-list --left-right --count origin/main...HEAD`); a file you
   are about to commit is often in the incoming set, and discovering that after
   your commit turns a clean rebase into a conflicted merge. Then merge (never
   rebase a branch others have) and prove the result is pushable with
   `git merge-base --is-ancestor origin/main HEAD` — success there means the push
   is a fast-forward, which is the actual answer to "is this safe to push?".
   **Resolve a conflict on the union of the two intents when each side fixed a
   different aspect of the same line**, not by picking a side. Read both hunk
   bodies before editing: one side may have swapped the vocabulary (`canonRole`)
   while the other added a format-tolerant comparison for the same variable, and
   either alone is a regression. Also re-derive any branch the other side added
   that your change now subsumes — a new `role === 'admin'` case is dead code once
   your alias map already normalises `admin`, and keeping it reintroduces the bug
   you just fixed.
2. **Compare typecheck AND lint counts against a baseline.** These repos often
   carry pre-existing type errors and lint noise, so a bare `tsc --noEmit` or
   `eslint .` "fails" and tells you nothing about your change. Capture the error
   SET on your branch and on the base branch (stash → checkout base → run →
   return), then diff the two sets. Report "0 new errors", not "tsc failed".
   `git stash -u -q` … `git stash pop -q` wraps the base run in one command, and
   for lint the counted summary line is the diff-able artefact:
   `bun run lint 2>&1 | grep -E '^✖'` → `237 problems` vs `244 problems`. Then
   account for the delta by rule name — a repo whose whole lint budget is
   `no-explicit-any` will show every new `any:` annotation you added, which is a
   measurable, reportable number rather than a claim that lint is "pre-existing".
   **`git worktree add <dir> HEAD` beats the stash dance for this**: run the
   baseline suite/lint/build in the clean worktree in one command, with zero risk
   to uncommitted work and none of the "No stash entries found" confusion when the
   user commits the same tree mid-session (which silently no-ops `git stash push`
   *and* `git stash pop`). Remember to `git worktree remove <dir>` after.
   **Read the WORKING TREE before editing a file you last saw earlier in the
   session.** A teammate's uncommitted edit to the same file, an untracked
   migration, or a formatter run makes your stale read wrong; patch from a fresh
   read or you silently clobber their fix. A stray untracked
   `supabase/migrations/*.sql` named after the very table you are touching is a
   signal to read it before designing your change — it may already target the
   function you were about to ask the user to modify.
   **The user commits the same tree while you work, so a commit can already
   contain YOUR diff — check before re-applying it.** A patch you wrote minutes
   ago can land under a commit authored by the user with a tidier message, and
   every stale signal then misleads at once: `git stash` reports "No stash
   entries found", `git diff` looks empty, and your read of the file appears
   reverted. Confirm with `git log --oneline -3` plus `git show <sha> -- <file>`:
   when the hunks are yours, the change is already landed — do not re-patch and do
   not re-commit it. Re-read the file from disk before the next edit either way,
   and re-run `git status` rather than trusting the session-start snapshot.
   **Never quote a commit SHA you have not just resolved on disk.** A handoff
   summary, an earlier turn, or a note file can name commits that were never
   created in this repo, and the error stays invisible until someone tries to check
   one out — `git cat-file -t <sha>` answers `fatal: Not a valid object name` while
   the work itself is fine and landed under a different hash. Before reporting a
   SHA, resolve it (`git log --oneline -20`, `git merge-base --is-ancestor <sha>
   origin/<branch>`) and say what you measured; if a hash does not resolve, say so
   instead of reasoning from it — the diff on disk is the truth, not the identifier
   you remembered.
   **Prove a failing test is pre-existing the same way: run THAT test on the
   stashed base and show it failing there too.** A suite where one test fails
   before and after your change is a different report from one where your change
   broke it — say which you measured, and never let a pre-existing red test hide
   behind "some tests fail".
3. **Build.** `vite build` / `next build`; a green build is the real gate.
4. **Confirm the fix reached the artifact.** Grep the minified output bundle for a
   distinctive string your change introduced (an alias key, a new table name).
   A source edit that never reached the bundle is the classic silent no-op.
   **When the change adds a COLUMN to a select list, the bare column name proves
   nothing — the bundle can already contain it from another call site that reads
   the same field as a property.** Measured: `select('...,role,xp,...')` in one
   component and the same column in a second component's list left the bundle
   showing `role,elearning_role,xp,level` after the build, while the pre-fix
   bundle matched on a bare `elearning_role` count of 1 for exactly that reason.
   Grep the SELECT LITERAL (`role,<col>,xp`) or the property read of the ROW
   object, and say which of the two you measured.
   **A JSON backend on its own host (`api.<domain>`) has no bundle to grep and no
   asset to fetch — prove it with a DISCRIMINATING BEHAVIOUR probe.** Pick the one
   input whose answer differs between the old and new build and send it: a request
   the old code overwrote (or admitted) must now be REFUSED, and a row the old code
   reported as unregistered must now report as registered. Re-probe the reported
   symptom AFTER the deploy and read the response BODY, not the status — a fix that
   turns an account-takeover into `409` and a locked-out row into `200 registered`
   is two probes, both cheap, neither provable by a `200` on an unrelated route.
   **Read per-project deploy state from the commit status API — it needs no CI
   workflow in the repo:** `curl -s
   https://api.github.com/repos/<owner>/<repo>/commits/<sha>/status` lists one entry
   per Vercel project (`Vercel – <app>-backend`, `… -frontend`) with `state` and a
   `target_url`; overall `state: success` is what "both halves deployed" means.
   Vercel reports `pending` for a minute or two after the push, so poll it instead
   of concluding the deploy never triggered.
5. **Hand DB changes to the user.** The `service_role` key is a *PostgREST* key:
   it reads/writes rows and calls RPCs, but it CANNOT run DDL (`CREATE OR REPLACE
   FUNCTION`, `ALTER TABLE`, `CREATE INDEX`) and cannot read `pg_catalog` — the
   OpenAPI spec carries schema but **zero information about RLS, grants, policies,
   view owners or function bodies**. When no DB connection string or Supabase
   personal access token is present, do not stall and do not keep probing: hand
   the user **copy-pasteable read-only SQL**, one statement per block (the
   Supabase SQL Editor renders only the LAST statement's grid, so several
   statements in one block silently discard the earlier results). Say briefly what
   you are looking for in each block so their paste-back is unambiguous, and give
   them the whole runnable set in one message rather than revealing it a query at
   a time. Start from
   `scripts/catalog_rls_introspection.sql` — it holds the full read-only catalog
   query set (object kind, RLS flags, policies, table/column grants, view owner,
   function SECURITY, triggers, live role vocabulary) in that one-statement-per-block
   form. Every one of those queries is `SELECT`-only, so say so explicitly: an
   audit that mutates is a different conversation.
6. **Paste the SQL into the chat itself — a repo file is the record, the message
   is the delivery.** When the fix is DDL the user must run, they will ask for it
   inline even if you already committed it; hand the ordered blocks in the reply,
   keep the file for the audit trail, and say which block is which. End any block
   that creates or replaces an RPC with `NOTIFY pgrst, 'reload schema';` —
   otherwise the new function can still answer `404 PGRST202 Could not find the
   function` after a successful apply, and a `404` right after the user ran your
   script reads as a failed migration when only the schema cache is stale.
   **Make every handed-over migration IDEMPOTENT and end it with a verification
   `SELECT` whose expected output you state in the message.** These repos apply
   migrations by hand, so the user may re-run one you already delivered (
   `CREATE OR REPLACE` / `IF NOT EXISTS` / a `DELETE` that no-ops make that safe),
   and a stated expectation ("expected: exactly one casing per division —
   `BENDAHARA` 3, `K3` 5") turns their paste-back into a pass/fail instead of a
   transcript you have to interpret.
   **A GitHub push does NOT apply a migration — say so before they ask.** Check
   for a DB workflow (`ls .github/workflows/`) and treat the Supabase CLI link as
   untrustworthy: `supabase/config.toml` routinely names a DIFFERENT `project_id`
   than the deployed app's ref, so `supabase db push` would hit the wrong database.
   When reporting status, keep three separate columns — code committed, code
   deployed, SQL applied — and answer "is it done?" from a live probe of each,
   never from the push.
7. **Close with the user's remaining actions as a short numbered list, and state
   whether a deploy is needed.** A DB-grant fix takes effect with no redeploy,
   while a bundled source change does not — saying which one this is stops a
   pointless deploy (or a mistaken wait). **Map every change back to the symptom
   it fixes, one line each, and say explicitly which reported symptoms are NOT
   covered.** Several fixes accrue in one session (a widened RPC, a stale-grant
   workaround, an unrelated push path), and a bare list of commits and migration
   files leaves the user guessing which artifact answers the question they asked —
   they will re-ask "does this fix Y?" and the answer may be "no, that one needed
   no SQL at all". Name the negative result too: the guard
   that correctly REJECTED an escalation with `400 P0001` is as much a verification
   as the request that started returning `204`.

## Pitfalls

- **Never gate a flow on a denormalised boolean that summarises a column — gate on
the column.** A flag like `is_registered` / `has_password` / `is_active` can drift
from the data it summarises, and a drifted row locks the user out of BOTH branches
at once: the status endpoint reports "not registered" while the claim/register
branch refuses with `ErrConflict` because the flag is already true, and login fails
because there is no credential to verify — three paths, no way in, no error that
says so. Derive the gate from the credentials themselves in one helper
(`passwordHash != nil || fbHash != nil || supabaseUserId != nil`) and use that
helper in EVERY branch (status, login, claim); keep the flag as a display-only
column. **The drift is written by an ORM `Save`/`upsert` that persists a struct
loaded BEFORE the clearing write** — read-modify-write on the whole row re-asserts
the stale flag, which is why an admin "save" after a password reset produces it.
**The same flag usually gates the CLAIM/register branch too, so the INVERSE drift
is an account-takeover path, not a cosmetic UI bug.** A row whose flag is false
while a working credential exists is one the status endpoint tells to "create a
password" — the claim branch then passes its own check and overwrites the hash the
account logs in with, so knowing the identifier alone is enough to seize it. Count
BOTH directions before calling the data clean (`flag=true` + all credentials null,
AND `flag=false` + any credential set) and repair the inverse rows too, instead of
leaving them for the credential-derived gate to paper over.
**Never relay an assumed credential policy as fact.** "Everyone logs in with the
default password" is a claim to TEST, not a premise: run a candidate list (repeated
digits at several lengths, the identifier itself, common defaults) through the
backend's own verifier against peer rows that DO have hashes, and report the
measured ratio before telling the user what their users can log in with — 0 of 12
peers matching any candidate is how you learn no default exists and the account had
simply never registered.
**When the user asks for a specific default password anyway, set it from the
BACKEND's hasher and state the limit of what you established.** Generate the hash
with the repo's own tool (`go run ./cmd/hasher <pw>`) so the prefix/cost match the
live verifier, `PATCH` it, then log in once through the app's login route and keep
the returned token as the proof. Say plainly which accounts the default applies to —
the one you set, not a class of users — and that they change it from the profile
page. Share the credential in the reply; it is a one-off, low-value, user-requested
value, and the alternative (telling them to read it out of the DB) is worse.
- **When credentials move to a new gate, every writer that CLEARS a credential must
clear ALL of them.** Adding a field to the gate without updating the reset/clear
path leaves the old credential satisfying the gate: the reset appears to work, the
status endpoint says "already registered", and the user can never set a new
password. Patch the reset together with the gate, in the same change.
- **A 403/404 on a role-gated read can mean the gate rejected a row that LOOKS fine:
compare the row's derived flag against its credential columns before reading logic.**
Cheapest form: `?select=<pk>,<flag>,<credential cols>` with the service key. A
boolean at odds with the columns beside it is a data bug in a UI query's clothing.

- **A role-scoped RPC that filters `student_id = p_viewer_id` returns exactly ONE
  row for the student role — any peer-list UI built on it silently shows the
  caller alone.** Symptom reaches you as a frontend complaint ("the group list
  doesn't show any names"), and the page's own filter (`rows.filter(r =>
  r.assistant_id === mine)`) is usually CORRECT. The tell is a count pair: the
  raw table with the same `schedule_id`/`assistant_id` filter returns N rows while
  the RPC returns 1 — probe both before reading the page. Then grep the function
  body for the viewer-scoped predicate (`WHERE gm.student_id = p_viewer_id`,
  `custom_user_id = p_viewer_id`) and widen THAT.
  **Widening the RPC is the only possible fix, because the client's `/api/rpc`
  proxy overwrites identity parameters from the JWT** — `p_viewer_id`,
  `p_caller_id`, `p_student_id`, and for non-staff `p_user_id`/`p_target_id` are
  replaced with the token's user id before the call reaches Postgres, so no
  parameter the frontend invents can ever ask for another user's rows. Test the
  RPC directly with the service key (any `p_viewer_id`, no JWT) to see the real
  scoping; the app can never exercise that same call.
  Widen to the caller's *membership set*, not to openness: e.g. `OR gm.schedule_id
  IN (SELECT vg.schedule_id FROM public.group_members vg WHERE vg.student_id =
  p_viewer_id)` keeps a student confined to their own classes while letting staff
  keep the unrestricted branch. **Leave contact columns out of a peer-list
  projection** (`student_phone` and friends): a directory of classmates is exactly
  where PII leaks by accident, and the column was absent from the original
  contract for that reason.
- **A success reported from inside the app is not a success — verify against the
  repo the app rebuilt from.** A DELETE that the app's own API acknowledged (it
  runs with the service key and bypasses whatever blocks you) and a save the user
  reports as done can BOTH be true while the object persists: the request never
  reached the DB, or a client default re-seeded it. Before reporting "deleted /
  applied", read the target back the same way the app reads it AND check the
  version-controlled seed/build input — if the row is still declared there, it
  returns on the next rebuild no matter how clean the current state looks.
- **Don't trust the repo's `.env` for "the database".** Confirm the ref against
  the deployed bundle; multiple deployments of one product often use different
  projects.
- **A `PGRST205 Could not find the table 'X' in the schema cache ... Perhaps you
  meant 'Y'` is a rename/alias mismatch, not a missing table.** The hint names the
  table that actually exists in *that* project; align the code to the project's
  name instead of creating the stale one, and check both directions (repo→DB and
  DB→repo) before touching either.
- **Never hand the user a blanket `GRANT ALL ON ALL TABLES IN SCHEMA public TO
  anon` from a repo script without measuring its blast radius.** These projects
  are routinely shared with sibling apps, so the schema holds many more tables
  than the app uses and the script unlocks all of them. Count them first (table
  names come from the OpenAPI `definitions` keys of `GET /rest/v1/` with the
  service key), inspect the *columns* of the tables you would expose
  (`password_hash`, `fb_password_hash`/`*_salt`, phone, email), name the sibling
  tables it would touch, and hand over the scoped variant (`GRANT SELECT, INSERT,
  UPDATE, DELETE ON public.t1, public.t2 ... TO anon, authenticated, service_role;`
  plus `GRANT EXECUTE ON FUNCTION` for the helpers the policies call, plus
  `GRANT USAGE, SELECT ON ALL SEQUENCES`).
  **Grep the script for `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ... TO
  anon` — that line is worse than the blanket grant and must never ship:** it does
  not merely open today's tables, it makes every table created afterwards open *by
  default*, so the hole grows on its own and no future audit sees a deliberate
  grant. **Also read the script's `DROP POLICY` list — the names reveal the
  hardening it intends to delete:** a dropped policy called "Staf bisa
  memperbarui profil praktikan" recreated as `CREATE POLICY "Allow update users"
  ... USING (true)` silently lets anyone holding the public anon key rewrite a
  row, `role` column included. Report the script's two halves separately so the
  user knows what is safe to apply: the RLS half (`ENABLE ROW LEVEL SECURITY`,
  `DROP`/`CREATE POLICY`) cannot create a leak and is usually fine as-is; the
  grants half is the one to replace. Full recipe and SQL skeleton:
  `references/rls-exposure-audit.md` §2d.
- **`42501` "permission denied for table X" with hint `GRANT UPDATE ON public.X` can mean a single COLUMN lacks its grant — and PostgREST rejects the whole statement, not just that column.** Postgres table privileges are per-column: a role can hold `UPDATE ON t` for nine columns and be denied the tenth, and a `PATCH` body naming the tenth fails entirely, so an app feature that batches a guarded column with a normal one breaks while its sibling call succeeds. Diagnose by probing **one column per request** (`PATCH /rest/v1/t?<pk>=eq.<valid-id>` with `{col: <typed neutral>}`), never by a ranged or multi-column body: a ranged probe (`?id=gte.0`) answered 403 for *every* column and read as "no UPDATE grant at all", while the column-by-column sweep showed 9 of 43 granted. Build the neutral value from the OpenAPI type/format (`uuid` → a random UUID, integer/number → `0`, boolean → `false`, else a sentinel string) — an untyped sentinel on an `integer` column returns `22P02` *before* privileges are checked, which the sweep then misreads as denied. A denied column cannot be inferred from `information_schema` over PostgREST; the per-column sweep IS the measurement. Fix with the scoped `GRANT UPDATE (col_a, col_b) ON public.t TO authenticated;` — not the table-wide grant the hint suggests.
- **A column-level `GRANT` can open a feature whose safety lived in the grant, not in RLS.** When a guarded column (`level_access_overrides`, `assessment_access`, a role flag) is unwritable *only* because the grant is missing, the granting statement is the moment its trigger/guard must exist. Read the guard function before granting: a `BEFORE UPDATE` trigger that skips privileged callers and then compares `NEW.<col> IS DISTINCT FROM OLD.<col>` must list **every** column being opened — a flag added later (e.g. an app-specific `elearning_role` that an app-level resolver maps to full admin) is frequently absent from it, so shipping the grant without extending the trigger converts a broken button into a privilege-escalation path any user can hit with the public anon key. Hand over the `GRANT` and the extended guard trigger as ONE script with an explicit "run both blocks, in order" instruction: a user who applies only the grant has silently opened the escalation, and the UI looks fixed while the hole is live.
- **A client `select()` list is subject to the SAME per-column privilege check — one ungranted column fails the whole read.**
  This failure looks like the opposite of a missing grant, because it appears right after a deploy that ADDED a column to a select list: one page starts returning `403` while its siblings still load, which reads as a code regression. Measured shape on `users`: `select=<15 granted cols>` → `200`; the same list plus one ungranted column → `403 42501`; that column alone → `403`. So when a UI breaks immediately after a field was added to a `.select(...)`, prove the SELECT grants before touching the code — fix with `GRANT SELECT (col) ON public.t TO authenticated;`, never the table-wide `GRANT SELECT`. Expect a lopsided table as the common state: `users` had 22 of 43 columns readable and 0 of 43 updatable, so reads succeeded while every write that batched a guarded column failed — check BOTH operations per column, not just the one in the reported error.
- **The role-name and role-KEY grep finds the flag's READ but not its SOURCE — a resolver fed `undefined` degrades silently to the lower role.**
  Before concluding "the app ignores the flag", trace the variable back one hop:
  `resolveRole(row.role, row.<shadow>)` proves nothing if the `select(...)` that
  produced `row` never named `<shadow>`. Grep the shadow column across every
  profile/row query in the client — `rg -n "<shadow_column>" src/` — and when the
  hits are all property reads and resolvers with no SELECT literal among them,
  that absence IS the bug. A demo of the discrimination, cheap and with no code
  change: probe the row with the real token through both select lists and print
  `resolveRole(role, undefined)` versus `resolveRole(role, <value>)` side by side
  — the two answers differing is the proof, and it costs one script instead of a
  rebuild-deploy-observe loop.
- **A `401 42501` proves the GRANT is missing and proves NOTHING about RLS.**
  Table-privilege checks run *before* row-level security is evaluated, so when the
  grant is absent you never learn whether RLS exists, what the policies say, or
  whether this table is protected. Do not answer "is my RLS okay?" from an
  unauthenticated probe: `42501` across the board is consistent with a fully
  hardened schema *and* a wide-open one. Say what you measured ("no anon grant on
  these 13 tables") and name the RLS question as unmeasured — then get it from
  SQL, because PostgREST exposes none of it (see the next pitfall).
- **You cannot read RLS state over PostgREST — plan for handing over SQL.**
  `pg_class` / `pg_policies` / `pg_tables` / `information_schema.tables` all 404
  through `/rest/v1/`, even with `service_role`; the OpenAPI spec carries schema
  but zero policy/grant/owner information. If no `DATABASE_URL`/connection string
  is in the env and neither `psql` nor the Supabase CLI is installed, there is no
  direct SQL path at all — stop probing. `service_role` also exposes every
  `SECURITY DEFINER` helper in the project, so `GET /rest/v1/` lists RPCs that
  belong to *sibling* apps (`get_users_secure`, `admin_update_user`, …): those
  names are a hint the sibling reads through RPC rather than table grants,
  which makes a blanket table grant destructive to its design — but it is only a
  hint until you read the function bodies. Then hand the user one-statement-per-block
  read-only SQL (`pg_class` + `pg_policies` joined per table) and say plainly it is
  `SELECT`-only.
- **Never test a local-only shortcut, then leave it wired in.** Swapping
  `VITE_SUPABASE_ANON_KEY` to the `service_role` value inside a gitignored
  `.env.local` does make a broken client work instantly (service_role bypasses
  both RLS and grants) and needs zero DB access — but it only fixes *this* machine,
  ships a bypass-everything key to the browser, and leaves production's `401`s
  untouched. Offer it only when the user cannot reach the SQL Editor, back the
  file up first, unset it when done, and never set `VITE_`-prefixed service_role
  in a deployment environment. Prefer the scoped `GRANT` (fixes local *and* prod)
  and say why the shortcut is the worse trade.
- **Anon key ⇒ 401 on the OpenAPI spec and RLS-filtered data.** Reach for the
  service key; if it's absent, scan sibling project env files by ref.
- **When the client routes every RPC through its own `/api/rpc` proxy that holds the
  `service_role` key, DIRECT table reads from the client still go out under the ANON
  key and are RLS-filtered to `[]`.** The two paths look interchangeable in the source
  (same `supabase` object) and only the proxied one is privileged, so a page that works
  for staff and is empty for students is the usual tell. Prove it with one probe pair:
  `GET /rest/v1/<t>?select=*` with the anon key → `200 []`, the same URL with
  `service_role` → rows. Fix by moving that read onto an RPC the role is already
  allowed to call — not by adding a grant, which would open the table to every
  anonymous caller. Check the RPC's parameter list first: one that takes no
  `p_schedule_id`-style argument answers `400` even for a valid viewer.
  **Before writing any new endpoint, check whether a page already fetched the
  value.** A list derived from a table (available divisions, categories, owners)
  is very often already present as a column of an RPC payload the same function
  loads a line earlier — deriving it there is zero endpoints, zero migrations, and
  no new attack surface. Offer the RPC route instead only when the picker must
  show entries that no row carries yet (an item with no users), and say so.
  **Then check the fetch's `error` — an unguarded `const { data } = await rpc(...)`
  renders a failed call as an EMPTY list, which reads as "the data is gone" rather
  than "the session died", so the user reports a data bug and you go hunting in
  the DB.** Any list whose length reaches the UI needs `if (error) toast / empty-state`;
  a panel that legitimately shows nothing and a panel that failed to load must not
  be the same pixels. The same silence hides a 401: nothing throws, nothing logs,
 the grid is just blank.
 **The WRITE path fails even more quietly than the read path, because
 supabase-js RESOLVES with `{ error }` instead of throwing — so an unguarded
 side-effect call looks like a success and can even log one.** A handler shaped
 `await sv.from('t').delete().eq('k', v);` followed by
 `console.log('removed')` never throws, prints the success line, and leaves the
 row in place: the console looks clean while the row persists, so the bug is
 invisible from the app and only a read-back finds it. Never wrap a fallback
 INSIDE `if (error) { ... }` either — the fallback's own failure is just as
 unobservable, the log after it still claims success, and in review the shape
 reads as resilience. Pick ONE path, act on its `error` (log/throw and return
 early), and drop the alternate route rather than keeping it as a safety net.
 When you close a hole of this shape, lock the single-path contract in a test
 whose mock makes the direct-table route THROW — a green suite that merely
 asserts the happy path lets the pattern come back and fail silently in
 production exactly as before.
- **Read the SHAPE of a client error to know which layer failed — the browser's
  `Failed to fetch` is not a server rejection, and a healthy host cannot emit it.**
  A request the server refused arrives as a JSON body (`{"error":"Unauthorized:
  Invalid or expired token"}`) alongside an HTTP status, so `Failed to fetch` means
  no answer ever arrived (offline, DNS, connection reset, or a local dev proxy with
  nothing behind it). Separate the two before debugging: probe the endpoint with a
  deliberately invalid token AND with no token — a live host answers `401` JSON in
  both cases — and only then read the client. **A client wrapper that catches every
  failure and returns `{ error: { message: 'Network error' } }` cannot surface a
  server rejection at all**, so a page built on it shows its own handled message or
  nothing, and the raw `Failed to fetch` in the console belongs to some OTHER
  request on that page (service worker, realtime socket, static asset). Name the
  candidate requests and ask for the failing URL instead of assuming the page's own
  RPC calls are at fault. Pin the environment first too: these repos proxy `/api` to
  a second port in local dev, so a page that calls the proxy looks broken while
  production is fine — establish prod-vs-local before diagnosing the cause.
- **A 200 from an RPC called with the service key does NOT prove the app's path
  works.** The app goes through its own `/api/...` proxy that enforces RBAC; test
  through that, with a real per-role token.
- **Case- AND FORMAT-duplicated dimension values** (`K3` vs `k3`, `Bendahara` vs
  `BENDAHARA`) silently break string equality joins between an access table and
  the user row. Compare distinct values across both tables before blaming logic.
  The same applies to *format* variants of one key: user rows often carry a
  prefixed code (`TE B`, `TSE B`, `S1-C`) while the schedule/class row stores the
  bare letter (`B`, `C`), so a raw `u.class_code = s.class_code` predicate throws
  away legitimate rows with no error (measured: 6 of 300 `group_members` rows
  dropped from a roster for exactly this). Group both tables by the key before
 writing any comparison, and compare on a normalised form in ONE helper shared
 by every predicate — `upper(NULLIF(regexp_replace(code, '^.*[-\s]', ''), ''))`
 — instead of string equality scattered across functions.
 **Normalise for COMPARISON only; never for the value you store or hand back.**
 Building a picker/dropdown from duplicated rows invites a case-folding dedupe,
 but the consumer of that value usually matches it with exact-string equality
 (`division_access.division = user.division`, a `menu_key` join), so a "tidied"
 upper-cased option silently grants nothing: the admin picks `BENDAHARA`, the
 lookup runs with `Bendahara`, and the feature is dead with no error. Dedupe on
 `lower(value)` while keeping the FIRST spelling as the value. Expect the
 duplicated rows to be already dead in the DB — the real ones are whichever
 casing the matching code looks up, so a case-variant row in an access table is
 leftover noise to clean, not a second live entry.
 **Clean it by DELETING the losing rows only — never re-home their menu or child
 rows onto the winning casing.** The two sets usually differ in content, so
 folding them together silently GRANTS access the losing set never had: a
 `Bendahara` set carrying `/manajemen-user` and `/input-nilai` would hand those
 menus to every `BENDAHARA` assistant the moment it is merged. Removing dead rows
 is behaviour-preserving and reportable; adding them is a privilege decision for
 the user, so state the difference and let them re-add through the panel.
- **One table can carry TWO vocabularies of COLUMN NAMES (`full_name`/`username`
  vs legacy `nama`/`nim`), and a row filled in only the legacy pair reads as a
  MISSING USER through any projection that names the canonical columns.** The
  symptom arrives as a UI datum — a roster rendering "Nama tidak ditemukan" for a
  few rows — and the wrong first move is to hunt for orphaned FK rows, because the
  row is fine. The discriminator is to read the SAME row through a SECOND query
  path: a sibling RPC (or `?select=*` with the service key) returned the name and
  NIM for exactly the ids the first one returned `NULL` for, while every other
  column of that same joined row (`class_code`, `shift`) was populated through BOTH
  paths — a NULL name beside a populated column from the same row means the JOIN
  succeeded and the COLUMN is wrong, not the relationship. Prefer two RPCs that
  join the same table over reasoning about the join (they were `get_group_members_
  secure` and `get_all_group_members_secure`, one reading the legacy pair and one
  the canonical).
  Fix in two halves, both needed: backfill the canonical columns from the legacy
  ones (`UPDATE users SET full_name = nama WHERE full_name IS NULL AND nama IS NOT
  NULL`, ditto `username = nim` — this also restores the rows' ability to LOG IN
  when the identity column is the NULL one) and make the reader tolerate both
  spellings (`COALESCE(u.full_name, u.nama)`) so the next import that writes the
  legacy pair does not reopen it. Count the affected rows first and report the
  number — a handful of rows in one table is a data fix, not a schema redesign.
  **Write that migration so ONE file works whether or not the legacy columns exist
  on the target project.** You cannot reference a column that may not exist in DDL
  you also want to run on the schema that lacks it, so gate on
  `information_schema.columns` and assemble the statement with `EXECUTE format(...)`:
  run the backfill only when the legacy column is present, and interpolate the
  projection expressions (`COALESCE(u_s.full_name, u_s.nama)` vs the bare canonical
  column) into the `CREATE OR REPLACE FUNCTION` text. One migration that runs clean
  on both schema shapes beats two variants the user has to choose between — and
  remember the repo copy is often a schema the production DB has already moved past.
- **Prefer Python (urllib/re/json/csv) or Git Bash for shell work on Windows.**
  The default shell may lack common Unix utilities; the curl examples above work
  in Git Bash, and anything looped/parsed is more reliable in Python anyway.
- **A 400 `PGRST200 Could not find a relationship between 'X' and 'Y'` is a
  MISSING FOREIGN KEY, not a permissions problem.** PostgREST resolves an embedded
  resource (`select=...,users(role)`) only when a real FK links the two tables — a
  shared *value* (`active_sessions.nim` matching `users.nim`) is not enough, even
  when every row matches. Confirm there are no orphans first, then hand the user
  the DDL (service_role cannot run it — Step 7.5):
  `ALTER TABLE public.child ADD CONSTRAINT child_parent_fkey FOREIGN KEY (col)
  REFERENCES public.parent(pk) ON DELETE CASCADE;`. Verify by re-running the
  embed query — it must return rows, not merely stop erroring.
- **A 400 is a different layer from a 403.** 403 = the app's RBAC rejected the
  call before the DB was touched. 400 carrying a *database* message ("Akses
  ditolak: Hanya staff...", a constraint/type error) = RBAC admitted the call and
  a **DB helper function** (`is_staff`, `is_admin`, a menu check) or a constraint
  refused it. Fixing the API whitelist alone leaves that second gate intact —
  after deploying an RBAC fix, re-probe and expect the next layer down to surface.
  **The proxy's own whitelist is not the gate.** An RPC the proxy lists for a role
  can still refuse that role inside the function body, and the app reports it as a
  plain 400 in the browser console — the make-or-break move is to call the exact
  RPC with the SERVICE key, once per role, and read which roles return `200`:
  the whitelist lives in `api/**`, the real authorisation lives in the function,
  and only the second one decides. When the call is optional to that role (a
  settings/template fetch, a cosmetic enrichment), the fix is to gate the CLIENT
  call on the role — `if (!isPraktikan) { ... }`, `if (!user || !isStaff) return;`
  — never to widen the function, which would hand the role data the gate exists to
  withhold. Grep the whole client for the offending RPC afterwards, not just the
  page that reported it: a sibling page often holds the same always-400 call and
  has been logging it silently for months.
- **Quantify before you recommend, and re-measure when challenged.** A security
  or impact claim must rest on a count, not a status code or an impression:
  "18 tables exposed" collapsed to 13 once row counts replaced HTTP 200s, and a
  74-table remediation plan was pointless because 73 were already protected. State
  the measured number, scope the fix to it, and when the user pushes back
  ("are you sure?", "how exactly?") re-run the probe rather than restating the
  claim — the push-back is usually right, and an explicit correction lands better
  than a defended error. The same discipline applies in reverse when asked to
  REMOVE something the user fears is exposed: trace the field from its DB column
  through the client mapping to the rendered JSX before agreeing it is on screen.
  A field wired as `phone_number: null` that no render reads is already absent —
  say that plainly instead of letting your diff imply it closed a leak, and delete
  the dead field anyway so it cannot become one the moment the column is populated.
- **Never aim a write probe at a row you have not chosen as disposable — `PATCH` with a body that differs from the stored value mutates production even when the row "should" be blocked.** The blocked case is exactly the one you cannot predict, so pick the target id from a **seeded test account** (Step 6c) and read the row back with `service_role` afterwards; if the probe changed a real row, revert it immediately and say so. Grader/journal tables are the worst offenders: a probe that flipped a real student's `role` looks identical to a probe that did nothing. Probe with read-only
  RPCs; a write RPC (`upsert_*`, `*_create_*`) creates real rows you must then
  hunt down and delete. If you must, capture the returned id, remove the row
  immediately, and tell the user.
- **Locking down a table can break a sibling app — and column-level `REVOKE` is
  NOT a safe shortcut.** Before blocking `anon` from a table, grep *every* deployed
  bundle for direct client access: reads (`.from(t).select(...)`) *and* writes
  (`.insert/.update/.upsert/.delete`). A client using `select("*")` breaks under a
  column-level `REVOKE` too — PostgREST expands `*` to all columns and the whole
  request fails if one is revoked — and a client that writes needs
  `INSERT/UPDATE/DELETE` left granted. **Server code counts too:** a handler
  initialised as `SERVICE_ROLE_KEY || ANON_KEY` writes with the anon key whenever
  the service role is unset, so a "server-only" table can still need its anon grant
  — and you cannot read another host's deployment env to rule that out. Fix the
  client's column list first, then revoke. See `references/rls-exposure-audit.md`.
- **A write-probe's error CODE is the verdict, not its HTTP status — and `204` alone is not evidence either.**
  With `Prefer: return=minimal` (the default in most probe snippets) a `PATCH` returns `204` whether it updated one row or zero, so "grants are fine" and "RLS silently hid the row" are indistinguishable. Send `?select=<a-granted-col>` **and** `Prefer: return=representation`: `200 [{"nim":"…"}]` = row visible and written, `200 []` = RLS filtered it out (grant fine), `403 42501` = privilege missing. That trio is also the cheapest way to prove the row scope of an RLS policy, which a non-returning probe can never show.
  `PATCH`/`DELETE ...?id=eq.-999999` mutates nothing, so the error CODE is the verdict: read it — `42501`/RLS
  = blocked, `23505`/`23503` = RLS admitted the write, but `22P02`/`23502`/`42703`
  /empty-body = the probe is malformed and RLS was never evaluated, so it proves
  nothing. Type and NOT NULL checks run *before* RLS, unique/FK *after* — a sweep
  returning `400` everywhere is a broken probe, not a locked database. See
  `references/rls-exposure-audit.md` §3b.
- **A probe that can fail in TWO different layers proves nothing — before trusting a verdict, check that only your hypothesis could produce that response.** A "is this object a table or a view?" test done through `DELETE ?id=eq.<sentinel>` looks decisive and is not: on an `integer`/`uuid` key the sentinel returns `22P02` (malformed filter), and a *view* whose auto-update rewrite is refused returns `22P02` too — so one code means both "my filter is wrong" and "this object is not updatable", and a view reads as a table. Read the object kind from the OpenAPI spec instead (`definitions.<name>.properties`, its `<pk/>` description) and confirm with `GET /rest/v1/<name>?select=*&limit=1` which of the candidate key columns actually exists. The general rule: when a second, unrelated failure mode emits the same code, the probe is not evidence — say "unmeasured" rather than reporting the ambiguous reading.
- **`204 No Content` on a `DELETE` does NOT mean "0 rows affected" — and for a
  VIEW it does not even mean the write was rewritten.** PostgREST returns `204`
  for any successful `DELETE` unless you send `Prefer: return=representation`, so
  "RLS admits the write" and "a real row was destroyed" are indistinguishable
  from the status. Settle it with a **self-cleaning proof**: seed one throwaway
  row with `service_role`, delete it through the suspect object with the **anon**
  key, then re-read with `service_role` and count the table before and after. Row
  gone = confirmed destructive hole; row present = write path unusable. Reverse it
  afterwards (delete the probe row with `service_role`) and print the count next
  to the baseline you captured. The seed must be a **full copy of an existing
  row** (`select=*&limit=1` + `service_role`, then override only the `id`): a
  hand-written placeholder row fails `23502` NOT NULL, the probe then has nothing
  to delete and reports a false verdict while looking like it passed. See
  `references/rls-exposure-audit.md` §3c.
- **Before `REVOKE anon`, prove the client actually sends a per-user JWT.** The
  step-2 grep tells you which tables the client reads; it does not tell you
  whether the client still HAS an identity to fall back on. Read the Supabase
  client's fetch wrapper in the **live bundle**: if `_currentToken` (or the
  equivalent variable) is never assigned — a `setSupabaseSession()` that is a
  no-op, or a wrapper that was compiled away, both show as zero hits for the
  variable name in the minified JS — then every request already goes out under the
  anon key and closing anon kills the feature for every non-staff account. Fix
  the token injection first, deploy, confirm it on the served bundle, and only
  then revoke. Check the server routes too: a handler that skips the session setter
  under `import.meta.env.SSR` is correct for `/api`, but a *browser* component
  calling the same helper is not.
- **After you repair JWT injection, re-audit — enabling per-user identity can
  EXPOSE a table the anon audit cleared.** An anon-only sweep cannot see a broad
  policy written for `authenticated`: a table whose only policy is `FOR SELECT TO
  authenticated USING (true)` answers `401 42501` to anon and reads as protected,
  then serves every row — answer keys included — as soon as the client sends a real
  token. Re-probe read **and** write for that role before calling the schema clean,
  and check what the role switch does to a long-standing behaviour: an old client
  picks its table by role (`isStaff ? 'lessons' : 'student_lessons'` and the like),
  so a previously WORKING role (students, on the sanitised view) can break the
  moment the identity it keyed on starts arriving.
- **A per-user table with a `USING (true)` policy leaks SILENTLY — the leak looks
  like success.** A query the client scopes to one user comes back full of other
  users' rows, with no error to notice, so it stays live for months
  (`elearning_progress` served every row to the public anon key this way). Probe
  the NEGATIVE with the anon key — `?<userkey>=eq.<a key that cannot exist>` must
  return `[]` — and report that measured negative as the verification. A count of
  rows is not evidence of correct scoping.
- **A handler's metric cannot be "verified" by the app's test runner — lock the
  number in a pure function.** Serverless `api/**` code is outside what the
  frontend suite executes, so a green `bun run test` says nothing about it. Copy
  the computation into a test-local pure function, assert the values agreed with
  the user plus the previously-wrong edge cases (zero progress, saturation), seed
  it with the live row counts, and say plainly in the report which parts are
  measured vs unmeasured. State that the handler itself was not executed.
- **An idempotent fix that DELETES or de-duplicates must be safe to re-run for
real, not just idempotent in shape.** `CREATE OR REPLACE` / `IF NOT EXISTS` /
a `DELETE` that no-ops are safe; a `DELETE a USING b WHERE a.id > b.id` de-dup is
safe too, but a script whose only guard is "the user already ran it" is not —
they will re-run it when the first answer looks wrong. Say which of the statements
are re-runnable and what a second run reports.

**Then check whether the app's own WRITE path can REGENERATE the rows you just
cleaned, and say so.** A panel that deletes-then-reinserts its rows from an
unsorted array recreates duplicates on the next save, so the cleanup is a
data fix and not a bug fix — find the writer (`DELETE FROM t WHERE k = p_k;
INSERT ... SELECT p_k, unnest(p_v)`) and note the missing `DISTINCT`/normalised
`WHERE`. Report it as a follow-up worth doing instead of silently claiming the
symptom cannot return.

**A section that "disappeared" is usually EMPTY, not gone — check whether it is
rendered conditionally before looking for the missing JSX.** A table column or
action cell that vanished is commonly intact in the source and blank because the
permission predicate behind each child (`canEdit(u)`, `role === 'koordinator'`,
`u.id !== currentUser.id`) failed for the rows on screen: a filtered view down to
the caller's own row hides the delete button by design. Read the predicates and
name which of them failed, rather than hunting for a deleted block — and lock the
column with a test that counts the buttons per role, so a later condition change
cannot blank it again without failing CI.

**A column that looks CUT OFF at the right edge is a layout finding, not content loss — check the wrapper before hunting for missing JSX.** The usual shape is a table inside `overflow-x-auto` with percentage (`w-[1%]`) or `min-w-[...]` column widths: inside a scroll container the browser cannot resolve the percentages, so it raises the table's minimum width past the viewport and the rightmost columns (status, action buttons) land outside the visible area — the data is present and reachable by scrolling. Report it as horizontal-scroll/clipped columns with the wrapper and the column classes quoted, never as "column missing". Check the rest of the class list too: an undefined scrollbar utility (`scrollbar-thin` with no plugin in the config and no rule in the CSS) is a silent no-op that leaves the default thick scrollbar eating the last column's width. Tell the user which of the two shapes it is — a shift of table proportions versus a class that never existed.

- **A `setTimeout` scheduled while acting on item N fires after the user has moved
  to item N+1 and mutates the NEW item's state.** The missing piece is the CANCEL,
  not the timer: hold the handle in a `useRef` and clear it on every exit path the
  user controls (next/prev, every button that changes the step) AND whenever the
  item id changes. Symptom arrives as "one item got skipped" and reads as
  navigation logic. Prove it by scripting the flow with the timer still PENDING and
  reading the persisted per-item state (`references/browser-flow-reproduction.md`).
- **Before blaming navigation for a "skipped" item, enumerate the id sequence for
  GAPS — a hole in the data looks exactly like a bug in the logic.** List children
  in the app's own order (`order=sort_order`) and check `sort_order` for NULLs and
  per-module duplicates first; a module holding `l1, l3, l4` has no `l2`, so the
  "jump" is the data.

**When the user has no DDL access, hand over ONE combined read-only query, not a
  list of blocks.** Their SQL Editor renders only the last statement's grid, so a
  numbered set of `SELECT`s silently discards every result but the last — the user
  pastes back one table and you re-ask. Union the probes into a single rowset with
  a first column naming each probe (`'P1-policy' AS probe, <key>, <value>`) and say
  what you expect per probe so the paste-back is unambiguous. Only split when a
  statement genuinely cannot be unioned (different column sets are fine — pad
  them). Replace any postgres error the user hits as a fixable cast: `operator is
  not unique: unknown || "char"` on `relkind` needs `c.relkind::text`, and unioned
  columns need explicit casts because `text || "char"` is ambiguous where
  `concat()` is not.

## References

- `references/schema-extraction.md` — OpenAPI field mapping, count/dump recipes, output layout.
- `references/rbac-sso-debugging.md` — role-vocabulary mismatch, SSO chain, per-role JWT probe, DB role-literal sweep, fix patterns.
- `references/rls-exposure-audit.md` — find tables the anon key can read **and write**; close exposure without breaking client-side readers (`select("*")` makes column-level REVOKE unsafe; probe writes without mutating).
- `references/local-dev-and-db-connection.md` — bring the app up locally and prove it reaches the DB: Vite `configureServer` API mocks, `loadEnv` semantics, probe table/permission verdicts.
- `references/browser-flow-reproduction.md` — a client-interaction bug with no error to read: script the flow in a real browser against the deployed bundle AND localhost, diff the two transcripts. Token minting, clearing persisted state between runs, the CLI's stdin/base64 escaping and CDP timeout limits, assertable state, and a worked timer-outlives-its-item example.
- `references/cross-app-data-consistency.md` — two apps disagree on one number: reproduce both computations from raw rows, denominator/scope mismatch, silent-empty embeds, identity-key inventory, the anon "must be `[]`" negative probe, and locking the agreed numbers in a test.
- `scripts/sweep_role_gates.py` — run this instead of hand-typing the probes: enumerates every `.rpc()` in a bundle and diffs two roles (status **and** payload), sweeps `supabase/migrations/` for role-literal-blind functions, and checks live `is_admin`/`is_staff` per account. Read-only by default.
- `scripts/column_grant_sweep.py` — the per-column privilege matrix. For a chosen token it prints each column's SELECT and UPDATE verdict per table, builds the neutral value from the OpenAPI type so an `integer`/`uuid` column is not misread as denied, and emits the exact scoped `GRANT <op> (cols) ON public.<t>` statement for whatever is missing. Run it instead of hand-rolling the sweep whenever a `42501` hints at a column-level grant, and again after a fix to prove the verdict flipped.
- `scripts/catalog_rls_introspection.sql` — the read-only `pg_catalog`/`information_schema` query set for when you have **no DDL access**: object kind + RLS flags, all policies, table and column grants, view owner/`security_invoker`, function `SECURITY` + body, triggers, and the live role vocabulary. Written one statement per block for the Supabase SQL Editor; hand it to the user verbatim.
