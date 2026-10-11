# OOXML Motion Patch Recipe (python-pptx + ppt-master core writers)

Sometimes-needed depth for step 5 of the SKILL.md procedure: build visuals
first, then patch transitions + object animation into the package XML.

## Writers

- `create_transition_xml(effect, duration, effect_options)` — one slide
  transition. Morph needs `{"morph_by": "object"}` on the destination.
- `create_sequence_timing_xml(targets, duration, trigger)` — one `<p:timing>`
  tree. Each target is a mapping: `shape_id`, `delay_ms`, `effect`
  (canonical `entrance_*` / `emphasis_*` / `path_*` / `exit_*`), optional
  `duration`, `effect_options` (e.g. fly `direction`, grow-shrink `size`,
  path `relative: true`), optional per-row `trigger`, optional
  `repeat_count` for ambient loops.

## Patch order per slide part

1. Parse the slide part XML from the zip.
2. Set Morph names first: find `p:cNvPr` whose `id` equals the endpoint
   shape id and set `name` to `!!<key>` on BOTH slides of the pair.
3. Replace the transition carrier: remove existing `p:transition` and any
   `mc:AlternateContent` wrapper, then insert the new fragment BEFORE any
   existing `p:timing` element.
4. Replace timing: remove existing `p:timing`, append the new tree last.
5. Serialize back into the zip under the same part name.

Sort parts with a numeric key on the slide number (`slide(\d+)\.xml`),
not string sort.

## Fragment parsing

Writer output uses `p:`/`p14:`/`p15:`/`p159:` prefixes. `ElementTree`
refuses them without declarations, so wrap before parsing:

```python
NS = ('xmlns:p=".../presentationml/2006/main" '
      'xmlns:a=".../drawingml/2006/main" '
      'xmlns:r=".../officeDocument/2006/relationships" '
      'xmlns:p14=".../powerpoint/2010/main" '
      'xmlns:p15=".../powerpoint/2012/main" '
      'xmlns:p159=".../powerpoint/2015/09/main" '
      'xmlns:mc=".../markup-compatibility/2006"')

def frag(xml: str):
    return ET.fromstring(f"<frag {NS}>{xml.strip()}</frag>")[0]
```

## Validation (all must pass before delivery)

- Read-back each slide's transition from raw part bytes and confirm the
  canonical effect, options, and duration.
- Run the package transition validator, the package animation validator
  (it catches `spTgt` ids with no matching shape — the usual symptom of a
  mis-sorted slide map), and the morph-pair validator with one expectation
  per forced pair (source slide number, destination slide number, key
  without the `!!` prefix).
- Motion only shows in Slide Show; edit-mode screenshots prove layout,
  never animation.
