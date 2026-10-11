---
name: tutorial-praktikum-docx
description: Illustrated step-by-step .docx tutorial from screenshots.
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [docx, tutorial, praktikum, screenshots, ocr, python-docx]
    category: productivity
    related_skills: [docx, python-coursework, pdf]
---

# Tutorial Praktikum Bergambar (.docx)

Dokumen tutorial/praktikum bergaya "langkah bernomor + screenshot + caption" — mis. Tugas SPSL
(ENVI/ArcGIS), laporan praktikum, how-to perangkat lunak. Sumbernya sekumpulan screenshot yang
dikirim user, sering dengan patron berupa PDF tugas senior. Balas dan tulis isi dalam Bahasa Indonesia.

## When to Use (Kapan dipakai)
Use when the user hands over a folder of screenshots and wants a numbered, illustrated .docx
how-to (praktikum report, software tutorial), or wants an existing illustrated PDF re-made as .docx.
- User memberi folder screenshot lalu minta disusun jadi tutorial langkah-demi-langkah.
- User minta dokumen contoh (PDF tugas lama) ditiru gayanya tapi dibuat ulang sebagai `.docx`.
- User minta jumlah halaman dokumen semacam ini dikecilkan ("biar mentok 10 halaman").
- Bukan untuk: kode praktikum Python + rubrik poin (`python-coursework`), laporan magang/skripsi (`laporan-magang`).

## Aturan selalu
1. **Format teks**: Times New Roman 12 pt (isi), sub-bab 12,5–13 pt bold, judul 14 pt bold; margin kiri 3 cm, kanan/atas/bawah 2,5 cm; spasi 1,0–1,15.
2. **Langkah bernomor** dengan hanging indent (`%d.\t` + teks); tiap langkah = apa yang diklik + alasan singkat + nilai parameter yang terlihat di screenshot.
3. **Setiap gambar punya caption** `Gambar N. <deskripsi>` (italic, 9–11 pt). Caption baris gabungan: `Gambar 3–4. <deskripsi1>; <deskripsi2>`.
4. **Satu file `.docx`** di folder kerja user (bukan di home), balas dengan `MEDIA:<path>`; hasilkan PDF pendamping kalau PDF itu yang dipakai untuk verifikasi.
5. **Jangan mengarang isi dialog/parameter.** Semua nilai (ekspresi band math, nomor zona UTM, rentang mask, batas kelas) diambil dari OCR screenshot; yang tidak ada di screenshot ditulis sebagai langkah umum atau ditandai `[ISI: ...]`.
6. **Kontradiksi antar-screenshot dilaporkan, bukan didiamkan** — lihat Perangkap.

## Prosedur
1. **Baca patron dulu**: `read_file` pada PDF contoh (read_file mengekstrak teks PDF) → catat gaya penomoran, panjang penjelasan, penempatan gambar. Cek juga apakah ada `.docx` lama yang harus dilanjutkan.
2. **OCR semua screenshot** (perlu `pip install rapidocr_onnxruntime`; model tanpa vision tetap bisa membaca UI lewat OCR):
   `eng = RapidOCR()` → `r,_ = eng(path)` → `" | ".join(x[1] for x in r)`.
   Kerjakan per batch (~10–15 gambar) dan tulis hasil tiap batch ke JSON di workspace — jangan satu panggilan raksasa, progres harus selamat dari timeout. OCR ±1 detik/gambar; 55 gambar ≈ 40 detik.
3. **Petakan indeks screenshot → tahap** dari isi OCR (judul toolbox/dialog menyebut langkahnya: `/RasterManagement/LayerStacking`, `Band Math`, `Symbology`). Urutan tahap ikut alur kerja aplikasi, BUKAN urutan nama file (lihat Perangkap).
4. **Salin gambar ke workspace dengan nama ASCII pendek** (`img_00.jpeg`) sebelum `add_picture`; catat `Image.open(p).size` untuk hitung rasio.
5. **Tulis script builder python-docx** — jangan mengedit `.docx` manual: ukuran gambar akan diiterasi beberapa kali dan hanya script yang bisa rebuild bersih. Mulai dari `templates/tutorial_docx_builder.py`.
6. **Verifikasi sebelum menyerahkan**: render PDF + hitung halaman dengan `scripts/check_docx_pages.py`, ulangi dengan tinggi gambar berbeda sampai ≤ target halaman. Laporkan jumlah halaman, gambar terpakai, dan kontradiksi yang ditemukan.

## Kontrol jumlah halaman (inti)
- **Tinggi gambar adalah tuas utama**, bukan lebarnya. Lebar penuh 13,5 cm untuk screenshot potret menghasilkan gambar setinggi sampai 22 cm → ±1 gambar per halaman. Ukur dulu: `sum(min(H*iw/ih, 5,5 cm))` semua gambar dibagi tinggi teks per halaman (±25,7 cm). Contoh nyata: 55 screenshot pada lebar 13,5 cm = 48 halaman; pada tinggi tetap 3,4 cm + packing 2–3 per baris = 10 halaman.
- **python-docx tidak punya kolom/tabel gambar**: taruh beberapa run `add_picture` di SATU paragraf → gambar mengalir ke samping otomatis. Flush (mulai paragraf baru) saat akumulasi lebar > lebar teks (≈15,4 cm).
- Selalu `add_picture(..., height=Cm(H))` lalu lebar mengikuti rasio; jangan menyetel lebar saja.
- **Pengecualian ukuran untuk dialog kunci**: simpan map `{indeks: tinggi_cm}` dan beri 6,0–6,5 cm pada screenshot yang isinya harus terbaca (dialog parameter/ekspresi band math, Symbology/Classification, histogram). Contoh: tinggi 3,4 cm + 7 pengecualian = 10 halaman; tanpa pengecualian harus 3,2 cm. Tawarkan trade-off ini ke user saat dia minta batas halaman.
- Rapatkan tipografi: `Normal.space_after = 4 pt`, `line_spacing 1.1`, caption 9 pt dengan `space_after 8 pt`, paragraf gambar `space_before 3 / after 1`, `line_spacing 1.0`.
- Set `w:eastAsia` rFonts ke Times New Roman di style `Normal`, bukan hanya `font.name`.

## Perangkap
- **Nama file screenshot tidak mencerminkan urutan langkah.** Batch WhatsApp memakai suffix `(...)` yang ambigu (`15.03.12 (1)` vs `15.03.12`); urutan benar ditentukan dari ISI OCR, lalu diverifikasi dengan membaca ulang teks yang muncul.
- **Cek silang nilai parameter antar screenshot.** Contoh: satu dialog menunjukkan UTM *Zone 50 North* sedangkan metadata citra menunjukkan *Zone 50 South* (Gili Iyang ≈6,9° LS) — tulis yang benar di tutorial DAN beri tahu user perbedaannya, jangan memilih diam-diam.
- **Jangan percaya "selesai" dari ukuran file atau jumlah shape.** Verifikasi geometri programatik: jumlah gambar per halaman, tidak ada bbox keluar area teks / tumpang tindih (`scripts/check_docx_pages.py`).
- **python-docx tidak bisa memprediksi page break** — satu-satunya jalan iterasi render → hitung halaman → ubah tinggi. Jangan menjanjikan angka halaman sebelum diukur.
- **Konversi LibreOffice headless bisa terlewat saat beberapa file dikonversi sekaligus** — periksa keberadaan PDF hasil sebelum dibaca; kalau hilang, konversi ulang file itu satu per satu.
- Halaman berisi gambar saja (teks 0 karakter) menandakan packing terlalu rapat / page break sial; periksa distribusi gambar per halaman, bukan cuma total halaman.
- Jangan menyajikan nilai hasil perhitungan (mis. TSS 8,1429–22,0809 mg/L) sebagai fakta ilmiah tanpa catatan validasi — sebut bahwa itu keluaran algoritma dan perlu data in-situ/R².

## Support files
- `templates/tutorial_docx_builder.py` — kerangka builder python-docx: packing gambar beberapa per baris, map tinggi per screenshot, caption gabungan.
- `scripts/check_docx_pages.py` — konversi ke PDF (LibreOffice) lalu laporkan jumlah halaman, gambar per halaman, dan cek overlap/keluar margin.
