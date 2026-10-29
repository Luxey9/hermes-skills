---
name: web-frontend-branding
category: software-development
description: 'Use when wiring a favicon/logo, or writing app icon prompts.'
---

# Web Frontend Branding

## When to Use

- Wiring a favicon, apple-touch-icon, or logo into a frontend `<head>` or static server.
- The user asks for logo / icon *ideas* for an app or product (`saran logo`, `saran icon`, `concept brand`) — deliver generator prompts per the section below, not asset files.
- Swapping an existing logo without breaking browsers' tab-icon cache.

## Procedure

1. Copy the logo asset into the served frontend dir (e.g. `frontend/logo.png`); keep the source filename stable so cached HTML query strings keep working.
2. Wire it in `index.html` `<head>`: `<link rel="icon" type="image/png" href="logo.png?v=N">` plus `<link rel="apple-touch-icon" href="logo.png?v=N">`; bump `?v=N` on every logo swap to bust browser tab-icon cache.
3. Verify the static server actually serves the extension: check its MIME map includes `.png` (e.g. `image/png`) and that the file path stays inside the served dir (path-traversal guards 403 otherwise).
4. Tell the user to hard-refresh (`Ctrl+Shift+R`); tab favicons cache aggressively and a normal reload often shows the old icon.

## Deliver prompts, not assets (default for "saran logo/icon")

When asked for logo/icon *ideas* for an app (`saran logo`, `saran icon`, `concept buat brand X`), the deliverable is **ready-to-paste image-generator prompts**, not SVG/PNG/ICO files. Ship the prompt set first; generate or trace assets only when explicitly asked (`bikin filenya`, `generate`, `jadikan ico`). Building assets unasked burns a long render cycle and gets thrown away.

1. Read the product first so the prompts are grounded: what the app *does* (one-line product metaphor) and its existing palette. Grep the codebase for hex tokens — `grep -rhoE "#[0-9a-fA-F]{6}" src --include="*.css" | sort | uniq -c | sort -rn | head -20` — and reuse the top accent colors inside the prompt text. Generic prompts produce generic icons.
2. Offer 3-4 named concepts on different axes: one **literal** (the product's own shape — safest, most legible), one **name/mythology** driven, one **outline/minimal**, one **material** (glass / neon / gradient). Give each a one-line "why it fits".
3. Write each prompt in English (generators parse it better) inside a fenced block, self-contained: shape, background gradient with hex values, accent gradient with hex values, lighting/bloom, style words, composition, `1:1`, `1024x1024`.
4. Add one master suffix block (negative prompt + flags) plus a plain-language version for DALL·E/Flux/Sora that cannot take `--` flags.
5. Close with a short decision table: squircle full-bleed, ONE symbol only, zero text, legible at 32px, grayscale contrast check.

Depth — concept archetypes, master suffix, palette defaults, prompt-failure modes: `references/app-icon-prompt-cookbook.md`.

## Pitfalls

- Never let text/letters into the prompt: generators reliably misspell the app name. Always carry `no text, letters, typography, watermark`.
- Do not hand over prompts without the palette step; colors invented for a prompt won't match the app they belong to.
- Replace placeholder favicons (`<link rel="icon" href="data:,">`) rather than adding a second link tag — duplicate icon tags resolve unpredictably across browsers.
- Confirm the MIME entry before shipping; a missing `.png` mapping serves `application/octet-stream` and some browsers ignore the icon silently.
