# AutoJs / AutoX — API notes that survive version drift

Only the parts worth carrying forward. AutoJs6 and AutoX forks diverge on image
API names and ranges; the patterns below avoid the divergent surface.

## Image handling

Do not rely on named matchers. `images.getSimilarity`, `images.findImage`,
`images.findMultiColors` have different signatures and return ranges between
forks — a script that works on one throws or silently mis-matches on another.

Instead: read pixels yourself and compare in JS.

```js
function signature(img, cx, cy, size) {
  const h = size / 2, sig = [];
  for (let gy = 0; gy < 8; gy++) {
    for (let gx = 0; gx < 8; gx++) {
      const px = Math.max(0, (cx - h + gx * size / 8) | 0);
      const py = Math.max(0, (cy - h + gy * size / 8) | 0);
      let c;
      try { c = images.pixel(img, px, py); } catch (e) { c = 0; }
      sig.push((c >> 16 & 255), (c >> 8 & 255), (c & 255));
    }
  }
  return sig;   // 64 samples x 3 channels
}

function sim(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]);
  return 1 - d / (a.length * 255);   // 1.0 identical, 0.0 opposite
}
```

Read once into the signature, compare later in pure JS. An 8x8 grid over a ~44px
window is enough for icon/tile discrimination; it is also fast enough to run
across an 8x9 board every frame.

Sample-window sizing matters more than the threshold people argue about:

| Window | Result |
|---|---|
| ~36px | too small — distinct icons score above threshold, false groups |
| ~44px | discriminates board tiles at threshold 0.93 |

Threshold guidance: **0.93 for icon matching**, not 0.85. Loose thresholds group
adjacent cells and the bot taps nonsense.

## Memory

`captureScreen()` and `images.clip()` return objects that must be released.
~600ms loop interval means thousands of captures in one level.

```js
try { board.recycle(); img.recycle(); } catch (e) {}
```

Always in `try/catch` — double-recycle throws, and the throw would kill the loop.

## Coordinate guards

Computed edge coordinates go negative (`cx - half` where `cx < half`).
`images.pixel` and `images.clip` throw on negatives. Wrap every derived
coordinate in `Math.max(0, ...)`.

## Popup / modal detection

Do not template-match for popup buttons — layout changes, and the buttons differ
per state (loss vs level-complete vs booster prompt). Use brightness of a region
you already own the coordinates for.

```js
let baseline = 0, strikes = 0;
// each frame:
const b = brightnessOfKnownRegion(img);
if (b > baseline) baseline = b;
strikes = (baseline > 0 && b < baseline * 0.62) ? strikes + 1 : 0;
if (strikes >= 2) { /* modal is up */ }
```

A modal dims everything behind it, so a monotonically-tracked baseline plus a
62% drop across 2 frames is a reliable, template-free signal.

When the modal is detected: save the frame BEFORE tapping anything.

```js
if (DIR) { try { images.save(img, DIR + "/popup_" + Date.now() + ".png"); } catch (e) {} }
```

That screenshot is the calibration artifact — the user sends it, the agent reads
the real button coordinates off it. Blind coordinate guessing on a state that
only appears after a loss is the single biggest time sink in this class of work.

## Threads and responsiveness

`press()` plus `sleep()` on the main thread blocks the floaty button. Split:

```js
let result = null;
const worker = threads.start(function () {
  try { result = playLoop(); } catch (e) { /* interrupt is normal exit */ }
});

while (state.run) sleep(200);   // main thread stays free for input

try { worker.interrupt(); } catch (e) {}
try { win.close(); } catch (e) {}
exit();
```

The worker's `catch` swallowing the interrupt is intentional — `interrupt()`
raises inside the thread and is the normal shutdown path.

`win.close()` before `exit()`: a floaty overlay is a separate window and outlives
the script otherwise, leaving a dead STOP button stuck on screen.

## Floating window (E4X)

```js
const win = floaty.rawWindow(
  <frame bg="#00000000">
    <button id="stop" w="110" h="110" marginLeft="20" marginTop="240"
            text="STOP" bg="#e74c3c" textColor="#ffffff" textSize="18sp"/>
  </frame>
);
win.setTouchable(true);
win.stop.click(() => stopIt("button"));
```

Three things that each waste a round trip if not stated up front:

- The `<frame>` markup is E4X, not HTML. A host-side JS/Node syntax check reports
  `Unexpected token '<'` — expected, not a real error.
- If the button is invisible the app is missing the **display over other apps**
  permission. That is a settings fix, not a code fix.
- **Position with `marginLeft` / `marginTop` in the XML.** Do NOT use
  `win.setPosition(...)` / `setX` / `setY` — absent on some forks, and the throw
  lands inside `floaty.rawWindow`, so the window never appears. For runtime
  movement use `v.getLayoutParams()` (`leftMargin` / `topMargin`) and
  `v.setLayoutParams(lp)`; read it back the same way.
- **Zero `&` in an attribute value or a `toast()` string.** `&amp;` throws
  `InflateException: org.xml.sax.SAXParseException: unterminated entity ref`
  (error position points at the offending `android:text`). Write the word
  (`dan`, `and`); escaping is unreliable. Grep the file for `&` after editing.

## Keeping a UI script alive

`floaty.rawWindow()` does not block. A script that just builds a window and ends
has that window torn down immediately — the user sees the buttons flash for a
second and reports "it finished on its own". Park the main thread on a sentinel
set by the confirm button:

```js
let done = false;
win.go.click(() => { /* write config, save proof PNG */ done = true; });
while (!done) sleep(300);          // last statement — holds the window open
try { win.close(); } catch (e) {}
exit();
```

For bot loops the equivalent is `while (state.run) sleep(200)` on the main thread
with the work in `threads.start(...)`.

## Hardware keys as the guaranteed kill switch

```js
events.observeKey();
events.onKeyDown("volume_up",   () => stopIt("vol up"));
events.onKeyDown("volume_down", () => stopIt("vol down"));
```

Volume keys work when the floaty is buried under a notification shade or a
keyboard. Ship both mechanisms; the floaty is convenience, the volume key is the
guarantee.

## Device probing

```js
toast(device.width + " x " + device.height);
```

Board rectangles and grid dimensions are per-device. Never present them as
known — have the user read the toast, or scale an existing rectangle by
`device.width / <assumed width>`.

**Measure the screenshot before deriving any scale.** An uploaded frame may be
downscaled, letterboxed, or rotated in the viewer, and the app may occupy only
part of the frame (split-screen or landscape). Get the content rect first:

```python
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask = hsv[:,:,2] > 150                       # bright pixels = app content
cols = np.where(mask.mean(axis=0) > 0.10)[0]
rows = np.where(mask.mean(axis=1) > 0.10)[0]
# cols.min()/max(), rows.min()/max() -> content bbox, in image pixels
```

If that bbox does not span the frame, the remainder is black bars or another
window — every coordinate computed against the full frame is wrong. Then recover
the true scale from a feature of known size that the script itself drew (the
calibration rectangle or grid dots), and convert the bbox back to screen pixels.

Mismatched aspect ratio (e.g. image 2.28:1 vs a 1080x2462 portrait device) means
the device was in landscape or the image was rotated. Work out which by locating
a known landmark (an orange header belongs at the top), rotate once, and only
then measure.

## Storage

- `/sdcard` is an **alias** for `/storage/emulated/0`. Give the real path.
- Android 11+: direct writes under `/storage/emulated/0/<dir>` need "All files
  access" and often fail silently.
- `context.getExternalFilesDir(null)` →
  `/storage/emulated/0/Android/data/<package>/files` — permission-free, always
  writable. Preferred default.
- Test with a real write. `files.ensureDir` succeeding does not prove write
  access:

```js
files.ensureDir(dir + "/");
const probe = files.join(dir, ".probe");
files.write(probe, "ok");
files.remove(probe);
```

- Toast the winning directory at startup so the user can find the files.
- Retrieval: Android 13+ stock file managers block `Android/data`. Use a
  third-party manager or `adb pull`.
