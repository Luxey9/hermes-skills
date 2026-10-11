---
name: image-ocr
description: "Use when reading text from an image: Windows OCR fallback."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [OCR, Images, Screenshots, Windows, PowerShell, Text-Extraction]
    category: media
    related_skills: [tim-riset]
---

# Image OCR (Windows built-in engine)

Read text out of a local image — screenshot, photo of a poster, scanned page —
when `vision_analyze` cannot see it. Windows ships a real OCR engine
(`Windows.Media.Ocr`); drive it from Windows PowerShell 5.1. No installs, no
Tesseract, works offline.

## When to Use

Use this when the user attaches an image you must *read as text* (poster,
flyer, form, table) and the vision route fails or is unavailable. If
`vision_analyze` works, use it first — it also describes layout, which OCR
does not.

## Procedure

① Try `vision_analyze` **once**. If it reports no vision support, do not retry
it — switch to this route immediately.

② Run the bundled script (path = this skill's `scripts/win_ocr.ps1`):

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill_dir>/scripts/win_ocr.ps1" \
  "C:/path/photo.jpeg" "C:/path/photo.ocr.txt"
```

Use **forward-slash native Windows paths**. Lines come back through stdout in
reading order and are written UTF-8 to the out file.

③ OCR is a raw pass, not truth. Stylized fonts, logos and tight kerning drop
glyphs (stray single letters, mangled numerals). Read for the *message* (names,
dates, URLs, numbers); when a proper name or figure matters for the answer,
verify it with one `web_search` before quoting it.

④ If output is garbled, preprocess with PIL and rerun on the upscaled copy:
convert to grayscale, `ImageOps.autocontrast`, resize ×2 with `Image.LANCZOS`.
The engine's `MaxImageDimension` is 10000 px — stay under it.

⑤ **Terminal / log screenshots need per-line cropping.** The engine reads a
screenshot better when the lines are isolated and blown up than when it scans the
whole panel: find the text bands from a brightness row-profile, stack them into
one tall strip with a few px of padding, then ×4 `INTER_LANCZOS4` + min-max
normalise + Otsu binarise before OCR. Whole-panel OCR on a green-on-black console
returns "seconds." and timestamps while dropping every payload field.

⑥ **Wrapped lines are unrecoverable — re-derive instead of re-OCRing.** A long
JSON line wraps at the screen edge, so the numeric fields are half off-image.
Cross-check what did come back (a per-step size, a device dimension) against
values the script chose itself (marker start positions, ratios) to reconstruct
the missing fields arithmetically. Do not loop more OCR passes on a crop that is
physically missing the pixels.

## Why the bundled script looks the way it does (pitfalls baked in)

- **`GetFileFromPathAsync` faults in PowerShell 5.1 scripts.** Read bytes with
  `[System.IO.File]::ReadAllBytes` into an `InMemoryRandomAccessStream` via a
  `DataWriter` (`StoreAsync` → `DetachStream` → `Seek(0)`) and hand that to
  `BitmapDecoder.CreateAsync`. Do not fight the file-based async call.
- **Every WinRT async call needs the reflection `Await` helper** (picks the
  single-arg `AsTask` overload, `.MakeGenericMethod`, `.Wait(-1)`). Without it,
  you get `AggregateException` and no inner text — the classic wasted hour.
- **Run it with `powershell.exe` (5.1), not `pwsh`.** PowerShell 7 dropped the
  easy WinRT projection; 5.1 is the supported host for `Windows.Media.Ocr`.
- **Check `AvailableRecognizerLanguages` before assuming a language pack.**
  On a machine with only `en-GB`/`en-US` installed, Latin-script Indonesian
  still OCRs fine — pick engine: `id` if present, else user-profile, else
  `en-US`. Non-Latin scripts genuinely need their pack installed.
- **The script prints diagnostics to stdout first** (decoded size, languages,
  engine) — ignore those lines when reporting results.

## Verification

Re-read the out file after the run. Success = reading-order text that contains
the poster's headline, organizer and at least one date/number. If only logos
and hex come back, upscale + autocontrast once, then stop and tell the user
what was legible instead of guessing the rest.
