# Google Business Profile Probe — no API key, no login

Reading a public GBP listing without the Places API, an API key, or a browser.
The Maps **embed** endpoint renders server-side and returns a compact payload
holding every field the audit needs.

## The endpoint

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
  -H "Accept-Language: id-ID,id;q=0.9" \
  "https://maps.google.com/maps?q=085219884425&output=embed&hl=id" -o place.html
```

`q=` accepts a phone number (local or E.164), a place name, or `place_id:ChIJ…`.
**Use the phone number** when the brand name is a common phrase — it returns a
single place instead of twenty lookalikes.

The response is ~3 KB. Everything of interest is inside one `initEmbed([...])`
array literal in the inline script.

## Parsing

The payload is not JSON (unquoted keys, nested arrays of mixed types). Do not try
`json.loads`. Pull quoted strings and match on shape:

```python
import re
s = open("place.html", encoding="utf-8", errors="ignore").read()
strings = re.findall(r'"((?:[^"\\]|\\.){2,120})"', s)
```

What to look for, in the order they appear:

| Signal | Shape | Meaning |
|---|---|---|
| category | `gcid:electrician` | GBP category, machine name |
| gid | `/g/11zzvcc3bl` | stable Maps id, use to match in ranking samples |
| CID pair | `"1238…","1103…"` | the two numeric ids behind the listing |
| business name | plain string, appears twice | display name |
| rating | bare integer `1`–`5` | **absent entirely when there are zero reviews** |
| review count | `"3 ulasan"` (localised) | absent when zero |
| review URL | `https://search.google.com/local/reviews?placeid=ChIJ…` | appears once reviews exist |
| phone | `tel:085219884425` | from the tel: href |
| website | `"https://…","host",null,null,"…"` | second element is the display host |
| place id | `ChIJ…` | for `writereview` links and GSC |
| hours | array of `["Rabu",3,[2026,10,21],[["Buka 24 jam",…]]]` | day name + open string |
| coordinates | `[4231126071,1067969910]` | divide by 1e7 → lat, lng; the minus sign is dropped (see below) |

The rating and count sit adjacent in the record, e.g.
`"Listrik Aman",null,5,"3 ulasan","https://search.google.com/local/reviews?…"`.

**Coordinate sign is lost in the payload.** Indonesia sits at negative latitude,
so `[4231126071,1067969910]` means `-6.4231126071,106.7969910` — the minus never
survives. A positive lat around `6.42` is the Java Sea. Re-add the sign by country
before using the pair for `ll=`.

## Pin-vs-page consistency check

Reverse-geocode the listing coordinates and compare the result with what the site
claims (`addressLocality`, offered cities, title):

```bash
curl -s "https://nominatim.openstreetmap.org/reverse?lat=-6.4231&lon=106.7970&format=json&zoom=18&accept-language=id" \
  -H "User-Agent: local-seo-audit"
```

A pin in one city while the page schema says another is a real signal, not a
data glitch: Google cannot decide which place the business belongs to, and
area-targeted pages cannot fix a pin that contradicts them. Report it as a
mismatch on the pin lever, and never silently "correct" the page to match the pin
(or the reverse) without saying which one the user should move.

## The zero-reviews tell

A listing with no reviews omits both the rating slot and the count string — the
record jumps straight from the name to the website. That absence is the reliable
signal; do not report "0 reviews" from a missing count alone without also
confirming no rating integer and no review URL.

Re-probe to diff. The same query later returning a bare `5` plus `"3 ulasan"`
is proof that reviews landed — useful when the user says "it has reviews now"
and you want to confirm rather than agree.

## Ranking sample

```bash
curl -sL "https://maps.google.com/maps?q=tukang+listrik&output=embed&hl=id&ll=-6.3841225,106.796991&z=14"
```

Collect every `/g/<gid>` in order and check whether the target gid appears, and at
which index:

```python
gids = re.findall(r'/g/([A-Za-z0-9_\-]+)', s)
pos = gids.index(target_gid) + 1 if target_gid in gids else None
```

The set is capped at 20 and is a fixed sample, **not** the user's personalised
local pack. Report it as "not present in this 20-place sample", never as
"unranked". Centring `ll` on the business's own coordinates is the fairest test.

**The sample carries no business names** — each result is only a CID/gid/gcid
triple, e.g. `"3344460384858832899","14004013674356006206","/g/11m6rn2l5y","gcid:electrical_supply_store"`.
Do not spend calls trying to regex a name in front of the gid; there is none.
Use the `gcid:` values instead to characterise who is winning: a sample full of
`electrical_supply_store` means shops, not competitors doing the same service,
which changes what you tell the user. Read names from a separate place probe only
for the one listing you care about.

## Rendered view — for what the payload does not carry

Push the place URL through a text-rendering proxy to see the page as a visitor:

```bash
curl -sL "https://r.jina.ai/https://www.google.com/maps/place/?q=place_id:ChIJ…"
```

This yields markdown with the name, category, hours, phone, website, photo count,
and — when they exist — a `## Reviews` section with a `4.1(1,233)` style rating.
Its absence is a second, independent confirmation of zero reviews.

**Control test before drawing conclusions.** Render a large, obviously-reviewed
place (a corporate office works) and compare the strings present. This is how you
discover that `Suggest an edit` and `Suggest new hours` appear on *every* listing
and therefore prove nothing about ownership or verification.

Google's `search.google.com/local/reviews` page returns a CAPTCHA interstitial to
a proxy. Rating and count are reachable; review *text* is not. Ask for a
screenshot when the wording matters.

## Field facts worth quoting back to the user

- **No keyword field exists.** Signals are primary category, up to 9 secondary
  categories (10 total), the services list (custom entries allowed), and a
  description capped at 750 characters with no links and no prices.
- **Primary category is the strongest lever.** Exact-match categories outrank
  adjacent ones, and a specific category correlates with ~36% higher top-10
  presence than a generic one. `Service establishment` is a dead category — it
  harms rather than helps.
- **Service areas: max 20, ~2h drive radius, support setting only.** District
  visibility comes from pages on the site.
- **Review link to hand the user**, built from the place id:
  `https://search.google.com/local/writereview?placeid=<PLACE_ID>`
- **Listing URL:** `https://www.google.com/maps/place/?q=place_id:<PLACE_ID>`
