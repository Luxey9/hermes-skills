# Playbook fase scout - topik lomba/proposal inovasi

Dipakai bersama `SKILL.md` (bagian "Fase scout topik lomba/proposal"). Semua langkah di bawah dijalankan lewat `web_search`/`web_extract` di dalam `execute_code`, di-batch 6-10 kueri per panggilan dan hasilnya di-print ringkas (judul + URL + 200-250 karakter deskripsi). Jangan satu kueri satu panggilan.

## 1. Baca poster / buku petunjuk

- Poster lomba: `vision_analyze` dulu; kalau balas tidak ada data gambar, langsung ke skill `image-ocr` (Windows OCR, `scripts/win_ocr.ps1`) dengan path bergaya `C:/...`. OCR cukup untuk nama lomba, penyelenggara, ruang lingkup, hadiah, tanggal.
- Buku petunjuk/sistematika proposal biasanya di balik bit.ly + login Google -> tidak ada jalur anonim. Serahkan link ke user dan minta dia menyebut bobot kriteria penilaian: strategi topik bergantung padanya (novelty vs dampak vs kelayakan).

## 2. Cek "sudah ada pilotnya?" (gerbang wajib)

Kueri pengecekan, satu keluarga per kandidat:

```
<konsep> Indonesia pilot | proyek | peresmian | beroperasi
<konsep> Indonesia GIZ | UNDP | IPNLF | IESR | Pertamina NRE
site:giz.de OR site:undp.org <konsep>
```

Sinyal kandidat sudah "diambil": ada press release peresmian, factsheet, atau - paling mematikan - *manufacturing guidelines*/panduan replikasi. Kalau ada, jangan buang kandidat: potong jadi lapisan yang belum dikerjakan (digital/monitoring, model kelola koperasi, dampak terukur) ATAU ganti topik.

Contoh yang terbukti menggugurkan kandidat (verifikasi ulang sebelum dipakai):

- **Solar ice maker / cold storage surya untuk nelayan** - sudah diresmikan UNDP + GIZ + IPNLF di Kawa (Maluku), unit kedua di Sulamu (Kupang), sudah ada panduan manufaktur GIZ. Kapasitas lomba-skala (1 t es/hari) bukan lagi celah.
- **Monitoring PLTS IoT (ESP32 + Blynk/Telegram)** - ratusan jurnal, akurasi 98%+. Itu skripsi 101, bukan inovasi lomba.
- **PLTS komunal/desa jadi aset telantar** - kasusnya kuat (PLTS bantuan rusak inverter, terbengkalai) tapi solusinya sudah banyak ditulis; hanya laku sebagai *layer* di topik lain.

## 3. Kunci novelty ke konflik teknis, bukan ke produk

Pola yang paling kuat: temukan konflik dua efek dari teknologi yang sama, yang literatur terbaru baru *mencatat* dan belum menyelesaikan sizenya untuk Indonesia.

Contoh bentuk yang dipakai: PLTS terapung **menurunkan suhu air** (menguntungkan) tetapi juga **menurunkan oksigen terlarut dekat permukaan** (fatal untuk tambak intensif) - belum ada yang mengunci rasio penutupan panel ke DO/suhu untuk tambak tropis. Novelty = pertanyaan riset terukur (rasio -> DO, suhu, ekonomi), bukan "membuat alat".

Cara cepat menemukan konflik: baca kesimpulan/limitations paper 2025-2026, bukan abstraknya. Kalimat "namun", "belum dikaji", "perlu penelitian lanjutan" = kandidat pertanyaan riset.

## 4. Situs dan jangkauan penulis (hard constraint)

Situs pilot menentukan skor kelayakan. Prioritaskan lokasi dalam wilayah kerja penulis (mis. mahasiswa magang di PLN UP3 Bandengan -> Kepulauan Seribu, pantura Jakarta-Bekasi) supaya akses data, mitra kelurahan, dan izin lapangan realistis di dalam tanggal lomba. Kandidat tanpa situs terjangkau = risiko jadwal, turunkan peringkat meski literaturnya kuat.

Perhatikan juga pekerjaan yang butuh izin (pulau/kawasan konservasi) atau analisis laboratorium - itu yang paling sering menggagalkan pilot 3 bulan.

## 5. Kecocokan skill penulis

Kalau user punya skill perangkat lunak (React/Supabase/Next), kandidat yang menyertakan dashboard/monitoring live lebih sulit ditiru tim lain di depan juri daripada kandidat yang hanya lebih baik dari sisi hardware. Tandai ini eksplisit di matriks sebagai "kecocokan skill kamu".

## 6. Anchor framing nasional (verifikasi ulang tiap tahun)

Sebutkan 3-4 sinyal kebijakan terbaru supaya proposal "menempel" ke program yang sedang berjalan: program PLTS skala besar + Koperasi Desa/Kelurahan Merah Putih, dedieselisasi pembangkit pulau/3T, RUPTL terbaru (kapasitas surya & BESS), program elektrifikasi desa (Lisdes), percepatan sampah-energi, program kementerian lain yang menyentuh sektor sama (mis. KKP untuk tambak udang, Kemendes untuk EBT tambak). Ambil dari siaran pers resmi (esdm.go.id, kkp.go.id, pln.co.id) + IESR, bukan dari agregator berita.

## 7. Skeleton dokumen keluaran (bentuk yang diterima user)

```
# Rekomendasi Topik v<N> - <nama lomba>
> untuk <user>, <prodi> | <tanggal>
## 0. Kenapa versi sebelumnya diganti   (kalau ini revisi)
## 1-3. Kandidat (tiap kandidat):
   ### Judul opsi (2 alternatif)
   ### Masalah masyarakat + angka + sumber
   ### Novelty (sebutkan celahnya secara spesifik)
   ### Literatur kunci (bernomor, <=5 tahun, DOI lengkap)
   ### Kelayakan pilot di rentang tanggal lomba
   ### Metrik dampak yang DIUKUR, bukan diklaim
## 4. Matriks pemilihan + rekomendasi eksekusi (ambil mana, cadangan mana)
## 5. Langkah berikutnya (urut, dengan keputusan yang butuh user)
### Lampiran - tautan utama terverifikasi
```

Matriks: kolom `Kekuatan literatur | Kesulitan pilot | Kecocokan skill user | Kekuatan "kepedulian" | Peluang juara`, bintang 3 tingkat, lalu satu paragraf "rekomendasi eksekusi" yang menyebut topik inti + cadangan.

Bahasa keluaran mengikuti user (Indonesia). Tulis ke folder proyek user, bukan scratch. Lampirkan lewat `MEDIA:<path absolut>` dan sebut di akhir jawaban bahwa file sudah di-stash.

## 8. Anti-pola

- Mengarang judul/literatur tanpa kueri pembuktian - setiap DOI harus punya URL halaman artikel yang benar-benar dikembalikan pencarian.
- Menyusun nama jurnal/volume/DOI dari snippet deskripsi hasil search (lihat aturan `citation_*` di SKILL.md).
- Membandingkan dua versi dokumen rekomendasi tanpa menyebut eksplisit alasan versi lama digugurkan - user memakainya untuk memutuskan.
