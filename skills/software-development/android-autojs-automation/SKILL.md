---
name: android-autojs-automation
description: "Automate Android apps on phone: AutoJs, ADB, clicks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Android, AutoJs, AutoX, ADB, ScreenAutomation, TemplateMatching, ComputerVision]
    category: software-development
---

## This skill is superseded

The maintained version of this material is **`autojs-android-automation`** — it
carries the current rules, the fork API quirks, and the support files
(`templates/screen-bot.js`, `references/autojs-recipe.md`,
`references/vision-matching.md`, `scripts/img_ascii.py`). Load that one.

Keep this file only for the two things it states more plainly, and prefer the
other skill for everything else:

- The **transport decision table** (AutoJs on the phone vs ADB + OpenCV on a PC)
  — decide this with the user before writing any code, because the same script
  does not port between them.
- The **pitfall list as a fast pre-flight read**, and
  `references/vision-matching.md` for image measurement.

---

# Android screen automation (AutoJs / AutoX / ADB)

Automate a phone app by looking at the screen: capture → locate targets → tap.
Covers game bots, auto-clickers, and any UI with no usable API.

## When to Use

Any request to drive an Android app automatically — "bot for <game>",
"auto click", "farm this app on my phone". Also when the user already has a
partly-working AutoJs script that misbehaves.

## Choose the transport first — ask before writing code

| Option | Use when | Trade-off |
|---|---|---|
| **AutoJs / AutoX on the phone** | User wants it on the phone | Accessibility service; needs overlay permission for a floating button |
| **ADB + OpenCV on a PC** | Emulator, or long unattended runs | Needs USB debugging; `adb exec-out screencap -p` + `adb shell input tap x y` |

Do not pick for them — the same code does not port. A game served in a browser
is not a native APK; confirm what actually renders before choosing.

## Procedure

① **Establish the real screen size and coordinate space.** Never assume.
In AutoJs: `toast(device.width + "x" + device.height)`.
A screenshot handed to you may be **letterboxed** (content in a sub-rectangle
with black bars) or **rotated** — measure the content bbox before deriving any
scale factor. See `references/vision-matching.md`.

② **Calibrate the target region by having the user point at it, not by guessing.**
Ship a drag-two-markers helper: a floating `floaty.rawWindow` with two
draggable buttons, the user drops one on the top-left and one on the
bottom-right of the target area, taps a button, and the script writes
`config.json` plus an overlaid verification PNG. Guessing coordinates from a
low-resolution screenshot wastes a full round trip per attempt.

③ **Make the main loop read that config**, not hard-coded numbers, so the user
recalibrates without editing code.

④ **Always add a kill switch. Two of them.** A bare `while(true)` loop cannot be
stopped and is the single most common complaint. Put a round STOP button in a
`floaty.rawWindow` *and* bind `events.onKeyDown("volume_up" / "volume_down")` to
the same stop flag — the floating button can be hidden behind a notification or
the keyboard, the volume key cannot. See `references/autojs-recipe.md`.

⑤ **Run the loop on a worker thread** (`threads.start`) and keep the main thread
in a short `while (state.run) sleep(200)` loop. Otherwise a blocking
`press()` + `sleep()` inside the loop makes the stop button unresponsive and the
user concludes the script is hung.

⑥ **Detect state changes by measuring, not by hunting for buttons.** To tell
"a popup is covering the play area", sample brightness at a few fixed points in
the target region and compare against a running baseline: a drop past a ratio
(e.g. `< baseline * 0.62`) for two consecutive frames means a dialog. Then tap a
configured button and save that frame to disk so the user can correct the
coordinate from evidence.

⑦ **Verify the loop terminates and exits cleanly**: close the floaty, `exit()`,
and report the iteration count. A swallowed exception must not leave a floating
window on screen.

## Pitfalls

- **Never write coordinates you have not measured.** Deriving them from a
  downscaled screenshot compounds two errors (scale factor + offset) and lands
  taps in empty space. Ask for the tap-two-corners calibration instead.
- **`if (images.getSimilarity(...) > 0.85)` is not portable.** API name, return
  range, and behaviour differ across AutoX / AutoJs6 forks. Implement similarity
  yourself over a downsampled colour signature read with `images.pixel()` — it
  works on any fork and you control the threshold.
- **`images.clip()` throws on negative coordinates.** Clamp tile-centre crops
  with `Math.max(0, ...)` — edge tiles sit exactly where the region starts.
- **Match on colour signature, not on raw pixels of a fixed patch.** Icon art can
  share large identical background regions; deduplicate candidate signatures by a
  coarse colour histogram before comparing them.
- **`/sdcard` is an alias for `/storage/emulated/0`, and writes there are refused
  on Android 11+** without all-files access. Try in order: `/sdcard/<app>/`, then
  `/sdcard/Android/data/<package>/files/<app>/`, then
  `context.getExternalFilesDir(null)`. Prove the location with a real write —
  `files.ensureDir` can succeed while `files.write` is denied. Toast the chosen
  path so the user knows where to look.
- **AutoJs XML literals (`<frame>`, `<button>`) are not Node-parseable.** Ignore a
  linter pointing at `SyntaxError: Unexpected token '<'` in a `.js` file that
  contains UI XML — a false alarm on the host, not a broken script.

## Supporting files

- `references/autojs-recipe.md` — floaty kill-switch + threaded loop skeleton,
  draggable calibration window, path-fallback helper, popup detection.
- `references/vision-matching.md` — reading a screenshot programmatically:
  letterbox/rotation detection, deriving grid period, colour-signature matching.
- `scripts/img_ascii.py` — render an image as a character map when no vision
  route is available.
