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
