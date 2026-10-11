#!/usr/bin/env bash
# Verifikasi massal DOI untuk gate G2. Pakai: bash verify_doi.sh bibliography.bib
# Cetak "DOI <status>" per entri; exit 1 kalau ada yang gagal (bisa dipakai di CI/self-check).
set -uo pipefail
bib="${1:?path bib wajib}"
fail=0; n=0
while read -r doi; do
  n=$((n+1))
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 25 "https://api.crossref.org/works/$doi")
  if [ "$code" = "200" ]; then
    printf 'OK    %s\n' "$doi"
  else
    printf 'GAGAL(%s) %s\n' "$code" "$doi"; fail=$((fail+1))
  fi
  sleep 0.4
done < <(grep -oE 'doi[[:space:]]*=[[:space:]]*\{[^}]+' "$bib" | sed 's/.*{//' | tr -d '\r' | sort -u)
echo "--"
echo "total=$n gagal=$fail"
[ "$fail" -eq 0 ]
