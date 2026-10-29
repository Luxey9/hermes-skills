---
name: vercel-deploy-migration
description: Use when moving a Vercel deploy or env to another account.
category: software-development
---

# Vercel Deploy Migration

## When to Use
- Moving/restoring a Vercel project under a different account or team, or picking up a repo whose deploy lives on a suspended account.
- Syncing env vars between Vercel projects, or reattaching a custom domain to a new project.

## Diagnose before you migrate

Read every env var's AGE before trusting a project's config:
```bash
vercel env ls production
```
Timestamps are the cheapest staleness signal. Vars within minutes of each other plus a few strangers from months ago = a partial migration someone stopped halfway. Treat any age skew inside a related group (DB url + keys + signing secret) as a bug to fix before deploying.

Do the cheap reachability pass FIRST — it can cancel the whole migration:
```bash
for d in <domain1> <domain2>; do curl -s -o /dev/null -w "$d: %{http_code}\n" https://$d/; done
curl -s https://<backend-host>/api/health
nslookup -type=NS <zone>; nslookup <each-subdomain>
```
- A Vercel project being suspended freezes only ITS deployments/domains. If the subdomains resolve to a VPS/hosting IP (not Vercel) and return 200, traffic never went through the suspended project — nothing is user-facing broken, and the migration is optional/hardening, not a rescue.
- If DNS nameservers are external (not Vercel DNS), domain moves are a record repoint at the provider — no need to wait for the old project to release the domain first.

Only proceed to the workflow below once you know something is actually down or control must change hands.

Context this user runs: multiple Vercel accounts (personal + an org lab account), sibling frontends sharing one DNS zone (cloudhost.id nameservers, backend on a separate VPS). A suspended Vercel project freezes its domain but NOT services on other hosts (VPS backend/DB keep serving) — check what actually broke before planning a rescue.

## Always-on rules

- Never trust an existing project's env vars by age or name — `vercel env pull` to a scratch file and diff per-var against the known-good source before any deploy. Stale `VITE_*` vars point at an OLD Supabase project silently: the deploy 'works' but serves a dead database.
- Frontend env vars are baked at build time. Updating a var in the dashboard does nothing until the next deploy; never claim fixed-env until a fresh deploy picked it up.
- Prove which project a local link points at before pulling/pushing: read `.vercel/project.json` (projectId + orgId) and `vercel whoami`. A `vercel link` can silently bind to an existing same-named project under a different team.
- `vercel env pull <file>` takes exactly one argument (no environment argument in CLI 59); wrong arg count fails the pull but may still overwrite — re-verify the file after any pull error.
- `vercel env pull` SKIPS Sensitive-typed vars (they show as `Hidden` in `vercel env ls`). A var 'missing' from the pull is usually just sensitive, not absent — confirm against `vercel env ls` before re-adding it.
- Verify a credential by PROBING its service, not by parsing it. Supabase anon key: `curl .../auth/v1/settings -H "apikey: $KEY"` → 200 means valid; a bare `GET /rest/v1/` returns 401 even for a valid key (PostgREST needs a table + RLS), so never judge a key by that. Gemini: `GET https://generativelanguage.googleapis.com/v1beta/models?key=$KEY` → 200 valid.
- Do NOT chase nested-escape puzzles in pulled env files. `vercel env pull` writes JSON values (e.g. `FIREBASE_SERVICE_ACCOUNT`) single-line with `\n` + `\"` escapes and surrounding quotes; a naive `json.loads` on the manually-stripped body fails on the outer quotes. The round-trip through Vercel is what matters: verify the var is structurally complete (contains `private_key`, `project_id`, `client_email`) and that the stack that consumes it already works elsewhere. Parsing it locally is not the gate.
- Test on the preview URL (`<proj>-<hash>-<team>.vercel.app`) end-to-end before touching DNS or domains; curl the health endpoint of every dependency (`/api/health`) first.
- Add a `.vercelignore` BEFORE the first prod deploy. Vercel CLI uploads everything not matched by `.vercelignore` — it does NOT read `.gitignore`. A repo with local build/debug artefacts (node_modules, browser profile dumps, scratch dirs, screenshots) uploads them all and dies with `Error: Upload aborted` / `An unexpected error occurred!` partway through the upload. Ignore at least: `node_modules/`, `dist/`, `build/`, `scratch/`, `.env*`, any `*-profile*/` dump dirs, debug scripts, and `*.log`. Do NOT ignore runtime asset dirs the app fetches (e.g. a WASM `public/` payload) — check sizes before adding a blanket rule.
- A PARTIAL env update is the most dangerous state. When migrating to a different backend/DB, every var in the auth chain must move together: the DB URL, the anon/service keys, AND the JWT signing secret (`SUPABASE_JWT_SECRET` or equivalent). Updating the URL+anon key while the signing secret still belongs to the OLD backend produces the silent symptom login-succeeds-data-empty: the app signs tokens with one key and the new backend verifies with another, the token is rejected, the client falls back to the anon key, RLS returns zero rows. `vercel env ls` timestamps expose this instantly — vars updated minutes ago next to one still showing 139d ago is a partial migration, not a finished one.

## Workflow

1. Map the blast radius: curl every domain + backend health endpoint. A 200 on the live site means nothing is user-facing broken; a suspended project only blocks ITS OWN deployments/domains.
2. Identify target account: `vercel whoami`, `vercel project ls`. Link the repo: `vercel link` (or reuse `.vercel/repo.json` after inspecting it).
3. Export source env: `vercel env pull <file>` from the known-good project, once per source, into files you can diff (never pull straight over `.env.local` when comparing two projects).
4. Diff per-var (name + value) between source and target pulls. Only re-add vars that differ; `VITE_FIREBASE_*` blocks often stay valid across migrations.
5. Push changed vars: `vercel env rm <NAME> production --yes` then `vercel env add <NAME> production` (value via stdin). See pitfalls.
6. Deploy, test preview URL end-to-end (SSO login, the flows that read the DB).
7. Domain last: the domain must be released from the old project/account before it can be attached to the new one. For DNS on an external provider (not Vercel DNS), repoint the record (CNAME `cname.vercel-dns.com` or A `76.76.21.21`) at the provider, then attach the domain in the target project.
8. Never re-add `VERCEL_OIDC_TOKEN` — auto-generated per project/deployment.

## Env push pitfalls

- `vercel env add` can succeed server-side while your wrapper reports failure (output pipe breaks before CLI prints). After any batch push, ALWAYS verify with `vercel env ls production` instead of trusting per-var OK/ERR lines; 'Error: The variable ... has already been added' means the earlier attempt won.
- Multi-line values (Firebase service-account JSON): the pulled `.env` encodes them as ONE line with literal `\n` and surrounding quotes — copy that exact single-line form back; multi-line paste breaks the parser that reads it.
- Batch-push via a small Node/bash script reading the pulled env file and feeding stdin; keep the script in the repo's scratch dir, idempotent (skip/accept 'already added').

see references/env-sync-checklist.md for the diff/push recipe.
