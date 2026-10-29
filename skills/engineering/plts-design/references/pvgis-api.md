# PVGIS API — Yield Surya per Lokasi

## Endpoint (host BENAR: `jrc`, bukan `jdc` — jdc.ec.europa.eu itu NXDOMAIN)

```
GET https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat=-6.2&lon=106.8&peakpower=1&loss=14&outputformat=json&angle=10&aspect=0&pvtechno=crystSi
```

- `peakpower=1` → hasil per kWp; kalikan (Wp sistem / 1000) untuk produksi aktual.
- Parse `E_m` bulanan (12 nilai, kWh/kWp/bulan) + `E_y` tahunan; validasi: Σ bulanan ≈ E_y (selisih <0.01).
- Acuan Jakarta (loss 14%, angle 10°): **±1448 kWh/kWp/tahun**. Sudut tilt Indonesia ≈ 10° (lintang rendah).

## Jebakan

- **CORS: PVGIS menolak fetch langsung dari browser** — panggil dari Node/server/proxy; di UI selalu sediakan fallback input PSH manual (default 4.5) bila fetch gagal/timeout (set timeout ±15 detik).
- Bila endpoint versi berubah (v5_2 → dst), tes curl dulu sebelum menyalahkan kode; status HTTP 200 + JSON `tot` adalah tanda hidup.

## Implementasi referensi

Repo `plts-simulator`: `src/lib/pvgis.ts` (wrapper + parser) dan `tests/pvgis.test.ts` (fetch nyata Jakarta, assert 12 bulan).
