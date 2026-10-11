---
name: presentation-design
description: Use when building slide decks for this user.
---

# Presentation Design

Class-level workflow for building slide decks for this user. Follow it for
any new deck, rebuild, or heavy restyle. For low-level file mechanics use
the `ppt-master` vendored toolkit; this skill owns the user-facing workflow
and standing visual preferences.

## 1. Design gate (always first)

Never jump straight to building. Ask via one batched question set first:

- Visual style (offer the Lab AP maroon DNA vs. any template/reference
  the user named; if they link a catalog page, ask for a screenshot or the
  exact template — catalog URLs alone do not identify a design).
- Image source per slide (user-supplied files vs. openly-licensed search
  vs. no photos).
- Slide count and structure (roster of slide jobs, one line each).
- Motion intent (calm auto-cascade vs. carousel vs. morph story vs. static).

Confirm the roster + image plan before generating anything.

## 2. Build procedure

1. Confirm roster: one job per slide (cover, explainer, comparison,
   closing). Drop a slide rather than force content into a wrong layout.
2. Source images through the openly-licensed search script with a batch
   manifest shaped `{"items": [{"filename", "query", "status":
   "Pending", ...}]}`. Metadata ranking alone is not approval.
3. Vision-verify EVERY sourced image before placing it. Reject
   wrong-subject hits (similar-but-wrong plant type, interior shot used
   as exterior, archival photo, misleading subject) and re-search with a
   narrower query. Downscale giant panoramas to a thumbnail copy for the
   vision check; keep the full file for the deck.
4. Author visuals with python-pptx directly (grid constants + small
   helpers). Collect each animated target's `shape_id` at build time and
   reuse that map in the motion pass — never guess ids later.
5. Apply motion as a separate patch pass via the shared transition /
   animation writers (recipe in `references/ooxml-motion.md`). Keep motion
   calm by default: fades and short fly-ins, one morph story at most,
   carousel via staggered entrance delays, loops only for ambient layers.
6. Validate with the package validators (transitions, animations, morph
   pairs) and fix failures at the owning layer — never ship an
   unvalidated deck.
7. Render-verify: convert to PDF headlessly and rasterize pages (or use
   the render helper when its dependencies exist), then look at the
   key slides. Check text fit, image aspect, and alignment — the object
   model alone cannot prove fit.

## 3. Standing visual DNA (Lab AP default)

- White background, one restrained accent (maroon default), dark body
  text, muted secondary text. One accent color per deck, used consistently.
- Header: solid accent bar (left) + light panel with lab/org mark (right).
  Footer on every slide: short accent rule + `n / NN` + topic tag.
- Category badges as accent pills with ROOMY boxes — long labels must
  never sit in a tight pill; size the box from the text, not the old
  placeholder length.
- One representative image per content slide (photo or diagram that
  carries the slide's claim), framed with an offset accent shape behind
  it. Never ship a text-and-shapes-only deck when the user asked for
  illustrated slides.
- Titles big-bold-short; body small. Generous text boxes with wrapping on;
  fix overflow by shortening copy or splitting across slides, not by
  shrinking type deck-wide.

## 4. Pitfalls

- Sort slide parts numerically (`slide2` before `slide10`) before mapping
  per-slide ids — lexicographic sort silently attaches one slide's motion
  to another once the deck passes nine slides.
- Put the Morph transition on the DESTINATION slide with pairing names
  (`!!key`) on both endpoint shapes — a morph declared on the source
  slide fails pair validation.
- Parse generated transition/timing fragments with namespace declarations
  in scope (wrap in a dummy parent) — bare parsing dies on unbound
  prefixes even when the XML itself is valid.
- Expect the morph-pair expectation type to use explicit
  source/destination slide-number fields — inspect the constructor before
  calling it.
- When the finished file is open in PowerPoint, writes to the same path
  fail with a lock error — write the new revision to a fresh filename
  instead of retrying.
- Keep motion triggers consistent within one timing tree; a shape-triggered
  row must use the click trigger family, and loops (`repeat_count`) belong
  only on ambient motion, never on content entrances.
