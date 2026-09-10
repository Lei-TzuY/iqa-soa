#!/usr/bin/env python3
"""Verify every SHA-256 in MANIFEST.sha256 against the shipped files.

    python analysis/verify_manifest.py

Run from the root of the anonymous package. Exit status 0 if every listed file
is present and hashes to its recorded digest, 1 otherwise. Also reports any file
present in the package but absent from the manifest.

``MANIFEST.sha256`` and ``manifest.json`` are not listed in the manifest, since
a file cannot contain its own digest.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]

#: A file cannot contain its own digest, so these two are not self-listed.
SELF_EXCLUDED = {"MANIFEST.sha256", "manifest.json"}

#: Byproducts of RUNNING the package rather than files shipped in it. Running
#: the RQ1 tests creates bytecode caches; that is not a package defect, so an
#: "unlisted file" report must not fire on them.
GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                  ".venv", "venv", ".eggs"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = PKG / "MANIFEST.sha256"
    if not manifest.exists():
        print("FAIL - MANIFEST.sha256 not found")
        return 1

    listed: dict[str, str] = {}
    for line in manifest.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        listed[rel] = digest

    missing, mismatched, ok = [], [], 0
    for rel, want in sorted(listed.items()):
        p = PKG / rel
        if not p.is_file():
            missing.append(rel)
            continue
        got = sha256_file(p)
        if got != want:
            mismatched.append((rel, want, got))
        else:
            ok += 1

    def is_generated(p: Path) -> bool:
        rel = p.relative_to(PKG)
        return (any(part in GENERATED_DIRS for part in rel.parts)
                or p.suffix in GENERATED_SUFFIXES
                or "egg-info" in str(rel))

    on_disk = {
        str(p.relative_to(PKG)).replace(chr(92), "/")
        for p in PKG.rglob("*") if p.is_file() and not is_generated(p)
    }
    generated = sum(1 for p in PKG.rglob("*") if p.is_file() and is_generated(p))
    unlisted = sorted(on_disk - set(listed) - SELF_EXCLUDED)

    print(f"listed files      : {len(listed)}")
    print(f"verified          : {ok}")
    print(f"missing           : {len(missing)}")
    print(f"digest mismatches : {len(mismatched)}")
    print(f"unlisted on disk  : {len(unlisted)}")
    if generated:
        print(f"generated (skipped): {generated}  "
              f"(bytecode/test caches created by running the RQ1 tests)")

    for rel in missing:
        print("  MISSING   ", rel)
    for rel, want, got in mismatched:
        print(f"  MISMATCH   {rel}\n    manifest {want}\n    on disk  {got}")
    for rel in unlisted:
        print("  UNLISTED  ", rel)

    if missing or mismatched or unlisted:
        print("\nFAIL")
        return 1
    print("\nPASS - every file in the package is listed and hashes correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
