---
name: google-apps-script-development
description: "Use when writing Apps Script to sync data into Sheets."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [apps-script, google-sheets, automation, postgrest, harness, triggers]
    related_skills: [supabase-backend-debugging, xlsx, google-workspace]
---

# Google Apps Script — development and verification

Writing, testing, and shipping Apps Script that pulls a REST/DB source and writes
a spreadsheet: bound-vs-standalone shape, credentials in Script Properties, the
semantics of "Run" in the editor, triggers/webhooks, and how to test the logic
locally without publishing.

## When to use

- Auto-filling a spreadsheet (checkbox rekap, dashboard, export) from a DB/API.
- "Can the app push into my sheet?" when the web app itself can't be changed.
- Anything meant to run on the Apps Script runtime: menu items, installable
  triggers, `doPost` webhooks, scheduled jobs over Sheets data.

## Shape that works

- **Bound** (`Extensions → Apps Script` inside the spreadsheet) when the script
  only serves that file: it finds the sheet by name, no ID plumbing, and you get
  a custom menu (`onOpen`).
- **Standalone** (`script.google.com`) when it must run headless or over several
  files. Then there is **no menu and no UI**: read the target from a `SHEET_ID`
  Script Property.
- Support both with one helper, so a copy-pasted script never dies on the
  binding question:

```js
function getSpreadsheet_() {
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) return active;
  var id = (props_().getProperty('SHEET_ID') || '').trim();
  if (!id) throw new Error('Skrip tidak terikat spreadsheet: isi Script Property SHEET_ID.');
  return SpreadsheetApp.openById(id);
}
```

- Wrap every UI call, because `SpreadsheetApp.getUi()` **throws** outside a UI
  context (standalone run, trigger, webhook):

```js
function alert_(text) {
  Logger.log(text);
  try { SpreadsheetApp.getUi().alert(text); } catch (err) { /* no UI: log is enough */ }
}
```

## Credentials live in Script Properties, never in the file

- Read config through one accessor (`cfg_()`) that trims properties and applies
  defaults; add a menu item that prompts for URL + key so the user never edits
  code. In standalone mode, throw a message naming the exact properties to add.
- Put the **fingerprint of the run in the report** (endpoint host, target file
  name). The same script is often copied between deployments pointing at
  different backends; a report nobody can attribute is worthless.
- Give the user a read-only **diagnostic function** that prints whether the stored
  credential is the right *kind* and belongs to the *same* project as the URL
  (`role`/`ref` from a decoded JWT, key length + 3-char prefix) and never the key
  itself — copy-pasting a key from a sibling project is the most common setup bug.
  The `supabase-backend-debugging` skill carries the probe error-code triage table
  (`401` invalid key vs `42501` RLS vs `42703` missing column vs `PGRST202` signature).

## Editor "Run" is not a CLI run — design for it

- A function run from the editor gets **no arguments** and its **return value is
  never shown**, only `Logger.log` output. So:
  - make zero-argument execution the *safe* mode: `if (arguments.length === 0) dryRun = true;`
  - ship explicitly named entry points (`testSimulate`, `syncNow`) that log the
    report, so the user picks intent from the function dropdown.
- Always have a dry-run that computes and reports but writes nothing; have the
  user run it before the first real write.
- Never leave a first run able to write by accident.

## Triggers and webhooks

- Time trigger: `ScriptApp.newTrigger('handler').timeBased().everyMinutes(10).create()`,
  pre-removing any trigger of the same name so re-running the installer doesn't
  stack duplicates.
- Webhook receiver (`doPost`): shared secret in the query string, `LockService`
  around the write, and a `LAST_RUN` timestamp property to throttle bursts (one
  scan session can fire dozens of inserts).
- Requests: always `muteHttpExceptions: true`, check the status code yourself and
  throw with the first ~300 chars of the body — a script that silently ignores a
  non-2xx writes wrong data.

## Verify locally before deploying

Apps Script can't be run from the CLI, but the file can: load it with `node:vm`
and stub the globals, then assert on the cells the script produced. Recipe and
stub shapes: `references/node-vm-harness.md`. Two bugs this class of harness has
caught, both invisible in review: an ES5 `var` shadowing the outer index inside a
loop, and numeric header labels (`1.0` arriving as the number `1`).

## Matching keys across two systems

- **Identity may live in more than one column.** Mirror the app's own join
  (`WHERE ep.nim = u.nim OR ep.nim = u.username`): match the sheet key against
  *every* candidate column and take the grouping value from `major` **or**
  `division`. Reading a single column silently drops whichever half of the table
  was entered the other way.
- **Resolve the container against what exists.** The grouping column is free text
  and arrives mixed (`A`, `TL A`, `S1 Teknologi Listrik A`): build candidates,
  then take the first that matches an existing sheet/tab. Never assemble one
  canonical name and reject everything else.
- **Filter the key column to key-shaped values.** Roster columns carry captions
  and notes in the same column as the IDs (`KAMIS`, `16:00-18:40`, `Belakang`):
  require the id pattern (digits, minimum length) and *count* skipped rows so
  nothing looks silently ignored.
- **Never label "no records yet" as "absent from source".** Written cells come
  from records, so a legitimately empty subject simply has none — reporting that
  as "not in the DB" invents a data gap and sends the next session chasing it.
  Build the membership index from **all** source rows and report the states
  separately: *written* / *exists but no records yet* / *absent from source*.
- **Verify a report's claim against the source before acting on it.** One probe or
  one SQL count either confirms it or refutes the label; when refuted, fix the
  label, not the data.
- **Non-boolean states become formatting, and the palette is the user's.** Permission,
  illness, unexcused absence and approved reschedule cannot be a tick: colour the
  cell + add a note and leave the checkbox empty. If the user already wrote
  conditional formatting for this, translate those rules instead of inventing a
  scheme, rank the states for the case where several records hit one cell, and only
  ever clear marks you wrote (compare colours case-insensitively, and keep colours
  from earlier versions clearable). Full recipe lives in the
  `google-apps-script-integrations` skill, in its *mapping rows to cells*
  reference.
- **A record you cannot route to a column gets a marker on its row** — colour the
  identity/key cell and put the reason in its note, so the gap is visible in the
  spreadsheet; a counter that only exists in the execution log is never audited.

## Reporting the run

Per target sheet: rows processed, cells changed, cells now TRUE, the three key
states above, skipped non-key rows, and unmatched labels. Then a summary block:
source host + target name, rows pulled, identity provenance (which column supplied
keys, how many rows had none), and a per-role breakdown of rows that mapped to
**no** sheet — loud when a role that should be on the sheet appears there, quiet
when it is staff. One counterexample beats a confident summary.

## Pitfalls

- Any inner `var` reusing an outer name (`var marks = marks[key]`) hoists
  `undefined` and breaks every iteration — name inner variables distinctly.
- Header labels can be numbers (`1.0` → `1`); normalize both sides before
  comparing labels.
- IDs are text in the DB and numbers in the sheet; exported values can be
  scientific notation (`2.02671001E8`). Normalize both sides.
- Never blank a column you don't own: read the whole managed block and write back
  untouched values, so hand-entered ticks survive.
- Default to append-only TRUE writes; expose an explicit `OVERWRITE_FALSE`
  property for teams that want the sheet to mirror the DB exactly.
- PostgREST caps a page at 1000 rows: paginate with `limit`/`offset` until a
  short page returns.
