---
name: google-apps-script-integrations
description: Use when building Apps Script spreadsheet/API bridges.
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [apps-script, google-sheets, webhook, trigger, integration, testing]
    related_skills: [supabase-to-google-sheets-sync, supabase-backend-debugging, google-workspace]
---

# Google Apps Script Integrations

Apps Script is the only place a spreadsheet can host code. These integrations fail
for boring, repeatable reasons — wrong container, untestable code, a deployment
that quietly serves an old version — and each one costs an afternoon if it isn't
handled up front. This skill is the mechanics; the *mapping* of domain data into
cells belongs to the sync skill for the specific project.

## When to use

- A spreadsheet must be filled or refreshed from an external HTTP API (DB REST
  endpoint, internal service) on a schedule, a menu click, or a webhook.
- "There is no Extensions menu", "the script runs but the sheet never changes",
  "the webhook stopped after I edited the code".
- You need to test `.gs` logic without touching the cloud.

## Procedure

1. **Pick the container; prefer bound.** A script created from inside the
   spreadsheet (Extensions → Apps Script) can read the file directly. A standalone
   script (`script.google.com`) cannot: `SpreadsheetApp.getActiveSpreadsheet()`
   returns `null`, so add a `getSpreadsheet_()` helper that falls back to a
   `SHEET_ID` Script Property and calls `openById`.
2. **Never put credentials in the `.gs`.** Script Properties only
   (`PropertiesService.getScriptProperties()`), with a menu prompt or Project
   Settings as the entry point. Ship a diagnostic function that prints the
   key's *shape* (length, prefix, decoded claims) instead of asking the user to
   paste the secret; the `supabase-backend-debugging` skill carries the recipe in
   its *credential claims and targeting* reference.
3. **Write the logic so it is testable off-cloud**: pure `fetch → index → build
   rows → write block` functions, all I/O at the edges, report returned as a
   string (so a harness and the editor produce the same text).
4. **Test locally with `node:vm` before deploying** — required, not optional.
   Recipe and stub matrix: `references/local-test-harness.md`.
5. **Give the editor two entry points**: one dry-run that computes and reports but
   writes nothing, and one that writes. Call the sync function with **no
   arguments = dry-run**, so a mis-click from the function dropdown cannot mutate
   the sheet.
6. **Schedule or webhook, then verify with a real event.** Time trigger is the
   safety net; a webhook is the fast path. Both, at different cadences, is the
   usual answer. Setup, hardening and the redeploy rule:
   `references/webhook-and-deployment.md`.
7. **Report the anomalies every run**, in the sheet UI where possible and in
   `Logger.log` always: rows touched, cells changed, and the specific things it
   could not place. The user audits those lines first; a report that mislabels
   its own gaps costs more than a missing feature.

## Pitfalls

- **"No Extensions menu" is not a bug in the sheet.** The menu exists only in
  Google Sheets in a *desktop browser*. The mobile app has no such menu, and an
  `.xlsx` still open in Excel is not a Sheet: upload it, *Open with → Google
  Sheets*, then *Save as Google Sheet* (URL must read
  `docs.google.com/spreadsheets/d/<id>/edit`).
- **`SpreadsheetApp.getUi()` throws outside the sheet UI** (standalone script,
  trigger, webhook). Wrap it: log first, alert best-effort inside `try/catch` —
  never let the report depend on a dialog box.
- **A code edit is not a deployment.** A bound script's menu picks up the save,
  but a web app deployment keeps serving the previous version until *Deploy →
  Manage deployments → Edit → New version*. "The webhook stopped working after my
  edit" is almost always this, not a broken endpoint.
- **A gap that exists only in your report is invisible where the user works.**
  When a record cannot be routed to a managed cell, mark its row in the sheet
  (colour + note on the identity cell) as well as counting it — the user audits the
  spreadsheet, not the execution log.
- **A public web app is public.** `Who has access: Anyone` is required for an
  external service to call it, so the shared secret in the query string is the
  only gate: reject the request when the expected secret property is **empty**, not
  only when it mismatches.
- **One user action fires many events.** A single scan/save can insert dozens of
  rows, so throttle webhook-triggered work (a last-run timestamp property) and
  guard with `LockService.getScriptLock().tryLock(...)`; otherwise you pay for the
  same sync dozens of times and race yourself.
- **Server-side timestamp filters silently drop NULLs.** Rows that represent an
  absence/excuse have no check-in timestamp; `col >= X` in the query excludes them
  and the data never reaches your code. Filter on a secondary timestamp (`OR`
  condition) or fetch unfiltered and filter in the script.
- **REST APIs cap page size** (PostgREST 1000). Paginate with `limit`/`offset`
  until a short page returns, or you will silently truncate at the boundary.
- **Column drift across sibling deployments.** Try the fullest `select=` first and
  degrade to shorter lists on 4xx; one unknown column rejects the whole request.
- **Budget against the quotas before choosing a cadence**: 6 min per execution;
  triggers total 90 min/day on a consumer account (6 h Workspace); URL Fetch
  20k/day; max 20 triggers per script. A 10-minute trigger on a slow sync can eat
  a quarter of the daily trigger budget for nothing.

## Guiding the user through the install

Setup is where they get stuck, so do not paste the whole checklist at once: give
**one step**, tell them exactly what to look at, and wait for confirmation before
the next. Write it in the user's own language.

Order that works: paste the script → set Script Properties → run the **dry-run**
entry point from the editor → check the report → run for real → install the
trigger → (optional) deploy the web app and register the DB webhook.

When something fails, ask for the pasted execution log rather than guessing: the
report text carries the project it read, the row counts, and the reason each item
was skipped — enough to name the fault without another round trip.

## Reference files

- `references/local-test-harness.md` — `node:vm` harness: stub matrix, fixtures
  from the real workbook, assertions on sheet state.
- `references/webhook-and-deployment.md` — web app deployment, secret hardening,
  trigger cadence, and the changes that require re-deploying.
- `references/mapping-rows-to-cells.md` — honest anomaly labels, multi-alias
  identity matching, mixed group-key formats, non-boolean states as colour+note
  (palette from the user's own formulas, precedence, safe clearing, row markers
  for unroutable records).
