# Reproducing multi-step browser flows against two builds

For defects that have no error to read: "one item got skipped", "the step
advanced on its own", "the percentage was blank until I clicked". The handler
looks correct in the source, the console is clean, and every request answers
200. Reading more code does not converge — script the flow in a real browser
against TWO targets and diff the runs.

- Target A: the DEPLOYED bundle (old code, the reported symptom)
- Target B: `localhost` dev server (the fix)

The difference between the two transcripts IS the proof, and each run is
expected to fail differently.

## Setup

1. **Log in as a seeded test account** (see SKILL.md Step 6c). Mint the token with
the app's own secret and open `/?token=<jwt>`; the app stores it and strips the
query param.

```python
# mint an HS256 token with the app's JWT_SECRET, save to a scratch file
payload = {'nim': '999900001', 'nama': 'TEST Praktikan', 'role': 'praktikan'}
```

   A minted token is only valid where the app accepts that shape. A server route
   that verifies against Supabase Auth will refuse it — if the page needs a real
   session, ask the owner for the test account's password rather than attacking
   the stored hash.

2. **Clear the app's persisted state at the START of every run** — otherwise run 1
   poisons run 2 and you debug your own leftovers:

```js
Object.keys(localStorage)
  .filter(k => k.startsWith('lesson-step') || k.startsWith('lesson-code')
            || k === 'last-lesson-checkpoint')
  .forEach(k => localStorage.removeItem(k));
```

## Driving it

Use the standalone CLI, one eval per few actions, with timing from the shell:

```bash
npx agent-browser open "http://localhost:3000/?token=$TOK"
npx agent-browser eval --stdin < flow.js      # or: eval -b "$(base64 -w0 flow.js)"
```

- Pass multi-line JS on **STDIN** (or `--stdin`/`-b` base64). An inline argument
  loses shell escaping and the script arrives truncated (`SyntaxError: Unexpected
  end of input`).
- Keep each eval to a few actions. One long `async` script that sleeps
  internally outlives the CDP read timeout; take the waits from the shell's own
  `sleep` between calls instead.
- A bare `sleep` + retry is the recovery for an intermittent CDP read failure.
  If evals start failing wholesale, close the session and reopen once.

## Asserting

Assert on OBSERVABLE state at each step and return it as JSON:

- the rendered heading / which panel is on screen (test for a string unique to
  each panel — `RESET KODE` = code step, `Periksa Jawaban` = quiz, `Ikuti Kuis` =
  learn)
- the persisted per-item keys (`Object.keys(localStorage).filter(k => k.startsWith('<ns>:'))`)
- button `disabled` flags

An assertion on an inferred internal variable is not evidence. Run the identical
script against both targets and put the transcripts side by side in the report.

## Worked example — a timer that outlives its item

Shape: a component sets `setTimeout(() => setStep('code'), 1500)` after a correct
answer, and the user clicks **Next** within that window. The timer then fires in
the NEXT item and drags it forward, so the user sees one item skipped.

Script: answer correctly, click Next twice inside the delay, then wait past the
delay and read the persisted keys.

```
OLD BUILD   c-level-1-m1-l1=learn
            c-level-1-m1-l3=code    <- l3 was forced by l1's timer
NEW BUILD   c-level-1-m1-l1=learn
            c-level-1-m1-l3=learn   <- timer cancelled
```

The fix is not in the code that SETS the timer. Hold the handle in a `useRef` and
clear it on every exit path the user controls (next/prev, every button that
changes the step) **and whenever the item id changes** — a timer that survives a
navigation writes its update into whatever item is current now.

## Before blaming navigation, enumerate the data

A "skipped" item is often a GAP in the source data. List the children in the
app's own order and read the ids:

```bash
curl -s "$URL/rest/v1/lessons?select=id,sort_order&module_id=eq.<module>&order=sort_order" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC"
# -> l1 (0), l3 (1), l4 (2): there IS no l2, so l1 -> l3 is the data
```

Confirm `sort_order` carries no NULLs and no duplicates WITHIN a module (a
per-module `0,1,2` is fine even though it repeats across every other module).

## A bug writeup in the repo is a hypothesis

A checked-in notes file (`STATUS-*.md`, a hand-off bug-hunt writeup) describing a
live outage is a repo artefact like any other: re-probe it before acting.

Measured: the file reported `404 Lesson not found` for lessons that exist and
concluded the host was missing its Supabase env vars. The live route actually
answered `200 {"isCorrect":true,"correctAnswer":2}` for the right option and
`{"isCorrect":false,...}` for a wrong one — the outage it described was already
fixed, and following the file would have sent the session chasing a closed
problem and re-doing an env setup that was already correct.

Separate the columns when you report: code committed / code deployed / SQL
applied / symptom observed. A stale file disagrees with the live probe, and the
probe wins.
