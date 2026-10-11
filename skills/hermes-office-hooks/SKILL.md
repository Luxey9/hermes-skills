---
name: hermes-office-hooks
description: Use when wiring Hermes hooks to the Office dashboard.
version: 1.0.0
---

# Hermes Office hooks

Hermes TIDAK punya event `on_error` — daftar valid ada di `hermes_cli/plugins.py` (`VALID_HOOKS`).
Error tool Terdeteksi dari payload `post_tool_call` di `extra`: `status` (error/cancelled/timeout),
`error_type`, `error_message`, atau `result` berisi `{"error": ...}`.

## Pola wrapper penanda error

- `post_tool_call` di `config.yaml` diarahkan ke `scripts/hook-post.sh` (bash + grep, tanpa python).
- Wrapper meneruskan body via `printf | curl --data-binary @-` (curl.exe Windows gagal baca `-d @/tmp/...` path MSYS).
- Kalau error: ganti `hook_event_name` jadi `tool_error` via sed, collector (`server/collector.mjs`) normalize jadi `kind: hermes_error`.
- Command di config WAJIB dikutip karena path ada spasi: `bash "C:/.../hook-post.sh"`.
- `hooks_auto_accept: true` membuat hook baru jalan tanpa prompt; bila command berubah, status jadi `not allowlisted` sampai sesi baru dimulai.
- Verifikasi: `hermes hooks test post_tool_call --payload-file <absolut-win-path>` (path /tmp tidak terbaca hermes windows).
- Normalizer error di `collector.mjs`: case `on_error/tool_error/hook_error/session_error/error` -> `kind: hermes_error`.
- Frontend: `showHermesError()` tampilkan banner `#hoErrbar` + `logActivity` + `triggerIncident`.
