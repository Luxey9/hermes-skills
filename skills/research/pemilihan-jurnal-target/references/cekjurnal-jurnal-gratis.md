# Direktori jurnal cekjurnal.id — endpoint & filter

Halaman `/jurnal` dan `/jurnal-gratis` dirender klien-side (SPA) dan mengisi
daftarnya dari API JSON. Jangan scrape HTML-nya; panggil API-nya.

## Endpoint

```bash
curl -s "https://cekjurnal.id/api/jurnal.php?action=list&apc=gratis&per_page=100&page=1"
```

Parameter (nama persis):

| param | nilai |
|---|---|
| `action` | `list` |
| `apc` | `gratis` \| `0-500000` \| `500000-1000000` \| `1000000-2000000` \| `2000000-5000000` |
| `sinta` | `1`..`6` |
| `bahasa` | `id` \| `en` |
| `fast_track` | `1` |
| `q` | kata kunci (cocok nama/scope) |
| `sort` | `nama-asc` \| `nama-desc` \| `sinta-asc` \| `sinta-desc` \| `apc-asc` \| `apc-desc` \| `h5-desc` |
| `page`, `per_page` | paginasi; `per_page` di-cap 100 |

Balasan: `{success, total, page, per_page, data:[...]}`.

Field per jurnal: `nama`, `penerbit`, `sinta`, `e_issn`, `p_issn`, `apc`,
`apc_idr`, `bahasa`, `frekuensi`, `frekuensi_jumlah`, `scope`, `scope_en`,
`link`, `h5_index`, `citations`, `fast_track`, `akreditasi_mulai`,
`akreditasi_sampai`, `status`.

Halaman `/jurnal-gratis` (HTML statis) hanya memuat sebagian daftar — bukan
sumber lengkap; pakai untuk daftar cepat, bukan untuk hitungan final.

## Contoh: kandidat bidang energi/kelistrikan gratis

Dari 343 jurnal `apc=gratis`, 61 menyebut istilah energi/elektro di
nama+scope. Yang relevan untuk naskah kelistrikan/transisi energi:

- Sinta 1: Jurnal Elektronika dan Telekomunikasi (BRIN)
- Sinta 2: Ketenagalistrikan dan Energi Terbarukan (Kementerian ESDM);
  Journal of Electrical Engineering and Computer (JEECOM)
- Sinta 3: Electron: Jurnal Ilmiah Teknik Elektro (UBB); Jurnal EECCIS
  (Teknik Elektro UB); JMES (ITS)
- Sinta 4: Electrician (Unila); Journal of Applied Electrical Engineering
  (Polibatam); Journal of Electrical, Electronics and Informatics (Unud);
  TEKTRIKA (Telkom); Jurnal Nasional Pengelolaan Energi MigasZoom (PPSDM
  Migas); Jurnal Rekayasa Energi dan Mekanika (ITENAS); Manutech (Polman
  Babel); Machine (UBB); JMEMME
- Sinta 5: Journal of Energy and Electrical Engineering / JEEE (Unsil);
  Jurnal Rekayasa Elektro Sriwijaya; Eksergi: Jurnal Teknik Energi
  (Polines); BEES; Jurnal Kajian Teknik Elektro (UTA'45)
- Kebijakan/manajemen energi: STI Policy and Management Journal (BRIN),
  International Journal of Industrial Engineering and Engineering
  Management (UAJY)

Status gratis wajib diverifikasi ulang per jurnal lewat resep curl di
SKILL.md — data direktori bisa kedaluwarsa.
