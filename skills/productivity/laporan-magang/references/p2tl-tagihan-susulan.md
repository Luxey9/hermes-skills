# P2TL & Tagihan Susulan — catatan domain

## Definisi & dasar hukum
- P2TL = Penertiban Pemakaian Tenaga Listrik: rangkaian perencanaan, pemeriksaan, tindakan teknis dan/atau hukum, penyelesaian (Permen ESDM 33 Tahun 2014 Pasal 13; diperbarui Permen ESDM 2 Tahun 2025; Perdir PLN 088-Z.P/DIR/2016).
- Sanksi pelanggaran: pemutusan sementara dan/atau pembongkaran rampung + pembayaran Tagihan Susulan (TS).

## Golongan pelanggaran (Permen ESDM 33/2014 Pasal 13)
- **PI**: mempengaruhi batas daya, tidak mempengaruhi pengukuran energi.
- **PII**: mempengaruhi pengukuran energi, tidak mempengaruhi batas daya.
- **PIII**: mempengaruhi batas daya DAN pengukuran energi.
- **PIV**: bukan konsumen (sambungan liar/tanpa kontrak).

## Formulasi Matematis Teknis & Tagihan Susulan
1. **Daya Aktif 1-Fase & 3-Fase**:
   - 1-Fase: $P = V \times I \times \cos \varphi$
   - 3-Fase: $P = \sqrt{3} \times V_{LL} \times I_L \times \cos \varphi$
2. **Formulasi Error Metrologi Pengujian Meter**:
   - $\% \text{Error} = \frac{P_{\text{display}} - P_{\text{standar}}}{P_{\text{standar}}} \times 100\%$
   - Atau berbasis putaran/impuls: $E = \frac{T_{\text{teori}} - T_{\text{aktual}}}{T_{\text{aktual}}} \times 100\%$
3. **Formulasi Tagihan Susulan (Permen ESDM No. 33/2014 & Perdir 088-Z.P/DIR/2016)**:
   - **TS1 (Pelanggaran Golongan I / Pembatas Daya)**:
     * Pelanggan dengan Biaya Beban: $\text{TS}_1 = 6 \times (2 \times \text{Daya Tersambung (kVA)}) \times \text{Biaya Beban (Rp/kVA)}$
     * Pelanggan dengan Rekening Minimum: $\text{TS}_1 = 6 \times (2 \times \text{Rekening Minimum (Rp)})$
   - **TS2 (Pelanggaran Golongan II / Pengukuran Energi)**:
     * $\text{TS}_2 = 9 \times 720 \text{ jam} \times \text{Daya Tersambung (kVA)} \times 0{,}85 \times \text{Tarif per-kWh tertinggi pada golongan tarif}$
     * *Catatan Teknis*: Faktor pengali 9 mengasumsikan durasi pelanggaran maksimal 9 bulan ke belakang; 720 jam adalah jam komersial dalam sebulan ($24 \times 30$); faktor 0,85 merepresentasikan faktor beban rata-rata (*load factor*) pemakaian kontinu saat alat ukur terganggu.
   - **TS3 (Pelanggaran Golongan III / Daya & Energi)**:
     * $\text{TS}_3 = \text{TS}_1 + \text{TS}_2$
   - **TS4 (Pelanggaran Golongan IV / Non-Konsumen/Sambung Liar)**:
     * Dihitung berdasarkan daya kedapatan saat pemeriksaan lapangan dengan penalti tarif dan jam nyala khusus non-konsumen.

## Dinamika Teknis Kelainan APP di Lapangan
- **Pengukuran Langsung (TR < 41,5 kVA)**: Modus dominan adalah bypass jumper kawat fasa atau netral sebelum meter, perusakan segel metrologi/PLN, atau injeksi arus balik netral.
- **Pengukuran Tidak Langsung (CT-PT / Pelanggan Daya Besar)**:
  * Pembalikan polaritas terminal sekunder trafo arus (CT): menghasilkan error negatif signifikan (-33% pada 1 CT terbalik di sistem 3 fasa, hingga -66% pada pengawatan beda fasa).
  * Pemutusan sambungan kawat tegangan (PT): fasa kehilangan referensi tegangan sehingga konsumsi daya pada fasa tersebut tidak tercatat sama sekali.
  * Harmonisa & Saturasi Inti CT: beban non-linear industri menyebabkan distorsi bentuk gelombang yang menurunkan akurasi rasio transformasi arus CT.

## Konsep kunci
- Susut teknis (disipasi I²R, trafo) vs susut non-teknis (pencurian, manipulasi meter, salah pengawatan, error billing). P2TL menekan susut non-teknis; saving kWh = energi yang "diselamatkan".
- Indikasi pelanggaran: anomali data AMR/EMSYST/AP2T + pemeriksaan fisik APP (kWh meter, CT, PT, segel). Contoh error teknis: polaritas CT terbalik bisa menyebabkan error pengukuran puluhan persen.

## Jurnal kunci (≤5 tahun, metadata terverifikasi)
- Khairunnisah, A. (2024). P2TL ULP Kenten. JITET 12(1), 758–765. doi 10.23960/jitet.v12i1.3955
- Khairunnisah, A. (2024). P2TL ULP Koba. ELKOM 17(2), 1–8. doi 10.51903/elkom.v17i2.1971
- Simanjuntak & Sembiring (2024). Pelanggaran kWh meter digital ULP Aek Kanopan. Jurnal Ilmiah Tenaga Listrik 3(2), 49–54 (ojs.polmed.ac.id, artikel 1758).
- Carr & Thomson (2022). Non-Technical Electricity Losses. Energies 15(6), 2218. doi 10.3390/en15062218
- Wong et al. (2025). Energy Theft Identification: State Estimation Model for Partial Meter Bypass. IEEE Access. doi 10.1109/ACCESS.2025.3587208

## Unit kerja user: PT PLN (Persero) UP3 Bandengan
- Gabungan Area Pelayanan Kapuk + Gunung Sahari (Januari 2016), di bawah UID/Distribusi Jakarta Raya.
- Luas 77,29 km²; 3 posko: Gunung Sahari, Kota, Kapuk; batas: Area Cengkareng (utara/timur), Area Cempaka Putih (selatan), Area Grogol & Kebon Jeruk (barat).
- Struktur: Manager + AM Perencanaan, AM Konstruksi, AM Jaringan, AM Niaga, AM Transaksi Energi Listrik (TEL), AM Keuangan/SDM/Administrasi.
- Divisi TEL = pemegang tugas billing, pengendalian susut, P2TL, AMR, pemeliharaan APP, manajemen segel — bagian paling relevan untuk topik P2TL.
- **Pembagian tim P2TL lapangan**: *Mensar* = pelanggan menengah & besar (di atas 41,5 kVA s.d. 30 MVA); *Mencil* = pelanggan kecil (antara lain penertiban sambungan liar/P-IV).
- **Sebutan lapangan golongan**: P1/P2/P3/P4 = Golongan I/II/III/IV (padanan PI–PIV). Di dokumen resmi tulis "Golongan IV (P-IV)", bukan "P4".
- **Peran mahasiswa magang**: pendamping/helper (membawa & menyiapkan alat ukur, mencatat hasil ke Berita Acara) — bukan pelaksana pengukuran.
- **Alat ukur**: *Calmet* = alat uji/kalibrasi kWh meter (mengukur error); *clamp meter/tang amper* = pengukur arus. Dua alat berbeda, jangan ditukar.
