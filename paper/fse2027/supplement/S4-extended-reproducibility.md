# S4 — Extended reproducibility detail

Supplementary detail for Section 11 of the paper. Nothing here is a result.

---

## S4.1 What the replication package contains

- The runtime governance implementation, normalized QA Policy IR, and QA-XML front end/schema.
- The frozen benchmark definition at version `pilot-v7-rc4` and the frozen
  candidate definition.
- The deterministic validation tests named in Section 7.1, together with the
  machine-readable Claim--Evidence--Boundary map, trust-boundary inventory,
  deterministic end-to-end trace, and exact commands used to execute them.
- The successor QA-OFF qualification namespace: run manifest, per-cell raw
  evidence, the classification ledger, and the frozen analyzer's analysis
  artifact.
- The dated governance records stating the verdict, the invalidated cells, and
  the reason confirmatory execution was not entered.
- The figure-generation scripts.

## S4.2 What it does not contain, and why

The confirmatory chain is implemented to store, in non-overwriting namespaces:

```
registration_draft.json
eligibility_manifest.json
registration_manifest.json
randomization_mc_provenance.json
assignment_manifest.json
execution rows (with runtime snapshots)
final_analysis_manifest.json
```

**None of these files exists.** That chain has never been run, because
qualification returned HOLD and confirmatory execution was not entered. The
package therefore contains no confirmatory registration, assignment, execution,
or analysis artifact.

The historical Phase-P qualification is retained separately as
benchmark-engineering evidence. It underlies no claim in the paper.

## S4.2a Frozen measurement instrument — operational definitions

Full wording for the four non-endpoint dimensions named in Section 6.4 of the
paper. Definitions only; no measured value exists for any of them.

| Dimension | Metric | Operational definition |
| --- | --- | --- |
| Utility | Task success rate | Fraction of runs that satisfy the legitimate task objective. |
| Utility | False rejection rate | Required benign actions blocked by governance, over required benign actions. |
| Recovery | Safe recovery rate | Faulted runs that transition to an allowed, task-sufficient fallback without unnecessary risky behavior. |
| Efficiency | End-to-end latency; QA latency | Wall-clock task time, and incremental governance-processing time. |
| Efficiency | Tokens, model calls, tool calls, cost | Resource use recorded per run, with unknown monetary cost retained as missing rather than imputed. |
| Evidence | Trace completeness | Presence of proposal, policy reference, decision, execution disposition, and outcome required by the evidence schema. |

The six **prospectively specified endpoints** — the primary endpoint
(unsafe-action execution) and the five fixed-sequence secondaries
(safety/security violation, unsafe action proposed, constraint violation, privacy
leak, attack success) — remain named in the paper body. They are
applicability-scoped, so structurally inapplicable rows remain null rather than
missing, and interception recall is descriptive, keeping proposal exposure
separate from execution prevention. **None of them is measured anywhere**,
because the confirmatory matrix that would produce them was never executed.

## S4.3 Digest binding design

Each lifecycle artifact carries a canonical-JSON **self-digest** over its own
semantic content, and each downstream artifact binds the digest of the artifact
above it. The intended properties are:

| Property | Mechanism |
| --- | --- |
| A later stage cannot silently rewrite an earlier one | Downstream digest binding over the upstream artifact |
| An artifact cannot be edited without detection | Canonical-JSON self-digest |
| An ambiguous restart cannot recompute a different assignment, position, or final analysis | Crash-safe reservation and publication rules |
| Cross-bound or malformed artifacts cannot be normalized into usable evidence | Machine-enforced immediate-stop conditions |

These are properties of the implemented design. Because no confirmatory study was
entered, they are reported as implementation, not as executed evidence.

## S4.4 Deterministic validation commands

Two contexts run different subsets, and the difference is a property of the
evidence rather than a packaging convenience.

**From the replication package root**, which carries no version-control history:

```
$ python analysis/verify_manifest.py
  PASS - every file in the package is listed and hashes correctly.
$ python analysis/verify_released_counts.py
  PASS - every released count cross-checked; cell accounting recomputed
$ cd code && python scripts/submission_artifact.py verify-mechanism
  MECHANISM VERIFIED
```

**From a full checkout of the source repository**, additionally:

```
$ make verify-qualification
  QUALIFICATION VERIFIED
$ make verify-paper
  PAPER EVIDENCE VERIFIED
$ make verify-anonymity
  ANONYMITY VERIFIED (... exact checked scope ...)
$ make verify-artifact
  ARTIFACT VERIFIED
```

The qualification gate replays the frozen lifecycle against recorded
version-control objects, one of which is reachable only through a retained
pull-request head ref, so it is not runnable from an unpacked archive and is not
shipped as a package command. It fails with a named prerequisite error, never
silently, when those objects are absent. `verify_released_counts.py` is the
package-side substitute: it recomputes the cell-level accounting from the
released classification ledger and per-cell evidence and cross-checks every
number the manuscript prints against the released analyzer artifact.

The commands resolve and deduplicate exact pytest node IDs from
`artifact/claim_evidence_manifest.json`, execute them, validate retained
qualification accounting, and byte-compare generated paper evidence. CI runs
the complete deterministic suite in addition to this reviewer path. None of
these commands contacts a provider or reruns qualification.

## S4.5 Anonymity of the package

For double-anonymous review the artifact is provided as an anonymized snapshot
that removes author-identifying metadata while preserving the experimental
record. It is not distributed through a public repository link, because such a
link would identify the authors. The anonymity check is executable: it scans the
manuscript source, supplement, contracts, export paths, hidden files, and, when
present, PDF bytes and author/keyword metadata, and it reports exactly which of
those scopes it covered rather than a bare pass.

**Declared residual.** The frozen governance, candidate, benchmark and
qualification records retain the version-control object identifiers that bind
them to the commits under which they were produced. Those identifiers are part
of the chain of custody and are not rewritten, because rewriting a frozen record
is precisely what this lifecycle forbids. They carry no name, path or URL, but
they are linkable identifiers: if the source repository were publicly readable,
a hosted commit-search query would map any one of them back to it. The
repository is therefore not public, and the anonymity of this package is stated
as conditional on that. The verifier fails closed if such an identifier appears
anywhere outside those declared records --- in the manuscript source, the
supplement, the package prose, or the analysis and figure scripts.
