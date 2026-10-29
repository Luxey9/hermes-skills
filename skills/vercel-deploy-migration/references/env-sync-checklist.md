# Env Sync Checklist (Vercel project → project)

## Pull & label
```bash
vercel whoami                      # confirm account
vercel project ls                  # confirm target project exists
cat .vercel/project.json           # confirm what is linked (projectId/orgId)
vercel env pull ./scratch/env-target-check.txt    # target project
vercel env pull ./scratch/env-source-check.txt    # run from a checkout linked to the source project
```
Label files by PROJECT, not by date — comparing 'old vs new file' invites using the wrong one as truth.

Note: `vercel env pull <file>` also writes to `.env.local` when run without an explicit target in some flows — never pull straight over `.env.local` while comparing two projects, or you lose the source of truth.

## Diff (names then values)
```bash
diff <(grep -oE '^[A-Z_]+' env-a.txt | sort -u) <(grep -oE '^[A-Z_]+' env-b.txt | sort -u)
# then per-var value compare (md5 of the line) for shared names
```
Classify each shared var: SAME → skip; DIFFERENT → decide which side is the known-good value (check what the LIVE deployment uses, not which file is newer); only-on-one-side → decide if the target needs it (`APP_URL`, `BACKEND_API_URL` are easy misses — no VITE prefix, only used server-side).

For `VITE_SUPABASE_URL`: the supabase project ref inside the URL IS the database identity. If it differs between projects, anon key and service-role key differ with it — never mix keys from one DB into another's URL.

## Related-var groups: migrate the WHOLE group
Env vars are not independent. These move as a unit or the deploy half-works:

| Group | Vars | Symptom if only some move |
|---|---|---|
| Supabase | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | URL+anon updated but `SUPABASE_JWT_SECRET` left on the old project → login succeeds, every table returns empty (token signed by old secret fails PostgREST verification, client drops it, falls back to anon key, RLS returns 0 rows) |
| Firebase | `VITE_FIREBASE_*`, `FIREBASE_SERVICE_ACCOUNT` | admin SDK initialises against the wrong project |
| Backend routing | `BACKEND_API_URL`, `APP_URL`, `VITE_WEB_UTAMA_URL` | server-side fetch points at a dead host; self-referential links/callbacks point at the old domain |

`SUPABASE_JWT_SECRET` lives at Supabase dashboard → Settings → API → JWT Settings (NOT in `.env.local`, which `vercel env pull` never returns for Sensitive vars). Some codebases auto-detect the right encoding by verifying the anon key with the secret (raw UTF-8 vs base64) and log a CRITICAL error when neither works — that log line is the definitive tell that the secret belongs to a different project.

## Push
```bash
printf '%s\n' "$VALUE" | vercel env add NAME production
vercel env rm NAME production --yes   # required before re-adding an existing name
```
After the batch: `vercel env ls production` and verify every expected name + environment target. Treat 'already been added to all Environments' as success (a prior push won), do not rm-and-retry unless you first confirmed the stored value is wrong via a fresh pull.

## Post-sync
- Deploy preview: `vercel` (not --prod first).
- Verify at runtime: hit the preview URL, confirm the app reads the expected DB (check a record that only exists in the new DB, or grep the built JS bundle for the project ref).
- Only then: domain release → attach → DNS repoint → verify live.

## Sensitive vars and credential probes
`vercel env pull` cannot read Sensitive-typed vars, so a pull is NOT proof of absence — cross-check names with `vercel env ls production` (value shows `Hidden`, type `Sensitive`).

Probe the service instead of parsing the secret:
```bash
# Supabase anon key -> 200 = valid for that project ref
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://<ref>.supabase.co/auth/v1/settings" -H "apikey: $ANON_KEY"
```
`GET /rest/v1/` alone returns 401 even for a correct key — do not use it as a validity test. Decode the JWT payload (`base64` of part 2) to read the `ref` and confirm the key belongs to the URL it is paired with.

Gemini key: `GET "https://generativelanguage.googleapis.com/v1beta/models?key=$KEY"` → 200 valid, 400 invalid (a comma-joined multi-key value will have some keys fail).

## Do not chase escape puzzles
Pulled values for JSON secrets are single-line with `\n` / `\"` escapes plus umbrella quotes; hand-parsing them round-trips badly. Confirm structure (`project_id`, `client_email`, `private_key` present) and that the consuming stack works elsewhere, then move on — the escape layer is not the blocker. Budget: if two parse attempts fail, stop parsing and verify structurally.

## First prod deploy: check upload size
```bash
# list the big local dirs before deploying — anything here will upload unless ignored
for d in node_modules dist build scratch public; do [ -e "$d" ] && echo "$d: $(du -sm $d | cut -f1)MB"; done
```
`Error: Upload aborted` during a large upload means `.vercelignore` is missing or too thin. Vercel CLI reads `.vercelignore`, NOT `.gitignore` — a repo whose git ignore rules look correct can still ship hundreds of MB of local artefacts. Create `.vercelignore` before the first prod deploy and keep runtime asset dirs that the app fetches at runtime out of the ignore list.
