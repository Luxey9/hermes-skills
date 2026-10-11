# Peta sumber data publik — kelistrikan & energi terbarukan

Status diuji dari host Windows (curl/git-bash). Cek ulang kalau gagal — status HTTP bisa berubah.

## API & unduhan yang jalan (200)

| Sumber | Endpoint | Isi |
|---|---|---|
| NASA POWER | `https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=<lon>&latitude=<lat>&start=YYYYMMDD&end=YYYYMMDD&format=JSON` | iradiansi & cuaca jam-an, tanpa kunci. **Satuan daily = kWh/m2/hari; hourly = W/m2 rata-rata/jam.** Nilai hilang ditandai <= -900, wajib difilter. |
| PVGIS MRcalc | `https://re.jrc.ec.europa.eu/api/v5_2/MRcalc?lat=<lat>&lon=<lon>&horirrad=1&outputformat=json` | GHI horizontal **per bulan** (`H(h)_m`), 192 record untuk 2005-2020; `startyear/endyear` diabaikan diam-diam. Lebih tepat dari PVcalc untuk perbandingan GHI (PVcalc = simulasi PV, konfigurasi tilt). |
| Global Solar Atlas | `https://api.globalsolaratlas.info/data/lta?loc=<lat>,<lon>` | GHI/PVOUT tahunan (LTA, Solargis) **dan** rata-rata bulanan di `monthly.data` |
| GATRIK ESDM | `gatrik.esdm.go.id` — Statistik Ketenagalistrikan (PDF/JSON per tahun) | produksi, kapasitas, pelanggan, susut, bauran per sistem |
| Statistik ESDM | `statistik.esdm.go.id` | handbook energi & ketenagalistrikan |
| OWID/Ember | `https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv` | seri produksi listrik per sumber, per negara |
| Crossref | `https://api.crossref.org/works?query.bibliographic=<kw>&rows=20&filter=from-pub-date:2021-01-01` | metadata + total hit; `/works/<DOI>` untuk verifikasi DOI (200 = asli, 404 = palsu) |
| OpenAlex | `https://api.openalex.org/works?search=<kw>&per-page=25` | metadata, sitasi, akses terbuka |
| arXiv | `http://export.arxiv.org/api/query?search_query=all:<kw>&max_results=20` | preprint |
| UCI ML Repo | `archive.ics.uci.edu` (mis. `ElectricityLoadDiagrams20112014`) | kurva beban rumah tangga |
| Open-Meteo Archive | `https://archive-api.open-meteo.com/v1/archive?latitude=<lat>&longitude=<lon>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&daily=shortwave_radiation_sum&timezone=Asia%2FJakarta` | GHI harian, satuan **MJ/m2** (x0,2778 -> kWh/m2). Basis ERA5 -> bukan sumber independen dari PVGIS. |
| Kaggle dataset API | `https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>` | unduh dataset TANPA auth (mis. produksi PLTS atap Bandung `educatelabs/power-output-photovoltaic`) |
| GAW Bukit Kototabang | `https://gawbkt.id/api/radiasi-matahari-data` | radiasi aktual jam-an (10 parameter). Wajib header `X-Requested-With: XMLHttpRequest` + `Referer: https://gawbkt.id/data/radiasi-matahari`; tanpa itu 403. Hanya jendela bergulir ~20 hari; `start`/`end` diabaikan. |
| SINTA (via browser) | `sinta.kemdiktisaintek.go.id/journals/profile/<id>` | blok Current Accreditation + History Accreditation per jurnal |

## Terblokir / tidak stabil

- **403 ke curl**: `web.pln.co.id`, `ember-energy.org`, `iea.org`, `irena.org`, `bps.go.id`, laman `sinta.kemdiktisaintek.go.id`. Pakai `browser_exec` atau `web_search`/`web_extract`; **jangan ganti angkanya dengan perkiraan** — tandai `TIDAK DITEMUKAN`.
- **429 (rate limit)**: Semantic Scholar tanpa API key — pakai Crossref + OpenAlex dulu; S2 hanya untuk pelengkap abstrak.
- **503/429 sesekali**: OpenAlex — ulangi setelah jeda; jangan simpulkan "OpenAlex mati".
- **Cloudflare bot-wall**: sebagian situs OJS jurnal (mis. JASIEK) — halaman biaya/author-guidelines tidak bisa di-scrape.
- **NXDOMAIN**: sebagian jurnal resmi instansi sudah mati (mis. KET ESDM) — konfirmasi URL penerbitan aktif sebelum dijadikan target submit.

## Aturan pemakaian

1. Verifikasi URL/DOI sebelum angkanya masuk naskah. DOI gagal resolve = buang sitasinya.
2. Data privat instansi (nominal tagihan, data pelanggan) tidak boleh masuk naskah, walau sudah dipegang penulis.
3. Simpan respons mentah ke `00-topik/evidence/` atau `03-data/raw/` supaya klaim bisa dilacak ulang.
4. Catat perintah pencarian yang dipakai di `07-log/logbook.md`.
