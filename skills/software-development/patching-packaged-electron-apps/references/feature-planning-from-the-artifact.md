# Feature planning from the artifact: media / lyrics

Class of ask: *"can you add <feature>? what does it take, what are the
requirements?"* before any code. The answer is an inventory of what the shipped
bundle already has, then the shortest path on top of it. The reconnaissance is
read-only — ASAR routes live in `reverse-engineer-anything`; this file is the
architecture map and the sizing rules for the media pipeline specifically.

## Where this app family keeps media

Read the **source repo when the user owns it** (`nyxland-repo/app/src`, then the
`.vite/build` copies inside the asar). Confirm a package is actually wired rather
than listed — `grep -rn "spotify\|<Pkg>" app/src` scored nothing for
`@bitdisaster/exe-icon-extractor` even though the root `package.json` declared
it.

| Layer | File | What is there |
|---|---|---|
| Main | `app/src/main.js` (`psMediaScriptPath`) | writes `get-media.ps1` to userData and `ipcMain.handle("get-system-media")` |
| Main | same, `psControlScriptPath` | `control-media.ps1` + `ipcMain.handle("control-system-media", command, ...args)` |
| Preload | `app/src/preload.js` | `getSystemMedia`, `controlSystemMedia` |
| Renderer | `app/src/Island.jsx` | `const [spotifyTrack,setSpotifyTrack]=useState(null)`, `setInterval(fetchMedia,3000)`, `mediaPosition` ticker (~500 ms), tab id 3 = "Now Playing" |
| Tab table | `Island.jsx` `const TABS = [...]` | `{id:3,name:"Now Playing",icon:(color)=><Music size={16} color={color}/>}` + `DEFAULT_TAB_SHORTCUTS[3]="Alt+M"` |

`get-media.ps1` is the whole data source. Object shape:

```js
{ Title, Artist, Album, Status: "playing"|"paused"|"stopped",
  Source: SourceAppUserModelId, Artwork: "data:image/png;base64,…",
  Position: <seconds>, Duration: <seconds> }
```

It uses WinRT `GlobalSystemMediaTransportControlsSessionManager`.
**`Position` is already interpolated**: when `Status -eq "playing"` it adds
`([DateTimeOffset]::UtcNow - $timeline.LastUpdatedTime).TotalSeconds`, so the
timestamp returned is live, not the stale timeline value. Artwork falls back to
`Get-AppIconBase64 $sourceApp` when the player exposes no thumbnail.

## Why this shape wins for time-synced lyrics

The renderer already advances a local position ticker every ~500 ms and swaps it
out for the server value every 3 s polling cycle. Timed lyrics need exactly that
signal, so the feature is **wiring, not building**: no new tab, no new player, no
new dependency.

Alternatives and why they lose:

- Process-scan forks (`tasklist` / `Get-Process` to find `spotify`/`vlc`) —
  fragile, cannot see browser players, and adds nothing `get-media.ps1` does not
  already return.
- A separate overlay window — a second always-on-top surface fights the island
  for focus and for `setIgnoreMouseEvents`.
- An in-island player (own MP3s, folder scan, ID3, HTML5 audio) — a different
  project: file discovery, tag parsing, an audio engine. Name it as phase two,
  do not fold it into the lyrics answer.

## Sizing rule for an ask like this

Answer **feasibility + the 2–4 blocks + requirements + the single fastest test
path**, not a work breakdown. Rough budget for lyric support in this bundle:
main `~100` lines, preload `~2`, `Island.jsx` `~350–450` — call it 450–550 total.
Name the ICP anchor `lyrics:fetch` explicitly: one new handler means one seam to
verify.

Surface both delivery stages, since they differ in risk: test by swapping the
asar into the installed app (`%LOCALAPPDATA%\Programs\<app>\resources`), release
via the repo + `scripts/pack.mjs`.

## Before promising a lyrics source, test it live

Run a `curl` probe against every provider **in the same session** and report the
result — an uncached API is a claim, a probe is evidence:

```bash
curl -s --max-time 20 -A "<App>/<ver> (github.com/<user>/<repo>)" \
  "https://lrclib.net/api/search?track_name=<t>&artist_name=<a>"
curl -s --max-time 20 "https://music.163.com/api/search/get?s=<query>&type=1&limit=3" \
  -H "Referer: https://music.163.com"
curl -s --max-time 20 "https://music.163.com/api/song/lyric?id=<id>&lv=1&kv=1&tv=-1" \
  -H "Referer: https://music.163.com"   # lrc.lyric = [mm:ss.xxx] timed; tlyric = translation
curl -s --max-time 20 "https://api.lyrics.ovh/v1/<artist>/<title>"   # plain text only
```

Order: LRCLIB → NetEase → lyrics.ovh, re-run the probe when a newer session picks
this up instead of trusting a past note.

## Requirements to state up front

- `SMTC`/GSMTC exposes Spotify, Apple Music, and any browser player. A player that
  does not register a session produces no lyrics — feature absence, not a bug.
- **Normalise the title before querying.** Chart-track names arrive with `feat.`,
  dash-joined `Artist - Title`, and bracketed remaster tags, and providers miss on
  the raw string.
- `Duration` is what buys an exact match on LRCLIB; a session that reports 0 must
  fall back to a duration-less query.
- Fetch once per track, then serve from a local cache under
  `%APPDATA%\<App>\lyrics\` — never bundle lyric text in the repo or the asar.
