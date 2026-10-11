---
name: autojs-android-automation
category: software-development
description: "AutoJs/AutoX Android screen-automation scripts."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [AutoJs, AutoX, Android, Automation, Vision, Floaty, Bot]
    category: software-development
---

# AutoJs / AutoX Android Automation

Writing JS automation scripts for the AutoJs family (`org.autojs.autojs6`,
`org.autojs.autoxjs`, AutoX, AutoJs6) — screen-capture bots, autoclickers, tile
matchers. The API surface differs between forks, and the floaty UI has traps
that silently kill the script.

## When to Use

User asks for an Android automation script to run inside AutoJs on their phone,
or reports AutoJs errors from a script you wrote.

## Output contract (this user)

**Paste the whole file in chat every time you finish editing it.** The user asked
for this explicitly and repeatedly ("kirim sini", "kirim sini ahh kodenya setiap
selesai"). Attach it as `MEDIA:` too, but the fenced code in the reply is the
deliverable — do not answer with "udah diubah, tinggal jalanin" and a diff.
Re-paste the *complete* current file after each fix, never a fragment, so they can
copy one block into AutoJs without reconstructing anything.

Say where results landed (path + how to open it) in the same reply, and ask for
the one datum you actually need next (a toast string, a `config.json` body, a
screenshot) — not a list of questions.

**Name the ONE file to run, every time.** Diagnostic scripts accumulate fast
(`*_tap.js`, `*_diag.js`, `*_grid.js`, `*_calib.js`, `*_cek.js`, `*_capture.js`)
and the user loses track of which one is the bot. End every handover with an
explicit table — which file to run now, which are done with, which are only for a
specific failure — because "jalanin yang mana?" costs a whole round trip and is
entirely self-inflicted. When a diagnostic has served its purpose, say so and
name the condition that would bring it back.

## Fork API quirks (the big three)

These bite every time. Always wrap in fallbacks rather than picking one.

### 1. Position APIs are NOT universal — and `getLayoutParams` is not either

`setPosition` / `setX` / `setY` / `getX` / `getY` are missing in some forks, and
the call throws at runtime. The obvious Android-core fallback,
`v.getLayoutParams()`, **is also missing on some builds in the wild**
(`TypeError: getLayoutParams is not a function, it is undefined`). When a
position call throws during floaty setup you do not get a cosmetic bug — you get
the failure in quirk 4 below, because an un-positioned window falls back to the
default full-width gravity and eats every tap the bot issues.

**Put position in the XML layout.** `marginLeft` / `marginTop` (or `x` / `y`) are
resolved at inflate time by the view parser, so no runtime position API is needed
at all and no fork can be missing it:

```js
let win = floaty.rawWindow(
  <frame bg="#00000000" w="auto" h="auto">
    <button id="stop" w="120" h="120" marginLeft="0" marginTop="0"
            text="STOP" bg="#e74c3c" textColor="#ffffff" textSize="18sp"/>
  </frame>
);
```

If you still want a runtime helper for dragging, wrap it, but treat success as
optional — and never let a failed position leave a touchable window on screen:

```js
function move(v, x, y) {
  try {
    let lp = v.getLayoutParams();
    lp.leftMargin = Math.round(x);
    lp.topMargin = Math.round(y);
    v.setLayoutParams(lp);
    return true;
  } catch (e) {
    try { v.attr("marginLeft", x); v.attr("marginTop", y); return true; } catch (e2) {}
  }
  return false;
}
function pos(v) {
  try {
    let lp = v.getLayoutParams();
    return [lp.leftMargin || 0, lp.topMargin || 0];
  } catch (e) {
    try { return [Number(v.attr("marginLeft")) || 0, Number(v.attr("marginTop")) || 0]; }
    catch (e2) { return [0, 0]; }
  }
}
```

Best of all: set `marginLeft` / `marginTop` directly in the XML layout. Position
is applied at inflate time, so no runtime API is needed.

**A floaty you cannot position is a tap-eater, so do not create one.** If the
position call is unavailable, skip the on-screen button entirely
(`const FLOATY = false`) and stop on the volume keys — a headless bot that works
beats a visible button that swallows every click. Size the frame for its contents
(`w="auto" h="auto"`, or an explicit small size) and `setTouchable(false)` on any
window you are not actually using as a control.

### 2. `&` in XML attributes → `unterminated entity ref`

The floaty layout is parsed by a strict SAX parser. `&amp;` inside an attribute
value (e.g. `text="...1 &amp; 2..."`) makes it throw
`InflateException: org.xml.sax.SAXParseException: unterminated entity ref` and
`Failed to call method "floaty.rawWindow"`. The error position points at the
`text` attribute.

**Fix: never use `&` in floaty XML.** Write the word (`dan`, `and`) instead.
Do not try to escape it — the parser is inconsistent. Zero ampersands in the file.

### 3. No blocking call → script ends, floaty disappears

`floaty.rawWindow()` does not keep the script alive. When the script reaches its
last line, AutoJs exits and tears down the floaty. Symptom: "the buttons flash
and vanish after N seconds", "script finishes on its own".

**Fix: park the main thread on a sentinel flag.**

```js
let done = false;
win.go.click(() => { /* ...work... */ done = true; });
while (!done) sleep(300);          // <-- the thing that keeps floaty alive
```

Same pattern for long-running bots: run the work loop in `threads.start(...)`
and let the main thread spin on `while (state.run) sleep(200)`, so the UI stays
responsive and the kill switch actually fires.

### 4. Floaty `<frame>` size decides whether taps reach the app

Two opposite failures, one root cause — the frame's own size.

**Too small / unset** (`<frame>...</frame>`, no `w`/`h`): the frame collapses and
its children do not render or cannot be tapped, even though `rawWindow`
succeeded. Symptom: script runs, toasts fire, user reports "tombolnya ga
kelihatan".

**Full-screen** (`w="*" h="*"`): worse, and it is the trap to avoid. With
`win.setTouchable(true)`, a window spanning the display becomes a tap-absorbing
overlay — **every `click()`/`press()` the bot issues lands on the overlay instead
of the target app**, and any hit inside a button's bounds fires that button.
Symptom the user reports: "malah mencet stop sendiri" — the bot is tapping, but
nothing reaches the game.

**Rule: size the frame to its contents, not to the screen.** Put a real `w`/`h`
on the frame, `x`/`y` on the children (applied at inflate time, so no runtime
position API is needed), and park the window where the bot does not tap:

```js
win = floaty.rawWindow(
  <frame bg="#00000000" w="auto" h="auto">
    <button id="stop" w="120" h="120" marginLeft="0" marginTop="0"
            text="STOP" bg="#e74c3c" textColor="#ffffff" textSize="18sp"/>
  </frame>
);
win.setTouchable(true);
try {                                    // TOP|RIGHT corner, clear of the board
  let lp = win.getLayoutParams();
  lp.gravity = android.view.Gravity.TOP | android.view.Gravity.RIGHT;
  lp.x = 0; lp.y = 120;
  win.setLayoutParams(lp);
} catch (e) {}
```

Offer a `const FLOATY = false` escape hatch in the config block: with no on-screen
button the volume keys are the only stop, which is enough when the overlay itself
is suspect.

**Do NOT judge "is the tap landing" with an in-loop before/after pixel compare.**
This is the expensive trap: the tapped tile is *consumed and moves to a slot*, so
its origin can end up the same colour as the tile that was on it (white tile over
a white gap, dark UI over a shadow). The check then reports `0/3` while every tap
is landing perfectly — you go hunting an overlay bug that does not exist, round
after round, while the log line looks like hard evidence.

```js
// WRONG as a verdict - false negative whenever the origin pixel keeps its colour
let before = captureScreen(); tap(x, y); sleep(700); let after = captureScreen();
let moved = images.pixel(before, x|0, y|0) !== images.pixel(after, x|0, y|0);
```

**Test the tap channel ONCE, in a dedicated one-shot script, at one fixed point.**
Try each injection API in turn and sample several pixels *around* the target
(near the tapped point, which does change, not on it):

```js
function state(img) {                    // 4 sample pixels, not the tapped one
  let s = "";
  for (let dy = -30; dy <= 30; dy += 20)
    for (let dx = -30; dx <= 30; dx += 20)
      s += images.pixel(img, TX + dx, TY + dy) + "|";
  return s;
}
function cek(nama, fn) {
  log("COBA    | " + nama);              // log BEFORE the call
  let a = state(captureScreen());
  try { fn(); } catch (e) { log("  THROW:" + e); }
  sleep(800);
  log("  " + (state(captureScreen()) !== a ? "BEKERJA" : "ga ngefek") + " | " + nama);
}
```

Log **before** each call, to a file, so a hanging API shows up as a file that
stops mid-list rather than as "it just sat there". `Tap()`, `gesture()` and
`swipe()` can **hang** (not throw) on some forks — drop any that does.

Observed on one fork: `press(x,y,120)` and `click(x,y)` reach the app, `gesture`
works, `Tap()` hangs, and **`press(x,y,1)` does not register at all**. Use a press
duration of ~100–150 ms; a 1 ms tap can be issued without error and never be
delivered. Anything shorter than ~100 ms is not a valid "did tapping work" probe.

## Kill switch (mandatory for `while(true)` bots)

A bare `while(true)` has no exit. Provide **two** independent stops — the floaty
button can be covered by a notification or keyboard, the volume keys never are:

```js
const state = { run: true, why: "init" };
function stopIt(why) {
  if (!state.run) return;
  state.run = false; state.why = why;
  toast("STOP: " + why);
}
events.observeKey();
events.onKeyDown("volume_up",   () => stopIt("vol atas"));
events.onKeyDown("volume_down", () => stopIt("vol bawah"));
```

Check `state.run` inside inner loops too, not just the outer one, so a stop
mid-sequence does not wait for the remaining taps.

Also: `while (state.run && loop++ < MAX_LOOP)` — a loop counter is a cheap net
for when the user forgets to press stop.

## Print results where the user can actually see them

Two failure modes make results invisible: the toast expires before it is read,
and `Android/data` is unreachable from Windows Explorer / MTP.

- `console.show()` **after the capture, never before.** The console panel is a
  full overlay: its rows of text are perfectly periodic, so an edge profile taken
  with the panel up locks onto the *log line spacing* instead of the board, and any
  screenshot-based measurement is measured through the panel. Show it once the
  capture and the proof image are already saved.
- Log the intermediate values (`DIR`, `device.width x device.height`, the derived
  config JSON, per-step cell size). The user can screenshot the console instead of
  hunting a file.
- **Draw the numbers onto the proof PNG with `android.graphics.Paint`.** Toast
  text is transient; text baked into the saved screenshot always survives and is
  readable from a photo of the phone.

```js
let tp = new android.graphics.Paint();
tp.setColor(colors.YELLOW); tp.setTextSize(44); tp.setFakeBoldText(true);
let bp = new android.graphics.Paint(); bp.setColor(colors.BLACK); bp.setAlpha(190);
cv.drawRect(4, 4, 1250, 40 + 52 * lines.length, bp);
for (let i = 0; i < lines.length; i++) cv.drawText(lines[i], 16, 44 + i * 52, tp);
```

- Save the calibration result on **every marker release**, not only on the final
  button. If the button is mis-tapped the user still has a usable `config.json`.
- Prefer `Download/<name>` and `Pictures/<name>` in the candidate list — they stay
  visible over MTP to Windows, unlike `Android/data`. Call
  `android.media.MediaScannerConnection.scanFile(context, [path], null, null)`
  after saving so the file appears without a reboot.

### Reading the user's screenshot back

Measure it, do not eyeball it. Downscaled uploads lose the scale, so recover it
from a known feature (the rectangle the script drew), then convert to screen px.
When toast text is unreadable, run the Windows OCR route
(`image-ocr` skill) on an upscaled, contrast-normalised crop of the log area.
Log lines wrap and get truncated at the screen edge — re-derive missing fields
from the ones you got. Worked example: `sel = 111 x 117 px` with `cols/rows`
known gives `w = 111*cols`, and the marker start positions give the corners.

**When the script draws a grid overlay, the drawn LINES are the measurement.**
Threshold the overlay colour, then group runs of high-count rows/columns into
lines; `n+1` lines means `n` cells, and the spacing gives the pitch directly:

```python
rows = mask.sum(axis=1)                      # overlay px per row
hl = [mean(g) for g in groups(rows > width * 0.30)]   # horizontal lines
```

Trusting the drawn geometry `x 84..991 (w 907)` / `y 452..1672 (h 1220)` over the
text is what settles "is the box aligned": the text on such an overlay is often
tiny and OCRs to **garbage** (`periode 80x80 5x8` for a grid that is visibly 7x9)
— do not let a misread label override the lines you can count.

**Verify alignment by edge energy at each grid line, not by eye.** Compute the
edge profile of the game (not the overlay) and read the response at each line:

```python
colE = abs(np.diff(gray, axis=1)).sum(axis=0)
ratio = [colE[x-6:x+7].max() / colE.mean() for x in grid_lines_x]
```

A correct grid gives **2-6x the mean at every line** (lines land on real card
borders). Ratios near 1.0 mean the grid is offset by half a cell. This is a
one-line, purely numeric answer to "is it aligned", and it beats any amount of
staring at a downscaled screenshot.

**Cross-check the pitch from two sources.** Autocorrelation and the drawn lines
can disagree by ~3% (`135.5` vs `131`), which accumulates to ~40 px of drift over
9 rows — enough to miss the bottom row while the top is perfect. When both are
available, prefer the pitch derived from measured line positions, and only trust
autocorrelation when `per * rows` reproduces the total span.

## Wrap optional calls in try/catch

Scripts may run only once when configuring; do not let a non-essential call
abort setup. Guard `device.keepScreenOn`, `images.save`, `app.viewFile`.

## Let the user come back to the game first

A floaty appears on top of everything. Give a countdown before showing UI so the
user can switch back to the target app:

```js
const DELAY = 8;                  // 8, not 6 — the user called 6 too fast
const state = {};
toast("Buka app target — " + DELAY + " detik");
for (let i = DELAY; i > 0; i--) { toast("" + i, 800); sleep(1000); }
toast("Jangan gerak, lagi ngukur...", 2000);
// THEN create floaty / start capture
```

Create the floaty **after** the countdown, otherwise it covers the screen during
the wait and the delay is pointless. A toast countdown beats a silent `sleep` —
the user knows when to switch.

**A toast queue is not a progress bar.** `toast()` calls queue FIFO, and a
blocking measurement between them — autocorrelation across a full screenshot can
run 20–30 s — makes the whole backlog surface at once *after* the work finished.
The user sees `7..6..5` on time, then silence, then a burst, and reasonably reports
"the toast is out of sync, it hung after 5". Put a toast **before** each long
blocking step so the queue drains into a real status line, and shorten the step
rather than letting it run long:

```js
toast("Buka board — " + START_DELAY + " detik");
for (let i = START_DELAY; i > 0; i--) { toast("" + i, 800); sleep(1000); }
toast("Memindai grid... (10-30 detik)");     // fires as autoGrid() begins
if (!autoGrid()) { /* ... */ }
```

Sample the edge profile with a stride (`y += 10`, not `y += 4`): it costs nothing
in accuracy for a ~130 px period and cuts the scan from ~25 s to a few seconds.
When the user asks how long a run takes, answer in **checkpoints** (first tap,
first verdict), not one total.

**Everything measured must be captured after the switch, not before.** If the
countdown is too short the capture catches AutoJs itself, and every measurement
derived from it is garbage while looking perfectly plausible. Default to 8 s and
raise it on request — a measurement pass costs one run, a wrong measurement costs
several.

## Write path on Android 11+

`/sdcard/<name>` often fails to write on Android 11+ (scoped storage). Probe by
actually writing a file, not just `ensureDir` (which succeeds while `write`
fails):

```js
files.ensureDir(dir + "/");
let probe = files.join(dir, ".probe");
files.write(probe, "ok"); files.remove(probe);
```

Candidate order: `/sdcard/<name>` → `/sdcard/Android/data/<pkg>/files/<name>` →
`context.getExternalFilesDir(null)`. `/sdcard` is an alias for
`/storage/emulated/0`. Android 13+ blocks `Android/data` in the stock file
manager — use ZArchiver / Files by Google, or `adb pull`.

Note: `files.getSdcardPath()` and `context` only exist inside AutoJs, so a
plain Node syntax check needs the floaty XML block stripped first.

## Vision loop: read once, compare in JS

The `images` API differs between forks — `images.getSimilarity` exists in some,
is missing or has a different return range in others. Build signatures by hand
with `images.pixel` (stable everywhere): split a CROP×CROP patch into a 4×4 grid
of blocks, **average several samples inside each block**, then compare those
arrays in plain JS.

**Average inside each block — do not read one pixel per sample point.** A single
`images.pixel` per cell is ~70% sensor/JPEG noise, and that noise alone drops two
*identical* tiles to ~0.70 similarity, below any usable threshold. The matcher then
reports "no match" forever and you go hunting a grid bug that is not there. Block
averaging collapses the noise: identical tiles reach 0.96+, different tiles stay
under 0.93.

```js
const SIG_N = 4;                        // 4x4 blocks = 48 numbers
function signature(img, cx, cy) {
  let bs = Math.max(2, Math.floor(CROP / SIG_N));
  let h  = Math.floor(bs / 2);
  let x0 = Math.round(cx - CROP / 2), y0 = Math.round(cy - CROP / 2);
  let sig = [], lo = 999, hi = -1;
  for (let by = 0; by < SIG_N; by++)
    for (let bx = 0; bx < SIG_N; bx++) {
      let rr = 0, gg = 0, bb = 0, n = 0;
      for (let dy = -h; dy <= h; dy += h || 1)      // 3x3 samples per block
        for (let dx = -h; dx <= h; dx += h || 1) {
          let px = x0 + bx * bs + h + dx, py = y0 + by * bs + h + dy;
          if (px < 0 || py < 0) continue;
          let c;
          try { c = images.pixel(img, px, py); } catch (e) { continue; }
          rr += c >> 16 & 255; gg += c >> 8 & 255; bb += c & 255; n++;
        }
      if (!n) { rr = gg = bb = 0; n = 1; }
      rr /= n; gg /= n; bb /= n;
      sig.push(rr, gg, bb);
      let lum = (rr + gg + bb) / 3;
      if (lum < lo) lo = lum;
      if (lum > hi) hi = lum;
    }
  sig.flat = (hi - lo) < 22;            // uniform patch -> not a tile
  return sig;
}
function sim(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]);
  return 1 - d / (a.length * 255);   // 1.0 = identical
}
```

With block averaging, **`SIM_THRESHOLD = 0.95`** for "same icon". Calibrate that
number from the measured distribution rather than inheriting it: identical pairs
should sit ~0.96–0.98 and different pairs under ~0.93, so pick the value in the
gap. Clamp sample coords with `Math.max(0, ...)` — edge tiles produce negative
coordinates and throw.

**Reject uniform patches — they are empty slots, not tiles.** A blank area (or the
gap between tiles) has near-zero luminance spread, so it matches every other blank
area at ~1.0 and the solver confidently returns a "triple" of three empty spaces.
Flag it inside the signature builder, where the samples are already in hand:

```js
track lo/hi luminance across the 8x8 samples;
sig.flat = (hi - lo) < 22;      // uniform patch -> not a tile
```

Then skip `flat` entries as a group seed and as a group member, and log the count
every N loops: `kosong:12/63`. A large `flat` count is the signal that the region
spans emptier space than tiles — i.e. the calibration box is bigger than the
board. A solver that returns three tiles in one tidy row (`r0c0 r0c1 r0c2`) is
almost always matching background, not icons: real matches are scattered.

**`flat` is necessary but not sufficient — count how many times each signature
appears.** Background that is not *perfectly* uniform slips past the `flat` filter,
matches its twins at ~1.000, and the solver confidently returns "three empty
spaces". A signature histogram separates the two populations cleanly: a real card
appears **exactly 3×**; background appears four or more times (the margin, the
gaps between cells, the tray). The log line to look for is a histogram that is
mostly 3s.

```js
let pop = new Array(tiles.length);
for (let a = 0; a < tiles.length; a++) {
  if (tiles[a].sig.flat) { pop[a] = 99; continue; }
  for (let b = a + 1; b < tiles.length; b++) {
    if (tiles[b].sig.flat) continue;
    if (sim(tiles[a].sig, tiles[b].sig) > SIM_THRESHOLD) { pop[a]++; pop[b]++; }
  }
}
for (let i = 0; i < tiles.length; i++)
  if (pop[i] > 2 && pop[i] < 99) pop[i] = 98;   // appears 4+ times -> background
// then use `if (pop[i] >= 98) continue;` as group seed AND as group member
```

**`sim: max 1.000` in a diagnostic log is a red flag, not good news.** Real tiles
captured at slightly different sub-pixel offsets are never bit-identical; a perfect
1.000 pair is background. A bimodal distribution — median ~0.72 with a cluster at
0.999 — means the matcher is looking at two populations and picking the wrong one.

**Pick the highest-scoring group, not the first one found.** Neighbouring tiles
share background, so the first qualifying group is frequently three unrelated
neighbours. Score each candidate by its *weakest* internal similarity, plus a small
bonus for geographic spread, and take the best:

```js
let score = worst * 0.75 + Math.min(1, spread / 12) * 0.25;
if (score > bestScore) { bestScore = score; g = grp; }
```

Log the best pair score every N loops (`skor:0.973`). Silence from the solver is
ambiguous between a too-strict threshold and an empty crop; the score is not.

### Calibrate by tapping two corners, then MEASURE the pitch — never trust it

Hardcoded board coordinates are a coin flip, and so is a hand-pointed rectangle:
the user aims at two roughly-correct corners and the box ends up spanning empty
margin on one side. Every symptom of that looks like a *different* bug ("taps in
the wrong place", "taps outside the board", "matcher finds nothing"), so it costs
a round trip per wrong guess. Two markers plus a hitung button that writes
`{x, y, w, h}` to `config.json` is the **first** step, not the last word.

**Ask for two CELL CENTRES, not two box corners.** Centres are visually
unambiguous (the user drops the marker on the middle of the top-left tile and the
middle of the bottom-right tile); a box corner asks them to judge where the outer
frame ends, which is exactly the boundary they get wrong. Derive the whole grid
from the two centres — divide by `count - 1`, not `count`:

```python
perX = (x2 - x1) / (COLS - 1)        # centre-to-centre, N-1 gaps
perY = (y2 - y1) / (ROWS - 1)
x0 = x1 - perX / 2                   # back out the box origin
y0 = y1 - perY / 2
```

Two numbers from the user then replace the entire detection pass: no
`autoGrid()`, no 25 s scan, no countdown/toast desync. Ship it as a `CALIB`
constant that short-circuits detection, with `null` meaning "fall back to
auto-detect":

```js
let CALIB = { x: 90, y: 485, w: 903, h: 1178 };   // null -> autoGrid()
```

**Require the two sources to agree before trusting either.** A hand-measured
pitch and the edge-profile pitch answer the same question independently, so a
small disagreement validates both and a large one convicts one of them. Derive
the expected centre coordinates from the measured pitch and compare against the
user's numbers — under ~10 px means both are right, and the measured `y0` is
preferable because it is not eye-estimated:

```python
mine = (mx0 + mperX * 0.5, my0 + mperY * 0.5)
print("selisih", x1 - mine[0], y1 - mine[1])      # >10 px -> investigate first
```

The same cross-check catches an auto-detect that latched onto the wrong region:
when they disagree, find out which one moved, do not average them.

**Then derive the grid pitch from the image itself and reject a hand-pointed box
that disagrees with it.** Edge profile per column/row, then autocorrelation over a
sane lag window gives the cell pitch; the best phase offset aligns the grid with
the real cell boundaries:

**Autocorrelation's global maximum is NOT the cell pitch.** Artwork inside a tile
repeats too, so the in-tile motif produces a strong peak at a *sub-harmonic* of the
real pitch. Taking the tallest lag yields a grid ~1.5–2× too large, which taps the
gaps between tiles and reads as "it taps outside the board". Take the **first
prominent** peak instead, then drop multiples of it — and log every candidate with
its relative strength so the harmonic structure is visible in the log. Full
`period()` / `bestPhase()` / `snapLines()` routines, plus the three validation gates:
`references/grid-calibration.md`.

**Search the lag window above the smallest plausible pitch.** If the sub-harmonic
is inside `[lo, hi]` and outranks the true pitch, first-peak selection alone still
picks it. Set `lo` from the smallest cell the layout can have (measure roughly once
by eye, then freeze it) rather than a generic 40, and add a plausibility gate so an
absurd pitch cannot be accepted silently:

```js
function plausible(per, count, extent) {   // pitch * count must span the scan area
  if (per <= 0) return false;
  return per * count > extent * 0.45 && per * count <= extent * 1.05;
}
// perX = period(colProf, 90, 220)  -- 90, not 40: excludes the in-tile motif
if (!plausible(perX, COLS, AX1 - AX0))
  console.log("!! periode X " + perX + " tidak masuk akal untuk " + COLS + " kolom");
```

**Gate the pitch MAGNITUDE, not just the span.** `plausible()` above only checks
that `pitch × count` fills the scan area, so a pitch 25 % too large still passes and
the board silently grows past the real one — measured `per 126.6 x 164.2` gave
`h 1478` for a board that is `1179` tall. Each row then taps further off the real
grid until the bottom rows miss entirely, the board never changes, and the solver
re-taps the same dead cells forever (the log shows one `TAP rXcY …` repeated 20×).
Constrain the lag window to the physically possible range, search **one** pitch —
±4 % trial values only amplify a bad pick — and reject anything outside the range:

```js
// One card spanning ~1/7 of a 1080 px screen is ~130 px. Search near that only.
let perX0 = period(colProf, 118, 142);
let perY0 = period(rowProf, 118, 142);
if (perX0 < 100 || perY0 < 100) { /* nothing periodic found -> fail */ }

let sx0 = bestPhase(colProf, perX0, COLS, AX0, AX1);
let LX  = snapLines(colProf, sx0, perX0, COLS, 0.25);   // snap each line, then
let perX = (LX[COLS] - LX[0]) / COLS;                   // uniform pitch from span

if (perX < 115 || perX > 145 || perY < 115 || perY > 145) { /* reject */ }
```

Sanity-check the edge score too: **3–6× the mean at every line is a real board**.
A score above ~12× means the grid latched onto a repeated printed pattern (log
rows, a list, a toolbar), not cards — reject it. And apply the same pitch rule to a
stale `board.json` instead of trusting it; a board file from another level reads as
a perfectly valid region and poisons every run.

**Phase must be searched over the whole axis, not `[lo, lo+pitch)`.** Modulo-pitch
phase search scores a fixed number of taps starting anywhere, so a low-edge region
(margin, app header, toolbar) can win and the grid lands on chrome instead of the
board. Brute-force the start position and score the **sum of edge energy at every
grid line** — dense-cell regions outscore empty ones, so the board wins on merit.
See `bestPhase()` in `references/grid-calibration.md`.

Guard the result: `perX < 30 || perY < 30` means no periodic structure was found —
the board is not covered, do not build a grid on it.

**Reject a hand-pointed box whose implied pitch disagrees with the measured one**
by more than ~15%; a box twice the true size is the classic miss (the user aims at
the outer container, the pitch says otherwise). When they disagree, the box wins
nothing — rebuild from the measured pitch.

**Keep `CROP` SMALL — about 0.28 × pitch, clamped 24–40 px.** This inverts the
instinct ("sample most of the tile so you capture the artwork") and the numbers are
unambiguous. On a 130 px tile: `CROP 72` scored *identical* cards at **0.776** —
below any workable threshold, so the matcher could never find a triple — while
`CROP 30–36` scored the same cards **0.960–0.971** with different cards still under
0.93. A majority-of-cell patch is mostly card **border**, and every card wears the
same border, so a big patch makes *all* tiles look alike — including the ones you
need to tell apart. The cell-centre energy profile shows why: edge energy peaks at
r ≈ 35–45 px from centre (the border) and is lower inside. A patch of
`0.28 × pitch` sits inside the border and samples the icon.

```js
CROP = Math.max(24, Math.min(40, Math.round(Math.min(perX, perY) * 0.28)));
```

Tune this number **offline** on one saved screenshot before burning phone
round-trips — see `references/vision-tuning.md`.

Once the region is measured, hardcode it and set a `USE_CONFIG = true` flag that
reads `board.json` (measured) before `config.json` (hand-pointed), so a stale
hand-pointed file cannot silently override the measured values.

Do not trust "my screen matches the script" — decode the screenshot and measure.
Downscaled uploads mislead: recover the true scale from a feature of known size
inside the image (e.g. the calibration rectangle the script itself drew), then
convert back to screen pixels.

**Never infer orientation from an uploaded screenshot.** The upload may be
cropped, letterboxed, or downscaled, and each of those shifts it: a drawn
rectangle that the script placed at screen `x=47` can appear at image `x=35`, so
its *absolute position in the image is not its screen position*. Treating that as
"the script drew in the wrong place" or "the screen is rotated" sends you
chasing a coordinate bug that does not exist. Orientation is a device fact — read
it from `device.width/height` versus `captureScreen().getWidth()/getHeight()`,
never from a picture. Use the screenshot only for **relative** measurements
(cell pitch, column count, which colour is where), scaling from a feature the
script itself drew.

Confirm `cols`/`rows` arithmetically before shipping: `w / cols` and `h / rows`
must reproduce the measured cell size exactly. If they do not, the region or the
grid is wrong — a plausible-looking rectangle over empty background is the
classic miss, and it is invisible until you check the divisibility.

## Script runs but never taps

Four causes, in order of likelihood. Do not re-read the bot script hunting for a
logic bug — ship a diagnostic script that reports all four at once and dumps its
images, then fix the one that fired.

0. **An exception is being swallowed and the worker thread is dead.** This is the
   one that hides all the others: `try { playLoop(); } catch (e) { }` around a
   `threads.start` body means the first throw ends the loop silently — no toast,
   no error, screen just never taps. **Never leave a bare `catch (e) {}` around the
   loop body**; store it and log it, then re-report it at exit:

   ```js
   let result = null, workerErr = null;
   let worker = threads.start(function () {
     try { result = playLoop(); }
     catch (e) { workerErr = e; console.log("WORKER MATI: " + e); }
   });
   while (state.run) sleep(200);
   console.log("loop=" + (result ? result.loop : "?") +
               (workerErr ? " ERR=" + workerErr : ""));
   ```

   The classic swallowed throw is `images.clip` raising
   `y + height must be <= bitmap.height()` — see cause 4.

1. **Accessibility Service is off — or listed as on while its process is dead.**
   Two different states, one symptom (no exception, `click()` just does nothing):

   - **Not listed at all.** Send the user to Settings -> Accessibility -> AutoJs -> ON.
   - **Listed, but the engine refuses to run it.** AutoJs throws
     `Accessibility service enabled but not running (Re-enable or reboot the
     device)` and the script dies within seconds. Worse, a "is autojs in the list"
     check **passes** in this state — the package IS in
     `ENABLED_ACCESSIBILITY_SERVICES` — so you conclude tapping is fine while every
     tap is silently lost. The fix is a toggle, not a setting: turn AutoJs **OFF**
     in Accessibility, wait a beat, turn it **ON** again; reboot if that does not
     take. Battery optimisers and app restarts kill the running service while
     leaving it enabled, so this recurs across sessions.

   Read the enabled-service list and check the AutoJs package is in it:

   ```js
   let svc = android.provider.Settings.Secure.getString(
     context.getContentResolver(),
     android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
   console.log("autojs enabled? " + (svc && svc.toLowerCase().indexOf("autojs") >= 0));
   ```

   If false, send the user to Settings -> Accessibility -> AutoJs -> ON.
2. **Wrong coordinates.** Save the full screen *and* the clipped region to files so
   the target area can be looked at, instead of reasoning from a description. A
   plausible rectangle over empty background looks identical to a correct one in
   prose.
3. **Matcher found nothing.** Log the similarity histogram — top N pair scores plus
   counts above several thresholds — so a threshold that is too strict is
   distinguishable from a crop that is empty. Silence from the solver is ambiguous
   between those two; the histogram is not.
4. **The capture bitmap is a different orientation or size than the screen.**
   `requestScreenCapture(true)` **forces landscape**; `false` keeps the device
   orientation. With the wrong one, `captureScreen()` returns e.g. 2460×1080 while
   the device is 1080×2460, so a portrait-calibrated region throws
   `images.clip: y + height must be <= bitmap.height()` on every frame — which,
   without cause 0 handled, kills the worker in silence.

   **Always call `requestScreenCapture(false)`**, and prove the two agree at
   startup before the loop begins. **Also gate on the call's return value** —
   `requestScreenCapture()` fails *silently* when the MediaProjection consent
   dialog cannot be shown, and it will not show from a launcher shortcut, a
   floating window, or a notification action: only from inside the AutoJs app UI.
   Nothing is thrown, no toast fires, and the session burns on a black screen of
   empty pixels. Fail loudly on the first frame instead of at tap 200:

   ```js
   toast("Minta izin rekam layar...");
   let capOK = false;
   try { capOK = requestScreenCapture(false); } catch (e) {}
   sleep(1200);
   let t = null;
   try { t = captureScreen(); } catch (e) {}
   if (!t || capOK === false) {
     log("!!! CAPTURE GAGAL - jalankan dari DALAM app AutoJs, bukan shortcut");
     exit();                       // never fall through into the loop
   }
   log("device " + device.width + "x" + device.height +
       " | bitmap " + t.getWidth() + "x" + t.getHeight());
   t.recycle();
   ```

   Both pairs must match. Teardown first: a camera/mic-style resource permission
   that was denied once stays denied, so the fix is to the *launch path* (run it
   from the app) or re-grant in Settings -> Apps -> AutoJs -> Permissions, never a
   code change. A landscape bitmap on a portrait device also **invalidates
   every screenshot you have been reasoning from** — the uploads are 2460×1080,
   not a rotated view of a portrait screen. Do not "fix" the region coordinates
   for that; fix the capture argument.

   Belt-and-braces guard so one bad frame cannot kill the loop:

   ```js
   let bw = img.getWidth(), bh = img.getHeight();
   let bx = BOARD.x, by = BOARD.y, bww = BOARD.w, bhh = BOARD.h;
   if (bx + bww > bw || by + bhh > bh) {
     if (bw > bh) { try { img.recycle(); } catch (e) {} sleep(600); continue; }
     bww = Math.min(bww, bw - bx);
     bhh = Math.min(bhh, bh - by);
     if (bww < 50 || bhh < 50) { try { img.recycle(); } catch (e) {} sleep(600); continue; }
   }
   ```

   Corollary: a too-large board rectangle is *not* the usual culprit. Check the
   arithmetic first — `x + w <= bw` and `y + h <= bh` against the **bitmap** size,
   not the device size. When both hold against the device and only the bitmap is
   smaller, the rectangle is fine and the capture is wrong.

## Trap: the code fence swallows the XML

Floaty layouts use JSX-like `<frame>...</frame>` inside `.js`. `node --check`
fails with `SyntaxError: Unexpected token '<'`. That lint error is expected when
editing these files with tools that run a Node syntax check — verify by
stripping the XML block, not by "fixing" the layout:

```python
s2 = re.sub(r'floaty\.rawWindow\(\s*<frame[\s\S]*?</frame>\s*\)', 'floaty.rawWindow(null)', s)
```

## Report honestly: say what you measured, not what you assumed

When a previous guess turns out wrong, lead with the correction and the evidence
for it, then the fix. Naming the wrong assumption in one line ("I read the
screenshot as landscape; the device is portrait") is worth more than a silent
edit — the user is calibrating how much to trust the numbers you hand them.
Do not restate an unverified claim as fact ("your screen matches the script");
if it was never measured, say so and measure it.

## Verification

Before handing the script over: strip the XML, `node --check`, and grep for `&`
(must be zero) and for leftover `setPosition`/`setX`/`getX` (none, or wrapped in
fallbacks). Also grep `requestScreenCapture(true)` — must be zero. Syntax passing
is not enough — fork API calls only fail at runtime on the phone, so ask for the
exact error line when the user reports a failure.

Verify before shipping: `node --check` on the XML-stripped copy, zero `&`,
no bare `setPosition`/`setX`/`getX`, and a one-liner confirming `w / cols` and
`h / rows` reproduce the calibrated cell size.

## Support files

- `templates/screen-bot.js` — working end-to-end skeleton (countdown, floaty,
  dual kill switch, dialog dim-detection, worker thread, signature matcher).
  Copy it and edit the CONFIG block plus the one marked selection block.
- `scripts/autogrid-probe.js` — run this **first** on any new board. Measures the
  cell pitch by autocorrelation, derives `{x, y, w, h}` from it, writes
  `board.json`, and saves `grid.png` with the grid drawn on it. The bot reads
  `board.json` before any hand-pointed `config.json`. Verify by eye that the red
  centres land in the middle of every cell before trusting the region.
- `references/vision-tuning.md` — tune `CROP` and the similarity threshold
  **offline**, on one saved screenshot in Python, instead of burning phone
  round-trips. Includes the `CROP` sweep that exposes a broken patch size, the
  cell-centre energy profile that explains it, and the signature-population check.
  Do this before asking for another run.
- `references/grid-calibration.md` — the full grid-derivation routines:
  autocorrelation `period()`, whole-axis `bestPhase()`, per-line `snapLines()`,
  and the three cheap gates (magnitude, span, edge score) that stop a bad pitch
  from silently growing the board past the real one.
