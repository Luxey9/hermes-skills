# Driving Chromium over CDP

Use when the browser toolset will not drive a page, or when you need a session
that survives many calls. This is the fallback that works without any helper
library: launch Chromium yourself, attach to its page target, evaluate JS.

## Launch

Launch the browser **detached** so it outlives the launching script:

```js
const { spawn } = require('child_process');
const p = spawn(chromePath, [
  '--remote-debugging-port=9344',
  `--user-data-dir=${freshDir}`,   // a fresh dir avoids the single-instance lock
  '--no-first-run',
  '--headless=new',
  '--disable-gpu',
  'about:blank',
], { stdio: 'ignore', detached: true });
p.unref();
```

Put the launch in its own tiny script and run it once. Then the test script only
*attaches*, so a bug in the test cannot take the browser down with it.

A Playwright-managed Chromium is a reliable binary to point at —
`%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe` on Windows,
`~/.cache/ms-playwright/...` elsewhere. Install with
`npx playwright install chromium` if the directory is absent.

Confirm the port before attaching:

```bash
curl -s --max-time 3 http://127.0.0.1:9344/json/version
```

## Attach to the PAGE target, not the browser target

`/json/version` gives a `webSocketDebuggerUrl`, but that socket is
**browser-level** — it has no `Page` domain, and `Page.enable` / `Page.navigate`
fail with `'Page.enable' wasn't found`.

Enumerate targets and pick the page:

```js
const list = await (await fetch(`http://127.0.0.1:9344/json/list`)).json();
const page = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
const ws = new WebSocket(page.webSocketDebuggerUrl);
```

If the page list is empty, poll for a few seconds — a just-launched browser needs
a moment to open its first target.

## Message encoding is runtime-specific

A plain JSON command/reply client over the raw socket:

```js
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => {
  // Bun hands you a Buffer, browsers/node ws hand you a string.
  const raw = typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString('utf8');
  const m = JSON.parse(raw);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise((res) => {
  const i = ++id; pending.set(i, res);
  ws.send(JSON.stringify({ id: i, method, params }));
});
```

The `Buffer.from(...)` decode is not cosmetic: without it every reply is
silently dropped and the client hangs on the first `send` with no error.

## Evaluate

```js
await send('Runtime.enable');
await send('Page.navigate', { url });
await sleep(12000);                       // SPA boot: wait, do not poll blindly
const r = await send('Runtime.evaluate', {
  expression, awaitPromise: true, returnByValue: true,
});
console.log(r.result.value);
```

- Set `returnByValue: true` and return a **small JSON projection**, never the
  whole DOM.
- Check `r.exceptionDetails` before reading `r.result.value`.
- Wrap multi-statement work in an IIFE: `(() => { ... })()`. A bare arrow
  function returns the function itself, uncalled.
- `Page.enable`, `Runtime.enable`, `Network.enable` must be called before their
  events/commands do anything useful.
- Capture `Runtime.exceptionThrown`, `Runtime.consoleAPICalled`, and
  `Log.entryAdded` to see why an app failed to boot; `Network.responseReceived`
  with `status >= 400` tells you *which* request broke it.

## CLI-shaped drivers

If a browser CLI is available, prefer it for interactive driving and keep the raw
CDP client for cases it cannot express:

```bash
npx agent-browser open "<url>"                 # navigate; prints title + url
npx agent-browser eval "document.title"        # one expression
npx agent-browser eval --stdin < script.js     # multi-line: avoid shell quoting
npx agent-browser eval -b "$(base64 -w0 f.js)" # same, base64
npx agent-browser close --all                  # reset a wedged session
```

`--stdin` / `-b` exist because newlines and quotes in a heredoc-style script get
mangled by the shell. When long evals time out, split into single-expression
calls and let the shell own the timing (`sleep` between calls).
