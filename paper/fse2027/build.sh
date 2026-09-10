#!/usr/bin/env sh
# Reproducible ACM (acmart) build for the FSE 2027 submission candidate.
#
#   sh build.sh
#
# Produces build/main.pdf. No warning is suppressed; the build fails on any
# fatal error, and the readiness audit separately asserts zero undefined
# citations and zero undefined references in build/main.log.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

# latexmk runs bibtex with build/ as its working directory, so the source
# directory must be on the BibTeX search path. It must be FIRST and in native
# form: some TeX distributions ship their own bibtex/bib/*/references.bib, and
# a lower-priority or unresolvable entry silently loses the name collision.
NATIVE="$HERE"
command -v cygpath >/dev/null 2>&1 && NATIVE=$(cygpath -w "$HERE")
BIBINPUTS="$NATIVE;"; export BIBINPUTS
TEXINPUTS="$NATIVE;"; export TEXINPUTS

mkdir -p "$HERE/build"
cd "$HERE"
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$HERE/build" "$HERE/main.tex"
