---
name: patching-packaged-electron-apps
description: Use when patching installed Electron app code.
metadata:
  version: "1"
  hermes:
    tags: [electron, asar, windows, patch]
    related_skills: [reverse-engineer-anything]
---

# Patching packaged Electron apps

## When to Use

Use when the user asks to change, remove, or relabel something inside an
already-installed Electron app (overlay/dynamic-island utility, tray app, any
shipped desktop tool) and no source checkout is available — unpack `app.asar`,
patch bundled strings, repack, relaunch on Windows, roll back.

Goal: change behavior of an already-installed Electron app when source is not
available locally, keep the change reversible, and actually relaunch it so the
user can see the result. Keep the original artifact as a backup — every step
below assumes rollback is one file move away.

Read-only feature inspection of the same artifact belongs to the
`reverse-engineer-anything` skill (ASAR/JavaScript routes); come here once the
user asks to *change* something.

## 1. Locate the app and its app.asar

- Installed NSIS/electron-builder apps live under
  `%LOCALAPPDATA%\Programs\<app>\`; portable or updater-dropped installs may
  instead sit in `%LOCALAPPDATA%\<app>\`. Check both, then confirm layout with
  `ls -lh "<install>/resources"`.
- Code lives in `resources\app.asar`.
- The install directory name is not the executable name: list `*.exe`
  (`<App>.exe`, `Uninstall <App>.exe`) and launch by the exact file name.
  Guessing the process name silently finds nothing.
- User data (settings, notes, stores) is in `%APPDATA%\<app>`, separate from the
  code; patching code never wipes it.

## 2. Unpack, with a backup

```bash
RES="$LOCALAPPDATA/Programs/<app>/resources"
cp "$RES/app.asar" "$RES/app.asar.bak"
WORK="$LOCALAPPDATA/hermes/cache/scratch/<app>-extracted"
rm -rf "$WORK" && mkdir -p "$WORK"
npx --yes asar extract "$RES/app.asar" "$WORK"
```

Reuse an existing `app.asar.bak` rather than re-copying: once patched,
`app.asar` no longer equals the original.

## 3. Find the patch target in bundled code

- Renderer bundle: `WORK/.vite/renderer/main_window/assets/index-<hash>.js` or
  `WORK/build/renderer/main_window/assets/index-<hash>.js` (hash changes per
  build). Main process:
  `WORK/.vite/build/main.js` and `preload.js`.
- Locate by unique literal, not by structure:
  `grep -o '.{0,80}<needle>.{0,120}'` on the bundle. Bundled code is minified to
  one long line, so `grep -n` line numbers are useless; `awk 'length($0)>500'`
  maps the big lines first.
- **A windowed `grep -o` prints nothing when a newline sits inside the window**
  (`.` never matches newline). Vite-built `main.js` keeps its newlines even when
  the renderer bundle is one line, and a packed `app.asar` blob has newlines
  everywhere — so `grep -c` counting hits while `grep -o` stays silent is that
  tell, not a missing symbol. Strip newlines first (`tr '\n' ' '`), or extract
  the file and slice around `src.find(needle)` in Python.
- Read the match in context first. Identifiers (`Se.appName`, `V0`) belong to the
  bundler; patch the literal string or the short expression around it, never the
  identifier, which a later minifier pass may reuse.

## 4. Patch strings programmatically, with an occurrence count

Use a Python script with an explicit `(old, new)` list and print `src.count(old)`
per pair before writing — zero means the needle drifted (app update, different
build) and the edit would silently do nothing.

```python
import io
p = r"<WORK>/.vite/renderer/main_window/assets/index-<hash>.js"
src = io.open(p, encoding="utf-8", errors="ignore").read()
for old, new in [("<old literal>", "<new literal>")]:
    print(src.count(old), old[:60])
    src = src.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="").write(src)
```

Patch *every* place the behavior is expressed (classifier regex, color constant,
copy string) or the UI ends up half-changed.

When the user says a rendered element "doesn't show content" or "isn't readable",
the bundle usually renders one field where two are available — read the render
expression before touching layout. `children:A||B` shows only `A` whenever `A` is
non-empty, so the body text silently vanishes. Add the missing field as its own
span instead of assuming data loss.

### Keep the patch loop idempotent, and backups out of the packed tree

- **A re-runnable patch script must consume its own anchors.** If the
  replacement still *contains* the old literal
  (`wxMeteo:(...),` → `wxMeteo:(...),salahTimes:(...),`), `src.count(old)` stays
  1 after the first run, so a second run (e.g. re-applying after reverting one
  layer) inserts a **duplicate** entry — a doubled key in the preload bridge.
  Either assert the inserted marker's post-count is exactly 1, or include in the
  old string the trailing context the new string replaces. When re-applying to a
  reverted file, re-run only the layers you reverted.
- **Backups go in the scratch dir, never next to the bundle.** A `*.qpbak`
  left inside the extracted `app/` tree is packed into the new asar: the
  artifact silently grows by the backup's size (measured: one renderer backup +
  2 small files → 4.64 MB vs the correct 3.93 MB) while every diff still looks
  right. Move backups out before `asar pack` and sanity-check the output size
  against the size of the patch.
- **`Number(null)` is 0, not NaN.** A settings reader shaped
  `num(v,d){var n=Number(v);return isNaN(n)?d:n}` therefore ignores its default
  for an unset key and every fresh install gets `0`. Guard
  `if(v===null||v===undefined||v==="")return d` first. Symptom to watch: a
  documented default ("remind 10 min before") silently reads as the 0 option.

## 4b. Sizing lives in a computed width/height expression

Overlay/pill UIs package their geometry as one minified ternary pair
(`Ov=<flags>?W:...` width, `Iv=<flags>?H:...` height, applied as
`animate:{width:\`${Ov}px\`,height:\`${Iv}px\`}`). Search
`animate:{width:` / `width:\`${` to find it, then change the branch that matches
the state the user complains about (banner state, quick state, large state) —
not the base value, which other states reuse. Enlarge the branch *and* relax the
text itself: `whiteSpace:"nowrap"` + `textOverflow:"ellipsis"` + single line
must become `display:"-webkit-box", WebkitLineClamp:N,
WebkitBoxOrient:"vertical", whiteSpace:"normal", wordBreak:"break-word"`, and
container padding/gap must grow to match, or the extra height just adds empty
space.

State flags are evaluated in one long boolean chain — re-read the chain after
editing, because the branch you want may be `re`/`dn`/`Se`-driven rather than
the `w0` flag that looks closest by name.

When the user asks for a notch/banner to "fit the content", do not bump the
constant — replace that branch with an inline computation over the rendered
strings (`52 + min(2,lines(title,30))*16 + min(2,lines(body,36))*15`, clamped
72–150). An IIFE inside the ternary works because the branch is a plain
expression. Keep the clamp: an unbounded height overflows the transparent
window and clips the message instead of growing it.

Prefer a working default over an in-app settings toggle that does not exist: if
the fix needs a knob, set the new value as the default and report it, rather than
building a settings entry the app can't store.

## 4c-bis. "Fitur ini hilang" is usually a default-hidden flag, not deleted code

When the user reports a feature they remember (a panel, a stat readout, a tab)
as gone, prove whether it exists in the bundle *before* planning any patch. The
answer is frequently "present but hidden by a default value", and the fix is one
localStorage key, not a code edit.

1. **List the tab/route table** — `grep -o 'Vs=\[{id:1'` (or search
   `{id:<n>,name:"`) to see every feature the build registers. If the feature is
   in that list, the code ships and the problem is visibility.
2. **Find the hide list and its default.** Search `hidden-tabs` (or
   `hidden-*`) and read the fallback: `localStorage.getItem("hidden-tabs") ||
   "[6]"` means id 6 is hidden on a fresh install. The feature is deliberately
   off by default — usually a half-finished provider, or one that crashes on
   other hardware. State that motive rather than calling it a bug.
3. **Confirm the IPC path is intact end to end** — the bundled call, the
   preload bridge, and the main-process handler all three:
   `grep -o -i 'get-system-metrics\|cpu\|freemem' WORK/.vite/build/main.js`,
   `grep -o 'getSystemMetrics' WORK/.vite/build/preload.js`, then the renderer
   call site. All three present = nothing was removed.
4. **Report the runtime toggle first**, patched default second. Give the
   in-app path (settings → tabs), the direct hotkey from the hotkey map
   (`6:"Alt+G"`), and a console override:
   `localStorage.setItem('hidden-tabs','[]'); location.reload();`
5. **Only change the default if the user asks.** Flipping `"[6]"` to `"[]"` in
   the bundle makes the feature appear on every fresh install — do not do that
   silently, since the original author may have hidden it for a reason.
6. **Verify the hide list is the actual cause before recommending a toggle.**
   The default literal being `"[6]"` proves only what a *fresh* profile would
   do. Scan the live userData for the key and its value:
   `python -c "import glob,os;[print(f) for f in glob.glob('**/*',recursive=True) if os.path.isfile(f) and os.path.getsize(f)<8_000_000 and b'hidden-tabs' in open(f,'rb').read()]"`
   inside `%APPDATA%\<app>`. Chromium's leveldb stores a localStorage key as
   `_file://\0\x01<key>`, so `strings`-based grep for the bare name returns
   nothing even when the key exists — search the raw bytes for the key AND for
   its value (`b'[6]'`) separately. If the key is **absent**, the default is
   not what is hiding the tab: stop hunting storage and check hotkey delivery
   (§4n), because the user is probably pressing a shortcut that never arrives.

Related trap: a widget can be fully implemented and still read as "missing"
because its data source returns zeros — check the handler body
(`os.totalmem()/freemem()`, `os.cpus()`) before concluding the UI was stripped.

## 4d. Notification sound without shipping an audio file

A renderer-side `AudioContext` cue avoids touching the asar's assets, the
preload, or IPC — append one self-contained IIFE that publishes
`window.__<X>_BEEP__(kind)` and trigger it from a `useEffect` keyed on the
notification id. Two rules:

- **Dedupe on the record id**, not on a re-render: guard with a `window.__LAST_<X>__
  !== id` check, otherwise every unrelated state change re-fires the chime.
- **Say the autoplay limit out loud.** Chromium suspends an AudioContext created
  without prior user gesture, so the *first* cue after launch can be silent; it
  resumes after one click inside the app. Report that as a known limit instead of
  letting the user discover it — do not promise audio from the very first second
  unless you also add a preload/main-process playback path.

## 4d-bis. Notification icon: the app's OWN notifications need one supplied

A notification the app raises through the injected `__QP_NOTIFY__` carries no
`icon`, so the banner falls back to a letter circle (first char of `appName` on a
gradient) — after a rebrand the user reads it as a stranger's icon. Fix in three
parts:

- **Put the icon in the payload.** `icon: window.__QP_APPICON__ || void 0` with
  `window.__QP_APPICON__ = new URL("../../../src/assets/icons/icon.png", document.baseURI).href`
  set once in an appended block. The app's own icon lives at
  `src/assets/icons/icon.<png|ico>` inside the asar — same path main resolves for
  the window icon — and a `file://` page *can* load that `file://` URL. Prove it
  with an `Image()` load callback (`naturalWidth` 512 = resolved) rather than
  trusting the string.
- **Teach the banner a shape.** The banner hardcodes the system-icon look
  (`{width:24,height:24,borderRadius:"50%",objectFit:"cover"}`), which crops a
  square logo and eats text baked into the artwork. Branch that one style object
  on a payload field:
  `style:Se.iconShape==="app"?{width:24,height:24,borderRadius:7,objectFit:"contain",flexShrink:0}:{...unchanged...}`.
  System notifications keep the circle; app-owned payloads pass
  `iconShape:"app"`. The banner `<img>` has no `onError`, so a bad URL shows a
  broken-image glyph — assert `naturalWidth > 0` over CDP.
- **Patch every injected notify call site**, not just the new feature: task
  reminders raised by an older block show the same letter circle.
  `grep -o '__QP_NOTIFY__('` finds them, and each edit must consume trailing
  context (see the idempotency rule in §4) or a re-run duplicates it.

**Re-shoot at zoom before "fixing" what a small render seems to show.** A 24 px
banner icon appeared to carry a red count badge in a full-banner screenshot; the
DOM had no such element — it was the logo's own artwork (a tiny clock pill inside
the icon) at that size. `Page.captureScreenshot` with `clip:` set to the
element's exact rect at `scale: 6-8`, re-read the crop, and only then decide.
Never patch against a reading you have not zoomed.

## 4c. Adding a NEW feature (tab, panel, IPC bridge) instead of editing a string

When the ask is "add a chatbot tab", "add an agent", "add settings page" — read
[references/adding-features-to-bundled-renderers.md](references/adding-features-to-bundled-renderers.md)
before writing code; it carries the TDZ injection rule, the acorn diagnosis
recipe, the icon-identifier check, the recovery path after a corrupted bundle, and
the OpenAI-compatible tool-calling bridge skeleton. Summary of the traps:

- **The bundle's React is not global.** `window.React` is undefined in a Vite
  production bundle; a React sourced from anywhere else is a second copy and
  hooks throw "invalid hook call". Expose the bundle's own copy right before it
  mounts: insert `window.__RT__=<rootIdVar>;` immediately BEFORE
  `varRootId=document.getElementById("root")` (the 4th-and-later ref like
  `s3`, not the first `createRoot` mention which is react-dom's own
  definition). Give the appended IIFE a fallback — `})(window.__RT__||s3);` —
  because a shifted injection point leaves the global unset and the window
  blanks.
- **Never inject above the top-level destructuring.** `"use strict";const{app:p,
  ipcMain:i,...}=require("electron");` is line one; an injected block placed
  after `"use strict";` references those aliases in the temporal dead zone and
  the app dies with `Cannot access '<x>' before initialization`. Inject only a
  one-line `require("../src/<feature>.js")({app:p,ipcMain:i,shell:L})` wrapped in
  try/catch — real logic lives in its own plain-CJS file inside the asar.
- **Icon identifiers must already exist in the bundle.** Reusing a lucide
  identifier this build does not declare parses fine and crashes at render;
  grep the bundle's existing `o.jsx(<Id>,{size:` set first.
- **Verify from the app's own log**, not `tasklist`: `[RENDERER ERROR]` in
  `%APPDATA%\<App Display Name>\*.log` is the only proof the renderer survived.
  Clean log + live processes = loaded; live processes + renderer error = threw.
- **After any failed in-place patch, re-extract from `app.asar.bak` and redo all
  edits in one pass.** Iterative "insert a quote at the parse error offset"
  repair on a minified one-line bundle corrupts further; acorn (`npm i acorn`,
  parse with `ecmaVersion:"latest", sourceType:"module"`, print
  `src.slice(e.pos-300, e.pos+100)`) diagnoses the real token fast.
- **Hand-write imports anyway.** You cannot add `import` to a minified single
  module without breaking it — the injected component must be jQuery-style
  DOM building or an element-descriptor builder (`N(tag).set(k,v).text(x)`),
  rebuilt by a tiny `build()` that calls the exposed `createElement`.
- **IPC needs all three layers**: `ipcMain.handle(...)` in
  `WORK/.vite/build/main.js`, one line in `WORK/.vite/build/preload.js`
  (`contextBridge`), and the renderer call. `src/` copies inside the asar are
  dead weight — the packed build reads `.vite/build/*`, so never patch `src/`.
- **Register the new tab in the tab table, the hotkey map, and the size table**
  (find `{id:15,name:` for the list, `15:"Alt+Q"` for shortcuts,
  `?ge===14?` branches for width/height), then mount it next to a sibling
  `ge===15&&o.jsx(` block. Give the new id an entry in scoped-chain form inside
  the size table (`ge===16?640:` before the shared fallback) — an id with no
  width/height branch inherits the smallest state and the feature renders clipped.
  The hotkey has to go in the **renderer default map AND the main-process default
  map** the globalShortcut registrar iterates, and in `settings.json`'s
  `tabShortcuts` if the user ever saved shortcuts — three places, each failing
  silently. Verify with the log line
  `Global shortcut conflict/in-use for <Key>`.
- **Pinned tab lists are token arrays, not derived from the tab table.** The
  `tab-order` store and its fallbacks embed explicit ids, so a new id needs
  matching edits or it never shows for anyone: the migration block
  (`if(!c.includes(16)){const f=c.indexOf(15);…c.indexOf(f+1,0,16)…}`) gets a
  second clause for the new id, the `return[2,11,12,13,15,16,4,…]` fallback
  array gets the id inserted at its intended position, and the seeded default
  string (`"tab-order":"[2,4,5,6,7,8,10,0,1,3,9]"`) is rewritten to the
  canonical post-migration order. Read the token list back over CDP on first
  launch — a missing entry looks like "the patch did nothing" in the UI.
- **Appended renderer blocks live in separate closures.** Helpers published by
  one appended IIFE are not visible to a later one as a bare binding; publish on
  the React namespace *and* `window`, read back with a fallback, and keep a
  self-contained element-descriptor builder so the feature renders either way.
- **After 2+ failed syntax patch attempts, purge and re-inject from a script
  that edits the file in ONE pass.** Repeated in-place edits leave a broken
  fragment that later edits build on.

## 4e. Wheel gesture steals scroll from panels ("scroll pindah tab")

Island/pill apps map wheel delta to tab switching in one handler
(`const Ev=c=>{... Ms(dir?1:-1)}`, registered as `onWheel` on the shell root).
Symptoms: scrolling inside a list switches tabs instead. Fix in the handler, not
by removing it:

1. **Resolve the real scroll container at event time.** Do not rely on a
   hardcoded selector list of the app's scroll classes — walk `parentElement` up
to ~14 levels and test `getComputedStyle(n).overflowY/X` plus
   `scrollHeight > clientHeight + 2`. That catches appended/new panels
   (AI tab, custom lists) without naming them.
2. **If the container can still scroll in that direction, return without
   switching** — and do NOT call `preventDefault()`. React attaches `onWheel` at
   the root as a **passive** listener, so `preventDefault` throws
   "Unable to preventDefault inside passive event listener invocation" on every
   tick and native scrolling never happens. Returning silently lets the browser
   scroll the panel itself.
3. **Only switch tabs when the gesture is unambiguous**: horizontal-dominant
   delta, or explicit `altKey`/`metaKey`. A vertical wheel with no scrollable
   ancestor should be ignored, not hijacked.
4. Give the new panel's scroll box `overscrollBehavior:"contain"` so the wheel
does not chain to the shell.

## 4f. Task reminders (timer + sound + popup) in a bundled task list

The task list in these bundles is `useState(JSON.parse(localStorage.tasks))`
holding **plain strings**, with `localStorage.setItem("tasks",JSON.stringify(Un))`
in a `useEffect`. To add due-times you must migrate in three places at once or the
list silently breaks:

1. **State initialiser** — map legacy strings to objects
   (`typeof t==="string" ? {text:t,dueAt:0,notified:0} : {...}`). Without this,
   every existing task renders as `undefined`.
2. **Row render** — the row prints `children:c`; change to
   `children:[c.text?c.text:c, chip]` and the React key to `` `task-${c.text||c}` ``.
3. **Persist effect** — the app's own `JSON.stringify(Un)` **overwrites the whole
   array**, wiping a `notified` flag a separate reminder loop just wrote. Merge
   on write: read the current store, carry over the max `notified` for matching
   `(text,dueAt)` pairs, then save.

Reminder loop (self-contained IIFE appended to the renderer bundle):

- Tick `setInterval(...,1000)` inside a component, and call `tickOnce()` **inside
  the interval too** — a `useEffect` that only runs on a state bump reads stale
  localStorage and never fires.
- Due flag semantics: `notified===0` = pending, `2` = warned at ≤5 min, `1` = fired.
  Test `notified!==1` for the due branch so a 5-minute warning can still escalate.
- **Bump the AudioContext on first gesture** (`pointerdown`/`keydown`, once) or
  Chromium suspends it and the first chime is silent.
- Mount via a second `createRoot` on a detached host `<div>` appended to `body`,
  re-mounted on an interval so it survives re-renders.

**The React handle trap:** the bundle's `s3` is the **react-dom** export
(`createRoot`, `hydrateRoot`, `version`) — it has **no** `createElement` and no
hooks. Hooks live on the separate `m` (react) binding in module scope. Publish
both (`window.__QP_REACT__ = R /* react */; window.__QP_ROOT__ = s3 /* dom */`),
build elements with `R.createElement`, and mount with `s3.createRoot`. Passing
`m` where dom is expected throws `createElement is not a function`.

**Popup click-through:** the shell runs `setIgnoreMouseEvents(true)`. When the
popup opens call `setIgnoreMouseEvents(false,true)`; when the last action
completes, only restore `true` if the cursor is **not** over a popup element
(`document.elementFromPoint(lastX,lastY)`), otherwise the button under the
cursor stops responding mid-click.

**Verify through CDP, not by eye:** launch with `--remote-debugging-port=9333`,
connect with `ws`, seed `localStorage.tasks` with a due time 4 s out, wait, and
assert `host.innerText` plus the button labels. The island's tab state is a
React hook you can drive from the fiber: find the component with
`f.type.name`, walk `memoizedState`/`next`, and `hook.queue.dispatch([8,1])` to
force a tab — clicking the pill via synthetic mouse events does **not** resize
the window, so the tab UI never mounts.

**Trigger the notch banner, don't draw a second one.** The island already renders
an incoming-notification banner whose width/height come from `w0=!!(Se&&n!=="large")`
(`Ov=w0?420:...`, `Iv=w0?...`). Expose the setter instead of building a parallel UI:
the notification state is `[Se,ki]=m.useState(null)` and the mode setter is `i`
(both inside the big root component). Inject one expression right after that
`useState` line: `__qpX=(window.__QP_NOTIFY__=ki, window.__QP_SETMODE__=i, 1)`.
Assignments inside a comma expression are legal in the argument list, so this
needs no extra statement — a `function(){...}` declaration there breaks parsing.
Then `__QP_NOTIFY__({id, appName, title, body, priority:"high"})` + `__QP_SETMODE__("quick")`
shows the native notch banner (window resizes itself); `__QP_NOTIF_CLOSE__()`
(`ki(null)` + `i("still")`) collapses it back to the pill.

**Verify the shell actually resized.** `shell.getBoundingClientRect()` must change
from `170x40` to `~420x89` when the banner shows, and back to `170x40` after
closing — innerText alone can come from the detached popup host and proves
nothing.

**Never let an overlay card outlive the cursor.** A `setIgnoreMouseEvents` toggle
driven only by "is a popup open" creates a trap: once the popup is open the whole
window swallows clicks, and if the card stays up the user cannot click anything
underneath it. Track the pointer (`mousemove` capture, store clientX/Y), tag the
popup root and chip with `data-qp-*` attributes, and recompute
`setIgnore(!overPopup && !overChip)` on every pointer move **and** on an ~800 ms
tick so it survives re-renders. Guard the IPC with a cached last-state so it is
not spammed every frame.

Popup lifetime must be bounded by three independent exits, or it becomes
permanent furniture: an explicit `×` close button, an action button
(Tunda/Selesai), and a time-based expiry (`Date.now() - dueAt > 60000` skips the
card entirely, while the chip keeps showing the overdue task). Keep a
`__qpDismissed` map keyed by `text|dueAt` so a dismissed card never re-appears
from the next render tick.

**Prove sound at the OS layer, not in JS.** An `AudioContext` reporting
`state:"running"` and an `AnalyserNode` tapped onto `ctx.destination` prove
nothing — both can read fine while the user hears silence, and a
`createOscillator` counter only proves the code ran. The app's own mixer bridge
is the ground truth: `await window.electronAPI.audioMixer.getSessions()` returns
per-process `{volume, isMuted, peak}` plus `masterVolume`/`isMuted`. Poll `peak`
while the cue plays; a max around 0.15–0.30 means it reached the Windows audio
session. This is also how you distinguish "sound disabled" from "sound too
quiet" — check `masterVolume` first (a user sitting at 0.44 will hear a
0.15-peak cue as very faint).

**When the bundle is rebuilt, previously injected blocks vanish silently.** A
regenerated renderer can drop an earlier appended IIFE (the app's own
notification chime) while the new feature still calls it — the call site is a
`window.__X__ && window.__X__(...)` guard, so it fails silently forever. Before
patching a bundle you did not just create, grep for every `window.__QP_*` symbol
the existing code calls and confirm each has a definition; keep the old injected
blocks in a file (`qp_beep.js` etc.) and re-append them in dependency order
(definitions before the block that calls them).

## 4e. Wheel gesture steals scroll

Symptom: scrolling inside a list switches tabs instead.

**Root cause is usually the accumulator, not the scroll detection.** These
bundles accumulate `Ts.current += deltaY` and fire the tab switch at
`Math.abs(Ts.current) >= 30`. A guard of the form
`if(!(horizontal||altKey||metaKey)) return;` placed *after* the scroll-container
check still leaks: a single vertical notch of 120 px accumulates past the
threshold on its own, and a leftover accumulator from a previous gesture fires
it even when the current event has `deltaX === 0`.

Correct shape — prove horizontal intent before switching, and reset per gesture:

```js
const Ev=c=>{
  if(al.current||ms)return;
  const dy=c.deltaY||0, dx=c.deltaX||0;
  const adx=Math.abs(dx), ady=Math.abs(dy);
  const force=!!(c.altKey||c.metaKey||c.ctrlKey);
  const now=Date.now();
  if(now-(Ev._t||0)>240){Ev._hx=0;Ev._hy=0}   // new gesture window
  Ev._t=now;
  if(!force){
    const sc=QP_findScroll(c.target);
    if(sc){
      if(sc.canY){
        const top=sc.el.scrollTop<=1, bottom=sc.el.scrollTop+sc.el.clientHeight>=sc.el.scrollHeight-1;
        if((dy>0&&!bottom)||(dy<0&&!top))return;  // let the container scroll
      }
      if(sc.canX&&adx>ady)return;
    }
    Ev._hx=(Ev._hx||0)+adx; Ev._hy=(Ev._hy||0)+ady;
    if(ady>=adx*0.8){Ev._hx=0;return}          // vertical-dominant: never switch
    if(Ev._hx<140)return;                      // require real horizontal travel
    if(Ev._hx<Ev._hy*2.5)return;
  }
  ...switch tab...
}
```

`QP_findScroll(el)` walks up to 14 parents testing
`overflowY/X in {auto,scroll,overlay}` and `scrollHeight > clientHeight+2`;
returning a container means the event belongs to it.

Verify with CDP by dispatching `Input.dispatchMouseEvent` `type:"mouseWheel"`:
`deltaY` only must leave the tab unchanged, `deltaX` must switch it, and a
wheel over an `overflow-y:auto` probe element must raise its `scrollTop`.
Test at the container's top and bottom edges too — the boundary is where the
original leak fires.

## 4e-bis. Overlay mouse pass-through kills all input

Symptom: window stops responding to clicks *and* wheel everywhere.

If a helper overlay calls `setIgnoreMouseEvents(true, {forward:true})` on every
mousemove based on a hit-test, a stale hit-test result (element removed, rect
measured before layout, cursor coordinates never initialised) latches the whole
window into pass-through. Rules:

- Only ever call `setIgnoreMouseEvents(false)` when the overlay is genuinely
  mounted, and never re-arm `true` from a polling loop.
- Prefer leaving the window interactive and making the overlay
  `pointer-events:none` instead of toggling OS-level ignore.
- Grep the renderer for `setIgnoreMouseEvents` — the app's own `Qe()` callback
  dedupes via `gu.current`, so a helper calling the IPC directly bypasses that
  dedupe and can fight the app's state machine.

## 4g. Drag & drop into a tab inside a frameless always-on-top window

A drop handler on the tab container only fires if the OS lets the window receive
the drag. Three things break it silently:

1. `setIgnoreMouseEvents(true)` on the window — drops go to the window beneath.
   The tab must own the window while a drag is over it.
2. No `e.preventDefault()` on **dragover** — the browser then never fires `drop`.
   Set `dropEffect = "copy"` in the same handler.
3. `e.dataTransfer.files` is empty for text/URL drags — fall back to
   `getData("text/plain")`.

Resolve a dropped `File` to a real path with `webUtils.getPathForFile(file)`
exposed through preload — `file.path` is gone in Electron 32+. Read the file in
the **main** process behind an IPC handler (`ai:attach`), not the renderer: the
renderer has no `fs`, and main can apply the root allow-list, size caps and
binary sniffing (NUL byte in the first 8 KB) in one place.

## 4h. Per-tab module store instead of component state

Injected tabs get unmounted whenever the user switches away, so `useState`
attachments die mid-composition and any `window.__HOOK__` registered inside the
component points at a stale closure after remount. Fix with a module-scope
store plus a subscriber list:

```js
var S = (window.__S__ = window.__S__ || { list: [], subs: [], v: 0 });
function emit(){ S.v++; S.subs.slice().forEach(f => { try { f(S.v) } catch(e){} }); }
// in the component:
m.useEffect(() => { S.subs.push(fn); return () => { /* splice */ }; }, []);
```

Register the debug hook during render (not in `useEffect`) so the newest mounted
instance always owns it, and make every action read `S.list` rather than a
captured array. Persist to `localStorage` inside the promise callback, not only
in a `useEffect`, or a remount during the request loses the answer.

## 4i. Context budget for a chat tab

Cap three separate things — stored count, per-message size, and the bytes
eventually sent — and surface the third as a meter so the user can see the trim:

```js
function trimHistory(list){
  const out = []; let used = 0;
  for (let i = list.length - 1; i >= 0; i--) {
    const cost = String(list[i].content||"").length + 8;
    if (out.length && used + cost > BUDGET) break;   // newest-first, keep the tail
    out.unshift({ role: list[i].role, content: String(list[i].content||"") });
    used += cost;
  }
  return { list: out, used, dropped: list.length - out.length };
}
```

Also cap tool-result payloads sent back to the model (`JSON.stringify(out).slice(0, 12000)`) —
otherwise one folder listing blows the whole window.

## 4j. Message list affordances (delete / clear / search)

Per-message delete needs the **original index**, not the render index — filtering
or reversing the list otherwise deletes the wrong bubble. Map to `{x, i}` pairs
and pass `i` through to the handler; render keys stay on the filtered index.

Clear should be undoable: snapshot the list into a buffer with an 8 s timer and
render an inline toast with an *Urungkan* button, instead of a modal confirm.
A confirm dialog on a 135 px island is unusable; an undo strip is not.

Search is a header toggle that reveals one input and filters the array in the
render pass. Give it:

- a match counter `shown/total` next to the input
- a highlight class on each hit bubble
- an empty-state row when nothing matches (otherwise the pane looks broken)
- `Escape` clears the query and closes the bar

Do the filtering with `String(content).toLowerCase().indexOf(ql) >= 0` — no regex,
so user input can never throw.

## 4k. Collapse-on-Escape and overlay dismissal

Users ask for `Esc` to shrink the island back to a notch after a hotkey expanded
it. Route one capture-phase `keydown` listener through a priority chain: focused
input → blur only; popup card open → dismiss it; notch banner up → close it;
otherwise `SETMODE("still")`. Expose the current mode too (`__QP_GETMODE__`) —
without a getter you cannot tell whether the island is expanded, and Esc then
collapses an already-collapsed pill.

**`document.activeElement` is not the focused input by the time a capture
listener runs.** React/Chromium has already moved focus to `BODY`, while
`ev.target` still points at the `INPUT`. Checking only `activeElement` makes
`Esc` while typing collapse the whole island — the bug looks like "Esc is too
aggressive". Test **both** and blur whichever is an `INPUT`/`TEXTAREA`/`SELECT`
/`contentEditable`:

```js
var cand = [ev.target, document.activeElement];
for (var i = 0; i < cand.length; i++) {
  var t = cand[i];
  if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || (t && t.isContentEditable)) {
    try { t.blur(); } catch (e) {}
    return;                      // do NOT collapse
  }
}
```

Verify over CDP with `Input.dispatchKeyEvent` (`key:"Escape"`,
`windowsVirtualKeyCode:27`): focus an input, press Esc, assert mode is unchanged
and `activeElement.tagName === "BODY"`; press again and assert
`170x40`. Check the banner path separately by firing `__QP_NOTIFY__` first.

## 4l. Background image: remote URL *and* local file

The bundled appearance setting is one string in `localStorage` interpolated
straight into `backgroundImage:\`url('${Vn}')\`` on the island root. That breaks
for anything that is not already a URL, so add a normalizer and call it at the
interpolation site — never store a transformed value, or the settings field shows
something the user did not type.

```js
window.__QP_BGURL__ = function(v){
  var s = String(v == null ? "" : v).trim();
  if (!s || s === "none") return "none";
  if (s.indexOf("imgurl=") > -1) {                       // Google Images result page
    try { var d = decodeURIComponent(s.split("imgurl=")[1].split("&")[0]);
          if (/^https?:/i.test(d)) return d; } catch (e) {}
  }
  if (/^(https?:|data:|file:)/i.test(s)) return s;
  if (/^[a-zA-Z]:[\\/]/.test(s) || s.indexOf("\\\\") === 0)   // C:\path\foto.jpg
    return "file:///" + encodeURI(s.replace(/\\/g, "/"))
             .replace(/#/g, "%23").replace(/\?/g, "%3F");
  return s;
};
```

Rules that cost time here:

- **A pasted Google Images link is a search page, not an image.** Users paste
  `google.com/imgres?...imgurl=<encoded>` and report "the feature does not work".
  Extracting `imgurl=` is the fix; also validate with `new Image().onerror` and
  paint the preview border red so a bad URL fails loudly instead of silently.
- **Local files need main-process help.** Expose `ipcMain.handle("bg:pick", …)`
  using `dialog.showOpenDialog` + `fs.readFileSync(...).toString("base64")` and
  return a `data:` URL, plus a compact `file:///` fallback. The renderer cannot
  read disk, and `file://` from a `file://`-loaded page does load (no CSP
  block), but a `data:` URL survives app restarts without the file being
  reachable at the same path.
- **A picker that only writes `localStorage` repaints nothing.** The value lives
  in React state: after the IPC returns, also
  `window.dispatchEvent(new CustomEvent("qp-bg-changed", {detail:p}))` and
  subscribe with a `useEffect` that calls the setter. Without this the picker
  "works" (file stored) and the island stays blank.
- **`data:` URLs blow the localStorage quota on big photos.** ~1.4 MB base64
  stores fine (quota probes to 7 MB in this runtime), but a 5 MB photo does not.
  Wrap `setItem` in try/catch and fall back to the `file:///` URL the main
  process also returned.
- **A theme switch can wipe the image.** These apps reset `bg-image` to `"none"`
  when the user selects an "invisible"/transparent theme — if the user reports a
  vanishing background, check the theme branch before hunting a storage bug.
- **Check the settings sub-tab, not the tab id.** The appearance row lives under
  a settings *sub-tab* (`Appearance`), so `setTab(9)` alone shows General and the
  field looks missing. Click the sub-tab label, and `scrollIntoView` the row
  before screenshotting — it sits below the fold.

## 4m. Shipping the patched app (secrets, rebrand, publish, distribute)

When the ask moves from "change this" to "publish this" or "my friend wants to
install it", read [references/shipping-a-patched-app.md](references/shipping-a-patched-app.md).
It carries the rebrand checklist, the node_modules-strip recipe (62 MB → 5.6 MB),
the auto-updater kill, the API-key containment rules, the pre-publish audit
script, and the portable-zip build (section 8). Non-negotiables, because getting
these wrong leaks the user's key or ships someone else's updater:

- **Never let the key reach the renderer.** `getConfig` returns `hasKey` and a
  mask, never the value; writes go through a separate `setConfig` IPC that the
  main process persists. Verify by scanning the live DOM and `localStorage` for
  the key fragment, not by reading the code.
- **Mask with dots only.** Showing `abcd••••wxyz` still leaks four real
  characters into screenshots and logs. `"•".repeat(...)` with no slice.
- **Never render an absolute user path in the UI.** `C:\Users\<realname>\…` in a
  settings footer ends up in every README screenshot. Print
  `%APPDATA%\<App>\ai-config.json` instead.
- **The bundle ships with someone else's auto-updater.** Grep `manifestUrls` /
  `checkForUpdates` before publishing — the original author's GitHub/R2 manifest
  will overwrite the patched build with an upstream release. Empty the array and
  early-return `{status:"disabled"}`. Also delete `resources/app-update.yml` from
  any folder you hand out — it survives outside the asar and re-points the
  updater at the upstream repo.
- **Delete the legacy-userData fallback in the release build.** The migration
  path that rescues the developer's key after a `productName` rename will adopt
  that same key on every machine that ever ran the old app. One path only when
  shipping.
- **A repo is not a deliverable.** Source + scripts still need Node/Electron on
  the user's machine. Build a portable zip (copy the install dir, trim locales
  and `app.asar.bak`, swap in the slim asar) or an NSIS installer, and verify it
  with a clean-profile launch asserting `hasKey:false`.
- **An NSIS installer is a 40-second build, not a rebuild.** Wrap the finished
  portable folder with `electron-builder --win nsis --prepackaged appdir`; it
  needs a manual `electronVersion:` in the config, `rcedit` on the staged exe
  before wrapping (the copied exe still carries the original author's
  `ProductName`/`CompanyName`), and a real `/S` install → launch → `/S` uninstall
  test. Recipe and assertions in
  [references/shipping-a-patched-app.md](references/shipping-a-patched-app.md) §8.
- **An app icon is three surfaces, not one file.** The Win32 resource (Explorer,
  shortcut, taskbar, Properties) needs `rcedit` on the staged exe **before** the
  installer is wrapped; the NSIS installer/uninstaller need
  `win.icon` + `nsis.installerIcon` + `nsis.uninstallerIcon`; and the window icon
  the app paints itself lives at `src/assets/icons/icon.<ico|png>` **inside the
  asar**, so a file dropped next to the exe changes nothing. A logo delivered as
  flat RGB needs its background rebuilt into real alpha first — a plain
  PNG-to-ICO conversion ships an opaque box. Recipe, alpha math, and the
  `ExtractAssociatedIcon` check that proves corners are transparent:
  [references/app-icon-and-installer-branding.md](references/app-icon-and-installer-branding.md).
- **Verify the exact file you hand over.** After a rebuild, copy the new artifact
  into the delivery folder *first*, then install and test from that path.
  Testing a stale copy left in the delivery folder produces the old behaviour and
  reads as "the change did not apply", costing a whole rebuild to disprove.
- **Do not trim `dxcompiler.dll`, `dxil.dll`, `vk_swiftshader.dll`, or
  `LICENSES.chromium.html`** to save ~48 MB — the DLLs are the GPU fallback
  (black screen on old drivers) and the licence file is a distribution
  requirement. Trim `locales/` and `app.asar.bak` instead.

### Re-pointing the updater at the user's own repo (release flow)

The bundled updater reads one JSON manifest and needs nothing else:

```json
{ "version": "1.0.2", "name": "...", "changelog": ["..."],
  "platforms": { "win32-x64": { "url": "<release asset url>",
                                "sha256": "<hex>", "size": <bytes>,
                                "installerType": "nsis" } } }
```

Set `const Ge=["https://raw.githubusercontent.com/<user>/<repo>/main/version.json"]`
in `main.js` (it was emptied to disable the third-party updater). Getter key is
`` `win32-${process.arch}` ``, so `win32-x64` is the one that counts. Release flow:

1. Bump the version in **three** places: repo `package.json`, `app/package.json`
   (this is what `getAppVersion()` and the installed app report — miss it and the
   app keeps offering the update it is already running), and `version.json`.
2. Repack the asar, copy into the portable folder *and* the installer `appdir`.
3. `electron-builder --win nsis --prepackaged appdir --config electron-builder.yml`.
4. `gh release create vX.Y.Z <exe> <zip>` — upload first, then read the asset's
   `digest`/`size` from `gh release view --json assets`; do **not** copy the
   numbers from a local `sha256sum` of a file you might rebuild again.
5. Put that digest in `version.json`, commit, push.

**`?_t=<timestamp>` does not defeat raw.githubusercontent.com's CDN.** The
updater already appends a cache-buster, yet the old manifest is served for
~2-3 minutes after a push (measured: forward 1.5 min, revert 2.5 min). Never
debug a "manifest change ignored" report as a code bug before re-fetching the
raw URL yourself; verify the commit really landed with
`git show origin/main:version.json` (immediate) versus `curl` the raw URL
(delayed) to prove it is propagation, not a failed push.

Prove the whole pipeline by publishing a throwaway higher version pointing at an
existing asset, then from the app: `checkForUpdates()` → `available`,
`startUpdateDownload()` → resolves with `filePath`. A resolved promise means the
SHA-256 check passed (a mismatch throws). Confirm the downloaded file is
byte-identical to the local installer, delete it, and revert `version.json` in
its own commit.

## 4n. Global hotkeys die when two builds of the app run side by side

Symptom: the user says a shortcut "does nothing" — often the exact shortcut the
bundle's own map defines (`6:"Alt+G"`), while a tab can still be reached by
clicking. `globalShortcut.register()` is per-machine, not per-process: **Windows
gives a combo to exactly one registrant and lets every other `register()` call
return false silently.** A portable copy plus an older installed copy both
running means the one that started first owns every hotkey, and the second one's
tabs are unreachable by keyboard while its UI renders fine.

Diagnose from the app's own log first — `%APPDATA%\<app>\*.log` is the ground
truth, not the process list:

```
grep -a -i "shortcut" "$APPDATA/<app>/<app>.log" | tail -40
```

- `Shortcut OK: Alt+G -> tab 6` followed ~1s later by
  `Global shortcut conflict/in-use for Alt+G (tab 6)` on the *same run* means
two builds are fighting; the loser logged the conflict.
- All combos conflicting, in map order, in one burst = a whole second instance
  grabbed them. One or two conflicting = a foreign app owns that combo.

Confirm with paths, since `ProcessName` is identical for both installs:
`Get-Process <Name> | ForEach-Object { "{0}  {1}" -f $_.Id, $_.Path }`. Write that
to a `.ps1` and run it with `-File` — a `$_.` inside a `-Command` string gets
eaten by git-bash. Two distinct parent paths = two builds; a single path with ~5
rows is one Electron app (main + renderer + GPU + utility) and is normal.

Fixes, in the order to offer them:

1. **One build only.** Kill the other process *and* remove it from startup, or it
   comes back and re-steals the combos on next login. Say which exe path to keep.
2. **Distinct combos** if the user wants both: change the ported build's map to
   unmapped keys (`Alt+F6`), so the older install cannot collide.
3. **Bypass the hotkey entirely** to prove the tab itself is healthy — these
   bundles often expose a debug setter (`window.__QP_SETTAB__(6)`,
   `window.__QP_GETTAB__()`). Inject via DevTools/CDP. If the tab renders, the
   feature is fine and only shortcut delivery was broken; report it that way
   instead of hunting storage or repacking the asar.

Never conclude "the feature was removed" from "the shortcut does nothing" —
those are unrelated layers, and the log distinguishes them in one command.

### Retiring the rival install, not just killing it

Killing processes only holds until the next login — the loser relaunches itself
(its own `Run` entry, a squirrel-style `electron.app.<Name>` key, a Start Menu
shortcut) and re-steals every combo. Retire it completely:

1. Kill every matching process (`Get-Process -Name '<A>','<B>' | Stop-Process -Force`).
2. Run its own uninstaller silently — NSIS accepts `/S`:
   `Start-Process '<dir>\Uninstall <App>.exe' -ArgumentList '/currentuser','/S' -Wait -PassThru`.
   Exit code 0 with the folder gone is the success signal; a leftover folder
   means the uninstaller no-op'd, so `Remove-Item -Recurse -Force` it.
3. Remove the Uninstall registry key (`HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*`
   matched on `DisplayName`) — otherwise Apps & Features keeps listing a ghost.
4. Remove `Run` entries for **both** names. The ported build often registers
   its own (`id.<domain>.app`) next to the original's; delete both and tell the
   user, since autostart is now their choice, not the leftovers'.
5. Leave `%APPDATA%\<OldApp>` alone unless asked — it is user data, not a program.

Verify by re-reading the same three sources (process list, Uninstall key,
install dir) rather than trusting the uninstaller's exit code alone.

## 4o-bis. "Cuaca tidak sesuai" — sumber data, bukan kode

Symptom: widget cuaca menampilkan angka yang tidak cocok dengan BMKG/Google.
Diagnose the **source**, not the render: fetch every provider the bundle uses and
compare numbers side by side before touching anything.

Real measurement (Jakarta, same minute):

| Sumber | Suhu | Catatan |
|---|---|---|
| `api.weatherapi.com` (key bawaan) | 31.8 °C | geocode `"Jakarta Utara"` → **Sukabumi Utara** (kecamatan lain) |
| `wttr.in` | 31 °C | agregator, sering meleset |
| **BMKG** (adm4) | **27 °C, 81 %, Hujan Ringan** | otoritatif untuk Indonesia |
| `api.open-meteo.com` (lat/lon) | 27.9 °C | cocok dengan BMKG |

Two root causes, both common:

1. **City-string lookup mis-geocodes.** `q=Jakarta Utara, Indonesia` returns a
different district than the user's actual position. Always prefer coordinates.
2. **A third-party API key baked into the bundle** (`key=<author's key>`) is a
   liability: it expires, gets rate-limited, and it ships in your public repo.

Fix shape: BMKG first for Indonesia, open-meteo as the coordinate-based global
fallback. Drop the string-based providers entirely.

```text
lat/lon -> BMKG (authoritative, per-village)     -> ok? pakai
        -> gagal / di luar Indonesia
        -> open-meteo (lat/lon, model global)     -> ok? pakai
```

**BMKG needs an `adm4` village code, not coordinates.** Resolve it by walking
`wilayah.id` down the administrative chain from a Nominatim reverse geocode:

```
/reverse?format=json&zoom=16&addressdetails=1&lat=&lon=   -> address{}
/api/provinces.json                                       -> code (2 digit)
/api/regencies/<prov>.json                                -> code (xx.yy)
/api/districts/<reg>.json                                 -> code (xx.yy.zz)
/api/villages/<dis>.json                                  -> adm4 (xx.yy.zz.wwww)
https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=<adm4>  -> data[0].cuaca[][]
```

Matching traps that cost real debugging time:

- **User-Agent is mandatory** on Nominatim; without it the response is refused.
  `accept-language=id` makes `state` come back as the ISO code (`ID-JK`) instead
  of a name — drop the param and keep an `ISO3166-2-lvl4` → province-name map.
- **Indonesian address fields do not line up with BPS levels.** For Surabaya
  Nominatim returns `municipality:"Genteng"` (that is the *kecamatan*) and
  `city:"Surabaya"` (the *kota*). Include `municipality` in the district
  candidate list or the lookup fails with an empty district name.
- **Score candidates, do not equality-match.** Strip the noise words (`kota`,
  `kabupaten`, `administrasi`, `provinsi`, `daerah`, `khusus`, `ibukota`) from
  both sides, then score `sharedTokens / min(len)` — `"Daerah Khusus Ibukota
  Jakarta"` vs `"DKI Jakarta"` collapses to `jakarta` vs `dki jakarta` = 1.0.
  Feed several address fields as candidates and keep the best across all.
- **`data[0].cuaca` is an array of arrays.** Flatten, then pick the slot whose
  `datetime` (UTC, `...Z`) is nearest `Date.now()`. Fields: `t` (°C), `hu` (%)
  `ws` (km/h), `weather_desc` (Indonesian), `weather_desc_en`.
- **Cross-check the answer against the raw BMKG payload** before reporting. An
exact match on `t`/`hu`/`ws`/`weather_desc` is the only proof the chain resolved
to the right village.

open-meteo needs no key; map its `weather_code` to text yourself (WMO: 0 Cerah,
2 Berawan, 3 Mendung, 61 Hujan Ringan, 63 Hujan, 65 Hujan Lebat, 95 Badai Petir).
Its geocoding endpoint (`/v1/search?name=`) covers the "no coordinates yet" case.

Also remember the **unit conversion moves**: if the old code picked `temp_c` vs
`temp_f` at fetch time, the replacement returns Celsius only — convert at the
call site (`unit === "f" ? c*9/5+32 : c`) or every Fahrenheit user sees Celsius.

## 4o-ter. Electron has no working `navigator.geolocation`

Symptom: `getCurrentPosition` fails with
`code=2 Failed to query location from network service`, and the DevTools console
shows `Network location provider at 'https://www.googleapis.com/' : Returned
error code 403`.

Cause: Chromium resolves coordinates through a Google Geolocation API key that
is compiled into **Chrome**, not into Electron. `permissions.query({name:"geolocation"})`
returns `granted`, `setPermissionRequestHandler`/`setPermissionCheckHandler` and
`--enable-features=WindowsLocationProvider` change nothing — there is simply no
provider. Do not spend time on permission plumbing.

Working route: **WinRT `Windows.Devices.Geolocation.Geolocator` via PowerShell**,
called from the main process. Returns real WiFi/cell positioning with accuracy in
metres, and honours the Windows location privacy setting.

```powershell
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Devices.Geolocation.Geolocator, Windows.Devices.Geolocation, ContentType=WindowsRuntime]
$null=[Windows.Foundation.IAsyncOperation`1, Windows.Foundation, ContentType=WindowsRuntime]
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
$g=New-Object Windows.Devices.Geolocation.Geolocator
$g.DesiredAccuracy=[Windows.Devices.Geolocation.PositionAccuracy]::Default
$op=$g.GetGeopositionAsync()
$t=$asTask.MakeGenericMethod([Windows.Devices.Geolocation.Geoposition]).Invoke($null,@($op))
$t.Wait(15000)|Out-Null
$c=$t.Result.Coordinate
Write-Output ($c.Point.Position.Latitude.ToString()+';'+$c.Point.Position.Longitude.ToString()+';'+$c.Accuracy.ToString())
```

Bash quoting trap: the generic type literal ``IAsyncOperation`1`` contains a
backtick, so build the script as a JS array joined with `\n` and pass it through
`execFile("powershell.exe", ["-NoProfile","-ExecutionPolicy","Bypass","-Command",ps])`
— a single heredoc string in bash eats the backtick as a command substitution.

Diagnose the OS side before blaming the code:
`Get-Service lfsvc` must be `Running`, and
`HKLM:\...\CapabilityAccessManager\ConsentStore\location` must read `Allow`.
An entry under `...\ConsentStore\location\NonPackaged\C:#<path>` appears only
*after* the first successful request, so its absence just means "never asked".

**Refresh after a location change.** The weather `useEffect` runs on mount plus a
10-minute interval; writing new coordinates therefore does nothing visible for up
to ten minutes. Dispatch an event from the picker and subscribe inside the same
effect:

```js
const onLocationChanged = () => { getWeather(); };
window.addEventListener("qp-location-changed", onLocationChanged);
// cleanup: removeEventListener + clearInterval
```

## 4o. A renamed exe still carries the OLD app's identity

Symptom: the user rebranded the app, but a UI surface still shows the old name.
Copying `<Old>.exe` to `<New>.exe` — or repacking the asar under a new
`productName` — does **not** touch the Win32 version resource inside the
executable. `(Get-Item $exe).VersionInfo` keeps reporting
`FileDescription`/`ProductName`/`InternalName`/`CompanyName` of the original,
and any feature that reads *the executable's* name rather than the app's
reports the old brand forever.

Check what the surface actually reads before repacking anything:

- **Audio-session / mixer surfaces read the process image name.** Prove it by
driving the app's own helper directly instead of guessing — these bundles ship
an `audio-helper.exe` that talks JSON lines over stdio:
  `{"id":1,"cmd":"listSessions"}` → `{"sessions":[{processName,displayName,exePath,processId,…}]}`.
  Real output showed `processName:"Hermes"` for a differently-branded exe,
  confirming the field is the file name, not `productName`. Alt command names
  (`getSessions`) work too; a wrong one returns
  `Unknown command '<x>'` without killing the helper.
- **Tray tooltip, window title, menu labels** read literals in `main.js` —
  those *are* fixed by an asar patch.
- **`app.getPath('userData')`** follows `app.name`/`productName`, which is why a
  renamed build silently starts with an empty profile instead of the old one.

Fix in cost order: (1) override the display string at the render site — these
bundles render `v.displayName||v.processName`, so substitute there for a
one-line, reversible patch; (2) rewrite the exe's version resource with
`rcedit`/`osslsigncode` if Properties must read correctly — run
[scripts/set-exe-metadata.js](scripts/set-exe-metadata.js)
(`node set-exe-metadata.js <exe> <icon.ico> "<Product>" "<Company>"`); (3) full rebuild from
source. Say which one you did — an override fixes the label and nothing else.

## 4o-quarter. Feasibility questions before a feature patch ("bisa ga ya?")

When the ask is "can this app do X, what would it take, what are the
requirements?" rather than "change X", the deliverable is an inventory, not code:
what the shipped bundle already carries, the 2–4 blocks still missing, the
requirements the user must satisfy, and the single fastest test path. Grep the
**source repo when the user owns it** (`<repo>/app/src`, then the `.vite/build`
copies inside the asar) and confirm each candidate by symbol, not by name:
`grep -rn "lyric\|lirik" app/src` scoring zero is what makes "pure addition, no
collision" a fact instead of a guess.

Media / now-playing territory has a full map, the lyrics-provider probe commands,
and the sizing rule in
[references/feature-planning-from-the-artifact.md](references/feature-planning-from-the-artifact.md).
The two shape decisions worth carrying into any answer:

- **Prefer wiring over building.** The bundled player pipeline
  (`get-media.ps1` → `get-system-media` → `spotifyTrack` state + a ~500 ms position
  ticker with 3 s polling) already emits the exact signal a time-synced feature
  needs. Say which exist and count lines for the delta — the answer is then
  credible, and small.
- **Never promise a third-party data source without probing it live** in the same
  session (`curl` each endpoint, report what it actually returned). A provider
  that 503s is why a fallback chain is a requirement rather than a nicety.

Do not fold a second, larger product (an in-island local player: folder scan, ID3,
audio engine) into the answer for the small one. Name it as a separate phase with
its own cost so the user chooses deliberately.

## 4p. Windows toast icons come back empty in an island/notification-reader app

Symptom: the user compares with real Windows notifications ("like a WhatsApp
notification — the WA icon shows") and in the app's notification list every entry
renders the generic fallback (bell / letter circle) even though the toasts in
Windows show proper logos.

Raw evidence first: read the app's persisted store (`notifications-store.json`
under `%APPDATA%\<app>`) — every record with `applicationIcon: ""` means the
extraction failed *before* the renderer, not a CSS/field-name bug.

Typical root cause: the bundled `get-notifications.ps1` (written to userData at
launch from a template inside `main.js`) derives a process name from the
AppUserModelId as `$appId.Split('!')[-1].Split('.')[-1]`, which collapses every
modern AUMID to garbage:

| AUMID | old derivation | reality |
|---|---|---|
| `5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App` | `App` | real process is `WhatsApp.Root` |
| `Microsoft.ScreenSketch_8wekyb3d8bbwe!App` | `App` | `ScreenSketch` |
| `Chrome.3J3JX54VC35ZP63NPKMKDSJGU4` | hash | `chrome` |
| `com.nousresearch.hermes` | `hermes` | works, if the app is running |

Fix with three layers, cached per appId inside the same PowerShell run:

1. **MSIX package logo — the reliable one, needs no running process.** For
   AUMIDs containing `!`, take the family name (`Split('!')[0]`), then
   `Get-AppxPackage -PackageFamilyName` → `Get-AppxPackageManifest` →
   `VisualElements.Square44x44Logo` → read the asset. The manifest path is
   usually a base name without scale suffix, so also glob it
   (`AppList*.png`) and prefer `scale-200` > `scale-100` > big `targetsize-*`.
   Reading inside `C:\Program Files\WindowsApps\...` works for these asset
   files (verified) even though listing the directory is restricted.
2. **Process match, smarter.** Strip a trailing `_<publisherhash>` from the
   family name, split on `.`, try segments ≥4 chars (skip
   `windows|microsoft|system|app…`), match a process whose normalized name is
   equal / substring (either direction) / shares a 6-char prefix, or whose
   `MainModule.FileName` contains the hint — the last rule is what catches
   `WhatsApp.Root` living under `WindowsApps\5319275A.WhatsAppDesktop_…\`.
3. **Exe icon** via `[System.Drawing.Icon]::ExtractAssociatedIcon` → PNG →
   `data:image/png;base64,` (add `Add-Type -AssemblyName System.Drawing`
   wrapped in try/catch; the old script called the type without loading it).

Make icons **sticky** on the Node side: keep
`notifications-icon-cache.json` in userData keyed by AppId, fill missing
`Icon` from it before `syncNotifications`, and store any newly resolved icon —
otherwise a notification whose app has since quit loses its logo on the next
sync.

Test the script standalone before repacking: generate the patched
`get-notifications.ps1` from the same template and run it directly — the JSON
it prints shows `Icon` byte counts per app (expect ~2500–3500 for real logos).
Splicing trap: when replacing the old function by slicing between
`function Get-AppIconBase64($appId) {` and a `\n}\n\ntry {` anchor, include
that `\n}` in the replaced span or the leftover brace is a PowerShell parse
error — invisible to `node --check` because the script lives inside a JS string.

## 4q. Testing a framer-motion "island" window via CDP

- The BrowserWindow is a large transparent canvas (innerWidth may read e.g.
  1536x864); the visible island is a floating `#Island` div animated by
  framer-motion (`animate:{width,height}`). Measure the DIV's rect, never
  `window.innerWidth`, when asserting sizes.
- Island size expressions re-evaluate on every render, and renders usually tick
  only while media is playing — with nothing playing there is no ticker, so a
  state flag flipped between renders leaves the island at a stale size. Make
  size-affecting flags render-readable globals and accept the one-tick delay.
- With media = null the tab renders "Nothing Playing": media control buttons
  (and injected buttons inside them) are simply absent. Assert only while a
  track is actually playing.
- Programmatic `el.click()` / `dispatchEvent` may silently fail to trigger
  React handlers in this window even when the element exists. Use CDP
  `Input.dispatchMouseEvent` (mouseMoved → mousePressed → mouseReleased) at the
  element's rect center — that goes through the browser input pipeline and
  always lands.
- To create a controllable SMTC media session for tests: launch a scratch
  Chrome (`--user-data-dir=<temp>` so it does not join the user's instance,
  `--autoplay-policy=no-user-gesture-required`) on a local page that plays an
  audio file and sets `navigator.mediaSession.metadata`. A WAV gets title/artist
  from its LIST/INFO chunk (place it BEFORE the data chunk).
- `GetCurrentSession()` prefers the user's own actively-played track: the
  user's playback keeps stealing the session, so assert `getSystemMedia()`
  immediately before each UI check instead of assuming your test session wins.

## 5. Repack and swap in

```bash
cd "$WORK"
npx --yes asar pack "$WORK" "$RES/app.asar.new"
mv "$RES/app.asar.new" "$RES/app.asar"
```

Pack from inside the extracted directory so paths stay relative.

## 5b. Verify what actually runs — packed artifact, not the tree

Answering "the app already does X" from a repo checkout is a guess until the
packed bytes say so.

- **Presence, without unpacking:** asar file contents are stored uncompressed,
  so `grep -a -c "<marker>" "$RES/app.asar"` counts a marker and
  `grep -a -o '"version": *"[0-9.]*"' "$RES/app.asar" | head -1` reads the
  shipped version straight from the blob. Use both as a before/after check.
- **Prove live == built:** `sha256sum "$RES/app.asar" "<build>/out/app.asar"` —
  equal digests mean the installed app carries exactly the repacked bytes, and
  an installer built from the same tree will too.
- **Read-only extraction with stdlib only** (no node/npx needed):
  [scripts/asar-ro.py](scripts/asar-ro.py) — the header is a uint32 LE JSON
  length at byte 12, JSON at 16, file data at `16 + len` with per-entry
  `offset`/`size` relative to that. `python scripts/asar-ro.py cat <app.asar>
  /.vite/build/main.js`.
- **Answer behaviour questions from the built bundle** (`.vite/build/*`,
  `.vite/renderer/main_window/assets/*`), never from `src/` copies that also
  sit inside the asar — they ship unused and can lag the running code.

## 6. Restart so the change is live

1. Stop every process of the app:
   `powershell.exe -NoProfile -Command "Get-Process -Name '<ProcName>' | Stop-Process -Force"`
2. Start by full path — `cmd.exe /c start "" name.exe` from git-bash can return 0
   while launching nothing:

```bash
powershell.exe -NoProfile -Command "Start-Process 'C:\...\<app>\<App>.exe'"
```

3. Verify with `tasklist | grep -i <app>` before claiming success; an Electron app
   spawns several rows. No rows = launch failed, patch is not live.

If the UI still shows old code after a confirmed relaunch, the edit is missing
from the bundle (re-check step 4 counts), not a cache issue. Stale *content* is
different: apps that persist a notification/message store under
`%APPDATA%\<app>\` replay old records, so tell the user to generate a fresh event
(or delete that store) rather than repatching.

## Notes and limits

- Typical electron-builder apps carry no code-integrity check, so a repacked
  `app.asar` loads normally. The installer is untouched; an in-app auto-update
  overwrites the patch (backup keeps the original).
- **Close the app before the swap.** `mv app.asar.new app.asar` fails with
  `Device or resource busy` while any app process holds the file. Stop by exact
  process name first (`Get-Process -Name 'Quick Pill'`), confirm with
  `tasklist | grep -i`, then move. A helper like
  `Where-Object {$_.ProcessName -like ...}` through git-bash gets its `$_`
  eaten by bash — quote the whole `-Command` argument or use `-Name`.
- **Validate syntax before swapping.** `node --check` on each patched file
  (`main.js`, `preload.js`, renderer bundle) catches a broken injection while
  the original `app.asar` is still intact. It is CommonJS-mode and will report
  false `Unexpected identifier` errors for minified `oname=/re/s` regex
  literals — trust it only for exit-0 (good) and confirm real errors with an
  acorn parse (`sourceType: "module"`, `ecmaVersion: "latest"`), which reports
  the exact byte offset. A backup copy of the pristine extracted tree (or
  `app.asar.bak`) is the recovery path when a bundle is already corrupted.
- Report honestly which named symptom the patch fixes. A string/UI patch fixes
  what it touches and does not implement a new capability — say so instead of
  implying feature parity.
