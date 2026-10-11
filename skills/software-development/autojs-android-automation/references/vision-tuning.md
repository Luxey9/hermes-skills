# Tuning the matcher offline

One phone round-trip costs minutes and a re-paste of the script. The same numbers
`signature()` and `sim()` will produce on the phone can be computed **on a saved
screenshot in Python** in under a second, and the tuning sweep is what turns an
endless "still not tapping" loop into a single decisive edit.

Do this **before** asking the user to run the bot again. Ask them for one
screenshot with the board visible; everything below runs offline.

## Setup

Resize the upload to device coordinates first — the upload is downscaled and any
measurement taken on it is scaled wrong:

```python
import numpy as np, cv2
img = cv2.resize(cv2.imread(path), (1080, 2460), interpolation=cv2.INTER_LANCZOS4)
H, W = img.shape[:2]
```

## 1. Find the true grid pitch yourself

Do not take the pitch from the user or from the script's log — measure it. Edge
energy per column and row, then the strongest local peaks:

```python
a = img.astype(int)
colE = np.abs(a[:, 1:, :] - a[:, :-1, :]).sum(axis=2).sum(axis=0)   # per column
rowE = np.abs(a[1:, :, :] - a[:-1, :, :]).sum(axis=2).sum(axis=1)   # per row
```

Group runs above a threshold to get line candidates; the spacing between adjacent
strong lines is the pitch. `grid_lines_x` = `n+1` lines for `n` columns.

## 2. Port `signature()` and `sim()` exactly

Any difference from the phone's sampling means you are tuning a different function.
Mirror the block-averaging, the `bs = CROP // SIG_N` block size, and the 3-point
sub-sampling per block:

```python
SIG_N = 4

def signature(cx, cy, CROP, img, H, W):
    bs = max(2, CROP // SIG_N)
    h  = bs // 2
    x0, y0 = round(cx - CROP / 2), round(cy - CROP / 2)
    sig = []
    for by in range(SIG_N):
        for bx in range(SIG_N):
            rr = gg = bb = n = 0
            for dy in range(-h, h + 1, h or 1):
                for dx in range(-h, h + 1, h or 1):
                    px, py = x0 + bx * bs + h + dx, y0 + by * bs + h + dy
                    if px < 0 or py < 0 or px >= W or py >= H:
                        continue
                    c = img[py, px]
                    rr += int(c[2]); gg += int(c[1]); bb += int(c[0]); n += 1
            if n == 0: rr = gg = bb = 0; n = 1
            sig += [rr / n, gg / n, bb / n]
    return np.array(sig, float)

def sim(a, b):
    return 1 - np.abs(a - b).sum() / (len(a) * 255)
```

## 3. The decisive sweep: which `CROP` separates at all

For every candidate `CROP`, build all signatures once and look at the
**similarity distribution over every pair** — not just the top pair. What you are
looking for is a gap: identical cards high, different cards low.

```python
for CROP in (30, 36, 44, 56, 72):
    S = np.array([sim(...) for each pair of cells])
    print(f"CROP {CROP:3d}  max {S.max():.3f}  p99 {np.percentile(S,99):.3f}  "
          f"p95 {np.percentile(S,95):.3f}  median {np.median(S):.3f}  "
          f#>0.95 {(S>0.95).sum()}")
```

Read it like this:

- **`max` near `1.000` while `median` is ~0.7** — bimodal. One population is flat
  background matching itself; the tiles are the low mode. Do not tune the threshold
  to this; fix `CROP` and re-run.
- **`max` well below the threshold you want to use** — the patch is broken. On a
  130 px tile, `CROP 72` peaked at **0.776** (impossible to match anything) while
  `CROP 30–36` reached **0.960–0.971**. That single number was the whole bug.
- A good `CROP` shows a **clean gap**: identical pairs ~0.96+, different pairs
  under ~0.93. Pick the threshold in the gap, not at the edge of it.

Cross-check with the cell-centre energy profile — edge energy by radius from the
cell centre. A peak at **r ≈ 35–45 px on a 130 px tile is the card border**, and a
patch large enough to include it makes every tile look alike:

```python
yy, xx = np.mgrid[-65:65, -65:65]
r = np.sqrt(yy**2 + xx**2).astype(int)
# accumulate edge magnitude E[y0:y1, x0:x1] into bins by r, divide by counts
```

## 4. Resolve ambiguity with the signature population

`flat`-detection alone misses background that is not perfectly uniform. Count, for
each cell, how many *other* cells it matches above the threshold:

```python
# real cards -> exactly 2 matches (the other two members of their triple)
# background  -> 4 or more (margin, inter-cell gaps, tray)
```

A histogram dominated by `3` means every card is accounted for and the matcher will
work. A histogram with a large `4+` bucket means the grid still covers empty space —
go back to step 1, the region is wrong, not the threshold.

## 5. Verify against a public reference image first

If the board can be seen in any public screenshot, validate the whole approach on
that first. Public content is supersampled, so absolute similarity numbers run
*colder* than on device JPEG — use it to confirm **structure** (is the grid 7×9, do
identical icons cluster) not to fix the final threshold. State that caveat when you
report numbers from it. A screenshot the user supplied is the only thing you should
tune the shipped threshold on.
