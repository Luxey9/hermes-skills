# A/B testing your build against the deployed one

You changed the front end. The browser under test loads whatever is deployed. If
the deploy has not caught up, the site reproduces the bug you just fixed and every
conclusion you draw is about the wrong code.

## Confirm which bundle is live

```bash
curl -s https://<host>/ | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js' | head -1
```

Compare with the filename your local build just emitted. Different hash = the
deployed code is not your code. Either wait for the deploy, or serve your own
build (below) and test against that.

For the same reason, when reporting to the user: name the bundle hash you tested.
It is the only unambiguous answer to "which code did you verify?".

## Serve your own build, with the app's API proxied

The app's client-side calls (`/api/...`) do not exist in your static build. Proxy
them to the real host so the page behaves like production while running your code.

A minimal static server plus proxy:

- serve files from `dist/`;
- `index.html` fallback for unknown paths (SPA routing);
- forward `/api/*` to the production origin, preserving method, headers, and body.

Shelling out to `curl` for the proxied request is the reliable variant — a
runtime's `fetch` may reject the upstream TLS certificate, and per-request TLS
overrides are not always honoured by the HTTP client. `curl` is.

```js
const proc = Bun.spawnSync(['curl', '-sS', '-X', req.method, UP + url.pathname + url.search]);
return new Response(proc.stdout, { headers: { 'content-type': 'application/json' } });
```

Keep server output out of the conversation: some servers print a full-page HTML
error overlay on a failed request, which floods the transcript. Redirect to a file
and read back only the line you need.

## Enter a logged-in state without a login form

Driving the login UI is slow and often blocked. If the app issues its own session
token, you can mint one directly:

1. sign a JWT with the app's own signing secret using the claims the app expects;
2. POST it to the app's own token-exchange endpoint;
3. store the returned token where the client reads it (commonly `sessionStorage`).

Send it as a query parameter if the app accepts `?token=` on entry — that path
also proves the app's own token intake works.

Treat the minted token as a credential: keep it in the scratch directory, never
paste it into the conversation, and never write it into the repo.

## Compare deployed vs local on the identical scenario

Run the **same** reproduction script against both, back to back, and diff the
snapshots. Running it against local only proves your machine works; running it
against deployed only proves the old code was broken. The pair is the evidence.
