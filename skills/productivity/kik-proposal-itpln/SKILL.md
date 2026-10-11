---
name: kik-proposal-itpln
description: "Use when drafting an ITPLN x MKI Karya Inovasi proposal."
version: 1.0.0
author: ratman4080
license: MIT
metadata:
  hermes:
    tags: [ITPLN, MKI, Kompetisi, Proposal, EBT, Kepedulian]
    category: productivity
---

# Proposal Kompetisi Karya Inovasi dan Kepedulian (ITPLN x MKI)

Dokumen acuan: `Buku Panduan Kompetisi Karya Inovasi.pdf` (folder Riset user).
Rekomendasi topik tersimpan di `Rekomendasi_Topik_Lomba_KIK_2026_v2.md`.

## Trigger

User minta bantu milih topik, menyusun, atau mereview proposal kompetisi
ITPLN x MKI. Juga saat diminta menghitung kelayakan prototipe/timeline lomba ini.

## Aturan yang mengikat (jangan lupa, sering terlewat)

- **Self-funding 100%.** Tidak ada dana panitia/hibah institusi. Biaya = kriteria pemilihan topik,
bukan catatan kaki. Setiap usulan wajib disertai estimasi rupiah.
- **Tidak ada fase inkubasi.** Jangan rancang model bisnis yang butuh pendampingan usaha jangka panjang.
- **Video uji fungsi prototipe wajib diunggah 8–21 Okt 2026** bersama proposal dan lembar pengesahan.
  Prototipe harus SUDAH jadi dan SUDAH diuji saat proposal dikirim — bukan rencana pembuatan.
  Selalu hitung mundur dari tanggal ini saat menilai kelayakan topik.
- **Komposisi tim:** 1 Ketua Pengusul (dosen ATAU mahasiswa) + 2–4 mahasiswa, wajib gabungan
  dosen aktif dan mahasiswa aktif. Rekrutmen tim adalah risiko jadwal yang nyata.
- **TKT self-assessment 1–9 wajib** dengan bukti pengujian internal. Rubrik menulis "TKT lebih
  tinggi dihargai lebih", tapi syarat mutlaknya adalah bukti **cocok dengan klaim** — bukan
  setinggi mungkin. Jangan pernah tulis klaim TKT yang belum didukung alat/data yang ada:
  tahap "Validasi Lapangan & Verifikasi Mandiri TKT" (8–14 Nov 2026) memverifikasi klaim itu.
  Posisi jujur sebelum alat dirakit = **TKT 3** (konsep terbukti analitis/eksperimental).
  TKT 4 = alat dirakit & diuji di lingkungan laboratorium. TKT 5 = diuji di lingkungan
  relevan (mis. paket baterai asli dari bengkel). Skala: Permenristekdikti No. 42/2016.

## Yang TIDAK wajib saat submisi proposal

Panduan Bab IV hanya menyebut lima lampiran: CV tim, surat pernyataan pembiayaan mandiri,
pernyataan bebas plagiarisme, bukti pengujian/foto prototipe, draf HKI. **Surat mitra,
nama vendor terkunci, harga final, dan surat kerja sama BUKAN syarat** — cukup jadi rencana
di BMC/RAB. Jangan buang waktu pemilihan topik untuk mengurus itu di tahap proposal.
Yang benar-benar gating: **tim terbentuk** (lembar pengesahan butuh tanda tangan dosen
pendamping) dan **prototipe fisik bisa direkam video**.

## Bobot penilaian → urutan prioritas desain

| Komponen | Bobot | Cara memenuhinya |
|---|---|---|
| Orisinalitas & Kebaruan (Novelty) | **30%** | State-of-the-art dulu; kalau topiknya sudah ada preseden publik, gugur |
| TKT & Fungsionalitas | 25% | Data uji nyata, bukan simulasi saja |
| Dampak Lingkungan & Keberlanjutan | 20% | Angka: kWh, kg CO2, % limbah tereduksi |
| Hilirisasi & Kelayakan Ekonomi | 15% | BMC lengkap + TAM, bukan "bisa dijual" |
| Penyajian & Komunikasi | 10% | Pitch di depan PLN/MKI/ESDM/BUMN |

Aturan praktis: **novelty dulu, baru keterjangkauan prototipe.** Topik setajam apa pun gugur
kalau alatnya butuh >3 minggu atau >Rp 15 juta untuk dibuktikan.

## Format dokumen (berbeda dari dokumen kampus lain)

- Kertas A4, **Times New Roman 12 pt**, spasi 1.5, **margin 3-3-3-3 cm**.
- Bab: Ringkasan Eksekutif (≤500 kata) → Bab 1 Pendahuluan (1.1 Latar Belakang & Validasi
  Masalah, 1.2 Tujuan & Sasaran, 1.3 Urgensi Dampak Lingkungan/NZE/ESG) → Bab 2
  (2.1 Keunggulan Teknis & Novelty, 2.2 Self-Assessment TKT, 2.3 Kelayakan Operasional &
  Efisiensi Energi) → Bab 3 (3.1 BMC, 3.2 Potensi Pasar/TAM, 3.3 Kesiapan HKI) → Bab 4
  (4.1 Diagram Alir, 4.2 Pembagian Peran Tim) → Bab 5 Rincian Biaya Mandiri & Jadwal.
- Lampiran wajib: CV tim, surat pernyataan pembiayaan mandiri **bermaterai 10.000**, surat
  keaslian & bebas plagiarisme **bermaterai 10.000**, bukti pengujian/foto prototipe, draf HKI.
- Sub-tema tertulis di panduan harus muncul sebagai kata kunci di judul & Bab 1.
  EBT: pembangkit surya/angin/hidro/biomassa/geothermal, Smart Grid, Energy Storage System.
  Teknologi Ramah Lingkungan: efisiensi energi, EV charging, pengolahan limbah energi,
  circular economy.

## Cara menilai calon topik (urutan yang benar)

1. Cek preseden publik topik itu (preseden kuat = novelty mati di komponen 30%).
2. Hitung biaya mandiri prototipe minimum yang bisa diuji.
3. Hitung mundur ke 21 Okt: prototipe + video bisa jadi?
4. Cek fit-nya ke sub-tema tertulis (makin banyak sub-tema terpenuhi, makin mudah dibela).
5. Baru cek ketersediaan laboratorium/situs/izin (akses situs lambat = risiko jadwal).

## Hilirisasi & infrastruktur digital (opsional)

Menyambungkan server sendiri (Linux + CasaOS + agen AI self-hosted) ke alat boleh, tapi
**jangan jadikan itu klaim novelty** — kompetisi ini menilai EBT/teknologi ramah lingkungan,
agen AI yang ditempel ke alat uji terbaca sebagai gimmick dan bisa MENURUNKAN bobot Novelty 30%.
Pasang sebagai infrastruktur pendukung di 2.1.2 dan BMC blok Key Resources/Channels, dengan
justifikasi nyata: **kedaulatan data + tetap jalan tanpa internet stabil** (relevan untuk
situs 3T). Demo yang kuat: cabut internet, sistem tetap merekam, notifikasi terkirim saat
sinkron. Jangan pakai "openclaw" tanpa memperjelas mana yang dimaksud — ada dua proyek
bernama itu (agen AI `openclaw/openclaw`, dan reimplementasi game Captain Claw 1997).

## Pitfalls

- Jangan pakai format laporan magang (Arial, margin 4-2-3.5-2.5) untuk dokumen ini.
- Data nominal/privat (mis. tagihan pelanggan) tidak boleh masuk dokumen yang diunggah publik.
- Jangan sebut "untuk keperluan edukasi" sebagai justifikasi; rubric tidak menilai itu.
- Portal submisi: bit.ly/KaryaInovasi2026 (perlu login Google). Sekretariat: bpm@itpln.ac.id.
