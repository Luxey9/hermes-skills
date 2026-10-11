# Two Apps, One Metric — Cross-App Data Consistency

When app A's serverless handler recomputes a number that app B displays, a
disagreement is almost never "the handler is broken". Walk the four causes in
this order and you will land on it in a few probes instead of reading both
codebases.

## 0. Prove both sides share ONE Supabase project before anything else

Every later step assumes the handler and the displaying app read the same
database. Verify it first, because a wrong project makes the other four causes
unfindable:

- Fetch the platform's **env resolver, not just the hand-written fallbacks**:
  `rg -n "process\.env\.[A-Z_]+ *\|\||process\.env\.[A-Z_]+ *\?\?" api/` then open
  each file's top. A hardcoded DB URL buried behind `|| fallback` silently
  overrides every env var the operator sets, and the failure surfaces as wrong
  NUMBERS rather than an error.
- A **constant denominator across users** (identical `total_lessons` for the best
  and worst account) means the count is not coming from the data you can see —
  stop comparing formulas and go find the other DB.
- Same trick for the write side: call the handler once and check which project's
  table actually gained a row. Reconciling existing rows is wasted work while the
  writer targets a different project than the readers.
- Confirm both hosts point at one ref by reading each deployed bundle
  (Step 1) — two apps of one product can disagree while each looks self-consistent.

Fix the code so the URL is required (fail loudly when unset) rather than leaving a
fallback that points at a retired project; an operator cannot audit a default they
did not write.

## 1. Replicate BOTH computations from raw rows first

Do not read the two code paths and compare them. Pull the raw source rows and
compute each side's number in one throwaway script, printing numerator,
denominator and ratio for the SAME user:

```python
# per app, from raw rows only
rows = q(E_BASE, "/rest/v1/student_progress?select=nim,lesson_id,completed", E_KEY)
done = [r["lesson_id"] for r in rows if r["completed"] and r["nim"] == NIM]
print(len(done))                      # numerator
# denominator per app's own rule (see 2)
```

A mismatch then points at ONE of the four causes below, and the printed numbers
say which. Reporting the pair (e.g. `20/32 = 62.5%` vs `19/85 = 23.5%`) to the
user before changing anything also gets their intent confirmed in one round trip.

## 2. Denominator/scope mismatch is the most common cause

Two apps rarely disagree by accident on the numerator — they disagree because
they divide by different things. Read the *displaying* app's formula, not the
one you suspect:

```ts
// app B's own screen
const total = curriculum.reduce((acc, level, i) =>
  acc + (isLocked(level, i) ? 0 : lessonsOf(level).length), 0);   // open levels only
```

Rules that gate the denominator (level locks, feature flags, per-user
overrides, `access_mode`) must be reimplemented in the handler — the handler
has no UI to consult. Reimplement them from the same columns the UI reads, and
keep the numerator's scope identical to the denominator's (counting completions
in a locked level while dividing by open lessons is a second, quieter bug).

## 3. Arithmetic: recompute by hand before blaming data

Scaling constants and clamping hide double-multiplies: `x/total * 105` followed
by `* 100` reports percent-of-percent and saturates early. When a percentage
looks plausible-but-off (25.6 vs 24.4), do the division yourself — a factor of
1.05 with `Math.min(100, …)` is the tell.

## 4. Data path: assert the join actually returns rows

A nested embed can succeed and be useless. `levels?select=*,modules(*,lessons(*))`
returned **0 lessons** because the child table had `module_id` but no `level_id` —
PostgREST happily nests an empty array and every loop over it totals zero, so the
feature "works" and reports 0 forever.

- `select=*&limit=1` on the child table to see its ACTUAL columns; then pick the
  two-step join (`modules.level_id`) or add the missing FK.
- After any nested embed, assert the leaf count is non-zero for at least one
  parent. Zero leaves with non-zero parents = silent no-op, not an empty DB.
- A stale aggregate table is the same failure shape: confirm it has rows before
  trusting it as a source. An app-side "sync" whose RPC is gated to a higher role
  than the caller no-ops with no error.

## 5. Identity mismatch: enumerate EVERY join key, not just `users.role`

Two apps sharing one user base can disagree about which column IS the identity:

| table | logical user key |
|---|---|
| `users` (app A) | `status`/`nim` (sometimes neither — a username in the `nim` column) |
| `users` (app B) | `nim`, plus `username` as a distinct column |
| `<events>` | `nim` — may be empty |
| `<sessions>` | `nim` — populated |
| `<progress>` | `nim` |
| JWT payload | `nim` — can be null even for a fully logged-in user |

Recipe: for ONE known user, probe each candidate key in each table and print what
comes back. A key that resolves in one table and not the other is the bug.

A `null` in the token makes the server fall back to another field
(`payload.nim || payload.username`), and the row it writes is then keyed by a
username while every reader looks up the real id — the data looks present and is
never found. Check which fallback the handler uses and whether it can produce a
key no other table has.

The fallback rule generalises to every column in the identity chain — name AND
key: when the naming convention is documented but unenforced, individual rows
violate it (`nim: 'Faqod'` next to a `username: 'Faqod'`, in a table where every
other `nim` is a student number). Before writing a value into a shared column,
check whether the target is indexed, `NOT NULL` or `UNIQUE` — inserting a second
row for a key the other app looks up with `maybeSingle()` makes THAT lookup error,
and a provider that treats "error" as "no profile" then **recreates the user
empty** (`xp: 0`, no overrides → locks re-apply). One bad insert reads as "their
progress was reset" three layers away.

## 6. A per-user table with `USING (true)` leaks silently — probe the negative

A policy `FOR SELECT TO anon USING (true)` returns rows for EVERY user on a
query the client scopes to one user, so the leak is indistinguishable from
success. Probe the negative explicitly with the anon key:

```bash
# must be [] — a non-empty result is a cross-user read leak
curl -s "$URL/rest/v1/<t>?select=<cols>&nim=eq.999900999" -H "apikey: $ANON"
```

The same probe makes a good regression check after any RLS change; note it in the
report as a measured negative result.

## 7. Lock the agreed numbers in a pure-function test

Serverless `api/**` handlers are not executed by the app's own test runner
(vitest picks up `src/**`), so "verified" has to come from somewhere else. Copy
the handler's computation into a pure function in a test file and assert the
numbers you agreed with the user, plus the two edge cases that were wrong before
(zero progress, and the saturation point). Seed it with the REAL row counts from
the live DB so a future count change fails loudly instead of drifting.

## 8. Cleaning existing rows

**Before cleaning rows, walk the code path that regenerates them.** Two cases
want opposite actions: if that path runs on every page load, leave the rows alone
and fix the path (you would be hand-writing data it overwrites anyway); if it
writes to the WRONG project, no row-cleaning in the right project can ever be
visible and the cleaning is premature.

Recompute each stored row from the other app's DB rather than hand-editing, and
skip (report, do not invent) any row whose key does not exist over there:

- `PATCH` with `Prefer: return=representation` and read the response back — a
  silent `204` cannot tell "updated" from "matched nothing".
- Recompute with a FRESH read of the override/lock columns after changing them;
  a snapshot taken before your own edit silently produces the old number.
- Report the skipped keys by name; four unresolvable rows are a finding, not a
  gap to fill with a plausible guess.
- A row whose key turns out to be a USERNAME (see 5) is not skipped — re-point it
  to the real id so the two apps finally agree on identity, and recompute its
  numbers afterwards. A row left keyed by username stays invisible to the other
  app's readers forever, so "cleaned" would be a lie.
- Print the row count before and after the sweep. "12 of 16 recomputed, 4 reported
  as absent" is a verifiable statement; "progress fixed" is not.
