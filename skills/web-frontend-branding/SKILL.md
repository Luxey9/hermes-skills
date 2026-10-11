---
name: web-frontend-branding
category: software-development
description: 'Use when adding a favicon or logo to a web frontend.'
---

# Web Frontend Branding

## Procedure

1. Copy the logo asset into the served frontend dir (e.g. `frontend/logo.png`); keep the source filename stable so cached HTML query strings keep working.
2. Wire it in `index.html` `<head>`: `<link rel="icon" type="image/png" href="logo.png?v=N">` plus `<link rel="apple-touch-icon" href="logo.png?v=N">`; bump `?v=N` on every logo swap to bust browser tab-icon cache.
3. Verify the static server actually serves the extension: check its MIME map includes `.png` (e.g. `image/png`) and that the file path stays inside the served dir (path-traversal guards 403 otherwise).
4. Tell the user to hard-refresh (`Ctrl+Shift+R`); tab favicons cache aggressively and a normal reload often shows the old icon.

## Pitfalls

- Replace placeholder favicons (`<link rel="icon" href="data:,">`) rather than adding a second link tag — duplicate icon tags resolve unpredictably across browsers.
- Confirm the MIME entry before shipping; a missing `.png` mapping serves `application/octet-stream` and some browsers ignore the icon silently.
