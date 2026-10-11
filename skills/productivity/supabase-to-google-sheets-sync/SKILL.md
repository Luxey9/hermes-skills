---
name: supabase-to-google-sheets-sync
description: Use when syncing DB rows into Google Sheets cells.
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [supabase, google-sheets, apps-script, sync, checkbox, rekap]
    related_skills: [google-workspace, xlsx, supabase-backend-debugging]
---

# Supabase → Google Sheets Sync (Apps Script)

Push DB state into a spreadsheet (checkbox rekap, dashboard, export) without
writing app code: a **bound Apps Script** pulls from the Supabase REST API and
writes cells, on a menu click, a time trigger, or a webhook.

## When to Use

- "Absen di aplikasi langsung masuk ke spreadsheet" / any auto-fill of a
  checkbox or rekap column from database rows.
- A spreadsheet grading table must stay in sync with attendance/grades stored in
  Supabase (or any Postgres with a PostgREST endpoint).
- The target is Google Sheets and you cannot add server code to the web app.

## Shape that works

- Script lives **bound** to the target spreadsheet (Extensions → Apps Script) so
  it reads the sheet by name — no sheet ID/URL plumbing.
- Credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) in **Script Properties**,
  set through a menu prompt. Never inside the .gs, never in the sheet.
- Pull (not push) by default: the managed block is recomputed and written in one
  `setValues` per sheet, so the sheet self-heals after deleted rows.
- Modes: **menu click**, **time trigger** (`ScriptApp.newTrigger(handler)
  .timeBased().everyMinutes(10)`), optional **webhook** (`doPost`) with a shared
  secret in the query string + `LockService` + a last-run timestamp property to
  throttle bursts (one QR/scan session fires dozens of inserts).
- Always ship a **dry-run** menu item that computes and reports but writes
  nothing; the user runs it before the first real sync.

## Verify locally before deploying (non-negotiable)

Apps Script can't be run from the CLI, but the logic can. Write a Node harness
that loads the `.gs` file with `node:vm` and stubs the globals
(`SpreadsheetApp`, `UrlFetchApp`, `PropertiesService`, `Utilities.formatDate`,
`ScriptApp`, `Logger`, `LockService`), then call the sync function and assert on
cells. This catches real bugs (see below) that would otherwise surface as silent
wrong data in production. Keep the harness next to the script with the
spreadsheet path overridable by argv/env, plus a synthetic grid fallback.

## Pitfalls (each one cost a debug pass)

- **Header labels can be numbers.** A column labelled `1.0` in Excel arrives as
  the number `1`. Match headers through a normalizer that strips trailing `.0`
  (`1` === `1.0`), not by raw string compare.
- **Duplicate header labels exist.** The same `1.0/2.0/3&4` set often repeats in
  other sections of the same sheet. Take the **first** occurrence, and anchor the
  header row on a label unique to the target block.
- **IDs: numeric cell vs text column.** A NIM/username is text in the DB and a
  number in the sheet; exported text can be scientific notation (`2.02671001E8`).
  Normalize both sides (round scientific notation, strip spaces/quotes/`.0`).
- **PostgREST caps at 1000 rows.** Paginate with `limit`/`offset` until a short
  page comes back.
- **`var` shadowing kills the loop.** `var marks = marks[key]` (any inner `var`
  reusing an outer name) hoists `undefined` and breaks every iteration. Name
  inner variables distinctly. Same trap in Apps Script and in the vm harness.
- **Never blank a column you don't own.** Read the whole managed block and write
  back the untouched columns' original values so unmanaged checkboxes survive.
- **Default to append-only TRUE writes.** Only turning cells ON avoids wiping
  ticks entered by hand; expose an explicit `OVERWRITE_FALSE` property for teams
  that want the sheet to mirror the DB exactly.
- **Rows with no meeting/session reference** (manual entries) can't be placed in
  a dated column. Don't ship date-guessing as the answer: add an explicit
  `meeting`/`session` column, make the UI require it on manual entry, and keep
  the date match only as a fallback for historical rows. The sync reports the
  count per source (`chosen meeting / session title / date match`) so the user
  can see how much is still guesswork and when the old rows have aged out.
- **Verify the real layout with SheetJS, not with a text extract.** Markdown/PDF
  extraction of an .xlsx re-flows merged multi-row headers and points at the
  wrong header row. `XLSX.utils.sheet_to_json(ws, {header:1, raw:true})` gives the
  truth (real row numbers, real cell types).
- **After xlsx → Google Sheets import**, confirm the checkboxes survived; if they
  became plain `TRUE`/`FALSE` text, the user must Insert → Checkbox on the range.

## Reporting

Summarize per sheet: rows processed, cells changed, checkboxes TRUE, and any
unmatched keys (unknown session titles, IDs missing from the DB, mapped classes
with no sheet). The user needs the anomalies, not just "done".
