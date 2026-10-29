# Shipping a patched Electron app: rebrand, slim, publish

Everything here runs *after* the feature patches work. The goal is a repo the
user can push to GitHub without leaking a credential, without shipping someone
else's updater, and without a 60 MB asar nobody can download.

---

## 1. Rebrand checklist

The product name is scattered across four different layers. Miss one and the
user sees the old name in a window title, a log path, or a tray tooltip.

| Layer | Where | Effect |
|---|---|---|
| `package.json` | `name`, `productName`, `version`, `author` | `productName` drives `app.getPath("userData")` |
| Main process | `setAppUserModelId`, tray tooltip, tray menu labels, log filename, update-installer filename | taskbar grouping, log path |
| Renderer bundle | `document.title` in `index.html`, error-boundary strings, about/version text | what the user actually sees |
| Legacy cleanup | the `reg delete .../Run` name list for old login items | stale autostart entries |

Procedure:

```python
# count before replacing, always
for a,b in [('p.setAppUserModelId("com.old.vendor")','p.setAppUserModelId("id.new.app")'),
            ('_.setToolTip("Old Name")','_.setToolTip("NewName")'),
            ('"old-name.log"','"newname.log"')]:
    print(mn.count(a), a[:50]); mn = mn.replace(a,b,1)
```

Verify the rename *at runtime*, not by grepping: `document.title`, the newly
created `%APPDATA%\<NewName>\` folder, and a fresh log line are the proof.

### The userData migration trap (dev machine only — never in a distribution build)

`productName` change = **new userData directory** = the app starts with an empty
config and the user's API key / settings appear gone. A legacy-path fallback
solves that on the developer's own machine:

```js
const cfCandidates = [
  path.join(app.getPath("userData"), "ai-config.json"),
  // migrasi dari build lama — HANYA untuk build lokal developer
  path.join(os.homedir(), "AppData", "Roaming", "Old Name", "ai-config.json"),
  path.join(os.homedir(), "AppData", "Roaming", "old-name", "ai-config.json"),
];
```

**Strip that fallback before you ship anything.** A portable/zip build carrying
the legacy candidates silently adopts the *developer's* key on any machine that
ever ran the old app — the user's credential travels inside a file they hand to
friends. The shipped build reads exactly one path:

```js
const cfCandidates = [path.join(app.getPath("userData"), "ai-config.json")];
```

Keep the migration in your working tree, delete it in the release commit, and
prove it with a clean-profile launch (section 8) showing `hasKey: false`.

Report to the user that on *their* machine the key still lives in the *old*
folder until they re-save from the settings UI — otherwise "my key disappeared"
is the next support ticket.

---

## 2. Strip node_modules from the asar (62 MB → 5.6 MB)

The bundle usually carries a full `node_modules` (lucide-react, @babel,
framer-motion, caniuse-lite — thousands of entries) that the **packed build never
requires**. The renderer is already bundled; only the main process's own
`require()` calls matter.

Prove it before deleting:

```python
import re
mn = open(".vite/build/main.js").read()
print(sorted(set(re.findall(r'require\("([^"]+)"\)', mn))))
# -> ['../../src/ai-agent.js','child_process','crypto','electron','events',
#     'fs','http','https','node:path','os']
```

Also scan the `src/` tree the app loads at runtime (via its dynamic
`require(path.join(appPath,"src",name))` helper) — it must resolve to local files
and node builtins only. `require(n)` / `require(e)` with a variable is that
loader; check what names get passed to it.

Stage only what runtime needs, then pack the stage:

```python
keep_dirs  = [".vite", "src"]
keep_files = ["package.json"]
```

Result in practice: `node_modules` 53.6 MB dropped, `src`+`.vite` 5.6 MB kept,
`app.asar` 62 MB → 5.62 MB. Verify by relaunching and checking
`[RENDERER ERROR]` count is 0 and the AI/IPC handlers still register.

---

## 3. Kill the inherited auto-updater

A patched build of someone else's app still points at **their** update manifest.
On the user's machine that means an upstream release silently overwrites every
patch. Find it:

```python
for m in re.finditer(r'manifestUrls\s*[:=]', mn): print(mn[m.start()-80:m.start()+300])
```

Typical payload: two GitHub raw URLs plus a Cloudflare R2 bucket, all belonging
to the original author. Replace with an empty array and guard the check so the
UI does not spin forever:

```js
const Ge = [];
// inside checkForUpdates():
if (!this.manifestUrls.length) return { status: "disabled" };
```

Also strip any hidden first-run promo redirect — these bundles often call
`window.electronAPI.openExternal("<vendor>.com")` from a `setTimeout(...,3000)`
on first launch:

```js
// before
const T=setTimeout(()=>{...openExternal("vendor.example.com")...,localStorage.setItem("newuser","false")},3e3);
// after
const T=setTimeout(()=>{localStorage.setItem("newuser","false")},3e3);
```

Grep for `openExternal`, `openExternal(`, and the original author's domain across
`main.js`, `preload.js`, the renderer bundle **and** the `src/` copies.

---

## 4. API-key containment

Non-negotiable rules (a wrong move here leaks the user's credential into a public
repo or a README screenshot):

1. **The renderer never receives the key.** `getConfig` returns `hasKey: true` and
a mask. A separate `setConfig` IPC accepts `{model, baseUrl, apiKey}` and the main
process persists it.
2. **Mask with dots only.** `"•".repeat(min(32, max(10, len)))` — no `slice(0,4) +
slice(-4)`, which leaks eight real characters into every screenshot.
3. **Never render an absolute user path.** `C:\Users\<realname>\AppData\...` in a
settings footer ends up in the README. Print `%APPDATA%\<App>\ai-config.json`.
4. **Write the config with owner-only permissions**:
```js
fs.writeFileSync(cfgPath, JSON.stringify(cfg,null,2), {encoding:"utf8", mode:0o600});
try { fs.chmodSync(cfgPath, 0o600); } catch {}
```
5. **`.gitignore` carries** `ai-config.json`, `**/ai-config.json`, `.env*`,
`*.key`, `*.pem`, `*.asar`, `*.log`, plus the app's own state files
(`settings.json`, `app-cache.json`, `notifications-store.json`, `workspaces.json`).

---

## 5. Pre-publish audit (run BEFORE `git push`)

Scan the **tracked** file list, not the working tree — that is what actually goes
up:

```bash
git ls-files   # feed this list to the scanner, not `find .`
```

Six pattern groups, each with a reason:

| Group | Patterns | Why |
|---|---|---|
| live key | full key, `key[:8]`, `key[-8:]` | the only unrecoverable leak |
| config files | `ai-config.json` | contains the key verbatim |
| username | real Windows username, `<user>@...` | doxxing in a public repo |
| personal paths | `C:\Users\<realname>`, `C:/Users/<realname>` | same |
| original author | their name, email, GitHub handle, domain | attribution/legal noise, and the updater target |
| tokens | `ghp_`, `sk-`, `xox[baprs]-` | accidental CLI paste |

Read the key from the live config, do not hardcode it:

```python
keys = []
for p in ["%APPDATA%/NewName/ai-config.json", "%APPDATA%/Old Name/ai-config.json"]:
    k = json.load(open(os.path.expandvars(p), encoding="utf-8")).get("apiKey", "")
    if k: keys.append(k)
```

A generic "looks like a secret" regex will drown in false positives from minified
code — `disable-backgrounding-occluded-windows`, `IRandomAccessStreamWithContentType`,
and `GlobalSystemMediaTransportControls` all match `[A-Za-z0-9_-]{32,}`. Report
the count as "kandidat" and rely on the **live-key + username + path** groups for
the pass/fail gate.

Also assert on the local repo that the built artifact is ignored:

```bash
git check-ignore -v out/app.asar   # must print the .gitignore rule
```

---

## 6. Verify the push remotely, not locally

A clean local tree proves nothing about what landed on the server.

```bash
gh api repos/<owner>/<repo>/git/trees/main?recursive=1 --jq '.tree[].path' \
  | grep -iE "ai-config|\.asar|\.env|settings\.json|\.log$" || echo "bersih"
```

Then reconcile counts — a mismatch means something was filtered or failed:

```bash
git ls-tree -r --name-only origin/main | wc -l    # remote
node scripts/verify-nokey.mjs                      # bundle-level audit
```

`gh api repos/<o>/<r> --jq .size` can return `0` for minutes after the first push
(cache lag). Trust the tree listing and blob sizes, not `size`.

---

## 7. Ship a reusable audit script in the repo

Put the audit in the repo itself so CI enforces it on every push, not just this
session:

- `scripts/verify-nokey.mjs` — walks `app/`, scans for forbidden filenames,
the live key + head8/tail8 fragments, and generic long-token patterns; exits 1
when anything is found.
- `scripts/pack.mjs` — stages and packs `app.asar`.
- `.github/workflows/ci.yml` — `node scripts/verify-nokey.mjs` then
`node scripts/pack.mjs` on every push and PR.

**Windows pitfall in `pack.mjs`:** `execFileSync("npx.cmd", …)` throws
`spawnSync npx.cmd EINVAL` on Node 22. Use `execSync` with `shell: true` and
quote the paths yourself:

```js
const q = (s) => `"${String(s).replace(/"/g, '\\"')}"`;
execSync(`npx --yes asar pack ${q(appDir)} ${q(out)}`, { stdio: "inherit", cwd: root, shell: true });
```

---

## 8. Ship something a non-developer can actually run

The GitHub repo is source + scripts; it is **not** installable. Anyone without
Node/Electron cannot use it. Two shippable shapes:

| Shape | Effort | Result |
|---|---|---|
| Portable zip | minutes | extract → click `<App>.exe` → runs, no install |
| NSIS installer | ~1 min of build time from the prebuilt dir | one-click install, Start Menu, uninstaller |

Both wrap the same payload; the installer is just a compressed container. Build
the portable folder first — it is the input to the installer (below).

Do not quote an hour for the installer: it only takes that long when you rebuild
electron from source, which you almost never need.

### Building the portable zip from an installed app

The install directory *is* a complete portable app. Copy it minus the junk:

```python
skip_files = {"app.asar.bak"}                       # 62 MB of dead backup
# keep only the locales the user's audience needs
if rel == "locales" and name.lower() not in ("en-us.pak", "id.pak"): continue
```

Then three edits the copy needs:

1. **Rename the exe** (`Quick Pill.exe` → `NyxLand.exe`). It keeps working — the
   binary finds `resources/` relative to itself.
2. **Delete `resources/app-update.yml`.** electron-builder writes it with the
   original `owner:`/`repo:`/`provider: github`; leaving it in means the shipped
   copy can still poll the upstream release feed even after you emptied
   `manifestUrls` in the bundle. Grep the *unpacked folder* for it, not just the
   asar.
3. **Swap in your slim `app.asar`** — the one in the install dir is the old
   build; copy `out/app.asar` from the repo over `resources/app.asar`.

Also drop the old `Uninstall <OldName>.exe` and its icon: a portable folder with
someone else's uninstaller is confusing and looks untrustworthy.

Add a plain-text `BACA-INI.txt` / `README.txt` covering extract-then-run, the
SmartScreen "More info → Run anyway" step, where user data lives, and how to
fill in the AI credentials. Non-developers will double-click the exe *inside*
the zip and get a broken launch otherwise.

### Building an NSIS installer from the prebuilt app dir

The portable folder is already a valid packaged Electron app, so never rebuild
from source. `--prepackaged` tells electron-builder "this is finished, just wrap
it". Install time: `npm i electron-builder@26` (88 MB, ~30 s) once, then 40 s per
build.

```bash
# 1. stage a copy — electron-builder mutates the exe it is given
cp -r <portable> appdir && rm appdir/README.txt

# 2. rewrite the Win32 version resource FIRST (see 4o in SKILL.md)
node setmeta.js appdir/<App>.exe build/icon.ico

# 3. wrap
electron-builder --win nsis --prepackaged appdir
# -> dist/<App>-Setup-<version>.exe
```

Config that must be present (`electron-builder.yml`):

```yaml
appId: id.<domain>.<app>
productName: <App>
electronVersion: <x.y.z>      # REQUIRED with --prepackaged
win:
  target: [{ target: nsis, arch: [x64] }]
  icon: build/icon.ico
  artifactName: <App>-Setup-${version}.exe
nsis:
  oneClick: false                            # wizard, user picks the folder
  perMachine: false                          # per-user install, no UAC prompt
  allowToChangeInstallationDirectory: true
  createDesktopShortcut: true
  createStartMenuShortcut: true
  deleteAppDataOnUninstall: false            # leave %APPDATA%\<App> alone
```

- **`electronVersion` is mandatory.** Without it the build dies with
  `Cannot compute electron version from installed node modules` — there is no
  `node_modules/electron` to read because you never installed Electron. Take the
  version from the runtime (`LICENSES.chromium.html` / the app's own about box),
  not from npm `latest`.
- **rcedit the staged exe before wrapping, not after.** A copied/renamed exe keeps
  the original author's `ProductName`/`CompanyName`/`FileVersion` in its Win32
  resource; Properties and the installer's own metadata then read "the other app".
  `rcedit` npm package (`node_modules/rcedit/bin/rcedit-x64.exe`) with
  `{"version-string":{CompanyName,FileDescription,ProductName,LegalCopyright,
  OriginalFilename,InternalName},"file-version":"1.0.0.0","product-version":"1.0.0.0",icon}`.
  Re-wrap afterwards — the installer copies the exe at build time. Icon
  artwork itself (flat RGB → transparent alpha, multi-size ICO, the asar copy the
  window icon is read from) lives in
  [app-icon-and-installer-branding.md](app-icon-and-installer-branding.md).
- **No signing certificate, no selection.** electron-builder logs
  `signing with signtool.exe` and does nothing without a cert; SmartScreen still
  says "Unknown Publisher". Say that up front instead of promising a clean run.
- **The installer is smaller than the zip** (~116 MB vs ~159 MB from a 324 MB
  folder): NSIS LZMA beats deflate. Do not promise a big saving either way.

### Verifying the installer (do not ship an uninstalled artifact)

The build succeeding proves nothing — prove install, launch and uninstall:

```bash
# silent install to a throwaway dir; /D must be LAST and unquoted
powershell.exe -NoProfile -Command "$p=Start-Process -FilePath '<abs>\<App>-Setup-1.0.0.exe' -ArgumentList '/S','/D=C:\temp\install-test' -Wait -PassThru; $p.ExitCode"
```

Then assert, in this order: `(Get-Item install-test\<App>.exe).VersionInfo` shows
your `ProductName`/`CompanyName`; the Start Menu `.lnk` and the Desktop `.lnk`
exist; launching the installed exe with `--remote-debugging-port=<p>` yields
`document.title`, `backgroundImage === "none"`, `getConfig().hasKey === false`;
and `Uninstall <App>.exe /S` exits 0 and leaves the folder, the shortcuts and the
`HKCU:\...\Uninstall\*` key gone.

- **Grep the installer for leaks is not an audit.** The asar sits inside LZMA
  compression, so `grep -a` on `Setup.exe` returns 0 for the username, the key
  and the original author even when the asar still carries them. Audit
  `appdir/resources/app.asar` (and the staged folder) instead, then treat the
  installer grep as a check on installer strings only.
- **Keep the build inputs next to the artifact** (`electron-builder.yml`,
  `package.json`, the rcedit script, `icon.ico`, a README with the 3 commands)
  in a durable folder outside the pruned scratch dir, or the next version cannot
  be rebuilt without re-deriving the config.

### Size: what is actually in there

Users ask "why is it so big" — answer with the breakdown, not a shrug:

| Item | Typical | Trimmable? |
|---|---|---|
| `<App>.exe` (Electron runtime) | 210 MB | no |
| `locales/*.pak` (55 files) | 46 MB | yes → keep 2, save 45 MB |
| `app.asar.bak` | 62 MB | yes → delete |
| `audio-helper.exe` / native helpers | 39 MB | no, it is a feature |
| `dxcompiler.dll` + `dxil.dll` + `vk_swiftshader.dll` | 33 MB | **no** — removing them black-screens machines with old/absent GPU drivers |
| `LICENSES.chromium.html` | 15 MB | **no** — BSD notice, legally required |
| your `app.asar` | 5.6 MB | already minimal |

Say plainly that the app code is 5.6 MB and the rest is the framework. Quote the
compressed installer size (~38–45 % of raw) rather than the install size, since
that is what gets downloaded.

### Clean-profile verification (the step that catches key leaks)

Never test a distribution build against your own userData — it already has your
key and your settings, so everything "works" and nothing is proven.

```bash
<App>.exe --remote-debugging-port=9337 --user-data-dir=<scratch>/freshprofile
```

**`--user-data-dir` is often ignored**: these apps call `app.setName()` / ship a
`productName`, and Electron then resolves `userData` from that name, not the
flag. Do not conclude "the profile was clean" from an empty folder — check what
the app actually reports:

```js
window.electronAPI.ai.getConfig().then(c => c.path)   // which file it really reads
```

Assert all three on the fresh launch:

- `getConfig().hasKey === false` (no inherited credential)
- `Island.style.backgroundImage === "none"` (no leftover personal path)
- the feature globals exist (`typeof window.__X_PICK_BG__ === "function"`)

If a stale `file:///C:/Users/<realname>/…` still paints, the interpolation is
emitting `url('none')` and the browser resolves it against the page URL. Guard
the call site instead of the value:

```js
backgroundImage: (v && v !== "none") ? `url('${normalize(v)}')` : "none"
```

Same class of leak: a file-picker fallback that stores the **absolute path** in
`localStorage`. Persist the `file:///` URL (or a `data:` URL), never the raw
`C:\Users\…` string — `localStorage` is plain text in the user profile and gets
screenshotted, backed up and shared.

---

## 9. README screenshot hygiene

Before attaching a UI screenshot to a README:

- open the settings panel that shows the credential field and confirm the value
  renders as dots **only**;
- confirm no `C:\Users\<realname>` string is visible;
- take the shot of the *feature*, not of the error/notification that happened to
  be on screen — a stray WhatsApp toast in a `preview.png` is a wasted round trip.
