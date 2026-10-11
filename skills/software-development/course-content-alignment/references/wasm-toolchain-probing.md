# Probing a WASM toolchain's capability surface offline

Scope: answering "does compiler X support header Y / function Z" for the C lessons
of the E-Learning app — without a browser, and without trusting a vendored build.

## 1. Which toolchain is live

| where | what | runs for students? |
|---|---|---|
| `public/clang` + `public/lld` + `public/sysroot.tar` (+ `clang-worker.js`, `shared.js`) | clang 8.0.1 / wasi-sdk, target wasm32-wasi | **yes** |
| `scratch/tcc-wasm-repo/` (eliot-akira/tcc-wasm) | Tiny C Compiler 0.9.27, emscripten 2.53.3, target `i386-linux-gnu` | **no** — nothing in `src/` imports it |

Verify liveness before using a compiler as evidence: `grep -rln tcc src/` (empty =
vendored experiment only). When the user names a compiler, answer for that compiler
**and** state which one the app actually runs.

## 2. Header list and symbol presence = the sysroot tar

```bash
tar tf public/sysroot.tar | grep -E "^include/[^/]+\.h$"          # top-level (132)
tar tf public/sysroot.tar | grep -E "^include/sys/[^/]+\.h$"      # (29)
tar tf public/sysroot.tar | grep -E "^lib/clang/[^/]+/include/"    # compiler builtins
```

Symbol presence: read `lib/wasm32-wasi/libc.a` out of the tar and count the
NUL-delimited name (`d.count(b"\x00gets\x00")`); 0 = no implementation, so it
fails at the link step regardless of the header declaring it.

### Enumerate exhaustively, never sample

When the user asks "which headers can I use", test **every** header in the tar, one
compile each. The full sweep takes ~2 minutes and a sampled answer is a wrong
answer: an earlier "92 tested" list missed a real failure (`canvas.h`) and wrongly
claimed `netinet/in.h` / `arpa/inet.h` were absent.

```bash
# 1. build the candidate list from the tar (skip __* internal fragments)
python -c "
import tarfile, json
t=tarfile.open('public/sysroot.tar')
h=set()
for m in t.getmembers():
    x=m.name
    if not x.endswith('.h') or not x.startswith('include/'): continue
    h.add(x[len('include/'):])
h=sorted(a for a in h if not a.split('/')[-1].startswith('__'))
json.dump(h, open('scratch/_hdr_all.json','w'))
print('kandidat:', len(h))"
# 2. one api.compile per header, append each result to a JSONL so a crash keeps progress
```

### Verdict — 113 of 117 compile, 4 fail

Failing, with the real cause read out of the header itself:

| Header | Cause |
|---|---|
| `canvas.h` | contains `#include <string_view>` — a **C++** header; the runner compiles as C |
| `canvas_main.h` | pulls in `canvas.h` |
| `sys/mman.h` | a deliberate `#error`: "WASI lacks a true mmap; … compile with `-D_WASI_EMULATED_MMAN` and link with `-lwasi-emulated-mman`" |
| `wasi/libc-find-relpath.h` | needs the internal `__wasi_libc_find_relpath` API, not for general use |

Everything else in the tar compiles, including `netinet/in.h`, `arpa/inet.h`,
`netpacket/packet.h`, `sys/un.h`, `sys/socket.h`, `wasi/core.h`, `wasi/libc.h`, plus
a full `include/c++/v1/` (libc++). Regenerate the authoritative printed list with the
sweep above whenever the tar changes rather than retyping it here.

### Absent versus failing — do not conflate them

`setjmp.h`, `pthread.h`, `stdatomic.h`, `sys/wait.h`, `sys/statvfs.h` are **absent**
from the tar (only a libc++ `include/c++/v1/setjmp.h` exists, and it does
`#include_next <setjmp.h>` → "file not found"). `conio.h`, `windows.h`,
`graphics.h`, `dos.h`, `io.h`, `process.h` are absent too — Turbo C / Windows
headers, a **platform** limit, so "no flag will make it work" as opposed to "needs a
flag or a bigger sysroot". A symbol counted 0 in `libc.a` is unusable even when the
header lists it — say so instead of swapping in a function that fails at the link step.

## 3. Driving an Emscripten-built compiler from Node

An emcc `-sMODULARIZE -sEXPORT_ES6` build is a default-exported factory:

```js
import tcc from './tcc.js';
function feed(text){ const b = new TextEncoder().encode(text); let i = 0;
  return () => (i < b.length ? b[i++] : null); }        // byte-drip, so EOF lands right
const out = [];
await tcc({ arguments: ['-E','-'], print: s=>out.push(s), printErr: s=>out.push('[err] '+s),
            noExitRuntime: true, stdin: feed('#include <stdio.h>\n') });
```

Only two flags are needed to enumerate a tcc-family binary's configuration:
`-print-search-dirs` (install / include / libraries / crt / elfinterp) and
`-dM -E -` (every predefined macro, e.g. `__TINYC__`, `__STDC_VERSION__`,
`__SIZE_TYPE__`). Then test one header at a time with `-E -` and grep for
`error: include file '<h>' not found`; run the same loop over `-I <dir>` candidates
to see whether a path is usable.

Node's `preRun` hook receives the Module as its argument, so a probe can reach
`Module.FS` when the build exports it.

## 3b. Compile mode: the live runner compiles `.c` as C++

`public/shared.js` sends `-x c++` to clang for the input file — once in `compile()`
(around line 834) and once in `compileToAssembly()` (around line 851). Consequences
that look like compiler bugs but are not:

| code | `-x c++` (as shipped) | `-x c` |
|---|---|---|
| `int *p = malloc(4*sizeof(int));` | **fails** — `cannot initialize a variable of type 'int *' with an rvalue` | compiles |
| `void *b = calloc(1, 8);` | **fails** | compiles |
| `char *s = "x";`, VLA, designated init `{.y=2}` | compiles | compiles |

So a C-matter lesson that uses `malloc` without a cast can be on-syllabus, correct,
and still unusable. Before blaming the header or the libc, check the language mode.

Switching to `-x c` is safe for a C-only curriculum and leaves C++ available: the
link step keeps `-lc++ -lc++abi`, and `include/c++/v1/` plus `libc++.a` /
`libc++abi.a` stay in the tar, so `-x c++` can be sent again for individual C++
files later. Verify a mode change against the whole curriculum, not one sample.

## 3c. Stdin is EOF-forever — programs that re-read it spin

`public/shared.js` `host_read` (around line 272): when `stdinStrPos >=
stdinStr.length`, it sets `waitingForInput = true` and returns EOF (0 bytes) but keeps
yielding control back to the program. A program that reads again after EOF spins
without bound. Measured: `do { printf("masukkan: "); scanf("%d",&a); } while (a<=0);`
with empty stdin emitted **1,058,462 characters in 15 seconds** and never finished.

- Only bites when stdin is exhausted mid-run. Supplying `"5\n"` or `"0\n5\n"`
  finishes normally; a program with no input at all finishes normally.
- It is **not** caused by the `-x c` patch — confirmed by running the identical
  case against `git show HEAD:public/shared.js`; both spin.
- The app hides it: `waitingForInput` holds the output and prompts the user for more
  input (`src/pages/LandingPage.tsx`). A student pressing Enter on empty input is
  the trigger.
- Lesson-authoring rule: never write a lesson loop that reads again after a failed
  read, or give the exercise a non-empty sample input.

## 4. Pitfalls

- **An emcc build without `-sFORCE_FILESYSTEM` / `-sEXPORTED_RUNTIME_METHODS=FS`
  cannot be handed files.** Touching `Module.FS` (even inside `preRun`) aborts with
  `'FS' was not exported. add it to EXPORTED_RUNTIME_METHODS (see the Emscripten FAQ)`,
  and a `preRun` that expects `function(Module)` may receive nothing. So `-I <dir>`
  reports every header as missing — that is a missing filesystem, not a headerless
  compiler. Detect it in the build args, and state the distinction.
- **A cross compiler has no runtime.** `-run` answers `error: -run is not available
  in a cross compiler`; a bare link fails on every CRT object (`crt1.o`, `crti.o`,
  `crtn.o`, `library 'c'`, `libtcc1.a`). Only `-E` and `-c` are meaningful, and
  `-c -o out.o` exits silently with no artifact because there is no FS to write to.
- **`-I` on a path that does not exist in the MEMFS is silent** — no warning about
  the include dir itself, only per-header `not found`. Enumerate with
  `-print-search-dirs` before reporting a negative.
- **Probe scripts: `write_file`, run with `node`/`bun`, delete afterwards.** Never a
  bash heredoc (it eats backslash escapes — see SKILL.md), and do not leave probes in
  `scratch/`, which already mixes throwaway scripts with real data the user reads.
- **Always end a probe with `process.exit(0)` once the compile+link+run returns.**
  Without it the Node/Bun process does not exit even though the WASM program
  finished, so the harness reports a timeout and you read "the lesson hangs" out of
  something that actually printed its correct output. Confirm by capturing stdout:
  the run that "hung" showed `Grade: C` and `compileLinkRun RETURNED` before the
  timeout fired.
- **Do not trust a single timeout as "the code fails".** Re-run the same case: a job
  that hangs once may finish in ~1s in the next round. When rounds disagree, the
  causes are the missing `process.exit`, an actually exhausted stdin (section 3c), or
  stdin not being wired in at all. Separate them before reporting anything as broken,
  then re-run the curriculum end-to-end — a flaky first pass overstates the failures.
- **Cap what a probe may print when the case can loop.** A spinning program produced
  a 1 MB stdout that overflowed the terminal capture; silence `hostWrite` as well as
  the C `printf` when sweeping untrusted code.

## 5. TCC-wasm verdict (eliot-akira/tcc-wasm, i386-linux cross build)

- **Headers: none usable.** `tcc/config.h` sets `CONFIG_TCCDIR "/tmp/tcc/lib/tcc"`,
  which does not exist in the MEMFS, and every default include dir
  (`/tmp/tcc/lib/tcc/include`, `/usr/local/include[/i386-linux-gnu]`,
  `/usr/include[/i386-linux-gnu]`) is empty. `#include <stdio.h>` →
  `error: include file 'stdio.h' not found` for every candidate, including the five
  the source tree actually ships in `tcc/include/` (`stddef.h`, `stdarg.h`,
  `stdbool.h`, `float.h`, `varargs.h`) and `tcclib.h`; `-I` at `/tmp`, `/dev`,
  `/usr`, or `tcc/include` changes nothing.
- The source tree holds usable headers but the build does not wire them in:
  `tcc/include/` (5 + `tcclib.h`) and `tcc/win32/include/` (61: stdio stdlib string
  math …) — the latter is inert because the build is not `TCC_TARGET_PE`.
- Works: `-E` with `-D`/`-U` (macros expand correctly), `-dM -E`, `-c -o`, `-hh`.
- Does not work: any `#include`, linking, `-run`.
- To make it usable: rebuild with `-sFORCE_FILESYSTEM -sEXPORTED_RUNTIME_METHODS=FS`
  and preload `tcc/include` + `tcclib.h` into the MEMFS (the emcc arg list lives in
  `scratch/tcc-wasm-repo/build.ts`).
