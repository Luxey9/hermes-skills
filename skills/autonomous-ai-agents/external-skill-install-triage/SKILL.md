---
name: external-skill-install-triage
description: Vet and install third-party skill repos into Hermes.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, install, triage, github, hermes-home]
---

# External skill install triage

Use when the user hands you one or more GitHub URLs and says "install these skills in Hermes".
The copy is the easy half; deciding WHAT each repo actually is, and what it costs in every future
session, is the half that gets skipped. Procedure first, archetypes and pitfalls after.

Companion: `install-external-skill-repo` covers the single-repo copy + park/unpark mechanics.
This skill covers batch intake: classify each repo before installing, copy the real payload,
account for the index cost, verify discovery.

## When to Use

- The user pastes one or more GitHub repo or file URLs and says "install these skills".
- You must decide whether a repo is a skill library, a plugin repo, or a tool distribution.
- You are about to add skills under `$HERMES_HOME/skills` and need the collision, layout, and
  index-cost checks done first.
- Don't use for: authoring a skill of your own, or in-repo `skills/` tree work
  (see `hermes-agent-skill-authoring`).

## Procedure

1. **Inventory and dedupe the list.** The user often pastes the same repo twice, or pastes a
   `.../blob/<ref>/.../SKILL.md` file URL when they mean the repo. Print the deduped list before
   touching anything.
2. **Clone every candidate into scratch**, one dir per repo named `<owner>_<repo>`:
   `git clone --depth 1 https://github.com/<owner>/<repo>.git <owner>_<repo>`.
   Completion: every repo has a working tree, or you have reported which clone failed.
3. **Classify each repo** with the table below. Do this BEFORE copying — most surprises here.
4. **List skills and check collisions in one pass.** Extract `<name>`/`<description>` from every
   `SKILL.md`, then test each name against the live index (`get_all_skills_dirs` +
   `iter_skill_index_files` + `parse_frontmatter` from `agent.skill_utils`). A name already in the
   index is a no-op or a silent overwrite — report it, install only the free names.
5. **Copy the payload** into one category dir of your choosing (see Layout). Copy by named subdir,
   never `cp -r <repo>/.` — that drags `.git` and drops files at the category root.
6. **Verify all three**, then report:
   - on-disk count: `find <dest> -name SKILL.md | wc -l`
   - discovery count == on-disk count (catches the wrapper-dir bug), and print each new name with
     its resolved path
   - `skill_view(<one new skill>)` — a real load proves the slug resolves
7. **Report the index cost** before declaring done: sum `<name>: <description[:60]>` for each new
   skill, chars ÷ 4 = tokens/session, paid in EVERY session's system prompt forever.
8. **State the session boundary.** The skill index is built once per conversation, so the new
   skills are visible in the NEXT session, not this one. Say it rather than letting the user
   wonder why `skill_view` misses them.

## Classify each repo first

| What the repo is | Signal | What to do |
|---|---|---|
| **Skill library** | several `<dir>/SKILL.md`, often under `skills/` | copy each skill dir |
| **Plugin-layout library** | `skills/<plugin-name>/` where the dir name == the skill `name` | copy the INNER dirs, not the wrapper |
| **Single-skill repo** | repo root holds `SKILL.md` + `references/` | copy the whole repo as the skill dir |
| **Tool distribution, not skills** | only `SKILL.md` is `install-<tool>`; payload is `.ts`/`.mjs`/assets | do NOT install. Report what it actually is (e.g. a lint-plugin installer) and ask |
| **Repo already in the index cache** | the name only appears in `skills/.hub/index-cache/*.json` | that is the registry's catalog, not an install. Check the filesystem before telling the user a skill is missing |
| **One file from a monorepo** | `github.com/<owner>/<repo>/blob/<ref>/<path>/SKILL.md` | `curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>/SKILL.md -o <dir>/SKILL.md` |

A repo whose only skill is an *installer* is a tool repo. Installing it into `$HERMES_HOME/skills`
puts an installer in the system prompt and gives the user nothing to invoke.

## Layout

- Unrelated repos each vendoring a differently-named skill → ONE category dir of your own,
  `skills/<domain>/<topic>/`, each skill a subdir. Predictable, one line in the catalog.
- Keep the repo's own category dir when the repo IS a categorized library (`cybersecurity/`).
- After copying a whole single-skill repo, move `README.md`, `LICENSE`, `CHANGELOG.md`, and the
  repo's `references/` INTO the skill dir. Verify before deleting anything:
  `diff -rq <root-references> <skill>/references` — a repo-root `references/` and the skill's own
  can hold the same filenames, and `mv` fails with "Directory not empty".

## Pitfalls

- **Do not rewrite frontmatter.** Hermes ignores unknown keys (`domain:`, `mitre_attack:`,
  `license:`, `allowed-tools:`, `disable-model-invocation:`). A skill carrying
  `disable-model-invocation: true` still enters the index; say so instead of "fixing" it.
- **A body that links bundled files is a copy contract.** If a skill's prose points at a
  reference file, a script, or a sibling skill dir, those must exist at the resolved relative
  path after the copy, or the skill loads and then dead-ends. Enumerate every relative link in
  the body and resolve each to a real path before you copy.
- **The installed skill's own `linked_files` list is the copy checklist.** Load each new skill
  once after installing and confirm its linked files resolve; a short list means the payload
  copy was partial.
- **A `SKILL.md` at the category root becomes a skill named after the folder.** Stray root files
  are not harmless — move them into the skill dir.
- **`hermes skills list`'s last line is `N hub-installed, N builtin, N local — …`.** The `local`
  count is the one that must grow by the install count; do your own total with the discovery
  snippet, since the printed totals do not equal what the loader sees.
- **No `python3` on Windows Hermes hosts** — use `python`. Native tools reject MSYS `/c/...`;
  pass `C:/...` forward-slash paths. Run scratch work under `$HERMES_HOME/cache/scratch`.
- **Large repo → sparse clone** (`--filter=blob:none --sparse` + `git sparse-checkout set skills`)
  before blaming the network.

## Report shape

Table of repo → skill name → installed path, then: the skipped repo with its reason, the verified
counts, the token cost, and the session-boundary note. Offer the park/unpark toggle as a one-liner
(see `install-external-skill-repo`) rather than describing it.

## After install: consolidating into fewer skills

A follow-up ask is common ("jadikan satu skill", "merge these into one"). Two shapes, and the
difference decides the procedure:

- **Siblings from one repo** (one core SKILL.md + optional add-on skills): core keeps its path and
  its frontmatter (rewritten broad); each sibling becomes `references/<concern>.md` with the
  frontmatter stripped and its H1 kept; write `references/INDEX.md` + a load-when table at the end
  of SKILL.md; delete the sibling dirs. Rewrite the siblings' cross-references — `other-skill/`,
  `antislop.md`, `${CLAUDE_SKILL_DIR}` all break after the move.
- **Unrelated tool folded into an existing skill**: since the parts were never siblings, the
  survivor gets the tool's scripts, its body as a `references/` file, its LICENSE as
  `LICENSE-<tool>`, plus a routing row.

Always re-derive names after any shuffle: a stray file left at the category root becomes a skill
named after the folder, and a duplicated dir under two category levels yields duplicate names.
Assert `unique(name) == file_count` and diff the name set against the pre-change set to prove only
the intended entry disappeared.

## Hiding / freezing a skill you cannot uninstall

`hermes skills uninstall` removes ONLY hub-installed skills. Bundled and local skills are hidden by
moving them out of `$HERMES_HOME/skills`, and a builtin needs its seed copy moved too:
`$HERMES_HOME/hermes-agent/skills/` holds the same skill (often an older revision) and re-seeds on
update. Park both under `<external-skills>/<category>/` with `skills.external_dirs` left unset, and
say the move is reversible with one `mv`.

## Extending a shipped integrity gate

Some skills authenticate their own package (an `attribution_guard.py` subclass: exact frontmatter
regexes, a license sha256, AST checks that every route script keeps a live guard call). Fold
anything into such a skill and the gate exits non-zero on its next real run, killing the skill at
load-order step 2.

- Add only existence checks (`_REQUIRED_VENDORED_FILES`, an extra attribution filename) and the
  `all(... .is_file())` clause inside the existing check function.
- Never add a hand-written vendored path to the list of files whose AST is inspected for a guard
  call — those contain no such call and the gate fails every run.
- Re-run the gate after each edit; a stray newline turns an added tuple into a string-tuple bug.
- Run a negative control: move one vendored file aside, confirm the gate FAILS, restore, confirm it
  PASSES. A gate that has only ever passed may be passing without your check in it.
- Leave what it authenticates untouched (copyright, license digest, official_repository) and tell
  the user the install is no longer a byte-for-byte official distribution, with its self-updater
  dead.
