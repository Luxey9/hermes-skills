---
name: android-screen-automation
description: Automate Android apps by screen with AutoJs, ADB or bots.
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [autojs, autox, android, automation, adb, emulator, game-bot, screen-capture]
    related_skills: [computer-use, node-inspect-debugger, web-app-runtime-verification]
---

# Android Screen Automation

## When to Use

- User wants a phone app driven automatically: game bot, auto-tap, auto-farm,
  auto-checkout, screenshot-driven matching loop.
- User has an AutoJs/AutoX script that will not stop, mis-taps, or cannot find
  the game board.
- User asks where a script's saved files live on the phone.
- User wants a web/browser route for something already walled behind app login —
  confirm the login wall before committing to it.

Target device is the user's own phone unless stated otherwise.

## Core Principle

Build the whole runnable artifact and hand it over with a kill switch and a
calibration block. The agent cannot edit the phone, so every unknown becomes a
named constant plus one screenshot round trip — never a silent guess.

## Pick the runtime in ONE line, then build

Do not open with a menu of five approaches. Name the recommended one, say why in
a clause, and start building. The user came to build, not to choose.

| Situation | Runtime |
|---|---|
| User already has the app on their phone, no root | **AutoJs6 / AutoX.js** — accessibility + screen capture, JS, no root |
| Needs deterministic, high-frequency input; PC available | **Emulator (LDPlayer/BlueStacks/MEmu) + ADB** — `adb exec-out screencap -p` + `adb shell input tap x y` |
| Web app, browser is enough | Playwright/Selenium, but **check for a login wall first** — most shop apps redirect to an auth page |

Web-first is usually a trap: `games.shopee.co.id/*` redirects to
`shopee.co.id/buyer/login`. Verify the real game surface renders before promising
a browser route.

## Build order — follow it every time

1. **Ask nothing, build the whole thing.** Hand over the complete runnable file,
   not fragments with "you'd add the loop here". The user runs it on the phone
   where the agent cannot edit it.
2. **Put every guess in a named constant block at the top** (`BOARD`, `COLS`,
   `ROWS`, `BTN_*`, thresholds). The user calibrates by editing numbers, not code.
3. **Calibrate from evidence, not estimates.** Emit `toast(device.width + "x" + device.height)`
   and have the script save a screenshot at the moment it needs a coordinate.
   Then tell the user: run it, send me that screenshot, I'll read the coordinates.
   This turns guesswork into one round trip.
4. **Always ship a kill switch.** See below — it is not optional.
5. **Put a startup countdown before anything appears on screen** (~7 s,
   `toast` a number each second). The user must switch back to the target app
   first; the floaty and `requestScreenCapture` come *after* it, not before.
6. **Verify the pure logic locally before shipping.** A matching/solver function
   can be ported to plain Node with synthetic data and asserted in one file
   (`console.assert` + a `node check_*.js` run). Proves grouping and thresholds
   without the device. Device-free verification is the only verification the
   agent can actually perform here — do it.

## Kill switch — non-negotiable, two mechanisms

A bare `while(true)` leaves no exit and the user is stuck rebooting the app.

- **In-script flag, checked every iteration AND inside inner loops.**
  `let running = true;` → `while (running && loop++ < MAX_LOOP)`. Check `running`
  in the inner tap loop too, so a stop does not wait for a batch of taps to drain.
- **`MAX_LOOP` safety net** for a forgotten stop.
- **Floating button** (`floaty.rawWindow` + a STOP button). Requires the
  **"display over other apps"** permission — if the button is invisible, that
  permission is missing. Say so when handing it over.
- **Hardware volume keys** (`events.observeKey()` + `onKeyDown("volume_up")`).
  Always reachable even when a floaty is buried under a notification or keyboard.
  Ship both; the floaty is convenience, the volume key is the guarantee.
- **Close the floaty and `exit()` at the end.** Without it the overlay lingers
  after the script dies.
- **Run the work loop in `threads.start(...)`**, leaving the main thread on a
  `while (running) sleep(200)` guard. A blocking `press()` + `sleep()` on the main
  thread makes the stop button unresponsive — the exact bug the user reports as
  "no stop button".
- **Create the floaty only AFTER the startup countdown**, never before. An
  overlay lives on top of every app, so a floaty created at the top of the file
  covers the very screen the user must navigate during the wait — the delay
  achieves nothing. Structure the file as: capture-permission → countdown →
  floaty + `events.observeKey()` → start worker. Declare `let win = null;` up
  top and assign it after the countdown; guard teardown with `if (win)`.
- **Place views with `marginLeft` / `marginTop` in the XML, not with
  `setPosition` / `setX` / `setY`.** Those three are absent on some forks and
  fail at runtime with "cannot find function". Layout attributes are applied at
  inflate and always work:
  `<button id="stop" w="110" h="110" marginLeft="20" marginTop="240" .../>`. For
  a view that must move at runtime, use the core Android API instead:
  `v.getLayoutParams().leftMargin = x; v.setLayoutParams(lp);` — same for
  reading it back.
- **When the user asks "did you actually add X?", answer with grep evidence.**
  Report the file, line numbers and the matching lines. Claiming an edit landed
  without showing it costs a full round trip and erodes trust when a second
  look reveals the edit was ineffective.

## Pitfalls that cost real time

- **Do not call `images.getSimilarity` / `images.findImage` / `images.findMultiColors`
  by name.** Names, signatures and return ranges drift between AutoJs6 / AutoX
  forks and versions. Read pixels with `images.pixel(img,x,y)` into a flat array
  and compare in plain JS. Returns 1.0 identical, 0.0 opposite — a range the
  agent controls and can unit-test off-device.
- **Clip coordinates can go negative at board edges** and throw. Guard with
  `Math.max(0, ...)` on every computed pixel coordinate.
- **Average a small block per sample point; never read one pixel per point.**
  Single-pixel samples carry JPEG noise, sub-pixel tile jitter and anti-aliasing,
  and those dominate the difference: a pair of genuinely IDENTICAL tiles scored
  only ~0.70 that way while different neighbours reached ~0.87 — the signal was
  inverted, and no threshold can rescue an inverted signal. Build each sample as
  the mean of a small block instead (`SIG_N` blocks per side, sub-sampling a few
  offsets within each). Working implementation:
  `references/vision-thresholds.md`.
- **`img.recycle()` / `clip.recycle()` after reading.** A capture every ~600ms in
  a long loop exhausts memory without it. Guard in `try/catch` — recycle on an
  already-recycled image throws.
- **The sample patch must sit INSIDE the artwork, and its size is the single
  biggest lever on match quality.** A patch sized as a majority of the cell
  overlaps the tile border and the surrounding background, so every tile's
  signature is dominated by the same frame and *all* tiles look alike — the solver
  then finds nothing while the log looks healthy. Measured on one 130 px cell: a
  72 px patch (0.55x pitch) gave p99 similarity **0.776** between genuinely
  identical tiles — below any usable threshold — while a 34-36 px patch (0.28x
  pitch) gave **0.971**. Use `CROP = round(pitch * 0.28)`, clamped ~24-40 px.
- **Threshold and patch size cannot be picked independently.** Tune them against
  the measured separation: identical tiles must score clearly above the threshold
  and different tiles clearly below. A threshold chosen without that measurement is
  a guess, and the failure it produces ("no match found") is indistinguishable from
  an empty crop. Measure with `references/vision-thresholds.md` before shipping.
- **Detect a blocking popup by brightness of a known region, not by hunting for
  the button.** Track a running `baseline` of the region's mean brightness; a
  drop below ~62% for 2 consecutive frames means a modal dimmed the screen. This
  needs no template and survives layout changes.
- **Save a screenshot the moment the popup is detected** (`/popup_<ts>.png`) and
  tell the user to send it back. Guessing popup button coordinates blind is pure
  waste; one saved frame makes the next correction trivial.
- **Button coordinates that only appear on failure paths are unresolvable from a
  description.** If the user cannot produce a screenshot, say the coordinate is a
  placeholder explicitly — do not present a guess as calibrated.
- **Lint/"SyntaxError" from a host-side checker on AutoJs files is a false
  alarm.** Node cannot parse the `<frame>` E4X markup in `floaty.rawWindow`.
  Report it as expected rather than letting the user think the script is broken.
  To still get a real syntax check, strip the XML blocks and `node --check` the
  remainder — it catches genuine typos the false alarm hides:
  `re.sub(r'floaty\.rawWindow\(\s*<frame[\s\S]*?</frame>\s*\)', 'floaty.rawWindow(null)', src)`.
  Run it over every `.js` you hand over, and grep the same pass for
  `\.(setPosition|setX|setY|getX|getY)\(` to prove none survived.
- **No `&` anywhere in floaty XML (or in `toast()` strings).** The layout is
  parsed by a strict SAX parser: `&amp;` in an attribute value throws
  `InflateException: org.xml.sax.SAXParseException: unterminated entity ref` and
  the whole `floaty.rawWindow` call fails with `Failed to call method
  "floaty.rawWindow"`. The reported position points at the offending attribute
  (`@14:24 ... android:text`). Write the word (`dan`, `and`) instead — do not try
  to escape it, the parser handles entities inconsistently. After any edit, grep
  the file for `&`: the count must be zero (comments may keep one, strings may not).
- **`floaty.rawWindow()` does not keep the script alive.** When the script hits
  its last line AutoJs exits and tears the floaty down — symptom: "the buttons
  flash and vanish", "it just finishes after N seconds". A calibration/UI script
  needs an explicit main-thread sentinel, separate from the bot's kill switch:
  `let done = false;` → set `done = true` in the confirm button handler →
  `while (!done) sleep(300);` as the last statement. Without it the user never
  gets a chance to drag anything.
- **A screenshot may be landscape or show the app in only part of the screen.**
  Do not assume portrait. Compute the content bounding box first (bright-pixel
  column/row profile): if the bright region covers only part of the frame, the
  device was rotated, letterboxed, or in split-screen, and every coordinate
  derived from the full frame is wrong. The aspect ratio tells you the
  orientation; black bars tell you the content rect.

## Never put `floaty.rawWindow` XML inside a markdown code fence

The floaty layout is JSX-like `<frame>...</frame>` embedded in `.js`.
Markdown/GitHub-flavoured renderers treat `<frame>` inside a fenced block as an
HTML tag and **drop the rest of the block**, so the user receives a truncated
script that silently fails to parse. Same failure when the reply is echoed
through any HTML-rendering layer.

When printing a full AutoJs file in chat, either build the layout with explicit
JS calls instead of inline XML, or output the layout as a single line / escape
it so no bare `<frame>` tag appears at the start of a line. Always attach the
file as `MEDIA:` as well, and say which block is the layout so the user can
verify nothing was swallowed.

## Writing files on the device (Android 11+)

Storage access is the most common silent failure. `/sdcard` is an **alias** for
`/storage/emulated/0` — when the user asks "where is that path", give the real
absolute path, not the alias.

- Direct `/storage/emulated/0/<dir>` writes are refused on Android 11+ without
  "All files access".
- **The app-specific external dir always works permission-free** and is the
  right default:
  `/storage/emulated/0/Android/data/<package>/files/<dir>` — get it from
  `context.getExternalFilesDir(null)`.
- **Probe with a real write, not `files.ensureDir`.** `ensureDir` can succeed
  while the subsequent write is denied. Write a `.probe` file, then delete it.
- **Toast the resolved path at startup** (`toast("Simpan ke: " + DIR)`) so the
  user can find the folder without guessing which candidate won.
- Note for retrieval: Android 13+ stock file managers block browsing
  `Android/data`. Point the user at a third-party manager or `adb pull`.

## Working with this user

- **Paste the whole file into the chat when handing a script over.** This user
  says "kirim sini" and wants the complete runnable text inline — not a diff, not
  a description of what changed, not only a `MEDIA:` attachment. Attach the file
  *and* print it in a fenced block. Corrections land in the same shape: full file
  again, not "replace line 47 with …".
- **Answer in Indonesian**, terse. Code blocks, paths, commands and error
  strings stay verbatim in their original form.
- **Lead with the fix, not the survey.** When they say "can we do it on web
  first?" they want you to test it, not evaluate it.
- **Give the real path, never an Android alias**, and name the file manager step
  to actually reach it.
- Delivery format: one short hook line, a title, the full script in a fenced
  block, then only the constants they must fill in and why.

## Support files

- `references/autojs-api-notes.md` — API quirks, thresholds, pixel-signature
  matcher, popup detection, thread split, storage probing.
- `templates/autojs-bot-skeleton.js` — known-good AutoJs bot skeleton: constants
  block, optional `config.json` calibration load, countdown-then-floaty ordering,
  thread split, pixel-signature matcher, popup detect, safe file dir. Copy and
  change the constants.

## Verification checklist before handing a script over

- [ ] Startup countdown present, and the floaty is created *after* it (not before).
- [ ] Kill switch present: in-script flag + volume keys; flag checked inside the
      inner tap loop as well as the outer loop.
- [ ] `MAX_LOOP` cap set.
- [ ] `win.close()` and `exit()` at the end, guarded with `if (win)`.
- [ ] No `setPosition` / `setX` / `setY` anywhere — layout via `marginLeft` /
      `marginTop` or `getLayoutParams()`.
- [ ] Work loop runs in `threads.start`, main thread only guards the stop flag.
- [ ] No named image-matching API — pixel signatures compared in plain JS.
- [ ] Every derived pixel coordinate wrapped in `Math.max(0, ...)`.
- [ ] `recycle()` calls in `try/catch`.
- [ ] All device-specific values grouped in a top constants block.
- [ ] Pure grouping/threshold logic asserted off-device with `console.assert`
      in a standalone Node file.
- [ ] Constants the agent cannot know are marked as placeholders in the reply,
      with the screenshot round trip to resolve them.
- [ ] Zero `&` in floaty XML and in `toast()` strings (grep proves it).
- [ ] Calibration/UI-only scripts park the main thread on a `while (!done)`
      sentinel, so the window survives until the user confirms.
- [ ] The complete file is printed in the reply, not just attached — and the
      `floaty` XML block did not get eaten by markdown HTML rendering.
