---
name: llm-council
description: "Pressure-test a decision with 5 advisors and a verdict."
version: 1.0.0
author: Ole Lehmann (@olelehmann) + tenfoldmarc, merged & ported by Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [council, decision, debate, multi-perspective, delegate, verdict]
    related_skills: [parallel-subagent-builds, requesting-code-review]
---

# LLM Council

One question in, five independent perspectives out, then anonymized peer review, then a
chairman's verdict that says where the council agrees (high-confidence signal — advisors
converged independently), where it clashes (genuine tradeoff), what blind spots the review
round caught, a real recommendation, and the single next step.

This is not "ask the model five times." The value is the two things a single answer cannot
give you: **independent angles** (no anchoring) and **anonymized peer review** (reviewers
judge merit, not author). On a single model this approximates Karpathy's multi-model council
by using different *thinking lenses* per subagent.

Adapted from [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council) via
[aiwithremy/claude-skills-llm-council](https://github.com/aiwithremy/claude-skills-llm-council)
(Ole Lehmann) and [tenfoldmarc/llm-council-skill](https://github.com/tenfoldmarc/llm-council-skill)
(which adds the visual report + saved transcript). This port retargets both to Hermes.

## When to Use

Trigger phrases: `council this`, `run the council`, `war room this`, `pressure-test this`,
`stress-test this`, `debate this`. Also trigger when the user presents a real decision with
stakes *and* several options: `should I X or Y`, `which option`, `which positioning angle`,
`is this the right move`, `validate this`, `get multiple perspectives`, `I can't decide`,
`I'm torn between`.

Don't use for: yes/no questions with one right answer, factual lookups, create-a-thing tasks
("write me a tweet"), summarize-this tasks, or a casual `should I` with no real tradeoff.
If the user already knows the answer and wants validation, the council will say things they
don't want to hear — that is the feature. If nothing is genuinely uncertain, just answer.

## Prerequisites

- `delegate_task` available (the council spawns 5 advisor children, then 5 reviewer children).
- The desktop app for the inline HTML report, if you want the visual (see step 5); on other
  surfaces fall back to chat markdown.
- The council is model-agnostic. It runs on the active model — no extra API keys.

## Procedure

1. **Frame the question (with context enrichment).** Before framing, spend no more than a
   minute scanning for context that would make the advisors' answers specific instead of
   generic:

   - `search_files(pattern='.hermes.md|HERMES.md|AGENTS.md|CLAUDE.md', target='files')` for
     project rules/preferences; `read_file` the ones that matter.
   - `search_files` for a `memory/` folder, audience/voice/business docs, past decision notes,
     and prior `council-transcript-*.md` in the workspace (so you don't re-council the same ground).
   - Any file the user attached or named.

   Then reframe as one neutral prompt containing: (a) the core decision, (b) key context from
   the user's message, (c) key context pulled from those files, (d) what's at stake. Do not
   add your own opinion and do not steer it — but give each advisor enough to be specific.
   If the ask is too vague ("council this: my business"), ask exactly one clarifying question,
   then proceed. Save the framed question for the transcript.

   *Completion:* you have a framed question with the four parts, or one clarifying question is out.

2. **Convene the council — all 5 advisors in ONE `delegate_task` call** (a `tasks` array of 5,
   not five separate calls; separate calls get truncated to the concurrency cap). Each child
   gets its advisor identity + lens, the framed question, and the instruction to lean fully
   into its angle — no hedging, no balance (the other advisors cover what it doesn't). Target
   150–300 words each, no preamble.

   > Fail-fast check: the batch of 5 needs `delegation.max_concurrent_children >= 5`
   > (`hermes config get delegation.max_concurrent_children`; the loaded default is 10).
   > If it's below 5, raise it with `hermes config set delegation.max_concurrent_children 10`
   > or run the council sequentially in two rounds.

   Child prompt template (fill the bracket):

   ```
   You are [Advisor Name] on an LLM Council.

   Your thinking style: [advisor description]

   A user has brought this question to the council:
   ---
   [framed question]
   ---

   Respond from your perspective. Be direct and specific. Don't hedge or try to balance.
   Lean fully into your assigned angle. The other advisors cover the angles you don't.
   Keep your response between 150-300 words. No preamble. Go straight into your analysis.
   ```

   *Completion:* 5 advisor responses collected, each 150–300 words and on-lens.

3. **Anonymize.** Relabel the 5 responses **A–E** with the mapping randomized (so no reviewer
   can infer "the Contrarian is always Response A" and defer positionally). Keep the mapping
   private until step 4.

   *Completion:* you have a private map `{advisor -> letter}` and A–E text blocks.

4. **Peer review — 5 reviewers in ONE `delegate_task` call.** Each reviewer sees the framed
   question and all five anonymized responses and answers three questions: which is strongest
   and why; which has the biggest blind spot and what it is; what did *all five* miss. Under
   200 words, direct, reference responses by letter. Keep the advisor identities out of the
   reviewer prompts — that's the whole point of anonymization.

   Reviewer prompt template:

   ```
   You are reviewing the outputs of an LLM Council. Five advisors independently answered
   this question:
   ---
   [framed question]
   ---

   Here are their anonymized responses:

   **Response A:**
   [response]

   **Response B:**
   [response]

   **Response C:**
   [response]

   **Response D:**
   [response]

   **Response E:**
   [response]

   Answer these three questions. Be specific. Reference responses by letter.

   1. Which response is the strongest? Why?
   2. Which response has the biggest blind spot? What is it missing?
   3. What did ALL five responses miss that the council should consider?

   Keep your review under 200 words. Be direct.
   ```

   *Completion:* 5 reviews collected; then de-anonymize (which letter was which advisor) for
   the chairman.

5. **Synthesize the verdict.** You (the parent) are the chairman — one synthesis, the same
   model that ran the council, using the framed question, all 5 de-anonymized responses, and
   all 5 reviews. Follow the structure exactly. The chairman may disagree with the majority
   when the reasoning supports it and must say why. No "it depends," no "consider both sides."

   ```
   ## Council Verdict: {short topic}

   ### Where the Council Agrees
   {points multiple advisors reached independently — high-confidence signal}

   ### Where the Council Clashes
   {genuine disagreements; present both sides and why reasonable advisors differ}

   ### Blind Spots the Council Caught
   {what only surfaced in the peer review}

   ### The Recommendation
   {one clear, direct recommendation with reasoning}

   ### The One Thing to Do First
   {a single concrete next step}
   ```

   *Completion:* a filled verdict where every section names advisors, not vague "some advisors."

6. **Deliver it.** Two artifacts:
   - **Chat:** the verdict inline as markdown — the user reads it in the conversation. Keep it
     scannable with bullets.
   - **Visual (desktop):** write a self-contained HTML report and render it inline with a
     `::preview{file="..."}` line (this is how the Hermes desktop app shows it — it does **not**
     need to be opened by hand). Report contains: the question, the verdict up top (most people
     read only that), a compact agree/clash visual, collapsed `<details>` sections with each
     advisor's full response, a collapsed peer-review section, and a footer with timestamp and
     topic. Use the frame's CSS vars (`var(--foreground)`, `var(--border)`, `var(--card)`, …),
     no own background/margins — only a standalone page overrides them. On non-desktop surfaces
     fall back to the markdown verdict alone.

   *Completion:* the verdict is in chat, and on the desktop the report renders (or you said why not).

7. **Save the transcript.** Write `council-transcript-<timestamp>.md` next to the report (or
   the user's workspace / scratch dir). Include: the original question, the framed question,
   all 5 advisor responses, all 5 peer reviews with the anonymization mapping revealed, and
   the chairman's synthesis. It's the artifact that lets a future session see how the thinking
   evolved and avoids re-counciling the same question.

   *Completion:* the transcript file exists and holds all five sections.

## The five advisors

Thinking lenses that manufacture tension — not job titles.

1. **The Contrarian** — hunts what's wrong, missing, or will fail. Assumes the idea has a fatal
   flaw and digs for it. Not a pessimist: the friend who asks the question you're avoiding.
2. **The First Principles Thinker** — ignores the surface question and asks "what are we actually
   solving?" strips assumptions, rebuilds from zero. May conclude you're asking the wrong question.
3. **The Expansionist** — hunts upside others miss: what could be bigger, what adjacent
   opportunity is hiding, what's undervalued. Ignores risk (the Contrarian owns that).
4. **The Outsider** — zero context about you, your field, or your history. Catches the curse of
   knowledge: things obvious to you and confusing to everyone else. Most underrated lens.
5. **The Executor** — only cares if it can be done and the fastest path. Thinks "OK, what do you
   do Monday morning?" A brilliant idea with no first step gets called out.

Why these five: three natural tensions — Contrarian vs Expansionist (downside vs upside),
First Principles vs Executor (rethink everything vs just do it), Outsider keeping everyone
honest from the middle.

## Pitfalls

- **Splitting the advisors into separate `delegate_task` calls.** They are capped/truncated at
  `delegation.max_concurrent_children` and lose independence. One call, one `tasks` array of 5.
- **Skipping anonymization in review.** If reviewers know the author they defer to certain
  lenses instead of judging merit — and the entire "reviews" step becomes theater.
- **Council on a trivial question.** One right answer, no tradeoff: just answer it.
- **Steering the framed question.** Adding your opinion contaminates all five and the verdict.
- **Children can't be the chairman.** They can't hold the whole transcript or see the mapping;
  the parent synthesizes.
- **`::preview` needs two calls' worth of care:** write the file first, then emit the directive
  alone on its own line; the desktop app reveals the pane. Skip it entirely off-desktop.
- **Don't hand-write a fancier visual than the content supports.** The verdict is the product;
  the HTML just makes it scannable.
- Windows hosts: no `python3` (use `python`); native tools want `C:/...` forward-slash paths.

## References

Load on demand — the bodies live there, not here.

| Load when… | File |
|---|---|
| You want the long-form method: full worked transcript, the HTML report body spec, the transcript spec | `references/playbook.md` |
| The default 5×1×1 council doesn't fit: no-delegation cheap path, 8–12 advisor roster, multi-round debate, domain presets, anti-patterns | `references/variants.md` |

## Verification

- [ ] Exactly two `delegate_task` calls were made: one with 5 advisor tasks, one with 5 reviewer tasks.
- [ ] All 10 children returned substantive output (not refusals, not empty); advisors 150–300 words.
- [ ] Reviewer prompts contained **no** advisor identities (letters only).
- [ ] The verdict's five sections are present and specific (each section names the advisors it rests on).
- [ ] On desktop: the `::preview{file=...}` report renders inline; elsewhere, markdown delivered in chat.
- [ ] `council-transcript-<timestamp>.md` exists with question + framed question + 5 responses + 5 reviews + synthesis.
