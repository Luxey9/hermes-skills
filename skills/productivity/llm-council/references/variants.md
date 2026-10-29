# Council variants

The default council is five lens-advisors, one review round, one chairman. Three knobs worth
turning when the default doesn't fit. All of them still belong to the same skill — do not
spawn a second skill for a variant.

## 1. Cheap path — no delegation

If `delegate_task` is unavailable (or the user asks for "just a quick council"), you can
simulate the council in-session: write each advisor's take sequentially as explicitly
separated, labeled sections, then the reviews, then the verdict. Steps, anonymization, and
verdict structure are identical.

Caveat to state to the user: sequential in-session passes are *not* independent — the later
advisors see (implicitly) the earlier ones and anchoring creeps in. The peer review is also
degraded when the reviewer wrote one of the five. Use this for low-stakes questions only; for
a real decision, spawn the children.

## 2. Bigger council — 8 or 12 advisors

When the decision is large enough to justify it, raise the roster with lenses that add a new
tension rather than duplicating one. Candidates:

- **The Regulator** — what rules, compliance, or platform policy does this touch, and what is
  the cost of being wrong about them?
- **The Historian** — has this been tried before (by you or the field)? What happened?
- **The Customer's Customer** — the person downstream of your user, if this is a B2B decision.
- **The Operator at Scale** — what breaks when this goes from 10 to 10,000 units/users?
- **The Devil's Accountant** — the actual numbers: unit economics, cash, time-to-payback.

Keep it to lenses that fight the existing five (the Contrarian already covers "what fails" —
do not add a second pessimist, add a different axis). Each new advisor is one more entry in the
same single `delegate_task` `tasks` array, and each new advisor is one more reviewer in the
review call, so the concurrency cap (`delegation.max_concurrent_children`, default 10) bounds
the batch: 8 advisors + 8 reviewers means two batches of 8, which needs the cap raised to ≥ 8.
Verify the cap first — `hermes config get delegation.max_concurrent_children`, and see the
`hermes-agent` skill's `references/delegate-task-concurrency-diagnosis.md`.

## 3. Multi-round debate

Default is one review round. For a genuinely contested decision, add a second reviewer round:
give each advisor the *disagreements* surfaced in round one (not the full transcript) and ask
them to defend, update, or concede. The chairman then synthesizes both rounds. Cost: doubles
the child count again — run it only when the user says the first verdict wasn't decisive
enough, or on questions with irreversible consequences.

## 4. Domain presets (framing only)

Some councils want the framing pre-loaded. These are prompt prefixes, not new advisors:

- `council this — technical:` include the codebase constraints (stack, scale, deadline) in the
  framed question; make the Executor's "Monday morning" concrete (which file, which PR).
- `council this — hiring:` the Outsider becomes a strong performer reading the JD for the
  first time; the Executor owns "what does week one look like."
- `council this — pricing:` the Devil's Accountant lens from variant 2 is worth adding; make
  the Contrarian cite actual comparables, not vibes.
- `council this — writing/copy:` run the council on the *copy*, not the strategy; give every
  advisor the target reader as the Outsider.

## Anti-patterns

- **A second council on the same question without an update.** Re-run only when the inputs
  changed; otherwise read the saved transcript.
- **Letting a child be the chairman.** The chairman needs all five responses, the mapping, and
  all five reviews — children see only their own slice.
- **Reviewers who know the authors.** Anonymization is not optional; without it the review round
  degenerates to deference (the Contrarian sounds smart, so everyone picks the Contrarian).
- **Verdicts that hedge.** "It depends" and "consider both sides" mean the chairman failed to
  do the job. Pick, and explain the reasoning, even if it contradicts the majority.
