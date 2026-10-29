#!/bin/bash
# Pull one chunk of a YouTube live stream's audio, transcribe locally,
# append timestamped lines to $TMPDIR/transkrip.txt
#
# Usage:  VIDEO_ID=<id> bash live_pull.sh [seconds]
#
# Requires: yt-dlp (uv tool install yt-dlp), ffmpeg, faster-whisper

set -u

DUR="${1:-75}"
VID="${VIDEO_ID:-e02S12yiHB4}"
URL="https://www.youtube.com/live/$VID"

cd "$TMPDIR" || exit 1
export PATH="$HOME/.local/bin:$PATH"

OUT="seg_$(date +%H%M%S).mp4"

yt-dlp -f "worst[acodec!=none]/bestaudio" --no-part --downloader ffmpeg \
  --downloader-args "ffmpeg_i:-t $DUR" -o "$OUT" "$URL" >/dev/null 2>&1

if [ ! -s "$OUT" ]; then
  echo "GAGAL_TARIK: stream ended, or yt-dlp/ffmpeg missing"
  exit 1
fi

ffmpeg -y -i "$OUT" -vn -ac 1 -ar 16000 -c:a pcm_s16le cur.wav >/dev/null 2>&1

python - "$OUT" <<'PY' >> transkrip.txt
import sys
from faster_whisper import WhisperModel

model = WhisperModel('small', device='cpu', compute_type='int8')
segments, _ = model.transcribe('cur.wav', language='id', vad_filter=True)
tag = sys.argv[1]
for s in segments:
    print(f'[{tag} {s.start:6.1f}] {s.text.strip()}')
PY

echo "OK $OUT $(stat -c%s "$OUT") bytes"
rm -f "$OUT"
