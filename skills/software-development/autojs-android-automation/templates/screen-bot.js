// Generic AutoJs screen-capture bot skeleton.
// Copy and edit the CONFIG block. Everything below it is the tested shape:
//   countdown -> floaty -> kill switch -> worker thread -> main thread parks.
// Replace BOARD/COLS/ROWS with values from the two-corner calibration script.
"auto";

// ==================== CONFIG ====================
const BOARD = { x: 0, y: 0, w: 0, h: 0 };   // from calibration
const COLS = 7, ROWS = 9;                    // cols/rows must divide w/h exactly
const CROP = 44;                             // >= 24, <= cell * 0.4

// Screen-space taps for dialogs the bot must dismiss. Keep y < screen height.
const BTN_PRIMARY   = [540, 1900];
const BTN_SECONDARY = [540, 1980];
const BTN_FALLBACK  = [540, 1600];

const SIM_THRESHOLD  = 0.93;   // 1.0 = identical; below 0.85 = false matches
const DIM_RATIO      = 0.62;   // board brightness drop = overlay/dialog present
const DIM_STRIKES    = 2;
const STUCK_STRIKES  = 6;
const MAX_LOOP       = 4000;
const START_DELAY    = 7;      // seconds to switch back to the target app
const TAG            = "bot";  // used for the output folder name

// ==================== OUTPUT DIR ====================
// /sdcard alone fails on Android 11+; Download/ stays visible over MTP to Windows.
const DIRS = [];
try { DIRS.push(files.join(files.getSdcardPath(), "Download", TAG)); } catch (e) {}
try { DIRS.push(files.join(files.getSdcardPath(), "Pictures", TAG)); } catch (e) {}
try { DIRS.push(files.join(files.getSdcardPath(), TAG)); } catch (e) {}
try {
  DIRS.push(files.join(files.getSdcardPath(),
    "Android/data/" + context.getPackageName() + "/files/" + TAG));
} catch (e) {}

try { console.show(); } catch (e) {}

function scan(p) {
  try { android.media.MediaScannerConnection.scanFile(context, [p], null, null); } catch (e) {}
}

function pickDir() {
  for (let i = 0; i < DIRS.length; i++) {
    try {
      files.ensureDir(DIRS[i] + "/");
      let probe = files.join(DIRS[i], ".probe");
      files.write(probe, "ok");   // ensureDir succeeds while write can still fail
      files.remove(probe);
      return DIRS[i];
    } catch (e) { }
  }
  return null;
}
const DIR = pickDir();
console.log("DIR = " + DIR);
console.log("device: " + device.width + " x " + device.height);

// ==================== KILL SWITCH ====================
// Created AFTER the countdown so it does not cover the screen during the wait,
// and in a worker thread so it stays responsive while the loop sleeps.
const state = { run: true, why: "init" };
function stopIt(why) {
  if (!state.run) return;
  state.run = false;
  state.why = why;
  toast("STOP: " + why);
}
let win = null;

// ==================== VISION ====================
function brightness(img) {
  let pts = [
    [BOARD.x + BOARD.w * 0.25, BOARD.y + BOARD.h * 0.25],
    [BOARD.x + BOARD.w * 0.75, BOARD.y + BOARD.h * 0.25],
    [BOARD.x + BOARD.w * 0.25, BOARD.y + BOARD.h * 0.75],
    [BOARD.x + BOARD.w * 0.75, BOARD.y + BOARD.h * 0.75],
  ];
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    let c;
    try { c = images.pixel(img, pts[i][0] | 0, pts[i][1] | 0); } catch (e) { continue; }
    s += ((c >> 16 & 255) + (c >> 8 & 255) + (c & 255)) / 3;
  }
  return s / pts.length;
}

// Read the patch ONCE into an 8x8 RGB grid; compare the arrays in plain JS.
function signature(img, cx, cy) {
  let h = CROP / 2, sig = [];
  for (let gy = 0; gy < 8; gy++) {
    for (let gx = 0; gx < 8; gx++) {
      let px = Math.max(0, (cx - h + gx * CROP / 8) | 0);
      let py = Math.max(0, (cy - h + gy * CROP / 8) | 0);
      let c;
      try { c = images.pixel(img, px, py); } catch (e) { c = 0; }
      sig.push((c >> 16 & 255), (c >> 8 & 255), (c & 255));
    }
  }
  return sig;
}

function sim(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]);
  return 1 - d / (a.length * 255);
}

function tap(x, y) { press(x | 0, y | 0, 120); }
function tapWait(x, y, ms) { tap(x, y); sleep(ms); }

// ==================== WORKER ====================
function playLoop() {
  let baseline = 0, dimStrikes = 0, stuck = 0, loop = 0, dialogs = 0;

  while (state.run && loop++ < MAX_LOOP) {
    let img = captureScreen();
    if (!img) { sleep(400); continue; }

    // Dialog detection by dimming, not by hunting for a button image.
    let b = brightness(img);
    if (b > baseline) baseline = b;
    if (baseline > 0 && b < baseline * DIM_RATIO) dimStrikes++; else dimStrikes = 0;

    if (dimStrikes >= DIM_STRIKES) {
      dialogs++;
      if (DIR) { try { images.save(img, DIR + "/dialog_" + Date.now() + ".png"); } catch (e) {} }
      try { img.recycle(); } catch (e) {}

      tapWait(BTN_PRIMARY[0], BTN_PRIMARY[1], 2200);

      // still dim -> it was a different dialog, try the next button
      let img2 = captureScreen();
      let b2 = brightness(img2);
      try { img2.recycle(); } catch (e) {}
      if (b2 < baseline * DIM_RATIO) tapWait(BTN_SECONDARY[0], BTN_SECONDARY[1], 2200);

      dimStrikes = 0; stuck = 0;
      continue;
    }

    // Guard the clip. A bitmap smaller than the device (wrong capture
    // orientation) makes this throw on every frame. BOARD must fit the BITMAP,
    // not the device — check that arithmetic before blaming the board size.
    let bw = img.getWidth(), bh = img.getHeight();
    let bx = BOARD.x, by = BOARD.y, bww = BOARD.w, bhh = BOARD.h;
    if (bx + bww > bw || by + bhh > bh) {
      if (bw > bh) { try { img.recycle(); } catch (e) {} sleep(600); continue; }
      bww = Math.min(bww, bw - bx);
      bhh = Math.min(bhh, bh - by);
      if (bww < 50 || bhh < 50) { try { img.recycle(); } catch (e) {} sleep(600); continue; }
    }

    let board = images.clip(img, bx, by, bww, bhh);
    let cw = bww / COLS, ch = bhh / ROWS;

    let tiles = [];
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        tiles.push({
          x: bx + x * cw + cw / 2,
          y: by + y * ch + ch / 2,
          sig: signature(board, x * cw + cw / 2, y * ch + ch / 2)
        });
      }
    }
    try { board.recycle(); img.recycle(); } catch (e) {}

    // ---- EDIT ME: the actual move selection ----
    let g = null;
    for (let i = 0; i < tiles.length && state.run && !g; i++) {
      let grp = [tiles[i]];
      for (let j = i + 1; j < tiles.length && grp.length < 3; j++) {
        if (sim(tiles[i].sig, tiles[j].sig) > SIM_THRESHOLD) grp.push(tiles[j]);
      }
      if (grp.length >= 3) g = grp;
    }
    // ---- END EDIT ----

    if (g) {
      stuck = 0;
      for (let k = 0; k < 3 && state.run; k++) { tap(g[k].x, g[k].y); sleep(600); }
      sleep(900);
    } else {
      stuck++;
      if (stuck >= STUCK_STRIKES) {
        tapWait(BTN_FALLBACK[0], BTN_FALLBACK[1], 1500);
        stuck = 0;
      }
      sleep(600);
    }
  }
  return { loop: loop, dialogs: dialogs };
}

// ==================== RUN ====================
// false = keep device orientation. true FORCES landscape: captureScreen() then
// returns a swapped-size bitmap (e.g. 2460x1080 on a 1080x2460 phone), every
// images.clip() throws "y + height must be <= bitmap.height()", and if the
// worker swallows that the bot just never taps. Always false.
requestScreenCapture(false);
sleep(800);

// Prove capture and screen agree BEFORE the loop starts. Both pairs must match.
try {
  let t = captureScreen();
  console.log("device " + device.width + "x" + device.height +
              " | bitmap " + t.getWidth() + "x" + t.getHeight());
  t.recycle();
} catch (e) { console.log("orient check failed: " + e); }

toast("Buka app target — " + START_DELAY + " detik");
for (let i = START_DELAY; i > 0; i--) { toast("" + i, 800); sleep(1000); }

win = floaty.rawWindow(
  <frame w="*" h="*" bg="#00000000">
    <button id="stop" w="110" h="110" x="20" y="240"
            text="STOP" bg="#e74c3c" textColor="#ffffff" textSize="18sp"/>
  </frame>
);
win.setTouchable(true);
win.stop.click(() => stopIt("tombol"));

events.observeKey();
events.onKeyDown("volume_up",   () => stopIt("vol atas"));
events.onKeyDown("volume_down", () => stopIt("vol bawah"));

toast("Jalan — Vol+/- atau tombol STOP buat berhenti");

// NEVER swallow the worker's exception. A bare `catch (e) {}` here turns the
// first throw into silence: no toast, no error, screen simply never taps, and
// you go hunting for a logic bug that is not there.
let result = null, workerErr = null;
let worker = threads.start(function () {
  try { result = playLoop(); }
  catch (e) { workerErr = e; console.log("WORKER DIED: " + e); }
});

while (state.run) sleep(200);   // parks the main thread; keeps UI + keys alive

try { worker.interrupt(); } catch (e) {}
try { if (win) win.close(); } catch (e) {}

console.log("loop=" + (result ? result.loop : "?") +
            " dialogs=" + (result ? result.dialogs : "?") +
            (workerErr ? " ERR=" + workerErr : ""));
toast("Selesai (" + state.why + ") loop=" + (result ? result.loop : "?") +
      (workerErr ? " ERR!" : ""));
exit();
