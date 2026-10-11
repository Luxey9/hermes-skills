---
name: pemilihan-jurnal-target
description: "Pick target journal: APC, SINTA, scope candidates."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [jurnal, sinta, apc, publikasi, cekjurnal, riset]
    category: research
    related_skills: [tim-riset, blocked-page-recovery, grounded-citations]
    requires_toolsets: [terminal, web]
---

# Pemilihan jurnal target (APC, SINTA, scope)

Dipakai saat perlu daftar jurnal kandidat untuk submit — terutama yang **gratis
tanpa APC** — dan saat harus memverifikasi klaim biaya/akreditasi sebelum
masuk checklist submit. Pelengkap skill `tim-riset` (alur riset end-to-end).

## When to Use

- User minta daftar/cari jurnal tempat submit naskah ("sumber mana yang gratis",
  "jurnal apa yang tanpa biaya", "cari jurnal SINTA")
- Perlu memverifikasi APC, akreditasi, atau kecocokan scope sebelum submit
- Membandingkan beberapa jurnal kandidat untuk satu naskah

## Aturan inti

1. **Direktori jurnal = API, bukan HTML.** Halaman daftar di cekjurnal.id
dirender klien-side; `curl` ke HTML-nya memberi data parsial. Ambil dari
endpoint API-nya. Selengkapnya + daftar parameter: `references/cekjurnal-jurnal-gratis.md`.
2. **Klaim APC pihak ketiga bukan bukti.** Konfirmasi di situs penerbit
sendiri sebelum dimasukkan ke checklist submit; kalau pernyataannya tidak
ketemu, tulis "belum terkonfirmasi", jangan "gratis".
3. **Filter bidang pakai `scope`, bukan substring pendek.** `daya` cocok palsu
ke "Sumber Daya Manusia"; `kendali` ke "kendali mutu". Pakai frasa domain
(`energi terbarukan`, `sistem tenaga`, `tenaga listrik`, `elektronika daya`,
`konversi energi`, `manajemen energi`) lalu baca `scope` kandidat.
4. **Paginasi lalu hitung.** `per_page` di-cap 100 — tarik semua halaman dan
cocokkan jumlah terkumpul dengan field `total` sebelum melaporkan hasil.

## Verifikasi cepat klaim gratis

```bash
curl -sL -A "Mozilla/5.0" "<link jurnal penerbit>" | tr -s ' \n' ' ' \
  | grep -oiE ".{80}(no charge|free of charge|tidak dipungut|gratis|article processing charge|biaya publikasi).{80}"
```

Frasa pengonfirmasi yang lazim: "no Article Processing Charge", "tanpa biaya
publikasi", "tidak dipungut biaya apapun atau free article processing charge".

## Kalau browser tidak tersedia

Backend browser lokal bisa gagal dengan pesan "Chromium browser is missing"
(perbaikannya: `npx agent-browser install --with-deps`). Untuk situs direktori
seperti ini tidak perlu memperbaikinya — pivot ke API lebih murah dan stabil.
Sisakan browser hanya untuk laman yang benar-benar SPA dan tidak punya API
(mis. sinta.kemdiktisaintek.go.id yang 403 ke curl).

## Yang dicatat per kandidat

Nama, penerbit, peringkat + masa berlaku akreditasi, EISSN/PISSN, scope
(cocok dengan naskah), template & batas panjang, APC + sumber konfirmasinya,
lama review, dan status fast track. Masukkan ke tabel perbandingan; jangan
lampirkan seluruh hasil API ke jawaban.
