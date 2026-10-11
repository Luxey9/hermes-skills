"auto";
// ==========================================================================
// AutoJs / AutoX bot skeleton - copy and change ONLY the constants block.
//
// File order matters. Do NOT move the floaty to the top: an overlay covers
// every app, so a floaty created before the countdown hides the very screen
// the user has to navigate during the wait.
//
//   1. constants + kill-switch flag
//   2. requestScreenCapture
//   3. countdown (nothing on screen)
//   4. floaty + events.observeKey
//   5. worker thread + main-thread guard
// ==========================================================================

// ============================== CONSTANTS =================================
// CALIBRATE FIRST: run `toast(device.width + " x " + device.height)`,
// then measure the board rect and grid from a real screenshot.
// Better: have the user drag two markers over the board corners (see the
// calibration script) and write the result to config.json, then read it back
// here so recalibration needs no code edit.
const BOARD = { x: 0, y: 0, w: 0, h: 0 };   // board rect on screen
const COLS = 7, ROWS = 9;                   // grid shape
let CROP = 44;                              // sample window, ~44px works

// Coordinates on failure paths (popup buttons). VERIFY FROM A SAVED SCREENSHOT
// before trusting these - a blind guess is a placeholder, not a calibration.
const BTN_MAIN = [0, 0];
const BTN_ALT  = [0, 0];

const SIM_THRESHOLD = 0.93;   // 0.85 is too loose: groups adjacent distinct tiles
const POPUP_DIM     = 0.62;   // brightness drop signalling a modal
const POPUP_STRIKES = 2;
const STUCK_STRIKES = 6;
const MAX_LOOP      = 4000;   // safety net
const START_DELAY   = 7;      // seconds to get back to the app

// ===================== LOAD CALIBRATION (optional) ========================
// Written by the two-marker calibration script; lets the user recalibrate
// without touching this file.
const DIRS = [];
try { DIRS.push(files.join(files.getSdcardPath(), "bot")); } catch (e) {}
try {
  DIRS.push(files.join(files.getSdcardPath(),
    "Android/data/" + context.getPackageName() + "/files/bot"));
} catch (e) {}

for (let i = 0; i < DIRS.length; i++) {
  try {
    const p = files.join(DIRS[i], "config.json");
    if (files.exists(p)) {
      const c = JSON.parse(files.read(p));
      BOARD.x = c.x; BOARD.y = c.y; BOARD.w = c.w; BOARD.h = c.h;
      COLS = c.cols; ROWS = c.rows;
      // sample window scales with the cell so a small grid is not over-sampled
      CROP = Math.max(24, Math.min(64,
        Math.round(Math.min(c.w / c.cols, c.h / c.rows) * 0.4)));
      break;
    }
  } catch (e) {}
}

// ============================ KILL SWITCH =================================
// Declared here, but the floaty is created AFTER the countdown (step 4 below).
const state = { run: true, why: "init" };
function stopIt(why) {
  if (!state.run) return;
  state.run = false;
  state.why = why;
  toast("STOP: " + why);
}

let win = null;

// ========================= FILE DIRECTORY =================================
function pickDir() {
  // Android 11+ often refuses /storage/emulated/0 directly. Probe with a real
  // write -- files.ensureDir can succeed while the write is denied.
  const cands = [];
  try { cands.push(files.join(files.getSdcardPath(), "bot")); } catch (e) {}
  try {
    cands.push(files.join(files.getSdcardPath(),
      "Android/data/" + context.getPackageName() + "/files/bot"));
  } catch (e) {}
  try { cands.push(context.getExternalFilesDir(null).getAbsolutePath() + "/bot"); } catch (e) {}

  for (let i = 0; i < cands.length; i++) {
    try {
      files.ensureDir(cands[i] + "/");
      const probe = files.join(cands[i], ".probe");
      files.write(probe, "ok");
      files.remove(probe);
      return cands[i];
    } catch (e) {}
  }
  return null;
}
const DIR = pickDir();

// ============================== HELPERS ===================================
function brightness(img) {
  const pts = [
    [BOARD.x + BOARD.w * 0.25, BOARD.y + BOARD.h * 0.25],
    [BOARD.x + BOARD.w * 0.75, BOARD.y + BOARD.h * 0.25],
    [BOARD.x + BOARD.w * 0.25, BOARD.y + BOARD.h * 0.75],
    [BOARD.x + BOARD.w * 0.75, BOARD.y + BOARD.h * 0.75],
  ];
  let s = 0, n = 0;
  for (let i = 0; i < pts.length; i++) {
    let c;
    try { c = images.pixel(img, pts[i][0] | 0, pts[i][1] | 0); } catch (e) { continue; }
    s += ((c >> 16 & 255) + (c >> 8 & 255) + (c & 255)) / 3;
    n++;
  }
  return n ? s / n : 0;
}

// Pixel signature: read once, compare later in pure JS. Never call
// images.getSimilarity / findImage -- names and return ranges drift per fork.
function signature(img, cx, cy) {
  const h = CROP / 2, sig = [];
  for (let gy = 0; gy < 8; gy++) {
    for (let gx = 0; gx < 8; gx++) {
      const px = Math.max(0, (cx - h + gx * CROP / 8) | 0);  // guard negatives
      const py = Math.max(0, (cy - h + gy * CROP / 8) | 0);
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
  return 1 - d / (a.length * 255);   // 1.0 identical, 0.0 opposite
}

function tap(x, y) { press(x | 0, y | 0, 120); }
function tapWait(x, y, ms) { tap(x, y); sleep(ms); }

// ============================== WORK LOOP =================================
// Replace the grouping logic with the real task. The skeleton below assumes
// "find N similar items and tap them" (match-3 class).
function playLoop() {
  let baseline = 0, dimStrikes = 0, stuck = 0, loop = 0, popups = 0;

  while (state.run && loop++ < MAX_LOOP) {
    const img = captureScreen();
    if (!img) { sleep(400); continue; }

    // --- modal detection ---
    const b = brightness(img);
    if (b > baseline) baseline = b;
    dimStrikes = (baseline > 0 && b < baseline * POPUP_DIM) ? dimStrikes + 1 : 0;

    if (dimStrikes >= POPUP_STRIKES) {
      popups++;
      // save the frame BEFORE tapping: this is the calibration artifact
      if (DIR) { try { images.save(img, DIR + "/popup_" + Date.now() + ".png"); } catch (e) {} }
      try { img.recycle(); } catch (e) {}

      tapWait(BTN_MAIN[0], BTN_MAIN[1], 2200);
      const img2 = captureScreen();
      const b2 = brightness(img2);
      try { img2.recycle(); } catch (e) {}
      if (b2 < baseline * POPUP_DIM) tapWait(BTN_ALT[0], BTN_ALT[1], 2200);

      dimStrikes = 0; stuck = 0;
      continue;
    }

    // --- scan the board ---
    const board = images.clip(img, BOARD.x, BOARD.y, BOARD.w, BOARD.h);
    const cw = BOARD.w / COLS, ch = BOARD.h / ROWS;

    const tiles = [];
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        tiles.push({
          x: BOARD.x + x * cw + cw / 2,
          y: BOARD.y + y * ch + ch / 2,
          sig: signature(board, x * cw + cw / 2, y * ch + ch / 2),
        });
      }
    }
    try { board.recycle(); img.recycle(); } catch (e) {}

    // --- group: find the first triple above threshold ---
    let group = null;
    for (let i = 0; i < tiles.length && state.run && !group; i++) {
      const g = [tiles[i]];
      for (let j = i + 1; j < tiles.length && g.length < 3; j++) {
        if (sim(tiles[i].sig, tiles[j].sig) > SIM_THRESHOLD) g.push(tiles[j]);
      }
      if (g.length >= 3) group = g;
    }

    if (group) {
      stuck = 0;
      // re-check state.run inside: stop must not wait for the batch to drain
      for (let k = 0; k < 3 && state.run; k++) { tap(group[k].x, group[k].y); sleep(600); }
      sleep(900);
    } else {
      stuck++;
      if (stuck >= STUCK_STRIKES) { tapWait(BTN_ALT[0], BTN_ALT[1], 1500); stuck = 0; }
      sleep(600);
    }
  }
  return { loop: loop, popups: popups };
}

// ================================ RUN =====================================
requestScreenCapture(true);

// --- countdown: nothing on screen yet, user switches to the app ---
toast("Open the app - " + START_DELAY + " seconds");
for (let i = START_DELAY; i > 0; i--) { toast("" + i, 800); sleep(1000); }

// --- NOW create the overlay. marginLeft/marginTop, never setPosition. ---
win = floaty.rawWindow(
  <frame bg="#00000000">
    <button id="stop" w="110" h="110" marginLeft="20" marginTop="240"
            text="STOP" bg="#e74c3c" textColor="#ffffff" textSize="18sp"/>
  </frame>
);
win.setTouchable(true);
win.stop.click(() => stopIt("button"));

events.observeKey();
// volume keys are the guarantee - reachable even when the floaty is buried
events.onKeyDown("volume_up",   () => stopIt("vol up"));
events.onKeyDown("volume_down", () => stopIt("vol down"));

toast("running - vol keys or STOP to halt");

let result = null;
// worker thread keeps the main thread free so the stop button stays responsive
const worker = threads.start(function () {
  try { result = playLoop(); } catch (e) {}
});

while (state.run) sleep(200);

try { worker.interrupt(); } catch (e) {}
try { if (win) win.close(); } catch (e) {}  // floaty outlives the script without this
toast("done (" + state.why + ") loop=" + (result ? result.loop : "?"));
exit();
