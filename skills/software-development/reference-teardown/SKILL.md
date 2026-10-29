---
name: reference-teardown
description: "Use when reusing reference repo architecture. Read-only."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [architecture, teardown, reference, reuse, inspection]
    related_skills: [codebase-inspection, spike, systematic-debugging]
---

# Reference Teardown

Dissect a reference repo to reuse its architecture in a NEW project without modifying the reference.

## When to Use

- User points at an existing project as the model for something new
- User asks to bedah / map / split shell vs domain before scaffolding
- New project must prove the shell generically before adding domain cards

## Procedure

1. Locate the reference root first: list top-level dirs, then map two levels down with a depth-capped file find. Quote paths containing spaces on every call.
2. Establish recency with git before reading code: active branches, branch log, HEAD stats, diff against main. Read the active branch, not main.
3. Search case-insensitively before concluding anything is missing — identifiers may differ in casing from the folder name.
4. Read overlay/app shells bottom-up, batching independent reads:
   - window manifest (borderless, transparent, always-on-top, focusable, skip-taskbar)
   - native placement plus input layer (monitor choice, click-through or poll gate, wake strip)
   - pure state machine (states, timers, pinned override for pending decisions)
   - geometry module (hidden, compact, expanded sizes, hit margin, rect push to native)
   - shell controller (mode and view switching, geometry animation, input wiring, frame loop with idle stop)
   - event routing plus relay contract (external event to state to card, stdout replies, timeouts, fail-closed fallback)
5. Split shell from domain before reusing anything. Shell is window management, FSM wiring, geometry, input, collapse, cursor hit-test, frame loop. Domain is views, characters, agent or pill routing, drag or upload sequences, sounds, integrations. Only the shell ports verbatim.
6. Define two reuse contracts for the new project: fire-and-forget (show, timeout, dismiss) and decision-pending (show, pinned, answer or timeout, fail-closed to deny or terminal). Keep the shell ignorant of domain sources: show, answer, dismiss.
7. Scaffold the new project in a separate folder. Leave the reference tree untouched; confirm the reference shows only its pre-existing branch state when challenged.

## Pitfalls

- Porting domain views along with the shell drags the whole product along — port the shell first, prove it with one trivial card, then add the decision card.
- Trusting the window manifest alone misses the hard part — the click-through decision and focus-stealing avoidance live in the native poll and input layer, so read it.
- Reading main when work lives on a feature branch produces a stale teardown — check active branches and diff against main first.
- Align the direct `windows` crate with Tauri's transitive version before debugging WinRT call sites — duplicate windows-core/windows-future graphs compile separately but their RuntimeType traits never unify, so run `cargo tree -i` on the ambiguous spec and pin to a single version.
- Stub `src-tauri/icons/` before the first backend check — tauri-build's Windows resource step fails the whole check when the icon is absent, blocking all Rust verification.
- Reuse the reference Tauri test harness verbatim when the bridge pattern is kept — re-deriving the `plugin:event|listen` mock drifts from the event path production uses and burns a cycle.
- Ignore generated outputs before the first commit (`node_modules/`, `dist/`, `src-tauri/target/`, `src-tauri/gen/`) — otherwise the scaffold commit sweeps in thousands of vendored files and cleanup rewrites history.
- When the reference is a live website rather than a repo, the teardown is a DOM/CSS/asset harvest — follow `clone-web-ui` instead of reading source files that aren't there.
