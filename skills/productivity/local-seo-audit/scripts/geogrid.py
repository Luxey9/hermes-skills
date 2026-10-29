"""Measure the target listing's position in a local-pack grid — no API key.

Baseline before any work, re-run weekly to prove movement. Positions are 0 when
the gid is absent from that point's 20-place sample.

    python scripts/geogrid.py --query "tukang listrik" --gid <GID> --out grid.csv

Defaults centre on the business's own coordinates; pass --lat/--lng for another
origin. Keep --steps 3 / --span-km 10 for a re-measure (9 requests); go 5x5 only
when a density map is actually needed (25 requests, slower).
"""

import argparse
import csv
import re
import time
import urllib.parse
import urllib.request

EMBED = "https://maps.google.com/maps?q={q}&output=embed&hl=id&ll={lat},{lng}&z=13"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def fetch(lat, lng, query):
    url = EMBED.format(q=urllib.parse.quote_plus(query), lat=lat, lng=lng)
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "id-ID,id;q=0.9"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def positions(html):
    return re.findall(r"/g/([A-Za-z0-9_\-]+)", html)


def grid(lat, lng, span_km, steps):
    dlat = (span_km / 111.0) / (steps - 1)
    dlng = (span_km / 110.0) / (steps - 1)
    half = (steps - 1) / 2
    for i in range(steps):
        for j in range(steps):
            yield round(lat + (i - half) * dlat, 6), round(lng + (j - half) * dlng, 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--gid", required=True, help="target /g/<gid> from the GBP probe")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--span-km", type=float, default=10.0)
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--delay", type=float, default=1.2)
    ap.add_argument("--out", default="geogrid.csv")
    a = ap.parse_args()

    lat0 = a.lat if a.lat is not None else -6.3841225
    lng0 = a.lng if a.lng is not None else 106.796991

    rows, found = [], 0
    points = list(grid(lat0, lng0, a.span_km, a.steps))
    for n, (lat, lng) in enumerate(points, 1):
        try:
            gids = positions(fetch(lat, lng, a.query))
        except Exception as e:  # noqa: BLE001
            gids = []
            print(f"[{n}/{len(points)}] {lat},{lng} err {e}")
        pos = gids.index(a.gid) + 1 if a.gid in gids else 0
        found += 1 if pos else 0
        rows.append((n, lat, lng, pos))
        print(f"[{n}/{len(points)}] {lat},{lng} -> {pos or '-'}")
        time.sleep(a.delay)

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["point", "lat", "lng", "position"])
        w.writerows(rows)

    print(
        f"\npoints {len(rows)} | present {found} | top3 "
        f"{sum(1 for r in rows if 0 < r[3] <= 3)} | top10 "
        f"{sum(1 for r in rows if 0 < r[3] <= 10)}"
    )
    print(f"grid saved: {a.out}")


if __name__ == "__main__":
    main()
