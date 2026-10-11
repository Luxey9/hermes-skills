---
name: hermes-state-inspection
description: "Use when mapping Hermes sessions to projects."
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

## Pitfalls

- Quote Windows home paths on every shell call — an unquoted space splits the path into fake arguments and the lookup fails for syntax reasons, not missing data.
- Scope recursive source searches to one subdirectory with a tight pattern — a full-tree grep over the Hermes source times out before returning, so narrow first, then widen only on zero hits.
- Open `state.db` and `projects.db` read-only on every inspection — the gateway holds write locks while running and a read-write open can block or corrupt live state.
- Never treat `project_meta.active_id` as session ownership — it names the selected project in the UI while each session maps independently through its own working directory.
- Never promise project-named sessions by default — without an explicit `/new <name>` or a manual rename, every fresh session auto-titles from its first message.
