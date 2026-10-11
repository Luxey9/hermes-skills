---
name: hermes-shell-hooks
description: "Use when configuring Hermes shell hooks in config.yaml."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, hooks, configuration]
    related_skills: [hermes-agent]
---

# Hermes Shell Hooks

## When to Use

Any task that declares, edits, or debugs shell hooks under `hooks:` in the
active profile's `config.yaml` — pre/post_tool_call forwarding to a local
HTTP receiver, audit loggers, auto-formatters — or that interprets
`hermes hooks list / doctor / test` output.

Use this whenever declaring or changing shell hooks under `hooks:` in the
active profile's `config.yaml` (typically `pre_tool_call` / `post_tool_call`
forwarding to a local HTTP receiver, audit loggers, or formatters).

## Procedure

1. Probe the receiver before wiring anything — POST a probe payload with
   curl and require HTTP 200 plus the expected body before touching config.
2. Read the current state with `hermes config get hooks` and
   `hermes hooks list` so the edit merges rather than clobbers.
3. Normalize any pasted snippet to the schema in
   `references/schema-and-commands.md` first, then write it with
   `hermes config set` — never hand-edit `config.yaml` (a stray indent can
   corrupt the live gateway config).
4. Verify with `hermes hooks list`, `hermes hooks doctor`, and
   `hermes hooks test <event>`; the receiver must show the test delivery.
   Report real test output, never a claim without it.
5. Handle consent: hooks need first-use approval. Set
   `hooks_auto_accept` or approve once via a TTY / `--accept-hooks` run;
   a new session is required before allowlist status refreshes.

## Always-on rules

- `command` is ONE shell string run via shlex.split with `shell=False` —
  never an argv array. Convert pasted arrays to a single string.
- Strip paste artifacts from URLs (`@url:` prefixes, backticks, markdown
  link wrappers) down to the plain `http://host:port/path` before saving.
- Quote every header inside the command: `-H "Content-Type:
  application/json"`. An unquoted header splits into extra argv items and
  the hook fails (curl exit 6) while the server still looks healthy.
- On Windows git-bash, wrap the `hermes config set` value in outer single
  quotes and escape inner double quotes; verify with `hermes config get`.
- A `doctor` line saying "script missing or not executable" is expected
  for inline commands such as `curl ...` (that check targets script
  files). Trust `hermes hooks test` over that warning when the test
  delivers with exit 0.
- In test output, `parsed: <none>` on an observer hook means success
  (no block/modify directive contributed), not failure — confirm via
  exit code plus the receiver's response body.
- Keep hooks fail-open (the default) for observability forwarding; use
  `fail_closed: true` only for genuine security gates on `pre_tool_call`.
- Keep the casual/normalized field names the receiver actually emits
  (`kind`, `sessionId`/`session_id`, `tool`, `text`) in the normalizer's
  accepted vocabulary — hook producers send mixed casings and a normalizer
  that only reads one casing silently misroutes events (e.g. everything
  falls back to a single default session).
- When the receiver serves both SSE and static files, test with a fresh
  subscriber AFTER sending events: a broadcaster with no backlog replays
  nothing to late joiners, which looks exactly like 'events not arriving'.
  Require backlog replay (capped, e.g. 200) before blaming the hook sender.
- Never derive a display name from `tool_input.command` free text: a bare
  command (`echo halo`) splits into innocent-looking words that pass every
  naive filter and become the visible project. Only extract file paths with
  extensions from commands; discard a command with no path in it entirely.
- Drop numeric/IP/port segments from path mining (`3456`, `127.0.0.1:port`):
  URLs inside commands split on `/` into segments that look like names.
  Reject all-digit, dotted-quad, and host:port segments explicitly.
- Lock display identity per session (first valid name wins): once a session resolves to a real project, remember it and ignore later path-less or null events — a later event with no location must never overwrite a good name with a fallback word.
- Treat hook `cwd` as the sender process directory, not the session home:
  it is frequently the user home or launcher dir. Resolve display identity
  by session id against the session store (`SELECT cwd FROM sessions
  WHERE id=?`) as fallback, then basename that — never the raw hook cwd.
- In ESM (`.mjs`) receivers, `require` does not exist: load `node:sqlite`
  once at the top via `createRequire(import.meta.url)`, never with a
  dynamic `await import` inside a sync normalizer (syntax/runtime failure).
  Resolve the store path from `HERMES_HOME` with `%LOCALAPPDATA%/hermes`
  and `%USERPROFILE%/AppData/Local/hermes` fallbacks — a manually started
  receiver often runs without the env var set.

## References

- `references/schema-and-commands.md` — canonical schema, quoting pattern,
  CLI command set, and consent/test interpretation notes.
