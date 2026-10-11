---
name: image-compositing
description: Pixel-exact image overlay stamping.
---

# Image Compositing

## Procedure

### Pixel-exact overlay (default when exact style match required)

1. Identify reference image containing desired overlay and target image.
2. Determine bounding box of overlay region in reference `(x1, y1, x2, y2)`.
3. `crop = reference.crop((x1, y1, x2, y2))`
4. `target.paste(crop, (x1, y1), crop)` — use crop as mask to preserve transparency.
5. Convert to RGB and save.

### Manual text/overlay recreation (only when no reference exists)

1. Load target as RGBA.
2. Create separate overlay layer: `overlay = Image.new('RGBA', size, (0,0,0,0))`.
3. Draw backgrounds, shapes, lines on overlay using `ImageDraw`.
4. Render text with `ImageFont.truetype`, measure via `textbbox`.
5. Composite: `result = Image.alpha_composite(target, overlay)`.

## Pitfalls

- **Never redraw when exact match is required.** If a reference image exists with the desired styling (font, shadow, position, transparency), extract the pixel region and paste it. Redrawing with PIL fonts produces visibly different rendering (hinting, anti-aliasing, shadow falloff) and requires iterative position guessing. "Samain persis" means pixel-copy, not approximate.
- **Use separate overlay layer for transparency.** Drawing directly on the image RGBA layer without alpha compositing produces incorrect blending. Always create an RGBA overlay layer, draw on it, then `alpha_composite`.
- **Crop region must include all styling elements.** When extracting an overlay region, include any drop shadows, background gradients, accent lines, and padding — not just the text bounding box.

## User Preferences

- User communication: Indonesian, terse, action-first. No filler.
- When user says "samain persis" or "kek modal nimpa doang", use pixel-exact reference extraction. Do not attempt manual recreation.