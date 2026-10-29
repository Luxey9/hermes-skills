---
name: web-app-runtime-verification
description: "Verify web app fix in real browser before claiming done."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, browser, cdp, frontend, regression, evidence]
    related_skills: [dogfood, systematic-debugging, node-inspect-debugger]
---

# Verifying a change in a running web app

## Overview

Finding a bug and writing a fix is half the job. This skill is the other half:
proving, in a real browser, that the bug existed and that the change removes it.

The method is always the same three beats: **reproduce → patch → re-run the same
reproduction**. The reproduction comes first, because a fix written against a
code reading is a guess; and it comes back after, because a fix that was never
re-executed is unverified.

Use this when the deliverable is a *verified behavior change* in a browser app.
For hunting unknown bugs across a whole app, use `dogfood`; for server-side data
probes, use `supabase-backend-debugging`.

## When to Use

- You changed front-end behavior and are about to tell the user it is fixed.
- A fix was written from reading code and has never been executed.
- A previously-working flow broke and you need before/after evidence.
- You must decide whether a deployed site is running your new code.

**Don't use for:** exploratory bug hunting across a whole app (`dogfood`), or
backend/data questions answerable with HTTP probes
(`supabase-backend-debugging`).

## Procedure

1. **Confirm the driver actually drives**, before anything else. Run one cheap
   probe (navigate somewhere trivial, read `document.title` or an `h1`). A
   browser tool returning `success` is not proof the page moved. Probe for the
   helper names this build exposes rather than writing a workflow against
   presumed ones.
2. **Know which build you are testing.** Fetch the deployed entry HTML and
   extract the hashed asset filenames; compare against your local build output.
   If the deployed bundle is older, the live site will cheerfully reproduce the
   "fixed" bug. See `references/local-vs-deployed.md`.
3. **Reach the state the bug lives in.** Enter a logged-in session, seed the
   scoped data, set the app's own persisted keys. Do not test from a cold page if
   the bug only appears mid-flow.
4. **Clear the app's persisted state** before each run (checkpoint keys,
   `sessionStorage` tokens, drafts). Leftover state from the previous run
   silently changes the scenario.
5. **Capture the reproduction as machine-checkable output** — persisted keys, a
   step/panel label, the rendered heading, a status code, a response body. Print
   a JSON array of snapshots so before/after can be diffed.
6. **Patch.** Root cause only; no drive-by refactors.
7. **Type-check and build** — necessary, not sufficient.
8. **Re-run the identical reproduction** on the patched code. Same script, same
   steps, same assertions. Compare against step 5's output.
9. **Report**: what was reproduced, what changed, the before/after evidence, and
   explicitly anything you could not verify.

## Right-size the claim

State only what the evidence supports. The honest ladder, weakest first:

- *Read the code and reasoned* — say "I have not run this."
- *Type-check + build pass* — say "compiles, not yet exercised."
- *Reproduction ran against the patched code* — say "verified", and show the output.

The step everyone is tempted to skip is the third one. Do not promote the second
to the third. When the harness blocks you, deliver the unverified diff **plus** a
short manual reproduction the user can run in 4-6 steps, and offer to fix the
harness — a fabricated pass costs far more than an admitted gap.

## When the browser is not available

A blocked harness is not zero evidence. Before writing "unverified", collect what
is still provable, strongest first:

1. **Dependency-source ground truth.** The exact rule usually lives in the
   installed package — read `node_modules/<pkg>/dist/**` for the validation
   function, the constants, and the stylesheet it relies on, and quote it. This
   is version-exact and beats both docs and recollection.
2. **Emitted-markup evidence.** Render the component with `react-dom/server`
   inside whatever provider it needs and with the props its real parent supplies,
   then assert on the markup: attributes, classes, inline styles, ordering. This
   catches whole classes of bug (element absent, wrong type, wrong geometry)
   without a browser.
3. **Invariant tests over source assets.** Parse the stylesheet/config and assert
   the invariants the fix depends on — *including the dependency assumptions you
   are leaning on*, so a version bump surfaces as a red test. Lock the mechanism
   behind the bug CLASS, not the one symptom you happened to see.
4. Typecheck + build — proves the prop/API is wired, not that behavior is right.

State the smaller claim explicitly ("cannot replay the drag here; verified the
markup, the dependency rule, and locked the invariants") and hand the user a 3-4
step manual check — including a **hard refresh** when the change is CSS or JS,
because a cached bundle makes them exercise the old code and report the fix as
failed.

Prefer a fix that does not depend on a runtime config value at all. When the fix
rides on a mode flag, a passing typecheck proves the value reaches the library
but not that it takes effect — remove the dependency, or make the config
redundant, and the fix stops being hostage to it. Recipes in
`references/offline-verification.md`.

## Pitfalls

- **Fixed-height overlays clip their own controls.** When header/footer buttons look cut off top-and-bottom, suspect the container height constant first, not the button CSS — size the expanded container from content plus padding headroom, and pin header buttons to the top so they cannot slide under the badge.
- **Ask for a screenshot on layout complaints and analyze the pixels.** A user photo of clipped controls localizes the fault (top inset vs container height vs overflow) faster than code reading — diagnose from the image before touching CSS.

- **Bump the JS cache-buster on every front-end change.** A `?v=` query on the
  script tag is the deploy mechanism on no-build static sites — forget it and
  the browser keeps running the old bundle while you claim the fix is live.
- **Verify a static server actually serves the new bytes.** `node --check` proves
  syntax, `/health` proves the server is up — neither proves the browser got the
  new file. Fetch the entry HTML and confirm the new `?v=` is referenced.
- **Do not diagnose from a snapshot taken mid-reload.** Under a dev server with
  hot reload, writing a file inside the watched tree triggers recompiles; DOM
  reads come back empty (`#root` with no children, aborted module requests) while
  that settles. Reload once, wait a beat, re-read.
- **A launcher that starts the browser and exits kills the browser.** Spawn it
  detached with `unref()` so it outlives the script; a browser that dies with its
  script reads as "the browser keeps crashing".
- **A failing build is not a failing fix — check which side broke.** Serve your
  own build output rather than assuming the dev server represents it.
- **Re-issuing a byte-identical tool call can return the cached previous result.**
  Change the argument or target before retrying.
- **Keep probes one step per call when the driver is flaky.** Long multi-step
  eval scripts time out as a unit and lose all evidence; short calls that each
  print something survive partial failure.
- **A piped gate reports the exit status of the pipe's LAST stage.**
  `bun run lint 2>&1 | tail -2` prints the errors and still exits 0, so the
  failure reads as green. Read the summary line (`✖ N problems`), or run the
  gate unpiped, before you call it passed — a gate that failed silently turns
  into a claim you cannot defend when the user asks how you verified it.
- **In a repo with a pre-existing dirty baseline, never report "clean".** Lint
  the OLD revision of each file you touched against the new one
  (`git show <rev>:<path> > scratch/old.tsx && npx eslint scratch/old.tsx` vs the
  working file) and report both counts — "36 problems before, 36 after, zero
  added" is a real statement; "lint is clean" in a repo carrying hundreds of
  pre-existing errors is a false one, and it destroys trust in the rest of the
  report.
- **Time-box the tooling.** A couple of honest attempts to get the browser
  driving, then stop. Burning the session on the harness is not verification.
- **A harness that renders nothing is not evidence the element is absent.** A
  component can silently emit nothing when its required provider or a required
  prop is missing. Print the markup and confirm the elements you expect appear at
  all before concluding anything from their absence — a wrong conclusion here
  gets written into a skill and costs the next session the cheapest verification
  tool it had.
- **A typed prop that typechecks proves wiring, not behavior.** `tsc` passing on
  a config prop means the value reaches the library, not that the library behaves
  as you assume. Read the library's own rule or exercise it; never report the
  prop itself as the fix.

## Going deeper

- `references/cdp-driving.md` — driving a Chromium instance directly over CDP:
  launching detached, page vs browser targets, per-runtime message encoding,
  eval hygiene.
- `references/local-vs-deployed.md` — serving your own build for A/B testing,
  confirming which bundle is live, proxying the app's API, minting a session
  token to skip the login UI.
- `references/postgrest-column-grants.md` — when a Supabase-backed app fails per
  role: distinguishing a missing column grant from a field stripped by a view.
- `references/offline-verification.md` — collecting real evidence when the live
  browser is unavailable: SSR markup harnesses, dependency-source ground truth,
  CSS/markup invariant tests, and how to phrase the resulting claim.
