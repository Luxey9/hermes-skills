# Adding a new feature (tab, panel, IPC bridge, agent) to bundled code

Depth notes for step 4c of the parent skill. Assume: no source checkout, the
only truth is `WORK/.vite/build/main.js`, `preload.js`, and the hashed renderer
bundle.

## Division of labour

- **Main-process logic goes in a NEW plain-CJS file inside the asar** (e.g.
  `WORK/src/ai-agent.js`), required from the packed entry
  (`.vite/build/main.js`). `src/` is dead weight for *existing* code — never
  patch it — but a new `require` from the build entry is fine.
- **Count the path depth from the packed entry, not from `src/`.** The entry
  lives at `WORK/.vite/build/main.js`, so the asar's `src/` is TWO levels up:
  `require("../../src/ai-agent.js")`. `require("../src/...")` resolves to
  `.vite/src/` and throws `Cannot find module`, which the surrounding
  try/catch swallows — the app runs, the tab renders, and every IPC call
  returns "bridge not available" with no error anywhere. Verify the real
  layout before trusting either form:
  `npx asar list "$RES/app.asar" | grep -i ai-agent` prints the packed path
  (`\src\ai-agent.js`), which is asar-root-relative — the `require` string is
  relative to the *calling file*, so it must climb out of `.vite/build/`.
- **Log the outcome of the `require` to the app's own log file, not
  `console.log`.** A packaged Windows app has no visible stdout, so a failed
  require is silent. Route both branches through the app's own logger -
  `try{require(...)({...});a("<FEATURE>_OK")}catch(e){a("<FEATURE>_FAIL "+(e&&e.stack||e))}`
  - and grep the log on the next start. A missing `_OK` line means the block
  never executed even though the syntax is clean.

## Trap 1 — never inject above the top-level destructuring (TDZ)

Every bundled entry begins with one destructuring line:

```js
"use strict";const{app:p,BrowserWindow:pe,screen:M,ipcMain:i,...}=require("electron");
```

Any injected block placed after `"use strict";` but *before* that line
references `p`, `i`, `L` in the temporal dead zone. Symptom at runtime:

```
ReferenceError: Cannot access 'y' before initialization
Cannot read properties of undefined (reading '__QPN')
```

The second message is the renderer variant of the same fault, not a different
bug. Fix by either injecting `"use strict";` + one `require(...)` call only
(nothing that touches the aliases at module scope), or by appending after the
destructuring statement.

## Trap 2 — verify the renderer IIFE parameter before appending

Feature code appended to the renderer bundle usually ends in a UMD-style
tail that already passes the React namespace:

```js
})(window.__RT__||s3);
```

If the exposed global (`window.__QP_RT__`, `window.__RT__`) is never set
because the injection point shifted, the bundle throws on load and the whole
window blanks. Always give the IIFE a fallback to the bundle-local React
identifier (`||s3`) rather than relying on the global alone.

## Trap 2b — two IIFEs, two closures: `s3` in one is not `s3` in the other

Appending a second IIFE that takes the bundle's React namespace (`s3`) and calls
`R.__QPN`/`R.__QPB` helpers published by a *first* appended IIFE fails even when
the parameter looks right: each appended block is its own function scope, so a
helper assigned inside block 1 is not visible as a bare `R` binding in block 2
unless both were handed the *same* object. Symptom is a render-time
`TypeError: Cannot read properties of undefined (reading '__QPN')` and the app
logging `[RENDERER PROCESS GONE] reason=crashed`.

Rules that avoid it:

- Publish helpers on **both** the React namespace and `window` inside the block
  that declares them (`R.__QPN=N; window.__QPN=N;`), and read them back with a
  fallback chain in the consumer (`R.__QPN||window.__QPN`).
- Ship a **self-contained fallback builder** in the consumer so the feature still
  renders when the helper block is missing or ran before the namespace existed:
  return a plain `{tag, props, kids, set(), text(), append()}` descriptor and
  `createElement` it. Never let a feature depend on a single fragile global.
- Chain-style builder methods must return `this`; a `forEach` that pushes into
  `this.kids` loses its `this` unless bound.

## Trap 3 — icon identifiers must exist in the bundle

Tab tables embed lucide icons by minified identifier:

```js
{id:15,name:"Quick Notes",icon:e=>o.jsx(Uy,{size:16,color:e})}
```

Reusing an identifier that is *not declared in this bundle* (e.g. `Ti`) parses
fine and crashes at render, tripping the error boundary. Before appending a tab,
extract the identifiers the bundle already uses and pick one from that set:

```python
import re
ids = set(re.findall(r'o\.jsx\(([A-Z][a-zA-Z0-9_]{1,3}),\{size:', src))
declared = {i for i in ids if re.search(r'\bconst\s+'+re.escape(i)+r'\s*=', src)}
```

## Trap 4 — after a failed patch, restore a baseline before retrying

Repairing quote damage in a minified single-line file by iterating "parse,
insert one quote at the error offset, retry" corrupts further: it inserts
closing quotes inside already-valid strings, collapsing them into `""""` and
`x.send(""listDevices")`. Two reliable exits:

1. Re-extract the pristine bundle from `app.asar.bak` and re-apply ALL edits in
   one pass from a script. Cheapest and always correct.
2. If unrecoverable in place, collapse the obvious artifacts only
   (`re.sub(r'""{2,}', '""', s)` then fix each remaining `:"}` → `:""}`) and
   re-verify with acorn — never leave a partial repair.

Structural rule: keep every injected block in its own file or as one
self-contained statement, so a rollback is deleting one line.

## Trap 5 — parse with acorn, not `node --check`

`node --check` runs in CommonJS mode and reports false positives for minified
regex literals; it also only gives a line:column. For real diagnosis install
acorn once into the scratch dir and parse explicitly:

```bash
npm i acorn          # inside $TMPDIR/acornjs
node -e 'const a=require("./acornjs/node_modules/acorn"),fs=require("fs");
const s=fs.readFileSync(P,"utf8");
a.parse(s,{ecmaVersion:"latest",sourceType:"module"})'   # renderer
```

Report `e.pos` and print `s.slice(pos-300, pos+100)` — the byte window names the
broken token far faster than the line number.

## Trap 5b — fix the whole file in ONE pass, then verify

Edit protocol that keeps a minified bundle recoverable:

1. Read the current file, compute the replacement in memory, write once
   (`io.open(p,"w",encoding="utf-8",newline="").write(out)`).
2. Verify with acorn (`sourceType:"module"` for renderer, `"script"` for
   `.vite/build/main.js`). Fix the *reported token*, then re-verify.
3. Only after both files parse, repack. Swapping a bundle that has not parsed
   guarantees a `[RENDERER PROCESS GONE]` cycle and costs a full re-extract.

Grep for the identifier you *removed* after the pass (`grep -c '<oldId>'`) — a
half-applied rename is the most common silent breakage.

## Trap 6 — verify from the app's own log, not from `tasklist`

The patched app logs to `%APPDATA%\<App Name>\quick-pill.log` (the *display*
name, which can differ in casing from `%APPDATA%\<app>`). `[RENDERER ERROR]` and
`[RENDERER CONSOLE ERROR]` lines are the only proof the renderer survived.
Processes alive + clean log = feature loaded; processes alive + renderer error =
feature threw.

## Trap 7 — a new tab needs its hotkey in THREE tables

A tab that appears in the tab list still will not open by keyboard until its
id is registered in every shortcut table, and each table fails silently:

1. Renderer display/default map — the literal next to `{id:N,name:"<Tab>"}`
   (`15:"Alt+Q"` style) feeds the Settings UI, not the OS.
2. Main-process default map — a separate `R={0:"Alt+B",...,9:"Alt+S"}` object.
   `globalShortcut.register` only iterates *that* map, so a tab missing here
   never registers even though the UI advertises the key.
3. `%APPDATA%\<app>\settings.json` → `tabShortcuts` — once the user has saved
   any shortcut, a partial object there overrides the defaults and the new key
   stays unbound. Confirm the file's real path before editing (the display-name
   folder, e.g. `%APPDATA%\Quick Pill\`, not the lowercase one).

Probe: after restart grep the app log for `Global shortcut conflict/in-use for
<Key>` — a line per key means registration ran; a *missing* line for the new key
together with no other error means it was never in the map. Two app instances
alive at once also produce conflicts, so restart cleanly before concluding.

When **every** key conflicts on a fresh start, it is not a map bug — a second
build of the same app owns the combos (Windows hands each global shortcut to one
registrant only). Diagnose by path, since both installs share `ProcessName`, and
follow §4n of the parent skill before touching any bundle.
Logging only failures is not enough to distinguish "registered" from "never
ran": add a success line to the registrar
(`J.register(o,()=>{Ue(parseInt(n,10))})?(Z.push(o),a(`Shortcut OK: ${o} -> tab ${n}`)):a(...)`) and
confirm one line per key on the next start.

## Trap 7b — the tab list is persisted, so a new tab can be silently absent

Editing the `Vs` tab table and the shortcut maps is **not** enough. These apps
persist a user-ordered tab list in `localStorage` (`tab-order`) and a
`hidden-tabs` set, then render `a.filter(...)` over the *persisted* array. A new
id missing from that array renders nothing: the hotkey fires, the state moves to
`ge===<newId>`, no branch matches, and the UI falls back to the first tab in the
list — the user reports "it opens Overview instead".

- Find it by grepping `tab-order` in the renderer: the loader reads
  `JSON.parse(localStorage.getItem("tab-order")||"null")` and then runs a chain
  of `if(!c.includes(N))` migrations, each with a literal default array at the
  end of the `catch`.
- Fix in three places: append a migration block for the new id mirroring the
  neighbouring ones (`splice(c.indexOf(prev)+1,0,newId)`), add the id to the
  literal default array, and drop removed ids from both with one `_rm` loop that
  saves once.
- Confirm from disk, not from the UI: the value lands in
  `%APPDATA%\<Display Name>\Local Storage\leveldb\*.log` as plain text. Grep that
  directory for `tab-order` and read the newest match —
  `[2,11,12,13,15,16,...]` proves the migration ran.
- Migrations are code, so they only apply to a bundle that actually contains
  them: compare `stat` mtimes of the work copy and `resources/app.asar` before
  re-testing, and repack if the source is newer.

## Trap 8 — `createElement` children are varargs, not an array

When the injected component builds elements by hand, passing a children *array*
as the third argument nests it as one child instead of spreading it:

```js
m.createElement("div", {style}, kids)    // one array child — nothing renders
m.createElement("div", {style}, ...kids) // correct
```

Spread every array argument (`...kids`, `...rows`, `...listChildren`). The
symptom is a container with correct styling and no content, which reads like a
layout bug and sends you hunting in the wrong file.

A blind `str.replace("h(", "o.jsx(")` over a component body also rewrites
`.push(` into `.pusm.createElement(` — do the rename with word boundaries and
grep the result before parsing, or re-inject the whole component from source.

## Trap 9 — write the new component at module top level, using the bundle's hook object

An injected component must live in the **same module scope** as the bundle's
React binding, not inside a fresh IIFE. Determine the binding empirically before
writing code — count the hook prefix the bundle itself uses:

```python
import re
cands = {}
for m in re.finditer(r'\b([A-Za-z_$][A-Za-z0-9_$]{0,3})\.useState\(', src):
    cands[m.group(1)] = cands.get(m.group(1), 0) + 1
print(sorted(cands.items(), key=lambda x: -x[1])[:5])   # winner = the real binding
```

The winner (a short name like `m`) is what every app component calls. Insert the
new `function <NewTab>(...)` **immediately before a sibling component
declaration** (grep `function aM(` / another `function <Name>(`), so it sits at
top level and can reference that name directly. Verify the runtime object is a
React module before relying on it — a variable that only looks like React
(`s3` was react-dom's dev build) yields `useState is not a function` at first
render, and an error boundary turns the whole window into a blank or fallback
tab.

## Trap 10 — removing a tab means removing four things

Deleting a feature (removing an unwanted tab) needs every one of these gone, or
it leaves dangling references:

1. The entry in the `Vs` tab table.
2. Its key in the renderer shortcut map **and** the main-process `R` map.
3. Its render branch — `ge===<id>&&...`. These are `&&`-joined expressions in one
   huge `children:[...]` array, so cut from the marker to the balanced closing
   paren **including the trailing comma**, not with a regex.
4. Its id in the persisted `tab-order` (see Trap 7b) and `hidden-tabs`.

A safe cut: walk forward from `ge===<id>&&` counting `(`/`[`/`{` with a
string/escape-aware scanner, stop when depth returns to 0 and the next
non-space char is `,`/`]`/`}`, and splice that exact range. Re-run acorn after
each tab so a bad cut fails immediately instead of compounding.

## Agent bridge skeleton (tool-calling over an OpenAI-compatible endpoint)

Keep the wire format minimal and let the renderer hold the transcript:

- `ipcMain.handle("ai:config")` → `{model, baseUrl, hasKey, roots}` (no secrets).
- `ipcMain.handle("ai:chat", (_e, messages) => ...)` loops up to `maxSteps`:
  POST `{model, messages, tools, stream:false}`, and on `message.tool_calls`
  push `{role:"assistant", tool_calls}` then one `{role:"tool", tool_call_id,
  content: JSON.stringify(result).slice(0, 12000)}` per call (`id` must be
  echoed or 400).
- Credentials in `%APPDATA%\<app>\ai-config.json` — never in the bundle.
- File tools must validate every path against an allow-list of roots
  (`resolved.startsWith(root + path.sep)`) *inside* each tool; the model will
  invent absolute paths outside the allowed tree.
- Scope tools to read-only (`search_files`, `read_file`, `list_folder`,
  `open_path`) unless the user asked for write access explicitly.

Skipped by default: streaming, persisted chat history, in-app endpoint editor.
Say which are skipped rather than implying they exist.
