#!/usr/bin/env python3
r"""Double-anonymous scan of the submission package.

Three surfaces are checked:

  1. the compiled PDF's byte stream, which is what a reviewer downloads;
  2. the PDF's document information dictionary and XMP metadata;
  3. every source file that would ship with the submission, including the
     supplement.

"IQA-SOA" is the system's name and is NOT identifying; the repository path that
contains it would be, so only path-shaped occurrences are flagged.

    python tools/anonymity_scan.py

Exit status 0 if clean, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "build" / "main.pdf"

# (label, pattern). Patterns are applied case-insensitively.
IDENTIFIERS = [
    ("author name 'Lei-TzuY'",        r"Lei-?TzuY"),
    ("author name 'Bill Lei'",        r"Bill\s*Lei"),
    ("author name 'Tzu-Yi Lei'",      r"Tzu-?Yi\s*Lei"),
    ("author email",                  r"byilyi2|@gmail\.com"),
    ("public repository path",        r"[A-Za-z0-9_-]+/iqa-soa|Quality_Assurance"),
    ("GitHub URL",                    r"github\.com|githubusercontent"),
    ("Windows filesystem path",       r"C:[/\\]Users|Desktop[/\\]FSE"),
    ("home directory",                r"[/\\]Users[/\\][A-Za-z0-9_.-]+[/\\]"),
    ("ORCID",                         r"orcid\.org"),
    ("acknowledgements section",      r"\\begin\{acks\}|ACKNOWLEDG"),
    ("stale draft footer",            r"Working Draft|Draft v0\.[0-9]|Route-A submission path"),
]

# Files that ship with the submission.
SOURCE_GLOBS = ["*.tex", "*.bib", "*.md", "supplement/*.md", "supplement/*.json"]

# Toolchain strings that legitimately appear in PDF metadata.
METADATA_ALLOWED = {"format", "creator", "producer", "creationDate", "modDate",
                    "trapped", "encryption", "subject", "title"}


def scan_text(label: str, text: str) -> list[str]:
    hits = []
    for name, pattern in IDENTIFIERS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            hits.append(f"{label}: {name} -> {m.group(0)!r}")
    return hits


def main() -> int:
    findings: list[str] = []

    # 1. PDF byte stream ----------------------------------------------------
    print("1. COMPILED PDF BYTE STREAM")
    if not PDF.exists():
        print("   PDF not built"); return 1
    raw = PDF.read_bytes().decode("latin-1")
    pdf_hits = scan_text("pdf", raw)
    for name, _ in IDENTIFIERS:
        flagged = any(name in h for h in pdf_hits)
        print(f"   [{'FOUND' if flagged else 'clean'}] {name}")
    findings += pdf_hits

    # 2. PDF metadata -------------------------------------------------------
    print("\n2. PDF METADATA")
    doc = pymupdf.open(PDF)
    for k, v in doc.metadata.items():
        note = ""
        if k in ("author", "keywords") and v:
            note = "  <== must be empty under double-anonymous review"
            findings.append(f"pdf metadata: {k} = {v!r}")
        print(f"   {k:<12} = {v!r}{note}")
    xmp = doc.xref_xml_metadata() or ""
    if isinstance(xmp, int):
        xmp = ""
    xmp_hits = scan_text("pdf xmp", xmp)
    findings += xmp_hits
    print(f"   xmp: {len(xmp)} chars, {'identifiers found' if xmp_hits else 'no identifiers'}")

    # 3. Source files -------------------------------------------------------
    print("\n3. SOURCE FILES")
    files: list[Path] = []
    for g in SOURCE_GLOBS:
        files.extend(sorted(ROOT.glob(g)))
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = scan_text(str(f.relative_to(ROOT)), text)
        findings += hits
        print(f"   [{'FOUND' if hits else 'clean'}] {f.relative_to(ROOT)}")
        for h in hits:
            print(f"       {h}")

    # 4. Embedded images ----------------------------------------------------
    print("\n4. EMBEDDED FIGURE METADATA")
    try:
        from PIL import Image
        for p in sorted((ROOT / "figures").glob("*.png")):
            info = dict(Image.open(p).info)
            info.pop("dpi", None)
            ok = not info
            print(f"   [{'clean' if ok else 'FOUND'}] {p.name}  metadata={list(info)}")
            if not ok:
                findings.append(f"figure metadata: {p.name} -> {list(info)}")
    except ImportError:
        print("   (Pillow unavailable; skipped)")

    print("\n" + "=" * 62)
    if findings:
        print(f"DOUBLE_ANONYMOUS_SCAN: FAIL ({len(findings)})")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("DOUBLE_ANONYMOUS_SCAN: PASS")
    print("PDF_METADATA_SCAN: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
