# Kerangka builder .docx tutorial bergambar (TNR 12, gambar di-packing beberapa per baris).
# Pakai: python build.py <TINGGI_CM> <OUT.docx>   env BIGSET="3:6.5,9:6,35:6" (indeks:tinggi)
# Verifikasi halaman pakai scripts/check_docx_pages.py, bukan perkiraan.
import os, glob, sys
from PIL import Image
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

SRC = r"<folder screenshot user>"
WORK = os.path.join(os.environ.get("BH_AGENT_WORKSPACE", "."), "tut_img")
ROW_W = 15.4  # cm lebar teks (A4 - margin 3/2,5 cm)

files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SRC, "*.jpeg")))
os.makedirs(WORK, exist_ok=True)
SHORT, SIZES = {}, {}
for i, f in enumerate(files):                       # nama ASCII pendek: hindari spasi/karakter aneh
    dst = os.path.join(WORK, "img_%02d.jpeg" % i)
    if not os.path.exists(dst):
        Image.open(os.path.join(SRC, f)).convert("RGB").save(dst, "JPEG", quality=88)
    SHORT[i], SIZES[i] = dst, Image.open(dst).size

H = float(sys.argv[1]); OUT = sys.argv[2]
BIG = {int(k): float(v) for k, v in (kv.split(":") for kv in os.environ.get("BIGSET", "").split(",") if kv)}
NOTES = {i: "deskripsi singkat screenshot %d" % i for i in range(len(files))}  # ganti dari JSON OCR


def build():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")  # wajib, selain font.name
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.line_spacing = 1.1
    for s in doc.sections:
        s.left_margin, s.right_margin = Cm(3), Cm(2.5)
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)

    pending = []

    def width_of(i):
        hh = BIG.get(i, H)
        iw, ih = SIZES[i]
        return min(hh * iw / ih, ROW_W if i not in BIG else 19.0)

    def flush():
        """python-docx tidak punya kolom gambar: beberapa run add_picture dalam SATU
        paragraf mengalir ke samping secara otomatis; flush saat baris penuh."""
        if not pending:
            return
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(3), Pt(1)
        p.paragraph_format.line_spacing = 1.0
        for k, i in enumerate(pending):
            if k:
                p.add_run("  ").font.size = Pt(6)
            p.add_run().add_picture(SHORT[i], height=Cm(BIG.get(i, H)))
        ids = pending[:]
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(8)
        cap.paragraph_format.line_spacing = 1.0
        label = ("Gambar %d" % (ids[0] + 1) if len(ids) == 1
                 else "Gambar %d\u2013%d" % (ids[0] + 1, ids[-1] + 1))
        r = cap.add_run("(%s). %s" % (label, "; ".join(NOTES[i] for i in ids)))
        r.italic = True
        r.font.size = Pt(9)
        r.font.name = "Times New Roman"
        pending.clear()

    def img(i):
        if pending and sum(width_of(x) for x in pending) + width_of(i) + 0.3 > ROW_W:
            flush()
        pending.append(i)

    def H1(t, size=13):
        flush(); p = doc.add_paragraph(); r = p.add_run(t)
        r.bold, r.font.size = True, Pt(size)
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(9), Pt(5)

    def P(t):
        flush(); doc.add_paragraph(t)

    def STEP(n, t):
        flush(); p = doc.add_paragraph()
        p.add_run("%d.\t" % n).bold = True
        p.add_run(t)
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.75)
        p.paragraph_format.space_after = Pt(3)

    def CENTER(t, bold=False):
        flush(); p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(t).bold = bold

    # ---- isi dokumen ----
    # Judul (14 pt bold, center), A. Data/perangkat/algoritma, B. Tahapan
    # (H1 per tahap + STEP + img dalam urutan isi, bukan urutan nama file), C. Penutup.
    # ...
    flush()
    doc.save(OUT)
    return len(doc.inline_shapes)


print("built H=%.1f imgs=%d -> %s" % (H, build(), OUT))
