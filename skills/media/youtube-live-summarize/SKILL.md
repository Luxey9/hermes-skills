---
name: youtube-live-summarize
description: "Use when a YouTube live stream needs a summary."
version: 1.0.0
author: ratman4080, Izza
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [YouTube, Live, Transcript, Whisper, Webinar]
    related_skills: [youtube-content]
---

# YouTube Live Summarize

## When to use

User shares a `youtube.com/live/<id>` link and wants a summary, quotes, notes, or a
running report from an **ongoing or recent livestream** — typically a webinar they
must write a report about, often same-day.

Try `youtube-content` first for normal videos. Use this skill when the stream is live,
or when caption extraction returns `Transcripts are disabled for this video`.

## The core problem

Live streams frequently have **no captions at all**:

```
ERROR: <id> has no automatic captions
[info] Available subtitles: live_chat json
```

There is no transcript to fetch. You must pull the **audio** and transcribe it
yourself. Do not give up and ask the user for the content — that is the whole point
of this skill.

## Setup (once per machine)

```bash
uv tool install yt-dlp                 # not on PATH afterwards; call by full path
$HOME/.local/bin/yt-dlp --version
pip list | grep -i faster-whisper      # usually already in the Hermes runtime
```

Also required: `ffmpeg` on PATH (`which ffmpeg`).

## Pipeline

Live DVR audio only exists in a rolling window, so you cannot cleanly download "the
whole stream" while it runs. Pull **overlapping chunks** and transcribe as you go.

### Step 1 — pull + transcribe one chunk

```bash
cd "$TMPDIR"
bash SKILL_DIR/scripts/live_pull.sh 75      # seconds of audio per chunk
```

Set `VIDEO_ID` to override the default video. Each run appends lines like
`[seg_103020.mp4   12.5] spoken text` to `$TMPDIR/transkrip.txt`. Segment names are
timestamped, so chunks are distinguishable.

### Step 2 — loop

Re-run every 75-90 seconds while reporting progress. Append, never overwrite.
Three to five chunks usually cover one speaker's segment.

### Step 3 — read only the tail

```bash
tail -28 "$TMPDIR/transkrip.txt"
```

Chunks overlap; reading the whole file each cycle produces duplicates.

### Step 4 — synthesize

Quotes must be **verbatim** from the transcript. Never invent plausible-sounding
quotes — the user hands this document to an authority.

## Reporting cadence

When the user asks to be updated every 30s/1 minute, actually report each cycle:

```
**LAPORAN BERKALA #N** — HH:MM

**Insight Narasumber X:**
- point (quote if strong)
- point

Lanjut tarik.
```

Number, timestamp, and end every report with what you are doing next. Incremental
reports beat one dump at the end — the user is often on a deadline and needs to start
writing before the stream finishes.

## Pitfalls

- **Browser tool times out on YouTube live.** Do not use `browser_exec` to scrape a
  stream; it burns 420s and returns nothing. Use curl/yt-dlp.
- **yt-dlp not on PATH after `uv tool install`.** Call `$HOME/.local/bin/yt-dlp` or
  export PATH inside the script.
- **`--write-live-chat` does not exist.** Use `--skip-download --write-subs
  --sub-langs "live_chat"`. Chat is a weak substitute for speech but reveals audience
  questions and topic hints.
- **Live chat is noisy.** Dedupe; most messages are a single number or emoji. Scan for
  the host's own messages and question clusters.
- **Transcription runs near real-time on CPU.** Do not set a terminal timeout under
  ~400s for a 90s chunk.
- **Whisper mangles proper nouns** (Indonesian names especially: a speaker becomes
  "Sonya", "Kaliya", "Kasornia" across chunks). If the user supplies a poster or
  screenshot with correct names, trust the image over the transcript.
- **Coverage gaps.** Chunks missed while busy leave holes. Webinar hosts usually
  re-summarize the material in Q&A — mine that recap to fill gaps.
- **Overall duration is unknown while live.** Do not promise a complete transcript;
  promise a running one.

## Output deliverable

For a report obligation (KIP Kuliah, campus assignment), produce a `.docx` with
`python-docx` matching the required template exactly. Put Name + NIM in the section
**footer** so identity repeats on every page.

See `references/report-docx-pattern.md` for the section structure that satisfied a
KIP Kuliah webinar report.
