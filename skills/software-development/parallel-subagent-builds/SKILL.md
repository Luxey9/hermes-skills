---
name: parallel-subagent-builds
description: Use when parallel subagents build code in one shared repo.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subagents, delegation, parallel, git, testing]
    related_skills: [claude-code, codex, requesting-code-review]
---

# Parallel Subagent Builds (Shared Repo)

## When to use
- Orkestrasi multi-subagent yang mengubah SATU repo yang sama — fitur paralel, wave build, atau recovery agent mati.

## Alur

1. **Scaffold dulu sebagai parent** (struktur folder, package.json, tsconfig, entry files) sebelum spawn — agent butuh kanvas yang sudah berdiri.
2. **Max 3–4 subagent concurrent per gelombang.** Lebih dari itu memicu rate limit provider; children mati di tengah tugas dengan error HTTP dan partial state-nya menggantung di working tree.
3. **Brief tiap agent wajib membawa:** path repo + SHA HEAD saat ini, daftar file yang DIA pun (own), stack + "JANGAN npm install / JANGAN push remote", dan protokol konflik paralel:
   - Utamakan FILE BARU untuk fitur sendiri; patch file shared dengan read-merge kondisi terbaru (file bisa berubah setelah dia baca pertama).
   - `git add` HANYA file miliknya; commit terpisah; lapor SHA + output test nyata (bukan karangan).
4. **Kontrak interface dikunci di brief paling awal** — siapa yang menulis file types/interface, bentuk stub mana yang boleh ditulis (tandai STUB). Agent engine dan UI bisa membangun paralel di atas stub yang disepakati.
5. Minta tiap agent menjalankan **test scoped** (file test miliknya) hijau. Suite penuh adalah tanggung jawab parent di akhir.

## Recovery saat satu agent mati di tengah wave

- **Cek `git status` + `npm test` DULU sebelum respawn** — agent mati menitipkan WIP uncommitted di disk; test merah pasca-mati itu expected, bukan kerusakan.
- Jangan replay brief asli. Spawn SATU finisher dengan konteks: daftar file WIP persis, bug yang sudah teridentifikasi (sebut baris/simbolnya), kontrak yang sudah dikunci sibling yang landed, dan target "perbaiki, lengkapi, FULL suite hijau, commit semua sisa".
- **Steer sibling yang masih hidup begitu ada yang mati:** jangan sentuh/revert WIP si mati, commit hanya file sendiri, verifikasi test scoped sendiri saja — parent yang beresin tree setelah semua landing.
- Agent yang gagal dengan "response truncated berulang" biasanya karena brief menuntut terlalu banyak file besar dalam satu tugas — pecah tugasnya; suruh commit bertahap supaya hasil parsial selamat.

## Verifikasi parent setelah semua landed

`git log` review SHA → full `npm test` → `tsc -b` + build → dev server background + health check → baru lapor ke user. Jangan pernah lapor sukses dari self-report agent saja.

## Jebakan

- **Commit snapshot silang:** agent paralel yang menyentuh file saling-import bisa membawa WIP sibling ke commit-nya. Wajibkan `git add <file eksplisit>` per agent; kalau snapshot nyelonong masuk commit bersama, pastikan test di HEAD hijau — jangan rewrite history.
- Rate limit adalah soal antrean, bukan kegagalan final: 429 → tunggu wave yang hidup selesai, baru respawn yang mati (2 sekaligus, bukan 5).
- Agent mati meninggalkan test merah BUKAN alasan revert: WIP-nya biasanya 80% jadi — finisher lebih murah daripada ulang dari nol.
