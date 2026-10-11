---
name: course-content-alignment
description: "Align app course content to a source module doc."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [curriculum, elearning, content-sync, praktikum, supabase, pdf]
    related_skills: [supabase-backend-debugging, python-coursework, pdf]
---

# Course Content Alignment (kurikulum app ⇄ modul sumber)

The user runs learning-platform repos (E-Learning) whose levels/modules/lessons
live in a Supabase DB seeded from a curriculum source. They periodically ask to
"sesuaikan materi dengan modul" — align the app's content with the official
module document. Respond in Bahasa Indonesia.

## When to use

- "sesuaikan materi di db dengan modul", "materi X tidak sesuai modul", "ada materi yang tidak ada di modul".
- A level's lessons need auditing against a module PDF/DOCX, or a level was added/renamed.
- The user names a specific topic to remove (e.g. "materi tentang tuple").

## Iron rules

1. **The module document is the source of truth; the app is the thing being
   corrected.** Never let app content define the syllabus.
2. **NEVER rewrite lesson content to "improve" it.** The user's explicit rule:
   *jangan tulis ulang; kalau ada yang tidak ada di modul, hapus*. Edit = trim the
   out-of-scope part, fix a wrong example, or delete the lesson — nothing more. Do
   not re-author explanations, reorder pedagogy, or add topics you think belong.
3. **Content in the module that is missing from the app is NOT your call to add**
   unless asked — report the gap and let the user decide.
4. **Keep child ids stable.** Renaming a level id is safe for progress; renaming
   lesson ids breaks `student_progress` (keyed on lesson id). Order for a parent
   rename: insert new → re-point children → delete old (see
   `supabase-backend-debugging` Step 6d).

## Step 1 — Extract the module document in full, first

Do not audit from memory or from the app. Dump the whole document to a text file
once, then read from that:

```bash
python -c "
from pypdf import PdfReader
r = PdfReader('MODUL.pdf')
open('modul_full.txt','w',encoding='utf-8').write(
  '\n'.join(f'===== HALAMAN {i+1} =====\n'+(p.extract_text() or '') for i,p in enumerate(r.pages)))
print('pages:', len(r.pages))"
```

- Some pages return near-empty text (scanned images) — note them and read those
  pages individually rather than concluding the module lacks the section.
- Build the module map first (which Modul covers which topic, with page ranges),
  then map app levels onto it. Report the mapping to the user before editing.

## Step 2 — Decide each lesson's fate, per level

For each level, list the app's modules/lessons beside the module's sections.
Classify each lesson: **in scope** (keep), **partly out of scope** (trim the
offending passage/example), or **out of scope** (delete the lesson; delete the
whole module if all its lessons are out of scope).

Level/theme titles follow the module's wording verbatim. If the user's own list
has an obvious typo (e.g. "pegolahan"), use the correct spelling and flag it
rather than propagating it.

## Step 3 — Find off-syllabus content with a keyword scan, then read context

A keyword sweep finds candidates; it does NOT decide. Expect heavy false
positives, and read the surrounding text before deleting anything:

```ts
// scratch/scan_deviasi.mts — service-key client
const banned = ['tuple','set ','numpy','pandas','with open','json','csv',
                'class ','oop','rekursi','lambda','pointer','struct'];
for (const l of all) {
  const text = (l.title + ' ' + (l.explanation||'') + ' ' + (l.code_example||'')).toLowerCase();
  const hits = banned.filter(b => text.includes(b));
  if (hits.length) console.log(l.id, '|', l.title, '| kena:', hits.join(', '));
}
```

Known false-positive mechanisms to filter by eye: `oop` matches **l**oop;
`class` matches the English word and HTML `class=` attributes; `file` matches
"header **file**"; `pointer` may genuinely be in the module. Report the *real*
hits, not the raw scan count.

When a topic must go, fix **every** field that carries it, not just the prose:
`explanation` (HTML), `code_example`, `initial_code`, `solution`, `hint`,
`test_cases[].description`/`expectedOutput`, and `validation_rules[]` patterns.
A lesson whose explanation is clean but whose exercise still requires the banned
construct (e.g. a `return a, b` multi-return drill) is not fixed. Re-scan the
whole row after the edit and print "masih ada X? bersih/YA".

## Step 3b — For CODE lessons, the runner is a second source of truth

The module says what is *in scope*; it does not say what *compiles*. Every C
lesson in these apps is executed **in the browser on the app's own WASM toolchain**
(`public/clang` + `public/lld` + `public/sysroot.tar`, driven by
`public/clang-worker.js` / `shared.js` via `src/hooks/useCodeRunner.ts`) — a
clang against **wasi-libc**. The Judge0/Wandbox helpers still present in that file
are dead paths; do not treat their results as the app's behaviour. So a lesson can
be perfectly on-syllabus and still fail at the first Run. Both gates must pass
before you call a lesson clean:

| lesson is… | action |
|---|---|
| in module **and** compiles | keep |
| in module **but** fails to compile | keep the topic, swap in an equivalent **the module also lists**, and retitle if the title names the broken symbol |
| not in module, compiles | trim it (Iron rule 2) |
| not in module, does not compile | trim it |

Run the verification, do not reason about it. Prefer the **offline WASM harness**
(load `public/shared.js` in Node → `api.compileLinkRun(code)` → read stdout): it is
the student's actual toolchain and needs no browser or network. The batch recipe,
the loader shape, and the verified break/pass table are in
`references/c-lesson-code-validation.md`. Only fall back to a public glibc
compiler for syntax/logic checks of symbols the sysroot does have — its pass is
**never** evidence the app will run the lesson.

Typical conflicts, and the replacement to reach for. Decide from the **sysroot**,
never from a glibc compiler — a symbol a glibc toolchain still carries (`gets`
lives on as a compat symbol; `gcc-13.2.0-c` even runs it) can be absent from
wasi-libc and fail at LINK:

| module-listed symbol | verdict on this toolchain |
|---|---|
| `gets(buf)` | **fails to link** — `wasm-ld: undefined symbol: gets`; the header only declares it as `__deprecated__("gets is not defined on WASI")`. Replace with the module's own `scanf("%[^\n]", var)` + `getchar()` and retitle, since the title names the broken symbol. |
| `strcat` | links, but check the module — it may be absent from the syllabus. Out of scope still means trim. |
| `#include <windows.h>`, `Sleep`, `getch`, `getche`, `system` | **all absent** — 0× in the sysroot. The module documents `<windows.h>` only for `system("cls" / "echo …" / "color …")`, and `system` is missing too, so there is **no faithful in-scope replacement**. Do not invent a swap that silently fails at link: report the conflict and let the user choose (rewrite as a conceptual non-portability lesson, move it to theory, or delete it). |

Never leave a lesson whose solution cannot build: the student sees a compile
error as the answer.

## Step 3c — Schema drift: sync the repo's setup SQL too, and never let a type lie

These repos keep their own `docs/*setup*.sql` / `*permissions*.sql` as the
provisioning source. They drift from the live database, and the drift is silent
because nobody re-runs them — until someone provisions a fresh environment and
gets a schema the app has never seen. When you have to **create or rewrite a
column**, or you are writing a `CREATE TABLE` seed generator, verify each column's
shape against the live DB instead of copying the file:

```bash
# per table: column -> PostgREST `format`; NULLability -> `required`
curl -s "$URL/rest/v1/" -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python -c "
import sys,json; d=json.load(sys.stdin)['definitions']
for t in ('lessons','game_settings','achievements'):
    p=d.get(t,{}).get('properties',{}); req=set(d.get(t,{}).get('required') or [])
    print(t, {k:(v.get('format') or v.get('type')) for k,v in p.items()}, 'NOT NULL:', req)"
```

Drift found this way, all invisible to a reader of the SQL: a column the file
invents and the DB lacks, a `requirement_value INTEGER` the DB actually stores as
`text`, a `category` the file declares and no row has, a PK the file writes as
`TEXT` while the DB default-generates a `uuid`, and an `id` cross-reference the
file declares as a foreign key that the live schema never created. Correct the
document toward the DB (the DB is what runs), then say in the commit which
column/constraint you aligned — the next reader has no other way to tell.

**Read the declared type before parsing a value the API returns.** A `TEXT` column
holding JSON comes back as a JSON *string*, so field access on it silently yields
`undefined`; measured by column, not by assumption
(`lessons.quiz`: `format=text`, value `"{\"question\":…,\"correctAnswer\":2}"`).
Parse when it is a string and guard the failure — a value that fails to parse is
corrupt data (`500`), never "this column has no value" (`400`), or a whole
feature reports itself unconfigured while the data is sitting right there.

## Step 4 — Apply via the service key, then verify counts

Script the change (idempotent upsert), print a before/after count per level, and
re-read the rows to confirm. Row-writing mechanics, ordering rules, and the
canonical script shape live in `references/db-seeding-recipes.md`.

```
level-N | modul: X | lessons: Y     # after must differ by exactly the intended delta
modul yatim: 0                      # no module left pointing at a removed level
```

## Step 5 — Commit per logical change; push HANYA setelah user menyetujui

Split commits by concern (content sync vs auth/role fix vs feature). Commit locally
when the change is verified, then **stop**. The user batches pushes himself (he may
have unrelated local work to send in the same push) and has explicitly said: do not
push without his approval. Report the local commit SHA and the branch; wait for
"push" before touching any remote.

**Before reporting push status, MEASURE it against the live remote — never from
memory of what you just did.** The working tree is shared, so another session can
commit while you work: `git log --oneline -3` may not show your work as HEAD, and
the unpushed set can include files you never touched. Report which commits are
not yours and ask before sweeping them into a commit.

```bash
git branch --show-current
git ls-remote --heads <remote> <branch>           # live ref; check BOTH remotes
git log --oneline --reverse origin/<branch>..HEAD # exactly what is unpushed
git status --short                                # strays to report, not to commit
```

**Write commit messages with `-F <file>`, never `-m "..."`.** The shell expands
the quoted message on this setup, so a backtick or `${...}` inside it is executed
or substituted and silently disappears from the text — a message describing
`key={`quiz-${lesson.id}`}` came out as "key pembungkus jadi  dan". The commit
still succeeds, so you only notice by re-reading it. Write the message with
`write_file`, then `git commit -F <file>` (`git commit --amend -F <file>` to
repair one already made). This bites hardest on messages that quote code.

When he does approve, push to **every** deployed remote — with two remotes
(`origin` + `upstream`) still verify both with `git ls-remote --heads <remote> <branch>`
and confirm the SHA matches. A deployer reading only one remote makes prod stale.

**Pushing the feature branch is not the end of the job when the deployer reads
`main` — measure the divergence before promising anything reaches users.** Work
accumulates on a feature branch while `main` keeps moving with other people's
commits, so the two diverge in BOTH directions and a deploy of the branch never
reaches production while a merge fails on files changed on both sides:

```bash
git fetch origin main
git rev-list --count origin/main..HEAD     # what you would bring in
git rev-list --count HEAD..origin/main     # what main already has that you lack
comm -12 <(git diff --name-only $(git merge-base HEAD origin/main)..HEAD | sort) \
         <(git diff --name-only $(git merge-base HEAD origin/main)..origin/main | sort)
```

The file list from `comm` is the conflict prediction — say which files and why
(shared auth/config modules are the usual ones) BEFORE merging, and
`git merge --no-commit --no-ff` to see the real conflict set when the user has
greenlit it. Resolve by taking the side that is the superset of behaviour, not
the side that is newer: when both branches reimplemented one thing (e.g. a token
filter), keep the more complete implementation and name in the commit which
behaviour you dropped. Auto-merged files can still carry a regression — re-verify
your own earlier fix survived the merge. A dry-run conflict check
(`git merge-tree $(git merge-base HEAD origin/main) HEAD origin/main | rg -c '^<<<<<<<'`)
tells the user whether the merge is safe to click in the web UI.

## Pitfalls

- **Know what each exercise field is FOR before writing or replacing one.**
  `initial_code` is the fill-in-the-blank template the student completes — rumpang
  placeholders (`__`, `__()`), in the same style as sibling lessons, never working
  code; `solution` is that template filled in; `code_example` is the demo shown
  above them. Keep the placeholder STYLE consistent with the neighbouring lessons
  (a bare `__;` where siblings write `__();` reads as a different kind of blank).
  And `solution` never reaches students at all — the role-split view strips it — so
  the template must be completable from `explanation` + `hint` + `initial_code`
  alone. Write `initial_code` as if no answer will ever be visible, and read a
  sibling lesson before inventing the blank pattern.
- **Coverage is not compliance — only a question-by-question answer to "sudah
  sesuai semua?" will do.** Mapping every module sub-section to a lesson proves
  coverage. It does not prove scope, and it does not entitle you to a yes. When
  the user asks whether the material now all matches the module, that is the
  moment to run the full sweep and report the counts, because a "yes" you did not
  measure is the one answer they will act on. This session answered "ya, kecuali
  6 lesson matplotlib" and drew the rejoinder that those 6 work on the user's
  machine — an unverified environmental caveat presented as a finding. **Do not
  pad a compliance report with findings you introduced yourself** (a local
  interpreter missing a package the app fetches at runtime, a probe harness
  artefact) — filter those out before reporting, and if one is genuinely
  uncertain, label it as your own assumption rather than as a defect in their
  content.- **A "struktur sudah sesuai" answer is not a "materi sudah sesuai" answer — audit
  CONTENT against the module's own symbol list.** Mapping every module sub-section to
  a lesson proves coverage, not scope. Sweep the module for every function/keyword it
  actually names per library, then sweep every lesson field for symbols NOT in that
  list; a lesson can map to the right sub-section yet teach four things the module
  never mentions. Keep your own words out of the verdict — when the user asks "sudah
  sesuai semua?", report the counts and the deviations instead of claiming compliance.
  Off-module leftovers hide in the most ordinary places: a table row, a `code_example`
  that the exercise doesn't use, and a single stray term in prose while the syntax
  itself is fine.
- **Match the module's own TERMINOLOGY, not a synonym you prefer.** If the module
  writes "formatting string" and demonstrates `print(f"…")`, retire the popular label
  (`f-string`) from titles, prose, hints, quiz and test descriptions. Renaming the term
  is in scope (it is not re-authoring); leaving a term the module never uses reads as
  off-syllabus even when the syntax is correct.
- **Audit in BOTH directions between the DB and the local fallback.** The app ships a
  static `src/data/curriculum.ts` used when the DB is unreachable, so it can carry
  stale rows, levels and modules that no longer exist in the DB — including lessons
  that were deleted there. Count lessons per side and diff the id sets; prune the
  file's orphans, then re-sync the intended edits. Assume drift, do not assume sync.
- **Embedding images means checking the renderer's whitelist AND the CSP, then
  proving it with a build.** Explanations are injected as HTML through a sanitiser
  that decodes and keeps only a fixed tag allowlist — confirm `img` is in it before
  writing any markup, and reuse an existing wrapper class instead of inventing one
  (`figure`/`figcaption` were silently dropped while a plain `div` + `p` rendered).
  The policy must allow the asset source too, and a static asset only reaches prod if
  the build copies it — finish with a real build and check the file landed in
  `dist/`. You cannot extract or upload an image out of a PDF, so say plainly that you
  authored the replacement (SVG built to the placeholder's described content) and
  invite the user to supply the original rather than implying it came from the module.
  When the user *does* hand over their own assets, replace yours and delete the
  authored set — leaving both means the next session cannot tell which is canonical.
- **Read a vector asset as source, and say so instead of claiming you cannot see
  images.** Asked whether you can view a diagram, the honest answer depends on the
  FORMAT: raster (PNG/JPG) needs vision, but SVG is plain text — list the directory
  with the shell, then read the file and parse its `viewBox`, shape elements and
  `<text>` labels. That is enough to learn a diagram's symbols, its connectors and
  its flow order, and to map each one onto an app's shape enum before writing any
  exercise data. Answer "raster no, SVG yes" rather than a flat no, and never let
  a missing vision channel stop you reading a file that is text on disk.
- **Before writing exercise data for an existing interactive component, read its
  VALIDATION and confirm it can express the shape you are about to encode.** A
  component can look generic and still be structurally limited: one measured puzzle
  kept a single column of drop slots (`solution.map(() => null)`) and graded with
  `slots.every((s, i) => s.shape === solution[i].shape && s.label === solution[i].label)`
  — exact order, one linear chain, no branches. Feeding it a flow with a decision
  that splits into two parallel paths makes the expected answer ambiguous, so the
  "correct" order is arguable and the exercise stops being gradable. Read the
  grader first, then either extend the component for the shape the topic actually
  needs (a decision gets two child slots) or scope the exercise to what it can
  represent — and tell the user which of the two you are doing and why, because
  silently flattening a branching topic into a linear drill removes the very thing
  the lesson is about. Related: a topic that changes EXERCISE TYPE stops being a
  coding lesson, so its `code_example`/`initial_code`/`solution` no longer apply —
  the interactive payload moves into the field the component reads (here
  `solution` carries the ordered symbol JSON, `initial_code` the read-only source
  to translate) and the exercise-type marker decides which editor renders.
  **That payload field is normally invisible to students.** The role-split view
  strips `solution`, so a client-graded interactive exercise arrives with the
  answer missing and renders empty for non-staff while working for staff — the
  same wrong-for-one-role shape as the quiz key. Settle it BEFORE writing data and
  tell the user which you chose: (a) ship the payload to students and accept that
  one Network-tab read exposes the answer, (b) grade on the server as the quiz
  does and keep the field server-only, or (c) keep client grading but mark the
  exercise non-scored so the exposed answer is worthless. Then note the two-part
  delivery: the sanitised view lists its columns explicitly, so a new exercise-type
  column must be appended to the view's SELECT too (see
  `supabase-backend-debugging` Step 5b) or the role reading the view never gets it.
- **"Jawaban benar dinyatakan salah" is an app bug, not bad answer keys — verify the
  keys, then find the grading path.** Check every key in the DB first
  (`correctAnswer` must be a `number`, in range, and factually right); when they are
  clean, the fault is in how the client grades. Two independent mechanisms have
  produced this exact symptom, so rule out BOTH:
  1. *Which table a role reads decides whether grading happens client-side.* Staf
     read `lessons` (key present → graded locally in the component, so it looks
     correct); non-staf read the `student_lessons` view, which deliberately strips
     `correctAnswer` and `solution`. Any code that substitutes a default for the
     missing key (`… : 0`) turns option 0 into a phantom "correct" answer and marks
     every real answer wrong. Keep the absent key `undefined` so the component knows
     it must ask the server, and gate client-side grading on the value really being
     a number. **When a defect appears for one role but not another, diff the data
     source per role (table vs view) before touching content.**
     A sentinel convention (`-1 = unknown`) is defeated the moment the producer
     defaults to `0`; make the unknown value `undefined` and gate on
     `typeof key === 'number' && key >= 0`. Before rewiring grading onto the
     server, prove that path end-to-end with a real token — shipping the client
     half alone converts a wrong-marking bug into a cannot-answer bug. And when the
     user asks why not simply ship the key to every role: answer with the measured
     trade-off (one Network-tab read of the curriculum response exposes all keys at
     once, versus a one-time env setup on the host), then name what the choice
     costs (a key that reaches the client cannot back graded assessment). Measure
     the cheaper attack paths before presenting the stripping as a security
     control — in these apps the client also writes `student_progress`, and code
     exercises can be satisfied through `validation_rules` patterns, so hiding one
     key closes one door while another stands open. Say that plainly rather than
     letting the view look stronger than it is.
  2. *A reused component keeps the previous item's state.* A wrapper keyed by a
     constant (`key="quiz"`) makes React reuse the same instance across lessons, so
     `correctAnswerIndex` from the previous lesson leaks in. Give the wrapper and the
     child a per-item key AND reset state in `useEffect(…, [id])` so it does not
     depend on the caller. Reproduce the sequence (answer item A, move to item B)
     before concluding anything.
- **When a topic genuinely branches, the branch must be something the student
  CHOOSES — not a position they happen to place first.** Extending the puzzle for
  the branching lesson works only if ambiguity is removed by the data shape: give
  each `decision` its own Ya/Tidak slots and grade "this card in that branch",
  never "this card at index N". Version the payload
  (`{version, flow:[{at:'main'|'yes'|'no', shape, label}]}`) and keep accepting the
  old flat array as all-`main`, so already-written exercises do not break. Group
  branches positionally — the nth `decision` on `main` owns the nth run of
  `yes`/`no` entries — and render the branch columns only under their decision.
  Two checks that catch the whole class: total slots must equal the number of
  correct cards in the bank (not bank size, which includes distractors), and no
  branch may exist before any `decision` on `main`.
- **A lesson with NO quiz can never be completed if the completion gate is
  hardcoded to a passed quiz.** `isQuizPassed = isLessonDone || quizXpGranted` is
  only true after a quiz is answered (or the lesson was already done), so a newly
  added quiz-less lesson is stuck forever with its finish button disabled — and it
  reads as a broken new lesson, not as a gate bug. When a lesson changes exercise
  KIND (code → interactive, quiz → no quiz), audit every gate keyed on the old
  kind: the quiz gate, `validationRules`, and `testCases`. Empty
  `validationRules`/`testCases` are already safe (their loops skip or pass); the
  quiz gate is the one needing an explicit `|| !hasQuiz`.
- **De-AI the prose with contextual rewrites, never a blind global replace.**
  Measured tells in this corpus: em dash `—` (155× in 72 lessons) and cliché
  phrases (`sangat penting`, `mudah dibaca`, `modern`, `efisien`, `fleksibel`,
  `selain itu`, `fundamental`, plus 41 total). Em dash → `, ` / `: ` / `; ` by
  context (a `\s*—\s*` → `, ` rule plus a space-before-punctuation cleanup is
  enough), and rewrite each cliché phrase in its own sentence. Two traps: (1) a
  global `\s{2,}` → `' '` collapse destroys HTML tag indentation and rewrites
  **every** lesson — always operate inside prose segments only, skipping
  `<pre>`/`<code>`; (2) em dash also hides in `code_example` comments,
  `validation_rules[].message`, and `test_cases[].description`, so sweep those
  fields too. Keep genuinely technical uses (`bilangan kompleks`, `koefisien
  korelasi Pearson`) — say so in the report instead of forcing them out.
- **Audit prose for leaked markdown before judging the writing.** A flawed
  markdown→HTML pass leaves raw `*`/`**` inside `<p>`/`<li>` in `explanation`
  (13 lessons had it), and — worse — pairs the `**` markers wrongly so bold lands
  on the wrong span: `*Operator unary<strong> adalah ... </strong>satu operand**`
  should read `<strong>Operator unary</strong> adalah ... <strong>satu
  operand</strong>`. Detect by stripping `<pre>`/`<code>` first, then looking for
  stray `*` and for `count(<strong>) != count(</strong>)`. Fix order matters:
  targeted rules for the clean cases, then — only for blocks still dirty — rebuild
  the block treating every marker (`*`, `**`, `<strong>`, `</strong>`) as an
  open/close toggle. Never use a greedy rule that crosses tags
  (`\*([^*<]{1,160}?)<strong>[\s\S]{1,500}?<\/strong>([^*<]{1,160}?)\*\*` swallowed
  whole `<td>` table rows and wrecked them).
- **Never repair `*` in `hint` blindly** — there it is usually the real operator
  (`3.14 * radius ** 2`, `"'+','-','*','/'"`). Restrict markdown repair to
  `explanation`. Back the rows up first (`select id,explanation,hint` → JSON) and
  dry-run before applying; re-sync `curriculum.ts` afterwards.
- **`expectedOutput` must equal what the runner really prints — and the runner
  never echoes stdin.** `pyodide.worker.js` replaces `sys.stdout` with a
  `StringIO` and the WASM `MemFS.host_read` pipes stdin straight in, so a test
  case whose `expectedOutput` lists the typed input (`Masukkan angka: -7\nHasil: …`)
  can never match and the lesson is unsolvable. It is also not internal: the
  lesson UI renders it as the student's target-output hint, so a wrong one
  actively misleads them about what to aim for — check visibility before assuming
  a broken value is harmless. This was the single most common
  defect: 15 of 43 C lessons plus 4 Python lessons. Same class: `expectedOutput`
  carrying non-output text (`(Ganti `A` dengan inisial pilihanmu)`), and a
  test-case `input` written in prose `scanf` cannot parse (`"23 dan 4"`, `"8 dan 8"`,
  `"12 dan 8"` — inputs are newline-separated, one value per line). **Fix by
  deriving `expectedOutput` from a real run** of the lesson's `solution` with that
  input, never by hand-editing the string, then re-sweep and report the
  COCOK/deviating counts.
- **Editing lesson blocks in `src/data/curriculum.ts` needs exact line-based
  boundaries.** One big `curriculum: Level[]` literal written by `JSON.stringify`:
  lesson entries at indent 12 (`"id"`), section closers `          },` at indent 10,
  some entries (e.g. `py7-l1`) on a single line. `\n` inside JSON strings is a real
  newline in the file, so searching for `"\n          },"` finds nothing. Correct
  limits: start at `            "id": "<id>",`; end at the **last** `          },`
  line before the next `            "id": ` line (or EOF). The **first** `          },`
  truncates mid-block, and deriving the end from the NEXT lesson id fails on
  one-line entries — either mistake corrupts the file badly (duplicated
  `},          },`, a 300 MB file, `RangeError: Invalid string length`). Work on
  `readFileSync(...).split('\n')` + `splice`, run `npx tsc --noEmit` after every
  run, recover with `git checkout -- src/data/curriculum.ts`, and keep the count
  invariant: capture `rg -c '^            "id": '` before and after and require it
  to be unchanged (the file may hold more entries than the DB if stale content was
  never pruned).
  When the change spans many lessons, prefer **regenerating the whole tree from the
  DB** over surgical splices — but carry over the level fields the DB does not store
  (`accessMode`, `locked`, `description`), reading them out of the existing file
  first or they silently reset to the wrong values.
- **`lessons.quiz` is a JSON *string* in the DB but an object in the curriculum
  file.** `JSON.stringify(dbRow.quiz)` writes a quoted string and `tsc` fails with
  `Type 'string' is not assignable to type 'Quiz'`. Parse it before writing the
  block; keep `test_cases`/`validation_rules` as strings in the DB and arrays in
  the file.
- **A lesson can be on-syllabus and still unable to run.** The module lists
  functions the target toolchain no longer has (`gets()`, `windows.h`). Scan
  lessons against the module for scope, then against a real compile for validity —
  a fix that only satisfies the module ships a broken exercise. See Step 3b.
- **Answer toolchain questions for the toolchain that actually runs, and name
  which one you checked.** This repo carries a second, unused C compiler in
  `scratch/` (a vendored TCC-wasm) beside the live one (`public/clang` +
  `public/lld` + `public/sysroot.tar`); `grep -rn tcc src/` is empty, so a
  capability of the vendored build says nothing about what students get. Header and
  symbol capability lives in the tar, never in `src/` or in a vendored compiler's
  source tree — extract and count. Probing recipes, plus the per-compiler verdict
  table (TCC: no usable headers, `-run` unavailable, cross compiler):
  `references/wasm-toolchain-probing.md`.
- **"Which headers can I use?" needs an EXHAUSTIVE sweep, and the answer ships as a
  file.** Test every header in the tar, one compile each (~2 min); a sampled list is a
  wrong list — an earlier 92-header sample missed a real failure and wrongly declared
  `netinet/in.h` / `arpa/inet.h` absent. Report the full list in chat (bisa jalan / tidak
  bisa, with the cause per failing header), and write it up as a Markdown doc at the repo
  root (`Kemampuan WASM.md` exists for this) covering: which binary is live, the header
  tables, verified library functions, the compile-mode and stdin caveats, and the practical
  boleh-dipakai / jangan-dipakai summary for whoever writes lessons. Regenerate, do not
  hand-edit, when the sysroot changes.
- **A C lesson can fail because of the compile MODE, before any header is at fault.**
  The runner sends `-x c++`, so `int *p = malloc(...)` without a cast is an error
  (`cannot initialize a variable of type 'int *' with an rvalue`) while the same code is
  legal C — a wrong-language diagnostic on correct on-syllabus code. Check the mode before
  blaming a header or the libc, and verify any mode change against the whole curriculum.
- **Never author a lesson loop that re-reads after a failed read.** When stdin is
  exhausted the WASM runner returns EOF forever while still running the program, so
  `do { scanf(...); } while (bad);` spins unboundedly (measured: >1 MB of output in 15s).
  Give input-reading exercises a valid sample input, or restructure to a single read.
- **Write probe scripts with `write_file`, never a bash heredoc, when they embed
  C code.** A quoted heredoc still collapses backslash escapes, so
  `printf("halo\n")` reaches the compiler as `printf("halo` + a real newline and
  every submission returns `warning: missing terminating " character` — which
  looks like a broken compiler, not a broken script. Same fix if the code is
  built in JS: emit the newline as a literal (`String.fromCharCode(92)+'n'` or a
  placeholder replaced at send time), not via an escape the outer shell eats.
- **A rename that changes the id SHAPE breaks prefix filters, not just literals.**
  After `c-level-1`/`py-level-5` → `level-1..6`, any `id.startsWith('c-')` /
  `startsWith('p-')` filter returns empty and the page renders blank with no
  error — it reads like missing data. Grep for shape-based matching after any id
  rename. Details in `supabase-backend-debugging` Step 6d.
- **Deleting a lesson can orphan student progress rows** that reference its id.
  Check `student_progress` for those lesson ids first and report the count you
  are invalidating rather than deleting silently.
- **Don't renumber `sort_order` from 0 when level titles are 1-based** — the
  level labels then disagree with the module's numbering.
- **A "materi kosong / halaman hampa" report is a DATA question first.** Before
  editing any content, count rows for the affected role (base table vs the
  sanitised view, anon vs service key) — see `supabase-backend-debugging`
  Step 5b. An empty page is usually a missing view/grant or a broken filter, not
  missing curriculum.
- **Content work gets interleaved with live bug reports.** The user will switch
  mid-task ("kenapa error 400 ini?"). Commit the already-verified content change
  first, then switch — an uncommitted partial edit left behind is the usual
  casualty.

## References

- `references/db-seeding-recipes.md` — service-key row writes, upsert/ordering rules, canonical script shape.
- `references/c-lesson-code-validation.md` — probing C lesson code on the live runner: the offline WASM harness (`public/shared.js` loaded in Node, `compileLinkRun`, `process.exit(0)`, one child process per lesson), the verified break-vs-pass table for module-listed symbols, and the glibc-vs-wasi-libc traps.
- `references/wasm-toolchain-probing.md` — enumerate a WASM toolchain's own capability surface offline: full-sysroot header sweep script, the 113/117 verdict table, compile-mode (`-x c++`) and stdin-EOF traps, driving an Emscripten-built compiler from Node, per-compiler verdicts.
