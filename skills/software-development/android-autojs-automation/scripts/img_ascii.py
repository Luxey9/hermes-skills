#!/usr/bin/env python3
"""Render an image as a coarse character map so layout can be read as text.

Usage: python img_ascii.py IMAGE [COLS] [ROWS]

Prints a luminance ramp with hue letters overlaid, plus a scale legend. Use when
you need to know where things are on a screenshot but cannot view it directly:
letterbox bounds, which side the content sits on, where a coloured overlay landed.
"""
import sys

import cv2
import numpy as np

RAMP = " .:-=+*#%@"


def classify(hue, sat, val):
    if sat > 100 and val > 90:
        if hue < 8 or hue > 170:
            return "R"
        if hue < 25:
            return "O"
        if hue < 40:
            return "Y"
        if hue < 85:
            return "G"
        if hue < 135:
            return "B"
        return "P"
    return RAMP[min(9, val * 10 // 256)]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    img = cv2.imread(path)
    if img is None:
        print("cannot read", path)
        return 1
    h, w = img.shape[:2]

    small = cv2.resize(img, (cols, rows), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue, sat, val = (hsv[:, :, i].astype(int) for i in range(3))

    print(f"image {w}x{h}  ->  {cols}x{rows} chars")
    print("     " + "".join(str(i % 10) for i in range(cols)))
    for y in range(rows):
        line = "".join(classify(hue[y, x], sat[y, x], val[y, x]) for x in range(cols))
        print(f"{y:3d}  {line}")
    print(f"1 char = {w / cols:.1f} x {h / rows:.1f} px")
    return 0


if __name__ == "__main__":
    sys.exit(main())
