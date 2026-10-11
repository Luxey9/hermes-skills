---
name: tim-riset
description: "Bentuk tim peneliti riset: topik sampai submit jurnal."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [research, jurnal, publikasi, multi-agent, kanban, delegation, referensi]
    category: research
    related_skills: [arxiv, grounded-citations, laporan-magang, docx, pdf, image-ocr]
    requires_toolsets: [terminal, files, web]
---

# Tim Riset — pipeline naskah sampai submit jurnal

Tim peneliti virtual berisi 8 peran. Tiap peran = satu subagent (delegate_task) atau satu profil Hermes (kanban swarm). Peran, prompt, dan kriteria lulus ada di `references/roles.md` — muat sebelum menjalankan peran apa pun.

## Kapan dipakai (When to Use)

- "bentuk tim riset", "cari topik skripsi/jurnal", "tulis artikel jurnal", "revisi paper"
- Riset topik/proposal lomba inovasi (mis. kompetisi EBT kampus/PLN): jalankan fase scout + librarian saja, tanpa pipeline naskah penuh
- Naskah harus lolos review jurnal (nasional/Sinta atau internasional)

## Fase scout topik lomba/proposal (mode ringan)

Dipakai saat user minta rekomendasi topik lomba atau proposal yang harus dipilotkan dalam hitungan bulan. Scout + librarian saja; tanpa pipeline naskah. Playbook rinci (kueri pencarian, skeleton dokumen keluaran, anchor framing nasional) ada di `references/lomba-inovasi.md`.

1. Baca poster/petunjuk lomba DULU -> ruang lingkup, tenggat, format luaran, kriteria penilaian. Kalau `vision_analyze` balas tidak bisa melihat gambar, pakai skill `image-ocr`; jangan bilang ke user file-nya tidak didukung.
2. Petakan konteks nasional 1-2 tahun terakhir (program pemerintah, RUPTL, siaran pers ESDM/IESR/BUMN) sebagai bahan framing proposal.
3. Cek lebih dulu apakah tiap kandidat sudah ada pilot/proyek nyatanya, lalu baca repositori kampus penulis untuk karya mahasiswa sebelumnya.
4. Novelty wajib berupa pertanyaan riset terukur, bukan produk. Cari konflik fisik/teknis yang literatur 1-2 tahun terakhir baru sekadar *mencatat*, belum diselesaikan untuk konteks Indonesia.
5. Situs pilot wajib dalam jangkauan kerja penulis - itu yang membuat proposal bisa dieksekusi di dalam rentang tanggal lomba dan datanya bisa diambil.
6. Keluaran berupa SATU file markdown di folder proyek (bukan tempelan chat): 3 kandidat utama + cadangan, tiap kandidat dengan judul opsi, masalah masyarakat berangka + sumber, novelty, literatur kunci ber-DOI, kelayakan pilot, lalu matriks pemilihan dan langkah berikutnya.

**Pitfall - cek pilot lembaga pembangunan sebelum mengusulkan.** Topik berbentuk "alat/instalasi X bertenaga surya untuk komunitas Y" sering sudah berjalan sebagai proyek GIZ, UNDP, IPNLF, IESR, atau BUMN: sudah diresmikan, ada factsheet, bahkan sudah terbit panduan manufakturnya. Kandidat macam itu gugur total di depan juri praktisi karena dinilai replikasi, bukan inovasi. Satu putaran kueri pengecekan di awal menghemat seluruh penulisan proposal - jalankan SEBELUM menyusun dokumen rekomendasi, bukan sesudah.

## Struktur tim

| # | Peran | Keluaran |
|---|---|---|
| 1 | Pencari Topik (scout) | 5-10 kandidat topik + argumen kebaruan + kelayakan data |
| 2 | Pencari Referensi (librarian) | `bibliography.bib` + annotated bibliography, semua DOI terverifikasi |
| 3 | Auditor Metodologi | lolos/tidak desain riset, instrumen, statistik, etika |
| 4 | Analis Data | skrip reproducible + gambar/tabel siap jurnal |
| 5 | Penulis (writer) | draf per bagian, IMRaD, satu bagian per pass |
| 6 | Reviewer | review adversarial + vonis (accept/major/minor/reject) |
| 7 | Editor/Penerbit | format template, cover letter, checklist submit, disclosure |
| 8 | Manajer Proyek (PM) | log keputusan, gate, jadwal — dipegang agen utama |

## Alur + gate

```
S0 topik --G1--> S1 referensi --G2--> S2 metode --G3--> S3 data/analisis --G4-->
S4 draf --G5--> S5 review internal --G6--> S6 revisi --G7--> S7 submit
```

Gate = gerbang yang tidak boleh dilewati. Gagal gate -> kembali ke tahap sebelumnya, bukan lanjut.

- **G1** topik lulus: kebaruan jelas (bukan pengulangan), data/instrumen bisa diakses, sesuai bidang penulis
- **G2** minimal 20 referensi, >=80% primer, >=60% terbit <=5 tahun, semua DOI benar-benar resolvable
- **G3** auditor menyatakan lolos (atau daftar perbaikan sudah dikerjakan)
- **G4** angka di draf bisa direproduksi dari skrip di `03-data/scripts/`
- **G5** reviewer vonis minor revision atau lebih baik
- **G6** semua komentar reviewer dijawab di `response-letter.md`
- **G7** checklist jurnal terisi lengkap + similarity/plagiarisme di bawah ambang jurnal

## Struktur folder proyek

```
Riset/<slug>/
  00-topik/kandidat.md, decision.md
  01-referensi/bibliography.bib, annotated.md, catatan-baca/
  02-metode/protokol.md, instrumen.md, analisis-plan.md
  03-data/raw/, processed/, scripts/, output/
  04-draf/00-abstract.md, 01-pendahuluan.md, ...
  05-review/review-round1.md, response-letter.md
  06-submit/manuscript.docx, cover-letter.docx, checklist.md
  07-log/logbook.md, keputusan.md
```

Scaffold: `bash scripts/new-project.sh <slug> "<judul kerja>"` (jalankan dari skill dir).

## Cara menjalankan peran

**Ringan (default)** — agen utama sebagai PM, peran dijalankan paralel lewat `delegate_task`:

```
delegate_task(tasks=[
  {goal: "Peran: Pencari Referensi. <tugas>", context: "<prompt peran dari references/roles.md> + path proyek + bahasa keluaran"},
  {goal: "Peran: Auditor Metodologi. <tugas>", context: "..."},
])
```

Aturan delegasi:

- Tiap anak tahu nol soal percakapan induk -> tempel prompt peran lengkap + path absolut + bahasa (Indonesia) di `context`.
- Reviewer **wajib** anak berbeda dari penulis. Auditor wajib anak berbeda dari pencari referensi.
- Anak tidak boleh menulis ke file yang sama; satu peran satu file.
- Utamakan anak menulis ke disk dan mengembalikan ringkasan + path, bukan menempel naskah penuh di jawaban.
- **Tulis batas fase bukti di `context` sejak awal**: "maksimum N query/unduhan; begitu cukup, langsung tulis file keluaran". Subagent cenderung menambah probe tanpa henti dan tidak pernah menulis artefak final — sebutkan file keluaran + jumlah query maksimum sebagai syarat berhenti. **Batas yang sama berlaku untuk fase audit/verifikasi**, bukan hanya pengumpulan data: anak reviewer/auditor bisa menghabiskan lebih dari satu jam memverifikasi ulang angka yang sudah benar. Tulis "maksimum N blok terminal untuk verifikasi, lalu WAJIB tulis file".
- **`steer` itu pengalih halus, bukan penghenti**: setiran dibaca di tool-result berikutnya, jadi skrip/proses yang sudah diluncurkan tetap selesai. Untuk mengalihkan anak yang menghabiskan waktu di fase eksplorasi, steer tepat sasaran dan cukup ("STOP probing, tulis <file> sekarang" — berhasil mengakhiri fase eksplorasi). Untuk pekerjaan yang harus berhenti seketika atau hidup lebih lama dari proses induk, pakai `cronjob` atau proses `hermes` terpisah dengan timeout.
- Minta anak menulis file bantu (spec/scratch) ke folder proyeknya, bukan ke direktori scratch bersama — dua anak paralel bentrok dan `write_file` menolak menimpa file milik anak lain. Induk yang mau menimpa file buatan skrip/anak lain wajib `read_file` dulu, baru tulis.
- **Kunci angka yang sah di `context` penulis.** Tempelkan daftar angka final (tabel hasil + rentangnya) dan daftar key bib yang boleh dipakai langsung di prompt penulis, plus larangan eksplisit "jangan tambah angka baru". Tanpa itu penulis mengarang angka atau memakai key di luar bib. Verifikasi setelahnya dengan `python scripts/check_draft.py`.
- **Kontribusi vs studi pendahulu harus dibedakan eksplisit.** Klaim celah "0 judul" sering artefak kata kunci sempit; begitu studi pendahulu ditemukan, geser kontribusi ke sudut yang belum dikerjakan (bukan mengulang interkomparasi) dan suruh penulis menyatakannya di diskusi.

Baca `references/data-publik.md` untuk peta endpoint data publik yang sudah diverifikasi (mana 200, mana 403) sebelum menyuruh anak mengunduh.

**Berat/durable (multi-profil + kanban)** — tiap peran jadi profil Hermes dengan model sendiri:

```bash
hermes profile create riset-scout --clone --description "Pencari topik riset: gap, kebaruan, kelayakan data"
# ... satu profil per peran (riset-ref, riset-auditor, riset-analis, riset-writer, riset-reviewer, riset-editor)
hermes kanban init
hermes kanban swarm "<tujuan riset>" \
  --worker riset-scout:"Cari topik" \
  --worker riset-ref:"Kumpulkan referensi" \
  --worker riset-analis:"Analisis data" \
  --verifier riset-reviewer --synthesizer riset-writer
```

Kanban butuh gateway jalan: `hermes gateway install` (Windows: Scheduled Task). Board = `hermes kanban boards create riset`.

## Pencarian referensi (tanpa skill tambahan)

Semua lewat `terminal`/`execute_code`. Wajib verifikasi DOI sebelum masuk bib. Endpoint yang sudah terbukti jalan/blokir ada di `references/data-publik.md`. Verifikasi massal: `bash scripts/verify_doi.sh 01-referensi/bibliography.bib` (exit 1 bila ada DOI gagal resolve).

**Field sitasi jurnal: baca tag meta, jangan reka dari snippet.** Halaman artikel (OJS Indonesia, Elsevier, Springer, MDPI) memuat `citation_*` Highwire — ambil persis dari sana lewat browser dan `js`:

```python
js("""(() => { const m = {};
  document.querySelectorAll('meta[name]').forEach(e =>
    m[e.getAttribute('name').toLowerCase()] = e.getAttribute('content'));
  return JSON.stringify({t: m['citation_title'], j: m['citation_journal_title'],
    a: m['citation_author'], d: m['citation_date'], v: m['citation_volume'],
    i: m['citation_issue'], doi: m['citation_doi'],
    p: m['citation_firstpage'], l: m['citation_lastpage']}); })()""")
```

Jangan menyusun nama jurnal/volume/DOI dari deskripsi hasil search — snippet mengacak ketiganya. Register URL halaman artikel (atau halaman DOI) ke ledger sitasi, bukan URL PDF unduhan.

**Kalau `web_search`/`web_extract` yang error — itu backend, bukan situs target.** Pesan `403 ... api.firecrawl.dev` / "Keyless Firecrawl" berarti URL target belum pernah dicoba; backend berganti tiap panggilan, jadi ulangi query yang sama dan jangan mengulang `web_extract` pada URL yang sama berulang-ulang, jangan langsung pindah ke arsip. Halaman berlogin (Google Docs/Forms/Drive, SSO): sekali coba lalu serahkan link ke user — tak ada jalur anonim.

```bash
# Crossref — cari + metadata + BibTeX
curl -s "https://api.crossref.org/works?query.bibliographic=smart+meter+loss+detection&rows=20&filter=from-pub-date:2020-01-01"
curl -s -LH "Accept: application/x-bibtex" "https://api.crossref.org/works/10.1109/TPWRD.2020.1234567/transform/application/x-bibtex"

# OpenAlex — cari + sitasi + akses terbuka
curl -s "https://api.openalex.org/works?search=tagihan+susulan+p2tl&per-page=25&filter=from_publication_date:2020-01-01"

# Semantic Scholar — abstrak + sitasi
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=kwh+meter+accuracy&limit=20&fields=title,year,authors,venue,externalIds,abstract"

# arXiv — preprints
curl -s "http://export.arxiv.org/api/query?search_query=all:power+quality+harmonics&max_results=20"
```

Aturan rujukan yang dipakai user: utamakan terbitan <=5 tahun terakhir; regulasi/standar (IEEE, IEC, SPLN, Permen ESDM) boleh lebih tua; jangan cantumkan data privat/rahasia instansi (mis. nominal tagihan susulan pelanggan) di naskah.

## Mode: jurnal SINTA vs skripsi

| | Jurnal (SINTA) | Skripsi |
|---|---|---|
| Unit keluaran | 1 artikel, IMRaD 6000-8000 kata | Bab I-V + daftar pustaka |
| Reviewer | anak subagent adversarial + vonis | dosen pembimbing (manusia) + mock review internal |
| Format | template jurnal target | pedoman kampus (lihat skill `laporan-magang` untuk ITPLN) |
| Gate khas | scope jurnal, plagiarism check, cover letter | cetak, lampiran wajib, sidang |

**Satu tim, dua mode.** Jangan bikin tim kedua untuk skripsi.

## Preset: Skripsi + Jurnal SINTA (1 proyek, 1 alur)

Topik dicari yang LOLOS dua-duanya sekaligus, bukan dua riset terpisah.

- **S0** cari topik yang layak skripsi **dan** bisa dipotong jadi 1 artikel jurnal
- **S1-S3** referensi, metode, analisis (satu set, dipakai bersama)
- **S4** dua artefak dari sumber yang sama: naskah jurnal (padat) + naskah skripsi (panjang)
- **S5** reviewer internal -> temuan dipakai untuk revisi keduanya
- **S7a** submit jurnal target **S7b** sidang skripsi

Aturan wajib: angka, tabel, gambar, dan referensi **identik** di kedua naskah. Kalau salah satu naskah mengubah angka, revisi yang lain juga.

## Target jurnal SINTA

- Peringkat SINTA: nilai akreditasi 85-100 = Sinta 1, 70-<85 = Sinta 2, 60-<70 = Sinta 3, 50-<60 = Sinta 4, 40-<50 = Sinta 5, 30-<40 = Sinta 6 (instrumen berbasis Permenkemdikbud 9/2018 + Perdirjen Risbang 19/2018).
- Regulasi terbaru: Permen Diktisaintek No. 9 Tahun 2026 tentang Akreditasi Jurnal Ilmiah -> status hanya terakreditasi (peringkat 1-4) atau tidak terakreditasi, masa berlaku 5 tahun. **Cek status akreditasi terkini di sinta.kemdiktisaintek.go.id/journals sebelum submit** (laman sering 403 ke curl — pakai browser).
- Realistis untuk penulis pertama kali: **Sinta 2 atau 3**. Sinta 1 umumnya sudah terindeks Scopus (tuntutan bahasa Inggris).
- Kriteria wajib jurnal (Pasal 4): EISSN + DOI, mitra bestari lintas institusi, terbit terjadwal, dewan penyunting sesuai bidang.
- Saat memilih jurnal, wajib dicatat: ISSN/EISSN, peringkat + masa berlaku, scope, template, batas panjang, biaya APC, lama review, dan akreditasi terakhir.

## Data publik (wajib untuk mode ini)

Data privat instansi DILARANG masuk naskah. Pakai sumber publik, verifikasi URL sebelum dipakai:

- Kelistrikan Indonesia: statistik PLN, gatrik.esdm.go.id, statistik.esdm.go.id, BPS (bps.go.id)
- Global: Ember (ember-energy.org), IRENA, IEA, ENTSO-E, PUDL (catalyst.coop/pudl)
- Geospasial/irradiansi (API tanpa kunci, terbukti jalan untuk Indonesia): NASA POWER `power.larc.nasa.gov/api/temporal/{hourly,daily}/point`, Global Solar Atlas `api.globalsolaratlas.info/data/lta?loc=<lat>,<lon>`, PVGIS `re.jrc.ec.europa.eu/api/v5_2/PVcalc?...&raddatabase=PVGIS-ERA5`, Open-Meteo `archive-api.open-meteo.com/v1/archive` (MJ/m2, ×0,2778 -> kWh/m2)
- Repositori dataset/paper: OpenAlex, Kaggle, UCI ML Repository, Zenodo, Mendeley Data

**Pitfall data satelit Indonesia (jangan buang waktu mengulang):** PVGIS hanya menerima database **ERA5** di Indonesia — SARAH2/SARAH3/CMSAF/NSRDB balas HTTP 400 'out of the spatial coverage'. Ground truth BMKG Data Online butuh registrasi+reCAPTCHA, WIS2 403, BSRN tak punya stasiun Indonesia, GAW Kototabang hanya jendela bergulir ~20 hari (parameter start/end diabaikan). Konsekuensinya: klaim validasi **nasional** tidak mungkin dari data publik — desain harus direvisi jadi validasi antar-produk satelit atau studi kasus tunggal yang jujur menyatakan keterbatasan. Cek kelayakan data SEBELUM menulis protokol.

Kalau data privat sebenarnya dibutuhkan, ganti variabelnya jadi skenario/agregat publik, atau bikin pernyataan keterbatasan (limitations) — jangan tempel angka privat.

## Konversi ke berkas submit

Naskah ditulis `.md` dulu (versi kerja + diff mudah). Untuk submit, konversi ke template jurnal. Pandoc TIDAK terpasang di mesin user — pasang lewat `winget install --id JohnMacFarlane.Pandoc`, atau pakai skill `docx` (python-docx) kalau harus mengikuti template Word dua kolom. Jangan kirim `.md` mentah ke editor jurnal.

## Jebakan yang wajib diperiksa auditor (semua topik, bukan hanya energi)

Ditemukan lewat audit nyata — tiap poin pernah lolos ke catatan proyek dan hampir masuk naskah:

1. **Periode tidak sejajar.** Jangan pernah membandingkan satu tahun data terhadap rata-rata jangka panjang (LTA). Cek noise antar-tahun produk itu sendiri dulu — kalau selisih antar-produk lebih kecil dari variasi tahunan internal, tidak ada temuan. Kunci jendela waktu seragam untuk semua produk dan tulis `year_min/year_max` di setiap tabel.
2. **Independensi sumber palsu.** Dua API berbeda sering berbagi basis data yang sama (mis. PVGIS-ERA5 dan Open-Meteo dua-duanya turunan ERA5; r jam-an 0,96-0,98). Hitung korelasi antar-sumber sebelum mengklaim "N sumber independen"; kelompokkan jadi klaster dan deklarasikan.
3. **Konfigurasi tidak dinormalisasi.** Bandingkan besaran yang sama: `GHI` horizontal vs `GHI` horizontal, jangan `E_y` tilt-optimum vs `E_y` slope 0°. Tilt/azimuth/loss/horizon wajib dikunci sama sebelum atribusi selisih.
4. **Persentase tanpa penyebut.** Setiap persen wajib berformat `PBIAS (penyebut = X)`. Kolom generik "selisih %" dilarang.
5. **Kapasitas/parameter sistem salah kutip.** Verifikasi ulang angka identitas (mis. 12x330 Wp + 24x120 Wp = 6,84 kWp, bukan "7 kW"). Bias kecil pada parameter ground truth bisa lebih besar dari sinyal yang diteliti.
6. **Cek keberadaan studi pesaing lebih keras.** Klaim "celah = 0 judul" sering artefak kata kunci sempit. Cari padanan istilah (inter-comparison, database comparison, resource assessment) dan cek DOI-nya, bukan hanya judul. Untuk lomba/naskah kampus, cek juga repositori institusi penulis (mis. `repository.itpln.ac.id`) — juri/reviewer internal sering menilai kebaruan terhadap karya kampus sendiri, dan alat dasar yang pernah dibuat mahasiswa lain harus diakui lalu digeser novelty-nya (deployment, model kelola, dampak terukur), bukan dipretensi belum ada.
7. **Satuan akumulasi antar-API tidak seragam.** Medan "iradiansi" yang sama dikembalikan dalam besaran berbeda: NASA POWER daily = kWh/m2 **per hari**, NASA POWER hourly = W/m2 **rata-rata per jam**, PVGIS MRcalc = kWh/m2 **per bulan**, Global Solar Atlas = **rata-rata tahunan**. Tulis tabel satuan + cara agregasi tiap sumber SEBELUM menulis skrip analisis; salah satunya menghasilkan bias palsu ratusan persen (mis. "PVGIS -94% vs NASA") yang lolos ke tabel karena angkanya tidak mustahil secara ajaib. Pasang `assert` sanitasi: GHI tahunan tropis wajar ~1400-2200 kWh/m2/th.

## Skrip analisis (3 tahap, wajib dipisah)

1. `03-data/scripts/fetch.py` — unduh + tulis `index.csv` (nama file, status, tanggal akses UTC). Lewati file yang sudah ada dan berukuran wajar, supaya ulang jalan tidak menghabiskan kuota API.
2. `03-data/scripts/analyze.py` — stdlib + numpy saja; hasil ke `03-data/processed/*.csv` dan tabel ke `output/hasil.md`. Prototipe nilai dulu (1 kota) sebelum batch 7 kota agar kesalahan satuan ketahuan lebih awal.
3. `03-data/scripts/analyze_figs.py` — gambar 300 dpi. Pakai `uv run --with matplotlib python analyze_figs.py` supaya tidak mengubah venv user (pandas/matplotlib/openpyxl tidak terpasang di mesin user dan tidak perlu dipasang).

Pemeriksa naskah sebelum dikirim ke reviewer: `python scripts/check_draft.py [folder]` (default `04-draf`) — mencetak jumlah kata per bagian, key `\cite{}` yang tidak ada di `bibliography.bib`, dan kalimat >30 kata; exit 1 bila ada key asing.

Kalau model tidak bisa melihat gambar, jangan mengklaim isinya: verifikasi PNG lewat header + ukuran piksel (`struct.unpack('>II', data[16:24])`) dan sebutkan bahwa verifikasi visual belum dilakukan.

## Lapor ke user

Setiap selesai satu tahap: tahap, artefak + path, gate lulus/tidak, langkah berikut, keputusan yang butuh user. Jangan tempel ulang isi naskah.
