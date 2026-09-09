# FSE 2027 anonymous manuscript source

This directory contains the ACM-template source for *Who Controls the Agent?
Auditable Runtime Governance and Fail-Closed Evaluation for LLM Agents*.

The source is anonymous. Do not include this repository-side README in a venue
upload if repository-internal build notes are disallowed; use the verified PDF,
the anonymous supplement, and the generated anonymous replication package.

## Build and verification

From the repository root:

```text
make generate-paper-evidence
make verify-paper
make verify-anonymity
```

If `latexmk` and the ACM template are installed:

```sh
cd paper/fse2027
sh build.sh
python tools/page_accounting.py
python tools/invariant_check.py
python tools/anonymity_scan.py
python tools/visual_qa.py
```

`main.tex` imports three generated tables from `artifact/generated/`: the
Claim--Evidence--Boundary summary, deterministic end-to-end trace, and frozen
study status. `make verify-paper` byte-compares those files with values derived
from the retained run and analysis JSON, so hand-edited paper numbers fail.

## Scientific boundary

The manuscript establishes deterministic mechanism evidence within the
instrumented tool/service boundary and governance evidence for the frozen
prospective lifecycle. The frozen successor verdict is HOLD, confirmatory
execution was not entered, and a QA FULL versus QA OFF safety treatment effect
is not established. Building or checking the paper performs no provider contact,
model inference, qualification rerun, rescoring, or reclassification.

## Anonymous submission contents

- `main.tex` and `references.bib`
- `figures/` (PNG metadata stripped)
- `supplement/`
- the anonymous export produced by `tools/build_artifact_package.py`

Generated build files live under `build/` and the unpacked export under
`artifact-anonymous/`; both are ignored by Git. The anonymity verifier scans
source text, supplement and artifact manifests, export paths and hidden files,
and, when present, PDF bytes plus author/keyword metadata.
