---
name: bulk-file-cleanup
description: "Use when asked to delete or clean up files in bulk."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cleanup, deletion, files, git, safety, irreversible]
    related_skills: [codebase-inspection, github]
---

# Bulk File Cleanup

## Overview

"Delete the leftover testing files" is an irreversible operation on a directory
the user has been building for months. The value you add is a **classified,
approved inventory** — not the speed of the delete. Deletion is the last step,
not the first, and the user sees the list before anything is removed.

## When to use

- "Delete the files left over from testing."
- "Clean up my <directory>."
- "Remove the junk / leftovers / backups."

Also read this before any command whose argument contains a **wildcard** —
`rm -rf _*`, `rm *_backup*`, `find . -name '*.bak' -delete`, `git clean -fdx`.
A glob is not an inventory.

## The gate — inventory, approve, then delete

1. **Enumerate, do not delete.** List the candidates with size and mtime and sort
them into classes:

   ```bash
   ls -la --time-style=+%Y-%m-%d          # top level, with sizes and dates
   ```

   Build the class list in Python or a loop — never in your head — and print a
   count per class. `du -sh .` on a large tree times out (it walks
   `node_modules`), so size the *targets* instead: `du -ch <files>` or
   per-directory `du -sh`.

2. **Present the inventory and stop.** Group by class, state the total count and
   size, and say what is irreversible. Ask for approval **per class**, so the user
   can keep some. A prior "go ahead and clean it up" is approval of the *class you
   described*, never of whatever the glob happens to match.

3. **Delete one class at a time**, reporting each result, so a mistake is bounded
   and visible.

## Classify before proposing anything

| class | test | delete? |
| --- | --- | --- |
| Probe/dump artefacts | `_*.txt`, `_*.json`, `_oNN.txt`, scratch workspaces | Usually yes — say they are rebuildable if you name the command |
| Build/cache output | `dist/`, `__pycache__`, `*.log` | Yes, regenerable |
| Credential-bearing dumps | `_tokens.json`, `_keyhunt.txt`, dumps holding `password_hash` | **No — hand to the user first.** They are evidence for a rotation decision |
| Git-tracked files | present in `git ls-files` | Never without an explicit instruction; deletion leaves staged removals |
| `docs/`, `supabase/migrations/`, `src/`, `api/` | — | Never — the audit trail |
| `.env*`, keys, OAuth/telemetry files | — | Never |
| A directory containing `.git` | `ls -d <dir>/.git` | Never — a nested clone with its own uncommitted work |

Run the two cheapest checks against every candidate that lives in a repo:

```bash
cd <repo> && git ls-files <path>              # non-empty => tracked => recoverable, and a change to be committed
cd <repo> && git status --porcelain <path>    # ?? => untracked => deleting it is PERMANENT
```

A directory the user calls "junk" routinely contains a nested `.git`. Treat a
`.git` inside a candidate as a stop sign, not a detail.

## Never delete by pattern

`rm -rf _*` also removes `_audit_ws/`, `_notes/` — anything whose name starts
with the character that happens to prefix the junk. Expand the pattern into an
explicit list first and pass that list, or delete the classes one by one. If you
cannot enumerate what the pattern matches, you do not know what you are deleting.

The pattern trap and the credential-dump class overlap **by construction**: the
files you must never delete unilaterally (`_tokens.json`, `_keyhunt.txt`, a
`_users_probe` dump holding `password_hash`) are exactly what a `_*` glob matches,
so one pattern delete takes the evidence a rotation decision needs along with the
junk — and the user is left unable to answer "did that dump contain a working
credential?". Enumerate per class precisely because the interesting classes hide
inside the disposable-looking one.

## `rm` is not reversible here

A delete issued from a POSIX shell (git-bash/MSYS, WSL, `rm`) **bypasses the
Recycle Bin** — there is no undo. Check the safety net *before* deleting, not
after:

```bash
ls -la /c/\$Recycle.Bin/*/            # did anything actually land there?
ls -d ~/OneDrive ~/AppData/Local/Microsoft/Windows/FileHistory
```

Shadow copies / restore points need elevation (`vssadmin list shadows`,
`Get-ComputerRestorePoint` both fail unelevated), so do not promise they exist.
Anything not in a git repo and not synced has **no** recovery path — say so
plainly rather than offering "we can probably get it back".

## Verify after

- Repos still intact: `git rev-parse --short HEAD`, `git ls-files | wc -l`,
  `git status --short` — the tracked-file count is the number to compare.
- Sibling directories and their working-tree changes untouched.
- Anything you promised was rebuildable: state the exact command to rebuild it, or
  do not claim it.

## When it has already gone wrong

Stop deleting immediately and lead with the inventory of what was removed, class
by class, with what is rebuildable versus gone. Do not re-argue the decision, do
not propose more deletions in the same message, and do not keep exploring the
directory. Then check the real recovery surface and report it honestly: Recycle
Bin (usually empty for a shell `rm`), OneDrive/File History, and whether
credential-bearing dumps were among the losses — that last one is a security
decision for the user, not a cleanup detail.

## Pitfalls

- **A pattern is not a plan.** Enumerating first is what separates a cleanup from
  an incident; approval was given against a list you showed, never against "the
  leftovers".
- **Deleting a credential dump destroys the user's own audit.** Token pipelines,
  password-hash dumps and key-hunt output may contain live credentials; deleting
  them silently removes the evidence that a rotation is needed. Hand them over,
  flag what they contained, and let the user decide.
- **"Rebuildable" is a claim you have to be able to satisfy.** Name the command
  (`GET /rest/v1/` with the service key, re-fetch the bundle from the live URL) in
  the same message as the proposal, or the user cannot weigh the trade.
- **A deep git-bash scan over a whole tree hangs.** `du -sh .`, `find . -type f`
  and `ls -R` walk `node_modules`; scope every command to the directory in
  question and use a timeout.
- **Do not "tidy" a repo without asking.** Untracked files that look like debris
  are often the only copy of work in progress, and `git status` noise is not the
  same as garbage.
