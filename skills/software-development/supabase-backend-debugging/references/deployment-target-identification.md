# Identifying the deployment's real backend

A repo's `.env`, the live URL, and the credential in the running app can each
point somewhere different. Establish which project the app actually reads
*before* probing data or claiming a migration is missing.

## 1. Read the live bundle, not the repo

1. `curl -sL https://<host>` → find the hashed asset (`/assets/index-*.js`) → fetch it.
2. `grep -oE "https://[a-z0-9]+\.supabase\.co"` → the project ref the shipped
   client was built against.
3. Repeat per host. Two hosts serving the same app with different refs = two
   deployments on two databases; the repo `.env` describes neither reliably.
   The operational domain (the one the users/admins actually open) decides which
   project is the target.
4. Grep product strings (app name, hardcoded domain literals) to confirm both
   hosts run the same codebase rather than two separate products.

## 2. Get a read-only credential without asking for secrets

The client bundle ships the anon/publishable key (`sb_publishable_...` or an
`eyJ...` JWT). Extract it and probe REST read-only — never echo the key back.

## 3. Triage probe error codes — each answers a different question

| Response | Means |
|---|---|
| `401 Invalid API key` | key belongs to another project / wrong key type — nothing else is testable yet |
| `42501 permission denied for table` | key is VALID, table and column EXIST; grants/RLS blocked the read |
| `42703 column <t>.<c> does not exist` | schema change was never applied to THIS project |
| `PGRST202 ... Perhaps you meant: fn(a, b, c)` | function exists with a different signature; the message lists the live argument list |
| `PGRST205 relation does not exist` | table absent from this project's schema |

So a column-existence question is settled by `42703` vs `42501`, and a new
function signature is verifiable from the `PGRST202` hint — no service key
needed. A probe that reaches the function's own guard (a `P0001`-style `RAISE`)
proves the new signature landed.

## 4. Diagnose the stored credential without leaking it

Inside the component that holds the key, decode only the JWT payload and log
`role`, `ref`, `exp`:

- `ref` != ref in the configured URL → key and URL come from different projects
  (the usual cause of `401 Invalid API key`).
- `role` != `service_role` (`anon`, or an `sb_publishable_...` pasted where a
  service key was needed) → RLS will silently filter every read.
- Flag pasted whitespace/newlines and a leftover `Bearer ` prefix.

Never log the key; a length plus a 3-character prefix is enough to catch a
truncated paste.

## 5. Apply the change where it is read

Run additive migrations on the project the operational deployment uses. Hitting
a sibling project is usually harmless (added column + defaulted function) but
fixes nothing. If it happens, confirm old callers still work by replaying the
previous argument list and checking you still reach the function's own guard.

## 6. Migrating env to a NEW deployment of the same app

When moving an app to a new hosting project/account (suspend, transfer, fork),
the env snapshot that matches production is `vercel env pull` output
(`.env.local` created by the CLI) — not the repo's hand-written `.env`, which
is often a stale template from a different environment (unfilled `APP_URL="MY_APP_URL"`
placeholders, older API keys). Diff the two before trusting either:

```bash
# which keys differ in NAME ...
diff <(grep -oE '^[A-Z_]+' .env | sort -u) <(grep -oE '^[A-Z_]+' .env.local | sort -u)
# ... and which same-named keys differ in VALUE
while IFS='=' read -r k v; do case "$k" in ''|'#'*) continue;; esac; \
  lv=$(grep -m1 "^$k=" .env.local | cut -d= -f2-); [ "$v" != "$lv" ] && echo "$k: BEDA"; done < .env
```

Rules for the move:

- **Copy values from the pulled/live snapshot, never from the repo `.env`.**
  The pull reflects what production actually runs; the template may carry
  superseded keys (measured: `GEMINI_API_KEY` and `JWT_SECRET` differed between
  the two files, and only one matched the live deployment).
- **Exclude host-generated vars**: `VERCEL_OIDC_TOKEN` (and similar) are
  auto-issued per project — carrying them over breaks the new deployment.
- **A var present in the dashboard but absent from the pull is likely a
  Sensitive one** (lock icon: value unreadable). Flag it `[ISI: source]` in the
  handoff file instead of guessing; `SUPABASE_JWT_SECRET` lives in the Supabase
  dashboard, not in any env file.
- **Write the handoff as placeholders, never as pasted values.** Assembling a
  "ready" env file invites fabricating a key whose value you never actually
  read; generate the checklist with `[ISI: .env.local → line X]` pointers and
  let the values be copied per-line.
- **Single-line JSON secrets must be copied byte-exact** (e.g.
  `FIREBASE_SERVICE_ACCOUNT`): one line with literal `\n` and its surrounding
  quotes, because the server code parses exactly that shape — reformatting it
  breaks the parser that unwraps it.
- **CLI `env add` can report failure while succeeding: verify with `env ls` before
  re-running.** Piping the value in (`input:`/stdin redirect) may fail the local
  process after the CLI has already accepted the variable server-side, so re-running
  the batch gets "has already been added to all Environments" on every name. Treat
  that error as PROOF the variable is present with the intended value path — not a
  failure to retry; a loop that blindly retries a failing push never learns this.
- **After `vercel link`, prove WHICH project you linked before pushing anything.**
  A same-named existing project is silently offered and accepted — you can end up
  on the old (suspended) project, not a fresh one. `vercel env ls` decides it:
  variables you never pushed plus creation dates months old = the existing project,
  and the plan changes (unsuspend/transfer) instead of duplicating env.
- After the new deployment is live, remember the downstream wiring: CORS {
  origins}, SSO callback URLs, Supabase Auth redirect allow-list — any
