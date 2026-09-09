#!/usr/bin/env python3
r"""Prepare the three manuscript figures for double-anonymous ACM submission.

Three operations, none of which alters figure semantics:

1. Flatten RGBA onto white (acmart/pdflatex handles RGB PNG predictably).
2. Trim uniform white margins, then re-add a small uniform pad. This makes the
   glyphs LARGER at a fixed \linewidth rather than smaller, so it improves
   readability instead of gaming the page budget.
3. Drop every PNG text/metadata chunk, so no toolchain or filesystem string
   survives into the submitted PDF.

No pixel of drawn content is removed, resampled, or rescaled.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

PAD = 12
HERE = Path(__file__).resolve().parent
NAMES = ["fig1-architecture", "fig2-decision-pipeline", "fig3-treatment-families"]


def sanitize(path: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    im = Image.open(path)
    before = im.size
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.split()[-1])
        im = flat
    else:
        im = im.convert("RGB")

    # Trim uniform white border only.
    gray = im.convert("L")
    inverted = Image.eval(gray, lambda p: 255 - p)
    box = inverted.getbbox()
    if box is not None:
        l, t, r, b = box
        l, t = max(0, l - PAD), max(0, t - PAD)
        r, b = min(im.width, r + PAD), min(im.height, b + PAD)
        im = im.crop((l, t, r, b))

    # Re-encode with no metadata at all (no pnginfo argument, no dpi).
    clean = Image.new("RGB", im.size, (255, 255, 255))
    clean.paste(im, (0, 0))
    clean.save(path, format="PNG", optimize=True)
    return before, clean.size


def main() -> int:
    for name in NAMES:
        p = HERE / f"{name}.png"
        before, after = sanitize(p)
        residual = list(Image.open(p).info.keys())
        print(f"{name}: {before} -> {after}  residual_metadata={residual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
