# Spec visual Solar Builder (target paritas UI/UX plts-simulator)

Distill dari ekspor SVG resmi Solar Builder; acuan saat menyentuh node/edge/warna di plts-simulator. Untuk skema data ekspor JSON (terminal, props, simSettings) lihat `solarbuilder-design-json.md`.

## Kanvas & layout
- Background hampir hitam navy `#0a1520`, flat tanpa grid dots.
- Alur ketat kiri→kanan per tahap: panels → Y connector → breaker/fuse → MPPT → baterai → fuse → inverter → load; branch paralel disusun simetris vertikal.
- Label jenis komponen melayang DI ATAS kartu (teks kecil abu terang), terpisah dari kartu.

## Kartu node: body gradasi gelap, border header kategori
Warna kategori (grad 2-stop hsl, ~12%→19% lightness per hue):

| Komponen | Hue | Nilai di kartu |
|---|---|---|
| Solar Panel | biru 210° | stat **cyan** (`21.1V · 9.51A`, OUTPUT W) |
| MPPT | ungu 270° | header magenta, nilai **cyan** (24V · 50A CHARGE) |
| Battery | hijau 120° | **progress bar SOC hijau** + overlay `80% · 0.96 of 1.20 kWh`; VOLTS/CAPACITY putih |
| Inverter | oranye 25° | header `PURE SINE`, nilai **amber** (CONT W · DC V · AC VAC) |
| Breaker/Fuse | emas 48° | rating **amber** (20A), header `CIRCUIT BREAKER` |
| Y Connector | coklat 33° | `2 → 1 · 30A` (qty in → out · rating) |
| AC Load | magenta 300° | `500W · AC 120V` (ganti 230V utk Indo) |

Radius sudut kecil (~4–6px), border 1px lebih terang dari body; header = strip dengan ikon + judul bold uppercase.

## Kabel & port
- Bézier tebal (~3–4px). **Warna kabel = jenis jalur, bukan tipe node**: merah = jalur daya DC (panel/MPPT/baterai), abu = sekunder, biru = keluaran AC inverter.
- Port: dot bulat kecil (~8–10px) berwarna kontras di titik sambung.
- Signature: baterai menampilkan SOC live via progress bar, bukan angka polos.

### Implementasi aktual di repo (SELESAI, commit `3443ab2`)
- **Kabel = `src/components/edges/CableEdge.tsx` + `cablePath.ts`**, didaftarkan lewat `edgeTypes` + `defaultEdgeOptions={ type:'cable' }` di `Editor.tsx` (edge preset/wizard lama tanpa `type` ikut jadi kabel).
- Ketebalan: **7px saat mengalir / 4px saat diam**, digambar dua lapis — `.cable__sheath` (selubung gelap, +3.5px) lalu inti `.cable`. Sebelumnya cuma `.react-flow__edge-path { stroke:#46586e; stroke-width:2 }`.
- **Panah arus bergerak** via `<animateMotion>` + `<mpath href>` ke satu `<path>` acuan (`id=cable-ref-<edgeId>`), `rotate="auto"` supaya mengikuti lekukan. **Jangan pakai animasi CSS `stroke-dasharray`** untuk ini: dash dihitung sepanjang busur tapi digambar per segmen, jadi pada bézier besar terlihat terpotong di tiap kurva.
- **Warna kabel = `kind` PORT yang dipakai** (`dc+`/`dc-`/`ac-l`/`ac-n`/`ground`/`signal`, dari `COMPONENT_SCHEMAS`), dipetakan di `src/lib/cable.ts` → kelas `cable--dc-pos` dst. Nilai hex-nya **sama persis** dengan dot port (`.pnode__handle--dcp` dsb). Ini penyimpangan yang disengaja dari 3 warna kasar SolarBuilder: skema port repo ini sudah memisahkan + dan −, L dan N, dan konsistensi "kabel menyatu dengan dot" lebih berguna daripada meniru warna kasar.
- Panah hanya dirender saat ada aliran; kabel tanpa arus tetap tampil tipis (itu informasi, bukan kegagalan).

## Model port per komponen (ekstraksi terverifikasi, circle r=5)
SolarBuilder memodelkan terminal polaritas eksplisit — BUKAN 1 titik in/out generik.
Port = pasangan +/- DC dan L/N AC sesuai fisik komponen:

| Komponen | Port (sisi) | Label port |
|---|---|---|
| Solar Panel | 2 keluar (bawah) | PV+ / PV− |
| MPPT | 2 masuk (kiri) + 2 keluar (kanan) | PV+, PV− → BAT+, BAT− |
| Battery | 2 keluar (atas) | + / − |
| Inverter | 2 masuk DC (kiri) + 2 keluar AC (kanan) | DC+, DC− → L, N |
| Fuse / Breaker | 1 masuk (kiri) + 1 keluar (kanan), in-line | IN → OUT |
| Y Connector | 2 masuk + 1 keluar | 2→1, rated per arus (30A) |
| AC Load | 2 masuk (atas) | L / N |

## Anatomi baris live per komponen (label kiri, nilai kanan)
Nilai = hasil simulasi per proses komponen, update saat playback:

- Panel: `OUTPUT <Wp>W` + `MPP <V> · <A>` (MPP = titik kerja saat itu)
- MPPT: `BATT <V>` + `CHARGE <A>`
- Battery: jenis+SOC `AGM 80% · <terpakai> of <nama> kWh` + `VOLTS <V>` + `CAPACITY <Ah>`
- Inverter: header `PURE SINE` + `CONT <W>` + `DC <V>` + `AC <VAC>`
- Fuse/Breaker: `CIRCUIT BREAKER <A>`
- AC Load: `LOAD <W>` + `AC <V>`

Angka pada SVG contoh (21.1V MPP, 0.96/1.20 kWh, AGM) = snapshot kondisi SolarBuilder — yang wajib dikloning adalah STRUKTUR; angka engine sendiri jadi pembanding validasi (wiring sama tapi V/A beda jauh = bug solver).

## Palette & panel ringkasan (hasil harvest live, terverifikasi)
Token dari stylesheet resmi: bg kanvas `#0a1520` + grid titik `#1a2a3a` 24px, panel `#16213e`, item `#0f3460` border `#1a4a80`, hover `#1a4a90`, item aktif hijau `#1a5a20`, aksen judul `#f0c040`, teks dim `#666`, palette lebar 148px (drawer mobile 185px di ≤768px).

Urutan grup palette (jangan diacak): Generation · Control · Storage · Protection · Loads · Distribution · Annotation — 21 item, label persis (`Fuse / Breaker`, `AC Disconnect (2-pole)`, `Y Branch Connector`, `DC Fuse Block`, `Text Note`). Ikon = 20 PNG di `/images/<Name>.png` (curl butuh `-A "Mozilla/5.0"`), Text Note pakai glyph 📝.

Baris ringkasan kanan (12): Total Solar W · Est. Harvest/Day Wh|kWh · Battery Bank kWh · Usable (DoD) kWh · DC Load/Day · AC Load/Day · Total Load/Day · From Battery/Day · Est. Autonomy `N days` · Solar Sufficiency % · Worst VDrop % · Diagram `N comps · M wires`.
Urutan & format string di atas adalah kontrak tampilan — angka koma dua digit untuk kWh, `—` untuk tak ada data, tone ok/warn/err per baris.

## Konversi ke plts-simulator
- **Status (fase 1–4 SELESAI, commit lokal di main)**: sistem port multi-handle + `PORTS`/`ENGINE_PORTS` di `src/components/nodeTypes.ts`, `<Handle id>` dinamis di BaseNode, kartu dengan grid baris spek live, node YBranchNode, preset `solabuilder-replika` di `src/data/presets.ts`. Test: `tests/ports.test.ts` (13 cas).
- **Yang MASIH berakhir beda (fase 5+)**: (a) bus −/kembalian belum digambar — kita single-rail, SolarBuilder dual-rail; (b) kartu masih teks — SolarBuilder memakai ILUSTRASI produk, lihat blok di bawah; (c) belum ada grid_input/transfer_switch (on-grid + outage).
- **(b) kabel sudah SELESAI** (commit `3443ab2`): bezier tebal berwarna per jenis konduktor + panah arus bergerak; bukan lagi abu lurus `#46586e`. Lihat blok "Implementasi aktual di repo" di §Kabel & port.
- Node belum ada di repo saat perlu on-grid: **Grid Input** + **Transfer Switch** (skema terminalnya di `solarbuilder-design-json.md`) — sumber grid, outage, biaya/kWh.

## Aset gambar: akar perbedaan visual (penting)

SolarBuilder menanamkan **23 `<image>` PNG base64 di dalam SVG ekspor** — foto/ilustrasi produk nyata (mis. panel dengan matahari, Victron SmartSolar biru dengan logo + QR + terminal BATTERY/PV). Kartu mereka mendominasi oleh gambar; kartu kita `<div>` teks. Ini beda KELAS, bukan sekadar styling.

Tiga tingkat paritas yang realistis (jangan janjikan 100%):
1. **Kosmetik** (bisa cepat): warna aksen per kategori, kabel bezier berwarna per jalur, port jadi dot kecil, header badge, opsi tema navy-alt `#0d3568` + aksen `#cc2222`/`#f0c040`.
2. **Ilustrasi**: gambar vektor/AI satu per jenis komponen (paling mendekati tanpa lisensi foto).
3. **Aset nyata**: foto produk per brand/model × 102 katalog — ini proyek konten, bukan kode.

Ekstrak gambar dari SVG: `re.findall(r'<image[^>]*href="data:image/png;base64,([A-Za-z0-9+/=]{40,})"', s)` → decode → baca dimensi PNG dari header (`struct.unpack('>II', raw[16:24])`) untuk memilih ukuran; vision_analyze PNG hasil decode.

## Resep ekstraksi SVG (port + label + posisi)
```python
import re
s = open(path, encoding='utf-8', errors='ignore').read()
# label + posisi: <text x=".." y="..">...<tspan>..</tspan></text>
texts = re.findall(r'<text[^>]*x="([\d.]+)"[^>]*y="([\d.]+)"[^>]*>(.*?)</text>', s, re.S)
labels = [re.sub(r'<[^>]+>', '', t[2]).strip() for t in texts]
# port = circle r=5 (semua port r sama); kumpulkan cx/cy
ports = re.findall(r'<circle[^>]*cx="([\d.-]+)"[^>]*cy="([\d.-]+)"[^>]*r="5"', s)
```
Port sisi kiri kartu = masuk (cx negatif relatif), kanan = keluar; pasangkan dengan label terdekat (OUTPUT/BATT/CHARGE/DC/AC/LOAD).