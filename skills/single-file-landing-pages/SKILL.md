---
name: single-file-landing-pages
description: Use when editing single-file HTML landing pages.
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [html, landing-page, single-file, geolocation, images, lucide, local-business]
    related_skills: [claude-design, popular-web-designs]
---

# Single-File Landing Pages

## When to Use

Any task that edits, extends, or debugs a portable single-file HTML landing page (inline CSS/JS, possibly base64 assets): adding sections, swapping card icons/photos, wiring booking/WhatsApp forms, adding geolocation, or fixing grid/layout regressions.

Maintain portable single-file HTML landing pages (one `.html`, inline CSS/JS) for local service businesses without breaking layout, inflating size, or silently shipping dead JS.

## Procedure

1. **Map structure before touching anything.** File is often 1–2 MB with base64 assets — never read it whole. Use narrow `read_file` windows (50–100 lines) plus `search_files` for `<section`, `<h2`, `id="`, `svc`, `bk-` markers. Identify the card grid, form IDs, and script blocks first.
2. **Edit surgically with `patch`, one target per call.** Anchor `old_string` on a nearby unique line (e.g. the `<h3>` title), not on a generic tag that repeats. When a script edit risks clobbering neighbors, read the exact window first, then patch.
3. **Rebranding / Brand Rename Checklist:** When updating a brand name across the page, search case-insensitively with `search_files` across the whole file first. Always update all touchpoints together:
   - `<meta name="description">` and `<title>`
   - Header navbar logo & footer brand text
   - Hero section lead copy and image `alt` texts
   - Interactive components: chatbot panels/avatars, bot welcome greetings, and dynamic WhatsApp message templates (`lines = [...]` in booking/consultation scripts)
   - Verify remaining occurrences with a final `search_files` regex check before reporting done.
4. **WhatsApp URL & Emoji Encoding:**
   - Prefer the canonical endpoint `https://api.whatsapp.com/send?phone=NUMBER&text=ENCODED_TEXT` over `wa.me`, which frequently fails to decode multi-byte emoji UTF-8 characters across various web/mobile client wrappers.
   - When joining message lines in JS, join with `\r\n` (CRLF) and encode via `encodeURIComponent()`. Beware of file editing tools accidentally inserting unescaped literal raw line breaks into JS string literals (`lines.join("\n")` -> `lines.join("\r\n")`), which breaks JavaScript syntax and kills all subsequent event listeners (animations, form submissions, buttons).
5. **Keep photos OUT of the single file.** Compress AI/user photos with ffmpeg (`-vf scale=960:-2 -q:v 4`) into a sibling `img/` folder and reference relatively (`img/name.jpg`). Total images should stay under ~1 MB. Hero loads eager with `fetchpriority="high"`; everything else gets `loading="lazy"` plus explicit `width`/`height`.
   - Already shipped with base64 blobs baked in? Extract them with a script rather than by hand — see `references/seo-and-page-weight.md`. BOTH `src="data:image/…"` and `data-full="data:image/…"` (lightbox originals) hold blobs; a `src`-only regex leaves the largest ones behind and the file stays multi-MB.
6. **Verify inline JS by extraction, not eyeballing.** Extract the `<script>` block and run `node -c` (check syntax) on it immediately after editing. A silent syntax error in inline JS halts execution for the entire document, disabling buttons and scroll reveal observers.
7. **Tell the user to hard-refresh.** Local `file://` opens cache aggressively — state `Ctrl+Shift+R` or close/reopen the tab after every edit round.
8. **Verify the deliverable over HTTP, not by eye.** Start a static server and fetch every local reference the HTML makes; assert 200 AND non-zero bytes. `curl -s -o /dev/null -w '%{http_code}'` proves routing but not content, and `/dev/null` is not path-translated when passed to a native binary from Python `subprocess` on this host — probe with `urllib.request` inside Python and check `len(resp.read())`. See `references/seo-and-page-weight.md` for the full audit script pattern.

## Card Layout Rule

- Either ALL service cards carry a photo or NONE do. One photo card inside a `stretch` grid forces text-only siblings to stretch into blank whitespace and reads as a bug.
- Default for 6–8 service cards: icon + title + text only, uniform height, no photos. Reserve photos for hero, one wide section, and genuine field documentation.
- Order inside a photo card is image first, icon + text after — mobile scanners see the visual hook in the first second. Keep a single aspect ratio (16/9) across all card photos so rows stay even.
- Never shrink a photograph into an icon slot. Icons are single-glyph stroke SVGs (Lucide-style, `stroke-width="2"`, one semantic metaphor per service); photos at 26 px become noise.

## Booking-Form GPS Recipe

- Add a `type="button"` GPS button under the address textarea plus a status `<p aria-live="polite">` and a hidden `lat,lng` input.
- On click: disable button, show "requesting location", call `navigator.geolocation.getCurrentPosition` with `{ enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }`.
- On success: store `lat,lng`, strip any prior location line from the textarea with a regex, then append a Google Maps `?q=lat,lng` link so it rides along in the WhatsApp message.
- On failure map `err.code`: 1 = permission denied, 2 = unavailable, 3 = timeout — each with a fallback line telling the user to type the address manually.
- Declare GPS needs HTTPS (or localhost); on `file://` some browsers block geolocation, which is environment behavior, not a code bug.
- Keep pre-existing validation (e.g. date `min=today`) untouched; declare new element IDs before the script block that references them.

## Pitfalls

- Patch `<img>` swaps with a regex anchored on the wrapping div (`hero-art`, `why-art`), never on `src="data:…"` alone — the base64 blob is megabytes long and truncates matches.
- Replacing icons? Match on the full `<svg …>…</svg>` plus its adjacent `<h3>` title, since bare `<path d="…"/>` strings repeat across decorative SVGs.
- Splitting or merging cards changes the grid count — re-verify card count and titles after, because a duplicated or orphaned card is easy to miss in a 1600-line file.
- When renaming brands across a single-file page, check dynamic JS string generators (e.g. WhatsApp message builders for consultation/booking forms) and chatbot config greetings — failing to update these leaks stale brand names into user messages.
- Always run syntax verification (`node -c`) on inline scripts after patching text in JS code blocks — a single unescaped literal newline inside a string breaks JS execution, silently killing scroll animations and click handlers.
- When the user says drop the photos for simplicity, remove the `<img>` tags AND their now-dead CSS in the same pass — leftover rules silently affect future cards.
- **A JSON-LD edit fails silently — parse it after every change.** Nothing renders
  wrong when the `application/ld+json` block becomes invalid; the whole rich-result
  graph just stops being read. Extract the block and `json.loads` it after each
  edit, before touching anything else.
- **Verify a phone number's bytes before believing a patch failed.** `read_file`,
  `search_files`, and printed output mask long digit runs (`+6285219884425`
  renders as `+628****4425`), so a `patch` against the masked-looking string can
  report success and change nothing — the file was already right. Dump
  `[hex(ord(c)) for c in line]` and compare digits before rewriting; a hit of
  `count(old) == 0` on a line you can literally see means display masking, not a
  broken file.
- **A favicon is page weight too.** A 512 px PNG logo can be hundreds of KB on
  every visit; resize to 192 px and quantize (`convert('RGBA').resize((192,192),
  LANCZOS).quantize(colors=128, method=FASTOCTREE)`) — an order of magnitude
  smaller and still valid for `<link rel="icon">` and JSON-LD `logo`.
- **Reuse an existing class before writing new CSS for a repeated chip list.** A
  button-styled chip (`.chip`) works verbatim on `<span>`s for a coverage/keyword
  list — new rules drift from the design system and add weight. Check the class
  is not styled by element selector (`button.chip`) before reusing it.
- Answer in the user's language (Indonesian here), concisely, with file state reported as done — no preamble about what you will do, no fabricated preview output.
- **A regex rewrite that drops an attribute silently orphans a file reference.** After renaming or deleting extracted assets, re-run the reference audit — deleting the extracted `inline-*` copies broke two `<img src>` pointing at the old name, and only the audit caught it. Never delete extracted source blobs until the audit reports zero missing refs.
- **Duplicate `alt`/`width`/`height` attributes are invisible until you read the whole tag.** A hero `<img>` carrying two `alt` and two `width` pairs still renders, but the browser uses the first and the declared dimensions can lie about the real aspect ratio (CLS). After any image edit, print the full tag and check the attribute count.
- **Declared `width`/`height` must match the file's real pixel size.** Resizing an asset without updating the HTML attributes produces layout shift — which is a Core Web Vitals regression, i.e. a ranking cost, not just a cosmetic bug. Re-read `Image.size` after every resize and write the true values back.
- **Do not hide the mobile nav links without providing a replacement.**
  `@media (max-width:760px) { .nav-links a:not(.btn) { display:none } }` leaves a
  phone visitor with zero navigation — no section links, no area links, only the
  WhatsApp button. Every link must stay reachable below the breakpoint, whether via
  a real menu button or a visible top-of-page section.
- **A section below the fold of a long mobile page is effectively invisible.**
  Count the sticky header plus the fixed bottom bar plus the gallery before
  placing anything the user expects to be found; move a coverage/area section up to
  just after the hero rather than "somewhere before the FAQ", and shorten its nav
  label so it wraps to one line at 390 px.
- **Test client-side behaviour in jsdom, not through a browser session.** For any
  nav, menu, or toggle you add, build the DOM with `runScripts:"outside-only"`,
  polyfill `window.matchMedia` before `window.eval`-ing each inline script, then
  dispatch real events (`MouseEvent`, `KeyboardEvent`) and assert `hidden`,
  `aria-expanded`, and body classes after each one. It runs in seconds and covers
  open/close/escape/link-tap/breakpoint paths a screenshot cannot. Keep it as
  `tools/test_mnav.js`.

## Mobile menu pattern

When the phone header has no room for section links, add a full-screen menu rather
than a drawer that fights the sticky header:

- Button in the header, `display:none` by default and `inline-flex` under the
  breakpoint; closed by default, `aria-expanded` kept in sync, `aria-controls`
  pointing at the panel. Panel is `hidden` in the markup so no-JS visitors still see
  a working page.
- Panel is `position:fixed; inset:0` with its own sticky head (brand + close),
  a nav list, a two-column grid of every area page, then the WhatsApp/call CTAs.
- Lock scroll with a `body.mnav-open { overflow:hidden }` class, and close on X,
  `Escape`, any link tap (so the anchor target is visible), and a
  `matchMedia("min-width:…")` change back to desktop. Restore focus to the button
  on close.
- Rows ≥48 px and the button ≥44 px — a local-service visitor on a phone is often
  tapping one-handed, outdoors.

## Going deeper

- `references/seo-and-page-weight.md` — extracting base64 blobs, thumbnail/lightbox image pairs, JSON-LD `@graph` for a local service business, title/description length gates, robots/sitemap, and the audit script.
- `references/location-pages.md` — growing the page into a generated set of per-district pages: shared stylesheet, one data-driven template, per-page schema, checker script, sitemap regeneration, scaling the data out of the template.
- Mobile chrome: `## Mobile menu pattern` above for the header menu, and
  `references/location-pages.md` for keeping every area page reachable from it.
- Once the page work ships, the off-page half (Google Business Profile probe, review levers, Search Console submission) lives in the `local-seo-audit` skill — load it instead of improvising a checklist.
