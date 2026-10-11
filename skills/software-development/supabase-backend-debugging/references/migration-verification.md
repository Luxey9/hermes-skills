# Verifying that a schema/RPC change actually landed

When a change depends on a migration (new column, new RPC parameter), the live
project is the only source of truth. "I already ran the SQL" is a report, not a
fact — probe before you build on it or tell the user it is live.

## Sequence: migrate → verify → dependents

A schema change is the first link of a chain (schema → UI that writes the new
field → downstream job/report that reads it). Build and ship in that order, and
gate each link on the previous one being verified live:

- Add the column and the matching RPC parameter with a **default**, so existing
  callers keep working while the UI catches up.
- Verify (probes below) **before** shipping the UI change or telling the user the
  feature works. An unverified migration is the one failure the user cannot see
  coming, because every other part looks finished.
- When a downstream job depends on the new field, make it **required** on the
  write path: blocking the save with a visible error beats storing rows the
  downstream job can never place.
- The consumer (cron job, webhook, spreadsheet sync, export) takes its URL and
  key from the project you just verified, and its first **dry-run report is the
  end-to-end check**: unmatched-key counts near zero means right project and
  right mapping; a run that matches nothing usually means the database is empty
  or parallel — not that the mapping is wrong. State which project the numbers
  came from.

## Repo first, user second

The repo already carries most of the schema truth: `supabase/migrations/*.sql`
(search it for the table and the `CREATE OR REPLACE FUNCTION` that writes the
row), the generated `types.ts`, and the client code that builds the payload. Read
those before asking the user to re-describe their own schema or to decide
something the code already answers. Save questions for genuine product forks —
which labels matter, which target the data must reach — not for facts already in
the tree.

## Get a read credential without opening .env

The client bundle already ships everything public: the project URL and the
publishable/anon key (public by design, safe to use and to print in part).

```bash
URL=$(grep -rhoE "https://[a-z0-9]+\.supabase\.co" dist/assets/*.js | head -1)
KEY=$(grep -rhoE "sb_publishable_[A-Za-z0-9_-]+" dist/assets/*.js | head -1)
```

For a Vite app the value comes from `VITE_SUPABASE_*`. **A locally built `dist/`
reflects your local `.env`, NOT what production serves** — hosting env vars
(Vercel/Netlify) are merged in at build time and win. Pull the bundle from the
live domain instead:

```bash
for host in app.example.com legacy.example.com sibling.example.com; do
  asset=$(curl -sL "https://$host" | grep -oE '/assets/[^>" ]+\.js' | head -1)
  printf '%-28s %s\n' "$host" \
    "$(curl -sL "https://$host$asset" | grep -ohE 'https://[a-z0-9]+\.supabase\.co' | sort -u | tr '\n' ' ')"
done
```

One repo is often deployed **twice against two different projects** (an app plus
its sibling, or a legacy domain still serving the same code). Label every host
with its project ref before concluding anything, and cross-check against the ref
the user *thinks* they migrated (`VITE_SUPABASE_PROJECT_ID`) — that is how you
catch a migration run on the wrong project.

To break a tie between two plausible projects, match a record out of the user's
own artifact — a roster row in their spreadsheet, an export, a screenshot —
against the candidates (`/rest/v1/users?select=id&custom_user_id=eq.<id>`) with
the read credential the bundle handed you. A returned row names the project that
holds the operational data; a permission-denied answer (`42501`) is
uninformative, so do not read it as "record absent". Say which record you
matched, so the claim is checkable rather than asserted. Evidence still yields to
the owner: when they name the project they actually operate, take it, and
immediately restate what it changes — which deployment must carry the UI change,
and whose credentials the integration, cron, or webhook must use.

When the owner then names the project they actually operate, that call wins over
your data-hunting: state the evidence once, take their project, and immediately
restate the two things it changes — which deployment has to carry the UI change,
and whose credentials the integration/webhook must use.

## Probe 1 — new column

```bash
curl -s -w "\nhttp=%{http_code}\n" \
  "$URL/rest/v1/<table>?select=<newcol>&limit=1" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
```

- `200 []` → the column exists (RLS may still hide rows).
- `401 {"code":"42501","message":"permission denied for table <t>"}` → the column
  **exists as well**: Postgres resolved the name and failed at the grant check. A
  project whose anon role holds no table grants answers every probe this way, so
  "no `42703`" is the signal — never read `401` as "migration missing".
- `400 {"code":"42703","message":"column <table>.<col> does not exist"}` → **not applied**.
  `42703` is raised by Postgres when planning the query, so this is not a stale
  PostgREST schema cache — the column genuinely is not there. Do not "fix" it by
  reloading the cache.

## Probe 2 — new / changed RPC signature

```bash
curl -s -X POST "$URL/rest/v1/rpc/<fn>" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_caller_id":0,"p_target_user_id":1,"p_type":"scan","<new_param>":"x"}'
```

- `404 {"code":"PGRST202", ... "Perhaps you meant to call <fn>(<params>)"}` → the
  parameter set does not match the deployed function. **The hint enumerates the
  live signature** — read your ground truth straight out of it, no dashboard
  access needed.
- An error from *inside* the function (permission check, validation) means the
  signature exists and the call reached the body — that is the pass signal.

**Keep the probe non-destructive.** Pick arguments that fail an access check
before any write: for a function with a `p_type`-gated check, use the type that
requires `caller == target` while passing different ids. Never probe a write path
with values that could pass validation — an introspection call must not create a
row.

## Signature-change mechanics that break callers

- PostgREST resolves RPCs by the **exact named-parameter set**. Add a parameter
  and old callers keep working only if the value has a default; a call with an
  unknown or missing name fails as `PGRST202` "no matches", not as a type error.
- When you replace a function, drop every old overload on purpose (loop
  `pg_proc`/`pg_namespace` and `DROP FUNCTION <oid::regprocedure>`) before
  creating the new one, then re-`GRANT EXECUTE` — recreating loses grants.
- After a drop/recreate, **re-probe with the OLD parameter set** (new param
  omitted). A sibling deployment onto the same database still calls the old
  shape; a body-level pass signal proves nothing broke, which is far cheaper
  than auditing every caller or rolling back.
- `BEGIN; ... COMMIT;` makes a migration all-or-nothing: one error anywhere
  leaves the database untouched. If the editor executed only a selection, the
  whole thing silently did not run. Ask for the editor's error text instead of
  re-running blind.
- The REST root spec (`GET /rest/v1/` with the OpenAPI accept header) can answer
  `401` with the very key that returns `200` on table and `/rpc/` paths. Probe
  those paths directly; do not conclude the key is wrong.
