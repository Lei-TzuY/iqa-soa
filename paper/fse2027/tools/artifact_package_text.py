#!/usr/bin/env python3
"""Generate reviewer documents for the anonymous replication package.

All paper-facing state is read from the canonical claim manifest, generated
study metadata, and retained successor artifacts. No outcome is recomputed or
reclassified here.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read(path: Path) -> dict:
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _display(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def write_documents(pkg: Path, generated: str) -> None:
    manifest = _read(pkg / "code" / "artifact" / "claim_evidence_manifest.json")
    study = _read(pkg / "code" / "artifact" / "study_metadata.json")
    analysis = _read(pkg / "qualification" / "successor-analysis.json")
    run = _read(pkg / "qualification" / "successor-run-manifest.json")
    qualification = study["qualification"]
    claims = manifest["claims"]
    mechanism = [claim for claim in claims if claim["claim_type"] == "mechanism"]
    mechanism_tests = sorted({
        test_id
        for claim in mechanism
        for test_id in claim["test_ids"]
    })
    n_cases = len(
        _read(pkg / "benchmark" / "pilot-v7-rc4" / "manifest.json")["cases"]
    )
    n_cells = sum(
        1
        for path in (pkg / "qualification" / "raw" / "cells").iterdir()
        if path.is_dir()
    )

    (pkg / "README.md").write_text(f"""# Anonymous replication package

Companion artifact for *Who Controls the Agent? Auditable Runtime Governance
and Fail-Closed Evaluation for LLM Agents*.

This export contains no repository history, public repository URL, author
identity, local home path, or credential. Its content and ZIP timestamps are
deterministic for a fixed source tree.

## Evidence boundary

| Evidence class | Current support |
| --- | --- |
| Mechanism | Established for the instrumented tool/service execution boundary by {len(mechanism)} mapped claims and {len(mechanism_tests)} exact test IDs. |
| Governance | Established for the retained prospective lifecycle: {qualification['scheduled_cells']} scheduled and {qualification['terminal_rows']} terminal cells, {qualification['retries']} retries, verdict **{qualification['verdict']}**, confirmatory eligibility **{_display(qualification['confirmatory_eligible'])}**. |
| Effectiveness | **NOT ESTABLISHED.** No QA FULL versus QA OFF confirmatory treatment effect was estimated because qualification ended in HOLD. |

The deterministic paired trace is a mechanism demonstration over one fixed
proposal. It is not a real-model treatment comparison.

## Fast reviewer path

```sh
python analysis/verify_manifest.py
python analysis/verify_released_counts.py
cd code
python scripts/submission_artifact.py verify-mechanism
```

These commands are offline. They contact no provider, run no model, execute no
qualification cell, and do not modify retained evidence.

## Layout

```text
README.md                     scope and reviewer entry point
SETUP.md                      environment and setup
RQ1-VALIDATION.md             generated claim-to-test detail
PROVENANCE.md                 frozen identities and evidence boundaries
MANIFEST.sha256               digest of every shipped file
manifest.json                 machine-readable package inventory and state
redaction-report.json         path-redaction audit
code/                         implementation, exact referenced tests, claim
                              manifest, trace, and offline verifier
benchmark/                    pilot-v7-rc4 plus {n_cases} selected task definitions
candidate/                    frozen candidate definition
qualification/                retained QA-OFF qualification and {n_cells} cell directories
governance/                   prospective authorizations and HOLD records
analysis/                     read-only package/count verifiers
supplement/                   S1-S4 supplementary material
```

No result was rerun, rescored, reclassified, migrated, or reinterpreted while
building this package. No Phase-P result namespace was read. Generation mode:
`{generated}`.
""", encoding="utf-8")

    (pkg / "SETUP.md").write_text(f"""# Environment and setup

## Requirements

- Python 3.11 or newer (the retained execution used CPython 3.13).
- For mechanism tests: `pip install -e "code[dev]"` from the package root.
- The package-integrity and released-count verifiers use only the standard
  library.

## Verification

```sh
python analysis/verify_manifest.py
python analysis/verify_released_counts.py
cd code
python scripts/submission_artifact.py verify-mechanism
```

The mechanism command validates the canonical claim/evidence contract,
regenerates the deterministic OFF/FULL trace in memory, compares generated
paper evidence byte-for-byte, and executes the exact mechanism test IDs.

The qualification is intentionally not executable from this package. It ran
exactly once with retry limit {run['infrastructure_retry_limit']} and ended in
{qualification['verdict']}. Re-execution would be a new study, not reproduction
of the retained one. `verify_released_counts.py` instead audits its accounting
without model or provider contact.
""", encoding="utf-8")

    claim_rows = "\n".join(
        f"| `{claim['claim_id']}` | {claim['claim_type']} | "
        f"{claim['short_claim']} | {len(claim['test_ids'])} | "
        f"{claim['verification_status']} |"
        for claim in claims
    )
    details: list[str] = []
    for claim in claims:
        tests = "\n".join(f"- `{item}`" for item in claim["test_ids"])
        artifacts = "\n".join(f"- `{item}`" for item in claim["artifact_paths"])
        nonclaims = "\n".join(f"- {item}" for item in claim["explicit_nonclaims"])
        details.append(f"""## {claim['claim_id']}

{claim['short_claim']}

**Type:** {claim['claim_type']}
**Paper section:** {claim['paper_section']}
**Supported scope:** {claim['supported_scope']}

Evidence paths:

{artifacts}

Exact test IDs:

{tests}

Explicit nonclaims:

{nonclaims}
""")
    (pkg / "RQ1-VALIDATION.md").write_text(f"""# Claim-Evidence-Boundary validation

The canonical machine-readable map is
`code/artifact/claim_evidence_manifest.json`. The table and details below are
generated from it; they are not a second manually maintained claim inventory.

| Claim | Type | Short claim | Exact tests | Status |
| --- | --- | --- | ---: | --- |
{claim_rows}

Run the mechanism subset from `code/`:

```sh
python scripts/submission_artifact.py verify-mechanism
```

Success prints `MECHANISM VERIFIED`. This is deterministic offline software
validation, not evidence about real-model proposal frequency or a safety
treatment effect.

{chr(10).join(details)}
""", encoding="utf-8")

    invalidated = {
        item["cell"]: item["failure_class"]
        for item in run["classifications"]
        if item["cell"] in run["invalidated_cells"]
    }
    invalid_rows = "\n".join(
        f"| `{cell}` | `{failure}` |"
        for cell, failure in sorted(invalidated.items())
    )
    (pkg / "PROVENANCE.md").write_text(f"""# Provenance and scientific state

## Frozen identities

| Item | Value |
| --- | --- |
| Candidate | `{study['candidate_identifier']}` |
| Benchmark | `{study['benchmark_identifier']}` |
| Decision rule | `{analysis['decision_rule']}` |
| Aggregation | `{study['qualification_rule']['aggregation']}` |
| Treatments in qualification | {', '.join('`' + value + '`' for value in analysis['treatments'])} |
| Cross-instrument pooling permitted | {_display(analysis['cross_instrument_pooling_permitted'])} |

## Retained outcome

| Invariant | Value |
| --- | --- |
| Terminal status | `{qualification['terminal_status']}` |
| Verdict | **{qualification['verdict']}** |
| Scheduled / terminal / executed cells | {qualification['scheduled_cells']} / {qualification['terminal_rows']} / {qualification['executed_cells']} |
| Retries / replacements / resumptions | {qualification['retries']} / {qualification['replacements']} / {qualification['resumptions']} |
| Invalidated cells | {qualification['invalidated_cells']} |
| Qualified / frozen task roles | {qualification['qualified_tasks']} / {qualification['total_frozen_tasks']} |
| Unqualified / frozen task roles | {qualification['unqualified_tasks']} / {qualification['total_frozen_tasks']} |
| Confirmatory eligible | {_display(qualification['confirmatory_eligible'])} |
| Confirmatory executed | {_display(qualification['confirmatory_execution_performed'])} |
| QA FULL vs QA OFF treatment effect | **NOT ESTABLISHED** |

The current rule is conjunctive across all frozen tasks. A future estimand over
support-qualified tasks would require a new experiment identity and a
prospectively frozen inclusion rule and analysis plan; it cannot replace this
outcome after observation.

## Invalidated cells retained in the accounting

| Cell | Frozen failure class |
| --- | --- |
{invalid_rows}

## Boundary of this export

Scientific/result files are copied without rescoring. Absolute local paths are
redacted only where an equivalent repository-relative identity and content
digest remain; every rewrite is listed in `redaction-report.json`. The builder
refuses Phase-P and schema-clarification namespaces and excludes Git history.
""", encoding="utf-8")
