# FSE Submission Readiness Checklist (as of pilot-v5 + targeted ablation)

This checklist separates what is already done (backed by artifacts indexed
in `results/pilot-v5-evidence-manifest.md`) from what remains before the
manuscript (`FSE_2027_IQA_SOA_Draft_v0.1.docx`) is submission-ready. It does
not itself execute anything.

## Benchmark extension
- [x] pilot-v5 frozen and hash-verified (12 tasks, 2 model families).
- [x] Ablation-readiness audit complete; injection/privacy/budget
      non-identifiability documented with root causes.
- [x] Coverage-extension task families specified
      (`docs/preregistration_coverage_extension_v1.md`), not yet authored as
      benchmark files.
- [ ] Author and freeze the new task families as a versioned benchmark
      (e.g. `pilot-v6`) without touching `pilot-v5`.
- [ ] Run 6-cell (or family-appropriate) real-model smoke on the new
      benchmark for both model families before any measured run, exactly
      as pilot-v5's smoke gate did.
- [ ] Run the full matched two-model experiment on the new benchmark.
- [ ] Run injection/privacy/budget ablations once their task clusters are
      confirmed identifiable from real evidence (not assumed).
- [ ] Optionally combine with an external/public agent-security benchmark
      to address the still-open "Benchmark Bias" threat.

## Baselines
- [x] No-QA (OFF) and Full-IQA-SOA (FULL) real-model baselines, two model
      families, pilot-v5.
- [ ] Partial-QA (G1) has only ever been run under the deterministic
      fixture (Phase 1), never with a real model. Decide whether the paper
      needs a real-model G1 arm or whether G0/G2 plus the component
      ablation (which already subsumes "partial" governance at guard
      granularity) is sufficient; state the decision explicitly either way.
- [ ] Consider whether a non-IQA-SOA baseline governance mechanism (e.g. a
      simple keyword/regex output filter, or an existing open-source
      guardrail library) is expected by reviewers as a comparison point.
      Not currently in scope; flag as a possible reviewer request.
- [ ] A third model family (beyond Qwen and Mistral) would strengthen RQ3
      but is optional, not blocking, given the explicit two-model scope of
      this study.

## Statistics
- [x] Task-cluster bootstrap + sign-flip randomization procedure already
      implemented and used (`iqa_soa.metrics.pilot`/`statistics`).
- [x] Manuscript explicitly states why 5 repetitions are not 5 independent
      task samples and why p < 0.05 is not claimed for the primary safety
      result (Section 7.6).
- [ ] Once coverage-extension task clusters exist, re-run the task-cluster
      test with the enlarged n_independent_tasks and report whether the
      safety effect becomes statistically distinguishable at conventional
      thresholds -- report honestly if it still does not.
- [ ] Decide and preregister a multiple-comparisons policy before running
      the coverage-extension guards' ablations (currently only 2 of a
      planned 6 ablations have been run; the remaining 4 will add
      additional comparisons).

## Figures
- [x] P1-P4 generated per model and combined for the pilot-v5 main
      experiment, visually inspected.
- [ ] No figure yet visualizes the targeted-ablation component-specificity
      result (Table 2) or the coverage-extension results once available;
      consider a dedicated ablation-specificity figure (e.g. a 2x3 grid:
      guard-removed x task, colored by outcome) for the camera-ready.
- [ ] Figure/table numbering in the manuscript should be reconciled with
      final LaTeX/Word camera-ready style (current numbering is
      provisional: Table 1 = treatment configs, Table 2 = ablation
      results, Table 3 = main results).

## Related Work
- [ ] Section 10 explicitly still contains no real citations (by design,
      per the existing draft note). A systematic literature search across
      FSE/ICSE/ASE and relevant security/AI venues is required before
      submission; this task does not fabricate any citation.
- [ ] Position IQA-SOA specifically against: LLM agent safety/red-teaming
      work, LLM guardrail systems (input/output filters), self-adaptive
      software (MAPE-K), and runtime verification/policy enforcement, per
      the four subsections already scaffolded.

## Threats to Validity
- [x] Nine new threats added from real pilot-v5/ablation evidence (Section
      9), alongside the five original design-level threats.
- [ ] Re-evaluate "Limited Task-Cluster Coverage" and "Non-Identifiability
      of Injection/Privacy/Budget" threats once the coverage extension
      runs; downgrade or remove only with new evidence, never preemptively.

## Artifact / reproducibility
- [x] `results/pilot-v5-evidence-manifest.md` indexes every authoritative
      artifact path, hash, model digest, and known anomaly.
- [x] Raw JSONL/evidence for every indexed run is immutable and untouched.
- [ ] Prepare an anonymized replication package (Appendix A item 8,
      already listed in the draft): strip any local paths/usernames,
      verify no credential values are present (the existing
      `_assert_no_credential_values` check already ran at collection time,
      but a final pre-submission sweep of the packaged archive is still
      advisable), and include `benchmark/pilot-v5/`,
      `results/pilot-v5-evidence-manifest.md`, the indexed raw/processed/
      figure directories, and the analysis/figure-generation scripts.
- [ ] Decide double-anonymous handling for the replication package (remove
      author-identifying paths/usernames such as `C:\Users\User\...`).

## Manuscript polish
- [x] RQ1/RQ2/RQ4/RQ5 preserved from the existing draft; RQ3 (Cross-Model
      Robustness) added without deleting the original RQ3 (renumbered to
      RQ4, Runtime Overhead).
- [x] Section 7 converted from a template ("Expected Analysis") to real
      Results, organized by RQ, with an explicit statistical-interpretation
      subsection.
- [x] Section 6 gained a Results subsection (6.1) reporting the two
      identifiable ablations and explaining why the other four were not
      run.
- [x] Abstract updated with one hedged, non-overclaiming sentence
      summarizing the core finding.
- [ ] Authors/affiliations remain `[TBD]` pending the double-anonymous
      submission decision -- not addressed by this pass, intentionally.
- [ ] A full read-through pass for tone/length/consistency once Related
      Work and the coverage extension are in, since new subsections were
      inserted programmatically and should be proofread as continuous
      prose before camera-ready.

## Current bottom line
The manuscript now reports **real, artifact-backed pilot-v5 results** for
RQ1, RQ2, RQ3, RQ4, and RQ5, with correctly hedged statistical language and
an expanded Threats to Validity section. It is **not yet submission-ready**:
Related Work has no citations, the injection/privacy/budget coverage gap is
only preregistered (not executed), and the replication package has not been
assembled. See the final Chinese report (Part 3, item M) for a readiness
estimate.

---

## Current status (2026-09-04) - post successor QA-OFF qualification

The sections above are the historical pilot-v5-era checklist and are retained
unchanged. This section supersedes them for submission planning. It records
status only; it authorizes no execution.

**Manuscript of record:** `FSE_2027_IQA_SOA_Draft_v0.5.docx` (supersedes the
v0.1 references above; v0.1-v0.4 are retained unmodified).
**Claim audit:** `docs/fse2027_post_successor_manuscript_gap_audit.md`.

### Lifecycle status

- [x] Phase-P real-model qualification - COMPLETE, HOLD / UNQUALIFIED,
      non-confirmatory, preserved unrepaired.
- [x] Post-Phase-P prospective redesign - COMPLETE and frozen.
- [x] Successor QA-OFF qualification (`prospective-candidate-i5-m1-b76f40da2`)
      - **COMPLETE / HOLD**. 102 scheduled cells, 102 observed, 0 retries,
      3 invalidated, 7 of 17 tasks qualified, terminal status
      `SCHEDULE_COMPLETE_VERDICT_HOLD`.
- [x] Corrected analysis and forensic diagnosis recorded additively; two
      authoritative `MATRIX_INVALID` blockers remain and the verdict is `HOLD`
      independently of the reclassified pre-execution bookkeeping entry.
- [ ] Confirmatory eligibility - **NO**.
- [ ] Confirmatory execution - **NOT ENTERED**.
- [ ] Production randomization - **NOT REALIZED**.
- [ ] Rerun / retry / replacement / rescoring - **NOT AUTHORIZED**.

### Manuscript integration status

- [x] Abstract, Introduction, 4.3, 5.1, 6.6, 7.1, new 7.2, 8.3, 9, 11, 12 and
      Appendix A/B synchronized to the successor `HOLD`.
- [x] New Section 7.2 reports the qualification factually (metrics table,
      invalidated-cells table, task disposition, diagnostic semantics, explicit
      non-claims).
- [x] Successor diagnostics (`RISKY_INSTRUCTION_PROPAGATED`,
      `UNSUPPORTED_COMPLETION_CLAIM`, `NONCANONICAL_RESOURCE_SELECTION`)
      reported as non-exposure; frozen exposure counts unchanged.
- [x] All QA-effect estimates remain `[TBD]`; Sections 7.3-7.6 unchanged in
      substance apart from renumbering.
- [ ] Related Work systematic expansion - still open (no citation invented).
- [ ] ACM template conversion and anonymization - still open.
- [ ] Anonymized replication package - still open; must now include the
      successor qualification namespace and the dated governance records.

### Remaining evidence gaps

See section 5 of `docs/fse2027_post_successor_manuscript_gap_audit.md` (G1-G9).
The binding one is G1: no candidate has yet satisfied QA-OFF qualification, so
no confirmatory registration, assignment, execution, or inference exists.

---

## Current status (2026-09-04, second pass) - `[TBD]` burn-down

The sections above are retained unchanged. This section records the placeholder
burn-down only; it authorizes no execution and changes no result.

**Manuscript of record:** `FSE_2027_IQA_SOA_Draft_v0.6.docx` (supersedes v0.5 for
planning; v0.1-v0.5 are retained unmodified on disk).
**Burn-down audit:** `docs/fse2027_tbd_burndown_audit.md`.

### Placeholder totals

| Category | Count |
| --- | ---: |
| `CAN_FILL_NOW` | 0 |
| `STRUCTURAL_PLACEHOLDER` | 10 |
| `REQUIRES_NEW_EVIDENCE` | 79 |
| `WITHDRAW` | 0 |
| Total inventoried (v0.5) | 89 |

Markers fell from 89 to 79 (bare `[TBD]`: 82 to 74). The ten resolved markers are
the author line, three draft/abstract self-references, the five confirmatory
registration rows in Section 7.1 - now stated as explicit absences ("Not
registered", "Not evaluated", "Not applicable") - and the Appendix A checklist
self-reference. All 79 remaining markers sit in Sections 7.3-7.6 and are
`REQUIRES_NEW_EVIDENCE`: 24 in 7.3, 14 in 7.4, 17 in 7.5, 24 in 7.6.

`CAN_FILL_NOW` is zero because every already-known fact class (qualification
status, 102/102 cells, 0 retries, 3 invalidated cells, 7/17 and 10/17 task
counts, confirmatory eligibility and execution state, diagnostics, artifact
availability, architecture, deterministic validation, frozen task inventory,
established limitations) had already been backfilled in v0.5. `WITHDRAW` is zero
because no placeholder belongs to a superseded analysis.

### Unchanged lifecycle state

- Successor QA-OFF qualification - COMPLETE / **`HOLD`**; 102 scheduled, 102
  observed, 0 retries, 3 invalidated, 7 of 17 tasks qualified.
- Confirmatory eligibility - **NO**. Confirmatory execution - **NOT ENTERED**.
- Rerun / retry / replacement / rescoring - **NOT AUTHORIZED**.
- No QA treatment effect, p-value, confidence interval, effect size, significance
  claim, or provider/model ranking is reported anywhere in v0.6.
