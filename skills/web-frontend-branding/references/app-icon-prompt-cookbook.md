# App Icon Prompt Cookbook

Reusable prompt material for authoring app/brand icon concepts for an image generator. Pair with the SKILL.md procedure: derive the palette from the actual product first, then name concepts, then write self-contained English prompts.

## Concept archetypes (pick 3-4, one per row)

| Archetype | Visual | When it wins | Risk |
|---|---|---|---|
| Literal object | The product's own silhouette (capsule, window, card, pill, dial) | Product is visually unique already; best 16px legibility | Can look like a generic UI glyph |
| Name / mythology | Symbol from the word's meaning (night, dawn, forge, glass) | Brand needs warmth or story | Abstract; dies at small sizes if too detailed |
| Outline / minimal | Thick gradient stroke of the literal shape, empty inside | Modern dev-tool aesthetic | Thin strokes vanish at 16px — keep stroke >= 1/20 of the canvas |
| Material study | Glass, liquid, chrome, neon bloom, emissive | Matches a glossy OS (Windows 11 / iOS) | Photoreal noise; generators add reflections that muddy the silhouette |

Rule: exactly ONE symbol per icon. Two objects is an illustration, not an icon.

## Prompt skeleton

```text
app icon, rounded squircle full-bleed, <background gradient + hex stops>,
<single symbol>, <symbol fill/stroke = accent gradient + hex stops>,
<glow / bloom / rim light>, <background accents: stars, bokeh, noise>,
<material words: flat vector, glassmorphism, minimal>, centered composition,
1:1 square, 1024x1024
```

Always in English, inside a fenced block, so it can be pasted verbatim.

## Master suffix

Midjourney / flag-aware models:

```text
--no text, letters, typography, watermark, mockup, phone frame, clutter
--style raw --stylize 150 --ar 1:1
```

DALL·E / Flux / Sora / natural-language models (no `--` flags):

```text
No text, no letters, no watermark. Perfectly centered single symbol,
flat vector, strong silhouette readable at 16 pixels.
```

## Palette discipline

- Pull accent colors from the product's own theme tokens, not from taste. Grep the source for `#RRGGBB`, rank by frequency, take the top 2-3 accents.
- Give every stop an explicit hex in the prompt; words like "blue" or "purple" drift across models.
- Keep a near-black background family (deep navy to near-black) unless the product is deliberately light.
- Check contrast in grayscale: the symbol must separate from the background with color removed.

## Failure modes and the fix

| Failure seen in output | Cause | Fix in prompt |
|---|---|---|
| Letters / misspelled app name baked in | Generators love typography | Carry the negative prompt every time |
| Icon inside a phone or desktop mockup | "app icon" alone invites presentation mockups | Add `full-bleed, no mockup, no device frame` |
| Beveled, plasticky 3D | "3D icon" or "skeuomorphic" words | Force `flat vector geometry, no 3D bevel` |
| Mushy detail, unreadable at 32px | Too many elements | Drop to one symbol, thicken strokes, delete background props |
| Square corners | Model ignores squircle wording | State `rounded squircle, corner radius about 22% of the side` |
| Washed-out glow | Bloom applied over the whole canvas | Confine the glow to the symbol (`neon bloom around the symbol only`) |

## Handoff checklist before telling the user it's done

- 3-4 named concepts, each with a one-line fit rationale and a paste-ready prompt block.
- One master suffix block, plus the flag-free variant.
- Short decision table (squircle, one symbol, zero text, 32px test, grayscale test).
- State what the next step would be (pick one, regenerate without glow, downscale to 256/128/64/48/32/16, pack `.ico`) — and wait to be asked before doing it.
