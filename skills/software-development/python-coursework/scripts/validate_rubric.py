#!/usr/bin/env python3
"""Validate a point-rubric instruction markdown for this user's coursework norms.

Usage: python validate_rubric.py <file.md> [expected_per_section]

Checks:
  1. Point totals per section (split on '## ') equal expected (default 35).
  2. No forbidden matplotlib APIs (axhline, axvline, gca, legend, invert_xaxis).
  3. No list comprehensions inside code fences.
  4. No characters above U+2500 (Cyrillic / box-drawing corruption).
"""
import re
import sys

FORBIDDEN = ["axhline", "axvline", "gca", "invert_xaxis", "legend"]
WEIRD_THRESHOLD = 0x2500


def main():
    path = sys.argv[1]
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else 35
    text = open(path, encoding="utf-8").read()

    ok = True

    # 1. per-section point totals
    blocks = re.split(r"^##\s+", text, flags=re.M)[1:]
    for i, blk in enumerate(blocks, 1):
        total = sum(int(m) for m in re.findall(r"\((\d+) poin\)", blk))
        if total != expected:
            print(f"Section {i}: {total} poin -> FAIL (expected {expected})")
            ok = False
        else:
            print(f"Section {i}: {total} poin -> OK")

    # 2. forbidden APIs anywhere in the doc
    for api in FORBIDDEN:
        if api in text:
            print(f"FAIL: forbidden API '{api}' present")
            ok = False

    # 3. rough list-comprehension check inside code fences
    for fence in re.findall(r"```(.*?)```", text, flags=re.S):
        for line in fence.splitlines():
            if re.search(r"\[\s*[^\]]*\bfor\b", line):
                print(f"FAIL: possible list comprehension: {line.strip()}")
                ok = False

    # 4. character corruption scan
    weird = sorted({c for c in text if ord(c) > WEIRD_THRESHOLD})
    if weird:
        print(f"FAIL: suspicious characters: {[hex(ord(c)) for c in weird]}")
        ok = False

    print("ALL CHECKS PASSED" if ok else "CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()