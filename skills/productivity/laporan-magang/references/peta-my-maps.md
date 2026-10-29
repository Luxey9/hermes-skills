# Peta Google My Maps → batas wilayah & gambar laporan (resep)

Dipakai saat laporan butuh peta wilayah kerja unit / deskripsi batas (subbab profil umum atau lokasi pelaksanaan), atau saat user mengirim link `google.com/maps/d/u/0/viewer?mid=<MID>&ll=...`.

## Langkah

1. **Unduh KML** (jangan scrape halaman viewer-nya — itu SPA, hasilnya cuma legend terpotong):
   ```bash
   curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
     "https://www.google.com/maps/d/kml?mid=<MID>&forcekml=1" -o map.kml
   ```
   File beberapa MB itu wajar.
2. **Parse struktur** (xml.etree, namespace `http://www.opengis.net/kml/2.2`): telusuri `Document → Folder` sebagai layer, hitung Placemark/Point/LineString/Polygon per layer. Pola umum: layer `BATAS_WILAYAH_<UID>` (poligon batas semua UP3), layer `<UNIT> 2` (poligon wilayah unit yang dituju), sisanya titik aset dari file xlsx (kode SPLT/FAT).
3. **Batas & tetangga wilayah**: ambil semua `<coordinates>` per placemark → bbox; untuk cek wilayah yang **bersinggungan**, hitung jarak minimum antar-titik poligon (sampling tiap ~N titik). Jarak ≈ 0 km = berbatasan langsung; > 1 km = biasanya tidak bersinggungan. Bandingkan dengan teks batas di draft user — kalau berbeda, tambahkan catatan `[ISI: verifikasi]`, jangan langsung menimpa teks user.
4. **Luas area**: polygon shoelace dengan proyeksi lokal (dx = dlon × 111,32 × cos(lat tengah)). **Cek dulu bentuk poligonnya** — poligon pesisir bisa menjorok ke laut/kepulauan, luasnya membengkak jauh di atas luas daratan; jangan klaim angka luas dari KML tanpa cek.
5. **Simpan KML di folder kerja user** (`<folder magang>/Peta wilayah <unit>.kml`) supaya user bisa buka di Google Earth → screenshot tajam untuk Gambar laporan.
6. **Screenshot untuk laporan**: instruksikan matikan semua layer titik aset (SPLT/FAT dkk.) — sisakan layer batas wilayah saja. Tulis instruksi ini ke draft/chat.

## Pitfall

- Layer titik aset jumlahnya ratusan; kalau ikut ter-screenshot, gambar laporan jadi sampah visual — selalu matikan dulu.
- `name` placemark tidak konsisten (kadang nama lama, kadang kosong; detail ada di `description` seperti `nama_kp`/`aj`) — jangan menyimpulkan wilayah dari `name` saja; cek `description` + geometri, cross-check dengan dokumen internal user.
- Semua temuan peta (tetangga, luas) tetap ditulis dengan catatan verifikasi — dokumen resmi unit tetap acuan.
