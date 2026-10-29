# .docx report pattern that satisfied a KIP Kuliah webinar report

Built with `python-docx` when the user only had a screenshot of the required template.

## Template requirements (from the poster)

- Two activity photos: "Bagian Foto A" and "Bagian Foto B"
- "Quotes of the day" box
- Insight from speaker 1
- Insight from speaker 2
- "WHAT'S NEXT?" column
- Name + NIM at the bottom of **every** page
- Digital signature (digisign) bottom-right of each sheet
- Upload link + same-day 23:59 WIB deadline

## Structure that worked

| Page | Content |
|---|---|
| 1 | Title, activity info table, FOTO A placeholder, FOTO B placeholder |
| 2 | Quotes of the Day — one bordered tinted block per quote |
| 3 | Insight Narasumber 1 — numbered subheading + justified paragraph each |
| 4 | Insight Narasumber 2 — same shape |
| 5 | WHAT'S NEXT? numbered list, Penutup, signature block |

## Key implementation details

**Identity on every page** — section footer, not body:

```python
footer = doc.sections[0].footer
footer.is_linked_to_previous = False
p = footer.paragraphs[0]
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run(f"Nama : {NAMA}          NIM : {NIM}")
```

**Photo placeholders** — a 1x1 table with grey fill and centred italic hint text beats
an empty box: the user sees exactly what to replace.

```python
box = doc.add_table(rows=1, cols=1)
box.style = "Table Grid"
set_cell_bg(box.cell(0, 0), "F7F9FC")
```

**Quote blocks** — 1x1 table, `w:shd` fill `EAF1FB`, quote bold italic in accent colour,
attribution small grey below. Reads as a pull-quote without Word styles.

**A4 + 2.54 cm margins + Arial 11** matches Indonesian campus conventions. Set
`w:eastAsia` rFonts too, or East Asian glyphs fall back to another face.

**Leave real space for the signature** — four empty paragraphs before the name, so a
digisign stamp drops in without pushing the name to a new page.

## Content rules

- Insights must be **verbatim-derived** from the transcript, not generic business advice.
- Each insight: bold claim as subheading, then one grounded paragraph with the specific
  numbers, names, and actions the speaker actually took.
- WHAT'S NEXT must trace back to something a speaker said, not be a wishlist.
- Never invent attendance numbers or quotes. If a chunk is missing, say so.
