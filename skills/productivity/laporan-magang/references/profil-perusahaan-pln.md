# Profil Perusahaan PT PLN (Persero) — fakta terkini & cara mengambilnya

Dipakai untuk Bab II (2.2 Profil Umum Perusahaan: logo + makna, visi, misi, moto) dan setiap kali butuh data korporat resmi. **Jangan tinggalkan `[ISI: sisipkan logo]`** — user menegur karena ini bisa diambil sendiri dari situs resmi.

## Cara mengambil (urutan yang terbukti jalan)

1. `web_extract` sering gagal untuk domain korporat: subdomain tertentu dijawab "Blocked: URL targets a private or internal network address" dan backend ekstraktor bergilir bisa balas 403. Jangan berhenti di situ — **pakai `curl` dari terminal**:
   ```bash
   UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
   curl -sL --max-time 40 -A "$UA" "https://www.pln.co.id/about-us-en/company-profile-en" -o cp.html -w "%{http_code} %{size_download}b\n"
   ```
2. Halaman SPA tetap **HTTP 200 walau isinya "Page not found"** — cek body dulu (`grep -q "Page not found"`), dan temukan URL asli dari `href` di halaman nav (mis. `/tentang-kami/profil-perusahaan` = 404-body, sedangkan `/about-us-en/company-profile-en` = halaman sungguhan).
3. Ubah HTML → teks dengan python (buang `script/style`, tag → newline, `html.unescape`, buang baris duplikat), lalu `find` kata kunci ("Vision", "Motto", "Meaning of Logos", "A Brief History").
4. Aset logo: `grep -o 'src="[^"]*"' page.html` lalu saring nama ber-`logo`/`pln`. Unduhan yang terverifikasi (Okt 2026):
   - `https://www.pln.co.id/_pln/pln.DN9ikc4e.png` — logo resmi lengkap (lambang + tulisan PLN), PNG 2560×917, latar transparan.
   - `.../webkorp/asset/file100425_0348_ec74.png` — lambang kotak tanpa tulisan (95×94).
   Simpan ke `<folder magang>/Aset Logo/` dan **verifikasi isinya dengan `vision_analyze`** sebelum dipakai di laporan (jangan menebak dari nama berkas).
5. Subdomain versi Indonesia (`web.pln.co.id`) bisa tidak resolve dari jaringan lokal walau domain utama jalan. Ambil wording versi Indonesia dari snippet mesin pencari untuk URL yang sama, lalu cek silang dengan dokumen Company Profile PLN/news resmi sebelum dipakai.
6. Catat sumbernya di Daftar Pustaka (APA): `PT PLN (Persero). (2026). Profil perusahaan: Visi, misi, dan makna logo. Diakses pada <tanggal>, dari https://www.pln.co.id/` dan perbarui Daftar Gambar (logo jadi Gambar 2.1, nomor gambar setelahnya bergeser).

## Fakta resmi (terverifikasi Okt 2026 — perbarui bila diakses ulang)

**Visi:** "Menjadi Perusahaan Global Top 500 dan #1 Pilihan Pelanggan untuk Solusi Energi." Visi lama ("Perusahaan Listrik Terkemuka se-Asia Tenggara dan #1 Pilihan Pelanggan untuk Solusi Energi") sudah basi — jangan dipakai lagi.

**Misi (4 poin):**
1. Menjalankan bisnis kelistrikan dan bidang lain yang terkait, berorientasi pada kepuasan pelanggan, anggota perusahaan, dan pemegang saham.
2. Menjadikan tenaga listrik sebagai media untuk meningkatkan kualitas kehidupan masyarakat.
3. Mengupayakan agar tenaga listrik menjadi pendorong kegiatan ekonomi.
4. Menjalankan kegiatan usaha yang berwawasan lingkungan.

**Moto:** halaman Indonesia menampilkan **"Listrik untuk Kehidupan yang Lebih Baik"**; halaman Inggris menampilkan **"#1 Energy Solutions"**. Tulis versi Indonesia + catatan agar user mengonfirmasi ke pembimbing — jangan diam-diam memilih salah satu.

**Makna logo (tiga elemen, dari laman korporat):**
| Elemen | Makna |
|---|---|
| Persegi panjang | PLN sebagai perusahaan yang terorganisasi; warna kuning melambangkan pencerahan bagi kehidupan masyarakat. |
| Petir | Tenaga listrik sebagai energi yang bergerak cepat dan dinamis, sebagaimana pegawai PLN yang senantiasa berinovasi untuk pelanggan. |
| Tiga gelombang | Aliran energi listrik pada tiga sektor usaha utama: pembangkitan, transmisi, dan distribusi; warna biru melambangkan loyalitas dan keandalan pegawai. |

**Statistik profil (laman korporat, angka berubah — selalu perbarui):** kapasitas pembangkit 80.189 MW; saluran transmisi 74.973 km; kapasitas gardu 171.807 MVA; saluran distribusi 1.086.835 km; pelanggan 96,2 juta; sambungan daya 192.621 MVA; rasio elektrifikasi 99,83%; SPKLU 5.000 unit.

## Pitfall
- Jangan pakai sumber pihak ketiga (situs konsumen/artikel agensi) untuk makna logo & visi/misi — deskripsinya sering beda dari laman korporat; pakai halaman resmi, situs pihak ketiga hanya sebagai kroscek.
- Setelah mengganti visi/misi di satu file draf, samakan juga di draf kembar (mis. `Latar_Belakang_*.md` dan `Draft Laporan Magang*.md`) — dua file sering hidup berdampingan dan mudah jadi tidak sinkron.
- Nomor subbagian ikut berubah saat menyisipkan "Moto" (AKHLAK yang tadinya nomor 3 jadi 4); rapikan penomoran, jangan menyerahkan subbab bernomor ganda.
- Fakta privat (nominal tagihan, Tagihan Susulan, target) tetap `[ISI: ...]` — aturan privasi hanya untuk data finansial/internal, bukan fakta publik korporat.
