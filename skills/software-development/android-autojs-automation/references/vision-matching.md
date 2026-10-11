# Reading a screenshot programmatically

When the user attaches a screenshot, do not eyeball it. Load it and measure.
That is the difference between a calibrated script and three wasted rounds.

## 1. Orientation and letterboxing

- Landscape and portrait are easy to confuse when a phone app is shown on a wide
  canvas. Compare the image aspect ratio to the expected screen aspect ratio; a
  near-exact reciprocal means it is rotated, not reshaped.
- A wide canvas with a thin content band means the capture was letterboxed. Find
  the content bbox and work only inside it:

```python
import numpy as np, cv2
img = cv2.imread(path)
V = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2].astype(int)
cols = np.where(V.mean(axis=0) > 60)[0]   # content columns
rows = np.where(V.mean(axis=1) > 60)[0]   # content rows
x0, x1, y0, y1 = cols.min(), cols.max(), rows.min(), rows.max()
```

- Confirm orientation by the app's own chrome: find the saturated brand colour
  and check which fifth of the image it occupies. An aspect ratio that is the
  near-exact *reciprocal* of the expected screen (e.g. 1600×702 against a
  2462×1080 phone) means the capture is rotated, not reshaped — rotate it back
  before measuring anything else.

- **Read the verification overlay to confirm or reject a claimed calibration.**
  When the user says "the size already matches the script", treat that as a claim
  to check, not a fact. Locate the overlay markers by colour (the rectangle and
  the per-cell dots you drew), compare their spacing against the grid period
  measured from the screenshot, and check whether the overlay actually sits on
  the target region. Saying "the calibration is wrong, here is the measurement"
  with numbers beats running a 4000-iteration loop against the wrong rectangle.

## 2. Derive the scale factor, never assume it

Screenshots are frequently downscaled. Recover the factor from a *known* feature,
not from a guess at the phone model. If a marker you overlaid is 100 px in screen
space, measure its rendered size in the image and divide by 100.

State the estimate with its uncertainty and verify it. If the content width in the
image does not divide cleanly into any standard phone width, the assumption is
wrong — say so instead of picking the closest number.

## 3. Find the grid period

Autocorrelation of the edge-energy profile gives the cell pitch directly, and it
survives the grid being partly occluded:

```python
colP = np.abs(np.diff(gray_roi, axis=1)).sum(axis=0)   # vertical edges per x
rowP = np.abs(np.diff(gray_roi, axis=0)).sum(axis=1)   # horizontal edges per y

def autoperiod(sig, lo=20, hi=140):
    s = sig - sig.mean()
    ac = np.correlate(s, s, 'full')[len(s) - 1:]
    ac /= ac[0]
    return sorted([(k, round(float(ac[k]), 3)) for k in range(lo, min(hi, len(ac) - 1))
                   if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1] and ac[k] > 0.12],
                  key=lambda t: -t[1])[:5]
```

Harmonics of the true pitch (2×, 3×) appear as secondary peaks. The fundamental is
usually the *smallest* strong peak — but it can be half a cell when the tiles have
internal structure, so sanity-check by dividing the region width by the period and
seeing whether you get a plausible integer count.

## 4. Cluster detections into rows and columns

Median-of-cluster beats one bounding box: collect candidate centres, then merge
values within a tolerance.

```python
def cluster(v, tol=25):
    v = sorted(v); out = []; cur = [v[0]]
    for k in v[1:]:
        if k - cur[-1] <= tol: cur.append(k)
        else: out.append(sum(cur) / len(cur)); cur = [k]
    out.append(sum(cur) / len(cur)); return out
```

The spread of consecutive deltas tells you whether the grid is uniform. Deltas
differing by 30%+ mean the tolerance is merging two real rows.

## 5. Signature matching that survives fork differences

Downsample each cell to an 8×8 grid of RGB samples read with `images.pixel`,
flatten to 192 numbers, compare with mean absolute difference:

```js
function sim(a, b) {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]);
  return 1 - d / (a.length * 255);
}
```

On synthetic data identical patches score ~0.99 and clearly different colours
~0.49, so a threshold near 0.93 separates them with margin. Raise it if the app
has several icons sharing a colour theme.

**Deduplicate candidate signatures first.** Icon art often shares a large
identical background; group candidates by a coarse colour histogram and compare
only across groups, or every tile will match every other one.

## 6. Always leave a runnable check

Test the matching and grouping logic on synthetic signals — three near-identical
signatures plus one far-off one — with platform-free asserts, so the solver is
validated before it ever runs on the phone. A wrong threshold is invisible in
production and obvious in a test.

## 7. Text-first, always

There is no reliable way to "look at" a screenshot through prose. If no vision
route is available, render the image as a coarse character map — luminance ramp
plus hue letters — and read the layout, the letterbox bounds, and where regions
start and end. That is enough to catch a misplaced overlay before wasting the
user's time. See `scripts/img_ascii.py`.
