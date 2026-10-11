// Auto-grid probe: measure the cell pitch instead of trusting a hand-pointed box.
// Copy into AutoJs, run with the target app's board on screen. Writes board.json
// (consumed by the bot) plus grid.png with the derived grid drawn on it.
// Change only the CONFIG block and the target-app toast text.
"auto";

// ==================== CONFIG ====================
const COLS = 7, ROWS = 9;          // from the app's layout, not from a guess
const APP_NAME = "Cocoki";        // for the countdown toast only
const DELAY = 6;                   // seconds to switch back to the app
const OUT_NAME = "autogrid";       // subfolder under Download/ and /sdcard/
// ================================================

requestScreenCapture(false);       // false = keep device orientation. NEVER true.
sleep(1200);

const DIRS = [];
try { DIRS.push(files.join(files.getSdcardPath(), "Download", OUT_NAME)); } catch (e) {}
try { DIRS.push(files.join(files.getSdcardPath(), OUT_NAME)); } catch (e) {}
try {
  DIRS.push(files.join(files.getSdcardPath(),
    "Android/data/" + context.getPackageName() + "/files/" + OUT_NAME));
} catch (e) {}

function saveDir() {
  for (let i = 0; i < DIRS.length; i++) {
    try {
      files.ensureDir(DIRS[i] + "/");
      let t = files.join(DIRS[i], ".probe");
      files.write(t, "ok"); files.remove(t);   // ensureDir succeeds while write fails
      return DIRS[i];
    } catch (e) {}
  }
  return null;
}
const DIR = saveDir();
try { console.show(); } catch (e) {}
console.log("DIR = " + DIR);

// ---- countdown so the user can switch back to the app ----
toast("Buka " + APP_NAME + " — " + DELAY + " detik");
for (let i = DELAY; i > 0; i--) { toast("" + i, 800); sleep(1000); }

const SW = device.width, SH = device.height;
let img = captureScreen();
if (!img) { console.log("captureScreen GAGAL"); exit(); }
const BW = img.getWidth(), BH = img.getHeight();

// prove capture matches the device before measuring anything
console.log("layar " + SW + "x" + SH + " | bitmap " + BW + "x" + BH);
if ((BW > BH) !== (SW > SH)) {
  console.log("!! orientasi bitmap != layar — jangan lanjut");
  exit();
}

// ---------- edge profiles ----------
function edgeProfile(vertical) {
  let prof = [];
  if (vertical) {
    for (let x = 0; x < BW - 2; x++) {
      let s = 0;
      for (let y = 0; y < BH; y += 2) {
        try {
          let a = images.pixel(img, x, y), b = images.pixel(img, x + 1, y);
          s += Math.abs((a >> 16 & 255) - (b >> 16 & 255))
             + Math.abs((a >> 8 & 255) - (b >> 8 & 255))
             + Math.abs((a & 255) - (b & 255));
        } catch (e) {}
      }
      prof.push(s);
    }
  } else {
    for (let y = 0; y < BH - 2; y++) {
      let s = 0;
      for (let x = 0; x < BW; x += 2) {
        try {
          let a = images.pixel(img, x, y), b = images.pixel(img, x, y + 1);
          s += Math.abs((a >> 16 & 255) - (b >> 16 & 255))
             + Math.abs((a >> 8 & 255) - (b >> 8 & 255))
             + Math.abs((a & 255) - (b & 255));
        } catch (e) {}
      }
      prof.push(s);
    }
  }
  return prof;
}

// autocorrelation peak -> cell pitch
function period(prof, lo, hi) {
  let n = prof.length, mean = 0;
  for (let i = 0; i < n; i++) mean += prof[i];
  mean /= n;
  let p = new Array(n);
  for (let i = 0; i < n; i++) p[i] = prof[i] - mean;
  let best = 0, bestLag = 0;
  for (let lag = lo; lag <= hi && lag < n; lag++) {
    let acc = 0;
    for (let i = 0; i + lag < n; i++) acc += p[i] * p[i + lag];
    acc /= (n - lag);
    if (acc > best) { best = acc; bestLag = lag; }
  }
  return bestLag;
}

// phase: which multiples of the pitch land on real edges
function bestOffset(prof, per, lo, hi) {
  let best = -1, bestOff = lo;
  for (let off = lo; off < Math.min(lo + per, prof.length); off++) {
    let s = 0;
    for (let k = 0; off + k * per < prof.length && k < 20; k++) s += prof[off + k * per];
    if (s > best) { best = s; bestOff = off; }
  }
  return bestOff;
}

let colProf = edgeProfile(true), rowProf = edgeProfile(false);
let x0 = Math.round(BW * 0.02), x1 = Math.round(BW * 0.98);
let y0 = Math.round(BH * 0.06), y1 = Math.round(BH * 0.94);

let perX = period(colProf, 40, 200), perY = period(rowProf, 40, 200);
console.log("periode X: " + perX + " px   periode Y: " + perY + " px");
if (perX < 30 || perY < 30) console.log("!! periode ga ketemu — board ga ketutup?");

let offX = bestOffset(colProf, perX, x0, x1);
let offY = bestOffset(rowProf, perY, y0, y1);

// ---------- derive the region from the measured pitch ----------
let bx = offX - Math.round(perX * 0.5);
let by = offY - Math.round(perY * 0.5);
let bww = Math.round(perX * COLS), bhh = Math.round(perY * ROWS);
if (bx < 0) bx = 0;
if (by < 0) by = 0;
if (bx + bww > BW) bww = BW - bx;
if (by + bhh > BH) bhh = BH - by;

console.log("BOARD auto: x " + bx + " y " + by + " " + bww + "x" + bhh);
console.log("sel: " + (bww / COLS).toFixed(1) + " x " + (bhh / ROWS).toFixed(1));

// ---------- save + prove ----------
let cfg = { x: bx, y: by, w: bww, h: bhh, cols: COLS, rows: ROWS,
            perX: perX, perY: perY, src: "auto-grid", screen: [SW, SH] };
try { files.write(files.join(DIR, "board.json"), JSON.stringify(cfg)); } catch (e) {}

try {
  let cv = new android.graphics.Canvas(img.getBitmap());
  let p = new android.graphics.Paint();
  p.setStyle(android.graphics.Paint.Style.STROKE);
  p.setStrokeWidth(6); p.setColor(colors.CYAN);
  cv.drawRect(bx, by, bx + bww, by + bhh, p);
  p.setStrokeWidth(3);
  for (let c = 1; c < COLS; c++) cv.drawLine(bx + c * bww / COLS, by, bx + c * bww / COLS, by + bhh, p);
  for (let r = 1; r < ROWS; r++) cv.drawLine(bx, by + r * bhh / ROWS, bx + bww, by + r * bhh / ROWS, p);
  p.setStyle(android.graphics.Paint.Style.FILL); p.setColor(colors.RED);
  for (let r = 0; r < ROWS; r++)
    for (let c = 0; c < COLS; c++)
      cv.drawCircle(bx + c * bww / COLS + bww / COLS / 2,
                    by + r * bhh / ROWS + bhh / ROWS / 2, 7, p);

  // numbers baked into the image — a toast expires, this does not
  let tp = new android.graphics.Paint();
  tp.setColor(colors.YELLOW); tp.setTextSize(40); tp.setFakeBoldText(true);
  let lines = [
    "AUTO-GRID  sel " + (bww / COLS).toFixed(0) + "x" + (bhh / ROWS).toFixed(0),
    "BOARD " + bx + "," + by + " " + bww + "x" + bhh,
    "periode " + perX + "x" + perY + "  " + COLS + "x" + ROWS
  ];
  let bp = new android.graphics.Paint();
  bp.setColor(colors.BLACK); bp.setAlpha(200);
  cv.drawRect(0, 0, BW, 30 + lines.length * 48, bp);
  for (let i = 0; i < lines.length; i++) cv.drawText(lines[i], 12, 36 + i * 48, tp);

  let out = files.join(DIR, "grid.png");
  images.save(img, out);
  try { android.media.MediaScannerConnection.scanFile(context, [out], null, null); } catch (e) {}
  console.log("png: " + out);
} catch (e) { console.log("gambar gagal: " + e); }

try { img.recycle(); } catch (e) {}
console.log("=== SELESAI. grid.png harus pas di tengah tiap sel ===");
toast("Selesai. Cek grid.png dari " + DIR, 9000);
