# Deriving the grid by autocorrelation

Depth for the "measure the pitch, never trust it" step. The short rules stay in
SKILL.md; this file holds the full routines.

## The trap: the global maximum is not the cell pitch

Artwork inside a tile repeats too, so the in-tile motif produces a strong peak at a
**sub-harmonic** of the real pitch. Taking the tallest lag yields a grid ~1.5–2×
too large, which taps the gaps between tiles and reads as "it taps outside the
board". Take the **first prominent** peak instead, then drop multiples of it — and
log every candidate with its relative strength so the harmonic structure is visible.

```js
function period(prof, lo, hi) {
  let n = prof.length, mean = 0;
  for (let i = 0; i < n; i++) mean += prof[i];
  mean /= n;
  let p = prof.map(function (v) { return v - mean; });

  let ac = new Array(hi + 1), maxAc = 0;
  for (let lag = lo; lag <= hi && lag < n; lag++) {
    let acc = 0;
    for (let i = 0; i + lag < n; i++) acc += p[i] * p[i + lag];
    ac[lag] = acc / (n - lag);
    if (ac[lag] > maxAc) maxAc = ac[lag];
  }

  let thr = maxAc * 0.70;
  let cands = [];
  for (let lag = lo + 1; lag < hi && lag < n - 1; lag++)
    if (ac[lag] >= ac[lag - 1] && ac[lag] >= ac[lag + 1] && ac[lag] >= thr)
      cands.push({ lag: lag, v: ac[lag] });
  cands.sort(function (a, b) { return a.lag - b.lag; });

  let list = [];
  for (let i = 0; i < cands.length; i++) {
    let dup = false;
    for (let j = 0; j < list.length; j++) {
      let ratio = cands[i].lag / list[j];
      if (Math.abs(ratio - Math.round(ratio)) < 0.08 && Math.round(ratio) >= 2) { dup = true; break; }
    }
    if (!dup) list.push(cands[i].lag);
    if (list.length >= 6) break;
  }
  console.log("  kandidat periode: " + cands.slice(0, 8).map(function (c) {
    return c.lag + "(" + (c.v / maxAc).toFixed(2) + ")";
  }).join(" "));
  return list.length ? list[0] : 0;
}
```

## Phase must be searched over the whole axis

Not `[lo, lo+pitch)`. A modulo-pitch phase search scores a fixed number of taps
starting anywhere, so a low-edge region (margin, app header, toolbar) can win and
the grid lands on chrome instead of the board. Brute-force the start position and
score the **sum of edge energy at every grid line** — dense-cell regions outscore
empty ones, so the board wins on merit:

```js
function bestPhase(prof, per, count, lo, hi) {
  let n = prof.length, span = per * count;
  let best = -1, bestStart = lo, lim = Math.min(hi, n) - span;
  for (let start = lo; start <= lim; start++) {
    let s = 0;
    for (let j = 0; j <= count; j++) {
      let idx = start + Math.round(j * per);
      if (idx < 0 || idx >= n) { s = -1; break; }
      s += prof[idx];
    }
    if (s > best) { best = s; bestStart = start; }
  }
  return bestStart;
}
let bx = bestPhase(colProf, perX, COLS, x0, x1);   // start = the first grid LINE
let by = bestPhase(rowProf, perY, ROWS, y0, y1);   // w = perX * COLS from there
```

## Snap each line, then take a uniform pitch from the span

Per-line snapping removes the accumulated drift of a slightly-wrong pitch, but
snapping alone can jump to a neighbouring line. Constrain the search to a fraction
of the pitch around each expected position, then recompute the pitch from the first
and last snapped line so it is uniform across the board:

```js
function snapLines(prof, start, per, count, frac) {
  let lines = [start];
  for (let k = 1; k <= count; k++) {
    let g  = start + per * k;
    let lo = Math.max(0, Math.round(g - per * frac));
    let hi = Math.min(prof.length - 1, Math.round(g + per * frac));
    let bw = -1, bi = Math.round(g);
    for (let i = lo; i <= hi; i++) if (prof[i] > bw) { bw = prof[i]; bi = i; }
    lines.push(bi);
  }
  return lines;
}

let LX = snapLines(colProf, sx0, perX0, COLS, 0.25);   // frac 0.25, not 0.30
let perX = (LX[COLS] - LX[0]) / COLS;                  // uniform pitch
```

A `frac` of 0.30 is loose enough to let a line snap onto its neighbour; 0.25 is the
practical ceiling.

## Three gates, all of them cheap

1. **Magnitude.** Search the lag window at the physically possible range (a card
   spanning ~1/7 of a 1080 px screen is ~130 px, so search `118..142`), then reject
   `per < 115 || per > 145`. A pitch 25 % too large still passes a span-only check
   and grows the board past the real one.
2. **Span.** `pitch × count` must fill the scan area:

   ```js
   function plausible(per, count, extent) {
     if (per <= 0) return false;
     return per * count > extent * 0.45 && per * count <= extent * 1.05;
   }
   ```

3. **Edge score.** 3–6× the mean at every line is a real board. Above ~12× the grid
   latched onto a repeated printed pattern (log rows, a list, a toolbar) — reject it.

```js
function edgeScore(prof, lines) {
  let m = 0;
  for (let i = 0; i < prof.length; i++) m += prof[i];
  m /= prof.length || 1;
  if (!m) return 0;
  let s = 0;
  for (let k = 0; k < lines.length; k++) {
    let a = Math.max(0, lines[k] - 2), b = Math.min(prof.length, lines[k] + 3);
    let mx = 0;
    for (let i = a; i < b; i++) if (prof[i] > mx) mx = prof[i];
    s += mx;
  }
  return s / lines.length / m;
}
```

## Pitch search: ONE value, not ±4 % trials

Trying `perX0`, `perX0 * 0.96`, `perX0 * 1.04` and keeping the best edge score looks
prudent and is not — the ±4 % variants only amplify a bad initial pick. Search one
pitch inside the physical range and validate the result. Give the loop a modest
redetect budget (`REDETECT_MAX = 2`); each redetect costs a full scan, so an
unbounded "keep re-detecting on stuck" loop makes the bot feel dead.

## Stale `board.json` is a poisoned input

A board file from another level parses as a perfectly valid region and silently
overrides the measurement. Apply the same pitch checks when loading it, and log the
rejection — otherwise the bot looks like it is ignoring your new code:

```js
let fx = c.w / c.cols, fy = c.h / c.rows;
if (fx < 115 || fx > 145 || fy < 115 || fy > 145) {
  log("  board.json DITOLAK: pitch " + Math.round(fx) + "x" + Math.round(fy));
  continue;                       // keep looking, fall back to auto-detect
}
```

## Stride the profile for speed

Sampling the edge profile every 4th pixel costs ~25 s on a full screenshot, while
the user sits watching a countdown that has already finished. Every 10th pixel is
indistinguishable for a ~130 px period and finishes in a few seconds:

```js
let colProf = edgeProfile(img, AX0, AY0, AX1 - 2, AY1, true,  10);
let rowProf = edgeProfile(img, AX0, AY0, AX1, AY1 - 2, false, 10);
```
