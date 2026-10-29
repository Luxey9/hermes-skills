# App icon: flat PNG → transparent .ico → wired everywhere

Use when the user hands over a logo image and says "make the icon fit", "remove
the white background", or sends a new icon after a rebrand. Applies to any
Windows desktop build (Electron installer, portable exe, shortcut icon).

---

## 1. Diagnose the source before writing any code

```python
from PIL import Image
im = Image.open(src)
print(im.mode, im.size)                        # RGB + 1024x1024 = no alpha
print([im.getpixel(p) for p in [(0,0),(1023,0),(0,1023),(1023,1023)]])
```

A logo exported from a design tool or a screenshot is almost always **RGB with a
solid background**. Windows then paints that background as a square around the
rounded shape — the user sees "the icon has a white box". Saving the same PNG as
`.ico` does not help: the pixels are still opaque.

Do not "remove white" globally. The logo's own lettering is usually white and
will be punched out. Only the white **connected to the border** is background.

---

## 2. Cut the background

```python
from PIL import Image, ImageFilter
from collections import deque
import numpy as np

im  = Image.open(src).convert("RGBA")
W, H = im.size
arr  = np.asarray(im).astype(np.float32)
minc = arr[:, :, :3].min(axis=2)          # whiteness = how high the darkest channel is

# flood fill near-white from every border pixel (BFS, 4-neighbour)
whiteish = minc >= 238
visited  = np.zeros((H, W), bool)
q = deque()
for x in range(W):
    for y in (0, H-1):
        if whiteish[y, x] and not visited[y, x]: visited[y, x] = True; q.append((x, y))
for y in range(H):
    for x in (0, W-1):
        if whiteish[y, x] and not visited[y, x]: visited[y, x] = True; q.append((x, y))
while q:
    x, y = q.popleft()
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = x+dx, y+dy
        if 0 <= nx < W and 0 <= ny < H and not visited[ny, nx] and whiteish[ny, nx]:
            visited[ny, nx] = True; q.append((nx, ny))
sil = ~visited                              # silhouette, holes (white text) filled in
```

`sil` is hole-free because enclosed white never connects to the border.

---

## 3. Rebuild alpha at the edge instead of trusting the mask

A binary mask blurred into alpha leaves **white halo** pixels: the original edge
pixels are literal `(255,255,255)` blended over the background, so any alpha you
assign them keeps them white. Estimate alpha from luminance across a band:

```python
core = sil.copy()                           # erode 4 px -> fully opaque interior
for _ in range(4):
    e = core.copy()
    e[1:, :] &= core[:-1, :]; e[:-1, :] &= core[1:, :]
    e[:, 1:] &= core[:, :-1]; e[:, :-1] &= core[:, 1:]
    core = e

DARK  = 40.0                                # darkest channel of the icon's own rim
alpha = np.zeros((H, W), np.float32)
alpha[core] = 255.0
band = sil & ~core
alpha[band] = np.clip((255.0 - minc[band]) / (255.0 - DARK), 0, 1) * 255.0
a = np.asarray(Image.fromarray(alpha.astype(np.uint8), "L")
               .filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32)
a[core] = 255.0; a[~sil] = 0.0
alpha = a

# unmix the colour that was composited over white: C = (P - 255(1-a)) / a
af = np.clip(alpha / 255.0, 1e-6, 1.0)[:, :, None]
C  = np.clip((arr[:, :, :3] - 255.0 * (1.0 - af)) / af, 0, 255)

out = np.dstack([C.astype(np.uint8), alpha.astype(np.uint8)])
out[alpha < 6] = 0
img = Image.fromarray(out, "RGBA")
```

Sanity check the result numerically — a clean edge looks like this and a halo
does not:

```python
print([(x, tuple(img.getpixel((x, 512)))) for x in range(0, 14)])
# clean: first visible pixel is dark, e.g. (57,77,110,102) then (9,26,52,186)
```

`DARK` is not a guess: sample the icon's outer rim. A glossy/metallic border will
genuinely be light *inside* the shape — that is design, not fringe, so keep the
luminance probe to the 4 px band.

---

## 4. Render master + multi-size ICO

```python
S, side = 1024, max(img.size)
inner = int(S * 0.985)                     # 1.5 % transparent margin, keeps corners
scale = inner / side
img = img.crop(img.getbbox()).resize(
    (round(img.width*scale), round(img.height*scale)), Image.LANCZOS)
canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
canvas.alpha_composite(img, ((S-img.width)//2, (S-img.height)//2))
canvas.save("icon-1024.png")
canvas.save("icon.ico", format="ICO", sizes=[
    (256,256),(128,128),(64,64),(48,48),(40,40),(32,32),(24,24),(20,20),(16,16)])
```

Verify every frame landed — PIL cannot enumerate ICO frames, but it reads the
directory:

```python
print(sorted(Image.open("icon.ico").ico.sizes()))   # must list all 9
```

Ignore any "still has a white halo" report that comes from looking at the icon on
a checkerboard whose light squares are #FFF — that reads as a white ring. Only
the pixel dump in step 3 is evidence.

---

## 5. Wire it into all three surfaces

An app icon is not one file. Miss a surface and the user gets a mixed brand
(installer new, Explorer old, taskbar original author's):

| Surface | What to touch |
|---|---|
| Win32 resource (Explorer, shortcut, taskbar, file Properties) | `rcedit` on the staged `<App>.exe`: `icon` **and** `ProductName`/`CompanyName`/`FileVersion` |
| NSIS installer + uninstaller | `win.icon`, `nsis.installerIcon`, `nsis.uninstallerIcon` in `electron-builder.yml` |
| Window icon the app paints itself | `app/src/assets/icons/icon.ico` + `icon.png` inside `app.asar` |

- The bundled main process resolves its window icon as
  `path.join(app.getAppPath(), "src/assets/icons/icon.<ico|png>")` — that path is
  **inside the asar**, so dropping a file next to the exe does nothing. Grep
  `src/assets/icons` in the packed `main.js` to confirm the lookup before
  deciding where the asset goes.
- Repack the asar (`npm run pack` / `scripts/pack.mjs`), then copy the new
  `out/app.asar` into **both** the staged `appdir/resources/` and the portable
  folder, or the zip and the installer drift apart.
- A 2 MB `icon.png` inside the asar is dead weight: 512 px is plenty for a window
  icon. Shrinking it legitimately shrinks the asar — do not read a smaller asar
  as "files went missing" until the delta matches the png.
- rcedit rewrites the exe resource, so it must run **before** the installer is
  built — the wrapper copies the exe at build time. Re-wrap after any icon change.

---

## 6. Verify from the shipped artifact, not the intermediate

```bash
# the 32x32 icon the OS will actually draw, extracted from the exe itself
powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Drawing; \
  \$i=[System.Drawing.Icon]::ExtractAssociatedIcon('<abs>\<App>.exe'); \
  \$i.ToBitmap().Save('out.png',[System.Drawing.Imaging.ImageFormat]::Png)"
```

```python
import numpy as np; from PIL import Image
a = np.asarray(Image.open("out.png").convert("RGBA"))
print(a[0,0], a[0,-1], a[-1,0], a[-1,-1])      # alpha 0 on all four = transparent corners
print(int((a[:, :, 3] == 0).sum()))             # > 0; an opaque box gives 0
```

Run it on **both** the installed `<App>.exe` and the `Setup.exe` — it is the only
proof the resource was replaced rather than served from cache.

**Install the file you are about to hand over.** After a rebuild, copy the new
installer into the delivery folder *first*, then silence-install from that exact
path. Installing a stale copy from the delivery folder and reading the old icon
off it looks exactly like "the icon change did not apply" and burns a full
rebuild cycle to disprove.

If the user still sees the old icon on a machine where the file is already
correct, that is the Explorer icon cache, not the build:
`ie4uinit.exe -show` (or restart `explorer.exe`). Say so instead of rebuilding.

Report icon work as three lines — sizes embedded, corners transparent, which
surfaces were rewritten — plus the reminder that a new icon does **not** clear
SmartScreen: that warning is code signing, not artwork.
