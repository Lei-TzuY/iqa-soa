#!/usr/bin/env python3
r"""Page accounting for the FSE 2027 submission candidate.

Page numbers come from LaTeX itself: every top-level component of main.tex
carries a \label{pg:...}, and the compiler records the page it landed on in
main.aux. That is authoritative, so the 18-page (text + figures) and 4-page
(references) budgets are checked against real official-template output instead
of being estimated from the source.

Within a page, the vertical position of each component's heading is located in
the PDF, so a component that shares a page with its neighbour contributes a
fraction rather than a whole page. Fractions are then reported alongside the
printed span.

FSE 2027 states that the Data Availability statement "will not count towards the
page limit for the submission", so it is reported separately. Appendices are
text and count inside the 18-page budget.

Usage:
    python tools/page_accounting.py [build/main.aux] [build/main.pdf]
"""
from __future__ import annotations

import re
import sys

import pymupdf

# label slug -> (display name, budget category, heading text to locate in the PDF)
COMPONENTS = [
    ("intro",      "1 Introduction",                     "text",   "INTRODUCTION"),
    ("problem",    "2 Problem Setting and Design Goals", "text",   "PROBLEM SETTING"),
    ("arch",       "3 Architecture",                     "text",   "IQA-SOA RUNTIME"),
    ("impl",       "4 Implementation",                   "text",   "IMPLEMENTATION AND"),
    ("bench",      "5 Benchmark Construction",           "text",   "BENCHMARK CONSTRUCTION"),
    ("rqdesign",   "6 RQs and Evaluation Design",        "text",   "RESEARCH QUESTIONS"),
    ("results",    "7 Results",                          "text",   "RESULTS"),
    ("discussion", "8 Discussion",                       "text",   "DISCUSSION"),
    ("threats",    "9 Threats to Validity",              "text",   "THREATS TO VALIDITY"),
    ("related",    "10 Related Work",                    "text",   "RELATED WORK"),
    ("repro",      "11 Reproducibility",                 "text",   "REPRODUCIBILITY"),
    ("future",     "12 Future Work",                     "text",   "FUTURE WORK"),
    ("conclusion", "13 Conclusion",                      "text",   "CONCLUSION"),
    ("dataavail",  "Data Availability",                  "exempt", "DATA AVAILABILITY"),
    ("refsstart",  "References",                         "refs",   "REFERENCES"),
    ("appb",       "Appendix B (provenance)",            "text",   "SUCCESSOR QA-OFF"),
    ("appc",       "Appendix C (confirmatory plan)",     "text",   "PROSPECTIVE CONFIRMATORY"),
]

BUDGET_TEXT = 18
BUDGET_REFS = 4


def read_aux(aux_path: str) -> dict[str, int]:
    """slug -> 1-based page number, from \\newlabel entries in the .aux."""
    pages: dict[str, int] = {}
    rx = re.compile(r"\\newlabel\{pg:([a-z]+)\}\{\{[^{}]*\}\{(\d+)\}")
    with open(aux_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = rx.search(line)
            if m:
                pages[m.group(1)] = int(m.group(2))
    return pages


def heading_y(doc, page_no: int, needle: str) -> tuple[int, float] | None:
    """(1-based page, top y) of `needle`, searched from `page_no` onward.

    The bibliography label sits before \\bibliographystyle, so its recorded page
    can be the one before the "References" heading actually lands on.
    """
    for p in (page_no, page_no + 1):
        if 1 <= p <= doc.page_count:
            hits = doc[p - 1].search_for(needle)
            if hits:
                return p, min(r.y0 for r in hits)
    return None


def main(aux_path: str = "build/main.aux", pdf_path: str = "build/main.pdf") -> int:
    pages = read_aux(aux_path)
    doc = pymupdf.open(pdf_path)
    total = doc.page_count
    height = doc[0].rect.height
    top, bottom = 60.0, height - 60.0
    live = bottom - top

    present = [c for c in COMPONENTS if c[0] in pages]
    # Absolute position, in page units, of the start of each component.
    # COMPONENTS is already in document order, so positions must be monotonic;
    # three components can share one page, and a heading whose glyphs do not
    # match the search string would otherwise sort before its predecessor.
    positions: list[float] = []
    running = 0.0
    for slug, _name, _cat, needle in present:
        p = pages[slug]
        found = heading_y(doc, p, needle)
        if found is None:
            pos = max((p - 1), running)
        else:
            fp, y = found
            frac = min(max((y - top) / live, 0.0), 1.0)
            pos = max((fp - 1) + frac, running)
            pages[slug] = fp
        positions.append(pos)
        running = pos

    # The document body starts at page 1.
    body_start = 0.0
    end = float(total)

    print(f"AUX: {aux_path}")
    print(f"PDF: {pdf_path}")
    print(f"TOTAL_PAGES: {total}\n")
    print(f"{'Component':<36} {'start':>5} {'end':>5} {'budget':>7} {'pages':>7}")
    print("-" * 64)

    # Title block runs from page 1 to the start of the Introduction.
    title_pages = positions[0] - body_start
    print(f"{'Title / Abstract / CCS / Keywords':<36} {1:>5} "
          f"{pages[present[0][0]]:>5} {'text':>7} {title_pages:>7.2f}")

    totals = {"text": title_pages, "refs": 0.0, "exempt": 0.0}
    for i, (slug, name, cat, _needle) in enumerate(present):
        start_u = positions[i]
        end_u = positions[i + 1] if i + 1 < len(present) else end
        end_page = pages[present[i + 1][0]] if i + 1 < len(present) else total
        contrib = end_u - start_u
        totals[cat] += contrib
        print(f"{name:<36} {pages[slug]:>5} {end_page:>5} {cat:>7} {contrib:>7.2f}")

    print("-" * 64)
    t, r, x = totals["text"], totals["refs"], totals["exempt"]
    print(f"{'MAIN TEXT + FIGURES (incl. appendices)':<50} {t:>6.2f}")
    print(f"{'DATA AVAILABILITY (exempt per FSE 2027 CFP)':<50} {x:>6.2f}")
    print(f"{'REFERENCES':<50} {r:>6.2f}")
    print()

    t_ceil, r_ceil = int(-(-t // 1)), int(-(-r // 1))
    print(f"TEXT_FIGURE_PAGES : {t:6.2f}  -> {t_ceil:>2} counted   budget {BUDGET_TEXT}")
    print(f"REFERENCE_PAGES   : {r:6.2f}  -> {r_ceil:>2} counted   budget {BUDGET_REFS}")
    ok_t = t_ceil <= BUDGET_TEXT
    ok_r = r_ceil <= BUDGET_REFS
    print()
    print(f"TEXT BUDGET  : {'PASS' if ok_t else 'FAIL'}  ({t - BUDGET_TEXT:+.2f} pages)")
    print(f"REFS BUDGET  : {'PASS' if ok_r else 'FAIL'}  ({r - BUDGET_REFS:+.2f} pages)")
    print(f"PAGE_LIMIT_COMPLIANT: {'YES' if (ok_t and ok_r) else 'NO'}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main(*(args or ["build/main.aux", "build/main.pdf"])))
