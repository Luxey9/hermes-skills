# Validating lesson code against the C runner

Scope: C lessons (`c-level-*`) in the E-Learning app. Python lessons run in
Pyodide locally and do not have this class of problem.

## 1. What the runner chain is

C runs **in-browser**: `src/hooks/useCodeRunner.ts` posts to the clang WASM worker
(`cWorker`) built from `public/clang-worker.js` + `public/shared.js` +
`public/sysroot.tar` — **clang 8.0.1 against wasi-libc**, not glibc. `sysroot.tar`
is the whole toolchain-capability surface. Judge0/Wandbox helpers still sit in that
file (`runCWithJudge0`, `runCWithWandbox`, `runCWithFallback`) but `runCode` does
**not** call them for C any more — they are dead paths. There is no Windows, no
`/usr/include`, and no glibc compat layer anywhere in the real chain.

**The sysroot, not a glibc compiler, decides what compiles.** Probe it directly,
no browser needed:

```python
import tarfile
t = tarfile.open(r"<repo>/public/sysroot.tar")
d = t.extractfile("lib/wasm32-wasi/libc.a").read()
print(d.count(b"\x00gets\x00"))   # 0 = no implementation -> link error
```

Wandbox (`gcc-head-c`) and Judge0 are **glibc/Linux and still ship `gets` as a
compat symbol** — `gcc-13.2.0-c` runs it fine with only a warning. Never use
them as evidence that a lesson will run in the app; they are useful only for
syntax and logic checks of things the sysroot does have.

## 2. Probe script shape

Use `write_file` for the script (see the heredoc pitfall in SKILL.md). Build C
newlines as a literal, so the compiled source really contains `\n`:

```ts
const NL = String.fromCharCode(92) + 'n';        // literal backslash-n
const P  = (s: string) => s.replace(/\{NL\}/g, NL);

async function runWandbox(label: string, code: string, stdin?: string) {
  const r = await fetch('https://wandbox.org/api/compile.json', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ compiler: 'gcc-head', code, stdin: stdin || '' }),
  });
  const d: any = await r.json();
  const err = (d.compiler_error || d.program_error || '').trim();
  console.log(`### ${label}  status=${d.status}`, JSON.stringify((d.program_output||'').slice(0,160)));
  if (err) console.log('  err:', JSON.stringify(err.slice(0,240)));
}
```

`npx tsx scratch/<name>.mts 2>&1 | grep -v dotenv`.

- **Wrap `fetch` in try/catch.** A silent exit with zero output means the request
  threw (see §5); without the catch the lesson just looks "untested".
- **Always include a known-good control** (`printf("halo\n")`, `sqrt`/`pow`) in
  the batch. Without it you cannot tell "this code is bad" from "the whole probe
  path is bad", and a mangled newline makes *every* sample fail identically.
- **Batch the lessons in one script and print a per-lesson status line**, so one
  run covers every code lesson of a level instead of one call per lesson.
- Reads-only. Do not submit user/lesson ids anywhere; these are public compilers.

## 3. Verified break / pass table (module-listed symbols on this toolchain)

| Construct | Verdict | Evidence / replacement |
|---|---|---|
| `gets(buf)` | **fails — cannot work, no workaround** | app sysroot `libc.a` has **0** `gets` symbol and `include/stdio.h` says so outright: `char *gets(char *) __attribute__((__deprecated__("gets is not defined on WASI")))`, declared only under `#if __STDC_VERSION__ < 201112L`. Module lists `scanf("%[^\n]", var)` + `getchar()`; use those (and note the module's own tip: `getchar()` must swallow the newline before a second read). |
| `#include <conio.h>`, `getch`, `getche` | **fails** | no `conio.h` in the sysroot, 0× symbols. Windows/DOS only — the module documents them, so flag for the user's decision rather than deleting silently. |
| `#include <windows.h>` + `Sleep(1000)` | **fails** | `fatal error: 'windows.h' file not found`, and `Sleep` is 0× in the sysroot. The module documents `<windows.h>` only for `system("cls" / "echo …" / "color …")` — but `system` is **also 0×**, so there is no faithful replacement. Reporting it honestly beats shipping a swap that fails at the link step. |
| `strlen`, `strcpy`, `strcmp` | **pass** | all three module-listed under `<string.h>`. |
| `strcat` | **pass technically, out of scope** | 1× in the sysroot, but 0× in the module → rule 2 says trim, not keep. |
| `sqrt(144.0)`, `pow(3.0,3.0)` | **pass** | module-listed under `<math.h>`; prints `12.00` / `27.00` with `%.2f`. |
| `atoi`, `abs` | **pass technically, out of scope** | module's `<stdlib.h>` bucket documents no such functions → swap the `code_example` to `sqrt`/`pow`. |
| ternary `a if c else b` (Python) | n/a | 0× in the module → remove from the lesson; not a runtime question. |

## 4. Offline capability probing (no browser)

```python
import tarfile
t = tarfile.open(r"<repo>/public/sysroot.tar")
d = t.extractfile("lib/wasm32-wasi/libc.a").read()
print(d.count(b"\x00gets\x00"))   # 0 = no implementation -> link error
```

Or compile/link for real by loading `public/shared.js` in Node and calling
`new API({readBuffer, compileStreaming, hostWrite})` → `api.compile` → `api.link`
→ `api.memfs.setStdinStr(stdin)` → `api.run`. That is the closest thing to the
student's Run button and needs no browser.

`api.compileLinkRun(code)` is the one-call shortcut (compile + link + instantiate +
run) and is what the worker itself uses; prefer it for sweeping many lessons.

```js
import fs from 'fs';
const API = new Function(fs.readFileSync('public/shared.js', 'utf8') + '\n; return API;')();
const api = new API({
  async readBuffer(f) { const b = fs.readFileSync('public/' + f); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); },
  async compileStreaming(f) { const b = fs.readFileSync('public/' + f); return WebAssembly.compile(b); },
  hostWrite(_s) {},          // silence it: a looping program can emit ~1 MB
});
await api.ready;
await api.compileLinkRun(code);
process.exit(0);             // MANDATORY — see below
```

- **`process.exit(0)` at the end is not optional.** Without it Node/Bun never exits
even though the WASM program finished, so a timeout is reported for a program that
printed its correct output. Confirm with stdout before calling anything "hanging".
- **One process per lesson, with an OS-level timeout, when sweeping a curriculum.**
  In-process batch runs can wedge on a single bad lesson; a per-job child process
  survives it and keeps the results already written. Append each result to a JSONL as
  it completes (and skip ids already present) so a crash costs nothing.
- Warming cost is real: the first `api.ready` untars `sysroot.tar` and compiles
  clang/lld (~0.7 s and up), each lesson after that ~0.75–1.1 s. A 40-lesson level is
  minutes, not seconds — run it in the background and poll the JSONL, do not block.
- Repeat any case that reports a failure. A job that times out in one round may finish
  in ~1 s in the next; the usual causes are the missing `process.exit`, stdin genuinely
  exhausted mid-run (see `wasm-toolchain-probing.md` §3c), or stdin not being wired in
  at all. Re-run the curriculum after fixing the harness — the flaky first pass
  overstates the failure count.

Verified against the shipped sysroot: `gets` **0×** (header declares it only as
`__deprecated__("gets is not defined on WASI")`); `system` and `Sleep` **0×**;
`sleep`/`usleep` exist BUT the module only documents `Sleep` → drop it.
`fgets`, `getchar`, `scanf`, `printf`, `puts`, `strcpy`, `strlen`, `strcmp`,
`strcat`, `atoi`, `abs`, `sqrt`, `pow` all exist. Wandbox/Judge0 are glibc and
still ship `gets` as a compat symbol (`gcc-13.2.0-c` even runs it with a warning) —
**never use them as evidence a lesson will run in the app.**

## 5. Reading a negative result honestly

- **A local Python `ERROR` on a run without stdin may be the harness, not the
  lesson.** Piping `''` into `execFileSync(stdin: '')` on Windows raises EPIPE
  (`Errno 22`) and the lesson looks broken. Use `spawnSync(..., {input: tc.input ?? ''})`,
  and normalise `\r\n` → `\n` before comparing. Confirm a real deviation by
  reading the lesson's own stdout (it usually matches).
- **Python lessons using `matplotlib` cannot be checked locally** when the
  interpreter has no wheel — the app fetches it at runtime
  (`loadPackagesFromImports` from cdn.jsdelivr.net). Report those as
  CDN-dependent; do not "fix" the lesson. This is also why a local `python` run
  reporting `ModuleNotFoundError: matplotlib` is not evidence of a bug.

- **Judge0 free tier rate-limits hard** — a `status: undefined` response is not a
  verdict. Either space submissions ~10–13 s apart with retries, or fall back to
  Wandbox, which accepts a full batch back-to-back (it did for every sample above).
- **"Everything fails identically" almost always means the probe is broken**, not
  that lessons all fail. Compare against the control in the same batch, and check
  the raw error text: a `missing terminating " character` warning points at the
  script's escaping, not at the C.
- **Do not present an unverified swap as a fix.** A proposed replacement that was
  never compiled is a guess; run it first, and report the observed status/stdout
  in the reply to the user.
- **A Wandbox/Judge0 pass is not an app pass.** Those compilers are glibc; the
  app is wasi-libc. When the question is "does this run for students?", the answer
  comes from `public/sysroot.tar` (symbol present?) and, if a browser is available,
  from the deployed playground. If neither was checked, say so — do not imply the
  swap is verified.
- **Wandbox compiles `.cc` as C++** (`gets` removed since C++14) and needs
  `compiler: 'gcc-head-c'` for C mode. Judge0 free tier rate-limits after a few
  back-to-back submissions; `status: undefined` is not a verdict.
