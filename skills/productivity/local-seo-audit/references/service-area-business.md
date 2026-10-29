# Service-Area Businesses (no street address)

A business with no public street address cannot win a proximity fight. Its
decisions are different from a storefront's, and so is the site work. For the
page-weight and JSON-LD edit mechanics referenced here, use the sibling
`single-file-landing-pages` skill and its `references/seo-and-page-weight.md`
file — it owns the on-page scripts.

## Diagnose first

The probe either returns an address record or it does not — a listing whose
payload has coordinates and hours but no street line is a service-area listing.
Say that plainly to the user, plus its consequence: in the local pack, distance
from the searcher dominates, so a query typed downtown will not surface a
listing based in the suburbs no matter how good the page is. What is left, and
what actually moves, is reviews and per-area pages.

## Review acquisition

- Build the review link from the place id: `https://search.google.com/local/writereview?placeid=<PLACE_ID>`.
- Put it on the site as a real, visible link, not hidden text — footer next to
  the phone number works, so a satisfied visitor does not have to search for it.
- Instruct asking on WhatsApp H+1 after the job closes, one or two per day. A
  same-day burst reads as prompted.
- Google renders review *count and rating* through a proxy render; the wording
  needs a screenshot from the user.

### Review-request pack (build it, don't just advise)

The bottleneck is not willingness, it is effort: a customer who has to compose a
review writes nothing. Hand over the material so pasting takes twenty seconds.

- **12–16 pre-written drafts**, varied in length and scene, each naming one job
  type and one district so the locals signal lands. Vary the voice too: short,
  plain, one story. Make **two of them 4-star with a mild, believable complaint**
  (late arrival announced by chat, slow material) — a wall of flawless 5-stars
  reads synthetic.
- **Four WhatsApp templates**: brief, familiar, institution/company, and one
  H+4 nudge used once. Each says "paste one of these" and carries the review link.
- **QR + printable card**: render the review link to a QR at high error
  correction, then a small print card (A6) with it for a sticker on the panel or
  meter box just serviced — customers reopen those days later, which is a review
  window that usually gets lost.
- **Decode the QR before shipping it.** Render and run a detector (OpenCV
  `QRCodeDetector.detectAndDecode`) and assert the decoded string equals the
  `writereview` URL; a silently mangled place id sends every scan to nowhere.
- State that `writereview` bounces to Google sign-in for anyone not logged in, so
  send it to customers with an active Google account on their phone and say
  "log in first".
- Also hand the listing URL (`/maps/place/?q=place_id:...`) so the owner can see
  their own listing, and so a name-query test can be run from their side.

## Site work that earns per-area visibility

In order of effort:

1. **Area section on the homepage** — a heading naming the metro area plus the
   districts/kelurahan actually served as a chip list, and one honest sentence
   about out-of-area jobs plus transport cost. This is keyword surface the
   homepage otherwise lacks; keep it real coverage, not a stuffed list.
2. **Nav anchor** to that section — internal links make it crawlable and
   user-reachable.
3. **One page per city** — separate H1, its own districts, its own local proof.
   Five cities need five URLs; a single page cannot rank in five places. This is
   the 4–12 week lever, so it is phase two, never the headline. Build them as a
   generated set, not hand-cloned copies: `single-file-landing-pages`
   `references/location-pages.md` has the template, schema shape and checker.
4. **`areaServed` in JSON-LD** listing cities as `City` nodes, mirroring the
   visible section.

## Measure it, don't vibe it

`scripts/geogrid.py` samples the local pack on a grid around the business's own
coordinates. A service-area listing routinely scores 0 of 9 points *including the
point on top of itself* — that is the numeric proof that prominence, not page
copy, is the blocker, and it stops the user buying "tricks". Report the count,
file the CSV, re-run weekly. Only a rising `present` count counts as progress.

## Address pin is the strongest remaining lever

Proximity dominates the pack, and a service-area listing has no pin to compete
with. A real address (home, rented room, a shop that will take post) verified as
a located business, then hidden again, moves the pin into the target zone. Warn
that a fabricated address risks suspension — use one that can actually receive mail.

## Domain and name for a bootstrapped brand

- **Rename early, not late.** With a handful of reviews and no brand equity, a
  rename costs almost nothing; at 30+ reviews it costs the recognition you built.
  Say this while the listing is still new.
- **Order the three moves: name → domain → pin → verify → reviews.** Deciding the
  name after sending review invitations means customers praise a brand that is
  about to change; the review text is not editable later. Reviews themselves
  survive a GBP rename (Google may ask for re-verification), so the rename is not
  a reason to delay the pin.
- **Name test, scored not eyeballed:** spellable over the phone, contains the
  core service keyword, fits a business card. Then *measure* the collision: query
  each candidate through the embed endpoint and count distinct `/g/` gids in the
  response. 0–3 results = usable, 8+ = crowded, 20 = the response is capped and
  the candidate is indistinct. Screen a batch of 8–10 candidates with the same
  one-liner loop and report the counts in a table; hand over only the low ones.
- **Write candidates in the user's own language.** A mixed name ("Aman Current",
  English noun after an Indonesian one) reads off-key to an Indonesian local
  service buyer; pure-Indonesian compounds ("Listrik Jago", "Sigap Listrik") and
  personal-name forms ("<name> Listrik") land better. Offer both flavours and let
  the user pick — do not hand back one candidate as a done decision.
- **Check the domain while you screen the name**, so the chosen name has a home:
  an RDAP `404` means free — `https://rdap.verisign.com/com/v1/domain/<domain>`
  for `.com`, `https://rdap.pandi.id/domain/<domain>` for `.id`, `.my.id`,
  `.web.id`. Confirm the `.com` is free even when recommending a cheap local
  extension, otherwise the later upgrade forces a second rename.
- **TLD:** the extension barely affects ranking; it affects human trust. For a
  bootstrap budget pick the cheapest local extension that needs no documents
  (`.my.id`) — `.web.id` costs more and signals "personal site" without an
  advantage. Move up to `.com` or `.co.id` (needs NIB/NPWP) once order flow
  exists, because procurement and government buyers read `.co.id` as a company.
- **Migrating without a reset:** add the new domain to the *same* hosting project
  (a new project resets accumulated signal), host-based 301 from the old host,
  then update canonical, `og:url`, every absolute URL in JSON-LD, sitemap and
  robots, plus the GBP website field, keeping NAP identical everywhere. The old
  host stays live and redirects so no page dies.

## Honest schema

- `aggregateRating` uses the probed rating and count verbatim. Ratings show in
  rich results only once there are reviews behind them.
- `sameAs` gets the Maps listing URL (`https://www.google.com/maps/place/?q=place_id:<PLACE_ID>`).
- Never invent an address to fill `PostalAddress`; `addressLocality` +
  `addressRegion` + `addressCountry` is enough for a service-area listing.

## Promise table

| Ask | Realistic time |
|---|---|
| #1 for the brand / domain query | 1–2 weeks once indexed |
| Local pack for "service + district" | 2–6 weeks with steady reviews |
| Page 1 organic on the generic service phrase | 1–3 months |

Say which row is which. The user almost always wants the generic phrase to move
as fast as the brand query, and it will not.
