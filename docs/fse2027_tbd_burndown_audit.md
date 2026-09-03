# FSE 2027 manuscript `[TBD]` burn-down and evidence-backfill audit

**Audit date:** 2026-09-04
**Canonical repository base:** `f7145c20625128288f3e43827ad51971797739e3` (`origin/main`, fresh-fetched)
**Source manuscript:** `FSE_2027_IQA_SOA_Draft_v0.5.docx`
(SHA-256 `dd8e92c8fc19fa216751eaee0c8161641a30298e6af39e940a12098f98164aaa`, preserved byte-for-byte)
**Produced manuscript:** `FSE_2027_IQA_SOA_Draft_v0.6.docx`
**Paper:** *Who Controls the Agent? Runtime Quality Assurance for Safe and
User-Controllable LLM Agents* (IQA-SOA, repository `Lei-TzuY/iqa-soa`)

---

## 0. Boundary declaration

This pass is documentation and manuscript maintenance. It contacted no provider,
made no Ollama contact, performed no model inference, executed no qualification,
ran no rerun, retry, cell replacement, rescoring or confirmatory execution,
realized no production randomization, and engineered no exposure. It redesigned
no benchmark and fabricated no statistic, p-value, confidence interval or effect
size.

Successor qualification remains **`HOLD`**. Confirmatory eligibility remains
**NO**. Confirmatory execution remains **NOT ENTERED**. Rerun remains
**NOT AUTHORIZED**.

Nothing under `results/` changed, and no production code changed.

---

## 1. Evidence admitted by this burn-down

| Source | Role |
| --- | --- |
| `results/prospective-candidate-i5-m1-b76f40da2-qualification/` | canonical successor QA-OFF qualification evidence (read-only) |
| `docs/post_phaseP_successor_qualification_analysis_correction.{md,json}` | corrected analysis; two authoritative blockers; verdict `HOLD` |
| `docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.{md,json}` | `HOLD` decomposition |
| `docs/post_phaseP_successor_qualification_hash_basis_amendment.{md,json}` | additive working-tree hash-basis amendment |
| `docs/post_phaseP_prospective_redesign_decision.md` | prospective semantics of the redesigned diagnostics |
| `docs/fse2027_post_successor_manuscript_gap_audit.md` | claim classification and gaps G1–G9 |
| `docs/fse_submission_checklist.md`, `docs/paper_mapping.md`, `findings.md`, `progress.md` | manuscript-state records |

Historical Phase-P result rows were not used as manuscript values. No content
from `Lei-TzuY/Quality_Assurance` enters this manuscript.

### Binding successor facts used

| Field | Value |
| --- | --- |
| QA mode | OFF only |
| Scheduled cells | 102 |
| Observed cells | 102 |
| Retries | 0 |
| Invalidated cells | 3 |
| Qualified tasks | 7 of 17 |
| Unqualified tasks | 10 of 17 |
| Terminal status | `SCHEDULE_COMPLETE_VERDICT_HOLD` |
| Verdict | `HOLD` |
| Confirmatory eligibility | NO |
| Confirmatory execution | NOT ENTERED |

Invalidated cells, retained in full in §7.2 of the manuscript:
`qwen|BEN-002|583010984` (`PROVIDER_INFRA_FAILURE`),
`mistral|BEN-003|583010984` (`MODEL_PROTOCOL_INVALID`),
`mistral|BEN-003|1723431918` (`MODEL_PROTOCOL_INVALID`).
None was dropped, merged, or softened.

---

## 2. Categories and the rule used to separate them

| Category | Definition |
| --- | --- |
| `CAN_FILL_NOW` | Admissible canonical evidence directly supplies a positive replacement value. |
| `STRUCTURAL_PLACEHOLDER` | The field must not stay ambiguous, but the scientifically correct value is an explicit absence (“Not evaluated”, “Not entered”, “Not applicable”, “No estimate available”). |
| `REQUIRES_NEW_EVIDENCE` | The value cannot be supplied without a new experiment or analysis that has not been authorized or executed, and the paper still plans to report it. |
| `WITHDRAW` | The placeholder belongs to an obsolete or superseded claim and should no longer appear. |

**Separation rule applied.** §7.1 is a *lifecycle-status* table: its first three
rows already report current state, so the remaining rows are completed with the
explicit absence that is currently true (`STRUCTURAL_PLACEHOLDER`). §§7.3–7.6
are *result* tables that carry no meaning until confirmatory data exist; filling
every cell with “not entered” would be noise, and the manuscript genuinely still
plans to report those numbers, so their markers are retained
(`REQUIRES_NEW_EVIDENCE`). This is the only boundary where two categories could
plausibly have been swapped, and it is recorded here deliberately.

**Result limit honoured.** No QA-treatment-effect cell was filled from QA-OFF
qualification data. The successor study establishes no QA ON vs QA OFF effect,
no unsafe-action reduction, no treatment effect, no causal improvement, no
statistical significance, and no model or provider ranking.

---

## 3. Inventory part A — resolved placeholders (10)

### TBD-001 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Title block (front matter) |
| Nearby text (v0.5) | Authors: [TBD for double-anonymous submission] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Authors: withheld for double-anonymous review. |
| Evidence basis | FSE double-anonymous submission policy; `docs/fse_submission_checklist.md` (author/affiliation handling left open pending the anonymity decision). |
| Reason | The author list is not missing evidence. Under double-anonymous review the scientifically and editorially correct value is an explicit withholding statement, not an open placeholder. |
| New evidence required | None. |

### TBD-002 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Front-matter DRAFT-ONLY note |
| Nearby text (v0.5) | …all QA FULL vs. QA OFF effect estimates remain intentionally [TBD]. |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | …all QA FULL vs. QA OFF effect estimates remain unreported pending confirmatory execution. |
| Evidence basis | Successor qualification verdict `HOLD`; confirmatory eligibility NO; confirmatory execution NOT ENTERED (`docs/post_phaseP_successor_qualification_analysis_correction.md`; gap audit §1). |
| Reason | A self-referential mention of the placeholder scheme, not a field awaiting a value. The lifecycle state is fully determined, so it is stated in words. The note is also re-versioned to v0.6. |
| New evidence required | None. |

### TBD-003 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Abstract |
| Nearby text (v0.5) | Confirmatory effect estimates remain deliberately [TBD] until the final registered matrix is executed. |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Confirmatory effect estimates are therefore deliberately not reported until the final registered matrix is executed. |
| Evidence basis | Same lifecycle state as TBD-002; gap audit §3.9 and §3.11 (`NOT_YET_SUPPORTED`). |
| Reason | A bracketed placeholder token does not belong in an abstract. The sentence already carries the correct meaning once the marker is written out; no claim changes. |
| New evidence required | None. |

### TBD-004 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Section 7 DRAFT-ONLY note |
| Nearby text (v0.5) | …supporting descriptive tables in Sections 7.3–7.6 remain [TBD]. |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | …supporting descriptive tables in Sections 7.3–7.6 are held open pending confirmatory execution. |
| Evidence basis | Gap audit §3.11; `docs/paper_mapping.md` current-status RQ table (RQ1–RQ4 have no admissible evidence today). |
| Reason | Self-referential mention, not a field awaiting a value. Rewritten so the note states the reason rather than pointing at a marker. |
| New evidence required | None. |

### TBD-005 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Table in §7.1, row “Final benchmark / registration version”, column “Final value” |
| Nearby text (v0.5) | [TBD] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Not registered — no confirmatory registration finalized |
| Evidence basis | Confirmatory execution NOT ENTERED; no Stage-C final registration exists (`docs/fse_submission_checklist.md` lifecycle status; gap audit §3.11, gaps G1/G5). |
| Reason | §7.1 is a lifecycle-status table whose first three rows already report current state (Phase-P `HOLD / UNQUALIFIED`; successor `HOLD`; confirmatory eligibility No). The truthful current value of this row is an explicit absence, not an unknown. |
| New evidence required | None to state the current value. A future positive value needs G1 (a qualified candidate) and Stage-C registration. |

### TBD-006 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Table in §7.1, row “Final eligibility outcome”, column “Final value” |
| Nearby text (v0.5) | [TBD] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Not evaluated — pre-outcome eligibility not entered |
| Evidence basis | Stage-B pre-outcome eligibility was never entered; gap audit §3.11 and checklist lifecycle status. |
| Reason | As TBD-005. “Not evaluated” is the established state, and leaving it ambiguous invites a reader to assume an eligibility decision exists. |
| New evidence required | None to state the current value. A future value needs frozen Stage-B eligibility on a qualified candidate. |

### TBD-007 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Table in §7.1, row “Registered confirmatory task count K”, column “Final value” |
| Nearby text (v0.5) | [TBD] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Not registered — no confirmatory task count fixed |
| Evidence basis | No Stage-C registration; gap audit G1/G2 (only 7 of 17 tasks satisfy their frozen roles, so no K is fixed). |
| Reason | K is a registration parameter, not a measurement. It is unfixed, and the qualified-task count must not be presented as if it were a registered K. |
| New evidence required | None to state the current value. A future K needs Stage-C final registration on a qualified candidate. |

### TBD-008 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Table in §7.1, row “Registered provider/model strata”, column “Final value” |
| Nearby text (v0.5) | [TBD] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Not registered — no confirmatory provider/model strata fixed |
| Evidence basis | No Stage-C registration; gap audit §3.11 and §3.12. |
| Reason | The two qualification arms are not registered confirmatory strata, and writing them here would misrepresent QA-OFF qualification provenance as confirmatory registration. The qualification arms remain reported in Appendix B. |
| New evidence required | None to state the current value. A future value needs registered strata under Stage-C. |

### TBD-009 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Table in §7.1, row “Protocol deviations / missing primary positions”, column “Final value” |
| Nearby text (v0.5) | [TBD — must satisfy frozen totality rules] |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | Not applicable — no confirmatory matrix executed |
| Evidence basis | Confirmatory execution NOT ENTERED; gap audit §3.11, gap G5 (the confirmatory chain has never been exercised end to end). |
| Reason | Deviations and missing primary positions are defined relative to a registered confirmatory matrix. No such matrix exists, so the field is not applicable rather than unknown. The three invalidated *qualification* cells are unaffected and remain reported in full in §7.2. |
| New evidence required | None to state the current value. A future value needs an executed confirmatory matrix. |

### TBD-089 — STRUCTURAL_PLACEHOLDER

| Field | Value |
| --- | --- |
| Section / table | Appendix A, final checklist bullet |
| Nearby text (v0.5) | …remove all DRAFT-ONLY notes, [TBD] scaffolding, and the author-only checklist before submission. |
| Category | `STRUCTURAL_PLACEHOLDER` |
| Replacement in v0.6 | …remove all DRAFT-ONLY notes, remaining placeholder scaffolding, and the author-only checklist before submission. |
| Evidence basis | None required — editorial wording only. |
| Reason | A mention of the placeholder scheme, not a placeholder. Reworded so the marker inventory is not inflated by a self-reference; the instruction it carries is unchanged. |
| New evidence required | None. |

---

## 4. Inventory part B — retained placeholders (79)

Every entry below is `REQUIRES_NEW_EVIDENCE`, and every one is a confirmatory
result cell in §§7.3–7.6 that the manuscript still plans to report. The marker
is retained verbatim; no long governance commentary was added to any cell,
because the section-level draft note already states why the cells are open.

| ID | Section | Row | Column | Retained marker | Reason |
| --- | --- | --- | --- | --- | --- |
| TBD-010 | §7.3 | Unsafe action executed | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-011 | §7.3 | Unsafe action executed | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-012 | §7.3 | Unsafe action executed | p-value | `[TBD]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-013 | §7.3 | Unsafe action executed | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-014 | §7.3 | Safety/security violation | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-015 | §7.3 | Safety/security violation | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-016 | §7.3 | Safety/security violation | p-value | `[TBD / gate closed]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-017 | §7.3 | Safety/security violation | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-018 | §7.3 | Unsafe action proposed | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-019 | §7.3 | Unsafe action proposed | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-020 | §7.3 | Unsafe action proposed | p-value | `[TBD / gate closed]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-021 | §7.3 | Unsafe action proposed | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-022 | §7.3 | Constraint violation | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-023 | §7.3 | Constraint violation | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-024 | §7.3 | Constraint violation | p-value | `[TBD / gate closed]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-025 | §7.3 | Constraint violation | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-026 | §7.3 | Privacy leak | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-027 | §7.3 | Privacy leak | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-028 | §7.3 | Privacy leak | p-value | `[TBD / unavailable / gate closed]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-029 | §7.3 | Privacy leak | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-030 | §7.3 | Attack success | K (K+) | `[TBD]` | No registered task count and no executed positions exist, so no K or K+ can be written. |
| TBD-031 | §7.3 | Attack success | Mean D_k (FULL − OFF) | `[TBD]` | A FULL−OFF task difference requires both arms; the successor study has a single treatment (QA OFF) and supports no contrast. |
| TBD-032 | §7.3 | Attack success | p-value | `[TBD / unavailable / gate closed]` | No randomization test has been run; writing any p-value would be fabrication. |
| TBD-033 | §7.3 | Attack success | Decision | `[TBD]` | Fixed-sequence gate decisions exist only after the frozen analyzer runs on registered data. |
| TBD-034 | §7.4 | QA OFF arm | Model | `[TBD]` | The registered confirmatory strata are not fixed; qualification arm identities must not be substituted for them. |
| TBD-035 | §7.4 | QA OFF arm | Task success | `[TBD]` | No registered utility observation exists for this treatment arm. |
| TBD-036 | §7.4 | QA OFF arm | Median steps | `[TBD]` | No registered completion-step observation exists for this treatment arm. |
| TBD-037 | §7.4 | QA OFF arm | Safe recovery | `[TBD]` | No registered fault-recovery observation exists for this treatment arm. |
| TBD-038 | §7.4 | QA FULL arm | Model | `[TBD]` | The registered confirmatory strata are not fixed; qualification arm identities must not be substituted for them. |
| TBD-039 | §7.4 | QA FULL arm | Task success | `[TBD]` | No registered utility observation exists for this treatment arm. |
| TBD-040 | §7.4 | QA FULL arm | False rejection | `[TBD]` | No governed real-model arm exists, so no false-rejection rate has been measured. |
| TBD-041 | §7.4 | QA FULL arm | Median steps | `[TBD]` | No registered completion-step observation exists for this treatment arm. |
| TBD-042 | §7.4 | QA FULL arm | Safe recovery | `[TBD]` | No registered fault-recovery observation exists for this treatment arm. |
| TBD-043 | §7.4 | PARTIAL arm | Model | `[TBD]` | The registered confirmatory strata are not fixed; qualification arm identities must not be substituted for them. |
| TBD-044 | §7.4 | PARTIAL arm | Task success | `[TBD]` | No registered utility observation exists for this treatment arm. |
| TBD-045 | §7.4 | PARTIAL arm | False rejection | `[TBD]` | No governed real-model arm exists, so no false-rejection rate has been measured. |
| TBD-046 | §7.4 | PARTIAL arm | Median steps | `[TBD]` | No registered completion-step observation exists for this treatment arm. |
| TBD-047 | §7.4 | PARTIAL arm | Safe recovery | `[TBD]` | No registered fault-recovery observation exists for this treatment arm. |
| TBD-048 | §7.5 | QA OFF | End-to-end latency | `[TBD]` | No registered timing observation exists for this treatment arm. |
| TBD-049 | §7.5 | QA OFF | Tokens | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-050 | §7.5 | QA OFF | Model calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-051 | §7.5 | QA OFF | Tool calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-052 | §7.5 | QA OFF | Cost/task | `[TBD]` | No registered cost observation exists; unknown cost is retained as missing and never imputed. |
| TBD-053 | §7.5 | QA FULL | End-to-end latency | `[TBD]` | No registered timing observation exists for this treatment arm. |
| TBD-054 | §7.5 | QA FULL | QA latency | `[TBD]` | Governance-processing time can only be measured with governance enabled on registered positions. |
| TBD-055 | §7.5 | QA FULL | Tokens | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-056 | §7.5 | QA FULL | Model calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-057 | §7.5 | QA FULL | Tool calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-058 | §7.5 | QA FULL | Cost/task | `[TBD]` | No registered cost observation exists; unknown cost is retained as missing and never imputed. |
| TBD-059 | §7.5 | PARTIAL | End-to-end latency | `[TBD]` | No registered timing observation exists for this treatment arm. |
| TBD-060 | §7.5 | PARTIAL | QA latency | `[TBD]` | Governance-processing time can only be measured with governance enabled on registered positions. |
| TBD-061 | §7.5 | PARTIAL | Tokens | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-062 | §7.5 | PARTIAL | Model calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-063 | §7.5 | PARTIAL | Tool calls | `[TBD]` | No registered resource observation exists for this treatment arm. |
| TBD-064 | §7.5 | PARTIAL | Cost/task | `[TBD]` | No registered cost observation exists; unknown cost is retained as missing and never imputed. |
| TBD-065 | §7.6 | FULL - Injection | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-066 | §7.6 | FULL - Injection | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-067 | §7.6 | FULL - Injection | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-068 | §7.6 | FULL - Injection | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-069 | §7.6 | FULL - Privacy | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-070 | §7.6 | FULL - Privacy | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-071 | §7.6 | FULL - Privacy | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-072 | §7.6 | FULL - Privacy | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-073 | §7.6 | FULL - Permission | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-074 | §7.6 | FULL - Permission | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-075 | §7.6 | FULL - Permission | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-076 | §7.6 | FULL - Permission | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-077 | §7.6 | FULL - Budget | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-078 | §7.6 | FULL - Budget | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-079 | §7.6 | FULL - Budget | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-080 | §7.6 | FULL - Budget | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-081 | §7.6 | FULL - Output Validation | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-082 | §7.6 | FULL - Output Validation | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-083 | §7.6 | FULL - Output Validation | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-084 | §7.6 | FULL - Output Validation | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-085 | §7.6 | FULL - Evidence | Unsafe execution Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-086 | §7.6 | FULL - Evidence | Task-success Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-087 | §7.6 | FULL - Evidence | False-reject Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |
| TBD-088 | §7.6 | FULL - Evidence | Latency Δ | `[TBD]` | An ablation delta requires an executed FULL reference and an executed minus-one configuration. |

### Evidence basis and required new evidence, by table

| Section | Evidence basis today | New evidence required |
| --- | --- | --- |
| §7.3 (24 markers) | Gap audit §§3.3, 3.8, 3.9, 3.11 — all `NOT_YET_SUPPORTED`; `docs/paper_mapping.md` RQ1 = no admissible evidence. | G1 qualified candidate; Stage-A/B/C registration frozen; prospective assignment persisted; every registered QA OFF and QA FULL position executed (G4); frozen analyzer run producing the registered fixed-sequence outcome. |
| §7.4 (14 markers) | Gap audit §§3.3, 3.8 — no governed real-model arm exists; `docs/paper_mapping.md` RQ2 = none. | G1 plus an executed registered QA FULL (and PARTIAL, if separately registered) arm carrying the frozen utility endpoints (G4). |
| §7.5 (17 markers) | Gap audit §§3.8, 3.15 — no governed arm and no exercised confirmatory chain; `docs/paper_mapping.md` RQ3 = none. | G1 plus per-treatment timing and resource collection over the executed registered matrix (G4/G5). |
| §7.6 (24 markers) | Gap audit §§3.8, 3.9 — exploratory ablations have no executed reference; `docs/paper_mapping.md` RQ4 = none. | G1 plus executed FULL and FULL-minus-one configurations; remains exploratory unless separately preregistered (G4). |

---

## 5. Why `CAN_FILL_NOW` is zero

Each fact class that could remove a placeholder was checked against the current
manuscript, and every one had already been backfilled in v0.5:

| Already-known fact | Where it already appears | Placeholder left to remove |
| --- | --- | --- |
| Successor qualification status / verdict | §7.1 table, §7.2 table and prose, §12 | none |
| Scheduled / observed cell counts (102 / 102) | §7.2 table, Abstract, §1 | none |
| Retry count (0) | §7.2 table and prose | none |
| Invalidated-cell count and identities (3) | §7.2 metrics table and invalidated-cells table | none |
| Qualified / unqualified task counts (7 / 17, 10 / 17) | §7.2 table and prose | none |
| Confirmatory eligibility (NO) | §7.1 and §7.2 tables | none |
| Confirmatory execution state (NOT ENTERED) | §7.1 table, §7.2 prose, §12 | resolved as TBD-005–009 (an explicit absence, not a positive value) |
| Diagnostic observations (PI-018, PRIV-017) | §7.2 prose, verbatim and non-exposure | none |
| Artifact availability | §11, Appendix B | none |
| Implemented architecture / mechanism facts | §§2–4 | none |
| Deterministic validation status | §§4.2–4.3 | none |
| Frozen dataset / task inventory | §5, §7.2 task disposition | none |
| Explicitly established limitations | §9 (observed measurement and protocol limitations) | none |

No remaining placeholder had a positive canonical value available, so
`CAN_FILL_NOW` is **0**. Anything that could have been written into §§7.3–7.6
from the QA-OFF qualification would have been a treatment-effect or ranking
claim, which the result limit and gap-audit §§3.8–3.10 forbid.

---

## 6. Why `WITHDRAW` is zero

Every placeholder-bearing analysis is still part of the planned paper:

- §7.3 carries the **primary confirmatory contrast** (QA FULL vs QA OFF on
  `unsafe_action_executed`) and the registered fixed-sequence secondaries.
- §7.4 and §7.5 are **supporting** utility and overhead reporting, explicitly
  scoped as supporting in §6.5 and in the Appendix A checklist.
- §7.6 is **exploratory** FULL-minus-one component contribution, explicitly
  scoped as exploratory unless separately preregistered.

The historical five-RQ mapping in the pre-2026-09 part of `docs/paper_mapping.md`
(where the old “RQ4 quality trade-offs” row lived) was already superseded by the
manuscript's four-RQ structure before v0.5, and no placeholder in v0.5 belongs to
it. No superseded claim therefore needed removal, and nothing was deleted from
the manuscript to reduce the count.

---

## 7. Totals

| Category | Count |
| --- | ---: |
| `CAN_FILL_NOW` | 0 |
| `STRUCTURAL_PLACEHOLDER` | 10 |
| `REQUIRES_NEW_EVIDENCE` | 79 |
| `WITHDRAW` | 0 |
| **Total inventoried** | **89** |

| Metric | v0.5 | v0.6 |
| --- | ---: | ---: |
| `[TBD…]` markers (all forms) | 89 | 79 |
| bare `[TBD]` markers | 82 | 74 |
| annotated markers (`[TBD / …]`, `[TBD — …]`) | 7 | 5 |
| markers resolved | — | 10 |

Every removed marker maps to exactly one entry in §3 (TBD-001–009, TBD-089).
Every remaining marker maps to a `REQUIRES_NEW_EVIDENCE` entry in §4.

---

## 8. Verification record for `FSE_2027_IQA_SOA_Draft_v0.6.docx`

| Check | Result |
| --- | --- |
| v0.5 SHA-256 unchanged | PASS — `dd8e92c8…164aaa` |
| v0.6 reopened programmatically | PASS — 463 paragraphs, same count as v0.5 |
| DOCX ZIP integrity (`testzip`) | PASS |
| Package parts preserved | PASS — no part added or removed |
| Styles, numbering, theme, footer, all three images, relationships, font table, settings | PASS — byte-identical to v0.5 |
| Heading outline and section numbering | PASS — unchanged |
| References and citation markers | PASS — unchanged |
| Tables | PASS — none added, removed, or restructured; only cell text intentionally edited |
| Paragraphs changed | 12 — 10 placeholder resolutions plus two version labels (v0.5 → v0.6) |
| v0.6 marker count ≤ v0.5 | PASS — 79 ≤ 89 |
| All remaining markers inside §§7.3–7.6 | PASS — 24 / 14 / 17 / 24 |
| Fabricated p-value, CI, effect size or significance claim | NONE — automated scan returned 0 hits |
| Manuscript still states successor qualification `HOLD` | PASS |
| Confirmatory execution presented as completed | NO |
| Three invalidated cells still present with their classes | PASS |
| Result files changed | NONE |
| Production code changed | NONE |

---

## 9. Disposition

The manuscript's placeholder scaffolding is now separated into two honest
states: fields whose current value is an explicit, evidence-backed absence, and
fields that are genuinely waiting on a confirmatory execution that has not been
authorized. Nothing was filled to reduce the count, and nothing was deleted to
reduce the count.

| Item | State |
| --- | --- |
| Successor qualification | COMPLETE / `HOLD` |
| Confirmatory eligibility | NO |
| Confirmatory execution | NOT ENTERED |
| Rerun / retry / replacement / rescoring | NOT AUTHORIZED |
| Provider contacted by this pass | NO |
| Model inference performed by this pass | NO |
| Result files changed | NONE |
| Production code changed | NONE |
