#!/usr/bin/env python3
"""Read-only ASAR inspector using only the stdlib (no node, no npx).

Usage:
  python asar-ro.py list <app.asar> [path-prefix]
  python asar-ro.py cat  <app.asar> <inner/path> [outfile]

Layout: uint32 LE header-JSON byte length at offset 12, JSON at 16,
file data at 16 + len; each entry's offset/size is relative to that base.
Unpacked entries live in <app.asar>.unpacked/<path> instead of the blob.
"""
import json
import struct
import sys


def load(path):
    blob = open(path, "rb").read()
    n = struct.unpack_from("<I", blob, 12)[0]
    header = json.loads(blob[16:16 + n].decode("utf-8"))
    return blob, 16 + n, header


def walk(node, prefix=""):
    for name, meta in node.get("files", {}).items():
        p = f"{prefix}/{name}"
        if "files" in meta:
            yield from walk(meta, p)
        else:
            yield p, int(meta["offset"]), int(meta["size"]), bool(meta.get("unpacked"))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, asar = sys.argv[1], sys.argv[2]
    blob, base, header = load(asar)
    entries = list(walk(header))

    if cmd == "list":
        prefix = sys.argv[3] if len(sys.argv) > 3 else ""
        for p, _o, s, u in entries:
            if p.startswith(prefix):
                print(f"{s:>12,}  {'unpacked  ' if u else ''}{p}")
        return 0

    if cmd == "cat":
        want = "/" + sys.argv[3].lstrip("/")
        for p, o, s, u in entries:
            if p != want:
                continue
            if u:
                print(f"unpacked entry - read {asar}.unpacked{want}", file=sys.stderr)
                return 2
            data = blob[base + o: base + o + s]
            if len(sys.argv) > 4:
                open(sys.argv[4], "wb").write(data)
                print(f"wrote {len(data)} bytes -> {sys.argv[4]}")
            else:
                sys.stdout.buffer.write(data)
            return 0
        print(f"not found: {want}", file=sys.stderr)
        return 2

    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
