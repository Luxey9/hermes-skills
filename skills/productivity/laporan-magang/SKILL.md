---
name: laporan-magang
description: Draft Indonesian internship reports or thesis chapters.
---

# Laporan Magang / Skripsi — Drafting (Bahasa Indonesia)

Membantu mahasiswa Indonesia menyusun laporan magang/skripsi: cari jurnal, susun bab, kelola referensi, jaga privasi data perusahaan.

## Aturan selalu
1. **Bahasa**: jawab dan tulis semua draft dalam Bahasa Indonesia.
2. **Format Narasi vs Poin (Gaya Akademis)**: Bagian sejarah, latar belakang, dan pengantar ditulis dalam bentuk **paragraf naratif mengalir** (kronologis, tanpa poin-poin kaku). Bagian visi, misi, tata nilai (AKHLAK), pilar strategis, pembagian posko/batas wilayah, serta struktur organisasi dan rincian tugas pokok disajikan secara **proporsional: kalimat pengantar/narasi + poin-poin/bullet yang tegas**, jangan dipaksakan full-paragraf tanpa poin (sulit dibaca penguji sidang) dan jangan pula full-bullet tanpa kalimat penghubung.
3. **Rujukan ≤5 tahun**: jurnal/artikel harus dari 5 tahun terakhir; REGULASI (UU, Permen, Perdir) dikecualikan karena dasar hukum. Kalau ada jurnal tua dalam set, ganti dengan padanan terbaru — jangan dibiarkan. Pedoman ITPLN 2025 (berlaku untuk magang mulai/dilaporkan ≥15 Des 2025) menghendaki publikasi 1–10 tahun terakhir, APA 7th + Mendeley/Zotero, dan **wajib mensitasi ≥5 karya ilmiah dosen/publikasi ITPLN** — ikuti yang lebih ketat.
4. **Privasi data**: nilai nominal finansial perusahaan (rupiah tagihan, Tagihan Susulan, target) sering data internal/privat. Tulis kualitatif + placeholder `[ISI: ...]`; tanya user apa yang boleh dipublikasikan. Jangan pernah menampilkan nominal Rp tanpa izin eksplisit.
5. **Jangan mengarang fakta**: nama pejabat, jumlah kasus, struktur organisasi, luas wilayah = placeholder `[ISI: ...]` sampai user mengisi. Fakta dari web daring wajib diberi catatan "verifikasi dengan dokumen internal". TAPI jangan pasang `[ISI]` untuk fakta yang bisa diambil sendiri dari sumber resmi publik (logo korporat, visi/misi/moto, alamat kantor, statistik perusahaan) — user menegur placeholder itu ("ini emang kamu gabisa ambil dari webnya pln.co.id???"). Ambil sendiri dari situs resmi, cantumkan sumber + tanggal akses di Daftar Pustaka, dan simpan berkas gambar ke folder aset laporan. Resep + fakta terkini: `references/profil-perusahaan-pln.md`.
6. **Deliverable**: SATU file .md di folder proyek user (bukan teks panjang di chat); bab baru di-append ke file yang sama. Simpan di folder magang/skripsi yang sudah ada, bukan di home. Edit file master yang ada — jangan membuat file paralel versi lain tanpa diminta.
7. **Bab per bab, user yang memimpin urutan**: kerjakan HANYA bagian yang diminta (mis. "profil perusahaan dulu, isi analisis belakangan") dan jangan merombak bagian lain tanpa permintaan. Kalau user memilih tetap memakai struktur pedoman lama sementara ("pakai 2020 dulu, nanti remap"), tulis mengikuti struktur itu dan pastikan peta remap + delta versi ada di `references/struktur-laporan-magang.md`.

## Prosedur
1. Clarify dulu: topik, keperluan (skripsi/tugas/referensi), bahasa (ID/EN/keduanya) — satu panggilan clarify berisi beberapa pertanyaan.
2. Cari jurnal paralel: OJS Indonesia (kata kunci "Tagihan Susulan", "P2TL", site:journal/ac.id) + Inggris (IEEE/MDPI: "non-technical losses", "electricity theft"). Kalau web_search kena 403 (backend bergilir), cukup ulangi — query sama sering sukses di backend lain.
3. Verifikasi metadata sitasi (penulis, tahun, volume, halaman) lewat pencarian lanjutan terarah; halaman dari snippet OJS sering tidak akurat.
4. Baca dulu draft lama user + pedoman kampus di folder user, dan **cek VERSI pedoman** (ITPLN: 2020 vs 2025) — struktur babnya beda total. Magang mulai/dilaporkan setelah 15 Des 2025 ikut Pedoman Magang ITPLN 2025 (PD-A03-1-010-02). Detail struktur per versi di references/struktur-laporan-magang.md.
5. Untuk Bab II (profil perusahaan): gali laporan magang lama di folder user — lebih cepat & akurat daripada web. Ekstrak PDF: `uv pip install --python <venv-python> pypdf` (venv Hermes biasanya tanpa modul pip; contoh venv: AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe), lalu extract per halaman ke .txt, grep fakta (sejarah, wilayah, struktur, divisi, nama jabatan).
6. Susun draft dengan logika corong: Latar Belakang = masalah umum → regulasi → kendala teknis → konteks unit → pernyataan tujuan; target 2–4 halaman Word (TNR 12, spasi 1,5).
7. Placeholder: tandai semua yang harus diisi user dengan `[ISI: ...]`; jelaskan di akhir pesan daftar yang harus diisi.
8. Append bab baru ke file .md yang sama (patch sebelum section akhir), lalu beri MEDIA: path file di balasan.
9. **Logbook mingguan = file .docx milik user, bukan markdown.** Logbook ada di `<folder magang>/Minggu N/Logbook Kegiatan Minggu N.docx`. JANGAN buat .md baru untuk logbook — baca docx dengan `read_file` (auto-extract), lalu **tulis balik ke docx yang sama** pakai `python-docx` (venv Hermes: `python` sudah punya docx 1.x). Backup dulu file aslinya (`cp X.docx X.bak.docx`) sebelum menimpa. Resep lengkap + aturan kalimat di `references/logbook-mingguan.md`.
10. **Pertanyaan format/teknis (font, margin, spasi, sistematika, shortcut Word) dijawab dari PDF pedoman yang ada di folder user, bukan dari ingatan**: ekstrak dengan pypdf per halaman, kutip halaman/ketentuan yang relevan, dan sebutkan bila pedoman yang ditanyakan sudah digantikan versi lebih baru (mis. pertanyaan "menurut pedoman 2020?" → jawab 2020 + bandingkan baris demi baris dengan 2025 yang berlaku).

## Skripsi + publikasi jurnal (satu proyek, bukan dua tim)

Skripsi dan artikel jurnal dari riset yang sama = SATU proyek, dijalankan pakai skill `tim-riset` (bagian "Mode: jurnal SINTA vs skripsi" + preset "Skripsi + Jurnal SINTA"). Jangan buat tim/skill kedua untuk skripsi. Aturan: angka, tabel, gambar, dan referensi wajib identik di kedua naskah; salah satu berubah -> revisi yang lain juga. Struktur bab skripsi tetap ikut pedoman kampus.

## Perangkap
- Website profil resmi BUMN/instansi (misal portal E-PPID, pln.co.id) berbasis SPA (Vue/React/Nuxt). Jangan buru-buru menyerah dan minta user menyalin teks: `curl -sL -A "Mozilla/5.0 ..." <url> -o page.html` dari terminal, lalu buang `<script>/<style>` + ubah tag jadi newline via python — cara ini mengembalikan teks halaman lengkap (berhasil untuk pln.co.id). SPA membalas **HTTP 200 walau halamannya "Page not found"**: cek body dulu, dan temukan URL asli dari `href` di halaman nav. Subdomain versi Indonesia bisa tidak resolve dari jaringan lokal walau domain utama jalan — ambil wording versi ID dari snippet mesin pencari, lalu cek silang dengan dokumen resmi.
- Peta Google My Maps (`google.com/maps/d/u/0/viewer?mid=...`) tidak bisa di-scrape sebagai halaman web (SPA), TAPI datanya bisa diunduh sebagai KML: `curl -sL -A "Mozilla/5.0" "https://www.google.com/maps/d/kml?mid=<MID>&forcekml=1"` lalu parse XML untuk batas wilayah/layer posisi — resep + pitfall di `references/peta-my-maps.md`. Jangan buru-buru minta screenshot/export dari user sebelum mencoba jalur KML.
- Tanggal di draft user sering salah (tahun ganda/salah pada periode magang) — cek silang dan beri tahu.
- PDF laporan lama sering butuh OCR sebagian; pypdf tetap mengekstrak halaman ber-teks — hasilkan teks mentah dulu, baru OCR halaman yang benar-benar kosong.
- Visi/misi & nama pejabat cepat basi — tulis versi yang ditemukan + catatan "sesuaikan dengan dokumen internal terbaru".
- Judul/draft lama user bisa tidak sinkron dengan topik baru (mis. ganti topik PLTS → P2TL) — ingatkan bahwa sampul & isi lama harus disesuaikan.
- Logbook yang sudah dirapikan pada minggu sebelumnya adalah **penentu gaya** untuk minggu berikutnya: baca 1–2 logbook terakhir yang sudah baku, contek pola kalimatnya (kata kerja pembuka, urutan klausa, cara menyebut daya/kawasan), lalu edit minggu baru supaya konsisten — jangan bikin gaya baru tiap minggu.
- Struktur bab ITPLN 2020 vs 2025 beda: di 2025 hal. Konsep Teori pindah dari Bab IV ke Bab III (3.2), Bab IV jadi "Hasil dan Pembahasan", dan "Deskripsi Tugas" bukan subbab baku lagi (2.4 = Lokasi Pelaksanaan). Sebelum menambah/menyerahkan konten ke draft lama, sinkronkan dulu nama & nomor bab ke versi pedoman yang berlaku — atau tanya user mana yang dipakai cohort-nya.

## Referensi
- `references/struktur-laporan-magang.md` — struktur Bab I–V versi Pedoman Magang ITPLN 2025 (PD-A03-1-010-02): isi tiap bab, TOR, format tipografi, lampiran, delta vs pedoman 2020
- `references/p2tl-tagihan-susulan.md` — domain P2TL: golongan pelanggaran, rumus TS, jurnal kunci, fakta unit UP3 Bandengan
- `references/logbook-mingguan.md` — membakukan kolom "Kegiatan" logbook mingguan (.docx): kata kerja sesuai peran mahasiswa (pendamping/helper), koreksi diksi & format baku, resep skrip python-docx, daftar pertanyaan klarifikasi
- `references/peta-my-maps.md` — Google My Maps unit: unduh KML via endpoint `forcekml`, parse batas/layer/tetangga wilayah, tips screenshot bersih untuk Gambar laporan
- `references/profil-perusahaan-pln.md` — Bab II profil perusahaan: visi/misi/moto terkini, makna logo, resep ambil logo & teks resmi dari pln.co.id (curl + parse + `vision_analyze`), entri APA-nya
