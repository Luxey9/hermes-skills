# AutoJs recipe — kill switch, threaded loop, calibration

Skeletons to copy. Fill the calibration constants from a real screenshot.

## Kill switch (two channels)

```js
const state = { run: true, why: "init" };
function stopIt(why) {
  if (!state.run) return;
  state.run = false; state.why = why;
  toast("STOP: " + why);
}

let win = floaty.rawWindow(
  <frame bg="#00000000">
    <button id="stop" w="110" h="110" text="STOP" bg="#e74c3c"
            textColor="#ffffff" textSize="18sp"/>
  </frame>
);
win.setPosition(20, 240);
win.setTouchable(true);
win.stop.click(() => stopIt("tombol"));

events.observeKey();
events.onKeyDown("volume_up",   () => stopIt("vol atas"));
events.onKeyDown("volume_down", () => stopIt("vol bawah"));
```

The floating button needs the *display over other apps* permission; if it never
appears, that is the cause. The volume keys need nothing, so they are the real
escape hatch.

## Threaded loop with clean teardown

```js
let result = null;
let worker = threads.start(function () {
  try { result = playLoop(); } catch (e) { /* interrupt() lands here */ }
});

while (state.run) sleep(200);      // main thread stays responsive

try { worker.interrupt(); } catch (e) {}
try { win.close(); } catch (e) {}
toast("Selesai (" + state.why + ")");
exit();
```

Check `state.run` *inside* inner action groups too, so pressing STOP does not
wait for a batch of taps to finish.

## Writable output directory (Android 11+ safe)

```js
function pickDir() {
  const cands = [];
  try { cands.push(files.join(files.getSdcardPath(), "myapp")); } catch (e) {}
  try {
    cands.push(files.join(files.getSdcardPath(),
      "Android/data/" + context.getPackageName() + "/files/myapp"));
  } catch (e) {}
  try { cands.push(context.getExternalFilesDir(null).getAbsolutePath() + "/myapp"); } catch (e) {}

  for (let i = 0; i < cands.length; i++) {
    try {
      files.ensureDir(cands[i] + "/");
      let probe = files.join(cands[i], ".probe");
      files.write(probe, "ok");   // ensureDir can succeed while write is denied
      files.remove(probe);
      return cands[i];
    } catch (e) {}
  }
  return null;
}
```

## Two-marker calibration window

Give the user draggable buttons and let them mark the target rectangle. Derive
`{x, y, w, h}` from the two centres, write it to `config.json`, then draw the
rectangle plus one red dot per grid cell on a fresh screenshot and open it — the
user sees immediately whether the grid lands on the targets.

```js
function draggable(view) {
  let sx = 0, sy = 0, ox = 0, oy = 0, down = false;
  view.setOnTouchListener(new android.view.View.OnTouchListener({
    onTouch: function (v, e) {
      switch (e.getAction()) {
        case android.view.MotionEvent.ACTION_DOWN:
          sx = e.getRawX(); sy = e.getRawY();
          ox = v.getX(); oy = v.getY(); down = true; break;
        case android.view.MotionEvent.ACTION_MOVE:
          if (down) { v.setX(ox + (e.getRawX() - sx)); v.setY(oy + (e.getRawY() - sy)); }
          break;
        case android.view.MotionEvent.ACTION_UP:
          down = false; break;
      }
      return true;
    }
  }));
}
```

Overlay the result with the Android canvas API — `img.getBitmap()`,
`new android.graphics.Canvas(bmp)`, `drawRect` / `drawCircle`, `images.save()`,
`app.viewFile()`.

### Place views with layout margins, not `setPosition`

`setPosition` / `setX` / `setY` do not exist on every fork and fail at runtime.
Set position at inflate time instead, which always works:

```js
<button id="stop" w="110" h="110" marginLeft="20" marginTop="240" .../>
```

To move a view at runtime (drag handles), use the core Android API — there is no
fork where this is missing:

```js
function move(v, x, y) {
  const lp = v.getLayoutParams();
  lp.leftMargin = Math.round(x); lp.topMargin = Math.round(y);
  v.setLayoutParams(lp);
}
function pos(v) {
  const lp = v.getLayoutParams();
  return [lp.leftMargin || 0, lp.topMargin || 0];
}
```

### Let the sample window follow the cell size

Hard-coding the crop window couples the script to one screen. Derive it from the
calibrated grid so a different device or a denser level still reads cleanly:

```js
CROP = Math.max(24, Math.min(64,
  Math.round(Math.min(cfg.w / cfg.cols, cfg.h / cfg.rows) * 0.4)));
```

A sample window larger than the cell averages in the gutter between tiles and
destroys discrimination; smaller than ~24 px picks up JPEG mush.

## Create the floaty only after the countdown

An overlay sits above every app. A floaty created at the top of the file covers
the screen the user is still navigating during the startup delay, so the delay
accomplishes nothing. Order the file: constants → `requestScreenCapture` →
countdown → floaty + `events.observeKey()` → worker thread. Declare `let win = null;`
ear the top, assign it after the countdown, and guard teardown with `if (win)`.

## Popup detection without template matching

```js
function brightness(img) {
  const pts = [[0.25, 0.25], [0.75, 0.25], [0.25, 0.75], [0.75, 0.75]];
  let s = 0;
  for (const [fx, fy] of pts) {
    const c = images.pixel(img, (X + W * fx) | 0, (Y + H * fy) | 0);
    s += ((c >> 16 & 255) + (c >> 8 & 255) + (c & 255)) / 3;
  }
  return s / pts.length;
}
```

Track a running maximum as the baseline. Two consecutive frames below
`baseline * ratio` means a modal is up. Save that frame to disk before tapping —
it is the only way the user can tell you the correct button coordinate.

## Taps a game ignores

For taps the app drops as "too fast", `press(x, y, 120)` (120 ms hold) reads as a
deliberate tap. Keep the inter-tap pause generous — most matching games re-animate
between placements.

## Solver shape for match-3 style boards

The board is a search problem, not a click list: state = visible cards plus slot
contents, move = take a card, goal = empty the board with the slot never full.
Priority order: a triple already visible > a card that uncovers new cards > use a
shuffle/remove booster only when nothing else is legal. Report the state as a
plain `{cells, slot}` structure so the loop can retry the same frame after an
animation.
