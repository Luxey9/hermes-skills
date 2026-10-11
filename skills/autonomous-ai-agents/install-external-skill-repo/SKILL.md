---
name: install-external-skill-repo
description: "Install a third-party agent-skill repo into Hermes."
metadata:
  hermes:
    tags: [skills, install, github, agentskills, external]
---

# Install an external skill repo into Hermes

Use when the user points at a GitHub repo of skills (agentskills.io / Claude-plugin layout)
and says "install these in Hermes".

## Recon first (never blind-copy)

```bash
git clone --depth 1 <repo>            # add --filter=blob:none --sparse + `git sparse-checkout set skills` for big repos
find <repo> -name SKILL.md | head    # locate the real skills root
```

Decide three things before copying:

1. **Skills root** — often `skills/`, but Claude-plugin repos nest it (`skills/<plugin>/`).
   Only the directory holding the `SKILL.md` dirs counts.
2. **Discovery depth** — Hermes `os.walk`s `$HERMES_HOME/skills` recursively and treats any dir
   containing `SKILL.md` as a skill. A wrapper dir (`skills/ppt-master/`) is harmless. But a
   `SKILL.md` ABOVE the real root collapses the whole tree into one skill — check with
   `find <repo> -name SKILL.md -not -path "<repo>/skills/*"`.
3. **Index cost** — measure BEFORE installing. Every skill's `<name>: <desc[:60]>` line enters
   the system prompt of every session. Sum it and report the real token cost to the user; for a
   large library offer a trimmed subset or `skills.disabled` instead of the full dump.

## Turn an install OFF / ON (external dir)

Zero-cost parking: move the category out of `$HERMES_HOME/skills` and list its parent as an
external dir. Config is the ONLY switch — an empty/absent `skills.external_dirs` means the parked
skills are not discovered at all.

```bash
H="$HERMES_HOME"
mkdir -p "$H/external-skills" && mv "$H/skills/<category>" "$H/external-skills/"   # park (OFF)
hermes config set skills.external_dirs '["external-skills"]'                      # ON
hermes config unset skills.external_dirs                                           # OFF again
```

Rules that bite:

- The value MUST be JSON-array-as-string (`'["external-skills"]'`). A bare string is rejected by
  `hermes config set`; relative entries are anchored at `$HERMES_HOME`, so do NOT write
  `~/external-skills` — `~` expands to the OS home (`C:/Users/<user>/external-skills`) and the dir
  silently does not exist.
- Takes effect in a NEW session: the skill index is built once per conversation.
- Toggling OFF needs no restart and costs nothing: verified 892 skills / ~24.0k index tokens
  enabled vs 74 skills / ~1.4k tokens parked (818 security skills = ~22.6k tokens/session).
- Same parking works for ppt-master (`skills/productivity/ppt-master`, ~109 MB) and any other
  single skill — park just that dir.
- Verify the toggle in ONE command (discovery count must jump by the parked count):
  ```bash
  "$HERMES_HOME/hermes-agent/venv/Scripts/python.exe" -c "
  import sys,os; sys.path.insert(0,os.environ['HERMES_HOME']+'/hermes-agent')
  from agent.skill_utils import get_all_skills_dirs, iter_skill_index_files
  d=get_all_skills_dirs(); print(len(d),'dirs',sum(len(list(iter_skill_index_files(x,'SKILL.md'))) for x in d))"
  ```

## Install

```bash
dest="$HERMES_HOME/skills/<category>"   # category = folder shown in skills_list
mkdir -p "$dest" && cp -r <repo>/<skills-root>/. "$dest"/
```

Keep the repo's own category dir as the Hermes category (e.g. `cybersecurity/`, `productivity/`).
Do NOT rewrite frontmatter: Hermes ignores unknown keys (`domain:`, `mitre_attack:`, `license:`),
so agentskills.io files load as-is.

## Verify (all three)

```bash
hermes skills list | tail -2                          # "N local" must grow by the install count
find "$dest" -name SKILL.md | wc -l                   # on-disk count
```

Confirm discovery equals on-disk (catches the wrapper-dir bug):

```bash
"$HERMES_HOME/hermes-agent/venv/Scripts/python.exe" -c "
import sys,os; sys.path.insert(0,os.environ['HERMES_HOME']+'/hermes-agent')
from agent.skill_utils import get_all_skills_dirs, iter_skill_index_files
print(sum(len(list(iter_skill_index_files(d,'SKILL.md'))) for d in get_all_skills_dirs()))"
```

Finally `skill_view(name)` one installed skill — a real load proves the slug resolves.

## Dependencies

Scripts run with whatever `python` the skill invokes; Hermes' own venv
(`$HERMES_HOME/hermes-agent/venv`) is on PATH as `python` in terminal sessions. Install that
skill's `requirements.txt` into that venv, then run the skill's own integrity gate if it ships
one (e.g. `attribution_guard.py`) as the smoke test.

## Merge a multi-skill bundle into ONE skill

When the user wants a repo's N skills to appear as one entry (fewer index lines, one load):

1. Core skill = the SKILL.md the others defer to. Strip its frontmatter, delete its
   first-run install wizard (the block that offers to install the siblings), rewrite its
   frontmatter to a broad description, keep it at `skills/<cat>/<name>/SKILL.md`.
2. Siblings -> `references/<concern>.md` (frontmatter stripped, H1 kept). Their
   cross-references (`other-skill/SKILL.md`, `../other/`) are dead after the move: rewrite
   them to `references/<concern>.md`, since relative links resolve against the SKILL.md dir.
   Agent-specific path vars (`${CLAUDE_SKILL_DIR}`) break too: point them at the real path.
3. Supplementary files (scripts, extra references, templates) go to `scripts/` or
   `references/` in the merged skill. Write a `references/INDEX.md` mapping topic -> file,
   and a short table at the end of SKILL.md so the agent knows what to load and when.
4. Delete the sibling dirs and verify: discovery count drops by N-1, `skill_view(<name>, 'references/<file>.md')`
   resolves for each moved file, the merged skill's index line is one entry.

Do NOT merge skills that must load together for different triggers into references you lose
on-demand loading of - a reference only loads when the agent reads it. Merging trades
per-trigger index lines for a fatter core; fine when the siblings are rarely both needed,
wrong when they are separate work modes (UI vs code vs prose).

## Pitfalls

- No `python3` on Windows Hermes hosts — use `python`. Windows-native tools reject MSYS
  `/c/...` paths; pass `C:/...` forward-slash paths.
- `agent.skill_utils.parse_frontmatter` takes TEXT not a Path, and returns `(fm, body)`.
- Verify pip installs with `python -c "import X"`; a "cache deserialization" warning is benign.
- `.claude-plugin/plugin.json` metadata is irrelevant to Hermes; ignore it.
- The threat scanner flags offensive-security skills (`known_c2_framework`, `c2_explicit`) at
  `scope="context"`. Skill bodies are not context-scanned, so they load fine — but never run
  their scripts against a live target.
