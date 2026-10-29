# Logbook Mingguan Magang — membakukan kolom "Kegiatan"

## Di mana & apa formatnya
- Lokasi: `<folder magang>/Minggu N/Logbook Kegiatan Minggu N.docx` (satu folder per minggu).
- Template baku: "Logbook Kegiatan — Program Magang 5 Bulan PLN Grup", kop identitas (Nama, NIM, Jenjang, Program Studi, Fakultas) + tabel `No | Tanggal | Jam Masuk | Jam Pulang | Kegiatan | Bukti Dokumentasi` (5 baris per minggu, kerja Senin–Jumat), lalu blok tanda tangan `JAKARTA, <tanggal> — Pembimbing Lapangan Kerja Praktek`.
- **Ini dokumen .docx milik user — bukan markdown.** Jangan pernah membuat file .md baru untuk logbook; user menyerahkan docx ke pembimbing.

## Prosedur
1. `read_file` pada docx-nya — Hermes auto-extract teks (tabel jadi baris berurutan), cukup untuk membaca isi tiap sel.
2. Baca juga 1–2 logbook minggu terakhir yang **sudah dibakukan** dulu. Gaya harus konsisten antar minggu; jangan ciptakan pola baru.
3. Tulis kalimat baku untuk tiap baris (lihat aturan di bawah), lalu **tulis balik ke docx yang sama** dengan `python-docx`.
4. **Audit kata kerja dulu** kalau mengerjakan >1 minggu: hitung distribusi kata pertama tiap sel Kegiatan di minggu-minggu sebelumnya (python-docx, `collections.Counter`). Minggu yang satu kata kerjanya berulang di semua butir = yang dibakukan ulang; samakan ke pola yang sudah beragam, jangan mengarang gaya baru.
5. Backup sebelum menimpa: `cp "Minggu N/Logbook Kegiatan Minggu N.docx" "Minggu N/Logbook Kegiatan Minggu N.bak.docx"`.
6. Verifikasi hasilnya dengan `read_file` pada docx setelah disimpan — cek tabel dan blok tanda tangan rapi. Kalau `read_file` menolak ("Terminal environment unavailable / the sandbox may still be starting"), retry sekali; kalau masih gagal, dump isi tabel lewat python-docx dan print — verifikasi setara.
7. **HANYA sentuh minggu yang diminta.** Kalau user bilang "jangan utak-atik selain X & Y", buktikan dengan `ls -l --time-style=+%Y-%m-%d_%H:%M "Minggu "*/Logbook*.docx` dan laporkan jam ubahnya di balasan — user memakai itu sebagai bukti minggu lain tidak tersentuh.
8. Balas ke user dengan tabel perbandingan draf → perbaikan + alasan, lalu daftar `[ISI: ...]`, lalu `MEDIA:` kedua file .docx.

## Resep skrip python-docx

```python
from docx import Document

def isi_tabel(path, rows, tgl_kanan):
    doc = Document(path)
    tbl = doc.tables[0]
    # baris data dikenali dari kolom 0 yang berisi angka (1..5)
    data_rows = [r for r in tbl.rows if r.cells[0].text.strip().isdigit()]
    assert len(data_rows) == len(rows), f"{len(data_rows)} baris vs {len(rows)} data"
    for row, (tgl, masuk, pulang, keg) in zip(data_rows, rows):
        c = row.cells
        c[1].text, c[2].text, c[3].text, c[4].text = tgl, masuk, pulang, keg
    doc.save(path)
```

Pitfall — blok tanda tangan:
- `paragraph.runs` bisa terpecah aneh (teks "JAKARTA, ..." tersebar di beberapa run). Pola aman: kosongkan SEMUA run lalu tulis ulang di `runs[0]`:
  ```python
  for p in doc.paragraphs:
      if 'JAKARTA' in p.text.upper():
          for r in p.runs: r.text = ''
          p.runs[0].text = 'JAKARTA, 16 Oktober 2026     '
  ```
- JANGAN pakai regex `re.sub` yang mengganti sisa baris — kalau tanggal baru sudah ada di dalam teks, hasilnya dobel ("JAKARTA, 16 Oktober 2026     16 Oktober 2026").
- Menulis `.text` pada sel/run membuang format khusus (bold, font) yang ada di dalamnya. Untuk logbook ini aman; kalau butuh format, salin `paragraph.runs[0]` baru dengan `add_run`.

## Aturan kalimat kolom "Kegiatan"

### 1. Kata kerja harus cocok dengan PERAN mahasiswa
Ini kesalahan paling sering. Tanyakan/simpulkan peran sebelum menulis; banyak mahasiswa magang hanya **pendamping (helper)** — membawa & menyiapkan alat, mencatat ke Berita Acara — sementara pengukuran dilakukan pelaksana tim.

| Boleh (kegiatan lapangan mahasiswa) | Jangan tulis (kerja pelaksana tim) |
|---|---|
| memeriksa, mengecek, melakukan pengecekan, menginspeksi, mengikuti/menyertai pemeriksaan, mendampingi, membantu, turut serta dalam, mencatat | mengukur, menguji, mengalibrasi, "melakukan pengukuran", mengoreksi/mengganti meter sebagai pelaku |

Bila ragu, tanyakan sekali: "pengukuran/pemeriksaan langsung dilakukan Anda atau pelaksana tim?"

**Jangan memakai satu kata kerja untuk semua butir.** User menegur "kok mendampingi terus ya, emang gaboleh klo aku bilang pengecekan juga??" ketika 5 dari 5 butir dibuka dengan *Mendampingi*. Yang dilarang cuma kata kerja pengukuran teknis; *melakukan pengecekan / memeriksa* justru dianjurkan karena jujur dan variatif. Aturan: kata "Mendampingi" maksimum **1–2 butir per minggu** (sisakan untuk butir yang memang murni mengikuti/mengamati), sisanya rotasi kata kerja lain. User menilai variasi kata kerja sebagai nilai tambah, jadi pastikan distribusinya sebelum menyerahkan.

### 2. Kalimat harus lengkap
Logbook sering diisi fragmen: *"Pemakaian rendah, sehingga terkena biaya rekening minimum"*, *"Pemeriksaan TM 295 kVA terindikasi beban tidak seimbang"*, *"Sakit Demam"*. Bakukan menjadi S–P lengkap: subjek (mahasiswa/tim) + kata kerja + objek (kWh meter pelanggan) + keterangan (daya, kawasan, temuan).

### 3. Pola baku yang dipakai
```
Mendampingi Tim P2TL <Mensar|Mencil> dalam <pemeriksaan berkala|pemeriksaan rutin|operasi sisir|inspeksi> kWh meter pelanggan <jenis pelanggan> berdaya <n> kVA di kawasan <nama>, <temuan/catatan>.
```
Variasi pembuka: *Mendampingi · Menyertai · Membantu · Mengikuti operasi sisir · Turut serta dalam · Mencatat*. Dipakai bergilir supaya tidak monoton, tapi jangan ganti istilah teknis.

**Panjang: 1–2 baris (±150 karakter).** Logbook ini untuk tanda tangan pembimbing lapangan, bukan esai — kalau kalimat mulai 3 baris, pangkas klausa penjelasnya.

### 4. Diksi & format baku
- "Sasaran Target Operasi" → pleonasme; cukup **Target Operasi (TO)**.
- kWh meter tidak "berkapasitas MVA" — yang MVA adalah **daya tersambung pelanggan**: "kWh meter milik pelanggan pusat data (data center) dengan daya tersambung 27 MVA".
- Yang mengalami fluktuasi beban adalah **pelanggan**, bukan kawasan.
- Lembaga/instansi institusi ditulis bertingkat: "Dinas Lingkungan Hidup Jakarta Barat (JakBar)"; satuan "TM" tetap huruf besar: "pelanggan tegangan menengah (TM)".
- Singkatan (APP, P2TL, TO, BA, EPM, TM, kVA, MVA) dijabarkan pada penyebutan **pertama** di seluruh set logbook, setelah itu boleh singkatan saja.
- Angka + satuan diberi spasi (`53 kVA`, bukan `53kVA`); desimal pakai koma (`41,5 kVA`); "di" (kata depan) terpisah dari tempat, "di-" (awalan) menempel pada kata kerja.
- Ragam cakap → baku: *resto* → **usaha restoran**, *objektifnya* → **dengan sasaran/tujuan**, *kawasa* → **kawasan**, *JakBar* → jabarkan dulu.
- Hari izin/sakit ditulis sebagai kalimat lengkap + alasannya, aman untuk verifikasi pembimbing: "Tidak melaksanakan kegiatan magang karena sakit (demam) dan telah mengajukan izin kepada pembimbing lapangan."

### 5. Jobdesc/mandat organisasi = hal yang WAJAR ditampilkan
Kalau user menerangkan struktur organisasi, singkatan internal, atau peran dirinya (mis. kepanjangan tim, rentang daya yang ditangani tim, pembagian subdivisi) dalam pesannya, ITU BUKAN data privat — tulis apa adanya di logbook. Aturan privasi hanya berlaku untuk **nominal finansial** (rupiah tagihan, Tagihan Susulan, target).

Fakta tim UP3 Bandengan (sudah dikonfirmasi user): ***Mensar*** = pelanggan menengah & besar (di atas 41,5 kVA s.d. 30 MVA); ***Mencil*** = pelanggan kecil — antara lain dipakai untuk penertiban sambungan liar (P-IV) di kawasan Muara Angke.

Font & tipografi: template logbook memakai default Word (Aptos, isi tabel 9 pt) dan tidak wajib diubah. Kalau user minta disamakan kaidah pedoman: font **Arial**; Pedoman 2020 mengizinkan huruf isi tabel diperkecil sampai **10 pt** (dari 12 pt); Pedoman 2025 = Arial 12 pt, spasi 1,5, 6 pt sesudah paragraf, margin 2,54 cm semua sisi. (Shortcut Word spasi 1,5 = Ctrl+5 — sering ditanya user.)

### 6. Hal yang belum pasti = `[ISI: ...]`, jangan dikarang
Kalimat yang bisa dibuat mengalir dan belum terdengar janggal boleh dirumuskan langsung (mis. pelanggan pusat data), tapi cukup **sekali** sebagai "pelanggan pusat data (data center)" — jangan tambah "PT penyedia layanan ..." karangan.

Nama pelanggan: **tidak wajib** ditulis di logbook — user pernah menolak asumsi sebaliknya ("8 butir 4 masa harus ada nama??"). Cukup jenis pelanggan + daya + kawasan: "kWh meter pelanggan hotel berdaya 53 kVA di kawasan Tubagus Angke". Instansi publik yang sudah disebut user sendiri (Dinas Lingkungan Hidup Jakarta Barat, Bank Mandiri) boleh tetap ditulis. Untuk versi **draf laporan Bab IV** yang dibaca penguji, baru tawarkan inisial/kode pelanggan.

Selalu minta konfirmasi untuk hal di luar dugaan:
- Nama lokasi yang meragukan (pelabuhan perikanan Jakarta ada dua: PPS Nizam Zachman Jakarta/Muara Baru vs PPP/KPL Muara Angke).
- Nama alat: *clamp meter* (mengukur arus) vs **Calmet** (alat uji/registrasi meter) — jangan pakai bergantian.
- Nama tim dengan ejaan tak baku (mis. "Mensar", "Mencil") — tanyakan kepanjangan resminya; kalau tak ada, tulis apa adanya.
- Kode golongan pelanggaran (P-I…P-IV): tuliskan angkanya + artinya sekali, mis. "pelanggaran Golongan IV (P-IV), yaitu pemakaian tenaga listrik oleh bukan pelanggan resmi" — dasar di `references/p2tl-tagihan-susulan.md`.

## Pertanyaan klarifikasi yang layak diajukan sekaligus (satu panggilan clarify)
1. Kode/ kepanjangan aplikasi internal (EPM) dan nama tim (Mensar/Mencil).
2. Pelanggan yang tidak disebut dayanya/di kawasan mana (placeholder).
3. Alat yang dipakai: clamp meter atau Calmet.
4. Nama pelanggan boleh ditulis lengkap atau cukup inisial.

## Checklist sebelum menyerahkan
- [ ] Setiap baris: subjek + kata kerja + objek + keterangan daya/lokasi.
- [ ] Kata kerja cocok dengan peran (helper vs pelaksana).
- [ ] Tidak ada fragmen, typo ("Lingkungn", "kawasa"), atau koma yang dipakai sebagai pengganti "di".
- [ ] Tanggal & jam sesuai; baris izin/sakit dinyatakan sebagai kalimat + alasan.
- [ ] Blok tanda tangan berisi tanggal minggu itu, tidak dobel.
- [ ] Backup .bak.docx ada; verifikasi dengan `read_file` (atau dump python-docx) setelah simpan.
- [ ] Variasi kata kerja: "Mendampingi" tidak mendominasi — maks 1–2 butir per minggu.
- [ ] Panjang tiap butir 1–2 baris.
- [ ] Hanya minggu yang diminta yang berubah (jam ubah file minggu lain tetap lama).
