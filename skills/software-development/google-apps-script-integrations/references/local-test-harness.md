# Local Test Harness for Apps Script (.gs)

Apps Script cannot be run from the CLI, but the logic can: load the `.gs` file
into `node:vm` with stubbed globals and assert on the resulting sheet state. This
catches the bugs that otherwise appear as silently wrong data in production.

## Shape

```js
import fs from 'node:fs';
import vm from 'node:vm';

const context = { console, Logger, PropertiesService, LockService, ContentService,
                  ScriptApp, Utilities, UrlFetchApp, SpreadsheetApp };
vm.createContext(context);
new vm.Script(fs.readFileSync(CODE_PATH, 'utf8'), { filename: 'Code.gs' })
  .runInContext(context);
const report = context.syncAbsensi(false);
```

Two fixtures, both useful: the **real workbook** (via SheetJS, path overridable
by argv/env — proves the header/layout assumptions) and a **synthetic grid** with
the same layout (`SHEET_XLSX=none`), so the harness still runs when the file is
absent and edge cases can be constructed on purpose.

## Stub matrix

| Global | Minimum the code needs |
|---|---|
| `SpreadsheetApp` | `getActiveSpreadsheet()` → fake sheets (`getName`, `getLastRow`, `getRange`); `getUi()` → `{ alert(){} }` |
| fake `Range` | `getValues`/`setValues` **plus** `getBackgrounds`/`setBackgrounds` and `getNotes`/`setNotes` whenever the sync styles cells |
| `PropertiesService` | `getProperty` reading from a plain object **and `setProperty` writing back** — a no-op setter hides the throttle/last-run logic |
| `UrlFetchApp` | returns the fake table by URL; **validates the requested `select=` columns against the fake rows' keys and answers 400 when one is unknown** |
| `Utilities` | the date format the code uses; `base64Decode`/`newBlob` if credentials are decoded |
| `LockService`, `ContentService`, `ScriptApp`, `Logger` | trivial stubs; `Logger.log` should append to an array so assertions can read the report |

Two of these are the difference between a useful harness and a decorative one:

- **Validate `select=` against the fake rows.** Without it, the graceful
  column-degradation path is never exercised and only breaks in production, where
  the schema really is different.
- **Make `setProperty` persist.** Throttle and "already ran" logic is otherwise
  untested.

## Assertions

Assert on state, not on prose: `values[row][col]`, the background colour of a
cell, the note text. Keep a helper that maps the identifying value (NIM/ID) to its
row so tests read like the spreadsheet (`rowOf(nim)`), and assert the *report*
only for the lines the user reads (counts, anomaly labels, the project it read).

Seed "leftovers" before the run — a stale colour, a stale note, a cell coloured
by hand outside the script's palette — and assert they survive or are cleaned
according to ownership rules. That is the only way ownership bugs surface.

Run the harness in both fixture modes on every change; between them they catch
name-shadowing, number-formatted headers, and an id-matching column that was only
half read.
