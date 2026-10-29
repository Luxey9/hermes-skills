---
name: clone-web-ui
description: "Use when cloning a live site's UI 1:1 into a repo."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [clone, ui, css, dom, harvester, puppeteer, reference]
    related_skills: [reference-teardown, blocked-page-recovery, web-app-runtime-verification]
---

# Clone Web UI 1:1

Replicate a live site's look and interaction into another repo. The deliverable
is a screenshot-verified match, not "I wrote some CSS".

## When to Use

- "bisa copycat web ini?", "bikin mirip kayak <site>", "kloning UI-nya"
- Porting a palette, panel, toolbar, or node/card style from a reference app

## Procedure

1. **Identify the stack from the HTML shell first.** `curl -sL <url>` returns a
   tiny index.html for SPAs — read its `<script src>`/`<link href>` and treat
   those asset URLs as the real source. A 200 with 1–2 KB is an SPA, not a
   failure.
2. **Pull the CSS before touching the DOM.** CSS is plain text, unminified
   enough to grep, and carries every color token, spacing value, breakpoint and
   class name you need. This is the highest-value file per byte on the site.
3. **Dump the rendered DOM with a real browser.** `web_extract` gives a
   markdown approximation (text only, class names stripped). Use puppeteer-core
   against the user's installed Edge/Chrome instead:
   ```
   npm i puppeteer-core      # in the scratch dir, not the project
   puppeteer.launch({ executablePath: '<Edge/Chrome path>', headless: 'new',
     userDataDir: '<scratch>/edge-profile', protocolTimeout: 180000 })
   page.goto(url, { waitUntil: 'networkidle2' })
   page.evaluate(() => document.documentElement.outerHTML)
   ```
   Windows Edge: `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.
   Always pass `protocolTimeout` — a busy canvas app blocks `Runtime.callFunctionOn`
   and the default 30 s throws a `ProtocolError` mid-harvest.
4. **Harvest every interactive component's property schema**, not just the
   item list. Click one palette item, click the canvas, then read the inspector
   panel: group titles, field labels, input `type`, default `value`, and the
   `<option>` lists of every `<select>`. Repeat per component type. This is the
   whole product spec and it cannot be recovered later without redoing the run.
   - **Reload the page between types and confirm the placement landed.** A
     placement click that misses leaves the previous node selected, and the
     harvest silently labels the new type with the old type's panel. Gate each
     sample on BOTH signals: the status/empty text changed (`Placed <Type>`)
     and the Label input equals the type you just picked. A stale-label sample
     is worse than a missing one — it fabricates a duplicate spec.
   - Write each type's schema to a file as you go (`props-schema.json`), then
     re-harvest only the failed types. Never hold 20 schemas in memory and
     write once at the end; one protocol hiccup loses the whole run.
5. **Download the image assets.** `curl -A "Mozilla/5.0" <base>/images/<Name>.png`
   — bare curl gets 403 from CDNs that gate on UA; a UA string fixes it. Save
   into the target repo's `public/images/` so Vite serves them at `/images/x.png`.
6. **Port in this order:** palette → panels → header/toolbar → canvas chrome.
   Palette first because it is pure data (groups, order, labels, icons) and it
   immediately shows whether the CSS landed. Never port half of two areas.
7. **Verify in a real browser against the production build**: `npm run build`,
   `vite preview --port <p>`, then puppeteer: assert group titles, item labels,
   `img.naturalWidth > 0` for every icon, computed width, and click-place ->
   node count. Screenshot and read it with vision.

## Minified JS: what is worth extracting

- Skip the string-array obfuscator (base64 + rotated table + `decodeURIComponent`).
  Re-running the page in a browser is faster and gives the same strings.
- Do not chase source maps — modern builds ship none (`<asset>.js.map` -> 404).
- If a real value only exists in JS (defaults, option lists), harvest it from
  the live DOM instead of deobfuscating.

## Landing it in the target repo

- Copy the site's exact tokens first (panel, border, accent, radius, font size,
  item padding). A "similar" palette looks obviously wrong side by side.
- Match class names to the target's existing convention, then delete the old
  CSS block wholesale — leaving both (`pal__item` + `palette-item`) is how you
  get an unstyled palette that still renders.
- New component kinds must be added end-to-end in one pass, or TS fails:
  UI kind union -> engine `ComponentType` -> schema map entry -> `UI_TO_SCHEMA`
  + `nodeTypes` -> `DEFAULT_PARAMS` -> a node component. Missing any one of
  those five spots is a compile error, and for a non-electrical kind
  (annotation/note) the schema needs `ports: []` plus test thresholds relaxed
  from "every type has >=2 ports".
- Update the tests that encode old counts (`expect(types.length).toBe(20)`)
  rather than deleting them.
- **Derived panels are computed, not stored.** For summary/metric panels
  (totals, autonomy, sufficiency, worst-drop) write one pure
  `buildSummary(nodes, edges, solve, sim)` + a thin hook, and unit-test the
  numbers against expected arithmetic. Reading a field that looks like it
  should exist on the engine type but does not (`dropPct` on a wire-drop record
  that only carries `dropV`) yields `NaN` on screen with no error — assert the
  formatted value in a test and the miss surfaces as a wrong string instead.
- Mount a summary panel in **every** inspector state (nothing selected, edge
  selected, node selected) or it vanishes on first click; and give the panel
  `max-height: none` with the parent scrolling, since a percentage cap clips
  the last rows.

## Porting chrome that has state (header, sim bar, status bar)

Live controls must be wired to a real store, not rendered as decoration — a
header that looks identical but has dead buttons is the failure mode the user
detects first. See `references/header-and-sim-bar.md` for the layout skeleton,
the token list, and the puppeteer recipes. For panels that pull vendor data
(irradiance, weather, tariffs) see `references/third-party-api-proxy.md` —
browser fetches fail on CORS even when curl succeeds, and the fix is a Vite
proxy, not a rewrite of the client.

1. **Give the chrome its own small zustand store** (`src/lib/simClock.ts`):
   `{ hour, running, speedIndex, startHour }` + `setHour/toggle/resetSim`, with
   the speed table copied verbatim from the site (labels AND the seconds-per-
   second mapping — `'1 hr/s'` -> 3600). Export pure formatters
   (`formatClock -> 'HH:MM'`, `wrapHour`, `sunGlyph`, `irradiancePct`).
2. **Tick with `requestAnimationFrame` in one hook mounted once in App**, reading
   speed from the store inside the frame callback. Do not `setInterval` per
   component — duplicated ticks double the rate. Advance by
   `wrapHour(hour + dtSec * speed / 3600)`.
3. **Feed the clock back into the engine.** `solve(graph, irradianceAtHour(hour), soc)`
   instead of a hardcoded `1.0`, and add an optional `startHour` to the 24-hour
   simulator so the selected hour becomes the first simulated hour (rotate the
   hour list, keep absolute-hour irradiance). Copying the UI without wiring the
   engine leaves the numbers page-long wrong while every test still passes.
4. **Status bar as a module-level pub/sub**, not React context: `setStatus(text, tone)`
   writes a module variable and notifies subscribers; a `useStatus()` hook
   subscribes, and the canvas calls `setStatus` on place/select. Pair it with an
   event (`plts:place` / `plts:place-done`) so palette highlight and status text
   clear together.
5. **Header buttons map to real handlers** — Export -> design JSON, Import ->
   file input + parse, Share -> clipboard JSON with a download fallback,
   Forecast -> run the sim and switch tab, Delete -> remove selected node OR
   selected edge (same button, check which id is in the graph).

## Harvesting the model/catalog database

Builder apps gate half their value behind a Brand -> Model pair of `<select>`s in
the inspector. Harvest it the same loop as the schema, plus one inner pass.

1. Place the type, confirm the label matches (see the stale-sample gate above).
2. Read `<select>[0]` options -> brand list. Loop every brand:
   `selectOption(brand)` -> wait ~400 ms -> read `<select>[1]` options -> model
   list. Store `{ type: { brands, models: { brand: [models] } } }` to JSON.
3. **Launch one browser per type when types keep mis-landing.** The reliable
   shape for a stubborn type is a fresh `userDataDir` per run and a retry loop
   that returns early unless `label.startsWith(<expected>)` — cheaper than
   debugging shared state across 9 types.
4. **Do not trust labels for specs.** Only a prefix survives the boilerplate:
   most model names carry no numbers at all (`EU2200i`, `ST Blade 6 Circuit`).
   Write small extractors per type family and unit-test them:
   - watts: `/^(\d+)\s*W\b/i` (panel) and `/(\d{3,5})\s*W/` (inverter/genset)
   - amps: Victron-style `MPPT 100/50` means Voc/amps -> `/(\d+)\/(\d+)/`,
     take group 2 for amps and group 1 for max PV voltage; fall back to
     `/(\d+)\s*A\b/` for `Tracer 40A MPPT`
   - battery: `/(\d+)\s*Ah/` plus `/(\d+(?:\.\d+)?)\s*V\b/` for nominal volts
   - DC-DC: `/(\d+)\/(\d+)-(\d+)/` -> in / out / amps
   A model that yields nothing is still selectable; never fabricate a spec.

## Grouped inspector fields

Port the inspector as declared data, not JSX sprinkled per type: a
`PROP_GROUPS: Record<kind, {title, fields[]}[]>` table plus one `GroupRow`
renderer for `number | text | select | check`. Add a `Component` group
(Label + Copy/Paste Props + Flip) and a computed `Calculated` group
(L-L voltage, kVA, DC draw, daily Wh) rendered read-only.

- Copy/Paste Props is a module-level variable holding the last copied params —
  no store key needed, and it survives node switches.
- When a site button has no truthful equivalent ("Flip Terminals" repositions
  pins that your port derives from a schema), wire it to a `setStatus(...)`
  explanation. A button that pretends to do something is worse than one that
  says why it can't.
- Put the action buttons in ONE `.prop-row` with equal flex, else two of three
  wrap and the group looks broken (confirms only via screenshot/vision).

## Column layout: the flex child trap

The panel that "sits on the left" when the site has it on the right is a CSS
root-cause, not a component-order problem. Order lives in the CSS, so swapping
JSX children fixes nothing; a `flex: 1` child with a rigid-body parent
stretches full width and pushes its sibling to the next row, where it renders
flush left and reads as "on the left".

1. **Draw the wrapper tree before editing.** `grep -n 'Inspector />' App.tsx`
to see which element wraps both the content and the side panel — that element
is almost always the one missing `display: flex`.
2. **Give the wrapper the row, the inner container the column.**
   ```css
   .main  { display: flex; min-height: 0; overflow: hidden; }   /* row */
   .editor { display: flex; flex-direction: column; flex: 1 1 auto; min-width: 0; }
   .main > .side { flex: 0 0 290px; border-left: 1px solid var(--border); border-right: none; }
   ```
   `min-width: 0` is mandatory on every flex child that holds a canvas, or the
   canvas refuses to shrink and shoves the panel off-screen.
3. **Measure, never eyeball.** Print the bounding boxes of each column and
   reconcile against the viewport:
   ```js
   page.evaluate(() => [...document.querySelectorAll('.editor > *, .main > *')]
     .map(e => ({ cls: e.className, x: Math.round(e.getBoundingClientRect().x) })))
   ```
   `palette x=0 · canvas x=148 · side x=1210` in a 1500-wide viewport is proof;
   `side x=0` is the bug. Do this BEFORE the screenshot — vision confirms the
   result, geometry finds the cause.
4. Delete any earlier CSS that claims to place the panel. Two blocks fighting
   over the same selector (one appending `order`, one re-declaring
   `flex-direction`) keeps the wrong result with no error to follow.

## Pitfalls

- `search_files` the new class names in the CSS before believing a port landed.
  A rewritten component against site class names with zero CSS matches renders
  unstyled and still passes every render test (`pattern: 'palette-item',
  path: 'src/index.css'` returning 0 matches is the tell).- **Full-page `web_extract` is not a substitute for the rendered DOM** — it
  returns text only, with every class name stripped, so accordion sections
  render as their title glyph (`?`) and you cannot tell what is collapsible.
- When the browser tool refuses because the user's default profile is locked by
  a running browser, do not tell the user the tool is broken: launch
  `puppeteer-core` with its own `userDataDir` in the scratch dir and continue.
- **Compose the final JSX in one statement.** Patching a panel to appear in
two code paths by string-substituting the same tail twice yields duplicate
mounts (`<Settings />` twice, silently: no type error, no test failure). After
inserting a shared block into several returns, `grep -c` the component tag and
reconcile the count with the number of return paths.
- **Mirror the site's own honesty about vendor data.** If a cloned panel calls
  a third-party API (irradiance, weather, pricing), it fails in the browser for
  CORS reasons even when curl works — see `references/third-party-api-proxy.md`.
- Every session re-learning "CSS first, DOM second" costs a full harvest cycle —
  read the stylesheet before the markup.
- **Header/app chrome and schematic nodes (SVG, canvas, graph editors) belong to
  the HTML only when they ship server-rendered.** A canvas-based app (Konva,
  Fabric) draws components on `<canvas>` and the DOM holds just the palette and
  panels — rebuild node visuals from the PNG assets and inspector. Don't hunt
  for node markup that isn't there.
- Reading state from the inspector immediately after a click catches the
  PREVIOUS selection — poll until the Label input matches the type you placed.
- On mobile-width screens the palette becomes a fixed drawer; copy the
  breakpoint (`768px`, width, `translateX`) or the layout breaks on phones.

## Verify checklist

- `tsc --noEmit` clean, `vitest run` all green, `npm run build` succeeds
- **Column geometry asserted numerically** (see *Column layout*): palette at
  x=0, side panel ending at viewport width — before any screenshot
- Production preview + headless puppeteer reading the real DOM (`.calc-stat`,
  `.palette-item`, `img.naturalWidth`) — screenshot alone hides clipping
- `search_files` the target CSS for the new class names; a component written
  against new classes with zero CSS matches renders unstyled and still "works"
- Production preview opened headless: zero console errors, all icons loaded
- **Motion-verify anything animated.** Set the fastest speed and sample the clock
  (or counter) twice ~3 s apart; a fresh speed setting at a slow rate will not
  visibly move in a short window and reads as broken. Assert `t0 !== t1`
  programmatically, never by eyeballing a single frame.
- **Verify a live-recompute toggle by the data, not the switch.** A "digital
twin" / auto-solve checkbox proves nothing by being checked: run the sim, sample
a node meter twice a few seconds apart while the clock advances, and require the
  numbers to differ (`152 W -> 153 W`). Throttle the re-solve (~4 Hz) so the
  renderer does not starve, and bail out when the graph is empty.
- Render-test assertions on SSR output must strip React comment markers:
  `html.replace(/<!--.*?-->/g, '')` — `renderToString` inserts `<!-- -->` between
  adjacent text nodes, so `toContain('🗑 Delete')` fails on markup that is correct.
- Every palette type placeable by click; active state toggles
- Answer honestly which areas still differ — never "udah plek ketiplek" without
  the screenshot evidence behind it. Name the concrete leftovers (a different
  canvas engine, a stubbed export) rather than a vague "almost done".
