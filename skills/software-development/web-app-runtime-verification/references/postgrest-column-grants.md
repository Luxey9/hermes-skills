# PostgREST column grants and view-stripped fields

Two failures that both look like "permissions are wrong" but have different root
causes and different fixes. Check which one you have before changing any grant.

## Symptom 1: `42501 permission denied for table <name>`

Cause: the statement names a column the role has no grant on. PostgREST rejects
the **whole statement**; it never partially applies. The error names the table,
not the column, so it reads as a blanket problem.

Reproduce precisely:

```bash
# select a group of columns: 200 means all of them are granted
curl -s -o /dev/null -w '%{http_code}\n' \
  "$URL/rest/v1/<table>?select=col_a,col_b&limit=1" \
  -H "apikey: $KEY" -H "Authorization: Bearer $TOKEN"
```

Bisect by adding or removing one column at a time until the status flips. Then:

```sql
GRANT SELECT (col) ON public.<table> TO authenticated;
GRANT UPDATE (col) ON public.<table> TO authenticated;   -- if PATCH needs it too
```

Grant per column, never `GRANT ALL` — widening the table is exactly how a locked
down schema gets reopened.

Notes:

- `SELECT` and `UPDATE` grants are independent. A column readable but not
  writable is the normal state and produces a *different* failure than a column
  readable-but-not-selectable.
- Granting write access to a privileged column (role, flags, quotas) hands every
  caller the ability to escalate. Pair the grant with a trigger that rejects the
  escalation, and re-verify the trigger afterwards.
- Adding a column to a client `select=` list is a deploy-order hazard: the client
  and the grant must land together, or every query 42501s.

## Symptom 2: the same screen shows different *values* per role

Cause: staff read the base table; everyone else reads a **view** that deliberately
drops sensitive fields (answer keys, solutions, internal notes). Access control
is working correctly. The dropped field arrives as `undefined`, and any
client-side fallback silently turns it into a valid-looking value:

```js
// field absent from the view -> undefined
correctAnswer: typeof raw.correctAnswer === 'number' ? raw.correctAnswer : 0
```

Every submission is then graded against option `0` — indistinguishable from a
real answer key. The symptom is "grading is wrong for one role only", which reads
as a scoring bug, not a permissions bug.

Rules:

- Never fall back to a numeric or sentinel default for a field a view may strip.
  Use `undefined` and branch on it, or delegate the decision to a server endpoint.
- Check a guard by what it *rejects*. `!== -1` lets a falsy default through;
  guard with `>= 0` on a value you have confirmed is a real number.
- Found it once, grep the other consumers. Sibling components usually carry the
  identical fallback.
- Do not "fix" this by adding the field to the view. That ships the secret to
  every client; prefer server-side validation.

## Distinguishing the two

Ask: does the failing role get an *error*, or a *wrong answer*?

| Observation | Cause | Fix |
|---|---|---|
| `42501` / 403 with a hint | missing column grant | `GRANT <verb> (col)` |
| 200 response, wrong value | field stripped by the view, bad fallback | change the client default; validate server-side |
