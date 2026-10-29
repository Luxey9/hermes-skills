# Skema ekspor JSON desain Solar Builder (sumber paritas data)

Ekspor `SolarBuilder-Design.json` = graf desain penuh (bukan render). Ini sumber otoritatif untuk paritas data & UI — lebih kaya dari SVG. User mengirim file ini sebagai lampiran; path di `AppData/Local/hermes/attachments/`.

## Bentuk top-level

```json
{ "version": 1, "components": [...], "wires": [...], "idCounter": 91,
  "simSettings": { ... } }
```

- `components[]`: `{ id, type, x, y, props }` — posisi + semua parameter komponen.
- `wires[]`: `{ id, fromCompId, fromTermId, toCompId, toTermId, props }`.
- `wire.props`: `{ lengthFt, maxDropPct, awgOverride, routing:'bezier', bendX?, bendY? }`.
- `idCounter`: nomor id berikutnya (`id_<n>`) untuk impor/ekspor.

## Nama tipe komponen (snake_case)

`solar_panel`, `charge_controller`, `battery`, `inverter`, `y_connector`, `fuse`, `ac_load`, `grid_input`, `transfer_switch`

## Nama TERMINAL per jenis (otoritatif — dipakai di wire.fromTermId/toTermId)

| Jenis | Terminal |
|---|---|
| solar_panel | `pv_pos`, `pv_neg` |
| charge_controller | `pv_pos`, `pv_neg`, `bat_pos`, `bat_neg` (4) |
| battery | `bat_pos`, `bat_neg` |
| inverter | `dc_pos`, `dc_neg`, `ac_line`, `ac_neu` (4) |
| ac_load | `ac_line`, `ac_neu` |
| grid_input | `l1`, `neu` |
| transfer_switch | `s1_l1`, `s1_n`, `s2_l1`, `s2_n`, `out_l1`, `out_n` (6) |
| y_connector | `in1`, `in2`, `out` |
| fuse | `in`, `out` |

Penting: **Solar Builder memakai bus +/− eksplisit** — setiap komponen DC punya dua terminal, dan arus balik (−) benar-benar digambar sebagai kabel. Ini alasan utama UI kita (single-rail, 1 pasang port) terlihat beda. Warna kabel ≠ jenis komponen.

## Field props penting per jenis (indikasi fitur engine mereka)

- **solar_panel**: `watts, voc, vmp, isc, imp, tempCoeff (-0.38), maxSysVolts, brand, model`.
- **charge_controller**: `controllerType:'MPPT', maxPvVoc, nominalPvWatts, battVolts, maxChargeAmps, maxLoadAmps, efficiency, absorbTimeHours, lvdVolts, lvrVolts`.
- **battery**: `batteryType:'Lithium'|'AGM', volts, ah, maxChargeAmps, maxDischargeAmps, brand, model`.
- **inverter**: `invType:'Pure Sine', phases, inputVolts, outputVolts, frequency, contWatts, peakWatts, efficiency, idleWatts`.
- **ac_load**: `phases, volts, frequency, watts, powerFactor, startWatts, startSeconds, dutyCycle, cyclePeriod, hoursPerDay, alwaysOn, startHour, switchedOff` (kulkas = duty-cycle + startHour).
- **grid_input**: `gridStandard, volts, frequency, amps, gridUp, outageEnabled, outageStart, outageEnd, costPerKwh` → fitur simulasi pemadangan + biaya.
- **transfer_switch**: `position:'Source 1'|'Source 2', poles` → sumber grid vs inverter (hibrida/on-grid).
- **fuse**: `fuseType:'Circuit Breaker', amps, volts, blown`.
- **y_connector**: `amps, volts`.

## simSettings (perilaku simulasi mereka)

```json
{ "sunriseHour": 5.5, "sunsetHour": 18.5, "cloudCover": 0,
  "peakSunHours": 4, "tempLowC": -10, "tempHighC": 25, "tempUnit": "C",
  "initialSOC": 0.8, "hudVisible": false, "hudOpacity": 0.9 }
```

Temp rendah + `tempCoeff` = mereka menghitung Voc saat dingin (cek limit input MPPT).

## Cara memakai file ini

1. Muat dengan json; bangun peta `{id: component}`; petakan `wires` ke pasangan terminal nyata (bukan `:a`/`:b` buatan).
2. Untuk importer ke plts-simulator, petakan tipe snake_case → `UiNodeKind`, terminal → port id, dan `lengthFt` → meter (×0.3048).
3. Untuk mereplikasi desain (bukan impor), susun preset dengan urutan kiri→kanan: panel → y_connector → fuse → charge_controller → baterai → fuse → inverter → transfer_switch → beban; grid_input → transfer_switch (jalur grid).
