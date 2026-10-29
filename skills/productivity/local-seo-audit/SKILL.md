---
name: local-seo-audit
description: Use when checking a local business's Google visibility.
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [seo, local-seo, google-business-profile, search-console, reviews, ranking]
    related_skills: [single-file-landing-pages, maps]
---

# Local SEO Audit

## When to Use

Any request about whether a local service business is findable on Google, why it
ranks where it does, or what to do about it: "cek bisnisku di Google", "optimasi
SEO", "kenapa nggak muncul di pencarian", Google Business Profile questions,
review strategy, Search Console handoff, local ranking checks.

This skill owns the **off-page surface** — Google Business Profile, ranking
reality checks, Search Console. For the HTML/on-page side (page weight, base64
extraction, JSON-LD, meta gates, sitemap/robots files) use
`single-file-landing-pages` and its `references/seo-and-page-weight.md`.

## Procedure

1. **Establish ground truth before advising anything.** Never open with a
   checklist. Fetch what actually exists first: is the site indexed, does the
   GBP listing exist, does it have reviews. Advice built on an assumed state is
   wrong half the time and the user has to correct you.
2. **Classify the query the user is comparing himself to, before promising it.**
   A screenshot of a site ranking #1 is usually a *branded* query (short brand or
   domain match, near-zero competition) — "why doesn't mine do that" then has two
   different answers. Say which class the example belongs to, and that ranking for
   a branded query is a different (much cheaper) job than ranking for a generic
   service phrase. Never let a branded-query success set the expectation for a
   commercial keyword.
3. **Probe the Google Business Profile by phone number.** A generic brand name
   returns a crowd of lookalikes; the phone number returns exactly one place.
   See `references/google-business-profile-probe.md` for the endpoint and the
   field-by-field parse.
4. **Run the findability triple, one query at a time, and report each row.**
   Phone query → does the listing resolve at all. Exact brand name query → can
   word-of-mouth find it. Category query → does it compete. The name row is the
   decisive one for a generic name: if it returns shops (electronics/electrical
   supply stores) instead of the business, the name is too generic and a rename is
   a real lever, not a cosmetic one.
5. **Diff against the previous probe, not against memory.** Rating and review
   count are *absent fields* when zero, then appear once reviews land. Re-probe
   rather than trusting an earlier read — the user often knows better than your
   last snapshot.
6. **Run a ranking reality check and state its limits.** Same embed endpoint with
   `ll=<lat>,<lng>&z=14` returns a 20-place sample for a query. Report absence as
   "not in this sampled set", never as "definitely unranked" — the sample is not
   the user's local pack. The sample carries gids and categories only, no names, so
   characterise rivals by `gcid:` category rather than burning calls to parse names.
7. **Baseline the grid at the business's own coordinates.** Centre the sample on
   the listing's own lat/lng (from the probe), not on a city centroid — a missing
   result *there* proves the problem is prominence, while a missing result from
   downtown only proves distance. Run `scripts/geogrid.py` (no key, 9 requests)
   and report the count, then re-run it weekly as the success metric. Absence at
   the business's own coordinates means reviews and pin strength come first, and
   that per-area pages alone will not fix the pack.
8. **Separate the levers by who controls them.** Reviews (user-controlled, fastest),
   site pages (user-controlled, slower), backlinks and prominence (slowest). Say
   which one moves first and why.
9. **Hand off Search Console as explicit steps.** The files existing is not the
   files being known to Google. See `references/search-console-submission.md`.
   Before sending the owner there, fetch the homepage, `robots.txt`, `sitemap.xml`
   and one inner page **with the Googlebot user agent** and report byte counts —
   a 200 with an empty body is not a pass. Confirm the verification artefact still
   serves (`<meta name="google-site-verification">` and/or the root `google<hash>.html`
   file) so nobody re-verifies a property that already verifies. Then post the
   Request-Indexing queue as bounded daily chunks (3 URLs/day), never 20 in one go.
10. **Ship the on-page half instead of only describing it.** When the business has
    a site, apply the local-signal package in `references/service-area-business.md`
    in the same session, verify it, and commit — a ranked list of advice the user
    must retype is a half-finished job.
11. **Check one out-of-Google channel when the owner asks about social.** Facebook
    local groups beat Instagram for local trades (people ask and get a number in
    the same thread); see `references/off-google-channels.md` for the channel
    order, the content mix, and group-posting rules — and hand over post-ready
    drafts, not a posting strategy.

## Always-On Rules

- **Never claim a GBP verification status you cannot see.** Google does not render
  a public "verified" badge on Maps listings. Verification is owner-side only.
  If the user asks, point them at `business.google.com` — do not infer it from
  page text. Guessing here destroys trust the moment they check.
- **Never describe GBP as having a keyword field.** It has none. The ranking
  signals are primary category, secondary categories, the services list, and a
  ≤750-char description. If you catch yourself saying "set your keywords in GBP",
  delete the sentence and rewrite it around categories and services.
- **Never present service areas as a ranking lever.** Max 20 areas, ~2h drive
  radius, and it is a support setting. Ranking in a specific district comes from
  dedicated pages on the site, not from a GBP slot.
- **Never promise a ranking.** Promise the levers that are known to move: reviews,
  category exactness, page speed, indexation. State plainly that position is
  Google's call.
- **Report only what a real fetch returned.** If a fetch is blocked or capped,
  say what you could not see instead of filling the gap with a plausible number.
- Answer in the user's language (Indonesian for this user), concise, evidence
  first, no preamble about what you are about to do.

## Ordering the Advice

Rank fixes by speed-to-effect, and lead with the fastest one that is actually
available:

| Lever | Time to effect | Controlled by |
|---|---|---|
| Reply to existing reviews | days | user, free |
| Get reviews from 0/3 → 10 | 2–4 weeks | user, free |
| Primary category exactness | days after edit | user, free |
| Page weight / Core Web Vitals | 4–8 weeks (CrUX window) | user, free |
| District pages on the site | 4–12 weeks | user, free |
| Backlinks, directory listings | months | user, effort |

A profile with a perfect field set and zero reviews loses to a thinner profile
with fifteen. Lead with reviews unless they are already healthy.

## Pitfalls

- **A brand name that is a common phrase does not surface the listing.** Generic
  Indonesian service names ("Listrik Aman", "Jaya Teknik") collide with hundreds
  of lookalikes and Google will not guess which one you mean. Always query by
  phone number for a positive identification.
- **"Suggest an edit" / "Suggest new hours" do not mean unclaimed.** Those strings
  render on verified, well-known listings too — verified against a large corporate
  place as a control. Never read them as a verification signal.
- **Review *text* is not reachable through a proxy render** — Google serves a
  CAPTCHA interstitial on the reviews page. Getting the count and rating is
  enough for the audit; ask the user for a screenshot when the wording matters.
- **Do not answer a "is it findable?" question with a yes/no.** Two different
  questions hide inside it: does the listing exist (yes), and does it surface in
  search (separate answer). Split them explicitly or the user hears the wrong one.
  Answer with the three probe rows and the mechanism behind each, then order the
  fixes: pin first, reviews second, name third — a unique name only helps once the
  listing can surface at all.
- **Judge the winning sample by category, not by name.** The ranking sample returns
  no names, only `gcid:` categories. Report *what kind* of place occupies the pack
  (e.g. supply stores vs other electricians) — it tells the user whether the
  competition is a same-service rival or a shop that merely matches the words.
- **Check the pin against the page, not just the pin's rank.** Reverse-geocode the
  listing coordinates and compare with the site's claimed locality. A pin in one
  city plus a schema/headline selling another city is a location-signal conflict:
  say so on the pin lever and name which side should move, instead of quietly
  rewriting one to match the other.
- **A GBP verification review freezes the identity fields.** While a verification
  (video, postcard, phone) is pending — Google's own dialog allows up to 5 days —
  editing name, primary category, address or owners can fail it, because the
  reviewer is matching the submitted evidence against the profile. Name it as a
  hold: reviews, photos, services, description and Q&A are safe; identity is not.
  Sequence the rename BEFORE submitting verification, or wait for the verdict.
- **Review bursts look synthetic.** Reviews arriving in one day read as prompted;
  spread the same count over weeks. Say this when giving a review target.
- **A sitemap that lists images which do not exist is worse than no sitemap.**
  Check every `<image:loc>` path resolves on disk before declaring the file done.
- **The render layer masks digit runs in output.** Phone-like values come back as
  `+628****4425` from `read_file`, `grep`, and even `repr()` in a printed payload,
  so a guessed "it is masked" repair looks like it succeeds while changing nothing.
  The file usually holds the full number already: dump `[hex(ord(c)) for c in line]`
  to see the real characters, and only rewrite when the ordinals are actually
  asterisks. Same trap for any long numeric id (place id, CID, coordinates).
- **Directory/backlink lists are global-product shaped, not local-service shaped.**
  A 700-entry "free backlink" list can contain zero entries for the user's country
  (count matches for the country/city with `search_files` before promising
  citations from it) — most of it is SaaS/AI-product directories. Mine 10–15
  usable rows, do not hand over the table.
- **Content linters may not read HTML at all.** A markdown/frontmatter linter
  (e.g. geo-lint) returns `[]` on a landing page and passes silently — check what
  file types it globs, and run it against the article pages instead of reporting a
  clean bill of health on the homepage.

## Going deeper

- `references/google-business-profile-probe.md` — the no-API-key embed endpoint,
  field-by-field parse, rating/review diff, category and services facts, review link.
- **Never quote an `aggregateRating` the listing does not have.** Read rating and
  count from a live probe and write those exact numbers into the JSON-LD; a
  rating with no review behind it is a rich-result loss, and stale numbers drift
  silently after the next review lands.
- `references/search-console-submission.md` — post-deploy GSC steps and what to
  expect in each report.
- `references/service-area-business.md` — service-area businesses (no street
  address): branded-vs-generic framing, review link from place id, honest
  aggregateRating, area/kelurahan section, city pages, domain/TLD choice for a
  bootstrapped local brand, what not to promise.
- `scripts/geogrid.py` — local-pack position grid with no API key; baseline,
  then re-run weekly.
- `references/off-google-channels.md` — Facebook vs Instagram for a local trade,
  content ratio that produces calls, local-group posting rules, what cannot be
  verified from outside.
