---
name: hermes-state-inspection
description: "Use when inspecting/recapping Hermes sessions or projects."
version: 1.0.0
author: curator
license: MIT
platforms: [linux, macos, windows]
---

# Hermes State Inspection

Answer session/project questions from the live stores, not from memory.
CLI output first, SQLite second, source grep last.

## Procedure

1. Resolve the home for the active profile before touching any file.
   - Prefer `$HERMES_HOME`; fall back to `hermes config path`.
   - Profiles scope everything: `~/.hermes/profiles/<name>/` has its own `projects.db` and `state.db`.
2. Cross-check with CLI before opening a database.
   - `hermes project list` for project slugs and folder counts.
   - `hermes sessions list --workspace <needle>` filters sessions by workspace key (repo root, else cwd).
   - `hermes project show <slug>` for a single project's folders and primary path.
3. Query `projects.db` read-only for the project side.
   - Tables: `projects(id, slug, name, primary_path, archived, board_slug)`, `project_folders(project_id, path, label, is_primary)`, `project_meta(key, value)`.
   - `project_meta` key `active_id` is the currently active project only, never the owner of a session.
   - Open SQLite with `mode=ro` (URI read-only) so a live gateway is never locked.
4. Query `state.db` table `sessions` read-only for the session side.
   - Relevant columns: `id, title, source, cwd, git_repo_root, git_branch, session_key`.
   - There is no `project_id` column on sessions; the mapping is derived, not stored.
5. Map session to project by path prefix, in this order.
   - Prefer `git_repo_root` when set, else `cwd`.
   - A session belongs to the project whose `project_folders.path` equals or is a parent directory of that value (case-insensitive on Windows).
   - `cwd IS NULL` or a path outside every project folder means ungrouped: report it as a loose session, never force it into the active project.

## Session titles vs project names

- The Desktop chat header renders `sessions.title`, never the project name — a session inside a project folder still shows its own auto-generated title.
- Auto-titles derive from the first user message (`agent/title_generator.py`: instant `derived` slice, then an `llm` upgrade); the working directory and project membership never feed the title.
- A session starts with a chosen title only via an explicit `pending_title`: `/new <name>`, `/title <name>`, or the `title` param on `session.create`. The Desktop new-session path sends no title, so fresh sessions always auto-title.
- Rename any session with `hermes sessions rename <id> <title>`; a `user`-sourced title is never overwritten by the auto-titler, while `derived`/`llm` titles can still be replaced on turns 2-3.
- No config sources auto-titles from the project name; `auxiliary.title_generation.enabled: false` only disables auto-titling, it does not change its source.

## Resolve an `@session` link or scroll inside one

When the user pastes `@session:<profile>/<id>` (or asks "what about that chat
where we..."), resolve it with `session_search` — do not guess from memory.

1. Split the link on `/` into profile + id. Pass the id segment as
   `session_id` and the profile segment as `profile`.
   - `@session:default/20260101_120000_abcdef` → `profile="default"`,
     `session_id="20260101_120000_abcdef"`.
   - A link whose profile is the active one still works with `profile` set;
     set it anyway so a non-default link resolves instead of erroring.
2. `session_id` alone returns first ~20 + last ~40 messages with
   `truncated: true` — enough to name the topic and find where it stopped,
   not enough to recap the arc.
3. To reach the middle, scroll: `session_id` + `around_message_id` + `window`
   (clamped 1–20, default 5). Anchor only on a real id from a window you
already received.
   - The window reports `messages_before` / `messages_after`; when either is 0
     you have hit that end. Re-anchor on the FIRST id to walk backward, the
     LAST id to walk forward; the boundary message repeats as an orientation
     marker.
4. Read the whole thing in one call only when you need a full recap — the
   store read in the section above is cheaper than many scroll windows.

## Recap a whole session from the store

`session_search` with `session_id` alone hydrates only the first ~20 and last
~10 messages of a long session (it reports `truncated: true`) — enough to name
the topic, not to recap the arc. For a full recap, read the store directly:

```python
con = sqlite3.connect(f"file:{home}/state.db?mode=ro", uri=True)
rows = con.execute("select id, role, content, active, compacted"
                   " from messages where session_id=? order by id", (sid,))
```

- Keep `user` + `assistant` rows only; `tool` rows are most of the volume and
  none of the arc. Truncate assistant messages (~300 chars), keep user messages
  whole, join into a scratch text file, then `read_file` it in one or two
  passes. Never paste the raw dump into the reply.
- `sessions.message_count` counts tool calls too — user turns are a small
  fraction of it (a 600-message session can hold ~25 user turns).
- Compacted history is replayed verbatim inside later context messages, so the
  same turn can appear twice — merge duplicates instead of reporting repeated
  work that only happened once.
- `user`-role rows also carry injected notices (background-process completions,
  model-changed banners, compaction summaries). Never attribute those to the
  person; report only what they typed.

## Pitfalls

- Quote Windows home paths on every shell call — an unquoted space splits the path into fake arguments and the lookup fails for syntax reasons, not missing data.
- Scope recursive source searches to one subdirectory with a tight pattern — a full-tree grep over the Hermes source times out before returning, so narrow first, then widen only on zero hits.
- Open `state.db` and `projects.db` read-only on every inspection — the gateway holds write locks while running and a read-write open can block or corrupt live state.
- Never treat `project_meta.active_id` as session ownership — it names the selected project in the UI while each session maps independently through its own working directory.
- Anchor scroll windows only on a message id that appeared in a previous
  `session_search` result — ids computed by adding to an existing id are
  rejected as `not in session_id`, and a linear guess can walk past the end of
  a sparse id space and return an out-of-session anchor. If an anchor is
  refused, re-scroll from the END id of the last window you actually received.
- Never report a session's ending from truncated output alone — read the tail
  with a scroll window first; a session can stop mid-tool-call and look
  finished in the hydrated head.
 — without an explicit `/new <name>` or a manual rename, every fresh session auto-titles from its first message.
