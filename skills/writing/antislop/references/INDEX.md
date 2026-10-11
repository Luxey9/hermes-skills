# Slop reference library

Merged from six upstream repos. Core rules are in `../SKILL.md`; the rest load on demand.

| File | Source | Load when |
|---|---|---|
| `ui.md` | miqdadbadjuber/anti-slop | building or editing UI, color, components, motion |
| `copywriting.md` | miqdadbadjuber/anti-slop | writing/editing copy, headlines, CTAs, product prose |
| `human.md` | miqdadbadjuber/anti-slop | accessibility: contrast, keyboard, focus, states |
| `layoutmobile.md` | miqdadbadjuber/anti-slop | layout must reflow phone to desktop |
| `code.md` | miqdadbadjuber/anti-slop | code comment hygiene, never touches logic |
| `no-ai-slop.md` | petergyang/no-ai-slop | editing a draft, preserving the writer's voice, slop detection |
| `stop-slop.md` | hardikpandya/stop-slop | prose editing; `stop-slop-phrases.md`, `stop-slop-structures.md`, `stop-slop-examples.md` |
| `unslop.md` | cursor/plugins (pstack) | fast pass over text, AI-tell checklist |

`scripts/contrast-check.py` computes WCAG contrast ratios; `scripts/contrast-mcp.py` exposes it as an MCP server.
Both come from miqdadbadjuber/anti-slop v3.2.20.
