# Bounded Voluntary Prestige Reset (anti-farming replay)

Use when a Supabase-backed course lets finished learners voluntarily reset
progress for a multiplier, without letting easy-lesson farming, XP injection,
or gradebook destruction slip through.

## Procedure

1. Gate eligibility on full completion first, never on cooldown alone:
   - Require every level fully completed (e.g. 6/6 levels, all lessons done)
     before the reset button enables — a single full-completion rule kills
     all low-level farming cheaper than any cooldown tuning.
   - Add cooldown between resets (e.g. 14 days) so a Monday snapshot cannot
     be followed by a Friday re-reset for the same weekly board.
   - Add a per-semester quota (e.g. max 2, academic semester Ganjil 1 Aug-31 Jan /
     Genap 1 Feb-31 Jul in Asia/Jakarta, no date gaps) counted from an immutable
     history table, never from client state. January belongs to the Ganjil that
     started the previous August; compute y/m in the deployment timezone, not UTC.
   - Load the curriculum the same way the app does (DB tables first,
     static fallback when empty) so eligibility and the app never disagree
     on what "complete" means.
2. Keep the multiplier non-stacking, capped, and lesson-only:
   - Take-max, never accumulate: `final = min(cap, max(old, new))` — stacking
     rewards repeated resets and must be impossible by construction.
   - Cap server-side too (e.g. x1.50) as a SINGLE multiplier for full completion
     (e.g. Master x1.50 for 6/6); do not advertise partial tiers (1-2 levels ->
     x1.0, 3 -> x1.10, ...) when the gate requires full completion, because those
     tiers are unreachable and the UI shows a reward the user can never claim.
     Use prestige_count for a cosmetic badge (Prestige-1/2), never for stacking.
   - Multiply lesson XP at exactly one choke point (e.g.
     `applyPrestigeMult(base, mult)` called only from the lesson-completion
     path); repeatable sources (games, Bug Hunt) must never pass through it,
     otherwise infinite sources compound every week.
   - Keep the weekly board on base XP sterile of multipliers; the lifetime
     board may show effective XP plus a tier badge.
3. Rewrite the server XP guard to understand the multiplier:
   - Old shape `NEW.xp > lesson_sum + game_sum → reject` will reject every
     multiplied update, so replace with
     `allowed = floor(lesson_base * mult) + game_sum` with the mult clamped
     to `[1.00, cap]` inside the trigger itself.
   - Create the prestige columns before the new trigger, or every XP update
     fails until the migration ordering is fixed.
4. Archive before deleting, and keep the gradebook readable:
   - Copy active progress rows to `progress_archive(nim, lesson_id,
     completed_at, prestige_no)` and snapshot `users(xp, level)` to
     `prestige_history(nim, prestige_no, ...)` before any DELETE — progress
     is proof of learning and the rekap must read union(active, archive).
   - Never delete achievements silently; if re-testing requires clearing
     them, the tier/count in history must preserve the identity.
   - Upsert the archive on `(nim, lesson_id, prestige_no)` so retries are
     idempotent.
5. Propagate prestige fields end-to-end like any partition dimension:
   - Columns `prestige_tier / prestige_mult / prestige_count /
     last_prestige_at` on `users`; include them in the session `select`, the
     store type, the login mapping, and the realtime `UPDATE` handler, or the
     client silently falls back to x1.0.
6. Make the UI state the rule, not just the button:
   - Show eligibility reason, completion fraction, quota used with the current
     semester label (e.g. Ganjil Agu-Jan), and cooldown remaining; disabled
     buttons must explain why. Never display a tier/mult as earned while
     ineligible — state that x1.50 activates only after full completion.
   - Require explicit double confirmation stating XP returns to zero,
     progress is archived, and the weekly board stays base.
   - Show the tier as a badge (e.g. `Master x1.50`), never as rank digits.
7. Execute the reset in one server transaction, and guard the prestige columns:
   - Move archive + history insert + progress delete + users update into a
     single SECURITY DEFINER RPC (e.g. do_prestige_reset) with FOR UPDATE on
     the user row, because 4 separate client calls leave permanent half-states
     when one fails mid-sequence.
   - Re-validate full completion, cooldown, and semester quota inside the RPC;
     treat the client eligibility check as a hint, never the decision.
   - Block direct self-grant of prestige_mult/tier/count with a BEFORE UPDATE
     guard trigger (non-staff changes rejected) plus column REVOKE, because an
     XP trigger that only clamps to [1.00, cap] lets any client claim x1.50
     without ever completing 6/6.

## Pitfalls

- Offer reset without a full-completion gate and learners farm the easiest
  memorized level on repeat — the gate must be total completion, because
  partial gates are replayed at minimal effort.
- Stack multipliers across resets and each cycle widens the gap
  permanently — take-max bounds the advantage by construction.
- Route game/Bug-Hunt XP through the multiplier and the only infinite
  source compounds weekly into an uncatchable kingmaker — keep repeatable
  XP on base always.
- Count multipliers into the weekly snapshot and reset-timing (reset right
  after snapshot, farm with mult) decides the week — weekly must aggregate
  base only.
- DELETE progress without archiving and the gradebook, audit trail, and
  weekly reconstruction lose the evidence — archive-then-delete, because
  restores from text audit logs are not restores.
- Deploy the new trigger before the prestige columns exist and all XP
  updates reject — order migrations columns-first, trigger-second.
- Run archive/history/delete/update as separate client calls and any mid-sequence
  failure leaves history without deletion or deletion without history — use one
  atomic RPC, because partial prestige states are not repairable from the client.
- Clamp prestige_mult in the XP trigger without checking history and any client
  can self-grant the cap without completing anything — add a guard trigger on
  the prestige columns, because the clamp alone is not authorization.
