# Offline verification: real evidence without a live browser

When the browser driver is unavailable — or the behavior is a pointer drag that no
snapshot can replay — you can still produce evidence. Only the *claim* shrinks,
not the rigor. Work the ladder strongest-first and say which rung you reached.

## 1. Dependency-source ground truth

The rule you are reasoning about is usually shipped with the dependency. Read it
from the installed copy rather than from docs, memory, or a blog post.

```
node_modules/<pkg>/dist/esm/index.js     # validation fn, constants, selectors
node_modules/<pkg>/dist/style.css        # geometry the component relies on
```

What to extract:

- the **validation function** (the exact boolean that rejects the interaction);
- the **state selector** that gates rendering or pointer handling;
- the **stylesheet rules** for position/offset/pointer-events of the element in
  question — these encode assumptions your CSS must satisfy.

Quote the lines in your report. This is version-exact evidence, and it also tells
you which of your own assumptions are invalid.

## 2. Emitted-markup evidence (SSR)

`react-dom/server` renders real markup in Node — no jsdom, no browser, no extra
dependency, and it works in a repo whose test runner is `node`-environment.

```ts
renderToString(
  createElement(RequiredProvider, null, createElement(Component, explicitProps)),
)
```

Two failure modes that make this look like "the component doesn't render here":

- **Missing provider.** Context-hungry components throw or bail (React Flow's
  `Handle` reports error #001 and emits nothing).
- **Missing props the real wrapper supplies.** A thin wrapper component passes
  props the base does not default; drive the BASE directly and you must supply
  them yourself (e.g. an explicit `kind` that indexes the port table). Without it
  the lookup returns empty and you get zero elements — not because they are
  absent in the app.

**Print the markup first** and confirm the elements you expect appear at all.
Never conclude "absent in the app" from a harness that rendered nothing.

Good things to assert afterwards: element counts per logical unit, `type`/role
attributes, generated classes, and inline geometry strings.

## 3. Invariant tests over source assets

When the fix depends on CSS or config, lock the invariants — in the repo's test
suite, not in a one-off script.

- **Strip comments before regexing CSS.** Comment text that names the property
  you are forbidding (`"do not use overflow: hidden here"`) matches your own
  forbidden-pattern assertion and fails a correct file.
- Extract a rule block by selector, then assert on its body
  (`position`, `z-index`, `pointer-events`, sizes, offsets).
- **Assert the dependency assumption too** (`assertEquals(handleRule, /translate\(50%\)/)`),
  so a library upgrade that invalidates your fix shows up as a failing test.
- Cross-file invariants are the valuable ones: "spacing constant >= handle size +
  hit area", "every logical port exposes both connection roles". Tie the two
  files together in one assertion, and the bug class cannot come back silently.

## 4. Phrase the claim honestly

Template:

> Could not replay the interaction here (no working browser driver). Verified: the
> emitted markup (N elements, roles X/Y), the library's validation rule quoted
> from `node_modules/...`, and the invariants now locked in `tests/<file>`.
> Please confirm with: 1) hard refresh, 2) <step>, 3) <step>.

The **hard refresh** matters: a cached bundle makes the user exercise the old
code and report your fix as failed, which looks like a wrong diagnosis when the
fix was simply never loaded.

## 5. Removing config dependency beats relying on it

If the fix only works when a runtime flag is set correctly, and you cannot verify
the flag is live in the user's session, make the code correct *without* the flag.
A passing typecheck proves the value reaches the library; it does not prove the
library then behaves as you assume. Prefer the structural fix and keep the flag as
redundancy — then a stale bundle or a missing prop can no longer defeat it.
