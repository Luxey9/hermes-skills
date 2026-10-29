# LLM Council

One question in, five independent perspectives out, anonymized peer review, then a verdict
you can act on. Based on Andrej Karpathy's LLM Council.

This reference is the long-form playbook for the council defined in `SKILL.md`: the deeper
"why", a full worked transcript, and the bodies of the two artifacts the council emits.

## Why the council exists

You ask one model a question and get one answer. It might be great, it might be mid — you
can't tell, because you only saw one perspective. Worse, a single model is agreeable: ask
"should I launch this?" and it finds five reasons yes; ask "is this a bad idea?" and it finds
five reasons no. Same product, opposite answers. That is fine for prose, dangerous for decisions.

The council fixes this by engineering disagreement before synthesizing it:
1. Five lens-distinct advisors answer independently (no anchoring).
2. Their responses are anonymized and each advisor reviews all five (merit, not author).
3. A chairman folds responses + reviews into one verdict: agreement, clash, blind spots,
   recommendation, and the first move.

## Full session transcript (how a run looks)

**User:** `council this: I'm thinking of building a $297 course on Claude Code for beginners. My audience is mostly non-technical solopreneurs. Is this the right move?`

**The Contrarian** — the market is flooded with Claude courses; at $297 you compete with free
YouTube; a non-technical audience means high support burden and refund risk; the people who'd
pay $297 are likely past beginner level anyway.

**The First Principles Thinker** — what are you actually trying to achieve? If revenue, a course
is one of the slowest paths; if authority, a free resource might do more; if building a client
base for higher-ticket offers, the price and audience are mismatched.

**The Expansionist** — beginner-AI for solopreneurs is a massive underserved market; everyone
teaches advanced material; owning the entry point might be worth far more than $297.

**The Outsider** — "I don't know what Claude Code is. If I saw '$297 course on Claude Code for
beginners' I wouldn't know if it's for me." The landing page must sell the outcome, not the tool.

**The Executor** — a full course takes 4–8 weeks; before building anything, run a $97 live
workshop for 50 people; validate demand, generate testimonials, produce raw material. If 50
won't buy the workshop, 500 won't buy the course.

**Peer review highlights** — strongest: the Outsider (framing problem nobody else saw).
Biggest blind spot: the Expansionist's upside case assumed demand exists *and* is reachable.
All five missed: distribution — none asked how the audience would ever hear about it.

**Verdict**
- *Agrees:* real demand in the beginner angle, but the tool-specific framing repels non-technical buyers.
- *Clashes:* price — Contrarian says too high vs free content, Expansionist says too low for the value.
- *Blind spots caught:* the Outsider's "the name means nothing to my buyer" is the single most
  important insight; every advisor except the Outsider assumed the audience already knows the tool.
- *Recommendation:* don't build the course yet; validate with a lower-commitment offer first,
  and reframe from tool → outcome ("automate your first task with AI").
- *Do first:* run a $97 live workshop called "How to automate your first business task with AI"
  to 50 people — don't mention Claude Code in the title.

## Artifact 1 — the HTML report body

Self-contained: inline CSS, no external assets, no page background/margins override when it is
meant to live inside the Hermes desktop preview frame (use the frame's CSS vars). Sections,
in order:

1. **The question** at the top (the framed prompt).
2. **The chairman's verdict** prominent — headline sized, this is what most readers scan.
3. **A compact agree/clash visual** — a grid or two-column block showing which advisors aligned
   and which diverged. Keep it clean; it is a signal map, not decoration.
4. **Collapsed `<details>` per advisor** — five collapsed blocks, summary line = advisor name +
   one-line gist, body = the full 150–300 word response.
5. **Collapsed peer-review block** — the three answers per reviewer, mapping revealed.
6. **Footer** — timestamp and the topic that was counciled.

Styling: system sans-serif stack, subtle borders, soft accent per advisor to differentiate,
nothing flashy. It should read like a professional briefing sheet.

Who produced what, traceable: each advisor block carries its name; the verdict section names
which advisors each claim rests on.

## Artifact 2 — the transcript

`council-transcript-<timestamp>.md`, in the same directory as the report (or the workspace /
scratch dir if the user gave none). It contains, in order:

- the original question
- the framed question (post-enrichment)
- all five advisor responses, attributed
- all five peer reviews, **with the anonymization mapping revealed** (letter → advisor)
- the chairman's full synthesis

This is the durable artifact. It lets a future session re-council an updated version of the
same question and diff how the thinking moved.
