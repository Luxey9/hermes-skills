# Verifikasi dokumen .docx bergambar: jumlah halaman, gambar per halaman, geometri.
# Pakai: python check_docx_pages.py <file.docx> [target_halaman]
# Butuh: LibreOffice (soffice), pypdf, pymupdf  (pip install pypdf pymupdf)
import os, sys, shutil, subprocess

DOCX = sys.argv[1]
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else None
SOFFICE = next(p for p in (
    shutil.which("soffice.exe"), shutil.which("soffice"),
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice") if p and os.path.exists(p))
OUTDIR = os.path.dirname(os.path.abspath(DOCX))
PDF = os.path.join(OUTDIR, os.path.splitext(os.path.basename(DOCX))[0] + ".pdf")
if os.path.exists(PDF):
    os.remove(PDF)
subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", OUTDIR, DOCX],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if not os.path.exists(PDF):                      # konversi batch bisa terlewat: ulangi satu file saja
    raise SystemExit("PDF tidak terbentuk — konversi ulang untuk file ini saja")

import pymupdf as fitz
from pypdf import PdfReader

print("halaman:", len(PdfReader(PDF).pages))
doc = fitz.open(PDF)
per_page, problems = [], []
for i, page in enumerate(doc):
    rects = [fitz.Rect(b["bbox"]) for b in page.get_text("dict")["blocks"] if b.get("type") == 1]
    per_page.append(len(rects))
    W, Hp = page.rect.width, page.rect.height
    for r in rects:
        if r.x0 < 0 or r.y0 < 0 or r.x1 > W or r.y1 > Hp:
            problems.append((i + 1, "gambar keluar halaman", tuple(round(v, 1) for v in r)))
    for a in range(len(rects)):
        for b in range(a + 1, len(rects)):
            inter = rects[a].intersect(rects[b])
            if rects[a].intersects(rects[b]) and inter.get_area() > 1:
                problems.append((i + 1, "gambar tumpang tindih", round(inter.get_area(), 1)))

print("gambar per halaman:", per_page, "total", sum(per_page))
print("masalah geometri:", problems or "tidak ada")
empty = [i + 1 for i, p in enumerate(doc) if not p.get_text().strip()]
if empty:
    print("halaman tanpa teks (periksa page break/packing):", empty)
if TARGET:
    print("target %d halaman -> %s" % (TARGET, "OK" if len(PdfReader(PDF).pages) <= TARGET else "BELUM: kecilkan tinggi gambar"))
