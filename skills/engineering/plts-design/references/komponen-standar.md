# Komponen Standar PLTS Pasaran Indonesia

## Tabel keputusan tegangan sistem

| Energi harian | V sistem | Bank baterai (LiFePO4) |
|---|---|---|
| <1 kWh/hari | 12V | 1× 12V 100Ah |
| 1–3 kWh/hari | 24V | 2× 12V 100Ah seri |
| 3–6 kWh/hari | 48V | 4× 12V 100Ah seri (atau paket 48V) |

## Komponen tipikal (kelas 24V, ~2 kWh/hari)

| Komponen | Spek | Catatan |
|---|---|---|
| Panel | 4× 200Wp mono, susun 2S2P | Voc array 79.2V < 100V input MPPT |
| MPPT | Victron SmartSolar 100/50 | EPEver Tracer 6415AN (60A) alternatif murah |
| Baterai | 2× LiFePO4 12V 100Ah seri | 2.56 kWh, efektif ~2.05 kWh (DoD 80%) |
| Inverter | Pure sine 24V, ≥1500VA | Surge ≥ 2.5× beban motor terbesar |
| Breaker | 20A per string panel, 60A sisi baterai | Kabel baterai→inverter ≥ 25mm² |

## Rumus cepat (urutan: beban → baterai → panel → MPPT → inverter)

- `E_total = Σ(W × qty × jam)` atau langsung target Wh/hari; faktor `hari otonomi` masuk di langkah baterai, bukan panel.
- `V_sistem` otomatis: <1.5 kWh/hari → 12V; <3.5 kWh → 24V; selain itu 48V.
- `Ah = E_total × otonomi / (V_sistem × DoD × 0.88)` — DoD: LiFePO4 0.8, AGM 0.5; bulatkan ke atas.
- `Wp = E_total / (PSH × 0.8)` — PSH Indonesia 4.2–5.0 (default 4.5); bulatkan ke ukuran katalog terdekat.
- `A_MPPT = Wp_total / V_sistem × 1.25`; cek `Voc_array = Voc_panel × jumlah_seri` < max input MPPT (warning bila ≥90% limit).
- `VA_inverter = (beban_puncak_bersamaan / 0.8) × 1.25` — beban puncak termasuk surge motor 2–3× (kulkas/kompresor); pure sine wajib.
- Implementasi referensi (tertest): `src/lib/designer.ts` di repo plts-simulator (13+ test, verifikasi 2000Wh→24V, 4000Wh→48V).

## Platform simulasi web

- **Solar Builder** (solarbuilder.net) — drag-drop, 200+ komponen nyata (Victron/Renogy/EcoFlow), breaker trip nyata, ekspor PNG/JSON. Pilihan utama user.
- **PVAlign** (pvalign.com/simulator) — 33+ node, wiring terminal per terminal, preset off-grid/grid-tie.
- **guru.technosains.com/plts/plts_versi_4.html** — kalkulator desain berbahasa Indonesia, output angka siap laporan.
- **PowerSim** (powersim.app) — fokus ROI rumah tangga. **PROSILI** (prosili.com) — mini-grid pre-feasibility, skala riset.
