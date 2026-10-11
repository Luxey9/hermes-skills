---
name: powerpoint
description: Create, read, edit .pptx decks with python-pptx.
version: 1.1.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pptx, powerpoint, presentations, slides, office, python-pptx]
    category: productivity
    related_skills: [docx, xlsx, pdf]
---

# Powerpoint Skill

Create, inspect, and edit PowerPoint (.pptx) presentations using the
python-pptx library. Five helper scripts cover deck creation from a JSON
spec, structured read-back, in-place edits, template-driven brand decks,
and slide rendering — all offline, no PowerPoint installation required.

## When to Use

- The user asks to build a slide deck, report presentation, or pitch deck.
- You need to extract text, notes, tables, chart data, or images from a
  .pptx someone shared.
- You need to update an existing deck: replace text, refresh or patch
  chart data, swap a logo, duplicate/remove/reorder slides, set
  backgrounds, footers, hyperlinks, or speaker notes.
- You must produce an on-brand deck from a company .pptx template.
- Do NOT use this for .ppt (legacy binary) files — convert them first with
  `soffice --convert-to pptx old.ppt` if LibreOffice is available.

## Prerequisites

- Python 3.10+ with `python-pptx` installed
  (`pip install python-pptx`).
- Optional: LibreOffice (`soffice`) plus poppler (`pdftoppm` or
  `pdftocairo`) for rendering slides to PNGs and for PDF export.
  `pptx_render.py` detects both with `shutil.which` and degrades
  gracefully (reports `{"rendered": false, "missing": [...]}`, exit 0)
  when absent — all create/read/edit operations work without them.
- Check availability via `terminal`:
  `python -c "import pptx; print(pptx.__version__)"` and `which soffice pdftoppm`.

## How to Run

All scripts live in `scripts/`, take `--help`, print JSON to stdout, and
exit non-zero on failure. Run them with `terminal`:

```bash
python scripts/pptx_create.py deck.json out.pptx
python scripts/pptx_read.py deck.pptx --outline      # full JSON outline
python scripts/pptx_read.py deck.pptx --notes        # speaker notes
python scripts/pptx_read.py deck.pptx --images ./img # export pictures
python scripts/pptx_edit.py deck.pptx --replace-text "Old Corp" "New Corp"
python scripts/pptx_edit.py deck.pptx --chart-data update.json
python scripts/pptx_edit.py deck.pptx --duplicate-slide 2
python scripts/pptx_edit.py deck.pptx --remove-slide 3 --move-slide 2 0
python scripts/pptx_from_template.py brand.pptx out.pptx --values vals.json
python scripts/pptx_render.py deck.pptx --outdir ./render  # slide PNGs
```

Author JSON specs with `write_file`; inspect script output and generated
JSON with `read_file`.

## Quick Reference

| Task | Command |
|---|---|
| New deck from spec | `pptx_create.py spec.json out.pptx` |
| 16:9 vs 4:3 | `"slide_size": "16:9"` or `"4:3"` in the spec |
| Outline as JSON | `pptx_read.py deck.pptx --outline` |
| Export images | `pptx_read.py deck.pptx --images DIR` |
| Replace text | `pptx_edit.py deck.pptx --replace-text OLD NEW` |
| Replace chart data | `pptx_edit.py deck.pptx --chart-data spec.json` |
| Patch one series | same flag, spec with `"ops"` (see below) |
| Swap picture | `pptx_edit.py deck.pptx --swap-image N NAME new.png` |
| Duplicate slide | `pptx_edit.py deck.pptx --duplicate-slide N` |
| Remove slide | `pptx_edit.py deck.pptx --remove-slide N` |
| Reorder slide | `pptx_edit.py deck.pptx --move-slide FROM TO` |
| Slide background | `pptx_edit.py deck.pptx --set-background N RRGGBB` |
| Hyperlink runs | `pptx_edit.py deck.pptx --hyperlink N TEXT URL` |
| Slide number on | `pptx_edit.py deck.pptx --enable-slide-number N` |
| Footer text | `pptx_edit.py deck.pptx --set-footer N TEXT` |
| Set notes | `pptx_edit.py deck.pptx --set-notes N TEXT` |
| Append notes | `pptx_edit.py deck.pptx --append-notes N TEXT` |
| Fill template | `pptx_from_template.py tpl.pptx out.pptx --values v.json` |
| Render slide PNGs | `pptx_render.py deck.pptx --outdir DIR` |

## Procedure

### 1. Create a deck

Write a JSON spec (see `pptx_create.py --help` for the full format), then
run `pptx_create.py`. Per slide you can set: `layout` (title,
title_content, section, two_content, title_only, blank), `title`,
`subtitle`, `bullets` (strings, or dicts with `level` 0-4, `size` pt,
`bold`, `italic`, `font`, `color` hex, `link` URL for a hyperlink),
`background` (solid hex), `footer` (text; enables the layout's footer
placeholder), `slide_number` (true; enables the layout's slide-number
placeholder), `images` (path + left/top/width/height in inches), `tables`
(`rows` as list-of-lists), `shapes` (rectangle, rounded_rectangle, oval,
diamond, right_arrow, chevron, with `fill` hex + optional `text`),
`charts` (bar, bar_h, line, pie with `categories` + `series`), and
`notes` (speaker notes).

### 2. Read a deck

`pptx_read.py deck.pptx --outline` returns slide size, layout inventory,
and per slide: layout name, all shape texts, table cells, image inventory
(filename/ext/bytes), chart categories/series/values, and speaker notes.
Use `--images DIR` to dump embedded pictures to files, then
`vision_analyze` on any exported image if you need to see its content.

### 3. Edit a deck

`pptx_edit.py` combines operations in one pass; use `--output` to keep the
original. Text replacement scans slide shapes, table cells, and notes.
Image swap retargets the picture's relationship id so position and size
are preserved. Slide removal drops the relationship and the `<p:sldId>`
entry; reorder moves the `<p:sldId>` element within `<p:sldIdLst>`
(python-pptx has no public API for either — the script does the XML-level
work). `--duplicate-slide N` appends an independent deep copy of slide N:
shape XML plus image/media/hyperlink relationships are cloned and rIds
remapped, so editing the copy never touches the original. Chart slides
are refused (see Pitfalls). `--set-notes`/`--append-notes` edit speaker
notes; `--set-background`, `--hyperlink`, `--enable-slide-number`, and
`--set-footer` handle deck polish.

Chart updates take a JSON spec via `--chart-data`. Full replace:
`{"slide": 0, "chart": 0, "categories": [...], "series": {...}}`. For
surgical edits, pass `"ops"` instead — a list of
`{"op": "update_series", "name": ..., "values": [...]}`,
`add_series`, `remove_series`, `rename_category` (`from`/`to` or
`index`), and `set_title`. python-pptx can only swap a chart's entire
dataset (`replace_data`), so ops are implemented as read-existing →
modify → replace; the per-part UX is a wrapper, and any chart data not
expressible as categories + numeric series will be normalized by the
round-trip.

### 4. Build from a template

`pptx_from_template.py` opens a brand .pptx, replaces every
`{{token}}` from a values JSON across slides/tables/notes, and can append
new slides that use the template's own layouts (by layout name or index)
so they inherit the master's fonts and colors. Tip: to start from a
template with zero slides, delete existing ones afterward with
`pptx_edit.py --remove-slide`.

### 5. Visual verification

`pptx_render.py deck.pptx --outdir ./render` converts the deck to PDF
with `soffice --headless` and splits it into one PNG per slide with
`pdftoppm` (or `pdftocairo`). Output JSON lists the PNG paths — review
each with `vision_analyze`. When either tool is missing the script exits
0 with `{"rendered": false, "missing": [...]}` and guidance; fall back to
the JSON outline from `pptx_read.py`, which verifies content and
structure, just not visuals.

## Converting to PDF

If LibreOffice is installed, export the finished deck to PDF directly:

```bash
soffice --headless --convert-to pdf --outdir ./out deck.pptx
```

The output lands at `./out/deck.pdf`. Fonts not installed on the host are
substituted, so render-verify (Procedure step 5) before shipping the PDF.
There is no offline pure-Python .pptx→PDF path; if `soffice` is absent,
say so rather than approximating.

## Pitfalls

- **Run splitting**: PowerPoint fragments paragraph text into runs at
  spell-check and edit boundaries. `--replace-text` first merges adjacent
  runs whose formatting is identical, so matches split across such runs
  are replaced with formatting fully preserved. Only when a match spans
  *genuinely differently-formatted* runs is the paragraph rewritten with
  the first run's formatting — verify those slides after replacement.
- **Chart slides cannot be duplicated**: each chart relationship embeds a
  separate XLSX workbook part; cloning that graph reliably is not
  supported, so `--duplicate-slide` refuses chart slides cleanly instead
  of corrupting the deck. Rebuild the chart on a new slide instead.
  External-hyperlink and image/media rels are carried over; layout and
  notes rels are recreated fresh.
- **Chart ops are a wrapper**: python-pptx replaces the whole dataset;
  `"ops"` round-trips existing plot data through `replace_data`, and
  changing chart *type* is not possible.
- **Reordering is XML-level**: python-pptx has no supported reorder API.
  `--move-slide` manipulates `<p:sldIdLst>` directly; safe for ordinary
  decks but re-read the deck afterward to confirm.
- **Copying slides between decks is unsupported** — duplication works
  only within one deck, where layouts and masters are shared.
- Footer/slide-number enablement copies the placeholder from the slide's
  layout; on layouts without those placeholders, `--set-footer` fails
  with a clear message (add a textbox instead).
- Hyperlinks apply to whole runs; `--hyperlink` links every run
  containing the given text on that slide.
- **A deck of only bullets and tables reads as "minim visualisasi"**: mix in cards, tinted callout strips, timelines, hub-and-spoke geometry with connectors, and native charts. Use `pptx_create.py` for the JSON route, but for anything design-driven write a standalone builder script using python-pptx directly (grid constants + `card()/strip()/chip()/chart()` helpers) — the JSON spec cannot express rounded-card grids or connector spokes. This pair of files is the artifact to keep: `build_*.py` (spec) plus an audit script.
- **Prefer the `pptx-designer` package over hand-rolled python-pptx for design-driven decks** (`pip install pptx-designer`, public API, MIT-style usage). It gives `ThemeComposer().compose(palette=..., fonts=..., decoration=..., layout=..., seed=...)` returning `semantic_roles` (background/surface/ink/muted/accent/success/warning/danger/border/data-series-N), semantic color names accepted by every helper, plus `Presentation()`, `set_widescreen`, `set_presentation_theme(prs, theme)`, `set_slide_theme(slide, theme)`, and tools in `pptx_designer.tools.{layout,cards,charts,shapes,text,svg}` (`page_header`, `kpi_card`, `highlight_cards`, `section_divider`, `native_chart`, `rect/rrect/oval/chevron/arrow/hexagon/diamond/callout`, `text`, `svg_chart`). Geometry pitfalls it does NOT solve, so wrap it: (a) `semantic_roles` has no `primary`/`on_primary` key in every palette — resolve every role through your own `role(theme, name)` helper that falls back to `theme["colors"]`; (b) `compose(fonts=...)` returns no font entry, so inject `font_heading`/`font_body` yourself (Segoe UI / Segoe UI Semibold ship on Windows); (c) `highlight_cards`/`kpi_card`/`section_divider` place text at fixed offsets and never auto-shrink, so budget ~1.4in height for 3-line card bodies and re-check with your own fitter; (d) `native_chart` style keys are limited to `show_legend/show_value/show_title/title/label_font_size/number_format/color_scheme/show_category_name/label_position` — an unsupported key (e.g. `show_percentage` on a bar) silently drops the data labels; (e) chart shapes are appended last in z-order and are opaque, so a footer textbox drawn earlier gets painted over — check z-order.
- **`pptx-designer` theme injection needs the slide theme, not a global**: `set_presentation_theme` writes the theme onto the package part; helpers read it per slide, so a `set_slide_theme` call per slide is the reliable path when you build slides in a loop.
- **Titles wrap to a second line exactly where the layout math says they won't.** A card title's line count must be estimated with the *bold* advance width; using the regular-text width under-counts by ~15% and the wrapped title then collides with the card body. Use `chars_per_line = width_in / (0.585 * pt / 72)` for bold, `0.515` for regular, and add ~0.055in per text box for the fixed internal top+bottom padding the engine emits.
- **Audit the deck before shipping, numerically** (`check_deck.py` pattern): walk `slide.shapes` and flag (a) anything outside the slide rect, (b) containers overlapping each other by >6% of the smaller, (c) text whose estimated ink height exceeds its box, (d) table row heights summing past the frame, (e) font sizes below ~9pt. Measure "ink height" as `ceil(len(text)/chars_per_line) * pt * line_spacing / 72` with `chars_per_line = width_in / (0.525 * pt / 72)` for Arial regular, `0.565` bold. Exclude footer-band chrome (y >= ~7.0 on a 7.5in slide) from the below-safe-area rule or every slide reports false positives.
- **Ignore self-overlap and text-inside-its-own-card** when overlap-checking: a text frame drawn on top of the card that contains it is not a defect. Only compare container-vs-container; skip a shape when the other contains it.
- **Verify against the actual rendering, not just the object model**: LibreOffice (`soffice --headless --convert-to pdf`) plus PyMuPDF gives a real check — iterate `page.get_text("dict")` spans and look for bbox overlaps between spans (catches clipped/wrapped text the pptx geometry cannot), and match every paragraph/table-cell string against `page.get_text()` to prove nothing was dropped in rendering. On this Windows host `soffice` is at `C:\Program Files\LibreOffice\program\soffice.exe` and `pdftoppm` is absent, so use PyMuPDF for PNG rendering instead of `pptx_render.py`.
- **Open Office locks the output file** — writing the .pptx again while the previous copy is open in PowerPoint fails with `PermissionError: [Errno 13]`. Write to a new filename or ask the user to close it; do not retry the same path.
- The default python-pptx template is 4:3; the create script sets 16:9
  unless the spec says otherwise. Custom templates keep their own size.
- **Tables do not auto-fit**: python-pptx sizes rows from the *number* of
  rows, not cell text, so a table with wrapping text overflows the slide and
  a table placed on a layout that also has a body placeholder overlaps that
  placeholder's empty text box. After creating, run a post-pass that sets an
  explicit `run.font.size` per cell (10-11pt header, 9-10pt body for 5-column
  tables), sets `cell.margin_*` to ~0.03in, sets each `row.height` to
  `ceil(maxlen/chars_per_line) * pt * 1.3 / 72`, and shrinks font sizes until
  `top + sum(row heights) <= slide_height`. Set `space_after = Pt(0)` on cell
  paragraphs too, or the PowerPoint default adds ~10pt per row.
- **Estimate bullet overflow before shipping**: chars-per-line ~=
  `width_in / (0.52 * pt / 72)`; total height per paragraph ~=
  `lines * pt * 1.22 / 72`. Shrink all runs uniformly by 1pt (floor ~11pt)
  until the body fits the region below the title. This catches the long
  text-heavy slides that the JSON outline cannot flag.
- Verify a finished deck's geometry with python-pptx directly
  (`shape.top + shape.height` for every shape vs `prs.slide_height`) —
  `pptx_read.py --outline` reports content but not whether it fits, and
  `pptx_render.py` needs LibreOffice, which is often absent on Windows hosts.
- Layout indexes vary by template. For brand templates, list layout names
  first: `pptx_read.py template.pptx --outline` (`layouts_available`).
- `slide.shapes.title` is None on blank layouts — the create script
  handles this, but remember it when writing ad-hoc python-pptx code.
- Always pass `encoding="utf-8"` when writing spec files; tokens like
  `{{city}}` may be filled with non-ASCII values.

## Verification

1. After any create/edit, run `pptx_read.py OUT.pptx --outline` and check
   slide count, texts, tables, notes, and chart values match intent.
2. `--images DIR` then file-size check confirms pictures embedded.
3. Render every slide with `pptx_render.py deck.pptx --outdir ./render`
   and review each PNG with `vision_analyze` — this catches overlapping
   shapes, truncated text, and color problems the outline cannot. If the
   render tools are missing, the script says so; rely on the outline.
4. The bundled test suite is the full contract:
   `python -m pytest tests/ -q` (requires python-pptx + pytest).
