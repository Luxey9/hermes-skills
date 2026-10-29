# SEO & Page Weight for Single-File Landing Pages

Depth for step 5 and step 8 of the parent skill: getting a multi-MB single-file
page down to a size Google will actually rank, and proving the result over HTTP.

## 1. The real ranking problem is weight, not keywords

A single-file landing page carrying base64 images is usually 2–4 MB. LCP and
total byte weight are Core Web Vitals inputs, so on-page keyword work on a 3 MB
page is rearranging deck chairs. Measure before you touch meta tags:

```bash
wc -c index.html
awk '{print length" L"NR}' index.html | sort -rn | head -5   # find the fat lines
grep -c -o -E 'data:image/[a-z+]+;base64' index.html
du -sh img
```

If a handful of lines are 100–400 KB each, they are base64 blobs. That is the job.

## 2. Extract every base64 blob — both attributes

`src="data:image/…"` is the obvious one. `data-full="data:image/…"` on gallery
lightbox buttons holds the *originals* and is usually the larger half. A `src`-only
regex leaves 800 KB+ behind and the page stays multi-MB while looking fixed.

Match any attribute whose value is a data URI, not a fixed list of attribute names:

```python
PATTERN = re.compile(
    r'((?:src|data-full|data-src|href)=")data:image/'
    r'(png|jpeg|jpg|webp|gif|svg\+xml);base64,([A-Za-z0-9+/=\s]+?)(")'
)
```

Decode, hash the bytes, write to `img/`, and rewrite the attribute. Content-hash
names (`inline-<sha1[:12]>.<ext>`) make the operation idempotent — re-running
collapses duplicates to one file instead of creating a new copy each pass.

Run it twice: the first pass reports what it replaced, the second must report 0.
`grep -c 'data:image/[a-z+]*;base64'` returning 0 is the exit condition.

## 3. Rename extracted files to descriptive, keyword-bearing names

`inline-8dab71a0f18b.jpg` wastes a ranking signal. Map each one to a slug derived
from the image's own `data-label` / alt text: `panel-listrik-mcb-rapi.jpg`,
`perbaikan-konsleting.jpg`. File name + alt text + surrounding caption are the
three things Google reads about an image.

Do the rename in the same script that writes the files, so the HTML rewrite and
the disk write cannot drift apart.

## 4. Two sizes per gallery image, not one

A grid thumbnail does not need the lightbox resolution. Emit both:

| Use | Max width | Quality |
|---|---|---|
| grid `<img src>` | 640 px | 82 |
| lightbox `data-full` | 1400 px | 85 |
| hero (WebP) | 960 px | 80 |
| logo rendered at 40 px | 96 px | 92 |

Pillow, with `optimize=True, progressive=True` for JPEG. Write the *actual*
resulting size back into the `width`/`height` attributes — see the CLS pitfall in
the parent skill.

A 512 px PNG logo rendered into a 40 px slot is a common 300–400 KB waste. Re-encode
to the real display size (×2 for retina is enough) and keep a `.webp` sibling.

## 5. Hero: `<picture>` + preload, and preload the format you ship

```html
<link rel="preload" as="image" href="img/hero-960.webp" type="image/webp" fetchpriority="high" />
…
<picture>
  <source srcset="img/hero-960.webp" type="image/webp" width="960" height="536" />
  <img src="img/hero-960.jpg" alt="…" width="960" height="536" fetchpriority="high" decoding="async" />
</picture>
```

The preload `href` must point at the same file the `<source>` serves, or the browser
downloads the WebP and *also* fetches the JPEG fallback — preloading the wrong one
costs a request instead of saving one.

## 6. Structured data: one `@graph`, not several scripts

Emit a single `<script type="application/ld+json">` with `@graph` holding
`LocalBusiness`, `WebSite`, and `FAQPage`. Cross-reference by `@id` so Google
resolves one entity:

- `LocalBusiness` (add the specific subtype too: `["LocalBusiness", "ElectricalContractor"]`)
  — name, `telephone` in E.164, `address`, `areaServed` as City list,
  `openingHoursSpecification`, `hasOfferCatalog` with one `Offer` per service.
- `WebSite` with `publisher: {"@id": "…/#business"}` and `inLanguage`.
- `FAQPage` with `mainEntity` mirroring the visible FAQ *verbatim*. Schema text that
does not appear on the page is a rich-result disqualifier.

Validate by parsing, not by eye:

```python
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
print([n.get("@type") for n in data["@graph"]])
```

## 7. Length gates

| Field | Target | Consequence |
|---|---|---|
| `<title>` | 30–65 chars | truncated in SERP past ~60 |
| `meta description` | 100–165 chars | truncated past ~160 |
| GBP description | ≤750 chars | hard field limit |

Write the length check into the audit script so it fails loudly rather than being
noticed later in the SERP preview.

## 8. robots.txt + sitemap.xml

Both are frequently absent on a Vercel static deploy. Sitemap should carry an
image extension block for the hero and the best gallery shots:

```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
```

`robots.txt` disallows the tooling/backup paths (`/tools/`, `*.bak`) and declares
`Sitemap:` with an absolute URL.

## 9. The audit script is the deliverable's proof

Never report "SEO done" off the diff. One script that asserts:

1. every local `src` / `href` / `data-full` / `srcset` resolves on disk;
2. zero remaining `data:image/…;base64` occurrences;
3. exactly one `<h1>`;
4. JSON-LD parses and lists its `@type`s;
5. title and description lengths inside the gates above;
6. first-paint weight = HTML + hero.

## 10. Proving assets over HTTP on this host

`curl -s -o /dev/null -w '%{http_code}'` from bash proves routing. But when the
probe runs from Python `subprocess` on Windows/MSYS, `/dev/null` is **not** path-
translated for the native binary and every request reports `000 0b` — which reads
as a total outage and sends you chasing a phantom. Probe in Python instead:

```python
with urllib.request.urlopen("http://127.0.0.1:8932/" + ref) as resp:
    body = resp.read()
    assert resp.status == 200 and body
```

Assert non-zero bytes as well as 200: a 200 with an empty body is a server
misconfiguration that a status-only check calls healthy.

Serve on a fresh port each round. A backgrounded `python -m http.server` from an
earlier call may already be dead, and a dead server also reports `000` — check
whether the port answers at all before concluding the files are broken.
