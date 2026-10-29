# Expanding a one-page site into location pages

When a single landing page has to rank in several districts, do not clone the
whole file. Clone the *content*, share the *chrome*. A 120 KB page copied eight
times is eight new problems: style drift, duplicated dead code, and a homepage
edit that never reaches the copies.

## Shape

- One directory per target: `/<service>-<area>/index.html`. The slug carries the
  keyword; the directory (not a query string) is what a static host serves at
  `/slug/` with no rewrite.
- Shared chrome in a versioned stylesheet: `assets/area.css`, built from the
  homepage's `:root` tokens (colours, radius, fonts) so the pages look like the
  same brand without carrying its inline CSS. 6 KB instead of 120 KB per page.
- A hub page at city level links the districts; district pages link the hub and
  two neighbours. Homepage coverage chips become real `<a>` for every page that
  exists and stay `<span>` for the ones that do not — dead links are worse than
  plain text.

## Generate, don't hand-write

Keep the whole set in one script (`tools/gen_area_pages.py`) as data: slug, name,
parent, districts, landmarks, coordinates, body paragraphs, FAQs. The script
emits every page from one template. Renaming the brand or changing the survey fee
is then a one-line edit plus a regeneration, not sixteen patches.

Make each page genuinely local rather than spinning one paragraph: real
kelurahan/district names for its chip list, real landmarks ("patokan") used in a
sentence, coordinates for the map embed and geo meta, and FAQs whose answers
differ from the sibling pages. Landmarks and district names are facts; prose is
what varies.

## Schema per page

`@graph` with three nodes: `Service` (`areaServed` = the district, `provider`
`@id` pointing at the homepage business node so all pages share one entity —
not eight competing businesses), `BreadcrumbList` mirroring the visible crumb,
and `FAQPage` carrying the page's own questions verbatim. Plus canonical, `og:*`,
and `geo.position` / `ICBM` from the page coordinates.

## Verify before commit

Write a checker (`tools/check_pages.py`) and run it after every regeneration:
JSON-LD parses with the expected node count, title ≤ 62 chars, description ≤ 160,
body word floor, and every internal `href` resolves to a file on disk. Then serve
the tree locally and fetch each page plus the shared CSS and logo, asserting 200
and non-zero bytes.

Rebuild `sitemap.xml` from the page glob rather than editing it by hand, keep the
image entries on the homepage entry, and parse the XML once after writing.

## Scaling past the first batch

When the coverage claim grows from a handful of districts to a whole metro, split
the data out of the generator (`tools/area_data.py` listing every area) and extend
the generator's `AREAS` list from it. Adding a city becomes one dict, not a
thousand-line edit in a template file.

- **Write the flagship few by hand, the rest as data.** Each area needs something
  only true of that area — flood-prone corridors, coastal corrosion, kos with one
  MCB for many rooms, a heavy-block home industry, unstable voltage far from the
  main feeder. Paraphrase a neighbour and the page is a doorway page.
- **Cross-link the whole set in the footer.** A footer list of every sibling page
  turns N orphan pages into one internally-linked cluster and gives each page a
  reason to be crawled after the first few are indexed. It stays cheap: N lines of
  generated HTML per page, and the sitemap count simply follows the glob.
- **Upgrade homepage chips to real `<a>` for every generated page**, in the same
  pass, or the homepage keeps advertising text where pages exist.
- **Prove the near-duplicate is scoped, don't assume it.** A shared services grid
  and terms table repeat verbatim on every page by design; run a duplicate-paragraph
  pass over the generated output, then state which blocks are intentionally shared
  and that the area body plus FAQ are unique — otherwise "21 near-identical pages"
  is a fair reading of your own output.
- **Re-verify the full set after regenerating**, not a sample: loop all pages over
  a local static server, parse each page's JSON-LD, and check every internal
  href resolves. A single stale slug in the footer breaks all of them at once.
- **Tell the user which areas still lack a page, before they ask.** After shipping
  a partial set, list the coverage as a table (hub + districts vs bare chips) so
  "only one city has pages?" never becomes the next message. Then ask for the
  three facts each new area needs — districts, landmarks, the area's characteristic
  electrical complaint — instead of inventing landmarks you do not know.
- **A broad coverage claim does not license thin pages.** If the user says they
  serve the whole metro, write the flagship areas with real local detail and keep
  the rest as chips until you have the facts; a page for an area nobody has worked
  in is a claim that later disappoints and costs reviews.

## Pitfalls

- **Descriptions grow past 160 the moment you template an area name into them.**
  Keep the template short enough that the longest district name still fits, and
  let the checker catch it — a truncated snippet is a CTR loss on every page.
- **Regenerate, never hand-edit a generated page.** The next run silently
  overwrites the hand edit.
- **`areaServed` at city level plus a district page is not a conflict** as long as
  the visible copy says which district the page is for — keep page promise, H1 and
  `areaServed` all on the same district.
- **A markdown/frontmatter content linter will not read these HTML pages** even
  though they are article-shaped; run it against markdown only and check the HTML
  with your own script.
- Pages are the 4–12 week lever. Say so, and keep reviews the headline — shipping
  eight pages does not move a local pack that has four reviews.
