# Search Console Submission — after the files are live

Pushing `robots.txt` and `sitemap.xml` to the repo deploys them; it does not tell
Google they exist. This is the handoff, and it is manual because it needs the
user's Google account.

## Pre-check before sending the user to GSC

Verify the site answers **as Googlebot**, not just as a browser:

```bash
GB="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
for u in "" robots.txt sitemap.xml; do
  printf '%-14s ' "/$u"
  curl -s --max-time 20 -A "$GB" "https://site.example/$u" | wc -c
done
```

Non-zero byte counts on all three mean crawling is unblocked. A 200 with an empty
body is not a pass.

Also confirm the verification artefact is still served — whichever method was used
at setup (`<meta name="google-site-verification">` or the
`google<hash>.html` file at the root). If the property was verified earlier, do
not send the user through verification again.

## Property type

For a Vercel/Netlify subdomain there is no DNS control, so the property must be
**URL prefix**, not **Domain**. Domain properties require DNS TXT access the user
does not have on a `*.vercel.app` host.

## The two actions

1. **Indexing → Sitemaps** → paste `sitemap.xml` → Submit. Status must go to
   *Success* immediately; *Couldn't fetch* means the file is not reachable or is
   malformed — debug that before moving on.
2. **URL Inspection** → paste the full URL → **Test live URL** first (confirms
   Google can fetch and render), then **Request Indexing**.

Request Indexing has a daily quota and repeat requests do not speed anything up.
Once is enough.

## What to tell the user to expect

| Report | Timing | What is normal |
|---|---|---|
| URL Inspection status | 1–3 days after request | `Discovered – currently not indexed` is normal, not an error |
| Indexing → Pages → Excluded | immediately | `/tools/`, `*.bak` excluded on purpose — not a problem |
| Experience → Core Web Vitals | 28-day CrUX window | empty is expected on a young property |
| Enhancement → FAQ / Breadcrumbs | days after crawl | validates the JSON-LD `FAQPage` |

SERP snippets lag the crawl. A stale `<title>` in results a day after deploy is
cache, not a failed change — check URL Inspection before re-editing anything.

## Do not bother with

- Re-verifying a property that already verifies.
- Submitting `robots.txt` as a sitemap — it is discovered on its own.
- Paid SEO tooling for a single-page local business. Sitemap + Request Indexing +
  reviews covers it.
