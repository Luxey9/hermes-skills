# hermes-skills

Koleksi skill Hermes Agent milik saya — hasil export dari `HERMES_HOME` lokal (profil `default`).

- `skills/` — 97 skill bawaan/terinstall Hermes (termasuk yang saya buat/kustom).
- `external-skills/` — skill pihak ketiga (`cybersecurity`, `productivity`).

## Cara pakai

Copy folder skill yang diinginkan ke Hermes kamu:

```bash
# contoh: install satu skill
cp -r skills/productivity/laporan-magang "$HERMES_HOME/skills/productivity/"

# contoh: install semua external skill
cp -r external-skills/. "$HERMES_HOME/skills/"
```

Lalu skill otomatis terdeteksi Hermes di sesi berikutnya.

## Catatan

- File `.hub/index-cache/` tidak ikut (cache lokal, diregenerasi otomatis).
- Skill dengan private/personal notes mungkin perlu disesuaikan ulang sebelum dipakai di mesin lain.
- Export terakhir: 11 Okt 2026.
