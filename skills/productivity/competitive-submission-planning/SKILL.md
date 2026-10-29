---
name: competitive-submission-planning
description: "Use when preparing a time-boxed competitive submission."
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [Competition, Grant, Proposal, Deadline, Rubric, Claims]
    category: productivity
---

# Competitive Submission Planning

## When to Use

Any submission judged by a rubric against a hard deadline: competitions, grant
applications, tenders, scholarships, awards, hackathons. Use when the user is
choosing what to enter, deciding what to build, or drafting the documents — and
whenever a deliverable will contain claims about work that was done.

Also load the organizer-specific companion skill if one exists (its rulebook,
rubric, and format override anything general here).

## Always-on rules

**1. Read the official rulebook in full before proposing anything.** Every other
decision depends on it. Skim-then-propose produces work that gets discarded
because the rules already excluded it. Extract to a table:
rule → consequence for the plan. Re-read it before every major decision point,
not just once.

**2. The rubric weights set the design order, not the build order.** Whatever
carries the largest weight is what the work must be shaped around. If novelty is
heaviest, an unwinnable-but-honest idea beats a polished imitation; if feasibility
is heaviest, the reverse. Write the weights down as a ranked list before
evaluating options.

**3. Find the WRITTEN list of required attachments, then work only the gating
items first.** Organizers list the mandatory documents. Anything not on that list
is not a submission blocker, however useful it would be later. Teams routinely
burn the scarce early days on documents nothing checks.

**4. Never write a claim of completed, tested, or validated work into a
deliverable unless the artifact exists and the evidence is recorded.** Most
rubrics have a verification stage that exists specifically to test these claims
(spot-checks, field validation, reference calls). A claim you cannot back does
not just cost points on that line — it casts doubt on the whole submission.
When the artifact is not ready, lower the claim, never inflate it. A modest
claim with complete evidence outscores an ambitious claim with none, because the
rubric asks whether the evidence matches the claim.

**5. Label your own scored evaluations as assessments, not measurements.** When
you rank options or score candidates, only the rubric weights are objective.
State that plainly in the document. Unlabelled scores get read back as verified
facts by whoever opens the file next, including the user.

## Procedure

1. **Ingest the rulebook** → extract: eligibility, team composition, required
   attachments, format spec (font/size/spacing/margins), rubric weights,
   timeline, submission portal.
2. **Build the gating table** — two columns: must-exist-before-submission vs
   may-follow-later. Classify every document and artifact by whether the rulebook
   names it as required.
3. **List candidate options** and score them against the rubric weights.
   Weight by the actual rubric percentages so the ranking reflects the organizer's
   priorities rather than yours.
4. **Filter for time and money** before committing. A candidate that cannot be
   demonstrated inside the window is out regardless of how well it scores.
5. **Scope-cut the chosen option** (see below).
6. **Draft the deliverable in a source format you can regenerate** (markdown),
   converting to the required format as a build step — never hand-edit the
   formatted artifact, because every later revision then has to be made twice.
7. **Fill every value you do not own with an explicit placeholder token** and
   list them at the end for the user. Names, IDs, numbers, and especially test
   results are the user's to supply.
8. **Verify the build output** by re-reading what was actually produced, not by
   trusting that the generator ran.

## Scope cutting under a deadline

When an option has several subsystems, do not default to building all of them.
Split into **core claim** and **supporting layer**, then ask: does dropping the
supporting layer reduce the novelty or the main claim? Usually it does not.
Drop the downstream layer (assembly, packaging, user-facing payoff) and keep the
instrument or method that the claim actually rests on. Write the dropped part
into the plan as a later phase, not as something promised in the deliverable.

The same applies to measurement design: pick the lightest level that still
proves the core claim (measure at system level rather than component level),
and escalate only if time remains. Escalating later is cheap; discovering on the
deadline that the full rig is unfinished is not.

Always price the risks honestly when reporting — safety hazards, shipping lead
times for components, calibration before numbers are trustworthy, and the chance
that the samples needed for a demonstration cannot be sourced. Lead-time and
sample-sourcing risks sink more submissions than technical difficulty.

## Pitfalls

- **Prototype-in-the-same-window.** Many competitions require the working demo in
  the same submission window as the proposal, with no "proposal now, build later"
  split. Confirm this early — it changes what is feasible entirely.
- **Hand-editing the formatted output.** Edit the source and rebuild. Editing the
  DOCX/PPTX directly means the next rebuild silently reverts your fixes.
- **Assuming a generated document matches the spec.** Re-open it and read back
  margins, font, size, and spacing from the file itself. Style assignments can
  fail silently.
- **Claiming a technology-readiness level the work has not reached.** Readiness
  scales are evidenced, not aspirational. Assess each component separately and
  use the weakest evidence, not the average.
- **Treating an absent team or partner as a detail.** If signatures, partnering
  letters, or advisor slots are required, they are the longest-lead gating item
  and must be started first.
- **Quoting a secondary source's numbers as verified.** Numbers lifted from a
  vendor page or a public implementation are unverified until reproduced. Mark
  them as needing verification at the point of use, and say which values must be
  re-measured before they can go into the deliverable.

## Supporting files

- `references/pkm-kc.md` — aturan naskah PKM-KC Belmawa yang sering menggugurkan (format berkas, batas RAB Tabel 2, bobot penilaian, sistematika). Muat sebelum menyusun proposal PKM-KC.
- `scripts/md2docx.py` — markdown → DOCX with a configurable submission format
  (page size, font, size, line spacing, margins). Handles code blocks, merged
  tables, and inline bold/italic. Prints a verification summary after writing.
