---
name: python-coursework
description: Use for Python praktikum code and poin-rubric docs.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [python, coursework, statistika, matplotlib, praktikum]
    related_skills: [test-driven-development, spike]
---

# Python Coursework (praktikum / studi kasus)

This user's Python assignments (ITPLN data-processing courses): study-case code using the
`statistics` module + `matplotlib`, and instruction documents with point-based rubrics.
Respond in Bahasa Indonesia — variables, print labels, and prose all in Indonesian.

## When to Use
- User asks for Python studi kasus / praktikum code (data processing, statistics, matplotlib plotting).
- User asks for a poin-rubric instruction document for a study case.
- User requests a document describing step-by-step Python tasks with `(N poin)` scoring.

## Code rules (hard preferences — user explicitly corrected these)
- ONLY basic logic: direct indexing `list[0]`, `min`/`max`/`sum`/`list.index(...)`,
  simple `if`/`elif`/`else`, single-level `for x in list:` loops. NEVER list
  comprehensions, generator expressions like `max(... for i in ...)`, `lambda`, or
  `zip`/`map` tricks.
- ONLY functions covered in course material. Assumed covered: `statistics` (`mean`,
  `median`, `stdev`, `quantiles`, `correlation`), `min`/`max`/`sum`, and matplotlib
  basics: `plot`, `bar`, `pie`, `scatter`, `hist`, `title`, `xlabel`, `ylabel`,
  `grid`, `show`, `axis('equal')`. FORBIDDEN unless the material teaches them:
  `axhline`, `axvline`, `gca`, `legend`, `invert_xaxis`, `subplots`.
- Keep each case under ~50 lines.
- Replace fancy single-liners with basic multi-line forms:
  - pie explode: make `efek_pisah = [0,0,0,0,0]` then set `efek_pisah[idx_terbesar] = 0.1`
  - largest element: `idx = data.index(max(data))`
  - max deviation: compare `max(x)-avg` vs `avg-min(x)` with if/else

## Instruction / rubric documents
- Format (user's gudang example): numbered items, sub-steps as `-` bullets, code
  fenced, points as `(N poin)` per item.
- Total points per study case must EXACTLY equal the requested total (e.g. 35). Every case in a multi-case document must have the exact same point ceiling (do not leave some at 35 and others at 32, 36, or 39).
- Reset instruction numbering: numbering MUST restart from 1 for every topic / title in a multi-case document, never continue consecutively across topics.
- File naming: keep filenames concise and descriptive (e.g., `Evaluasi_Tegangan_Ujung.py`), avoid overly long descriptive slugs or unnecessary prefixes like `SK1_...`.
- Word (.docx) document formatting rules:
  - Base font: Times New Roman 12 pt for all body text, headings, and numbered instructions.
  - Code blocks / Kunci Jawaban: Courier New or Consolas (9-10 pt).
  - Structure per case: (1) Judul Program Keterampilan, (2) Tujuan (1 kalimat ringkas), (3) Contoh Tampilan Output (screenshot / plot image rendered at centered width ~5.8 inches), (4) Total Nilai: 35 poin, (5) Numbered instructions with `(N poin)`, (6) Kunci Jawaban.
- Double-count pitfall: never put `(N poin)` on a header item AND its bullets — pick
  one place per step, else the sum overshoots the cap (validator caught 41/38 this way).
- Never use special symbols that may not render in editors (φ → write "Cos phi",
  ± → write "+-").
- Validate with the script, not by eye: see scripts/validate_rubric.py.
- Praktikum documents that are step-by-step tutorials with screenshots (ENVI/ArcGIS/Word how-tos,
  "langkah bernomor + gambar") are NOT this skill — use `tutorial-praktikum-docx` (OCR screenshots,
  python-docx builder, page-count budget). The TNR 12 baseline is the same.

## Universal Prompt Template for Instruction Documents
When asked to summarize or provide a prompt to generate rubrics/instructions matching this format:
- Structure prompt with: Title, Objective, Numbered Instructions + Sub-bullets with points summing exactly to target (e.g. 35), Output Example placeholder, and Answer Key.
- Specify: Font Times New Roman 12 pt, numbering restarts from 1 per topic, no double-counting between headers and bullets.

## Producing long files reliably (pitfall)
Large single-shot `write_file` calls for long documents repeatedly came back corrupted:
typos, truncation, and Cyrillic look-alike letters (а/р/к for a/p/k) inside otherwise
clean text — corruption appears at the output level, so output is trustworthy only
after verification. Fix: build the file in `execute_code` — write section 1 with
`open(path,'w')`, append each later section with `open(path,'a')` — and run the
validation script (point totals, keywords present, character scan above U+2500)
before telling the user it's done.