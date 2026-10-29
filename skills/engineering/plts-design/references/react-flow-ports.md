# Port & handle React Flow di `BaseNode` (repo plts-simulator)

Semua keluhan "tidak bisa connect" di repo ini berasal dari salah satu dari dua keluarga masalah: **tipe handle** atau **geometri handle**. Cek tipe dulu (murah, dari source), baru geometri.

## 1. Aturan tipe handle — sebab paling sering

Kutipan dari `node_modules/@xyflow/system/dist/esm/index.js` (`isValidHandle`) & `connectingSelector` di `node_modules/@xyflow/react/dist/esm/index.js`:

```js
// Loose : node/handle sumber != tujuan
// Strict: (isTarget && handleType === 'source') || (!isTarget && handleType === 'target')
```

- **Strict** (default React Flow): satu sisi WAJIB `source`, sisi lain WAJIB `target`.
- **Loose**: cukup sumber != tujuan.

Konsekuensinya: **port yang hanya punya satu tipe handle itu buntu di Strict.** Badge "tidak bisa ditarik" untuk baterai (dua kutub di sisi atas → dua-duanya `target`) maupun panel (dua kutub di sisi kanan → dua-duanya `source`) itu gejala yang sama, dan **bukan** soal polaritas: `+` ke `-` dan `+` ke `+` dua-duanya gagal.

**Aturan repo**: tiap port merender DUA `<Handle>` pada posisi identik — `id` sama, `type` beda.

- Ini pola yang dipakai `DefaultNode` bawaan React Flow (`Handle` target, label, `Handle` source).
- Urutan render: `target` dulu, `source` terakhir. Yang terakhir menang hit-testing, jadi drag selalu dimulai dari `source` dan berakhir di `target` → sah di Strict MAUPUN Loose, sehingga sambungan tidak lagi bergantung pada prop `connectionMode`.
- Label port cukup dipasang di SATU handle; posisinya identik, dua label = teks kelihatan dobel.
- `id` sama untuk dua tipe berbeda itu sah: React Flow menyimpan `handleBounds.source` dan `handleBounds.target` sebagai array terpisah, dan `data-id` internalnya memuat tipe.
- Saat beberapa handle bertumpuk, `getClosestHandle` memilih tipe BERLAWANAN dari handle asal — jadi pasangan bertumpuk justru ditangani dengan benar.

## 2. Geometri handle — empat jebakan yang semuanya bikin port tak terpegang

Dari `node_modules/@xyflow/react/dist/style.css`:

```css
.react-flow__handle               { position: absolute; pointer-events: none; }
.react-flow__handle.connectionindicator { pointer-events: all; }
.react-flow__handle-right { right: 0; transform: translate(50%, -50%); }
.react-flow__handle-top   { top: 0;   transform: translate(-50%, -50%); }
```

1. **Handle dipusatkan TEPAT di tepi kartu** (translate 50%) → separuh badannya di luar kartu. Kalau elemen kartu memakai `overflow: hidden`, separuh itu terpotong dan sisa area klik tinggal seiris. **Jangan pasang `overflow: hidden` di elemen kartu.** Sudut bulat tetap aman: biarkan header membulatkan sudut atasnya sendiri (`border-radius` di header) dan pastikan badan kartu lain tidak punya background. Cek dulu badan kartu sebelum menghapus overflow — kalau ada anak berbackground yang menyentuh sudut, dia akan menonjol.
2. **`position: absolute` butuh containing block ber-position.** Kalau kartu `position: static` sementara pembungkusnya (`position: relative`) menyimpan isi tambahan DI ATAS kartu (label tipe), handle sisi ATAS mendarat di area label, ~15px di atas kartu. Sisi kanan/kiri tampak benar hanya karena kartu adalah anak terlebar (tepi pembungkus ≈ tepi kartu) — **jangan simpulkan dari satu sisi saja**. **Kartu wajib `position: relative`.**
3. **`pointer-events` digerbangi kelas `connectionindicator`**, dan `elementFromPoint` melewati elemen `pointer-events: none`. Handle tanpa kelas itu tidak akan pernah terdeteksi kursor.
4. **Handle sisi atas separuh ada DI DALAM kartu**, tepat di bawah header yang punya background → tanpa `z-index`, header menangkap kliknya. Beri `z-index` pada handle (di atas isi kartu).

Tambahan:

- Jarak antar port di sisi yang sama harus >= lebar titik handle + area kliknya, kalau tidak kutub atas menutupi kutub bawah. Simpan sebagai satu konstanta (mis. `ADJ_PX`) yang dipakai bersama oleh logika offset DAN diuji terhadap angka di CSS.
- Perbesar area klik tanpa membesarkan titik visualnya: `.pnode__handle::before { content: ''; position: absolute; inset: -4px; border-radius: 50%; }`. Pseudo-element tetap mentargetkan elemen handle-nya, jadi hit-test tetap mengenainya.
- Emit offset bertanda `calc(50% - 10px)`, bukan `calc(50% + -10px)`.
- Handle sisi atas menyembul ke area label tipe → label WAJIB `pointer-events: none`.

## 3. Verifikasi tanpa driver browser

Urut dari bukti terkuat:

1. **Ground truth library terpasang.** Baca `node_modules/@xyflow/system/dist/esm/index.js` (`isValidHandle`, `getClosestHandle`) dan `style.css`. Versi-exact, lebih kuat daripada dokumentasi atau ingatan. Kutip barisnya di laporan.
2. **Harness SSR.** `renderToString(createElement(ReactFlowProvider, null, createElement(BaseNode, props)))`.
   - Dua syarat mutlak: provider ada (tanpa itu `Handle` melempar error #001 dan tidak merender apa pun) DAN prop `kind` eksplisit dikirim (tanpa itu `PORTS[kind]` kosong → nol handle).
   - Cetak markup-nya dulu. Kalau nol handle, periksa dua syarat di atas — **jangan** menyimpulkan SSR men-suppress `Handle`; kesimpulan itu pernah ditulis di skill ini dan salah, dan bikin alat verifikasi termurah ikut dibuang.
   - Yang berguna ditegaskan dari markup: jumlah handle per port, `type` tiap handle, `data-port`, dan offset inline (`style="top:calc(50% - 10px)"`).
3. **Tes invariant atas aset sumber** (`tests/canvas-ports.test.ts`): baca blok CSS dari `src/index.css` (buang `/* */` dulu — teks komentar ikut kena regex dan bikin assertion palsu) lalu tegaskan: kartu tidak `overflow: hidden`, kartu ber-`position`, handle punya `z-index`, area klik (`::before`) ada, `ADJ_PX` >= area klik handle, tiap kutub offset-nya berbeda tepat `ADJ_PX`, dan **setiap port punya handle `source` DAN `target` sejumlah port**. Kunci perilaku library yang jadi alasan fix juga (mis. `translate(50%)` pada handle kanan) supaya upgrade dependency memunculkan tes merah, bukan bug halus.
4. `npx tsc -b` + `npx vitest run` + `npm run build`. Bukti prop/API terpasang, bukan bukti perilaku.

Katakan klaimnya sesuai bukti: "drag tidak bisa direplay di sini; yang terverifikasi = markup handle, aturan validasi library, dan invariant yang dikunci" — plus 3-4 langkah cek manual untuk user (termasuk **hard refresh**, karena perubahan CSS/JS sering masih ke-cache dan user akan menguji bundle lama).
