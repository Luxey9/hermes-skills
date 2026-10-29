# Weekly Leaderboard (Asia/Jakarta week, event-based)

Use when a Supabase-backed leaderboard needs a fair weekly competition
without destroying lifetime progress, grades, or achievements.

## Procedure

1. Define the week in the database timezone, never in the browser:
   - Week = Monday 00:00:00 inclusive to next Monday 00:00:00 exclusive
     in `Asia/Jakarta` (configurable per deployment).
   - Filter with `timezone('Asia/Jakarta', completed_at)` /
     `timezone('Asia/Jakarta', played_at)` in Postgres. Client `new Date()`
     differs per laptop and causes boundary disputes.
   - Display the resolved range in the UI (e.g. "13-19 Okt • WIB").
2. Aggregate weekly XP from event tables, not from cumulative `users.xp`:
   - Lessons: `student_progress.completed_at` joined to `lessons.xp_reward`.
     If the progress table lacks per-row `xp_earned`, backfill by documented
     assumption and add the column for future rows.
   - Games: `game_history.played_at` + `xp_earned`.
   - Keep `users.xp` lifetime untouched; expose tabs Mingguan | Total with
     Mingguan as default.
3. Preserve existing partition scoping (kelas/jurusan/shift) in both the
   list query and the rank-count query so rank numbers match displayed rows.
4. Snapshot each closed week into an immutable `weekly_standings` table
   (one row per user per week: `week_start, nim, nama, kelas, shift,
   jurusan, weekly_xp, lesson_xp, bughunt_xp, lessons_completed, rank`).
   Snapshot via scheduled job shortly after week close; never recompute
   history from mutable tables alone.
5. Rank top learners by composite score, not raw XP alone:
   - Example weights: 60% lesson XP + 20% consistency (active days / 7)
     + 20% capped game XP. Weights are configurable per course.
   - Separate repeatable sources (e.g. Bug Hunt) onto their own board or
     cap them, otherwise they become kingmaker for finished learners.
   - Publish the tie-breaker (earlier completion, then more active days)
     in the UI.
6. Prefer non-destructive competition mechanics over destructive resets:
   - Never zero `users.xp` or delete `student_progress` /
     `unlocked_achievements` for a leaderboard season; progress is a
     gradebook, the leaderboard is a scoreboard.
   - For replay/prestige mechanics, use season multipliers or capped
     re-earn instead of deleting proof of learning; if a reset is ever
     offered, archive pre-reset rows first and record `prestige_count`.

## Pitfalls

- Compute week boundaries client-side and identical timestamps land in
  different weeks per device — always convert with `timezone()` in SQL
  because storage is UTC.
- Reconstruct weekly lesson XP from a constant when rewards vary per
  lesson — the history will be imprecise; add `xp_earned` to the progress
  table going forward because the constant assumption silently misranks.
- Count rank and list with different filters and rank numbers drift from
  displayed rows — apply the same week + partition guards to both.
- Let uncapped repeatable XP mix with one-shot lesson XP and finishers
  win every week by farming — split or cap the repeatable source because
  scarcity is what makes the weekly board competitive.
- Adding a transition carry, hard-code the single eligible week label so it
  self-expires, and aggregate the prior week from raw events so it works
  before any snapshot exists. Two variants, and they are NOT
  interchangeable — confirm which one the user wants before coding:
  - *Residue carry* (board would open empty): only zero-XP entries show
    `floor(50% of prior week)` with a visible badge, and sort carry strictly
    BELOW every non-carry entry so real activity always outranks carried
    residue.
  - *Bonus for all* (everyone gets it): every entry shows
    `floor(50% prior week) + this week`, badge it `+50%`, and sort purely by
    the summed XP — carry may then outrank a low-effort active user, which
    is the intended semantics, not a bug.
  Picking the wrong variant is a visible fairness bug: the residue carry
  loses to any activity, the bonus-for-all can hand the top spot to someone
  who did nothing this week.
- Snapshot only on a scheduled job that actually exists — a cron block left
  commented out in the migration, or a snapshot function with no button and
  no caller, means the archive table stays empty forever and the closed
  week's data is destroyed the moment the live window rolls over. Verify
  with a row count per `week_start` after the first week closes, and treat
  the empty table as expected only when no writer has ever run.
