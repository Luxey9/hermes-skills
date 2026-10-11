# Local Dev Run + "Is It Actually Talking to the DB?" (Vite + Supabase)

Use when the ask is "how do I run this locally / connect it to the database" or
a local run loads but every data call fails.

## 1. Resolve env the way the dev server does

- `loadEnv(mode, '.', '')` with an **empty prefix** loads *every* `.env*` key, not
  just `VITE_*` — so `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`,
  `BACKEND_API_URL` are all readable from `vite.config.ts` middleware, while
  client code still only sees `import.meta.env.VITE_*`. Both `.env` and
  `.env.local` are loaded (`.env.local` wins).
- Parse with a small script, never `source`/`. ./.env.local` in bash — values with
  spaces or unquoted characters abort the shell (`line 2: PRIVATE: command not
  found`) and you get a silently empty variable. Strip surrounding quotes, then
  print only `len()` / a prefix, never the value.
- Keys that decide whether the DB link works: `VITE_SUPABASE_URL`,
  `VITE_SUPABASE_ANON_KEY` (client), `SUPABASE_SERVICE_ROLE_KEY` (server-only
  probes and, per Step 7.5, no DDL), `SUPABASE_JWT_SECRET` (token re-signing),
  `BACKEND_API_URL` / `VITE_API_URL`.

## 2. Route table: what the dev server actually serves

Before "testing" an API route locally, look for a custom plugin in
`vite.config.ts` whose `configureServer` installs a middleware that intercepts
`/api/*` — that is the local stand-in for the serverless functions. Routes come
in three flavours, and the differences decide what a local result means:

| Route | Locally | How to confirm |
|---|---|---|
| Mocked in the dev middleware (`/api/login`, `/api/verify`, `/api/receive-token`, `/api/validate-quiz`) | full logic + upstream proxy | `POST` with a bogus identifier → the app's *own* domain error (`{"error":"NIM atau password salah."}`) proves the upstream backend was reached |
| File exists under `api/` but no middleware | `404` locally, works after deploy | `POST` → `404` |
| Prod-only | never local | — |

A `404` on a route that has a real `api/*.ts` file is a **dev-mock gap, not a
broken route**: state it as such instead of reporting the feature as broken. Do
not test login with a placeholder NIM — `/api/login` forwards to the real backend
and only rejects credentials it can verify; a real account is required.

## 3. Prove the DB link in one probe

GET one table per verdict, with the anon key and the service key, and read the
CODE not just the status:

```python
req = Request(f"{URL}/rest/v1/{t}?select=id&limit=1",
              headers={"apikey": K, "Authorization": "Bearer " + K})
```

| Result | Verdict |
|---|---|
| `200` + rows (service key) | URL/ref are correct; the DB is reachable |
| `401 42501 permission denied for table X` + `GRANT` hint | missing table-level GRANT (see SKILL.md pitfalls) |
| `200 []` | GRANT present, RLS filtering the caller |
| `404 PGRST205 ... Perhaps you meant 'Y'` | table renamed in this project; align code to the project |
| `401 Invalid API key` | key belongs to a different project ref (decode the JWT, Step 1) |

Also check the helper functions the policies call, via RPC with the anon key:
`POST /rest/v1/rpc/auth_role` returning a role (not `401 PGRST202`) means the
policy helpers exist, so the remaining gap is grants.

## Pitfalls

- **A local `.env*` value is not proof the deployed app matches it.** Compare the
  two before drawing conclusions from a local run: fetch the served bundle, pull
  the Supabase URL and the inlined JWT, and base64-decode the JWT's payload — a
  matching `ref` claim plus the same `iat`/`exp` proves the SAME project and key,
  so a local failure is a production failure too, not a local-environment
  artifact. Report that equivalence explicitly ("prod kena 401 yang sama") instead
  of letting the user assume prod is healthy; it changes whether the fix is
  "get it running on my machine" or "the app is down".
- **Serverless routes can be healthy while every client call fails.** The
  `/api/*` handlers read the DB with `SUPABASE_SERVICE_ROLE_KEY` (falling back to
  anon), so they answer normally — a login proxy returning its own domain error
  like `{"error":"NIM/email atau password salah."}` proves the upstream backend
  is reachable and says nothing about browser-side grants. Check both layers
  separately and name which one each verdict belongs to: `/api` working =
  config fine; browser `401` on tables = DB grants missing.
- **Local `.env` ≠ the deployed backend.** A dev run talking to a different
  Supabase project than production is normal; confirm the ref before drawing
  conclusions about "the database" (SKILL.md Iron rule 1).
- **A dead debug endpoint is not a bug to fix.** `api/debug-env.ts`-style stubs
  that always return `404 Not Found` are deliberate; say so rather than
  "repairing" them.
- **Don't report a buggy local feature when only the mock is missing.** Classify
  against the route table above first.
