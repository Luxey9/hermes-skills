#!/usr/bin/env bash
# Scaffold folder proyek riset. Pakai: bash new-project.sh <slug> "<judul>" [base_dir]
set -euo pipefail
slug="${1:?slug wajib}"
judul="${2:?judul wajib}"
base="${3:-$HOME/Documents/Riset}"
dir="$base/$slug"
[ -e "$dir" ] && { echo "sudah ada: $dir"; exit 1; }
mkdir -p "$dir"/{00-topik,01-referensi/catatan-baca,02-metode,03-data/{raw,processed,scripts,output},04-draf,05-review,06-submit,07-log}
printf '# %s\n\nTahap aktif: S0. Dibuat %s.\n' "$judul" "$(date +%F)" > "$dir/README.md"
printf '# Logbook\n\n| tanggal | peran | aktivitas | keluaran |\n|---|---|---|---|\n' > "$dir/07-log/logbook.md"
printf '# Keputusan\n\n| tanggal | keputusan | alasan |\n|---|---|---|\n' > "$dir/07-log/keputusan.md"
echo "$dir"
