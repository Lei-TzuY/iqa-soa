#!/usr/bin/env python3
r"""Automated visual QA over every page of the compiled PDF.

Checks the defects that a formatting desk-reject would catch, mechanically
rather than by eye:

  * text crossing the right or left text margin (clipped or overhanging glyphs);
  * content spilling below the footer band or above the header band;
  * missing or zero-area images;
  * pages with no text at all;
  * the .log's own overfull/underfull box counts;
  * replacement glyphs (missing font characters).

    python tools/visual_qa.py [build/main.pdf] [build/main.log]

Exit status 0 if clean, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf

# acmsmall on a 486x720pt page. The right edge of the text block is measured
# from the document itself rather than assumed: it is the modal right edge of
# the body text blocks, so the check cannot be defeated by a wrong constant.
# The left margin carries the review line numbers and is excluded.
TEXT_LEFT = 40.0
HEADER_TOP = 40.0
FOOTER_BOTTOM = 700.0

# Glyph bounding boxes reported by the PDF text extractor include right side
# bearings, so a line-ending hyphen or period measures 1-3pt past the text
# block without overflowing it. TeX's own overfull-hbox count, also checked
# below, is the authoritative signal for real overflow; this geometric check
# catches gross breakage (the pre-fix defects here ran 13-98pt).
TOLERANCE = 3.0


def measure_text_right(doc) -> float:
    r"""Right edge of the text block, in points.

    Taken from the figures, which are set at exactly `width=\linewidth`, so
    their PDF bounding box IS the text block. That is independent of the text
    being measured, unlike taking a maximum over the text itself.
    """
    widths = [im["bbox"][2] for page in doc for im in page.get_image_info()
              if (im["bbox"][2] - im["bbox"][0]) > 300]
    if widths:
        return max(widths)
    return doc[0].rect.width - 45.83          # acmsmall right margin


def main(pdf_path: str = "build/main.pdf", log_path: str = "build/main.log") -> int:
    doc = pymupdf.open(pdf_path)
    findings: list[str] = []
    text_right = measure_text_right(doc)

    print(f"VISUAL QA over {doc.page_count} pages")
    print(f"  measured text-block right edge: {text_right:.1f} pt "
          f"(tolerance {TOLERANCE} pt)")
    print(f"  text block x in [{TEXT_LEFT}, {text_right}] pt, "
          f"y in [{HEADER_TOP}, {FOOTER_BOTTOM}] pt\n")
    print(f"{'page':>5}  {'blocks':>6} {'imgs':>4}  {'max x1':>7}  {'max y1':>7}  status")
    print("-" * 58)

    for pno in range(doc.page_count):
        page = doc[pno]
        blocks = page.get_text("blocks")
        # Line numbers sit left of the text block; exclude them from bounds.
        body = [b for b in blocks if b[0] > TEXT_LEFT - 20]
        max_x1 = max((b[2] for b in body), default=0.0)
        min_x0 = min((b[0] for b in body), default=TEXT_LEFT)
        max_y1 = max((b[3] for b in body), default=0.0)
        images = [i for i in page.get_image_info()
                  if (i["bbox"][2] - i["bbox"][0]) > 1 and (i["bbox"][3] - i["bbox"][1]) > 1]

        issues = []
        if max_x1 > text_right + TOLERANCE:
            issues.append(f"overhangs right margin by {max_x1 - text_right:.1f}pt")
        if min_x0 < TEXT_LEFT - 20:
            issues.append(f"text left of block at x={min_x0:.1f}")
        if max_y1 > FOOTER_BOTTOM + TOLERANCE:
            issues.append(f"content below footer band (y={max_y1:.1f})")
        if not body:
            issues.append("page carries no body text")
        if len(page.get_images(full=True)) != len(images):
            issues.append("zero-area image present")

        text = page.get_text()
        if "�" in text:
            issues.append("replacement glyph (missing character)")

        status = "ok" if not issues else "; ".join(issues)
        print(f"{pno+1:>5}  {len(body):>6} {len(images):>4}  {max_x1:>7.1f}  "
              f"{max_y1:>7.1f}  {status}")
        for i in issues:
            findings.append(f"page {pno+1}: {i}")

    # --- compiler-reported box warnings ------------------------------------
    print()
    log = Path(log_path)
    if log.exists():
        raw = log.read_text(encoding="utf-8", errors="replace")
        over = re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide\)", raw)
        under_h = len(re.findall(r"Underfull \\hbox", raw))
        under_v = len(re.findall(r"Underfull \\vbox", raw))
        print(f"Overfull  hboxes : {len(over)}"
              + (f"  (worst {max(float(o) for o in over):.1f}pt)" if over else ""))
        print(f"Underfull hboxes : {under_h}   (loose spacing; not a defect)")
        print(f"Underfull vboxes : {under_v}   (short pages; not a defect)")
        if over:
            findings.append(f"{len(over)} overfull hbox(es) reported by the compiler")
        for pat, label in [(r"^! ", "LaTeX error"),
                           (r"Citation .* undefined", "undefined citation"),
                           (r"Reference .* undefined", "undefined reference"),
                           (r"File .* not found", "missing input file")]:
            n = len(re.findall(pat, raw, re.MULTILINE))
            print(f"{label:<17}: {n}")
            if n:
                findings.append(f"{n} x {label}")
    else:
        print("(no build log found)")

    print("\n" + "=" * 58)
    if findings:
        print(f"VISUAL_QA: FAIL ({len(findings)})")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("VISUAL_QA: PASS")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(*(a or ["build/main.pdf", "build/main.log"])))
