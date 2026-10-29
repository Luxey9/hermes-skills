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
- User minta manual book PDF bergambar langsung (screenshot + step-by-step + caption) dari aplikasi live — cakupannya sama, buildernya reportlab/`pdf_create.py`, bukan python-docx.
- User minta jumlah halaman dokumen semacam ini dikecilkan ("biar mentok 10 halaman").
- Bukan untuk: kode praktikum Python + rubrik poin (`python-coursework`), laporan magang/skripsi (`laporan-magang`).

## Aturan selalu
1. **Format teks**: Times New Roman 12 pt (isi), sub-bab 12,5–13 pt bold, judul 14 pt bold; margin kiri 3 cm, kanan/atas/bawah 2,5 cm; spasi 1,0–1,15.
2. **Langkah bernomor** dengan hanging indent (`%d.\t` + teks); tiap langkah = apa yang diklik + alasan singkat + nilai parameter yang terlihat di screenshot.
3. **Setiap gambar punya caption** `Gambar N. <deskripsi>` (italic, 9–11 pt). Caption baris gabungan: `Gambar 3–4. <deskripsi1>; <deskripsi2>`.
4. **Satu file `.docx`** di folder kerja user (bukan di home), balas dengan `MEDIA:<path>`; hasilkan PDF pendamping kalau PDF itu yang dipakai untuk verifikasi.
5. **Jangan mengarang isi dialog/parameter.** Semua nilai (ekspresi band math, nomor zona UTM, rentang mask, batas kelas) diambil dari OCR screenshot; yang tidak ada di screenshot ditulis sebagai langkah umum atau ditandai `[ISI: ...]`.
6. **Kontradiksi antar-screenshot dilaporkan, bukan didiamkan** — lihat Perangkap.
7. **Samarkan identitas asli, bukan akun contoh.** Data pribadi asli (nama/NIM/email orang lain) yang muncul di screenshot maupun teks wajib disamarkan, tetapi akun contoh/dummy khusus pengujian ditampilkan apa adanya TANPA blur, plus pernyataan di cover (`Seluruh screenshot memakai akun contoh ... , bukan data asli`). Blur parsial (sebagian diblur, sebagian masih terbaca) terlihat seperti kesalahan dan lebih buruk daripada tampil penuh atau samar penuh yang konsisten.
8. **Tetapkan skop di awal.** Sebelum memotret aplikasi live, kunci: audiens/role, bahasa, dan akun contoh yang dipakai — tanpa ini jumlah halaman dan alur melebar tak terkendali. Konfirmasi juga varian audiens yang mengubah alur (mis. kelas karyawan tanpa pre/post-test): satu varian = satu dokumen, jangan campur dua alur dalam satu naskah.
9. **Sampul/TOC berlatar gelap wajib template sendiri DAN mengecat latar di `onPage`.** Halaman sampul dan daftar isi berlatar penuh (maroon/gelap) memakai `PageTemplate` reportlab tersendiri yang diganti via `NextPageTemplate` tepat di batas `PageBreak` (cari indeks `PageBreak` secara programatik, jangan hardcode), dan seluruh teks di atasnya putih/off-white — teks gelap di atas latar gelap gagal kontras dan boros tinta saat cetak. **Style teks saja tidak mengecat halaman**: fungsi `onPage` template sampul wajib mengecat rect latar penuh (`canvas.setFillColor(...); canvas.rect(0, 0, W, H, fill=1, stroke=0)`), karena halaman reportlab default putih sehingga teks putih/emas tanpa rect jadi tak terbaca (light-on-light). Render ke PNG + `vision_analyze` untuk cek kontras sebelum menyerahkan.
10. **Capture gagal = kirim build placeholder, bukan menunggu.** Bila screenshot live gagal total (browser timeout berulang), tetap bangun PDF dengan kotak placeholder berlabel `Gbr. N. <deskripsi screenshot yang dimaksud>` yang dipetakan dari source (PRD/routes) — isi teks harus akurat dari source, bukan karangan. Simpan script builder di folder kerja user agar rebuild tinggal tempel gambar; tawarkan opsi user memotret sendiri lalu rebuild.

## Prosedur
1. **Baca patron dulu**: `read_file` pada PDF contoh (read_file mengekstrak teks PDF) → catat gaya penomoran, panjang penjelasan, penempatan gambar. Cek juga apakah ada `.docx` lama yang harus dilanjutkan.
2. **OCR semua screenshot** (perlu `pip install rapidocr_onnxruntime`; model tanpa vision tetap bisa membaca UI lewat OCR):
   `eng = RapidOCR()` → `r,_ = eng(path)` → `" | ".join(x[1] for x in r)`.
   Kerjakan per batch (~10–15 gambar) dan tulis hasil tiap batch ke JSON di workspace — jangan satu panggilan raksasa, progres harus selamat dari timeout. OCR ±1 detik/gambar; 55 gambar ≈ 40 detik.
3. **Petakan indeks screenshot → tahap** dari isi OCR (judul toolbox/dialog menyebut langkahnya: `/RasterManagement/LayerStacking`, `Band Math`, `Symbology`). Urutan tahap ikut alur kerja aplikasi, BUKAN urutan nama file (lihat Perangkap).
4. **Salin gambar ke workspace dengan nama ASCII pendek** (`img_00.jpeg`) sebelum `add_picture`; catat `Image.open(p).size` untuk hitung rasio.
5. **Tulis script builder python-docx** — jangan mengedit `.docx` manual: ukuran gambar akan diiterasi beberapa kali dan hanya script yang bisa rebuild bersih. Mulai dari `templates/tutorial_docx_builder.py`.
6. **Verifikasi sebelum menyerahkan**: render PDF + hitung halaman dengan `scripts/check_docx_pages.py`, ulangi dengan tinggi gambar berbeda sampai ≤ target halaman. Untuk manual PDF (reportlab): hitung halaman via `pypdf`, render halaman representatif (cover + halaman screenshot terpadat + halaman hasil) ke PNG via `pypdfium2`/`pdftoppm`, lalu `vision_analyze` untuk keterbacaan teks, ketajaman screenshot, cropping, dan konsistensi samaran — perbaiki dan rebuild sampai bersih. Laporkan jumlah halaman, gambar terpakai, dan kontradiksi yang ditemukan.

## Screenshot mandiri dari aplikasi web live
Gunakan saat screenshot belum ada dan harus memotret aplikasi web sendiri dengan akun contoh.
1. **Verifikasi kredensial lewat API dulu** (endpoint dibaca dari source halaman login, mis. `fetch('/api/...')`, bukan ditebak) dengan akun contoh sebelum otomasi browser — memastikan username/password valid dan backend hidup tanpa membakar timeout browser. Baca juga mekanisme sesi aplikasi dari source (query `?token=`, sessionStorage, postMessage) dan pakai mekanisme itu untuk injeksi sesi di skrip capture.
2. **Petakan alur dari source** (routes frontend + README/PRD) sebelum memotret: daftar halaman per role, urutan langkah (register → login → dashboard → sesi → course → profil → lupa-password), dan halaman publik tanpa login.
3. **Browser tool timeout = fallback ke capture lokal, bukan berhenti.** Bila `browser_exec` timeout (420 dtk) walau `curl` login API sukses, backend browser yang macet — jangan retry buta. Pakai Playwright Python lokal (`sync_playwright` + `chromium.launch(headless=True)` + `new_context(viewport=1366x900)`), ATAU bila repo sudah punya Chromium ms-playwright + skrip CDP node (`ws` + `/json/list` + `Page.captureScreenshot`), pakai itu dengan satu profil/port per sesi. Pola terbukti: login API → injeksi sesi via mekanisme aplikasi → klik kontrol (bukan `goto` per halaman untuk SPA satu-URL) + `wait_for_timeout` → `screenshot`. Verifikasi tiap capture via `inner_text` 300 karakter pertama atau `vision_analyze` sebelum dipakai.
4. **Tunggu data selesai, bukan cuma preloader hilang.** Setelah `goto`, tunggu dua syarat via `wait_for_function`: (a) teks loading hilang (`!document.body.innerText.includes('Memuat...')`, batas ~25 dtk), DAN (b) penanda data muncul (`includes('Kelompok Saya')`, `includes('belum dimasukkan')`, `includes('Sync: Baru saja')`, atau penghitung progres bukan skeleton). Tambah settle 2-3 dtk. Untuk toast sukses login yang menutupi konten (`Hore! Aksi kamu...`), tunggu ekstra ~6 dtk sampai hilang sebelum screenshot beranda. Cek teks hasil capture: splash/loading = ulangi tunggu, jangan dipakai.
5. **Blur selektif via JS `evaluate`, bukan CSS.** Bila hanya NIM orang lain yang wajib blur (akun contoh tetap terbaca), iterasi baris di browser: `li.forEach(li => { if (!li.innerText.includes('(Saya)')) li.querySelectorAll('.font-mono').forEach(el => { el.style.filter='blur(6px)'; }) })`. Selector CSS `:has-text()` tidak valid di browser dan gagal diam-diam — verifikasi via `evaluate` return count `{total_li, blurred}` lalu `vision_analyze`: NIM lain tak terbaca, NIM akun contoh terbaca.
6. **Akun contoh dari user = foto sendiri, bukan minta user memotret.** Bila user sudah memberi kredensial test, default-nya capture otomatis oleh agen; jangan menyerahkan build placeholder lalu meminta user mengirim screenshot. Placeholder hanya bila Playwright lokal juga gagal total.
7. **Daftar screenshot eksplisit + "kirim di sini" = kirim `MEDIA:` langsung.** Bila user memberi list shot bernomor dan memerintahkan kirim di chat, balas dengan tiap file sebagai `MEDIA:<abs path>` berlabel sesuai urutan list-nya di turn yang sama. Jangan menahan gambar di balik pertanyaan rakit-PDF; tawarkan rakit setelah gambar terkirim.
8. **Rapikan ke folder `final/` bernomor urut sebelum serahkan.** Salin shot terpilih ke subfolder `final/` dengan nama `<nn>_<nama>.png` mengikuti urutan list user (pecah grup multi-shot jadi `<nn>a/b/c/d_<nama>.png`), resolusi seragam (satu viewport, mis. 1366x900), lalu verifikasi tiap file via `PIL.Image.open().size`. Folder kerja mentah (`shots/`, `list/`) jangan ikut terkirim — user hanya menerima set final yang urut dan konsisten.
9. **Dialog submit difoto, lalu BATALKAN — jangan submit beneran.** Klik tombol Submit untuk memunculkan dialog konfirmasi (`Kumpulkan Jawaban?` + `Batalkan` / `Ya, Lanjutkan`), screenshot, lalu klik Batalkan dan verifikasi timer/status tetap jalan. Timer ujian akun contoh ikut berjalan saat sesi aktif — submit sungguhan mengunci pengerjaan dan merusak sesi untuk capture berikutnya.
10. **Sesi tanpa PIN tidak punya lock screen.** Bila `require_token=false`, tidak ada layar input PIN untuk difoto — catat itu di penyerahan (bukan kegagalan capture). Lock screen PIN hanya ada bila sesi dikonfigurasi ber-PIN; minta PIN ke admin/asisten bila user memintanya difoto.

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
- **Timeout browser bukan berarti situs mati.** Cek ringan (`curl -I <situs>`, lalu login API) untuk membedakan situs down vs backend browser yang macet, backend browser yang macet butuh strategi capture lain, bukan retry buta yang menghanguskan menit timeout.
- **Screenshot splash screen lolos karena tidak dibaca isinya.** Setiap habis memotret, baca kembali teks halaman (`innerText` 500-600 karakter pertama) atau `vision_analyze`: tabel/foto/daftar harus ada. Splash (logo + penanda loading + progress penuh) = ulangi, bukan dipakai.
- **SPA satu-URL: jangan `goto` per halaman.** Navigasi via state tidak ganti URL — klik kontrol lalu verifikasi `innerText` berubah; ukuran file kembar identik berarti navigasi nyangkut, diagnosa dulu via dump teks semua tombol (`[...document.querySelectorAll('a,button')]`) untuk memetakan tiap shot ke pemicu aslinya (label tombol bisa beda dari nama menu) sebelum motret ulang.
- **Throttle verifikasi visual.** Kirim `vision_analyze` maksimal 3–4 konkuren — burst lebih besar ditolak limit konkuren sehingga sebagian hasil kosong dan verifikasi pincang.
- **Varian audiens mengubah isi bab.** Tanyakan di awal apakah ada varian alur (kelas karyawan, susulan, ujian praktik): varian yang menghapus langkah wajib tercermin di daftar isi, alur cover, dan hitungan istilah (grep naskah/PDF untuk istilah yang seharusnya nol).
- **Nomor halaman TOC jangan disalin dari patron.** Halaman patron (mis. 7 > 9 > 10 > 12) mencerminkan isi patron, bukan build baru — tulis ulang dari hasil `pypdf` build sendiri, lalu rebuild; selisih 1 halaman saja merusak kepercayaan navigasi.
- **Blur CSS `:has-text()` gagal diam-diam.** Filter parsial (sebagian NIM blur, sebagian terbaca) terlihat seperti kesalahan — pakai JS `evaluate` per-baris dengan pengecualian `(Saya)`, hitung `blurred`, verifikasi visual.
- **Terapkan antislop selama penulisan naskah.** Tanpa karakter em dash di teks, tanpa klise AI, kalimat dipadatkan, judul bab berupa masalah nyata (`Kendala Umum`) bukan label template.
- **Judul menggantung di kaki halaman (orphan heading).** Sub-judul yang jatuh di baris terbawah dengan isinya di halaman berikut adalah cacat layout klasik — bungkus H2 + blok berikutnya dalam `KeepTogether` atau pindahkan manual; cek tiap render PNG halaman representatif, bukan cuma total halaman.
- Halaman berisi gambar saja (teks 0 karakter) menandakan packing terlalu rapat / page break sial; periksa distribusi gambar per halaman, bukan cuma total halaman.
- Jangan menyajikan nilai hasil perhitungan (mis. TSS 8,1429–22,0809 mg/L) sebagai fakta ilmiah tanpa catatan validasi — sebut bahwa itu keluaran algoritma dan perlu data in-situ/R².

## Support files
- `templates/tutorial_docx_builder.py` — kerangka builder python-docx: packing gambar beberapa per baris, map tinggi per screenshot, caption gabungan.
- `scripts/check_docx_pages.py` — konversi ke PDF (LibreOffice) lalu laporkan jumlah halaman, gambar per halaman, dan cek overlap/keluar margin.
