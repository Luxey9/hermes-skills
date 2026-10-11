# Schema and Commands

## Canonical schema

```yaml
hooks:
  pre_tool_call:
    - matcher: "<optional regex, tool-call events only>"
      command: "<single shell string, required>"
      timeout: 10          # optional; default 60, capped at 300
      fail_closed: false   # optional; pre_tool_call only
  post_tool_call:
    - command: "<single shell string>"
      timeout: 10

hooks_auto_accept: false  # true skips the first-use TTY prompt
```

Event names must match a known hook event; typos are skipped with a
"did you mean" warning. Unknown keys inside an entry are ignored, but a
missing `command` skips the entry.

Validate event names before writing config — `hermes hooks test <name>`
on an unknown event prints the full valid event list. Use that list as
the oracle; never guess an event name from a pasted snippet.

Common intent-to-event mapping (verify against the oracle, it grows):
chat-without-tool-calls ("message end") is `on_stream_end`, not
`on_message_end`; session lifecycle is `on_session_start` / `on_session_end`;
subagent lifecycle is `subagent_start` / `subagent_stop`.

## Known-good forwarding command

```
curl -s -m 5 -X POST http://127.0.0.1:3456/hook -H "Content-Type: application/json" -d @-
```

Hermes pipes the JSON event payload to stdin (`-d @-`) and reads stdout
back as JSON. The receiver's normal reply (e.g. `{"ok":true}`) parses as
`<none>` — an observer no-op — which is the success shape for forwarders.

## CLI set (in order)

```bash
hermes config get hooks
# value uses outer single quotes, inner doubles escaped:
hermes config set 'hooks.pre_tool_call' '[{"command": "curl -s -m 5 -X POST http://127.0.0.1:3456/hook -H \"Content-Type: application/json\" -d @-", "timeout": 10}]'
hermes config set 'hooks.post_tool_call' '[{"command": "curl -s -m 5 -X POST http://127.0.0.1:3456/hook -H \"Content-Type: application/json\" -d @-", "timeout": 10}]'
hermes hooks list
hermes hooks doctor
hermes hooks test pre_tool_call
```

## Consent and test interpretation

- `hermes hooks list` shows `not allowlisted` until the hook is approved
  once (TTY prompt or a run with `--accept-hooks` / `HERMES_ACCEPT_HOOKS=1`)
  plus a fresh session; `hooks_auto_accept: true` covers headless hosts.
- `hermes hooks test <event>` must show `exit=0` and the receiver's body
  in `stdout`. `parsed: <none>` means the hook contributed no block or
  modify directive — correct for pure observers.
- Probe the receiver independently first:
  `curl -s -m 5 -X POST http://127.0.0.1:3456/hook -H "Content-Type:
  application/json" -d '{"probe":true}'` must return HTTP 200.
