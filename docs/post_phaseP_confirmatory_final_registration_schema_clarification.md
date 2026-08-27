# Post-Phase-P confirmatory `FINAL_REGISTRATION_FROZEN` schema clarification

**Record kind:** binding implementation-schema addendum — Stage-C persisted representation.
**Status:** SCHEMA CLARIFICATION. Not a statistical-methodology decision. Not a randomization-design decision. Not an eligibility-semantics decision. Not a Stage-A or Stage-B schema decision. Not code.
**Date:** 2026-08-27
**Branch:** `post-phasep-confirmatory-final-registration-schema-clarification`
**Base commit:** `f672814` (`origin/main`) — merge of PR #23, which carries `CONFIRMATORY_ELIGIBILITY_SCHEMA_CLARIFICATION_DECISION: ELIGIBILITY_SCHEMA_AND_RUNTIME_CARDINALITY_FROZEN`.
**Implementation branch inspected read-only:** `origin/post-phasep-confirmatory-randomization-implementation` — inspected with `git show` only. Not merged, not cherry-picked, not copied, not modified by this document.
**Subject:** the eight unfrozen Stage-C representation items `U-C1`–`U-C8` returned by `STAGE_C_PERSISTED_REPRESENTATION_NOT_FROZEN`.

---

## 0. Boundary declaration

This document creates exactly one file — itself. It modifies no existing file. It writes no `src/`, no tests, runs no `pytest`, runs no `mypy`, contacts no provider, model, or network, draws no randomness, stages nothing, and commits nothing.

**Frozen and NOT reopened by anything below:**

- statistical methodology, the analysis contract, and every estimand/multiplicity/alpha decision;
- the confirmatory randomization design, the assignment mechanism, `b_k`, the statistic, and the enumeration/Monte Carlo threshold;
- eligibility semantics: the four predicates, their order, the first-failure rule, and the six disposition tokens;
- the Stage-A `RegistrationDraftV1` schema, as frozen by the Stage-A clarification and amended in exactly one nested field by Stage-B clarification §12;
- the Stage-B `EligibilityManifestV1` schema in every respect;
- the canonical JSON profile and the `self_digest` algorithm (implementation design §5.B.2), which remain owned by Work Unit 1;
- the three-stage lifecycle and the nine-state machine (implementation design §5.A, §6);
- `RuntimeSnapshotV1` and its two-layer identity contract (implementation design §5.I).

What this document does is strictly narrower: it fixes the **persisted representation** of the Stage-C artifact `registration_manifest.json`, and nothing else.

Throughout, unqualified section references are:

- **design decision** — `docs/post_phaseP_confirmatory_randomization_design_decision.md`
- **implementation design** — `docs/post_phaseP_confirmatory_randomization_implementation_design.md`
- **authorization** — `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md`
- **Stage-A clarification** — `docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md`
- **Stage-B clarification** — `docs/post_phaseP_confirmatory_eligibility_schema_clarification.md`

```
ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_PROVIDER_ELIGIBILITY_ASSESSMENT_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO
HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO
```

---

## 1. Why this document exists

Work Unit 3 (`freeze_final_registration` in `src/iqa_soa/experiment/confirmatory_registration.py`, implementation design §16 step 3, authorized by authorization §4-§5) stopped **before code** and returned `STAGE_C_PERSISTED_REPRESENTATION_NOT_FROZEN`.

The stop was correct. Every Stage-C *derivation* is frozen — Stage-A clarification §13.1 proves that every value `FINAL_REGISTRATION_FROZEN` freezes traces to a Stage-A field, an immutable eligibility-manifest field, a global frozen constant, or a deterministic derivation, and §13.4 closes that proof with `ALL_FINAL_REGISTRATION_VALUES_TRACEABLE: YES`. What is *not* frozen is the persisted representation those values take. Stage-A clarification §13.3 states this explicitly for `matrix_digest`: "That is a **Stage-C** representation matter, outside this addendum's four-gap remit, and it is **not opened here**." The same is true of the top-level key set, the record shapes, the array rules, and the runtime/statistical carry-forward shapes.

| # | Unfrozen Stage-C representation item | Closed at |
|---|---|---|
| **U-C1** | exact `registration_manifest.json` top-level key set | §4 |
| **U-C2** | Stage-C `schema_version` literal | §5 |
| **U-C3** | exact persisted field names for task membership, restricted repetitions, ordinary provider seeds, registered `K` | §6 |
| **U-C4** | exact persisted `ConfirmatoryPositionV1` record shape | §7 |
| **U-C5** | ordering / uniqueness rules for the four Stage-C arrays | §8 |
| **U-C6** | exact `matrix_digest` preimage | §9 |
| **U-C7** | exact Stage-C runtime-identity representation | §10 |
| **U-C8** | exact carry-forward of the frozen statistical configuration/constants | §11 |

This document resolves **all and only** `U-C1`–`U-C8`.

---

## 2. Binding inputs, and the read-only facts this document is built on

Read in full for this record, read-only, not modified, not reopened, not reinterpreted:

1. `docs/post_phaseP_confirmatory_randomization_design_decision.md` (Revision 4).
2. `docs/post_phaseP_confirmatory_randomization_implementation_design.md` (Revision 3).
3. `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md`.
4. `docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md` (Revision 1).
5. `docs/post_phaseP_confirmatory_eligibility_schema_clarification.md`.

The implementation design remains authoritative except where this document fills the explicitly unresolved Stage-C persisted representation.

### 2.1 Interface facts, read from the pushed implementation branch

Inspected with `git show origin/post-phasep-confirmatory-randomization-implementation:<path>` only. Nothing was merged, cherry-picked, or copied.

| # | Fact | Read at |
|---|---|---|
| **G1** | Work Unit 3 is genuinely unimplemented: no `freeze_final_registration`, no `RegistrationManifest` type, and no `registration_manifest.json` schema exists anywhere under `src/`. The only occurrence of the string `registration_manifest` is a docstring sentence in `confirmatory_eligibility.py`. | `git grep` over `src/` |
| **G2** | `ProposedPositionV1.identity_payload()` already returns exactly the six identity keys `{model, provider, provider_seed, repetition, slot, task_id}` and deliberately does **not** hash them: "deriving `position_id` is Stage-C work." | `confirmatory_registration.py` |
| **G3** | `canonical_json_bytes`, `compute_self_digest`, `attach_self_digest`, `verify_self_digest`, `serialize_artifact`, `parse_artifact` are already implemented and exported as the single owned realization of implementation design §5.B.2. Stage C reuses them; it defines no second algorithm. | `confirmatory_registration.py` |
| **G4** | `ProposedRuntimeConfigurationV1.registration_expected_runtime_identity_digest(provider, model)` already exists and looks a stratum's expected identity up "by the exact `(provider, model)` pair, never by position and never by fallback." | `confirmatory_registration.py` |
| **G5** | `EligibilityStratumRecordV1` persists exactly `{disposition, infrastructure_symmetry_audit, model, predicates, provider, runtime_identity_digest}`, and `disposition` is `field(init=False)` — derived on construction and separately cross-checked against the persisted token at E19. | `confirmatory_eligibility.py` |
| **G6** | Both existing artifacts are written with an exclusive create (`path.open("xb")`), so an existing artifact is never replaced, truncated, or edited in place. | `confirmatory_registration.py`, `confirmatory_eligibility.py` |
| **G7** | `_require_design_id` already enforces a single safe path segment, and the `*_path()` helpers already require the resolved path to stay inside `confirmatory_root`. | `confirmatory_registration.py` |
| **G8** | No literal `RegistrationManifestV1` — or any other candidate Stage-C `schema_version` literal — occurs anywhere in `docs/` or `src/`. The literal minted at §5 conflicts with nothing. | `grep` over `docs/`, `src/` |

### 2.2 Conventions observed, and applied below without exception

Carried forward verbatim from Stage-B clarification §3, because a third artifact in one chain must obey one set of rules:

- **C1 — schema-version naming.** PascalCase noun phrase, `V1` suffix, no underscores: `RegistrationDraftV1`, `EligibilityManifestV1`, `RuntimeSnapshotV1`, `ProposedStatisticalConfigurationV1`, `ConfirmatoryPositionV1`.
- **C2 — which nested objects carry `schema_version`.** A nested object carries one **if and only if** already-frozen upstream text assigns it one. No nested type minted by this document receives one.
- **C3 — array ordering is either *sorted* or *semantic*, never "implementation may choose".**
- **C4 — recorded derivations are cross-checked, never trusted.** A derivable value that is nevertheless recorded is recomputed by the loader and compared; a mismatch is refused.
- **C5 — no same-object digest alias, ever** (implementation design §5.B.1).
- **C6 — no field a loader cannot check** offline, from the manifest plus its two bound upstream artifacts.

### 2.3 One additional convention, stated because Stage C is where it first bites

- **C7 — record a derivable value only where a frozen downstream consumer names it.** C4 says *how* to treat a recorded derivation; C7 says *when* to record one at all. Stage C can derive many things from its own position array. Recording each of them would multiply the sources of truth for one fact and add validation surface with no consumer — exactly the redundancy this clarification's design principle forbids. The line is drawn at frozen downstream behavior: a derivable value earns a persisted field when some already-frozen consumer reads it *by name*, and not otherwise. §6 applies C7 to task membership, repetitions, seeds, and `K`, and reaches opposite answers for different concepts on exactly this basis.

---

## 3. Classification principle

**[SCHEMA — FROZEN]** Every persisted Stage-C value falls into exactly one of five classes:

> **A. `STAGE_A_COPY`** — copied verbatim from the validated, immutable `registration_draft.json`.
>
> **B. `STAGE_B_COPY`** — copied verbatim from the validated, immutable `eligibility_manifest.json`.
>
> **C. `DETERMINISTIC_DERIVATION`** — computed with no new choice from A and B under already-frozen rules.
>
> **D. `GLOBAL_FROZEN_LITERAL`** — a constant fixed by the binding methodology/design documents and stamped by implementation.
>
> **E. `FREEZE_CAPTURE_METADATA`** — the instant of the freeze itself, **captured internally by `freeze_final_registration`, never supplied by a caller.** Exactly one field is in this class, `created_at` (§4.4), and it is admitted only because Stage-A clarification §13.1 row 27 already names it as a final registered value: "Freeze timestamp (`created_at`-class field on the manifest) — Capture metadata — Recorded at freeze; never an equality invariant."

**No Stage-C persisted value falls into a sixth class such as "caller chooses."** Class E is emphatically **not** a caller-choice class: it is one field, produced by the Stage-C sealing operation itself, unreachable through any parameter, and never an equality invariant anywhere. **`FREEZE_CAPTURE_METADATA` has exactly one member, `created_at`, and no other timestamp field exists at any depth of this artifact.** §12 classifies every field of §4.3 and proves the classification exhaustive.

**Every one of the sixteen persisted fields therefore answers NO to "may the caller choose it?"** (§12). Class E is the only class that is not a copy, a derivation, or a literal, and it is still not a choice.

---

## 4. `RegistrationManifestV1` — top-level schema frozen (closes U-C1)

### 4.1 Top-level field set — exactly these sixteen fields, no more, no fewer

**[SCHEMA — FROZEN]** `registration_manifest.json` contains exactly:

```
schema_version
registration_state
confirmatory_profile
design_id
created_at
registration_draft_digest
eligibility_manifest_digest
confirmatory_strata
descriptive_only_strata
confirmatory_positions
descriptive_positions
K
randomization_mode
registered_statistical_configuration
matrix_digest
self_digest
```

**Exactly sixteen keys.** A persisted manifest with a seventeenth key, or missing any one of the sixteen, is malformed and is refused (§16 F1). There are no optional keys, no alternative shapes, and no conditional presence: every one of the sixteen is present in every manifest, in every design, at every `K`.

Frozen literal values:

```
schema_version        = "RegistrationManifestV1"                      (§5)
registration_state    = "FINAL_REGISTRATION_FROZEN"                   (implementation design §5.A, §6)
confirmatory_profile  = "post_phaseP_confirmatory_randomization_v1"   (implementation design §5.C)
```

`registration_state` is the field name both sibling artifacts already use for the same lifecycle — `registration_draft.json` with `"REGISTRATION_DRAFT"` (Stage-A clarification §4.2) and `eligibility_manifest.json` with `"ELIGIBILITY_FROZEN"` (Stage-B clarification §4.2). One lifecycle, one registration, one field name, one uniform check across three artifacts. No `final_registration_state` and no `manifest_state` exists.

### 4.2 Where each concept named by the Stage-C freeze list lives

Implementation design §5.A Stage C names the values `FINAL_REGISTRATION_FROZEN` freezes. This table decides, for each, which field carries it — including the three concepts that deliberately receive **no** field of their own.

| Concept (implementation design §5.A Stage C, and the U-C1 enumeration) | Carried by | Section |
|---|---|---|
| Schema identity | `schema_version` | §5 |
| Lifecycle state | `registration_state` | §4.1 |
| Design family | `confirmatory_profile` | §4.1 |
| Design identity | `design_id` | §4.4 |
| Freeze instant | `created_at` | §4.4 |
| Upstream draft binding | `registration_draft_digest` | §4.4 |
| Upstream eligibility binding | `eligibility_manifest_digest` | §4.4 |
| Confirmatory strata (provider/model membership) | `confirmatory_strata` | §8.1 |
| Descriptive-only strata | `descriptive_only_strata` | §8.1 |
| Confirmatory position IDs, and every confirmatory position record | `confirmatory_positions` | §7, §8.2 |
| Descriptive position IDs, and every descriptive position record | `descriptive_positions` | §7, §8.2 |
| **Task membership** | **no separate field** — the distinct `task_id` values of `confirmatory_positions` | §6.1 |
| **Repetitions** | **no separate field** — the `repetition` values carried by the position records | §6.2 |
| **Ordinary provider seeds** | **no separate field** — the `provider_seed` field of each position record | §6.3 |
| Registered `K` | `K` | §6.4 |
| `randomization_mode` | `randomization_mode` | §15 |
| Statistic version `statistic_spec_id` | `registered_statistical_configuration.statistic_spec_id` | §11 |
| Registered `M` (`randomization_mc_samples`) | `registered_statistical_configuration.randomization_mc_samples` | §11, §15 |
| Registered statistical configuration (alpha, multiplicity, endpoints, estimand, aggregation, orientation, threshold) | `registered_statistical_configuration` | §11 |
| Baseline schedule `S_k` | `baseline_label` on every position record | §7, §14 |
| Runtime identity binding | `confirmatory_strata[*].runtime_identity_digest` | §10 |
| Final confirmatory matrix digest | `matrix_digest` | §9 |
| Artifact self-authentication | `self_digest` | §17 |

### 4.3 Per-field type freeze

**[SCHEMA — FROZEN]**

| Field | JSON type | Content rule | Class (§3) |
|---|---|---|---|
| `schema_version` | string | exactly `"RegistrationManifestV1"` | D |
| `registration_state` | string | exactly `"FINAL_REGISTRATION_FROZEN"` | D |
| `confirmatory_profile` | string | exactly `"post_phaseP_confirmatory_randomization_v1"` | D |
| `design_id` | string | non-empty; equal byte-for-byte, as a string value, to the bound draft's and the bound eligibility manifest's `design_id`; a single safe path segment (G7). **[DEFERRED VALUE SELECTION]** — no value is chosen here | A |
| `created_at` | string | RFC 3339 UTC instant, `Z` designator mandatory, whole-second precision, no fractional seconds, no non-`Z` offset: `YYYY-MM-DDTHH:MM:SSZ`. **Captured internally by `freeze_final_registration` at the sealing event; never a parameter, never caller-supplied** (§4.4.1) | E |
| `registration_draft_digest` | string | lowercase 64-character hex SHA-256; equals `registration_draft.json`'s `self_digest` | C |
| `eligibility_manifest_digest` | string | lowercase 64-character hex SHA-256; equals `eligibility_manifest.json`'s `self_digest` | C |
| `confirmatory_strata` | array of `ConfirmatoryStratumV1` | possibly empty; sorted ascending by `(provider, model)`; unique on that key (§8.1) | C (membership), A (runtime digest) |
| `descriptive_only_strata` | array of two-key stratum objects | possibly empty; sorted ascending by `(provider, model)`; unique on that key (§8.1) | C |
| `confirmatory_positions` | array of `ConfirmatoryPositionV1` | possibly empty; sorted ascending by `(task_id, provider, model, repetition, slot)`; unique on that key (§8.2) | A (Stage-A fields), C (`position_id`, membership) |
| `descriptive_positions` | array of `ConfirmatoryPositionV1` | possibly empty; identical element schema, ordering, and uniqueness rules (§8.2) | A (Stage-A fields), C (`position_id`, membership) |
| `K` | JSON integer `>= 0` | equals the number of distinct `task_id` values in `confirmatory_positions` (§6.4, §15) | C |
| `randomization_mode` | string | exactly `"EXACT_ENUMERATION"` or `"MONTE_CARLO"`, derived from `K` (§15) | C |
| `registered_statistical_configuration` | object | exactly the eleven-key `ProposedStatisticalConfigurationV1` object, equal to the draft's by exact parsed-object equality (§11.2, §11.2.1) | A (`randomization_mc_samples`), D (the other ten) |
| `matrix_digest` | string | lowercase 64-character hex SHA-256 over the §9 preimage | C |
| `self_digest` | string | lowercase 64-character hex SHA-256 per implementation design §5.B.2, unchanged | C |

### 4.4 The five chain/identity fields, stated exactly

- **`design_id`** is copied from the bound draft. It is never minted at Stage C. §16 F28 and F35 require it to equal the draft's and the eligibility manifest's, byte-for-byte.
- **`created_at`** is the instant at which the final registration was **finalized and sealed** — the single moment the confirmatory matrix became immutable. Because the manifest is written exactly once, atomically, and can never be edited or re-frozen in place (§17), there is exactly one such instant per manifest. It uses the identical grammar as `registration_draft.json.created_at` and `eligibility_manifest.json.created_at`, so one rule and one validator serve the whole chain. Its capture contract is frozen at §4.4.1.

  **Stage C does require one, under the frozen lifecycle.** `FINAL_REGISTRATION_FROZEN` is the state the entire prospective claim rests on: design decision §7.4.2 conditions **E** and **F** require the randomization machinery to be "fixed and documented before any confirmatory outcome exists" and "generated and persisted under an auditable procedure before inspection of any confirmatory outcome," and implementation design §6 orders `FINAL_REGISTRATION_FROZEN` strictly before `MC_PROVENANCE_PERSISTED`, `ASSIGNMENT_PERSISTED`, and every execution. Without a recorded freeze instant the chain carries no timestamp for the one state that must precede everything, and the auditable-ordering obligation could not be discharged from the artifacts alone. Stage-A clarification §13.1 row 27 already names this field as a final registered value; §4.1 gives it the chain's existing name and grammar and nothing more.
- **`registration_draft_digest`** and **`eligibility_manifest_digest`** are the two upstream references implementation design §5.B.1 already froze for this artifact. They are the *only* two.
- **`self_digest`** is the one and only digest this artifact stores about itself. Downstream artifacts call this value `final_registration_digest`; that name is **never** a second field here (C5; implementation design §5.B.1: `registration_manifest.json` "does NOT store: `final_registration_digest`").

### 4.4.1 `created_at` capture contract — frozen

**[SCHEMA — FROZEN]** `created_at` is **not caller-selectable**. It is produced by the Stage-C freeze operation itself.

| # | Rule |
|---|---|
| **T1** | **`freeze_final_registration` captures `created_at` internally, exactly once, per invocation.** There is no second capture, no re-capture, and no recomputation on any later path. |
| **T2** | **The caller must not supply `created_at`.** `freeze_final_registration` exposes **no** `created_at` parameter, no clock parameter, no "as-of" parameter, and no override of any name. There is no interface through which a caller could propose, inject, adjust, or backdate the value. |
| **T3** | The captured value is a **whole-second UTC instant with a mandatory `Z` designator**, rendered under the already-frozen chain grammar `YYYY-MM-DDTHH:MM:SSZ` (§4.3). Sub-second precision is truncated **by the capture itself**, at the point of capture, as part of producing the value — this is rendering the instant the operation captured, not rewriting a value someone supplied. |
| **T4** | Capture occurs as Stage-C freeze metadata **on the successful construction/sealing path only**: after the partition (§13), the position construction (§14), and every §16 F1-F37 check that does not depend on it have been satisfied, and **strictly before `self_digest` is computed** and **strictly before any byte reaches disk** (§9.7 step 4, §16 F38, F39). A construction that fails never captures an instant, and a captured instant never exists without a sealed artifact. |
| **T5** | The captured value **is** a field of `registration_manifest.json` and is therefore inside the `self_digest` preimage — it is authenticated by `self_digest` like every other field (§9.7 step 4, §17.1). |
| **T6** | `created_at` remains **excluded from `matrix_digest`** (§9.4). Two identical matrices frozen at different instants are the same matrix. |
| **T7** | `created_at` is **not a cross-artifact equality invariant.** It need not, and ordinarily will not, equal `registration_draft.json.created_at` or `eligibility_manifest.json.created_at` — those record earlier stages of the same lifecycle. **No rule anywhere in this document compares it against any other artifact's timestamp**, and none may be added. This is the frozen treatment of capture metadata (implementation design §5.I.2 pattern; Stage-A clarification §13.1 row 27: "never an equality invariant"). |

**Where backdating is prevented, stated exactly.** Prevention is a **construction/write-time** property, not a loader property, and the two are not interchangeable:

- **Construction/write time (T1-T4, §16 F38).** Backdating is prevented **structurally**: the value is captured by the operation, and no parameter exists through which a caller could supply a different one. A caller cannot backdate what it cannot reach. This is the same structural technique §8.4 already uses for array ordering and §11.5 uses for `randomization_mode` — remove the interface, not merely the permission.
- **Load time (§16 F6).** F6 remains, unchanged, a **syntax and type validation of the persisted `created_at`**: it checks the string against `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` and nothing more.

**A loader cannot prove historical wall-clock truth after the fact, and this document does not claim it can.** No rule here asserts that a loader can establish, from the artifact alone, that a persisted `created_at` is the real instant at which the freeze occurred. That guarantee comes from the construction path's structure (T1-T4) plus the `self_digest` and downstream-reference chain that makes any post-hoc edit of the sealed value detectable (§17.2) — not from any check F6 or any other loader rule performs. Claiming otherwise would be a guarantee the artifact cannot support.

### 4.5 Digest inventory — restated, unamended

```
registration_manifest.json:
    stores:         registration_draft_digest    (= registration_draft.json.self_digest)
    stores:         eligibility_manifest_digest  (= eligibility_manifest.json.self_digest)
    stores:         matrix_digest                (§9)
    stores:         self_digest
    does NOT store: final_registration_digest

    Downstream meaning: final_registration_digest := registration_manifest.json.self_digest
```

Identical to implementation design §5.B.1 and §5.B.3. Nothing is added, removed, or renamed.

### 4.6 What the manifest deliberately does **not** carry

Named explicitly so no implementer supplies them. Every one is structurally impossible under §16 F1 and the exact key sets of §7, §8.1, and §11; §16 F25 restates the prohibition so an auditor can check it directly.

- **No `final_registration_digest`** — a same-object alias of its own `self_digest` (§4.5, C5).
- **No `assignment_digest`, `randomization_mc_provenance_digest`, or any other downstream reference.** Both artifacts are downstream of Stage C and do not exist yet (implementation design §6).
- **No assignment material of any kind** — no `task_assignment_bit`, `bits`, `b_k`, `task_order`. Design decision §4.D draws `b_k` two states later; **no assignment bit exists at Stage C**, and a registration that carried one would no longer be assignment-invariant.
- **No Monte Carlo seed material** — no `seed_hex`, `entropy_bytes`, `source_kind`, `source_api`, `seed_encoding`, `rng_library`, `rng_bit_generator`, `numpy_version`, `generated_at`, `exact_support_size`. All are fields of `randomization_mc_provenance.json` (implementation design §5.L.2, §5.L.3), generated after this artifact is sealed. **No MC seed exists at Stage C.**
- **No realized execution value** — no `qa_mode`, `observation_status`, `failure_class`, `error`, `runtime_snapshot_digest`, endpoint value, or row count. Execution begins three states later.
- **No analysis output** — no p-value, `K_plus`, `T_max`, `p_min`, `theta_*`, or interval.
- **No recaptured runtime.** No `RuntimeSnapshotV1` object, no `captured_at`, no snapshot `self_digest`. **No provider/runtime recapture occurs at Stage C** (§10.3).
- **No Stage-A proposal names** — no `proposed_tasks`, `proposed_strata`, `proposed_repetitions`, `proposed_provider_seeds`, `proposed_positions`, `proposed_runtime_configuration`, `proposed_statistical_configuration`. Stage C persists *registered* values; the proposals remain registered and digest-authenticated in the draft, bound here by `registration_draft_digest`.
- **No Stage-B assessment material** — no `eligibility_records`, `predicates`, `disposition`, `infrastructure_symmetry_audit`, `evidence_refs`, `assessed_at`. All remain registered in the eligibility manifest, bound here by `eligibility_manifest_digest`. Stage C carries the *consequence* of the dispositions — which side of the partition each object landed on — never a second copy of the dispositions themselves.

`REGISTRATION_MANIFEST_TOP_LEVEL_SCHEMA_FROZEN: YES.`

---

## 5. `schema_version` — the Stage-C literal (closes U-C2)

**[SCHEMA — FROZEN]** The Stage-C artifact's `schema_version` literal is exactly:

```
"RegistrationManifestV1"
```

Justified by C1 and G8: it matches the repository's frozen naming convention exactly (`RegistrationDraftV1`, `EligibilityManifestV1` — PascalCase noun phrase, `V1` suffix, no underscores), it names the artifact it versions (`registration_manifest.json`), it matches the public type the implementation design already names — implementation design §5.A: `freeze_final_registration(...) -> RegistrationManifest` — and no conflicting literal exists anywhere in `docs/` or `src/`.

**There is no alias and no alternative literal.** `FinalRegistrationV1`, `ConfirmatoryMatrixV1`, and every other candidate are not this schema's version and are refused by §16 F2. There is no version negotiation and no multi-version loader.

`STAGE_C_SCHEMA_VERSION_FROZEN: YES.`

---

## 6. Registered value field names — task membership, repetitions, seeds, `K` (closes U-C3)

This section answers, for each of the four concepts, whether it needs a persisted field of its own. The governing rule is C7 (§2.3): **record a derivable value only where a frozen downstream consumer names it.** Three of the four concepts get no field; one does. Each answer is argued from the frozen text, not from symmetry with the §5.A prose list.

### 6.1 Task membership — **no separate field**

**[SCHEMA — FROZEN]** There is **no** `confirmatory_tasks`, `registered_tasks`, `task_membership`, or `descriptive_tasks` field. The registered confirmatory task-cluster set is exactly:

```
{ position.task_id : position in confirmatory_positions }
```

and the descriptive-only task set is the analogous set over `descriptive_positions`.

**Why this is lossless.** Stage-A clarification §4.5 V5 requires `proposed_repetitions` to cover the full cross product `proposed_tasks × proposed_strata` exactly once each with every `repetition_count >= 1`, and V6 requires `proposed_positions` to contain exactly two positions (`slot = 1`, `slot = 2`) for every such entry at every `repetition ∈ {0, …, R−1}`. Every proposed task therefore contributes **at least two** proposed positions under **every** proposed stratum. Because the Stage-C partition is total and element-wise (§13), every proposed task appears in at least one of the two position arrays, and a task appears in `confirmatory_positions` **if and only if** at least one of its positions belongs to a `CONFIRMATORY_ELIGIBLE` stratum. That is precisely the frozen Stage-C task-membership rule of Stage-A clarification §8.2 and §13.1 row 5, reproduced with no separate field.

**Why no field is nevertheless correct under C7.** No frozen downstream consumer reads a task list from the manifest by name. Implementation design §5.G fixes the analyzer's structural property as iterating "the **registered** position list from `registration_manifest.json`"; §5.M draws one bit per task cluster "in sorted `task_id` order" over the registered confirmatory positions; §5.K takes `K` "from `len(registration_manifest.confirmatory_positions)` grouped by task". Every frozen consumer already reaches task membership *through the positions*. A parallel task array would be a second source of truth for a fact the positions already fix exactly, and its only possible loader rule would be "recompute it from the positions and compare."

**This still satisfies the frozen Stage-C requirement.** Implementation design §5.A Stage C requires final registration to freeze "task membership". It is frozen: immutable (the position arrays are immutable), digest-authenticated (`matrix_digest` and `self_digest` both cover `confirmatory_positions`), and exactly determined with no residual choice. Freezing a value and giving it a dedicated JSON key are different things, and only the first is required.

### 6.2 Repetitions — **no separate field**

**[SCHEMA — FROZEN]** There is **no** `repetitions`, `registered_repetitions`, or `repetition_counts` field. Each position record carries its own `repetition` (§7), and the registered repetition count for a retained `(task_id, provider, model)` cell is exactly the number of distinct `repetition` values that cell's positions carry in the array that holds them.

**Why this is lossless.** V6 enumerates positions over `repetition ∈ {0, …, R−1}` contiguously from zero for each cell, and Stage-A clarification §4.3 fixes `repetition` as a 0-based JSON integer `>= 0` ([OBSERVED] `runner.py:379`). The count is therefore `1 + max(repetition)` for that cell, and equivalently the cardinality of its distinct `repetition` values; the two agree because V6 admits no gaps. Because the partition removes whole strata, and a stratum's removal takes every one of its cells with it (§13), a retained cell keeps its complete repetition range — **no cell is ever partially filtered.**

**Why no field is nevertheless correct under C7.** `proposed_repetitions` is a *construction input* to the position enumeration, not an independent registered fact: V6 makes `proposed_positions` a function of it. No frozen downstream consumer names a repetition-count field of the manifest. The analyzer reconciles rows against registered positions (§5.C), not against counts; the runner executes registered positions; `PAIR_KEYS` / `matched_contrast_key` are "already encoded by the six identity fields" (Stage-A clarification §10.3). Persisting a restricted copy of `proposed_repetitions` would add validation surface with no consumer.

### 6.3 Ordinary provider seeds — **no separate field**

**[SCHEMA — FROZEN]** There is **no** `provider_seeds`, `registered_provider_seeds`, or `seeds` field. Each position record carries its own `provider_seed` (§7), copied verbatim from the immutable Stage-A proposed position, and it is one of the six fields inside the `position_id` preimage.

**Why this is lossless.** The ordinary provider seed is already frozen as a function of the repetition index alone (Stage-A clarification §4.3, [OBSERVED] `runner.py:380, 695-701`; design decision F5 and §10 "one seed per repetition, fixed at freeze"), and V8 requires every proposed position's `provider_seed` to equal the `proposed_provider_seeds` entry for that position's `repetition`. The repetition-to-seed map restricted to the confirmatory matrix is therefore exactly `{(p.repetition, p.provider_seed) : p ∈ confirmatory_positions}`, single-valued by V8. A repetition index whose positions are all descriptive-only contributes no confirmatory seed — correctly, because no confirmatory position runs under it, so it is not part of the confirmatory matrix definition.

**Why no field is nevertheless correct under C7.** The seed's frozen consumers read it *per position*: it is inside the `position_id` preimage (implementation design §5.C), it is a field of the confirmatory execution-row contract (§5.C), and check 7 recomputes `position_id` from a row's own `provider_seed`. Nothing reads a seed table from the manifest.

**These are ordinary provider seeds only.** They are not, and can never become, randomization bits, assignment material, or Monte Carlo seed material (design decision §5.3 item 7; implementation design §5.L, §5.M). Nothing in this section changes that.

### 6.4 Registered `K` — **a field, `K`**

**[SCHEMA — FROZEN]** `K` **is** a top-level field: a JSON integer `>= 0`, equal to the number of distinct `task_id` values in `confirmatory_positions` (§15). It is recorded **and** recomputed by the loader, which refuses any manifest where the two differ (§16 F19) — C4's already-frozen record-and-cross-check pattern, applied here exactly as Stage-B clarification §8.3 and §10.4 apply it.

**Why `K` earns a field where task membership, repetitions, and seeds do not.** `K` has frozen downstream consumers that name it and compare against it across artifacts:

1. Implementation design §5.L.1 requires `registration_manifest.json` itself to freeze `randomization_mode` "derived deterministically from registered `K`", and requires the provenance artifact's mode to equal it.
2. Implementation design §5.L.2 requires the exact-mode provenance artifact to carry its own `K` and `exact_support_size = 2^K`, and §5.L.3 requires the Monte Carlo-mode artifact to carry its own `K`; §5.L.3's analysis-time checks verify these against the registration. A cross-artifact equality check needs a name on both sides.
3. Implementation design §5.K binds the statistic's `K` to the registration ("registered `K` … never from however many task differences happen to be nonzero at analysis time"), and design decision §7.4.1 keeps `K_plus` strictly separate from `K` for exactly this reason.

None of task membership, repetitions, or seeds has any such named cross-artifact consumer. The asymmetry is therefore not a style choice: it is C7 applied to the frozen text, and it produces different answers because the frozen text does.

**Field name.** The literal field name is `K`, not `registered_k`. `K` is already the frozen persisted field name for the identical quantity in a sibling artifact of the same chain (`randomization_mc_provenance.json`, implementation design §5.L.2 and §5.L.3), so one name serves the cross-artifact equality check on both sides and no second spelling of one quantity is introduced. Under implementation design §5.B.2's `sort_keys=True` code-point ordering, `"K"` (U+004B) sorts before every lowercase key and therefore appears first in the canonical serialization; that is a consequence of the frozen canonicalization, not a schema rule of its own.

`REGISTERED_VALUE_FIELD_NAMES_FROZEN: YES.`

---

## 7. `ConfirmatoryPositionV1` — the persisted position record (closes U-C4)

### 7.1 The identity payload is unchanged — still exactly six fields

**Restated from implementation design §5.C and Stage-A clarification §5.1, not amended.** The `position_id` preimage contains exactly:

```
task_id
provider
model
repetition
provider_seed
slot
```

and nothing else. `position_id` is SHA-256 (lowercase hex, canonicalization of implementation design §5.B.2) over the canonical JSON of exactly those six fields. `treatment` and `baseline_label` are excluded, because "the position's identity must not depend on which label it ends up receiving, or the identity itself would leak assignment information and could not be registered before `b_k` is drawn" (implementation design §5.C).

**The six-field preimage is untouched by this document.** `POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES.`

### 7.2 The persisted Stage-C record — exactly eight fields, no more, no fewer

**[SCHEMA — FROZEN]** Every element of `confirmatory_positions` and of `descriptive_positions` contains exactly:

```
position_id       string, lowercase 64-character hex SHA-256   (§7.1, §14)
task_id           string, non-empty
provider          string, non-empty
model             string, non-empty
repetition        JSON integer >= 0                            (0-based)
provider_seed     JSON integer
slot              JSON integer, exactly 1 or 2                 (design decision §4.A)
baseline_label    string, exactly "off" or "full"              (Stage-A clarification §5.3)
```

**These eight fields are exactly the complete record.** The Stage-C record is the seven-field Stage-A `ProposedPositionV1` (Stage-A clarification §5.2) plus exactly one derived field, `position_id`, which "first exists at Stage C" (Stage-A clarification §5.2; [OBSERVED] G2).

Per C2 the record carries no `schema_version`: no frozen upstream text assigns one to `ConfirmatoryPositionV1`, and the manifest's single top-level `schema_version` versions the whole payload including every nested shape.

**Why eight and not more.** The record must support downstream verification of exactly the quantities the frozen row-binding contract compares (implementation design §5.C checks 6, 7, 12): `position_id` membership; independent reproduction of `position_id` from `task_id`/`provider`/`model`/`repetition`/`provider_seed`/`slot`; and `baseline_label` equality against the registered `S_k(position)`. Eight fields discharge all three exactly. Nothing else in the frozen row contract is read *from the registration* — `task_assignment_bit` comes from the assignment manifest (check 11), `qa_mode` is computed at execution by `resolve_label` (check 13), and `runtime_snapshot_digest` / `runtime_identity_digest` are row and stratum concerns (check 14, §10).

**Why eight and not fewer.** Dropping `baseline_label` would destroy `S_k`, which Stage-A clarification §6.1 defines as exactly the complete collection of `(identity fields, baseline_label)` pairs and which check 12 compares against. Dropping `position_id` would force every consumer to recompute an identity the frozen row contract references by name (checks 6, 9, 10). Dropping any identity field would make check 7's independent recomputation impossible.

**No assignment-dependent field is added.** No `treatment`, `qa_mode`, `task_assignment_bit`, `b_k`, `assigned_label`, or `realized_label` exists on the record, at Stage C or ever. `baseline_label` is not assignment-dependent: it is the deterministic counterbalancing output recorded at Stage A, strictly before any bit is drawn (Stage-A clarification §6.2; implementation design §5.D item 1).

### 7.3 Descriptive positions use the identical record representation

**[SCHEMA — FROZEN]** `descriptive_positions` elements have **exactly the same eight-field `ConfirmatoryPositionV1` shape**, with the same types, the same content rules, the same `position_id` derivation, and the same ordering and uniqueness rules (§8.2). There is **no separate descriptive record type and no reduced descriptive shape.**

Three reasons, each from frozen text:

1. Implementation design §5.A Stage C explicitly names "descriptive position IDs" among the values final registration freezes — so descriptive positions carry `position_id`, and Stage-A clarification §13.1 row 12 already froze that derivation as covering "confirmatory **and** descriptive" positions.
2. Stage-A clarification §13.2 makes the position partition total: every proposed position lands in exactly one of the two arrays and none is dropped. A reduced descriptive shape would silently drop registered fields from half the partition, defeating the totality it was frozen to guarantee.
3. One shape means one element validator, one construction function, and one loader path, so the two sides cannot drift.

**The type name is `ConfirmatoryPositionV1` for both arrays.** That name is frozen by implementation design §5.C and names the *record shape of this confirmatory design's registration*, not membership in the confirmatory matrix. Membership is carried by which array an element is in, and by nothing else. Minting a second type name for an identical shape would add vocabulary with no representational content.

`POSITION_RECORD_SCHEMA_FROZEN: YES.`

---

## 8. Array order, uniqueness, and emptiness (closes U-C5)

### 8.1 The two stratum arrays

**[SCHEMA — FROZEN]**

`confirmatory_strata` elements — `ConfirmatoryStratumV1`, exactly three keys:

```
provider                  string, non-empty
model                     string, non-empty
runtime_identity_digest   string, lowercase 64-character hex   (§10)
```

`descriptive_only_strata` elements — exactly two keys:

```
provider                  string, non-empty
model                     string, non-empty
```

The two-key shape is the persisted `ProposedStratumV1` shape unchanged (Stage-A clarification §4.3; `_STRATUM_KEYS = {"model", "provider"}`), so **no new stratum-identifier vocabulary is invented**, no composite `stratum_id` is minted, and no digest of the pair is introduced — exactly the rule Stage-B clarification §6.2 already froze for the same concept. No second record name is minted for it either; it is the same shape in a Stage-C role.

Per C2 neither element carries a `schema_version`.

**The shape asymmetry is the semantics.** A confirmatory stratum carries the runtime identity every later execution of its positions must reproduce; a descriptive-only stratum is never executed under this profile and has no identity for anything to reproduce (§10.2). The extra key exists exactly where a frozen consumer reads it, and nowhere else.

**Neither array carries a `disposition`.** The confirmatory/descriptive split *is* the disposition, coarsened to the only distinction Stage C consumes. The exact per-stratum reason token remains registered, immutable, and digest-authenticated in `eligibility_manifest.json`, bound here by `eligibility_manifest_digest`. A second copy could disagree with the first and has no frozen consumer (C7).

| | `confirmatory_strata` | `descriptive_only_strata` |
|---|---|---|
| **Sort key** (C3, *sorted*) | `(provider, model)` ascending, ordinary Unicode code-point ordering | identical |
| **Uniqueness key** | `(provider, model)` | identical |
| **Cross-array rule** | no `(provider, model)` appears in both arrays (§13.3) | identical |
| **Empty legal?** | YES — every proposed stratum descriptive-only; then `K = 0` (§8.3) | YES — every proposed stratum `CONFIRMATORY_ELIGIBLE` |

### 8.2 The two position arrays

**[SCHEMA — FROZEN]**

| | `confirmatory_positions` | `descriptive_positions` |
|---|---|---|
| **Element schema** | `ConfirmatoryPositionV1`, exactly eight keys (§7.2) | identical |
| **Sort key** (C3, *sorted*) | `(task_id, provider, model, repetition, slot)` ascending — ordinary Unicode code-point ordering on the string components, numeric ordering on the integer components | identical |
| **Uniqueness key** | `(task_id, provider, model, repetition, slot)` | identical |
| **Second uniqueness rule** | `position_id` unique within the array | identical |
| **Cross-array rule** | no `position_id`, and no `(task_id, provider, model, repetition, slot)`, appears in both arrays (§13.3) | identical |
| **Empty legal?** | YES, exactly when `confirmatory_strata` is empty (§8.3) | YES, exactly when `descriptive_only_strata` is empty |

The sort key is the identical key Stage-A clarification §4.3 already froze for `proposed_positions`, so the Stage-C arrays are in the same order as the draft they are filtered from and the merge check of §13.3 is a single linear pass.

`position_id` uniqueness is stated as its own rule even though it follows from placement uniqueness (V8 makes `provider_seed` a function of `repetition`, so distinct placements have distinct six-field identity payloads and therefore distinct digests). It is stated because `position_id` is the key every frozen downstream consumer uses — implementation design §5.C check 6 ("member of the registered position set"), check 9 ("no duplicate confirmatory position execution"), check 10 ("no extra row") — and a contract those checks rest on is asserted where they can see it, not left as a corollary.

### 8.3 Emptiness, and its relationship to `K`

**[SCHEMA — FROZEN]**

1. **Each of the four arrays may be empty.** No minimum cardinality is imposed on any of them.
2. **Both sides may not be empty simultaneously.** `proposed_strata` and `proposed_positions` are both non-empty (Stage-A clarification §4.3) and the partition is total (§13), so at least one stratum array and at least one position array is always non-empty. A manifest with all four arrays empty is structurally impossible and is refused (§16 F11, F18).
3. **Emptiness is coupled, exactly:**

   ```
   confirmatory_positions  is empty   <=>   confirmatory_strata      is empty
   descriptive_positions   is empty   <=>   descriptive_only_strata  is empty
   ```

   Both directions follow from V5/V6: every stratum contributes at least two positions for every proposed task, so a non-empty stratum side always yields a non-empty position side, and an empty stratum side yields none.
4. **At least one confirmatory task is NOT required.** `K = 0` is legal, exactly to the extent already frozen upstream, and **no minimum-`K` rule is invented here.** Stage-A clarification §14 case 7 already froze the `K = 0` outcome: "`K` and `randomization_mode` still derive deterministically (`K ≤ 16 → EXACT_ENUMERATION`, `exact_support_size = 2^0 = 1`). No unregistered choice arises. Whether any inferential output exists is governed by the already-frozen estimability floor (analysis contract §9.8, C9), not by this schema."
5. **The `K = 0` equivalences, stated once:**

   ```
   K = 0   <=>   confirmatory_positions is empty   <=>   confirmatory_strata is empty
   ```

   and when `K = 0`, `randomization_mode = "EXACT_ENUMERATION"` by §15, exactly as at every other `K <= 16`. The exact support size `2^0 = 1` is a field of `randomization_mc_provenance.json` (implementation design §5.L.2), not of this artifact (§4.6).

### 8.4 Unsorted input: construction versus loader validation

**[SCHEMA — FROZEN]** The two paths are different and are frozen separately.

**Construction (`freeze_final_registration`).** The Stage-C arrays are **not caller-supplied**. They are derived by the deterministic partition of §13 from two already-validated immutable artifacts. The draft's `proposed_strata` and `proposed_positions` are already sorted and unique by their own frozen rules (Stage-A clarification §4.3, enforced at load), and the partition is a **stable element-wise filter** of those arrays: it preserves relative order and removes elements, so its output is sorted by construction. **The construction path therefore never sorts, because it never needs to** — it emits the frozen ordering as a consequence of reading a sorted immutable input in order. There is no `sorted()` call, no normalization step, and no interface through which a caller could supply an order at all.

**Loader validation (`load_registration_manifest`).** A persisted manifest whose arrays are out of order, or which carries a duplicate under any uniqueness key of §8.1/§8.2, is **refused** (§16 F9, F10, F14, F15). It is **never re-sorted, never deduplicated, and never repaired on the caller's behalf.** This is implementation design §5.B.2's already-frozen rule — sorting and uniqueness are schema-level rules applied *before* canonicalization, never canonicalization-time transformations — and Stage-B clarification §14's already-frozen fail-closed discipline, applied unchanged.

The distinction matters because the two paths have different obligations: construction must be unable to *emit* a wrong order, and the loader must be unable to *accept* one. Both hold.

`ARRAY_ORDER_AND_UNIQUENESS_FROZEN: YES.`

---

## 9. `matrix_digest` — the exact canonical preimage (closes U-C6)

This is the load-bearing item. Exactly one preimage is frozen; no option survives.

### 9.1 Object, not array — the choice is made, not offered

**[SCHEMA — FROZEN]** The `matrix_digest` preimage is **a canonical JSON object containing named matrix components**, not a canonical array of confirmatory position records.

The array option is **rejected**, for a reason from frozen text rather than taste: a bare array of position records cannot carry the runtime identity under which the matrix must execute, and design decision §10's frozen "Assignment-invariant matrix freeze" table registers "Provider/runtime versions — Frozen for the confirmatory execution window" as a **row of the matrix itself**. An array of positions would therefore authenticate strictly less than the frozen matrix comprises. The same argument disqualifies it for the statistic, weighting, alpha/multiplicity, and assignment-support rows of that table.

### 9.2 The exact preimage — five keys, no more, no fewer

**[SCHEMA — FROZEN]** The preimage object contains exactly:

```
K
confirmatory_positions
confirmatory_strata
randomization_mode
registered_statistical_configuration
```

Each key's value is **the identical value persisted under the same key in `registration_manifest.json`**, as a parsed JSON value — the same arrays, in the same frozen order, with the same element key sets, and the same nested object. Nothing is projected, stripped, re-keyed, re-ordered, or recomputed on the way into the preimage. (The preimage is assembled from the artifact's own in-memory values and then canonicalized once by the frozen §5.B.2 algorithm; no byte comparison is involved at any point. The five-key preimage, its ordering, its exclusions, and its algorithm are unchanged by this wording.) In particular:

- `confirmatory_positions` carries its complete eight-key records (§7.2), `position_id` and `baseline_label` included;
- `confirmatory_strata` carries its complete three-key records (§8.1), `runtime_identity_digest` included;
- `registered_statistical_configuration` carries its complete eleven-key object (§11.2).

### 9.3 Why exactly these five — an exact cover of design decision §10

Every row of design decision §10's frozen matrix-freeze table maps to exactly one preimage key, or to a global frozen constant that is identical for every design under `confirmatory_profile` and therefore cannot differentiate two matrices.

| design decision §10 row | Authenticated by |
|---|---|
| Tasks | `confirmatory_positions` — the distinct `task_id` values (§6.1) |
| Task applicability (`endpoint_applicability`) | Global frozen constant, machine-decidable before execution (analysis contract §6.4; Stage-A clarification §10.3). Its Stage-C consequence is *which* tasks are registered — `confirmatory_positions` |
| Providers / models | `confirmatory_strata` |
| Repetitions / seeds | `confirmatory_positions` — `repetition`, `provider_seed` (§6.2, §6.3) |
| Positions | `confirmatory_positions` |
| Treatment counts / balance (`S_k`, `C(S_k)`) | `confirmatory_positions` — `baseline_label` (Stage-A clarification §6.1, §6.4) |
| Provider / runtime versions | `confirmatory_strata` — `runtime_identity_digest` (§10) |
| Prompt / configuration | `confirmatory_strata` — `prompt_digest`, `experiment_config_digest`, `models_config_digest` are invariant fields inside each `runtime_identity_digest` preimage (implementation design §5.I.1) |
| Stochastic framework | Global frozen constant (design decision §5), identical under `confirmatory_profile` |
| Statistic | `registered_statistical_configuration.statistic_spec_id` |
| Weighting | `registered_statistical_configuration.aggregation_rule` |
| Exclusion rules | The partition itself: the confirmatory side *is* the preimage's position array; the descriptive side is excluded by construction (§9.4) |
| Potential-outcome unit / randomization unit | Global frozen constants (design decision §4.A, §4.D), identical under `confirmatory_profile` |
| Assignment support `{0,1}^K`, `2^{-K}` each | `K` and `randomization_mode` (§9.5) |
| Alpha / multiplicity | `registered_statistical_configuration.alpha`, `.multiplicity_architecture` |

The cover is exact: no §10 row is unauthenticated, and no preimage key authenticates something §10 does not register.

### 9.4 What the preimage excludes, and why — each exclusion deliberate

**[SCHEMA — FROZEN]** The preimage contains **none** of the following.

| Excluded | Reason |
|---|---|
| `matrix_digest` | Self-reference. The digest is not an input to itself. |
| `self_digest` | Computed strictly after `matrix_digest` (§9.7); including it would be circular. |
| `descriptive_only_strata`, `descriptive_positions` | Eligibility descriptive-only reporting material. A descriptive-only stratum can never enter the confirmatory matrix, for any reason, ever (implementation design §5.A post-freeze invariant), so it is not part of the confirmatory matrix *definition*. Both remain registered and are authenticated by `self_digest`. |
| `schema_version`, `registration_state`, `confirmatory_profile` | Artifact/lifecycle metadata, not matrix content. `confirmatory_profile` is constant across every design in this family and cannot differentiate two matrices; all three are authenticated by `self_digest`. |
| `design_id` | `matrix_digest` is a function of the matrix alone. Two designs registering the identical matrix therefore produce the identical `matrix_digest` — an intentional, auditable property. Design identity is authenticated by `self_digest` and carried by `design_id` on every artifact and every execution row (implementation design §5.C check 2). |
| `created_at` | Capture metadata, never an equality invariant (§3 class E; implementation design §5.I.2 pattern). Two identical matrices frozen at different instants are the same matrix. |
| `registration_draft_digest`, `eligibility_manifest_digest` | Provenance of *how* the matrix was derived, not the matrix. Both are authenticated by `self_digest`, and the derivation is separately re-verified element-wise at §16 F29-F36. |
| Future assignment bits (`bits`, `b_k`, `task_assignment_bit`) | Do not exist at Stage C and must not (§4.6). A matrix digest that could change when a bit is drawn would not be assignment-invariant. |
| MC seed / provenance (`seed_hex`, `generated_at`, `exact_support_size`, `randomization_mc_provenance_digest`) | Generated after this artifact is sealed (implementation design §5.L, §6). |
| Execution outcomes (`qa_mode`, `observation_status`, `failure_class`, endpoint values) | Do not exist at Stage C. |
| Analysis output (p-values, `K_plus`, `T_max`, `p_min`) | Do not exist at Stage C; `K_plus` explicitly never affects matrix membership (design decision §7.4.1). |

### 9.5 `K`, the statistic, and `randomization_mode` — included, deliberately

**[SCHEMA — FROZEN]** All three are **included** in the preimage. This is decided, not left open.

- **`K` — included.** Design decision §10 registers "Assignment support — `{0,1}^K`, `2^{-K}` each" as a row of the frozen matrix. The support is part of what is registered, and `K` is the only thing that names its size. `K` is also a determined function of `confirmatory_positions`, so its inclusion adds no *new* information — that is a feature, not a defect: it means a manifest whose `K` disagreed with its positions could not produce a preimage that both hashes to the persisted `matrix_digest` and passes §16 F19, so the two checks agree by construction rather than compete.
- **`randomization_mode` — included.** It is the frozen procedure by which that support is enumerated (implementation design §5.L.1), it is registered in this artifact and required to equal the provenance artifact's mode, and it is assignment-invariant (it depends on `K` alone, never on any drawn bit or observed outcome).
- **The statistic — included, via `registered_statistical_configuration`.** Design decision §10 registers Statistic, Weighting, and Alpha/multiplicity as rows of the frozen matrix table. `statistic_spec_id`, `aggregation_rule`, `treatment_contrast_orientation`, `alpha`, `multiplicity_architecture`, `primary_endpoint`, `secondary_endpoint_sequence`, `primary_estimand_architecture`, `randomization_exact_enumeration_max_k`, and `randomization_mc_samples` are all assignment-invariant and all fixed before any bit exists. Under the alternative — excluding them — a design that registered a different `M`, a different contrast orientation, or a different endpoint sequence over the identical positions would produce an identical `matrix_digest`, which would make `matrix_digest` a weaker statement than "this is the registered confirmatory matrix." The whole nested object is included rather than a hand-picked subset, because a hand-picked subset would be a projection that exists nowhere else and would have to be maintained in parallel with §11's key set.

### 9.6 Ordering before hashing

**[SCHEMA — FROZEN]** Every array reaching the preimage is already in its frozen order (§8.1, §8.2), fixed by the schema before canonicalization and never by canonicalization. Implementation design §5.B.2 is explicit that "arrays preserve registered order; arrays are never reordered or deduplicated by the canonicalization step itself." Object keys — the five preimage keys, and the keys within every nested record — are ordered by `sort_keys=True` code-point ordering, exactly as the frozen algorithm does everywhere else.

**The preimage is therefore fully determined before hashing, with no ordering freedom anywhere.**

### 9.7 Algorithm and computation order

**[SCHEMA — FROZEN]** The algorithm is **the already-frozen one, by reference** — implementation design §5.B.2, realized once by Work Unit 1 (G3). No alternative algorithm, serializer, option set, hash function, or digest encoding is stated or permitted here.

```
matrix_digest = lowercase_hex( SHA256( canonical_json_bytes( <the §9.2 five-key object> ) ) )
```

where `canonical_json_bytes` is exactly `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` encoded UTF-8.

**No `self_digest`-removal step applies**: the preimage object has no `self_digest` field to remove. The removal step of §5.B.2 belongs to the `self_digest` construction and is not part of this one.

**Computation order, frozen:**

1. Build the sixteen-key artifact with `matrix_digest` and `self_digest` not yet set.
2. Build the §9.2 preimage object from that artifact's own already-final values.
3. Compute `matrix_digest`; place it in the artifact.
4. Compute `self_digest` over the artifact with only `self_digest` removed (implementation design §5.B.2) — so `self_digest` covers `matrix_digest`, and never the reverse.
5. Persist per §17.

**Verification, frozen:** a loader rebuilds the §9.2 preimage from the parsed manifest's own persisted values, recomputes the digest, and compares against the claimed `matrix_digest` (§16 F23). A mismatch fails closed. This is separate from, and additional to, `self_digest` verification (§16 F24).

`MATRIX_DIGEST_PREIMAGE_FROZEN: YES.`

---

## 10. Stage-C runtime-identity representation (closes U-C7)

### 10.1 The exact representation — one field on each confirmatory stratum

**[SCHEMA — FROZEN]** Stage C carries the registration-expected runtime identity as exactly one field:

```
confirmatory_strata[i].runtime_identity_digest    string, lowercase 64-character hex
```

copied verbatim, for the stratum `(provider, model) = (confirmatory_strata[i].provider, confirmatory_strata[i].model)`, from the unique registration-expected snapshot for that stratum:

```
registration_draft.json
    .proposed_runtime_configuration
    .registration_expected_runtime_snapshots[j]
    .runtime_identity_digest
```

where `j` is the index of the unique snapshot with `provider_name == provider` and `model == model` — the lookup Stage-B clarification §12.3 RC-5 already froze and the implementation already realizes (G4).

**There is no separate top-level runtime array.** A `registration_expected_runtime_identities` array would repeat the `(provider, model)` pairs that `confirmatory_strata` already carries, need its own ordering, uniqueness, and cover rules, and create a second place where a stratum's identity binding could be stated. Placing the digest on the stratum record it binds costs one key, duplicates nothing, and makes the binding structurally inseparable from its stratum.

### 10.2 Scope — confirmatory strata only, justified from downstream frozen behavior

**[SCHEMA — FROZEN]** The Stage-C runtime-identity binding covers **confirmatory strata only**, not all proposed strata. `descriptive_only_strata` elements carry no `runtime_identity_digest` (§8.1).

The justification is strictly the set of frozen downstream consumers, each of which reads the registration-expected identity for a stratum that is about to execute or has executed under the confirmatory profile:

1. **Pre-execution refusal.** Implementation design §5.J: the confirmatory runner, "before dispatching each position's execution, captures `pre_execution_runtime_snapshot` and refuses the execution if that snapshot's `runtime_identity_digest` does not equal the registration-expected `runtime_identity_digest`" (§5.I.6). Only registered **confirmatory** positions are ever dispatched.
2. **Row binding.** Implementation design §5.C check 14: the analyzer verifies that "the row's `runtime_identity_digest` equals the frozen registration-expected `runtime_identity_digest`." Only confirmatory rows enter that fourteen-point checklist (§5.C, §9).
3. **Resume.** Implementation design §5.O: every existing execution row's `runtime_identity_digest` must equal the registration-expected value. Again, confirmatory rows only.

**No frozen consumer ever reads a descriptive-only stratum's runtime identity from `registration_manifest.json`.** A descriptive-only stratum is never executed under `confirmatory_profile == "post_phaseP_confirmatory_randomization_v1"`, never produces a confirmatory row, and never has any snapshot compared against it. Carrying its digest here would be convenience metadata with no consumer.

**Nothing is lost.** Every proposed stratum's registration-expected runtime identity remains registered, immutable, and digest-authenticated in two upstream places this manifest binds by digest: the complete `RuntimeSnapshotV1` in `registration_draft.json` (bound by `registration_draft_digest`), and the copied `runtime_identity_digest` on every `EligibilityStratumRecordV1` (bound by `eligibility_manifest_digest`, Stage-B clarification §13.1). A consumer wanting a descriptive-only stratum's identity reads the draft or the eligibility manifest, both already authenticated from here.

### 10.3 What Stage C does **not** do

**[SCHEMA — FROZEN]**

- **No runtime recapture.** Stage C constructs no `RuntimeSnapshotV1`, hashes none, and reads no live runtime. Capture point 1 already happened at Stage A "before eligibility/final registration" (implementation design §5.I.5); capture points 2 and 3 belong to execution and analysis, states that do not exist yet. This is Stage-B clarification §13.2's rule, applied unchanged one stage later.
- **No `captured_at` equality invariant.** `captured_at` is capture metadata and is never compared for equality across captures (implementation design §5.I.2). It is not a Stage-C field and no Stage-C rule references it.
- **No cross-capture `self_digest` equality.** Each snapshot's own `self_digest` verifies individually per §5.B.2; snapshot `self_digest` values are *expected to differ* across captures and are never compared (implementation design §5.I.2, §5.I.5).
- **No duplicated `RuntimeSnapshotV1` objects.** The manifest carries the seventeen-field identity's *digest*, never the twenty-field snapshot. The frozen downstream requirements — §5.I.5's "all relevant `runtime_identity_digest` values equal the registration-expected `runtime_identity_digest`", §5.C check 14, §5.J, §5.O — are stated entirely in terms of `runtime_identity_digest` and require no other snapshot field. Duplicating the whole object would embed `captured_at` and a snapshot `self_digest` in a Stage-C artifact where §5.I.2 forbids either from being an invariant, and would invite exactly the comparison the frozen contract removed.
- **No new failure token.** `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` (pre-freeze), `RuntimeIdentityRefused` (pre-execution/resume), and `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (analysis) are implementation design §5.I.6's frozen tokens and are unchanged.

### 10.4 Validation — the copy is checked against both upstream artifacts

**[SCHEMA — FROZEN]** Because Stage A and Stage B both hold the same value (Stage-B clarification §13.1 copies it from Stage A), Stage C checks its copy against **both**, and a disagreement anywhere is an integrity failure of the whole manifest, never an eligibility finding:

- against the draft: §16 F32;
- against the eligibility manifest: §16 F37.

Equality is exact byte-for-byte string equality of two 64-hex values. There is no partial match, no prefix comparison, and no normalization.

`RUNTIME_IDENTITY_REPRESENTATION_FROZEN: YES.`

---

## 11. Statistical carry-forward (closes U-C8)

### 11.1 One nested object, not flat fields — the choice is made

**[SCHEMA — FROZEN]** The frozen Stage-A statistical configuration is carried into Stage C as **exactly one nested object**:

```
registered_statistical_configuration
```

Flat Stage-C fields are **rejected**. Flattening would spread eleven values across the top level, obscure that they are one already-frozen unit, and — decisively — make the carry-forward check eleven separate field comparisons instead of one object equality against `registration_draft.proposed_statistical_configuration`. The nested shape lets §16 F33 be a single exact statement.

The field name parallels Stage A's `proposed_statistical_configuration` with the lifecycle-appropriate prefix, which is exactly how the artifact chain already names the same concept at a later stage.

### 11.2 The exact key set — the eleven Stage-A keys, by exact parsed-object equality

**[SCHEMA — FROZEN]** `registered_statistical_configuration` is the **exact parsed-object carry-forward** of `registration_draft.json`'s `proposed_statistical_configuration`. It contains exactly:

```
schema_version                          = "ProposedStatisticalConfigurationV1"
statistic_spec_id                       = "confirmatory_task_sign_flip_v1"
randomization_mc_samples                  positive JSON integer, or null
alpha                                   = "0.05"
multiplicity_architecture               = "FIXED_SEQUENCE_GATEKEEPING"
primary_endpoint                        = "unsafe_action_executed"
secondary_endpoint_sequence             = ["safety_security_violation",
                                           "unsafe_action_proposed",
                                           "constraint_violation",
                                           "privacy_leak",
                                           "attack_success"]
primary_estimand_architecture           = "SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES"
aggregation_rule                        = "NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN"
treatment_contrast_orientation          = "FULL_MINUS_OFF"
randomization_exact_enumeration_max_k   = 16
```

Eleven keys, exactly the eleven Stage-A clarification §7.1 froze, with exactly the values §7.2 froze and the representations §7.4 froze — `alpha` a canonical decimal string, `randomization_mc_samples` and `randomization_exact_enumeration_max_k` ordinary JSON integers, `secondary_endpoint_sequence` ordered rather than sorted. **No value and no semantics is altered by this document.**

`schema_version` remains exactly `"ProposedStatisticalConfigurationV1"` (§11.3).

#### 11.2.1 "Exact parsed-object equality" — defined mechanically

**[SCHEMA — FROZEN]** The carry-forward requirement is **exact parsed-object equality**, defined over parsed JSON semantic objects and over nothing else:

> `registration_manifest.registered_statistical_configuration` must equal the **validated** `registration_draft.proposed_statistical_configuration` as a parsed JSON semantic object.

Mechanically, and exhaustively:

| # | Requirement |
|---|---|
| **S1** | **Exactly the same eleven keys** — the set of keys on both sides is identical. |
| **S2** | **Exactly the same JSON value for every key** — same JSON type and same value, compared as parsed values (string to string, integer to integer, `null` to `null`, array to array). |
| **S3** | **Arrays retain the same registered order.** `secondary_endpoint_sequence` is positional and semantic; equality is element-wise in order, never as a set. |
| **S4** | **No missing key** on the Stage-C side. |
| **S5** | **No extra key** on the Stage-C side. |
| **S6** | **No normalized or reinterpreted value.** `alpha` is not re-parsed into a float and re-rendered; `randomization_mc_samples` is not coerced between `null` and `0` or between integer and string; no string is case-folded, trimmed, or re-encoded. |
| **S7** | **No caller-selected replacement.** The object is taken from the validated draft; `freeze_final_registration` exposes no parameter through which a caller could supply, override, or amend any of the eleven values. |

**This is deliberate reuse of the already-authenticated semantic object, not a new Stage-C statistical schema.** The draft's object was validated at Stage A (V9) and authenticated by the draft's `self_digest`, which this manifest binds through `registration_draft_digest`. Stage C re-registers that same object; it does not define a second statistical schema, mint a second version literal (§11.3), or introduce a Stage-C-specific representation of any of the eleven values.

#### 11.2.2 What exact parsed-object equality does **not** mean

**[SCHEMA — FROZEN]** Exact parsed-object equality is **not** a byte comparison, and no rule in this document may be implemented as one.

- It does **not** mean comparing the source artifact's incidental serialized bytes.
- It does **not** add a raw-byte comparison of any kind.
- It does **not** add a source-file byte comparison.
- It does **not** add byte-for-byte canonical-input validation.

A semantically equivalent noncanonical JSON serialization of `registration_draft.json` remains **admissible** under the already-frozen reader contract, provided that it parses to the same object, that its `self_digest` verifies through the frozen semantic recanonicalization procedure (implementation design §5.B.2), and that every schema invariant passes. That is exactly what Stage-A clarification §12 and Stage-B clarification §16 already froze, and §17.1 restates it unchanged for this artifact. **No reader-side canonicality check and no new failure token is added here.**

**Persisted writes themselves remain canonical, as already frozen.** The distinction is one-directional and deliberate: what this document *writes* is canonical JSON plus one trailing LF (§17.1), while what a reader may *accept* is any serialization that parses to the authenticated object. §16 F33 compares parsed objects; it never compares input bytes.

### 11.3 The `schema_version` literal is not re-minted

**[SCHEMA — FROZEN]** The nested object keeps `schema_version = "ProposedStatisticalConfigurationV1"`. **No `RegisteredStatisticalConfigurationV1` literal is minted.**

The reason is the carry-forward itself. The Stage-C object is not a transformation of the Stage-A object — it *is* the Stage-A object, unchanged, now registered. Keeping the literal makes §16 F33 a single exact parsed-object equality against the draft; minting a new literal would make the two objects differ in exactly one key's value, forcing every carry-forward check to be a key-wise comparison with a documented exception, and would create a second `schema_version` literal for an identical eleven-key shape. Under C2 the object carries a `schema_version` because frozen upstream text (Stage-A clarification §7.1) assigns it one — and that same text fixes which literal it is.

### 11.4 No top-level `statistic_spec_id`, and no duplication anywhere

**[SCHEMA — FROZEN]** `statistic_spec_id` appears in this artifact **exactly once**, at `registered_statistical_configuration.statistic_spec_id`. There is **no** top-level `statistic_spec_id` field, and no other key duplicates any nested value.

The frozen downstream requirements are satisfied by the nested location. Implementation design §7 PR-8 requires `statistic_spec_id` "in registration manifest"; §11 defines `STATISTIC_VERSION_MISMATCH` as "the `statistic_spec_id` **recorded at registration**" not matching the implemented literal; §5.K requires it to be recorded so the analyzer can detect a mismatch rather than assume agreement. All three say *recorded in this artifact*; none requires a top-level key, and none reads a second copy. Sibling artifacts carry their own `statistic_spec_id` (`randomization_mc_provenance.json`, implementation design §5.L.2/§5.L.3; `final_analysis_manifest.json`, §5.B.3) — those are different artifacts and are unaffected.

The same holds for `randomization_mc_samples`: one location, inside the nested object. Implementation design §5.L.3's analyzer check — "`M` equals the registered `randomization_mc_samples`" — reads it there.

### 11.5 `randomization_mode` stays top-level, and stays derived

**[SCHEMA — FROZEN]** `randomization_mode` is **not** a member of `registered_statistical_configuration`. It is a top-level field.

Two reasons, both from frozen text. First, it is not a Stage-A statistical value at all: Stage-A clarification §7.1's key set excludes it deliberately, and §8.2/§10.2 classify it as a Stage-C deterministic derivation that "may [not] be proposed, overridden, or hinted at by the caller." Putting a Stage-C derivation inside an object frozen as the verbatim carry-forward of a Stage-A object would break the exact parsed-object equality of §11.2 — it would introduce a twelfth key the Stage-A object does not have, failing §11.2.1 S1 and S5. Second, implementation design §5.L.1 reads it as a property of the manifest — "the registration manifest's frozen `randomization_mode`" — which the provenance artifact must equal.

**Randomization mode remains derived from `K`, never caller-selected** (§15).

`STATISTICAL_CARRY_FORWARD_FROZEN: YES.`

---

## 12. Cross-stage exact derivation table

**[SCHEMA — FROZEN]** Every persisted Stage-C value, its source, its derivation, its validation rule, and whether a caller may choose it. Nested fields are shown under their parent. Class letters are §3's. **The final column reads NO on every row**, including `created_at` (§4.4.1).

| Stage-C field | Class | Source | Derivation | Validation | May caller choose? |
|---|---|---|---|---|---|
| `schema_version` | D | this document §5 | stamped literal `"RegistrationManifestV1"` | F1, F2 | **NO** |
| `registration_state` | D | implementation design §5.A, §6 | stamped literal `"FINAL_REGISTRATION_FROZEN"` | F1, F3 | **NO** |
| `confirmatory_profile` | D | implementation design §5.C | stamped literal `"post_phaseP_confirmatory_randomization_v1"` | F1, F4, F28, F35 | **NO** |
| `design_id` | A | `registration_draft.design_id` | copied verbatim | F5, F28, F35 | **NO** — chosen at Stage A |
| `created_at` | E — `FREEZE_CAPTURE_METADATA` | the Stage-C sealing event itself | captured internally by `freeze_final_registration` at the Stage-C sealing event, exactly once, before `self_digest` and before the write (§4.4.1 T1-T5) | F38 (capture prerequisite, construction/write time); F6 (persisted grammar, load time) | **NO** |
| `registration_draft_digest` | C | `registration_draft.self_digest` | copied after verification | F7, F26 | **NO** |
| `eligibility_manifest_digest` | C | `eligibility_manifest.self_digest` | copied after verification | F8, F34 | **NO** |
| `confirmatory_strata[*].provider` / `.model` | C | `draft.proposed_strata` filtered by Stage-B disposition | §13.1 stable filter | F9, F29, F36 | **NO** |
| `confirmatory_strata[*].runtime_identity_digest` | A | `draft.…registration_expected_runtime_snapshots[j].runtime_identity_digest` | copied verbatim for the matching `(provider, model)` | F9, F32, F37 | **NO** |
| `descriptive_only_strata[*].provider` / `.model` | C | `draft.proposed_strata` complement of the above | §13.1 stable filter | F10, F29, F36 | **NO** |
| `confirmatory_positions[*].position_id` | C | the six identity fields of the immutable proposed position | SHA-256 over the canonical six-key payload (§7.1, §14) | F12, F16 | **NO** |
| `confirmatory_positions[*].task_id` / `.provider` / `.model` / `.repetition` / `.provider_seed` / `.slot` / `.baseline_label` | A | the immutable `ProposedPositionV1` | copied verbatim, all seven | F12, F30, F31 | **NO** |
| `descriptive_positions[*]` (all eight fields) | A + C | identical to the above, on the descriptive side of the partition | identical | F13, F16, F30, F31 | **NO** |
| `K` | C | `confirmatory_positions` | count of distinct `task_id` (§15) | F19 (recorded **and** recomputed) | **NO** |
| `randomization_mode` | C | `K` | `K <= 16 → EXACT_ENUMERATION`; `K > 16 → MONTE_CARLO` (§15) | F20 (recorded **and** recomputed) | **NO** |
| `registered_statistical_configuration.randomization_mc_samples` | A | `draft.proposed_statistical_configuration.randomization_mc_samples` | copied verbatim | F21, F22, F33 | **NO** — proposed at Stage A |
| `registered_statistical_configuration` — the other ten keys | D | Stage-A stamped constants (Stage-A clarification §7.2) | copied verbatim; each equals its frozen literal | F21, F33 | **NO** |
| `matrix_digest` | C | the §9.2 five-key preimage | SHA-256 per implementation design §5.B.2 | F23 (recomputed) | **NO** |
| `self_digest` | C | the artifact minus `self_digest` | SHA-256 per implementation design §5.B.2 | F24 (verified) | **NO** |

**Every row resolves to a Stage-A copy, a Stage-B-driven deterministic derivation, a global frozen literal, or the internally captured freeze instant. Every row answers NO to "may caller choose?" — there is no exception.** The one class-E field is admitted only because Stage-A clarification §13.1 row 27 already names it as a final registered value; it is captured by the sealing operation rather than supplied (§4.4.1), carries no methodology, is never an equality invariant, and is excluded from `matrix_digest` (§9.4).

**`FREEZE_CAPTURE_METADATA` has exactly one member.** `created_at` is the only field in class E, and this document creates no other timestamp field — no `frozen_at`, `sealed_at`, `registered_at`, `assessed_at`, or `captured_at` exists at any depth (§4.6, §16 F1, F25).

**Note on Stage-B copies.** No field of this artifact is a class-B verbatim copy: Stage B's contribution reaches Stage C entirely as the *partition* (class C), by design, because copying dispositions here would create a second source of truth for them (§8.1). Stage B's `runtime_identity_digest` is a class-A value that Stage B also copies; Stage C copies it from Stage A and cross-checks it against Stage B (§10.4).

---

## 13. The partition algorithm — exact deterministic construction

### 13.1 The construction, stated exactly

**[SCHEMA — FROZEN]** Let `D = registration_draft.json` and `E = eligibility_manifest.json`, both already loaded and fully validated by their own frozen loaders. By Stage-B clarification §6.3 (E24) `E.eligibility_records` is an exact element-wise cover of `D.proposed_strata`: equal lengths, index-wise `(provider, model)` equality, both sorted ascending by that key and unique on it. The construction relies on exactly that alignment.

**Step 1 — partition the strata.**

```
confirmatory_strata     = []
descriptive_only_strata = []

for i in range(len(D.proposed_strata)):                 # the frozen Stage-A order
    stratum = D.proposed_strata[i]
    record  = E.eligibility_records[i]                  # index-aligned by Stage-B E24

    if record.disposition == "CONFIRMATORY_ELIGIBLE":
        confirmatory_strata.append({
            "provider": stratum.provider,
            "model":    stratum.model,
            "runtime_identity_digest":
                D.proposed_runtime_configuration
                 .registration_expected_runtime_identity_digest(
                     stratum.provider, stratum.model),   # §10.1, RC-5 lookup
        })
    else:
        descriptive_only_strata.append({
            "provider": stratum.provider,
            "model":    stratum.model,
        })
```

**Step 2 — partition the positions, by their own stratum's side.**

```
confirmatory_keys = { (s["provider"], s["model"]) for s in confirmatory_strata }

confirmatory_positions = []
descriptive_positions  = []

for position in D.proposed_positions:                   # the frozen Stage-A order
    record = final_position_record(position)            # §14.1, pure, deterministic
    if (position.provider, position.model) in confirmatory_keys:
        confirmatory_positions.append(record)
    else:
        descriptive_positions.append(record)
```

**Properties, by construction rather than by argument:**

- Both steps iterate an already-sorted, already-unique immutable array **in order** and append without reordering. Each output is therefore a **stable filter** of a sorted array, hence sorted and unique under the same key (§8.4). No `sorted()` call occurs anywhere in the construction.
- `record.disposition` is **read**, never recomputed. Stage-B clarification §8.3 already requires the eligibility loader to recompute the disposition from `predicates` and refuse a mismatch (E19); by the time Stage C sees it, the token has been cross-checked. **Stage C re-derives no disposition from predicates, evaluates no predicate, and reads no evidence.** §16 F36 checks only which side each stratum landed on.
- A position's side is decided **solely** by its own `(provider, model)` stratum's disposition — never by its task, repetition, slot, or label, and never by anything realized.

### 13.2 The permissive "may" is read as a total partition — restated, not re-decided

Implementation design §5.A Stage C says "a descriptive-only stratum **may** remain in the broader reporting design." Stage-A clarification §13.2 already froze the only reading consistent with Stage C freezing *both* confirmatory and descriptive position IDs:

> Every element of `proposed_strata` lands in exactly one of `confirmatory_strata` or `descriptive_only_strata`. Every element of `proposed_positions` lands in exactly one of `confirmatory_positions` or `descriptive_positions`, according to its own `(provider, model)` stratum's disposition. **No proposed stratum or position is dropped, and none appears in both sets.**

That is restated here, not re-decided. This document adds only the persisted representation of the two sides (§8.1, §8.2) and the element-wise cover validation (§13.3).

### 13.3 Exact element-wise cover validation

**[SCHEMA — FROZEN]** A loader validates the partition structurally, with no set arithmetic that could mask a duplicate. Both merges below are ordinary two-pointer merges of two arrays that are each sorted and unique under the merge key.

**Stratum cover** (§16 F29):

```
len(confirmatory_strata) + len(descriptive_only_strata) == len(D.proposed_strata)

merge(confirmatory_strata, descriptive_only_strata) by (provider, model) ascending
    reproduces D.proposed_strata exactly, element-wise:
        merged[i].provider == D.proposed_strata[i].provider
        merged[i].model    == D.proposed_strata[i].model
    for every index i
```

The merge is well-defined and total only if the two arrays are disjoint on `(provider, model)`; a shared key makes the merge fail, which is exactly the "on both sides" rejection.

**Position cover** (§16 F30):

```
len(confirmatory_positions) + len(descriptive_positions) == len(D.proposed_positions)

merge(confirmatory_positions, descriptive_positions)
        by (task_id, provider, model, repetition, slot) ascending
    reproduces D.proposed_positions exactly, element-wise on all seven Stage-A fields:
        task_id, provider, model, repetition, provider_seed, slot, baseline_label
    for every index i
```

**Side consistency** (§16 F17): every element of `confirmatory_positions` has its `(provider, model)` in `confirmatory_strata`, and every element of `descriptive_positions` has its `(provider, model)` in `descriptive_only_strata`.

**Disposition consistency** (§16 F36): every `confirmatory_strata` element's stratum has `disposition == "CONFIRMATORY_ELIGIBLE"` in the bound eligibility manifest, and every `descriptive_only_strata` element's stratum has one of the five `DESCRIPTIVE_ONLY_*` tokens.

**Together these reject, deterministically:**

| Condition | Rejected by |
|---|---|
| a proposed stratum missing from both sides | length equality, then element-wise merge |
| a proposed position missing from both sides | length equality, then element-wise merge |
| a stratum or position duplicated within one side | uniqueness (F9, F10, F14, F15) |
| a stratum or position appearing on both sides | merge disjointness (F11, F15) |
| a foreign stratum or position present in neither draft array | element-wise merge inequality |
| a `CONFIRMATORY_ELIGIBLE` stratum placed on the descriptive side | F36 |
| a `DESCRIPTIVE_ONLY_*` stratum placed on the confirmatory side | F36 |
| a position placed opposite its own stratum's side | F17 |

**No Stage-B disposition is recomputed at any point.**

---

## 14. Position construction — `ProposedPositionV1` → Stage-C record

### 14.1 The exact transformation

**[SCHEMA — FROZEN]** `final_position_record` is total, pure, and deterministic:

```
def final_position_record(p: ProposedPositionV1) -> ConfirmatoryPositionV1:
    identity = {                              # exactly the six §7.1 keys, no more
        "model":         p.model,
        "provider":      p.provider,
        "provider_seed": p.provider_seed,
        "repetition":    p.repetition,
        "slot":          p.slot,
        "task_id":       p.task_id,
    }
    return {
        "position_id":    lowercase_hex(SHA256(canonical_json_bytes(identity))),
        "task_id":        p.task_id,          # verbatim
        "provider":       p.provider,         # verbatim
        "model":          p.model,            # verbatim
        "repetition":     p.repetition,       # verbatim
        "provider_seed":  p.provider_seed,    # verbatim
        "slot":           p.slot,             # verbatim
        "baseline_label": p.baseline_label,   # verbatim  (§14.3)
    }
```

- **Fields copied verbatim: all seven Stage-A fields.** No coercion, no re-typing, no normalization, no case change.
- **`position_id` is the only derived field**, computed by the already-frozen algorithm of implementation design §5.B.2 over exactly the six-key identity payload (§7.1) — the payload the implementation already exposes and deliberately leaves unhashed at Stage A (G2).
- **No treatment transformation.** `resolve_label`, `complement`, and `qa_mode` do not appear. `baseline_label` is copied, never mapped.
- **No randomness.** No entropy source is consulted, no bit is drawn, no seed is derived. `final_position_record` is a pure function of its argument.
- **No Stage-C input other than `p`.** The function reads no eligibility record, no clock, no environment, and no configuration.

### 14.2 Loader reconstruction and cross-check

**[SCHEMA — FROZEN]** A loader never trusts a claimed `position_id`, and never trusts a claimed Stage-A field.

**Reconstruction, from the manifest alone** (§16 F16): for each of the eight-key records in both arrays, rebuild the six-key identity payload from the record's own `task_id`, `provider`, `model`, `repetition`, `provider_seed`, `slot`; canonicalize per implementation design §5.B.2; SHA-256; lowercase-hex; compare to the claimed `position_id`. A mismatch is refused. This is the Stage-C analogue of implementation design §5.C check 7, which applies the identical discipline to execution rows: "a row cannot merely *claim* a `position_id`; the analyzer recomputes it."

**Cross-check, against the bound draft** (§16 F30, F31): the element-wise position merge of §13.3 compares all seven Stage-A fields of every record against the proposed position at the same merged index — so `baseline_label` equality is checked positionally for every position on both sides, and so is every identity field, independently of the digest.

Both checks run. Recomputing `position_id` alone would accept a record whose fields hash correctly but were never proposed; comparing fields alone would accept a record with a fabricated `position_id`. Together they admit only a faithful transformation of a registered proposed position.

### 14.3 `baseline_label` is copied, never recomputed — restated

Stage-A clarification §6.3 already froze what Stage C may do to `S_k`: it **may** filter positions by the immutable eligibility disposition, and it **must not** recompute a label, rerun `_ordered_treatments` or any other ordering procedure, choose a new schedule, alter a label because eligibility results are now known, or reorder/renumber/reassign `slot` values. The binding equality it froze —

```
registration_manifest.baseline_label == registration_draft proposed position.baseline_label
```

byte-for-byte, for the position with the identical six identity fields — is realized here as a verbatim copy in §14.1 and as positional equality in §14.2. **This document adds no rule to §6.3 and weakens none.**

---

## 15. `K`, `randomization_mode`, and `M` — restated without change

**[SCHEMA — FROZEN]** Restated from the already-frozen upstream text. Nothing in this section is new.

**Registered `K`:**

```
K = | { position.task_id : position in confirmatory_positions } |
```

the number of distinct `task_id` values in the registered confirmatory positions. Zero-difference tasks are irrelevant here — `K` is fixed at Stage C, before any outcome exists, and `K_plus` is an analysis-time reporting derivation that "explicitly never affect[s] matrix membership or `K`" (design decision §7.4.1; Stage-A clarification §10.4).

**Randomization mode — derived from `K`, never caller-selected:**

```
K <= randomization_exact_enumeration_max_k   ->   randomization_mode = "EXACT_ENUMERATION"
K >  randomization_exact_enumeration_max_k   ->   randomization_mode = "MONTE_CARLO"
```

where `registered_statistical_configuration.randomization_exact_enumeration_max_k` is required by §16 F21 to equal its frozen literal `16`, so this is exactly implementation design §5.L.1's `K <= 16` / `K > 16` rule. **`randomization_mode` is never proposed, overridden, defaulted, or hinted at by a caller** (Stage-A clarification §8.2, §10.2).

**`M` — the already-frozen bidirectional gate, restated:**

| Mode | `registered_statistical_configuration.randomization_mc_samples` | On violation |
|---|---|---|
| `"EXACT_ENUMERATION"` (`K <= 16`) | **MUST** be `null` | **The freeze is refused.** The registered value is neither discarded, ignored, nor reinterpreted (Stage-A clarification §8.3) |
| `"MONTE_CARLO"` (`K > 16`) | **MUST** be a positive JSON integer | **FINAL REGISTRATION REFUSES TO FREEZE.** Stage C does **not** select `M` — not here, not at MC-provenance generation, not at assignment, not at execution, not at analysis (Stage-A clarification §8.3) |

Both refusals are hard refusals: no partial freeze, no warning-only path, no automatic repair, no default value. The remedy is the one implementation design §5.A already froze — the registration is abandoned as a unit and a **new** triple is created under a **new** `design_id`. **No new `M` is invented anywhere.**

`K = 0` remains legal exactly to the extent already frozen upstream (§8.3 item 4), and yields `randomization_mode = "EXACT_ENUMERATION"` with `randomization_mc_samples = null`, like every other `K <= 16`.

---

## 16. Fail-closed validation contract

**[SCHEMA — FROZEN]** A loader applies the rules below **in the numbered order** and aborts on the **first** failure. There is **no normalization, no repair, no sorting on the caller's behalf, no deduplication, no default-filling, no warning-only path, and no partial acceptance.** A manifest that fails any rule is not a valid `RegistrationManifestV1` and no consumer proceeds with it.

**First-failure order is contractually observable.** This is frozen deliberately, and stated so it is not left ambiguous a second time: for any given malformed manifest, the rule that fires is exactly the lowest-numbered rule it violates, and a conformant implementation may be tested on that. This matches Stage-B clarification §14, which froze the identical property for E1-E26, and is what lets a focused test assert *which* defect an artifact has rather than only *that* it has one.

Failures are raised as `ConfirmatoryRegistrationError` — the existing module-scoped error of `confirmatory_registration.py` (G1, G3), which already owns Stage A. **No new error taxonomy is minted**, because Stage C lives in the same module the implementation design assigns it (§5.A, §8 item 1).

### 16.1 Tier 1 — checkable from the manifest alone

| # | Rule |
|---|---|
| **F1** | Top-level object has exactly the sixteen keys of §4.1 — no missing key, no extra key. (This is what structurally forbids `final_registration_digest`, `assignment_digest`, every assignment/seed/execution/analysis field, and every retired or foreign name from ever loading.) |
| **F2** | `schema_version` equals `"RegistrationManifestV1"`. |
| **F3** | `registration_state` equals `"FINAL_REGISTRATION_FROZEN"`. |
| **F4** | `confirmatory_profile` equals `"post_phaseP_confirmatory_randomization_v1"`. |
| **F5** | `design_id` is a non-empty string and a single safe path segment. |
| **F6** | `created_at` is a string matching `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` exactly. **This is a syntax/type validation of the persisted value and nothing more** — it does not, and cannot, establish that the persisted instant is the true wall-clock moment of the freeze; that guarantee is structural and lives at construction/write time (§4.4.1, F38b). |
| **F7** | `registration_draft_digest` matches `^[0-9a-f]{64}$`. |
| **F8** | `eligibility_manifest_digest` matches `^[0-9a-f]{64}$`. |
| **F9** | `confirmatory_strata` is an array; every element is an object with exactly the three keys of §8.1; `provider` and `model` are non-empty strings; `runtime_identity_digest` matches `^[0-9a-f]{64}$`; the array is sorted ascending by `(provider, model)` and unique on it. |
| **F10** | `descriptive_only_strata` is an array; every element is an object with exactly the two keys of §8.1; both are non-empty strings; the array is sorted ascending by `(provider, model)` and unique on it. |
| **F11** | The two stratum arrays are disjoint on `(provider, model)`, and their union is non-empty (§8.3 item 2). |
| **F12** | `confirmatory_positions` is an array; every element is an object with exactly the eight keys of §7.2, with the frozen types: `position_id` matches `^[0-9a-f]{64}$`; `task_id`/`provider`/`model` non-empty strings; `repetition` a JSON integer `>= 0`; `provider_seed` a JSON integer; `slot` a JSON integer in `{1, 2}`; `baseline_label` in `{"off", "full"}`. |
| **F13** | `descriptive_positions` satisfies the identical element schema and type rules as F12. |
| **F14** | Each position array is sorted ascending by `(task_id, provider, model, repetition, slot)` and unique on that key (§8.2). |
| **F15** | `position_id` is unique across the **union** of the two position arrays, and no `(task_id, provider, model, repetition, slot)` appears in both arrays (§8.2, §13.3). |
| **F16** | Every position record's six identity fields reproduce its claimed `position_id` under the §7.1 / §14.2 recomputation, in both arrays. |
| **F17** | Every `confirmatory_positions` element's `(provider, model)` is in `confirmatory_strata`; every `descriptive_positions` element's `(provider, model)` is in `descriptive_only_strata` (§13.3). |
| **F18** | Emptiness coupling holds in both directions: `confirmatory_positions` is empty **iff** `confirmatory_strata` is empty, and `descriptive_positions` is empty **iff** `descriptive_only_strata` is empty (§8.3 item 3). |
| **F19** | `K` is a JSON integer `>= 0` **and** equals the number of distinct `task_id` values in `confirmatory_positions` (§15). Recorded **and** recomputed; a difference is refused (C4). |
| **F20** | `randomization_mode` is exactly `"EXACT_ENUMERATION"` or `"MONTE_CARLO"` **and** equals the value derived from `K` by §15. Recorded **and** recomputed; a difference is refused (C4). |
| **F21** | `registered_statistical_configuration` is an object with exactly the eleven keys of §11.2; `schema_version` equals `"ProposedStatisticalConfigurationV1"`; each of the ten stamped constants equals its frozen literal exactly, including the order of `secondary_endpoint_sequence`; `randomization_mc_samples` is `null` or a positive JSON integer. |
| **F22** | The mode/`M` gate of §15 holds: `EXACT_ENUMERATION` requires `randomization_mc_samples` to be `null`; `MONTE_CARLO` requires it to be a positive JSON integer. |
| **F23** | `matrix_digest` matches `^[0-9a-f]{64}$` **and** equals the digest recomputed from the §9.2 five-key preimage rebuilt from this manifest's own persisted values. |
| **F24** | `self_digest` matches `^[0-9a-f]{64}$` and verifies per implementation design §5.B.2's unchanged verification procedure (§17). |
| **F25** | No JSON object key anywhere in the artifact, at any depth, is one of the forbidden names of §16.4. |

### 16.2 Tier 2 — requires the bound `registration_draft.json`

A manifest may be *parsed* standalone, but it is never *accepted* — and never consumed downstream — without both bound upstream artifacts. These rules run only after every Tier-1 rule has passed.

| # | Rule |
|---|---|
| **F26** | The bound `registration_draft.json` loads through its own frozen loader (which enforces V1-V11 and RC-1…RC-5) and its own `self_digest` verifies; this manifest's `registration_draft_digest` equals that verified `self_digest`. |
| **F27** | The draft's `registration_state` equals `"REGISTRATION_DRAFT"` — this manifest is bound to a Stage-A artifact, not to some other stage's. |
| **F28** | This manifest's `design_id` and `confirmatory_profile` equal the draft's, byte-for-byte. |
| **F29** | Exact element-wise stratum cover of `draft.proposed_strata` per §13.3 — equal total length and index-wise `(provider, model)` equality after the ascending merge. This is the single rule that rejects a missing, duplicate, foreign, or both-sides stratum. |
| **F30** | Exact element-wise position cover of `draft.proposed_positions` per §13.3 — equal total length and index-wise equality on all seven Stage-A fields after the ascending merge. This is the single rule that rejects a missing, duplicate, or foreign position. |
| **F31** | For every position on both sides, `baseline_label` equals the bound draft's proposed position's `baseline_label` at the merged index (§14.3). (Implied by F30 and stated separately because it is the binding equality Stage-A clarification §6.3 froze by name.) |
| **F32** | For every `confirmatory_strata` element, `runtime_identity_digest` equals `draft.proposed_runtime_configuration.registration_expected_runtime_snapshots[j].runtime_identity_digest` for the unique `j` with matching `(provider_name, model)` (§10.1, §10.4). |
| **F33** | `registered_statistical_configuration` equals `draft.proposed_statistical_configuration` by **exact parsed-object equality** per §11.2.1 S1-S7 — same eleven keys, same JSON value for every key, arrays in the same registered order, no missing key, no extra key, no normalized or reinterpreted value, no caller-selected replacement. The comparison is over **parsed objects**; it is never a comparison of the draft's incidental serialized bytes (§11.2.2). |

### 16.3 Tier 3 — requires the bound `eligibility_manifest.json`

| # | Rule |
|---|---|
| **F34** | The bound `eligibility_manifest.json` loads through its own frozen loader (which enforces E1-E26) and its own `self_digest` verifies; this manifest's `eligibility_manifest_digest` equals that verified `self_digest`. |
| **F35** | The eligibility manifest's `registration_state` equals `"ELIGIBILITY_FROZEN"`; its `design_id` and `confirmatory_profile` equal this manifest's; and **its `registration_draft_digest` equals this manifest's `registration_draft_digest`** — so all three artifacts bind the same draft, and an eligibility manifest assessed against a *different* draft can never be admitted. |
| **F36** | Stage-B exact stratum cover and disposition consistency (§13.3): every `confirmatory_strata` element's stratum has `disposition == "CONFIRMATORY_ELIGIBLE"` in the bound eligibility manifest, and every `descriptive_only_strata` element's stratum has one of the five `DESCRIPTIVE_ONLY_*` tokens. No disposition is recomputed from predicates. |
| **F37** | For every `confirmatory_strata` element, `runtime_identity_digest` equals the bound eligibility manifest's `eligibility_records` entry for that `(provider, model)` (§10.4). |

### 16.4 Forbidden key names

**[SCHEMA — FROZEN]** No JSON object key at any depth of `registration_manifest.json` may be any of:

```
final_registration_digest                                    (same-object alias; §4.5)
registration_manifest_digest                                 (same-object alias)
assignment_digest  randomization_mc_provenance_digest        (downstream artifacts)
task_assignment_bit  bits  b_k  task_order                   (assignment material)
seed_hex  entropy_bytes  source_kind  source_api
seed_encoding  rng_library  rng_bit_generator  numpy_version
generated_at  exact_support_size                             (MC provenance; §5.L)
qa_mode  observation_status  failure_class  error
runtime_snapshot_digest                                      (execution rows; §5.C)
captured_at                                                  (capture metadata; §5.I.2)
assessed_at  eligibility_state  eligibility_records
predicates  disposition  infrastructure_symmetry_audit
evidence_refs  isolation_evidence                            (Stage-B material; §4.6)
proposed_tasks  proposed_strata  proposed_repetitions
proposed_provider_seeds  proposed_positions
proposed_runtime_configuration
proposed_statistical_configuration                           (Stage-A names; §4.6)
registration_expected_runtime_snapshot
registration_expected_runtime_snapshots                      (no snapshot duplication; §10.3)
confirmatory_tasks  registered_tasks  task_membership
descriptive_tasks  repetitions  registered_repetitions
repetition_counts  provider_seeds  registered_provider_seeds
seeds                                                        (no redundant derivations; §6)
registered_k  statistic_spec_id                              (at top level; §6.4, §11.4)
```

This is a **key-name** prohibition, not a raw-substring search: it is exactly checkable and cannot false-positive on a legitimate string *value*. Two entries are position-sensitive and are stated that way: `statistic_spec_id` is forbidden **at the top level only** and is required inside `registered_statistical_configuration` (§11.4); `registered_k` is forbidden everywhere, the registered value being carried by `K` (§6.4). F1 and the exact key sets of F9, F10, F12, F13, and F21 already make every name above structurally impossible at its own depth; F25 restates the prohibition so an auditor can check it directly.

### 16.5 Immutable write prerequisites

| # | Rule |
|---|---|
| **F38** | **Write refused unless Stage B is complete and `created_at` was internally captured.** Two conjuncts, both required. **(a) Stage-B prerequisite:** `eligibility_manifest.json` must already exist for this `design_id` and must load and validate through E1-E26, and the artifact about to be written must pass F1-F37 against it and the draft. `ELIGIBILITY_FROZEN` strictly precedes `FINAL_REGISTRATION_FROZEN` (implementation design §5.A, §6); there is no path that freezes a final registration first. **(b) `created_at` capture prerequisite (§4.4.1):** the `created_at` sealed into the object must be the value **captured internally by this `freeze_final_registration` invocation**, must **not** have been supplied by the caller — `freeze_final_registration` exposes no parameter through which it could be (T2) — must conform to the exact whole-second UTC-`Z` grammar `YYYY-MM-DDTHH:MM:SSZ` (T3), and must be the value present in the object **before** `self_digest` is computed and **before** any byte reaches disk (T4, T5). This conjunct is a **construction/write-time** guarantee, structural in the interface; it makes no claim that a later loader can independently prove historical wall-clock truth (§4.4.1). |
| **F39** | **Write is an exclusive create.** `registration_manifest.json` for a given `design_id` is written once. If one already exists the write is refused — never replaced, never truncated, never edited in place (§17; G6). The complete F1-F37 contract runs against the sealed artifact *before* any byte reaches disk, so construction cannot mint anything a load would refuse. |

### 16.6 The complete rejection inventory

| Rejected condition | Rule |
|---|---|
| malformed top-level shape; any extra or missing key | F1 |
| wrong schema version / lifecycle state / profile / design id | F2, F3, F4, F5, F28, F35 |
| malformed freeze timestamp | F6 |
| malformed or wrong `registration_draft_digest` | F7, F26 |
| malformed or wrong `eligibility_manifest_digest` | F8, F34 |
| malformed stratum record; unsorted or duplicated stratum array | F9, F10 |
| stratum on both sides; all four arrays empty | F11, F18 |
| malformed position record; wrong types or vocabulary | F12, F13 |
| unsorted or duplicated position array | F14 |
| duplicate `position_id`; position on both sides | F15 |
| `position_id` mismatch | F16 |
| position placed opposite its own stratum's side | F17 |
| broken emptiness coupling | F18 |
| wrong registered `K` | F19 |
| wrong `randomization_mode`, or wrong mode-for-`K` | F20 |
| wrong statistical configuration shape or stamped literal | F21 |
| wrong `M`/mode relationship | F22 |
| `matrix_digest` mismatch | F23 |
| `self_digest` malformed or mismatched | F24 |
| forbidden downstream / assignment / seed / execution field present | F1, F25 |
| upstream draft missing, unverifiable, or a non-draft artifact | F26, F27 |
| missing / duplicate / foreign / both-sides stratum vs. the draft | F29 |
| missing / duplicate / foreign position vs. the draft | F30 |
| `baseline_label` mismatch | F31 |
| runtime identity mismatch against Stage A | F32 |
| statistical carry-forward mismatch against Stage A | F33 |
| eligibility manifest missing, unverifiable, or bound to a different draft | F34, F35 |
| wrong partition vs. the frozen dispositions | F36 |
| runtime identity mismatch against Stage B | F37 |
| final registration attempted before eligibility is frozen | F38a |
| `created_at` caller-supplied, or not the internally captured sealing instant | F38b (structural; not representable through the interface, §4.4.1 T2) |
| persisted `created_at` malformed | F6 |
| overwrite / second freeze for one `design_id` | F39 |

`FAIL_CLOSED_VALIDATION_SCHEMA_COMPLETE: YES.`

---

## 17. Immutability, canonical JSON, and the reader contract

### 17.1 Canonical JSON and `self_digest` — reused by reference, unamended

**The canonical algorithm is not modified.** Implementation design §5.B.2 applies to `registration_manifest.json` exactly as written, realized once by Work Unit 1 (G3) and reused here without a second implementation. Restated only for the avoidance of doubt:

- Canonical bytes are `json.dumps(object_without_self_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` encoded UTF-8.
- Object keys are sorted by ordinary Unicode code-point ordering via `sort_keys=True`; objects use string keys only.
- Arrays preserve registered order; the sorting and uniqueness rules of §8.1, §8.2, and §11.2 are **schema-level preconditions applied before canonicalization**, never canonicalization-time transformations.
- `NaN` / `Infinity` / `-Infinity` are forbidden. `K`, `repetition`, `provider_seed`, `slot`, `randomization_mc_samples`, and `randomization_exact_enumeration_max_k` are ordinary JSON integers, never strings; `alpha` is the canonical decimal string `"0.05"` carried forward unchanged from Stage A (Stage-A clarification §7.4). No new numeric representation choice arises in this artifact.
- `self_digest` is SHA-256, lowercase hex, over the canonical bytes of the object with **only** `self_digest` removed. `matrix_digest` is **not** removed — it is ordinary content, computed first (§9.7).
- The persisted file is the canonical JSON *including* the computed `self_digest`, reserialized under the identical algorithm, plus exactly one trailing LF that is not part of any digest; a reader strips at most one trailing `\n` first.
- Verification: read bytes → strip at most one trailing LF → parse → extract claimed `self_digest` → remove it → recanonicalize → recompute SHA-256 → compare. Mismatch fails closed.

**No byte-for-byte canonical-input gate is added.** A semantically equivalent noncanonical input that parses to the same authenticated object is **not, by itself, a failure condition** — exactly as Stage-A clarification §12 and Stage-B clarification §16 already froze. This document adds no reader-side canonicality check and no new failure token.

#### 17.1.1 Where byte-level language is, and is not, used in this document

**[SCHEMA — FROZEN]** Byte-level wording is confined to two legitimate uses, and is used for nothing else. Stated so an auditor can check the distinction directly rather than by grep.

| Use | Where | Status |
|---|---|---|
| **Scalar string equality** — two strings are equal character-for-character: `design_id` against the draft and the eligibility manifest (§4.4, F28, F35); `runtime_identity_digest` against Stage A and Stage B (§10.4, F32, F37); `baseline_label` against the draft (§14.3, F31, quoting Stage-A clarification §6.3's own binding equality) | §4.3, §4.4, §10.4, §14.3, F28, F31, F32, F35, F37 | **Legitimate.** These compare parsed string *values*, not artifact serializations. |
| **Explicit denial of a byte gate** — "no byte-for-byte canonical-input gate is added" | §17.1, §11.2.2, §19 case 66, §20 | **Legitimate and required.** These are negations that must remain; removing them would reintroduce the ambiguity Stage-A clarification §12 and Stage-B clarification §16 closed. |

**Byte-level language is NOT used, anywhere, for:**

- the statistical carry-forward, which is **exact parsed-object equality** (§11.2.1, §11.2.2, F33);
- the `matrix_digest` preimage, which is assembled from the artifact's own in-memory values and canonicalized once (§9.2, §9.7);
- any comparison of an upstream artifact's serialized bytes against anything.

**No rule in this document may be implemented as a raw-byte comparison, a source-file byte comparison, or a byte-for-byte canonical-input validation.** Persisted writes remain canonical exactly as frozen (§17.1); what a reader may accept is any serialization that parses to the authenticated object.

### 17.2 Write-once immutability

**[SCHEMA — FROZEN]** Restated in substance from implementation design §5.A, §6, and §12; **not reopened, not amended, not softened.**

- `registration_manifest.json` is **write-once**. The write is an exclusive create (§16 F39; G6).
- **No overwrite.** An existing manifest for a `design_id` is never replaced or truncated.
- **No update.** No field is ever edited in place, for any reason, at any later state.
- **No in-place eligibility promotion.** After `FINAL_REGISTRATION_FROZEN`, no task, provider, model, stratum, or position may move into or out of the confirmatory matrix — not before assignment, not after assignment, not after execution, not after analysis, not ever. A stratum recorded in `descriptive_only_strata` can never later appear in `confirmatory_strata` of this `design_id`.
- **No reassessment.** Stage C never re-evaluates a predicate, never re-derives a disposition, and never re-reads a mutated eligibility manifest (§13.1).
- **A replacement design requires a new `design_id`.** The entire registration triple — `registration_draft.json`, `eligibility_manifest.json`, `registration_manifest.json` — is abandoned as a unit and a new triple is created under a new `design_id`. The abandoned artifacts are retained for audit and never reused.

Any attempted in-place edit fails closed by construction: either `self_digest` no longer verifies (§16 F24), or, if `self_digest` was recomputed, every downstream `final_registration_digest` reference breaks at the referencing artifact (implementation design §5.B.3).

### 17.3 The semantic reader contract — reused, not restated as an alternative

The frozen semantic reader contract of implementation design §5.B.2 is reused verbatim (§17.1). A loader parses, verifies, and rebuilds; it never repairs a malformed artifact, never normalizes an invalid one into validity, and never reserializes around a mismatch.

---

## 18. Complete artifact skeleton

Shape illustration only, over invented placeholders. **No real provider, model, task, design id, digest, eligibility decision, or matrix appears here or anywhere in this document.** Keys are shown in canonical sorted order — note `"K"` first, per §6.4. `<64-hex>` marks a lowercase 64-character hex digest.

```json
{
  "K": 1,
  "confirmatory_positions": [
    {
      "baseline_label": "off",
      "model": "<proposed model, deferred>",
      "position_id": "<64-hex>",
      "provider": "<proposed provider, deferred>",
      "provider_seed": 0,
      "repetition": 0,
      "slot": 1,
      "task_id": "<proposed task, deferred>"
    },
    {
      "baseline_label": "full",
      "model": "<proposed model, deferred>",
      "position_id": "<64-hex>",
      "provider": "<proposed provider, deferred>",
      "provider_seed": 0,
      "repetition": 0,
      "slot": 2,
      "task_id": "<proposed task, deferred>"
    }
  ],
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "confirmatory_strata": [
    {
      "model": "<proposed model, deferred>",
      "provider": "<proposed provider, deferred>",
      "runtime_identity_digest": "<64-hex, copied from the draft>"
    }
  ],
  "created_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "descriptive_only_strata": [],
  "descriptive_positions": [],
  "design_id": "<deferred value selection>",
  "eligibility_manifest_digest": "<64-hex>",
  "matrix_digest": "<64-hex>",
  "randomization_mode": "EXACT_ENUMERATION",
  "registered_statistical_configuration": {
    "aggregation_rule": "NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN",
    "alpha": "0.05",
    "multiplicity_architecture": "FIXED_SEQUENCE_GATEKEEPING",
    "primary_endpoint": "unsafe_action_executed",
    "primary_estimand_architecture": "SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES",
    "randomization_exact_enumeration_max_k": 16,
    "randomization_mc_samples": null,
    "schema_version": "ProposedStatisticalConfigurationV1",
    "secondary_endpoint_sequence": [
      "safety_security_violation",
      "unsafe_action_proposed",
      "constraint_violation",
      "privacy_leak",
      "attack_success"
    ],
    "statistic_spec_id": "confirmatory_task_sign_flip_v1",
    "treatment_contrast_orientation": "FULL_MINUS_OFF"
  },
  "registration_draft_digest": "<64-hex>",
  "registration_state": "FINAL_REGISTRATION_FROZEN",
  "schema_version": "RegistrationManifestV1",
  "self_digest": "<64-hex>"
}
```

The illustration shows a one-stratum, one-task, one-repetition design in which the single proposed stratum is `CONFIRMATORY_ELIGIBLE`: both descriptive arrays are therefore empty, which §8.3 permits exactly because `descriptive_only_strata` is empty; `K = 1 <= 16`, so `randomization_mode = "EXACT_ENUMERATION"` and `randomization_mc_samples` is `null` per the §15 gate. It illustrates the schema; **it registers nothing and decides nothing.**

And the `matrix_digest` preimage for the same illustration (§9.2), which excludes both descriptive arrays and every metadata field:

```json
{
  "K": 1,
  "confirmatory_positions": [ "…the two records above, identical values…" ],
  "confirmatory_strata": [ "…the one record above, identical values…" ],
  "randomization_mode": "EXACT_ENUMERATION",
  "registered_statistical_configuration": { "…the eleven-key object above, identical values…" }
}
```

---

## 19. Adversarial self-check

Every case resolves to exactly one deterministic outcome under §4-§17.

| # | Case | Outcome |
|---|---|---|
| 1 | Manifest carries a seventeenth top-level key. | F1 fails. Refused. |
| 2 | Manifest omits `created_at`, or any other of the sixteen. | F1 fails. Absence encodes nothing. Refused. |
| 3 | `schema_version` written as `"FinalRegistrationV1"` or `"registrationmanifestv1"`. | F2 fails — exact literal. Refused. |
| 4 | `registration_state` written as `"ELIGIBILITY_FROZEN"`. | F3 fails. Refused. |
| 5 | `registration_draft_digest` names a different draft than the one supplied. | F26 fails. Refused. |
| 6 | `eligibility_manifest_digest` names a different eligibility manifest. | F34 fails. Refused. |
| 7 | The bound eligibility manifest is valid but was assessed against a **different** draft. | F35 fails on `registration_draft_digest` inequality. Refused — this is the cross-artifact substitution F35 exists for. |
| 8 | Manifest bound to a `registration_manifest.json` in place of a draft. | F27 fails. Refused. |
| 9 | A proposed stratum appears in neither stratum array. | F29 fails on length, then element-wise merge. Refused. |
| 10 | A stratum appears in both arrays. | F11 fails (disjointness); F29's merge would also fail. Refused. |
| 11 | A stratum record present in neither draft array (foreign). | F29 fails element-wise. Refused. |
| 12 | Two `confirmatory_strata` records for the same `(provider, model)`. | F9 fails (uniqueness). Refused; never deduplicated. |
| 13 | A `CONFIRMATORY_ELIGIBLE` stratum placed in `descriptive_only_strata`. | F36 fails. Refused — wrong partition. |
| 14 | A `DESCRIPTIVE_ONLY_UNASSESSED` stratum placed in `confirmatory_strata`. | F36 fails. Refused. Only `CONFIRMATORY_ELIGIBLE` strata may enter the confirmatory matrix. |
| 15 | Someone re-derives a disposition from `predicates` at Stage C and gets a different token. | Structurally impossible: Stage C reads `disposition` and never evaluates a predicate (§13.1). A persisted eligibility manifest whose token disagreed with its predicates was already refused at Stage-B E19. |
| 16 | A proposed position appears in neither position array. | F30 fails on length, then element-wise merge. Refused. |
| 17 | A position appears in both arrays. | F15 fails. Refused. |
| 18 | A position record present in neither draft array (foreign). | F30 fails element-wise. Refused. |
| 19 | The same position listed twice in `confirmatory_positions`. | F14 (placement uniqueness) and F15 (`position_id` uniqueness) both fail. Refused. |
| 20 | A confirmatory position whose stratum is on the descriptive side. | F17 fails. Refused. |
| 21 | `position_id` fabricated; identity fields correct. | F16 fails — the digest is recomputed, never trusted. Refused. |
| 22 | Identity field altered; `position_id` recomputed to match it. | F16 passes, then F30 fails element-wise against the draft. Refused. Both checks exist for exactly this pair of cases. |
| 23 | `baseline_label` changed from `"off"` to `"full"` on a retained position. | F31 fails (and F30). Refused. Stage C may filter and nothing else (Stage-A clarification §6.3). |
| 24 | `baseline_label` added to the `position_id` preimage. | F16 fails — the preimage is exactly the six identity fields (§7.1). Refused; the identity would otherwise leak assignment-relevant structure. |
| 25 | Stage C reruns `_ordered_treatments` and writes a different schedule. | Forbidden by Stage-A clarification §6.3; detected by F31/F30. Refused. |
| 26 | A stratum becomes descriptive-only and someone rebalances the surviving task's OFF/FULL counts. | Impossible and unnecessary: filtering removes whole `{"off","full"}` pairs (Stage-A clarification §6.4). Any rebalancing act is caught by F30. |
| 27 | `runtime_identity_digest` copied from the wrong stratum's snapshot. | F32 fails against the draft; F37 fails against the eligibility manifest. Refused — an integrity failure of the whole manifest, never an eligibility finding. |
| 28 | `runtime_identity_digest` omitted from a `confirmatory_strata` record. | F9 fails — exactly three keys. Refused. |
| 29 | `runtime_identity_digest` added to a `descriptive_only_strata` record. | F10 fails — exactly two keys. Refused (§10.2). |
| 30 | A complete `RuntimeSnapshotV1` embedded in the manifest. | F1/F9/F25 fail. Refused — no snapshot duplication, no `captured_at`, no cross-capture `self_digest` comparison (§10.3). |
| 31 | Stage C captures a fresh runtime snapshot. | Not represented and not performed: no capture occurs at Stage C (§10.3), and there is no field for one. |
| 32 | Two snapshots differ only in `captured_at`, hence in `self_digest`, with equal `runtime_identity_digest`. | Not a failure of any kind, at any stage (implementation design §5.I.2). Nothing in this artifact compares either field. |
| 33 | `K` recorded as `3` while `confirmatory_positions` spans two tasks. | F19 fails — recorded and recomputed differ. Refused. |
| 34 | `K` recorded as `20` with `randomization_mode = "EXACT_ENUMERATION"`. | F20 fails (assuming F19 passed). Refused. |
| 35 | `randomization_mode` supplied by a caller rather than derived. | Not representable: it is a class-C derivation, recomputed and compared at F20. Any caller value that differs is refused. |
| 36 | `K = 12` and `randomization_mc_samples = 10000`. | F22 fails. **The freeze is refused** — the registered value is neither discarded nor reinterpreted (Stage-A clarification §8.3). A new `design_id` is required. |
| 37 | `K = 20` and `randomization_mc_samples = null`. | F22 fails. **FINAL REGISTRATION REFUSES TO FREEZE.** Stage C does not select `M` (§15). |
| 38 | `K = 0` — every proposed stratum descriptive-only. | Legal. `confirmatory_strata` and `confirmatory_positions` are both empty (F18 satisfied), `randomization_mode = "EXACT_ENUMERATION"`, `randomization_mc_samples = null`. No minimum-`K` rule is invented (§8.3 item 4). |
| 39 | All four arrays empty. | Structurally impossible; F11 and F18 fail. Refused. |
| 40 | `confirmatory_strata` non-empty but `confirmatory_positions` empty. | F18 fails. Refused. |
| 41 | `alpha` written as the JSON number `0.05`, or as `"0.050"`. | F21 fails — the stamped literal is the canonical decimal string `"0.05"`; F33 fails against the draft. Refused. |
| 42 | `secondary_endpoint_sequence` reordered or sorted alphabetically. | F21 fails — the order is semantic and frozen (Stage-A clarification §7.2); F33 fails. Refused. |
| 43 | `registered_statistical_configuration` given a twelfth key, or a `RegisteredStatisticalConfigurationV1` `schema_version`. | F21 fails — exactly eleven keys, and the literal is not re-minted (§11.3). Refused. |
| 44 | A top-level `statistic_spec_id` added "for convenience". | F1 and F25 fail. Refused — one location only (§11.4). |
| 45 | `randomization_mode` moved inside `registered_statistical_configuration`. | F1 (missing top-level key) and F21 (twelfth key) both fail. Refused (§11.5). |
| 46 | `matrix_digest` computed over a bare array of confirmatory positions. | F23 fails — the preimage is the frozen five-key object (§9.1, §9.2). Refused. |
| 47 | `matrix_digest` preimage includes `descriptive_positions`. | F23 fails. Refused — descriptive-only reporting material is not part of the confirmatory matrix definition (§9.4). |
| 48 | `matrix_digest` preimage includes `design_id` or `created_at`. | F23 fails. Refused — deliberate exclusions (§9.4). |
| 49 | `matrix_digest` preimage arrays hashed in a different order. | F23 fails — ordering is fixed by the schema before hashing (§9.6). Refused. |
| 50 | `matrix_digest` correct but `self_digest` stale. | F24 fails. Refused. |
| 51 | `self_digest` recomputed over an object from which `matrix_digest` was also removed. | F24 fails — only `self_digest` is removed (§17.1). Refused. |
| 52 | A same-object `final_registration_digest` field added, equal to `self_digest`. | F1 and F25 fail; implementation design §5.B.1 agrees. Refused. |
| 53 | An `assignment_digest` or `randomization_mc_provenance_digest` added. | F1 and F25 fail. Refused — both artifacts are downstream and do not exist yet. |
| 54 | A `task_assignment_bit`, `bits`, or `b_k` field added anywhere. | F1/F12/F25 fail. Refused — **no assignment bit exists at Stage C**. |
| 55 | A `seed_hex`, `entropy_bytes`, or `generated_at` field added anywhere. | F1/F25 fail. Refused — **no MC seed exists at Stage C**; those are `randomization_mc_provenance.json` fields. |
| 56 | An `exact_support_size` field added. | F1/F25 fail. Refused — it is a provenance field (implementation design §5.L.2), not a registration field. |
| 57 | A `qa_mode`, `observation_status`, or `failure_class` field added. | F1/F12/F25 fail. Refused — execution begins three states later. |
| 58 | A p-value, `K_plus`, or interval added. | F1/F25 fail. Refused — analysis output is not a registered value. |
| 59 | `confirmatory_positions` sorted by `position_id` instead of placement. | F14 fails; the array is never re-sorted on the caller's behalf. Refused (§8.4). |
| 60 | `confirmatory_strata` sorted by `model` then `provider`. | F9 fails — the key is `(provider, model)`. Refused. |
| 61 | A construction helper is handed unsorted arrays. | Not representable: the Stage-C arrays are not caller-supplied; they are a stable filter of the already-sorted immutable draft, and the construction path never sorts because it never needs to (§8.4). |
| 62 | A final registration frozen before the eligibility manifest exists. | F38 fails. Refused — `ELIGIBILITY_FROZEN` strictly precedes `FINAL_REGISTRATION_FROZEN`. |
| 63 | A second `registration_manifest.json` written for the same `design_id`. | F39 fails — exclusive create. Refused; never replaced or truncated. |
| 64 | A manifest edited in place after being written. | Either F24 fails, or — if `self_digest` was recomputed — every downstream `final_registration_digest` reference breaks (implementation design §5.B.3). Forbidden regardless (§17.2). |
| 65 | A descriptive-only stratum promoted to confirmatory in place after outcomes. | Forbidden absolutely (§17.2). Requires abandon-and-recreate under a new `design_id`. |
| 66 | A reader receives semantically equivalent but noncanonical bytes that parse to the same authenticated object. | Not a failure — implementation design §5.B.2's verification procedure is unchanged and no byte-for-byte input gate is added (§17.1). |
| 67 | A caller passes `created_at="2020-01-01T00:00:00Z"` to `freeze_final_registration` to backdate the freeze. | **Not representable.** `freeze_final_registration` exposes no `created_at` parameter, no clock parameter, and no override (§4.4.1 T2). The call does not typecheck; there is no interface through which the value could be supplied. F38b states the prerequisite the construction path satisfies structurally. |
| 68 | A persisted manifest carries a `created_at` earlier than the bound draft's or eligibility manifest's `created_at`. | **Not a failure, and not compared.** `created_at` is not a cross-artifact equality invariant and no rule compares it against any other artifact's timestamp (§4.4.1 T7). A loader cannot prove historical wall-clock truth after the fact, and this document claims no such check (§4.4.1); F6 validates the persisted grammar only. |
| 69 | A second timestamp field — `frozen_at`, `sealed_at`, `registered_at` — is added to record "when the matrix was really fixed". | F1 and F25 fail. Refused — `FREEZE_CAPTURE_METADATA` has exactly one member and no other timestamp field exists at any depth (§3, §12). |
| 70 | The draft on disk is a semantically equivalent but noncanonical serialization; a Stage-C implementation compares its raw bytes against the manifest's nested statistical object and refuses. | **The implementation is non-conformant.** F33 is an exact **parsed-object** equality (§11.2.1 S1-S7); §11.2.2 forbids raw-byte, source-file-byte, and byte-for-byte canonical-input comparison. Provided the draft parses to the same object and its `self_digest` verifies through semantic recanonicalization, the carry-forward is valid. |

---

## 20. Conflict check against the frozen contracts

Every rule frozen above, checked against the frozen upstream text for direct contradiction.

| This addendum | Frozen text checked | Result |
|---|---|---|
| Sixteen-key top level (§4.1) | Implementation design §5.B.1 field inventory; §5.B.3; §12 audit catalog row | **Agrees**: `registration_draft_digest`, `eligibility_manifest_digest`, `matrix_digest`, `self_digest` all present; `final_registration_digest` absent |
| `registration_state = "FINAL_REGISTRATION_FROZEN"` (§4.1) | Implementation design §5.A, §6 state machine | **Uses the frozen state name verbatim**, under the field name both siblings already use |
| `schema_version = "RegistrationManifestV1"` (§5) | Stage-B clarification §3 C1; implementation design §5.A (`-> RegistrationManifest`) | **Consistent**; no conflicting literal exists (G8) |
| One `created_at`, class E, internally captured and not caller-selectable (§4.4, §4.4.1) | Stage-A clarification §13.1 row 27; implementation design §12 | **No contradiction** — row 27 already names a "`created_at`-class field on the manifest" as a final registered value and calls it capture metadata "recorded at freeze; never an equality invariant", which is exactly the capture contract frozen at §4.4.1 |
| No task/repetition/seed fields (§6.1-§6.3) | Implementation design §5.A Stage C ("task membership … repetitions, ordinary seeds"); §5.G, §5.K, §5.M | **No conflict** — §5.A requires the values *frozen*, which they are; §5.G/§5.K/§5.M reach every one of them through the registered position list, which is the only path any frozen consumer uses |
| `K` recorded and recomputed (§6.4) | Implementation design §5.L.1, §5.L.2, §5.L.3, §5.K | **Required by them** — the provenance artifact carries its own `K` and `exact_support_size = 2^K` and the analyzer compares; the field name `K` matches the sibling artifact's |
| Six-field identity payload (§7.1) | Implementation design §5.C; Stage-A clarification §5.1 | **Restated, unamended** |
| Eight-field position record (§7.2) | Implementation design §5.C; Stage-A clarification §5.2, §13.1 row 12 | **No conflict** — §5.C constrains the identity payload and the execution-row contract; the Stage-C record is the Stage-A seven plus the `position_id` §13.1 row 12 already froze |
| Descriptive positions use the identical record (§7.3) | Implementation design §5.A Stage C ("descriptive position IDs"); Stage-A clarification §13.1 row 12, §13.2 | **Required by them** |
| Array ordering and uniqueness (§8.1, §8.2) | Stage-A clarification §4.3 (`proposed_strata`, `proposed_positions` keys); implementation design §5.B.2 | **Same keys, same ordering rule**; sorting stays a schema-level precondition |
| Reject-not-normalize; construction vs. loader (§8.4) | Implementation design §5.B.2; Stage-B clarification §14 | **Consistent** — no normalization, no repair, no warning-only path |
| `K = 0` legal; no minimum-`K` rule (§8.3) | Stage-A clarification §14 case 7; design decision §7.4.1 | **Restated, unamended**; the estimability question stays where analysis contract §9.8 C9 left it |
| `matrix_digest` as a five-key object (§9) | Implementation design §5.B.1, §5.B.3 (names the field, never enumerates the preimage); Stage-A clarification §13.3 ("not opened here"); design decision §10 | **Fills a gap both documents explicitly left open**, and the preimage is an exact cover of design decision §10's frozen matrix-freeze table (§9.3) |
| `matrix_digest` uses the §5.B.2 algorithm by reference (§9.7) | Implementation design §5.B.2 | **Reused, not restated as an alternative**; no second algorithm exists |
| Per-confirmatory-stratum runtime identity (§10) | Implementation design §5.I, §5.I.1, §5.I.2, §5.I.5, §5.I.6, §5.C check 14, §5.J, §5.O; Stage-B clarification §12.3, §13 | **No conflict** — `RuntimeSnapshotV1` is untouched; the digest is copied, never recaptured; `captured_at` and cross-capture `self_digest` are never compared; scope matches exactly the set of strata any frozen consumer reads |
| Nested `registered_statistical_configuration`, eleven keys, exact parsed-object equality (§11.2, §11.2.1) | Stage-A clarification §7.1, §7.2, §7.4, §8; implementation design §5.K, §11 PR-8, §5.L.3 | **Carries every value and semantics forward unchanged**; `statistic_spec_id` is "recorded at registration" exactly as §5.K and §11 require |
| No byte-canonicality gate on the carry-forward (§11.2.2) | Implementation design §5.B.2; Stage-A clarification §12; Stage-B clarification §16 | **Consistent** — the equality is over parsed objects; the semantic recanonicalizing reader is untouched and no raw-byte or canonical-input comparison is added |
| `created_at` internally captured, not caller-selectable (§4.4.1) | Stage-A clarification §13.1 row 27; implementation design §6, §5.I.2 | **No contradiction, and strictly stricter** — row 27 permits the field and calls it capture metadata; removing the caller interface can only narrow what may be registered, and no cross-artifact timestamp invariant is created |
| `schema_version` literal not re-minted (§11.3) | Stage-A clarification §7.1, §7.2 | **Keeps the frozen literal**; no second literal for one shape |
| `randomization_mode` top-level and derived (§11.5, §15) | Implementation design §5.L.1; Stage-A clarification §8.2, §10.2 | **Agrees verbatim**; never caller-selected |
| Mode/`M` gate refuses the freeze (§15) | Stage-A clarification §8.3, §8.4, §14 cases 4-5; implementation design §5.L.3, §17, §6 refusal cell | **Restated, unamended, and strictly no weaker** — Stage C still selects no `M` anywhere |
| Total partition, read not recomputed (§13) | Implementation design §5.A Stage C and post-freeze invariant, §6 refusal cell; Stage-A clarification §13.2; Stage-B clarification §6.3 (E24), §8.3 (E19) | **Reproduces them exactly**; the element-wise cover makes §6's refusal structurally checkable |
| Thirty-nine fail-closed rules, first-failure order observable (§16) | Implementation design §5.B.2, §6, §11; Stage-B clarification §14 | **Consistent, and matches the Stage-B precedent**; no new error taxonomy minted |
| Immutability and abandon-and-recreate (§17.2) | Implementation design §5.A, §6, §12, §13 | **Restated, unamended** |
| Canonical JSON / `self_digest` / reader (§17.1) | Implementation design §5.B.2; Stage-A clarification §12; Stage-B clarification §16 | **Restated, unamended**; no byte-for-byte input gate added |
| Authorized surfaces only | Authorization §5.1, §5.3, §5.4, §11, §12 | **No expansion** — the Stage-C schema lands in `confirmatory_registration.py` and `tests/unit/test_confirmatory_registration.py`, both already authorized; no module, test file, or workflow rule is added |

**No frozen sentence directly contradicts any rule frozen here, and no upstream clause is superseded by this document.** Unlike Stage-B clarification §12.6, this addendum supersedes nothing: it fills a representation that both the implementation design and the Stage-A clarification explicitly left open for the Stage-C work unit.

```
METHODOLOGY_CHANGE:                        NO
RANDOMIZATION_DESIGN_CHANGE:               NO
ELIGIBILITY_SEMANTICS_CHANGE:              NO
STAGE_A_SCHEMA_CHANGE:                     NO
STAGE_B_SCHEMA_CHANGE:                     NO
IMPLEMENTATION_AUTHORIZATION_EXPANSION:    NO
```

---

## 21. Boundaries

**[NOT AUTHORIZED, and not done by this document]**

- No code is written. `freeze_final_registration` is not implemented here; this document freezes the schema it must realize.
- No actual provider or model eligibility is assessed or assigned. `CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED` remains true for every provider/runtime configured in the repository (design decision §9), unchanged.
- No `design_id` is minted. No task matrix, no `K`, no `M`, no assignment, no Monte Carlo seed, no randomization bit.
- No execution, no provider contact, no network access, no model inference.
- No results or confirmatory artifacts are created. `results/confirmatory/` is not written to, and no real `registration_manifest.json` exists anywhere.
- No Phase-P evidence is read, modified, reinterpreted, staged, deleted, regenerated, or migrated. `results/phaseP-rc4-qualification/` has no relationship to anything above and was not inspected.
- The implementation branch was inspected read-only with `git show`. It was **not** merged, cherry-picked, or copied.
- No candidate, version, RC, or named phase is created.
- No `src/` file, no test file, and no existing document is modified. No `pytest`, no `mypy`. Nothing is staged or committed.

---

## 22. DECISION

## **`FINAL_REGISTRATION_SCHEMA_CLARIFICATION_DECISION: STAGE_C_SCHEMA_FROZEN`**

Justification: all eight Stage-C representation items `U-C1`-`U-C8` are closed with exactly one representation each, and nothing upstream is reopened. The `registration_manifest.json` top-level key set is fixed at exactly sixteen keys with exact JSON types, frozen literals, and an explicit inventory of what the artifact deliberately does not carry (§4). The schema-version literal is minted once, against a verified absence of any conflicting literal, matching both the repository's naming convention and the public type the implementation design already names (§5). Task membership, repetitions, and ordinary provider seeds receive **no** separate fields, because the final position records already freeze each of them losslessly and no frozen downstream consumer reads any of them by name, while registered `K` **does** receive a field — named `K`, matching the sibling provenance artifact — because three frozen consumers compare against it across artifacts; the asymmetry is C7 applied to the frozen text, argued case by case (§6). The persisted position record is exactly the eight fields of the Stage-A seven plus `position_id`, with the six-field identity preimage untouched and descriptive positions using the identical representation, as implementation design §5.A's "descriptive position IDs" and Stage-A clarification §13.1 row 12 already require (§7). All four arrays receive exact sort keys, uniqueness keys, cross-array disjointness rules, and coupled emptiness rules; `K = 0` stays legal exactly as frozen upstream and no minimum-`K` rule is invented; and construction is distinguished from loader validation, the former emitting the frozen order as a consequence of stably filtering a sorted immutable input, the latter refusing an unsorted artifact rather than normalizing it (§8). `matrix_digest` is frozen as one canonical JSON object of exactly five named components — the array option rejected because it cannot carry the runtime, statistic, or support rows design decision §10 registers as part of the matrix — with every key enumerated, every exclusion argued individually, ordering fixed before hashing, the already-frozen §5.B.2 algorithm reused by reference, the computation order fixed so `self_digest` covers `matrix_digest` and never the reverse, and an exact cover argument against every row of design decision §10 (§9). Runtime identity is carried by exactly one copied field on each confirmatory stratum, scoped to confirmatory strata only and justified strictly from the three frozen consumers that read it, with no recapture, no `captured_at` invariant, no cross-capture `self_digest` comparison, and no snapshot duplication (§10). The statistical configuration is carried forward as one nested object bound to the Stage-A eleven-key object by **exact parsed-object equality** — same keys, same JSON values, arrays in registered order, nothing normalized, nothing caller-replaced — explicitly defined as a parsed-object comparison and explicitly **not** a byte comparison of the source artifact, so it adds no byte-canonicality gate and leaves the semantic recanonicalizing reader untouched; the frozen `schema_version` literal is kept so the check is a single equality, `statistic_spec_id` appears exactly once, and `randomization_mode` stays top-level and derived (§11.2, §11.2.1, §11.2.2). `created_at` is **not caller-selectable**: it is captured internally by `freeze_final_registration` exactly once on the successful sealing path, before `self_digest` and before the write, under the chain's whole-second UTC-`Z` grammar, with no parameter through which a caller could supply or backdate it — so backdating is prevented structurally at construction/write time (F38b) while F6 remains a persisted-grammar check that makes no claim to prove historical wall-clock truth (§4.4.1). A cross-stage derivation table classifies every persisted field into exactly one of five classes, `FREEZE_CAPTURE_METADATA` has exactly one member, and **every one of the sixteen fields answers NO to caller choice** (§12). The partition is a deterministic stable filter that reads Stage-B dispositions and never recomputes them, with element-wise cover validation that rejects every missing, duplicate, foreign, both-sides, and wrong-side case (§13). Position construction is a pure total function with one derived field and no randomness, cross-checked by both digest recomputation and field-wise comparison against the draft (§14). `K`, `randomization_mode`, and the bidirectional `M` gate are restated without change (§15). Thirty-nine numbered fail-closed rules across three tiers plus two write prerequisites cover every rejection the contract requires, with first-failure order frozen as contractually observable and no new error taxonomy minted (§16). Immutability, the canonical JSON profile, the `self_digest` algorithm, and the semantic reader contract are reused by reference and unamended, with no byte-for-byte input gate added (§17). Seventy adversarial cases each resolve to exactly one deterministic outcome (§19), and every frozen contract is checked for contradiction with none found and nothing superseded (§20).

```
REGISTRATION_MANIFEST_TOP_LEVEL_SCHEMA_FROZEN: YES
STAGE_C_SCHEMA_VERSION_FROZEN: YES
REGISTERED_VALUE_FIELD_NAMES_FROZEN: YES
POSITION_RECORD_SCHEMA_FROZEN: YES
POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES
ARRAY_ORDER_AND_UNIQUENESS_FROZEN: YES
MATRIX_DIGEST_PREIMAGE_FROZEN: YES
RUNTIME_IDENTITY_REPRESENTATION_FROZEN: YES
STATISTICAL_CARRY_FORWARD_FROZEN: YES
FAIL_CLOSED_VALIDATION_SCHEMA_COMPLETE: YES

STAGE_C_CREATED_AT: PASS
CREATED_AT_CALLER_SELECTABLE: NO
FREEZE_CAPTURE_METADATA_CLASS: PASS
STATISTICAL_CARRY_FORWARD_EQUALITY: EXACT_PARSED_OBJECT
NO_BYTE_CANONICALITY_CONFLICT: PASS
SEMANTIC_RECANONICALIZING_READER_PRESERVED: PASS
F1_TO_F39_COMPLETE: PASS
```

```
FINAL_REGISTRATION_SCHEMA_CLARIFICATION_DECISION:
STAGE_C_SCHEMA_FROZEN

UNRESOLVED_STAGE_C_ITEMS_U_C1_TO_U_C8:
NONE

REMAINING_WORK_UNIT_3_SCHEMA_CHOICES:
NONE

WORK_UNIT_3_CODE_IMPLEMENTATION_UNBLOCKED:
YES

METHODOLOGY_CHANGE:
NO

RANDOMIZATION_DESIGN_CHANGE:
NO

ELIGIBILITY_SEMANTICS_CHANGE:
NO

STAGE_A_SCHEMA_CHANGE:
NO

STAGE_B_SCHEMA_CHANGE:
NO
```

```
THIS_DOCUMENT_IS_A_BINDING_IMPLEMENTATION_SCHEMA_ADDENDUM: YES

IMPLEMENTATION_AUTHORIZATION_EXPANSION: NO
CODE_IMPLEMENTATION_AUTHORIZED_UNDER_EXISTING_PR21_DECISION: YES

RUNTIME_SNAPSHOT_V1_REOPENED: NO
CANONICAL_JSON_PROFILE_CHANGED: NO
CANONICAL_READER_RULE_CHANGED: NO
UPSTREAM_CLAUSE_SUPERSEDED: NONE

ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_PROVIDER_ELIGIBILITY_ASSESSMENT_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO
HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO
```

---

## 23. Validation

Documentation-only, static. Commands run in producing this record, and nothing else:

```
git branch --show-current
git status --short
git log -6 --oneline --decorate
git show origin/post-phasep-confirmatory-randomization-implementation:<path>   (read-only)
git diff --check
git diff --name-only
```

Observed:

```
git diff --check      -> (empty)
git diff --name-only  -> (empty; the new file is untracked and unstaged)
git status --short    -> ?? docs/post_phaseP_confirmatory_final_registration_schema_clarification.md
```

`git status --short` is authoritative here, and it reports exactly one entry: this new, untracked document. `git diff --name-only` is empty precisely because the file is untracked and unstaged, not because nothing was written.

This record was produced in the dedicated worktree `FSE-final-registration-schema-clarification`, whose working tree was clean at preflight and which contains no `results/` tree at all. Historical Phase-P evidence — `results/phaseP-rc4-qualification/` in the primary working directory — was **not** read, inspected for mutation, modified, deleted, staged, or regenerated by this task, and is not touched anywhere above.

No `pytest`. No `mypy`. No analyzer, harness, probe, or validator invocation. No provider/model/network call. No staging. No commit. No `git clean`, no `git reset --hard`, no `git add .`, no force-push. The implementation branch was not merged or cherry-picked.

```
ZERO MODEL INFERENCE
NO PHASE-P EVIDENCE MODIFIED
NO RC4 MODIFICATION
NO HISTORICAL PHASE-P REINTERPRETATION
NO RANDOMIZATION BIT GENERATED
NO SEED GENERATED
NO M SELECTED
NO K DERIVED FROM ANY REAL MATRIX
NO DESIGN_ID MINTED
NO PROVIDER ELIGIBILITY ASSIGNED
NO CANDIDATE CREATED
NO CODE WRITTEN
NO TESTS WRITTEN
NO TESTS RUN
NO IMPLEMENTATION BRANCH MERGED OR COPIED
NO FILES OTHER THAN docs/post_phaseP_confirmatory_final_registration_schema_clarification.md CREATED
NO EXISTING FILE MODIFIED
```

---

## Final report block

```
WORK_UNIT:
STAGE_C_FINAL_REGISTRATION_SCHEMA_CLARIFICATION

FINAL_REGISTRATION_SCHEMA_CLARIFICATION_DECISION:
STAGE_C_SCHEMA_FROZEN

UNRESOLVED_U_C1: RESOLVED    (exact sixteen-key top-level schema; all sixteen fields,
                             created_at included, have non-contradictory exact
                             source/derivation/caller-choice semantics, §4, §4.4.1, §12)
UNRESOLVED_U_C2: RESOLVED    ("RegistrationManifestV1", §5)
UNRESOLVED_U_C3: RESOLVED    (no task/repetition/seed fields; K is a field named K, §6)
UNRESOLVED_U_C4: RESOLVED    (eight-key ConfirmatoryPositionV1, both arrays, §7)
UNRESOLVED_U_C5: RESOLVED    (sort keys, uniqueness keys, emptiness coupling, §8)
UNRESOLVED_U_C6: RESOLVED    (five-key canonical object preimage, §9)
UNRESOLVED_U_C7: RESOLVED    (one copied digest per confirmatory stratum, §10)
UNRESOLVED_U_C8: RESOLVED    (one nested object, exact parsed-object equality, §11)

UNRESOLVED_STAGE_C_ITEMS_U_C1_TO_U_C8:
NONE

U_C1: CLOSED
U_C8: CLOSED

STAGE_C_CREATED_AT: PASS
CREATED_AT_CALLER_SELECTABLE: NO
CREATED_AT_INTERNAL_CAPTURE: PASS
F38_CREATED_AT_WRITE_PREREQUISITE: PASS
FREEZE_CAPTURE_METADATA_CLASS: PASS
STATISTICAL_CARRY_FORWARD_EQUALITY: EXACT_PARSED_OBJECT
BYTE_IDENTICAL_NORMATIVE_LANGUAGE_REMOVED: YES
NO_BYTE_CANONICALITY_CONFLICT: PASS
SEMANTIC_RECANONICALIZING_READER_PRESERVED: PASS
F1_TO_F39_COMPLETE: PASS

EXACT_TOP_LEVEL_SCHEMA: FROZEN
POSITION_RECORD_SCHEMA: FROZEN
MATRIX_DIGEST_PREIMAGE: FROZEN
RUNTIME_IDENTITY_REPRESENTATION: FROZEN
STATISTICAL_CARRY_FORWARD: FROZEN

REGISTRATION_MANIFEST_TOP_LEVEL_SCHEMA_FROZEN: YES
STAGE_C_SCHEMA_VERSION_FROZEN: YES
REGISTERED_VALUE_FIELD_NAMES_FROZEN: YES
POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES
ARRAY_ORDER_AND_UNIQUENESS_FROZEN: YES
FAIL_CLOSED_VALIDATION_SCHEMA_COMPLETE: YES

REMAINING_WORK_UNIT_3_SCHEMA_CHOICES:
NONE

WORK_UNIT_3_CODE_IMPLEMENTATION_UNBLOCKED:
YES

METHODOLOGY_CHANGE: NO
RANDOMIZATION_DESIGN_CHANGE: NO
ELIGIBILITY_SEMANTICS_CHANGE: NO
STAGE_A_SCHEMA_CHANGE: NO
STAGE_B_SCHEMA_CHANGE: NO
IMPLEMENTATION_AUTHORIZATION_EXPANSION: NO
RUNTIME_SNAPSHOT_V1_REOPENED: NO
CANONICAL_JSON_PROFILE_CHANGED: NO
CANONICAL_READER_RULE_CHANGED: NO
UPSTREAM_CLAUSE_SUPERSEDED: NONE

THIS_DOCUMENT_IS_A_BINDING_IMPLEMENTATION_SCHEMA_ADDENDUM: YES

SOURCE_CODE_CHANGED: NO
TESTS_CHANGED: NO
TESTS_RUN: NO

FILES_CHANGED:
docs/post_phaseP_confirmatory_final_registration_schema_clarification.md

GIT_STATUS:
?? docs/post_phaseP_confirmatory_final_registration_schema_clarification.md

ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_PROVIDER_ELIGIBILITY_ASSESSMENT_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO
HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO

ZERO MODEL INFERENCE
NO PHASE-P EVIDENCE MODIFIED
NO RC4 MODIFICATION
NO HISTORICAL PHASE-P REINTERPRETATION
NO RANDOMIZATION BIT GENERATED
NO SEED GENERATED
NO M SELECTED
NO DESIGN_ID MINTED
NO PROVIDER ELIGIBILITY ASSIGNED
NO CANDIDATE CREATED
NO CODE WRITTEN
NO IMPLEMENTATION BRANCH MERGED OR COPIED
NOT STAGED
NOT COMMITTED

READY_FOR_STAGE_C_SCHEMA_CLOSURE_REVIEW:
YES
```
