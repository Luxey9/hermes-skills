---
name: laporan-magang
description: Draft Indonesian internship reports or thesis chapters.
---

# Laporan Magang / Skripsi — Drafting (Bahasa Indonesia)

Membantu mahasiswa Indonesia menyusun laporan magang/skripsi: cari jurnal, susun bab, kelola referensi, jaga privasi data perusahaan.

## Aturan selalu
1. **Bahasa**: jawab dan tulis semua draft dalam Bahasa Indonesia.
2. **Format Narasi vs Poin (Gaya Akademis)**: Bagian sejarah, latar belakang, dan pengantar ditulis dalam bentuk **paragraf naratif mengalir** (kronologis, tanpa poin-poin kaku). Bagian visi, misi, tata nilai (AKHLAK), pilar strategis, pembagian posko/batas wilayah, serta struktur organisasi dan rincian tugas pokok disajikan secara **proporsional: kalimat pengantar/narasi + poin-poin/bullet yang tegas**, jangan dipaksakan full-paragraf tanpa poin (sulit dibaca penguji sidang) dan jangan pula full-bullet tanpa kalimat penghubung.
3. **Rujukan ≤5 tahun**: jurnal/artikel harus dari 5 tahun terakhir; REGULASI (UU, Permen, Perdir) dikecualikan karena dasar hukum. Kalau ada jurnal tua dalam set, ganti dengan padanan terbaru — jangan dibiarkan.
4. **Privasi data**: nilai nominal finansial perusahaan (rupiah tagihan, Tagihan Susulan, target) sering data internal/privat. Tulis kualitatif + placeholder `[ISI: ...]`; tanya user apa yang boleh dipublikasikan. Jangan pernah menampilkan nominal Rp tanpa izin eksplisit.
5. **Jangan mengarang fakta**: nama pejabat, jumlah kasus, struktur organisasi, luas wilayah = placeholder `[ISI: ...]` sampai user mengisi. Fakta dari web daring wajib diberi catatan "verifikasi dengan dokumen internal".
6. **Deliverable**: SATU file .md di folder proyek user (bukan teks panjang di chat); bab baru di-append ke file yang sama. Simpan di folder magang/skripsi yang sudah ada, bukan di home.

## Prosedur
1. Clarify dulu: topik, keperluan (skripsi/tugas/referensi), bahasa (ID/EN/keduanya) — satu panggilan clarify berisi beberapa pertanyaan.
2. Cari jurnal paralel: OJS Indonesia (kata kunci "Tagihan Susulan", "P2TL", site:journal/ac.id) + Inggris (IEEE/MDPI: "non-technical losses", "electricity theft"). Kalau web_search kena 403 (backend bergilir), cukup ulangi — query sama sering sukses di backend lain.
3. Verifikasi metadata sitasi (penulis, tahun, volume, halaman) lewat pencarian lanjutan terarah; halaman dari snippet OJS sering tidak akurat.
4. Baca dulu draft lama user + pedoman kampus (biasanya ada di folder user) agar struktur bab pas dengan kampusnya.
5. Untuk Bab II (profil perusahaan): gali laporan magang lama di folder user — lebih cepat & akurat daripada web. Ekstrak PDF: `uv pip install --python <venv-python> pypdf` (venv Hermes biasanya tanpa modul pip; contoh venv: AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe), lalu extract per halaman ke .txt, grep fakta (sejarah, wilayah, struktur, divisi, nama jabatan).
6. Susun draft dengan logika corong: Latar Belakang = masalah umum → regulasi → kendala teknis → konteks unit → pernyataan tujuan; target 2–4 halaman Word (TNR 12, spasi 1,5).
7. Placeholder: tandai semua yang harus diisi user dengan `[ISI: ...]`; jelaskan di akhir pesan daftar yang perlu diisi.
8. Append bab baru ke file .md yang sama (patch sebelum section akhir), lalu beri MEDIA: path file di balasan.

## Skripsi + publikasi jurnal (satu proyek, bukan dua tim)

Skripsi dan artikel jurnal dari riset yang sama = SATU proyek, dijalankan pakai skill `tim-riset` (bagian "Mode: jurnal SINTA vs skripsi" + preset "Skripsi + Jurnal SINTA"). Jangan buat tim/skill kedua untuk skripsi. Aturan: angka, tabel, gambar, dan referensi wajib identik di kedua naskah; salah satu berubah -> revisi yang lain juga. Struktur bab skripsi tetap ikut pedoman kampus.

## Perangkap
- Website profil resmi BUMN/instansi (misal portal E-PPID) sering berbasis SPA (Single Page Application / Vue / React) di mana HTTP fetch mentah hanya mengembalikan metadata kerangka kosong tanpa teks body — jika browser automation tidak aktif, minta user teks langsung atau cari dokumen PDF laporan tahunan.
- URL Google Maps viewer (`google.com/maps/d/u/0/viewer?mid=...`) tidak bisa diekstrak isinya — minta screenshot/export, jangan buang waktu mencoba.
- Tanggal di draft user sering salah (tahun ganda/salah pada periode magang) — cek silang dan beri tahu.
- PDF laporan lama sering butuh OCR sebagian; pypdf tetap mengekstrak halaman ber-teks — hasilkan teks mentah dulu, baru OCR halaman yang benar-benar kosong.
- Visi/misi & nama pejabat cepat basi — tulis versi yang ditemukan + catatan "sesuaikan dengan dokumen internal terbaru".
- Judul/draft lama user bisa tidak sinkron dengan topik baru (mis. ganti topik PLTS → P2TL) — ingatkan bahwa sampul & isi lama harus disesuaikan.

## Referensi
- `references/struktur-laporan-magang.md` — struktur Bab I–V laporan magang (contoh pedoman ITPLN) + isi tiap bab
- `references/p2tl-tagihan-susulan.md` — domain P2TL: golongan pelanggaran, rumus TS, jurnal kunci, fakta unit UP3 Bandengan
