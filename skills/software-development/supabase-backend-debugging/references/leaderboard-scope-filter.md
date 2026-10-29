# Leaderboard Scope Filter (partition dimension)

Use when a Supabase-backed leaderboard/rank view must be scoped by an extra
partition key (shift, kelas, jurusan, cohort) and that key already exists in
the `users` table but leaks across partitions in the UI.

## Procedure

1. Confirm the column exists in `users` and is readable under the current
   SELECT RLS policy. If the policy restricts columns, fix RLS first.
2. Propagate the dimension end-to-end before touching queries:
   - Every token-issuing endpoint that signs the Supabase JWT must carry it
     (`/api/login`, `/api/verify`, `/api/receive-token`, plus any dev-login
     shim in `vite.config.ts`).
   - Extend the client `TokenPayload` type and the fallback JWT decode path
     so old/new tokens both parse.
   - Extend the client `UserProfile` store type.
   - Extend the session provider: include the column in `select`, set it on
     profile insert, sync it on login when the token carries non-null, and
     carry it in the realtime `UPDATE` handler.
3. Extend the leaderboard service together, never piecemeal:
   - `getLeaderboard(limit, ...dims)` — add `.eq(dim, value)` only when the
     value is non-null/non-empty; add the column to `select`; map it into
     the returned profile.
   - `getUserRank(xp, ...dims)` — apply the SAME `.eq` guards so rank and
     list agree.
   - `getLeaderboardFilters()` — return distinct values for the new dim so
     staff dropdowns can populate.
4. Scope the UI:
   - Student view: auto-scope to the logged-in user's own dimension values
     (kelas + jurusan + shift). Never leave the new dim unfiltered for
     students.
   - Staff view: optional dropdown (`Semua X` = unfiltered), wired into the
     same service args plus reset logic and `hasActiveFilter`.
   - Show the active scope in the subtitle so leaks are visible immediately.
5. Verify: `tsc --noEmit` (only your touched files must be clean) and a full
   production build.

## Pitfalls

- Filter the list without filtering the rank (or vice versa) and rank numbers
  drift from the displayed rows — always change both functions in one edit.
- Normalize the dimension to `string | null` at every boundary (`String(v)`,
  empty string becomes `null`) because the DB may store int and the token
  may store string; mismatched types silently match zero rows in PostgREST.
- Never overwrite a stored non-null dimension with a null token value — only
  sync when the incoming token value is non-null, otherwise old sessions and
  old tokens wipe good data back to null.
- Adding a service param without updating every caller leaves one path
  unscoped — grep for all callers of `getLeaderboard`/`getUserRank`/
  `getLeaderboardFilters` and update them in the same pass.
- Verify the dimension's data distribution, not just the code path — run
  `select <dim>, count(*) from users ... group by <dim>` before claiming
  the filter works, because correct `.eq()` code over an all-NULL column
  silently filters nothing and every partition shows the same rows.
