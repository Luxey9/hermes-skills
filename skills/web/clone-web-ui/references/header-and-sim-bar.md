# Cloning a builder-style header, sim bar, and status bar

Layout skeleton that matches Solar Builder-class apps (dark builder UIs):

```
.header                  brand (☀️ Name) | .header-actions (6 icon buttons)
                         | .sim-bar | .header-right (danger actions)
.main                    .palette | .canvas-wrap | .side (inspector)
.status-bar              hint (left) | counts (right)
```

Styling tokens worth copying verbatim: panel `#16213e`, border `#0f3460`,
item `#0f3460`, hover `#1a4a90`, active `#1a5a20`/`#2a8a30`/text `#88ff88`,
accent `#f0c040`, monospace clock with `font-variant-numeric: tabular-nums`.
Set `font: inherit` on every `<button>`/`<select>` inside a themed bar — browsers
default to system UI fonts and it looks instantly foreign.

## Sim bar control set (clone the order, not a subset)

`▶ Simulate` (toggles to `⏸`, gets `.active` while running) · speed `<select>`
(6 steps) · hour `<input type=range>` · `HH:MM` clock · sun glyph · `%irr` ·
`⏩ Forecast` · `↻ Reset Sim`.

## Driving a range input from puppeteer

Setting `.value` alone does nothing in React. Use the native setter, then
fire an input event:

```js
await page.evaluate(() => {
  const el = document.querySelector('.sim-time-slider');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(el, '18.5');
  el.dispatchEvent(new Event('input', { bubbles: true }));
});
```

`page.select(selector, value)` works for `<select>` and is the cleanest way to
switch simulation speed before ticking.

## Bookmark-worthy assertions

```js
// header inventory
[...document.querySelectorAll('.header-actions .tool-btn')].map(b => b.textContent.trim())
// motion proof
const t0 = await readClock(); await wait(3000); const t1 = await readClock();
if (t0 === t1) throw new Error('clock not advancing');
```

## Settings panel that drives the sim

Add a `settings` slice to the store (`digitalTwin`, `lat`, `lon`, `tilt`,
`lossPercent`, `days`, `stepMinutes`, `initialSoc`, `grid`) exported as
`DEFAULT_SETTINGS` so tests can assert it. Render it as three groups —
`Digital Twin` / `Location` / `Simulation` — at the bottom of the inspector, in
**every** inspector state, same as the summary block.

- Location presets are a `LOCATIONS: {label, lat, lon}[]` table; that is all a
  real forecast needs.
- Clamp free-text numeric input into the `<select>` you actually support
  (`stepMinutes` is 15 or 60; anything else must fall back, not widen the type).
- A forecast panel needs a loading state AND an error box in the panel itself —
  a silent failure looks like "the feature doesn't exist".

## Sub-nav pattern

When the cloned app has extra app tabs (Editor/Wizard/Report) the site does not
have, keep them in a compact `.toolbar` sub-nav UNDER the cloned header rather
than merging them into it — the header stays pixel-faithful and the extra
features stay reachable.
