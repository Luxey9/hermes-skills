# Testing Apps Script locally with a node:vm harness

The `.gs` file is plain JavaScript, so it can be run and asserted on outside
Google, as long as the globals it touches are stubbed. This is the difference
between shipping a sync that silently writes wrong cells and knowing before the
user clicks.

## Skeleton

```js
import fs from 'node:fs';
import vm from 'node:vm';

const context = { console, Logger: { log: (t) => logged.push(String(t)) }, /* ...stubs */ };
vm.createContext(context);
new vm.Script(fs.readFileSync(CODE_PATH, 'utf8'), { filename: 'Code.gs' }).runInContext(context);
const report = context.syncAbsensi(false);   // call the real function
```

## Stubs to provide

| Global | Minimum shape used by sync code |
|---|---|
| `Logger` | `log` that **captures** into an array — the report text is the assertion surface |
| `PropertiesService` | `getScriptProperties()` → `{ getProperty, setProperty }` over a plain object |
| `UrlFetchApp` | `fetch(url)` → `{ getResponseCode(), getContentText() }` |
| `SpreadsheetApp` | `getActiveSpreadsheet()` → fake sheet with `getName/getSheets/getLastRow/getLastColumn/getRange` (returning `{ getValues, setValues }`), plus `getUi()` |
| `Utilities` | `formatDate`, `base64Decode`, `newBlob` (only what the script calls) |
| `ScriptApp`, `ContentService`, `LockService` | minimal no-op shapes for the trigger/webhook code paths |

## Firm up the fake sheet enough to be real

- Keep the grid as a plain array-of-arrays; `getRange(row, col, n, m)` returns
  closures over it so `setValues` mutates the same data the asserts read.
- Implement `getLastRow()` as "last row with any non-empty cell", not
  `grid.length` — trailing blanks otherwise change the row count under the script
  and mask off-by-one reads.
- Stub `getUi().alert` as a no-op so UI paths don't explode.

## Make the fake API enforce the API's rules

A stub that returns the same payload for every query hides bugs. Parse `select=`
from the URL and return **400** when a requested column is missing from the
fixture rows — that is what exercises graduated column fallbacks and schema drift:

```js
const select = decodeURIComponent((url.match(/[?&]select=([^&]*)/) || [null, ''])[1]);
const wanted = select ? select.split(',').map((s) => s.trim()) : [];
const known = new Set(Object.keys(data[0] || {}));
const bad = wanted.filter((c) => !known.has(c));
if (bad.length) return { getResponseCode: () => 400, getContentText: () => JSON.stringify({ message: `column ${bad[0]} does not exist` }) };
```

## Two fixtures, and assertions that hold for both

- Real file (argv/env path, read with SheetJS) **plus** a synthetic grid with the
  same layout, so the harness still runs on a machine without the file.
- Never assert an absolute count that only holds for one fixture (row totals, map
  sizes). Assert relations instead: the target cell is `true`, the line contains
  the expected phrase, the report does **not** contain the misleading label.
- Prefer asserting on output over internals: capture `Logger.log` text and regex
  the report, and call small pure helpers (`context.someHelper_(...)`) directly
  for unit-level cases.
- Keep one assertion proving the **dry-run wrote nothing**: snapshot the grid, run
  the dry path, compare snapshots. Also assert the zero-argument call (editor Run)
  takes the safe path.

## Fixture cases that earn their keep

- identity stored in a secondary column rather than the primary one;
- grouping value present in one format and absent in another;
- a row of caption/note text sitting in the key column;
- an unmatched label that must be **reported**, not silently dropped;
- a status that must **not** mark anything (e.g. leave/absence);
- a non-target role (staff) that must appear in the "no container" tally but not
  on the sheet.
