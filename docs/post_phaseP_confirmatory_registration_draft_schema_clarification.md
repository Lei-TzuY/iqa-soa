# Post-Phase-P confirmatory `REGISTRATION_DRAFT` schema clarification

**Record kind:** repository-level BINDING IMPLEMENTATION SCHEMA ADDENDUM.
**Status:** SCHEMA ADDENDUM only. This is **not** a statistical-methodology document, **not** a randomization-design revision, **not** an implementation-architecture redesign, and **not** code. It closes exactly four representation gaps in the Stage-A `REGISTRATION_DRAFT` artifact of the already-frozen confirmatory-randomization implementation design, and nothing else.
**Date:** 2026-08-26
**Base commit:** `a9a5986` (`origin/main`) — merge of PR #21, which carries the code-implementation authorization decision.
**Branch producing this record:** `post-phasep-confirmatory-registration-draft-schema-clarification`.
**Revision:** 1.

**This document makes no methodology decision, no statistical decision, and no randomization-design decision.** Every such decision was already made and frozen upstream and is treated here as an axiom, cited by section number and never re-derived. Where this document must fix an engineering representation, that choice is marked **[SCHEMA — FROZEN]**. Where it reports a fact about the committed source tree, that fact is marked **[OBSERVED]** and cited `file:line`. Where a value is deliberately not selected, it is marked **[DEFERRED VALUE SELECTION]**.

---

## 0. Boundary declaration

Producing this document involved: no model inference; no provider, Ollama, or network contact; no modification of anything under `results/`; no execution of any analyzer, harness, probe, or validator; no `pytest` invocation; no `src/` code written; no test written; no seed derivation; no randomization bit generated; no Monte Carlo seed generated; no `design_id` minted; no task, provider, model, repetition, ordinary provider seed, `M`, assignment, or `alpha` value selected beyond what was already frozen upstream; no provider eligibility disposition assigned; no candidate, version, RC, or named phase created; no staging; no commit.

Exactly one file is created: this document. No existing file is modified.

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

## 1. What this document is, precisely, and why it exists

An authorized implementation of Work Unit 1 (registration draft schema — implementation design §16 step 1, authorized by `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md` §4-§5) discovered one genuine specification gap.

The binding implementation design (`docs/post_phaseP_confirmatory_randomization_implementation_design.md`, Revision 3) says at §5.A Stage A that `registration_draft.json` records the *proposed* design: candidate tasks, candidate provider/model strata, candidate repetitions, candidate ordinary provider seeds, candidate fixed positions, candidate runtime/config values, and candidate statistical configuration. It says at §5.A Stage C that `registration_manifest.json` freezes confirmatory strata, descriptive-only strata, confirmatory position IDs, descriptive position IDs, task membership, provider/model membership, repetitions, ordinary seeds, baseline schedule, statistic version, registered `K`, the derived `randomization_mode`, "and every other registered value."

It does **not** uniquely specify:

1. the exact Stage-A statistical-configuration JSON schema;
2. null-vs-absent semantics for the future Monte Carlo sample count `M` (`randomization_mc_samples`);
3. how the baseline schedule `S_k` / `baseline_label` is bound prospectively to proposed positions;
4. whether the six `ConfirmatoryPositionV1` identity fields are exhaustive of the Stage-A proposed-position **record** or only of its **identity payload**.

This addendum closes **only** those four representation gaps, plus the minimum surrounding shape freeze required to make the Stage-A artifact total (§4) and to prove that no Stage-C registered value requires an unregistered implementation choice (§13).

**What this addendum does not touch.** No statistical quantity, estimand, multiplicity rule, randomization rule, `K` threshold, provider-eligibility predicate, runtime rule, failure token, state-machine transition, module boundary, function signature, digest-chain relationship, or canonicalization rule is created, revised, weakened, strengthened, reordered, or reinterpreted. `RuntimeSnapshotV1` is not reopened (§11). The canonical reader/verification procedure is not changed (§12).

---

## 2. Binding inputs

Read in full for this record, read-only, not modified, not reopened, not reinterpreted:

1. `docs/post_phaseP_confirmatory_randomization_implementation_design.md` (Revision 3) — the binding implementation design.
2. `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md` — the binding authorization boundary.

Inspected read-only as frozen upstream axioms:

3. `docs/post_phaseP_analysis_contract_decision.md` (Revision 4).
4. `docs/post_phaseP_confirmatory_randomization_design_decision.md` (Revision 4).

Source facts verified directly for this record (read-only, no execution):

| # | Fact | Verified at |
|---|---|---|
| **O1** | `QAMode` is a `str` enum whose canonical serialized members are `"off"`, `"partial"`, `"full"`, `"ablation"` | `src/iqa_soa/types.py:19-25` |
| **O2** | Execution rows persist the treatment label as `treatment.qa_mode.value` — i.e. the lowercase canonical serialized form, not the Python attribute name | `src/iqa_soa/experiment/runner.py:614` (and `runner.py:553` for the context copy) |
| **O3** | `repetition` is a **0-based** integer index: the runner iterates `for repetition in range(actual_repetitions)` | `src/iqa_soa/experiment/runner.py:379` |
| **O4** | The ordinary provider seed is `_seed_for(repetition) -> int`, a function of the **repetition index alone** (given frozen `config.seeds`); it does not depend on task, provider, or model, and both members of a matched contrast receive the identical value | `src/iqa_soa/experiment/runner.py:380, 695-701` |
| **O5** | The frozen run manifest already persists the ordinary seeds as a flat list indexed by repetition: `"seeds": [self._seed_for(index) for index in range(actual_repetitions)]` | `src/iqa_soa/experiment/runner.py:329` |
| **O6** | Physical call order within a `(case, repetition)` is `enumerate(ordered)` over the deterministic `_ordered_treatments` tuple, persisted as 0-based `treatment_index` alongside `treatment_order` | `src/iqa_soa/experiment/runner.py:381-384, 616-617, 703-722` |

O1-O6 are historical observations about the current committed tree. Nothing in `src/` is modified by this document.

---

## 3. Classification principle

**[SCHEMA — FROZEN]** For every value that Stage C (`FINAL_REGISTRATION_FROZEN`) eventually freezes, exactly one of three categories applies:

> **A. `GLOBAL_FROZEN_CONSTANT`** — already fixed by the binding methodology/design documents, and therefore stamped by implementation as a literal or version constant. It requires no caller choice in Stage A.
>
> **B. `STAGE_A_PROPOSED_VALUE`** — an experiment-specific or deferred prospective value that **must** be recorded in `registration_draft.json` before eligibility is assessed.
>
> **C. `DETERMINISTIC_STAGE_C_DERIVATION`** — computed without any new choice, from the immutable Stage-A draft contents plus the immutable eligibility manifest.

**No Stage-C registered value may fall into a fourth category such as "choose later."** §10 classifies every statistical quantity the frozen contracts name; §13 proves the classification is exhaustive over the Stage-C freeze list. If any value required a fourth category, this clarification would return `CLARIFICATION_BLOCKED_BY_FROZEN_CONTRACT`; §13 shows none does.

---

## 4. `RegistrationDraftV1` — top-level schema frozen

### 4.1 Artifact schema version literal

**[SCHEMA — FROZEN]** The Stage-A artifact's `schema_version` literal is exactly:

```
"RegistrationDraftV1"
```

### 4.2 Top-level field set — exactly these thirteen fields, no more, no fewer

**[SCHEMA — FROZEN]** `registration_draft.json` contains exactly:

```
schema_version
registration_state
confirmatory_profile
design_id
created_at
proposed_tasks
proposed_strata
proposed_repetitions
proposed_provider_seeds
proposed_positions
proposed_runtime_configuration
proposed_statistical_configuration
self_digest
```

There is **no** `registration_draft_digest` same-object alias field, exactly as implementation design §5.B.1 already requires (`registration_draft.json: stores: self_digest; does NOT store: registration_draft_digest`). The name `registration_draft_digest` remains a **downstream-only** reference name used by `eligibility_manifest.json` and `registration_manifest.json` when pointing at this artifact's `self_digest`.

There is **no** `position_id` anywhere in `registration_draft.json` (§5).

Frozen literal values, restated unchanged from the implementation design:

```
registration_state    = "REGISTRATION_DRAFT"                          (implementation design §5.A, §6)
confirmatory_profile  = "post_phaseP_confirmatory_randomization_v1"   (implementation design §5.C)
```

### 4.3 Per-field type freeze

**[SCHEMA — FROZEN]** Every field's JSON type and admissible content:

| Field | Type | Content rule | Class (§3) |
|---|---|---|---|
| `schema_version` | string | exactly `"RegistrationDraftV1"` | A |
| `registration_state` | string | exactly `"REGISTRATION_DRAFT"` | A |
| `confirmatory_profile` | string | exactly `"post_phaseP_confirmatory_randomization_v1"` | A |
| `design_id` | string | non-empty; byte-identical wherever it appears in this design's artifact chain and execution rows (implementation design §5.C check 2). **[DEFERRED VALUE SELECTION]** — no value is chosen here | B |
| `created_at` | string | RFC 3339 UTC instant, `Z` designator mandatory, second precision, no fractional seconds, no non-`Z` offset: `YYYY-MM-DDTHH:MM:SSZ` | B |
| `proposed_tasks` | array of string | non-empty; each a `task_id`; sorted ascending by Unicode code point; unique | B |
| `proposed_strata` | array of `ProposedStratumV1` | non-empty; sorted ascending by `(provider, model)`; unique | B |
| `proposed_repetitions` | array of `ProposedRepetitionsEntryV1` | exactly one entry per `(task_id, provider, model)` in `proposed_tasks × proposed_strata`; sorted ascending by `(task_id, provider, model)` | B |
| `proposed_provider_seeds` | array of `ProposedProviderSeedEntryV1` | exactly one entry per distinct `repetition` index appearing in `proposed_positions`; sorted ascending by `repetition`; unique on `repetition` | B |
| `proposed_positions` | array of `ProposedPositionV1` | non-empty; sorted ascending by `(task_id, provider, model, repetition, slot)`; unique on that tuple (§5, §6) | B |
| `proposed_runtime_configuration` | object | the complete registration-expected `RuntimeSnapshotV1` (implementation design §5.I), bound as already implemented under Work Unit 1. **Not reopened** (§11) | B |
| `proposed_statistical_configuration` | object | exactly one `ProposedStatisticalConfigurationV1` (§7) | mixed A/B — see §7 |
| `self_digest` | string | lowercase 64-character hex SHA-256, computed per implementation design §5.B.2 | C |

Nested element types:

```
ProposedStratumV1 — exactly:
    provider            string, non-empty
    model               string, non-empty

ProposedRepetitionsEntryV1 — exactly:
    task_id             string, non-empty, member of proposed_tasks
    provider            string, non-empty
    model               string, non-empty       ((provider, model) member of proposed_strata)
    repetition_count    JSON integer >= 1

ProposedProviderSeedEntryV1 — exactly:
    repetition          JSON integer >= 0       (0-based, O3)
    provider_seed       JSON integer            (O4)

ProposedPositionV1 — exactly the seven fields frozen at §5.2.
```

`repetition_count` is per `(task_cluster, model_stratum)` because that is the granularity of the frozen target estimand's inner average `Sched(k, m)` (analysis contract §5.3) and of analysis-contract §22 item 1. A uniform repetition count across all `(task, stratum)` pairs is a permitted special case, not a separate schema.

`proposed_provider_seeds` is keyed on `repetition` alone because the ordinary provider seed is already frozen as a function of the repetition index (design decision F5 and §10 "Repetitions / seeds — one seed per repetition, fixed at freeze"; analysis contract §10.4 items 1 and 3, "the seed is a matched-contrast property, not a treatment property" and "seed and repetition are collinear"), and because the committed instrument already persists exactly that shape ([OBSERVED] O4, O5). **These are ordinary provider seeds only.** They are not, and can never become, randomization bits, assignment material, or Monte Carlo seed material (design decision §5.3 item 7; implementation design §5.L, §5.M).

### 4.4 Canonical JSON and `self_digest` — unchanged

**Nothing in §5.B of the implementation design is altered by this addendum.** Restated for the avoidance of doubt, not amended:

- Canonical bytes are `json.dumps(obj_without_self_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` encoded UTF-8 (implementation design §5.B.2).
- Fields requiring exact decimal representation are canonical decimal strings; integer-valued fields — the design names `K`, `max_attempts`, `entropy_bytes`, `randomization_mc_samples` explicitly — remain ordinary JSON integers, never strings.
- `NaN` / `Infinity` / `-Infinity` are forbidden.
- Arrays preserve registered order; the sorting and uniqueness rules stated in §4.3 are **schema-level rules applied before canonicalization**, exactly as the design already does for `retryable_error_classes` (§5.I.4), never canonicalization-time transformations.
- Object keys are sorted by ordinary code-point ordering via `sort_keys=True`.
- `self_digest` is SHA-256, lowercase hex, over the canonical bytes of the object **with only `self_digest` removed**.
- The persisted file is the canonical JSON including the computed `self_digest`, plus exactly one trailing LF that is not part of any digest.

### 4.5 Write-time validation — the draft is not written unless all of these hold

**[SCHEMA — FROZEN]** Implementation design §6 gives the `→ REGISTRATION_DRAFT` transition the refusal behavior "N/A (first stage; malformed draft simply is not written)". This addendum states what "malformed" means, exhaustively:

| # | Rule |
|---|---|
| **V1** | `schema_version`, `registration_state`, `confirmatory_profile` equal their frozen literals (§4.2). |
| **V2** | `design_id` is a non-empty string; `created_at` matches the frozen timestamp form (§4.3). |
| **V3** | `proposed_tasks` is non-empty, sorted, unique. |
| **V4** | `proposed_strata` is non-empty, sorted, unique, and every element has exactly the two keys `provider`, `model`. |
| **V5** | `proposed_repetitions` covers the full cross product `proposed_tasks × proposed_strata` exactly once each, is sorted, and every `repetition_count >= 1`. |
| **V6** | `proposed_positions` is exactly: for every `proposed_repetitions` entry with count `R`, for every `repetition ∈ {0, …, R−1}`, exactly two positions, with `slot = 1` and `slot = 2`. Sorted and unique on `(task_id, provider, model, repetition, slot)`. |
| **V7** | Within every `(task_id, provider, model, repetition)` group, the two positions' `baseline_label` values are exactly the multiset `{"off", "full"}` — one of each (§6). |
| **V8** | `proposed_provider_seeds` covers exactly the distinct `repetition` values appearing in `proposed_positions`, sorted, unique; and every position's `provider_seed` equals the entry for that position's `repetition` (O4; design decision F5). |
| **V9** | `proposed_statistical_configuration` has exactly the frozen key set (§7); every stamped constant equals its frozen literal; `randomization_mc_samples` is `null` or a positive JSON integer (§8). |
| **V10** | `proposed_runtime_configuration` is a complete `RuntimeSnapshotV1` whose `runtime_identity_digest` and `self_digest` both verify per implementation design §5.I and §5.B.2. **Governed by §5.I; not reopened here** (§11). |
| **V11** | `self_digest` is computed last, per implementation design §5.B.2, over the object with `self_digest` removed. |

V1-V11 are total: they constrain every field of §4.2 and every element type of §4.3. A draft failing any of them is not written; there is no partial, warning-only, or repair path. Once written, the draft is **never edited in place** — supersession requires a new `design_id` (implementation design §5.A, §6).

---

## 5. Proposed position record versus position identity payload — frozen

This closes gap 4 of §1.

### 5.1 `ConfirmatoryPositionV1` identity payload — unchanged, still exactly six fields

**Restated from implementation design §5.C, not amended.** The identity payload contains exactly:

```
task_id
provider
model
repetition
provider_seed
slot
```

Those six fields — **and only those six** — are hashed at final registration to derive `position_id`:

```
position_id = SHA256( canonical JSON of the six identity fields only )
```

canonicalized and hex-encoded per implementation design §5.B.2. The treatment label is excluded because "the position's identity must not depend on which label it ends up receiving, or the identity itself would leak assignment information and could not be registered before `b_k` is drawn" (implementation design §5.C).

`POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES.`

### 5.2 The Stage-A record is **not** identical to the identity payload

**[SCHEMA — FROZEN]** The Stage-A proposed-position **record** is a strict superset of the identity payload by exactly one field.

`ProposedPositionV1` contains exactly these seven fields, no more, no fewer:

```
task_id           string, non-empty
provider          string, non-empty
model             string, non-empty
repetition        JSON integer >= 0              (0-based, O3)
provider_seed     JSON integer                   (O4)
slot              JSON integer, exactly 1 or 2   (design decision §4.A: slot ∈ {1,2})
baseline_label    string, exactly "off" or "full"
```

**`baseline_label` is NOT part of `position_id`.** It is carried by the record, never by the identity payload.

**No `position_id` exists in `registration_draft.json`.** `position_id` first exists at Stage C, derived from the six identity fields of each retained proposed position.

At final registration, for every retained position:

```
position_id     = SHA256(canonical JSON of the six identity fields only)
baseline_label  = copied from the immutable Stage-A proposed position
```

This is precisely what lets `S_k` be bound prospectively, before eligibility, **without** making treatment assignment part of position identity.

### 5.3 Treatment-label vocabulary — the repository's existing canonical serialization

**[SCHEMA — FROZEN]** `baseline_label` uses the repository's already-existing canonical serialized `QAMode` labels:

```
"off"    ==  QAMode.OFF.value
"full"   ==  QAMode.FULL.value
```

[OBSERVED] `src/iqa_soa/types.py:19-25`; execution rows already serialize the realized label the same way, as `treatment.qa_mode.value` ([OBSERVED] `src/iqa_soa/experiment/runner.py:614`). **No new treatment-label vocabulary is invented.** `QAMode.PARTIAL` and `QAMode.ABLATION` exist in the enum but are outside the confirmatory design, whose contrast is exactly `OFF` versus `FULL` and whose `complement` is defined only on that pair (implementation design §5.D; design decision §4.A).

Because both the row's `qa_mode` and the registered `baseline_label` use the identical serialization, implementation design §5.C checks 12 and 13 (`baseline_label` equals the registered `S_k(position)`; `qa_mode` equals `resolve_label(baseline_label, b_k)`) compare like with like, with no encoding conversion anywhere.

### 5.4 `slot` versus the legacy `treatment_index`

`slot ∈ {1, 2}` is the confirmatory schema's own field, frozen by design decision §4.A and carried in both the identity payload and the execution-row contract (implementation design §5.C). The committed legacy runner separately persists a 0-based `treatment_index` and a `treatment_order` list ([OBSERVED] `runner.py:381-384, 616-617`). Those legacy fields are unchanged, and the plumbing that populates a confirmatory row's `slot` is runner/collector work already scoped by implementation design §8 items 6 and 8. **This addendum neither renames nor modifies any legacy field.**

`PROPOSED_POSITION_SCHEMA_FROZEN: YES.`

---

## 6. Baseline schedule `S_k` binding — frozen

This closes gap 3 of §1.

### 6.1 Every proposed physical position carries exactly one `baseline_label`

**[SCHEMA — FROZEN]** Every element of `proposed_positions` carries exactly one `baseline_label ∈ {"off", "full"}` (§5.2, §5.3). No position may carry zero, and none may carry more than one.

The **complete Stage-A collection** of

```
( position identity fields , baseline_label )
```

over all elements of `proposed_positions` **is** the frozen proposed baseline schedule `S_k`.

`S_k` is therefore a persisted, digest-authenticated, immutable object as of the moment `registration_draft.json` is written — which is strictly before eligibility is assessed (implementation design §5.A Stage B), strictly before final registration, strictly before `randomization_mc_provenance.json`, strictly before any `b_k` is drawn, and strictly before any execution (implementation design §6).

### 6.2 Where the recorded labels come from

`S_k` is the output of the existing deterministic counterbalancing schedule, which implementation design §5.D item 1 owns and leaves **unmodified**: `_ordered_treatments` ([OBSERVED] `runner.py:703-722`) is a pure function of frozen configuration — no entropy source is consulted, and the same inputs always reproduce the same order (implementation design §2 Fact 1). Recording its per-slot output into `proposed_positions` at Stage A is therefore a **faithful transcription of an already-deterministic frozen function**, not a new choice, not a new schedule, and not a randomization act.

Balance is structural, not asserted: V6/V7 (§4.5) require each `(task_id, provider, model, repetition)` group to contain exactly two positions, `slot = 1` and `slot = 2`, carrying exactly one `"off"` and one `"full"`. Applying `complement` uniformly to every position nested in a task therefore preserves the OFF/FULL count within that task exactly — design decision §6 requirement 2 and implementation design §5.D's balance invariant, satisfied by construction of the schema rather than by argument.

### 6.3 What Stage C may and may not do to `S_k`

**[SCHEMA — FROZEN]**

Stage C **may** do exactly one thing to the proposed baseline schedule:

> **FILTER** positions according to the already-frozen immutable eligibility disposition of their `(provider, model)` stratum (implementation design §5.A Stages B and C: "Only `CONFIRMATORY_ELIGIBLE` strata may appear in the confirmatory matrix").

Stage C **must not**:

- recompute a different baseline label for any position;
- rerun schedule shuffling, `_ordered_treatments`, or any other ordering procedure to obtain a new label;
- choose a new baseline schedule;
- alter any baseline label because eligibility results are now known;
- reorder, renumber, or reassign `slot` values.

**Binding equality.** For every retained final confirmatory position:

```
registration_manifest.baseline_label  ==  registration_draft proposed position.baseline_label
```

byte-for-byte, for the position with the identical six identity fields.

**Consequence, stated exactly:** eligibility affects **membership** — which positions are in the confirmatory matrix and which are descriptive-only — and **never** the `S_k` value of any retained position.

### 6.4 Filtering cannot unbalance a retained task

The eligibility disposition is per `(provider, model)` stratum (implementation design §5.A Stage B). By V6/V7, every `(task_id, provider, model, repetition)` group contributes a complete `{"off", "full"}` pair. Filtering therefore removes **whole pairs**, never a single member of a pair. Every retained task cluster consequently keeps exact OFF/FULL balance under `S_k` and under `C(S_k)` alike, with no rebalancing step and no rebalancing choice at Stage C.

`BASELINE_SCHEDULE_BOUND_AT_STAGE_A: YES.`

---

## 7. `ProposedStatisticalConfigurationV1` — frozen key set

This closes gap 1 of §1. The complete classification argument for every quantity, including the ones that deliberately receive **no** key, is in §10.

### 7.1 The exact key set — eleven keys, no more, no fewer

**[SCHEMA — FROZEN]** `proposed_statistical_configuration` contains exactly:

```
schema_version
statistic_spec_id
randomization_mc_samples
alpha
multiplicity_architecture
primary_endpoint
secondary_endpoint_sequence
primary_estimand_architecture
aggregation_rule
treatment_contrast_orientation
randomization_exact_enumeration_max_k
```

No `etc.` No "future configuration." No optional key. No architecture choice.

### 7.2 Key-by-key freeze

| Key | Type | Frozen value / admissible content | Class (§3) | Frozen source |
|---|---|---|---|---|
| `schema_version` | string | exactly `"ProposedStatisticalConfigurationV1"` | A | this addendum §7.1 (schema identity, mirroring the `RuntimeSnapshotV1` precedent at implementation design §5.I) |
| `statistic_spec_id` | string | exactly `"confirmatory_task_sign_flip_v1"` | A | implementation design §5.K, §7 PR-8 |
| `randomization_mc_samples` | JSON integer `> 0` **or** `null` | caller-proposed; `null` means "no Monte Carlo sample count has been prospectively proposed for this draft" | **B** | §8 of this addendum; implementation design §5.L.3; design decision §7.4.2 conditions E-G |
| `alpha` | string | exactly `"0.05"` (canonical decimal string) | A | analysis contract §16.3 (`ALPHA: two-sided 0.05`); design decision §10 "Alpha / multiplicity" |
| `multiplicity_architecture` | string | exactly `"FIXED_SEQUENCE_GATEKEEPING"` | A | analysis contract §16.1 |
| `primary_endpoint` | string | exactly `"unsafe_action_executed"` | A | analysis contract §6.1 |
| `secondary_endpoint_sequence` | array of string | exactly, **in this frozen order**: `["safety_security_violation", "unsafe_action_proposed", "constraint_violation", "privacy_leak", "attack_success"]` | A | analysis contract §6.2 (S-1 → S-5), §16.1 |
| `primary_estimand_architecture` | string | exactly `"SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES"` | A | analysis contract §5.2 |
| `aggregation_rule` | string | exactly `"NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN"` | A | analysis contract §8.2, §5.3; design decision §7.3 |
| `treatment_contrast_orientation` | string | exactly `"FULL_MINUS_OFF"` | A | analysis contract §5.3 item 4; design decision §7.3; implementation design §5.K |
| `randomization_exact_enumeration_max_k` | JSON integer | exactly `16` | A | design decision §7.4; implementation design §5.L.1 |

**Only `randomization_mc_samples` is caller-proposed.** Every other key is a stamped literal that implementation writes without consulting the caller; a draft whose stamped key does not equal its frozen literal fails V9 and is not written.

### 7.3 Why the stamped constants are recorded at all

Implementation design §5.K already establishes the pattern for `statistic_spec_id`: a `GLOBAL_FROZEN_CONSTANT` that is nevertheless *recorded* in the artifact chain so that the analyzer can detect a mismatch (`STATISTIC_VERSION_MISMATCH`, implementation design §11) rather than silently assuming agreement. This addendum applies that identical, already-frozen pattern to the remaining constants that final registration or confirmatory analysis reads. Recording a constant is an auditability act; it is **never** a caller choice, and it introduces no new statistical content.

### 7.4 Representation notes

- `alpha` is a **canonical decimal string**, not a JSON number, because implementation design §5.B.2 requires canonical decimal strings for schema numeric fields that need exact decimal representation, and `0.05` has no exact binary floating-point representation. `randomization_mc_samples` and `randomization_exact_enumeration_max_k` are ordinary JSON integers, because §5.B.2 names integer-valued fields — `randomization_mc_samples` explicitly — as remaining ordinary JSON integers, never strings.
- `secondary_endpoint_sequence` is **ordered, not sorted**. Its order is semantic (the frozen fixed-sequence gate order S-1 → S-5, analysis contract §16.1) and implementation design §5.B.2 requires arrays to preserve registered order.
- The frozen `alpha` is **two-sided**. Two-sidedness is carried by the frozen statistic itself — `T(r) = |(1/K) Σ_k r_k D_k^obs|` is an absolute value (design decision §7.1) — not by a separate schema field, so no sidedness key is added.

`STATISTICAL_CONFIGURATION_KEYSET_FROZEN: YES.`

---

## 8. `randomization_mc_samples` — nullability and the Stage-C gate, frozen

This closes gap 2 of §1.

### 8.1 One representation, always present

**[SCHEMA — FROZEN]** `proposed_statistical_configuration` contains the key `randomization_mc_samples` **always**, in every draft, in every design, regardless of the eventual `K`.

Its type is: **positive JSON integer OR `null`.**

Interpretation of `null`:

> `null` = **no Monte Carlo sample count has been prospectively proposed for this draft.**

`null` is not "zero samples," not "decide later at Stage C," and not "the field is inapplicable." It is a registered, digest-authenticated statement that the caller proposed no `M`. Absence of the key is **never** a valid encoding of that statement, and a draft missing the key fails V9 and is not written.

### 8.2 Stage-C derivation of `K` and `randomization_mode`

Stage C derives, with no new choice:

```
K = | { task_id ∈ proposed_tasks :
        at least one proposed position with that task_id belongs to a stratum whose
        eligibility_manifest disposition is CONFIRMATORY_ELIGIBLE } |
```

and then, exactly per implementation design §5.L.1:

```
K <= 16   ->   randomization_mode = "EXACT_ENUMERATION"
K >  16   ->   randomization_mode = "MONTE_CARLO"
```

Both are `DETERMINISTIC_STAGE_C_DERIVATION` (class C). Neither is a Stage-A field, and neither may be proposed, overridden, or hinted at by the caller.

### 8.3 The frozen mode/`M` consistency gate

**[SCHEMA — FROZEN]**

**If `K <= 16`** (`randomization_mode = "EXACT_ENUMERATION"`):

- `randomization_mc_samples` **MUST** be `null` in the draft.
- No `M` is used anywhere. No Monte Carlo sample count is selected, derived, defaulted, or fabricated.
- If the draft instead contains a positive integer, **final registration refuses that draft** rather than silently discarding, ignoring, or reinterpreting the registered value.

**If `K > 16`** (`randomization_mode = "MONTE_CARLO"`):

- `randomization_mc_samples` **MUST** be a positive JSON integer in the draft.
- If the Stage-A value is `null`, **FINAL REGISTRATION MUST REFUSE TO FREEZE.**
- It **MUST NOT** select `M` at Stage C, at MC-provenance generation time, at assignment time, at execution time, or at analysis time.
- The draft is abandoned, and a **new Stage-A draft under a new `design_id`** must prospectively propose `M` — exactly the abandon-and-recreate remedy already frozen at implementation design §5.A ("the entire registration … is abandoned as a unit and a **new** … triple is created under a **new** `design_id`") and §6 ("Draft may be superseded by a **new** draft under a new `design_id`; never edited in place once written").

Both refusals are hard refusals: no partial freeze, no warning-only path, no automatic repair, no default value.

### 8.4 Why the gate is stated in exactly this direction

Every experimental choice stays **before** eligibility and final registration. Under this rule:

- `M` is proposed at Stage A, which precedes eligibility (Stage B), which precedes final registration (Stage C), which precedes MC-provenance generation, which precedes assignment, which precedes any execution, which precedes any endpoint value or failure information (implementation design §6).
- The design decision's `MONTE_CARLO_ASSIGNMENT_INDEPENDENCE` conditions are therefore satisfied *a fortiori*: condition **E** ("the RNG algorithm and `M` are fixed and documented before any confirmatory outcome exists") and condition **G** ("never selected, filtered, regenerated, or extended in response to the observed `p_MC`") hold structurally, because `M` is frozen and digest-authenticated several lifecycle states before an outcome can exist (design decision §7.4.2 A-G).
- Nothing invents `M` after the draft.

### 8.5 Interaction with the exact-mode provenance artifact — no contradiction

Implementation design §5.L.2 requires that, in `EXACT_ENUMERATION` mode, the artifact `randomization_mc_provenance.json` contain **no** `randomization_mc_samples` field — the field must be **absent**.

That rule governs `randomization_mc_provenance.json`. This addendum's rule governs `registration_draft.json`. They are different artifacts under different frozen rules, and both are satisfied simultaneously:

```
EXACT_ENUMERATION mode:
    registration_draft.json           -> randomization_mc_samples = null      (present, null)
    randomization_mc_provenance.json  -> randomization_mc_samples ABSENT      (§5.L.2, unchanged)

MONTE_CARLO mode:
    registration_draft.json           -> randomization_mc_samples = <positive integer>
    randomization_mc_provenance.json  -> randomization_mc_samples = the same registered value (§5.L.3)
```

The Stage-A `null` is **never** copied into the exact-mode provenance artifact. The exact-mode forbidden-field list of §5.L.2 is unchanged, unweakened, and unextended by this addendum.

Carry-forward at Stage C: the registered `randomization_mc_samples` value — `null` in exact mode, the proposed positive integer in Monte Carlo mode — is carried into `registration_manifest.json` as one of its registered values, which is what implementation design §5.L.3's analyzer check ("`M` equals the registered `randomization_mc_samples`") already presupposes. This addendum does not otherwise freeze `registration_manifest.json`'s top-level key set.

`M_NULLABILITY_AND_STAGE_C_GATE_FROZEN: YES.`

---

## 9. `statistic_spec_id`

**Restated from implementation design §5.K, not amended.**

```
statistic_spec_id = "confirmatory_task_sign_flip_v1"
```

is a **`GLOBAL_FROZEN_CONSTANT`** (class A). It is stamped into Stage A by implementation and is **not caller-selectable**. The Stage-A statistical object records it for auditability (§7.1, §7.3), which is what lets the analyzer raise `STATISTIC_VERSION_MISMATCH` (implementation design §11, §7 PR-8) rather than assume agreement.

No `<semver>` placeholder exists anywhere; a change to the statistic's implementation requires minting a new literal id, never bumping a version field (implementation design §5.K).

---

## 10. Complete statistical-quantity classification

**This section is the completeness check.** `statistic_spec_id` + `randomization_mc_samples` are **not** assumed sufficient. Every statistical quantity referenced by final registration or confirmatory analysis in the frozen analysis contract, the frozen randomization design decision, or the frozen implementation design is classified below into exactly one of §3's three categories. No quantity is invented here.

### 10.1 Quantities that become Stage-A statistical-configuration keys

| Quantity | Classification | Detail |
|---|---|---|
| Statistic version | **`GLOBAL_FROZEN_CONSTANT`**: `"confirmatory_task_sign_flip_v1"` — implementation design §5.K | Stage-A key `statistic_spec_id`, stamped |
| Monte Carlo sample count `M` | **`STAGE_A_PROPOSED_VALUE`** | Stage-A key `randomization_mc_samples`, JSON integer `> 0` or `null` (§8) |
| Significance threshold | **`GLOBAL_FROZEN_CONSTANT`**: two-sided `0.05` — analysis contract §16.3 | Stage-A key `alpha`, canonical decimal string `"0.05"` |
| Multiplicity architecture | **`GLOBAL_FROZEN_CONSTANT`**: `FIXED_SEQUENCE_GATEKEEPING` — analysis contract §16.1 | Stage-A key `multiplicity_architecture` |
| Fixed-sequence family membership: primary | **`GLOBAL_FROZEN_CONSTANT`**: `unsafe_action_executed` — analysis contract §6.1, §16.1 | Stage-A key `primary_endpoint` |
| Fixed-sequence family membership and order: secondaries | **`GLOBAL_FROZEN_CONSTANT`**: S-1…S-5 in frozen order — analysis contract §6.2, §16.1 | Stage-A key `secondary_endpoint_sequence` |
| Primary estimand identity | **`GLOBAL_FROZEN_CONSTANT`**: `SCHEDULED_ATTEMPT_PRIMARY_WITH_MECHANISM_SECONDARIES` — analysis contract §5.2 | Stage-A key `primary_estimand_architecture` |
| Weighting / aggregation | **`GLOBAL_FROZEN_CONSTANT`**: `NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN` — analysis contract §8.2, §5.3 | Stage-A key `aggregation_rule` |
| Contrast orientation | **`GLOBAL_FROZEN_CONSTANT`**: `FULL − OFF` — analysis contract §5.3 item 4; implementation design §5.K | Stage-A key `treatment_contrast_orientation` |
| Exact-enumeration threshold | **`GLOBAL_FROZEN_CONSTANT`**: `16` — design decision §7.4; implementation design §5.L.1 | Stage-A key `randomization_exact_enumeration_max_k` |

### 10.2 Quantities that are Stage-C deterministic derivations — deliberately **not** Stage-A keys

| Quantity | Classification | Exact derivation |
|---|---|---|
| `K` | **`DETERMINISTIC_STAGE_C_DERIVATION`** | Count of `task_id` values in the immutable `proposed_tasks` retaining at least one proposed position whose `(provider, model)` stratum is `CONFIRMATORY_ELIGIBLE` in the immutable eligibility manifest (§8.2) |
| `randomization_mode` | **`DETERMINISTIC_STAGE_C_DERIVATION`** | `K <= 16 → "EXACT_ENUMERATION"`; `K > 16 → "MONTE_CARLO"` (implementation design §5.L.1) |
| `position_id` (every position) | **`DETERMINISTIC_STAGE_C_DERIVATION`** | SHA-256 over the canonical JSON of the six identity fields of the immutable Stage-A proposed position (§5.1) |
| Confirmatory / descriptive-only stratum sets | **`DETERMINISTIC_STAGE_C_DERIVATION`** | Partition of `proposed_strata` by immutable eligibility disposition (§13.2) |
| Confirmatory / descriptive position sets | **`DETERMINISTIC_STAGE_C_DERIVATION`** | Partition of `proposed_positions` by their stratum's disposition (§13.2) |
| `θ_target` weights `w_k = 1/|A_Y|`, `w_m = 1/|M|`, `w_r = 1/|Sched(k,m)|` | **`DETERMINISTIC_STAGE_C_DERIVATION`** | Fixed arithmetic over the registered membership (analysis contract §5.3), given `aggregation_rule` |
| `registration_draft_digest`, `eligibility_manifest_digest`, `matrix_digest`, `self_digest` | **`DETERMINISTIC_STAGE_C_DERIVATION`** | Implementation design §5.B.2 / §5.B.3, over already-registered content |

### 10.3 Quantities that are global frozen constants requiring no Stage-A field at all

| Quantity | Classification and source |
|---|---|
| Potential-outcome unit = scheduled position; randomization unit = task cluster | **`GLOBAL_FROZEN_CONSTANT`** — design decision §4.A, §10. Carried by `confirmatory_profile` and by the frozen `ProposedPositionV1` / task-cluster structure itself; no separate field |
| Assignment support `B = {0,1}^K`, each point `2^{-K}` | **`GLOBAL_FROZEN_CONSTANT`** — design decision §4.E-4.F |
| `H0_sharp`; `B ⊥ Ω` | **`GLOBAL_FROZEN_CONSTANT`** — design decision §5.5, §5.6 |
| Relative sign `r_k(b) = 1 − 2(b_k ⊕ b_obs,k)`; statistic `T(r) = \|(1/K) Σ_k r_k D_k^obs\|` | **`GLOBAL_FROZEN_CONSTANT`** — design decision §7.1; carried by `statistic_spec_id` |
| Zero-difference blocks retained in `K`; `K_plus` used only for reporting granularity, never for membership | **`GLOBAL_FROZEN_CONSTANT`** — design decision §7.3, §7.4.1; implementation design §5.K |
| Monte Carlo plus-one formula `(count + 1)/(M + 1)` | **`GLOBAL_FROZEN_CONSTANT`** — design decision §7.4.2; implementation design §5.L.3 |
| Total-observation / fail-closed rule | **`GLOBAL_FROZEN_CONSTANT`** — design decision §8; implementation design §5.G, §5.H |
| Four eligibility predicates and their `DESCRIPTIVE_ONLY_*` tokens | **`GLOBAL_FROZEN_CONSTANT`** — design decision §9; implementation design §5.A Stage B, §11 |
| `endpoint_applicability` map and `endpoint_role_compatibility` map | **`GLOBAL_FROZEN_CONSTANT`** — analysis contract §6.4, §6.5: machine-decidable from frozen case declarations and frozen endpoint registration, produced before execution and hash-pinned with the rest of the freeze. Computed by implementation, never typed by a caller. Its Stage-A consequence is the caller's `proposed_tasks ⊆ A_Y`, which is already a class-B field |
| `PAIR_KEYS` / `matched_contrast_key` | **`GLOBAL_FROZEN_CONSTANT`** — analysis contract §10.2; already encoded by the six identity fields |
| Clustering unit = task (`task × model` is never a cluster) | **`GLOBAL_FROZEN_CONSTANT`** — analysis contract §10.6 |
| MC source constants: `source_kind = "PYTHON_SECRETS_TOKEN_BYTES"`, `source_api = "secrets.token_bytes"`, `entropy_bytes = 32`, `seed_encoding = "uint256_big_endian"`, `rng_library = "numpy"`, `rng_bit_generator = "PCG64"` | **`GLOBAL_FROZEN_CONSTANT`** — implementation design §5.L.3. Fields of `randomization_mc_provenance.json`, not of the draft |
| Assignment source constants: `source_kind = "PYTHON_SECRETS_RANDBITS"`, `source_api = "secrets.randbits"` | **`GLOBAL_FROZEN_CONSTANT`** — implementation design §5.M. Fields of `assignment_manifest.json`, not of the draft |

### 10.4 Quantities explicitly outside the confirmatory statistical configuration

Listed so that no reader mistakes their absence for an unresolved choice.

| Quantity | Disposition |
|---|---|
| `bootstrap_seed` and `_bootstrap_mean_ci` | **Legacy-only.** Implementation design §5.L.3 freezes that it is never read by, derived from, or fed into the confirmatory Monte Carlo path, and that `metrics/confirmatory.py` has no parameter through which it could reach the MC draw. Not a Stage-A field; not a registered confirmatory value |
| `TASK_COMPOSITION_RESAMPLING_INTERVAL`, `confidence = 0.95`, `INTERVAL_DEGENERATE_ZERO_VARIANCE` | **Descriptive / legacy analysis objects** — analysis contract §15.3, §15.4. Not confirmatory-test inputs; not registered confirmatory values |
| `θ_complete`, `[θ_lower, θ_upper]`, the global missingness-sensitivity surface | **Analysis-contract reporting objects** — analysis contract §5.4-§5.6. The confirmatory test requires total observation and fails closed instead of invoking missingness machinery (design decision §8; implementation design §5.G, §5.H). Not registered confirmatory values |
| `K_plus`, `p_min = 2^{1−K_plus}`, `T_max` | **Analysis-time deterministic reporting derivations** from the realized `D_k^obs` — design decision §7.4.1. Explicitly never affect matrix membership or `K`. Not registered values |
| `exact_support_size = 2^K` | **Deterministic derivation from `K`**, and a field of `randomization_mc_provenance.json` in exact mode (implementation design §5.L.2), not of the draft |
| `numpy_version`, `seed_hex`, `generated_at` (MC mode) | **Captured at MC-provenance generation time** from the executing environment and the entropy source (implementation design §5.L.3). Environment observations and post-registration generation outputs, not caller choices and not Stage-C registered values. Generating any of them is **[NOT AUTHORIZED]** by this document |
| `EXPERIMENT_READY` conditions R-A…R-H and every numeric tolerance in R-B…R-G (applicable-cluster minimum above 6, loss tolerance, per-stratum minimum, bounds-width tolerance, effective-information target) | **Upstream-open readiness parameters** — analysis contract §12.3 and §22 item 2, marked `[NOT AUTHORIZED]` there pending the registered design study. They are **not** among the values implementation design §5.A Stage C freezes, `EXPERIMENT_READY` is **not** a state in the frozen §6 state machine, and no confirmatory artifact carries them. Their openness therefore creates no fourth category for any *registered* value (§13.4) |
| The resolution observation "six nonzero task-cluster differences are necessary, not sufficient, for `p < 0.05`" | **Combinatorial property of the frozen statistic** — analysis contract §12.2; a realized-outcome property that "cannot be a pre-run gate." Not a registered value |
| Repetition counts, ordinary seeds, task membership, stratum membership, `design_id` | **`STAGE_A_PROPOSED_VALUE`** (class B), carried by the dedicated top-level fields of §4.2 rather than by the statistical-configuration object. Their concrete values are **[DEFERRED VALUE SELECTION]** and none is chosen here |

**No quantity above required a fourth category.**

---

## 11. Runtime clarification is out of scope

`RuntimeSnapshotV1` is **not reopened.** Implementation design §5.I (two-layer contract: `runtime_identity_digest` over exactly the invariant fields; `captured_at` / `self_digest` as capture metadata that is never compared for equality), §5.I.1 (identity payload), §5.I.3 (`EnvironmentIdentityV1` field set), §5.I.4 (timeout/retry representation), §5.I.5 (three capture points), and §5.I.6 (failure tokens) stand entirely unchanged.

The Work Unit 1 repair already follows frozen §5.I by binding the complete registration-expected `RuntimeSnapshotV1` into `proposed_runtime_configuration` and deriving/validating its identity digest. §4.3 and V10 (§4.5) record that field's presence and its validation obligation **by reference only**; they add no field, remove no field, and change no comparison rule.

**This addendum changes no runtime methodology.** It also makes no statement about the cardinality relationship between `proposed_strata` and runtime snapshots; that relationship is governed by §5.I and is not opened here.

---

## 12. Canonical reader clarification

**No byte-for-byte reader canonicality is added.** Implementation design §5.B.2's verification procedure remains exactly:

```
read bytes
  -> strip at most one trailing LF
  -> parse JSON
  -> remove self_digest
  -> recanonicalize (§5.B.2 algorithm)
  -> recompute SHA-256 over the recanonicalized UTF-8 bytes
  -> compare against the claimed self_digest
```

The **writer** emits canonical JSON plus exactly one LF.

A semantically equivalent noncanonical input representation that parses to the same authenticated object is **not, by itself, a new failure condition** under the current frozen verification procedure. **This addendum does not change that rule**, does not add a reader-side canonicality check, and does not add a failure token.

---

## 13. Required completeness proof

### 13.1 Traceability table

Every value that implementation design §5.A Stage C names as frozen by `FINAL_REGISTRATION_FROZEN`, mapped to exactly one source.

| # | Final registered value | Source class | Exact source / derivation |
|---|---|---|---|
| 1 | `schema_version` | Global frozen constant | Literal, stamped by `freeze_final_registration` |
| 2 | `registration_state` | Global frozen constant | Literal `"FINAL_REGISTRATION_FROZEN"` (implementation design §5.A, §6) |
| 3 | `confirmatory_profile` | Global frozen constant | Literal `"post_phaseP_confirmatory_randomization_v1"` (implementation design §5.C) |
| 4 | `design_id` | Stage-A field | `registration_draft.design_id` (§4.3), byte-identical |
| 5 | **Task membership** | Deterministic derivation | Task ids in `proposed_tasks` retaining ≥1 confirmatory position after the eligibility partition (§13.2) |
| 6 | **Provider/model membership** (confirmatory strata) | Deterministic derivation | `{ s ∈ proposed_strata : eligibility_manifest disposition(s) = CONFIRMATORY_ELIGIBLE }` |
| 7 | **Descriptive-only strata** | Deterministic derivation | `proposed_strata \ (row 6)` — the exact complement (§13.2) |
| 8 | **Repetitions** | Stage-A field | `proposed_repetitions`, restricted to retained `(task, stratum)` pairs; values copied unchanged |
| 9 | **Ordinary provider seeds** | Stage-A field | `proposed_provider_seeds`, copied unchanged; per-position `provider_seed` copied from the immutable proposed position |
| 10 | **Positions** (confirmatory) | Deterministic derivation | Elements of `proposed_positions` whose `(provider, model)` is in row 6 |
| 11 | **Positions** (descriptive) | Deterministic derivation | Elements of `proposed_positions` whose `(provider, model)` is in row 7 (§13.2) |
| 12 | **`position_id`** (confirmatory and descriptive) | Deterministic derivation | `SHA256(canonical JSON of the six identity fields only)` of the immutable proposed position (§5.1) |
| 13 | **`baseline_label` / `S_k`** | Stage-A field | Copied from the immutable proposed position; equality is binding (§6.3) |
| 14 | **`statistic_spec_id`** | Global frozen constant | `"confirmatory_task_sign_flip_v1"`, stamped into Stage A (§9) and carried forward |
| 15 | **`K`** | Deterministic derivation | §8.2 / §10.2 |
| 16 | **`randomization_mode`** | Deterministic derivation | `K <= 16 → EXACT_ENUMERATION`; `K > 16 → MONTE_CARLO` (implementation design §5.L.1) |
| 17 | **`randomization_mc_samples` (`M`)** | Stage-A field | `proposed_statistical_configuration.randomization_mc_samples`, carried unchanged; the mode/`M` gate of §8.3 refuses the freeze rather than selecting a value |
| 18 | `alpha` | Global frozen constant | `"0.05"` (analysis contract §16.3), stamped into Stage A, carried forward |
| 19 | `multiplicity_architecture`, `primary_endpoint`, `secondary_endpoint_sequence` | Global frozen constant | Analysis contract §6.1, §6.2, §16.1; stamped into Stage A, carried forward |
| 20 | `primary_estimand_architecture`, `aggregation_rule`, `treatment_contrast_orientation`, `randomization_exact_enumeration_max_k` | Global frozen constant | §7.2; stamped into Stage A, carried forward |
| 21 | Registration-expected `RuntimeSnapshotV1` and its `runtime_identity_digest` | Stage-A field (+ deterministic digest) | `proposed_runtime_configuration` (§4.3, V10), governed by implementation design §5.I; not reopened (§11) |
| 22 | `registration_draft_digest` | Deterministic derivation | `registration_draft.json.self_digest` (implementation design §5.B.3) |
| 23 | `eligibility_manifest_digest` | Deterministic derivation | `eligibility_manifest.json.self_digest` (implementation design §5.B.3) |
| 24 | `matrix_digest` | Deterministic derivation | SHA-256 over the frozen confirmatory matrix under §5.B.2 canonicalization — every input is already registered (§13.3) |
| 25 | `self_digest` | Deterministic derivation | Implementation design §5.B.2 |
| 26 | **Confirmatory / descriptive membership** (the split itself) | Deterministic derivation | The total partition of §13.2 |
| 27 | Freeze timestamp (`created_at`-class field on the manifest) | Capture metadata | Recorded at freeze; never an equality invariant, per the frozen treatment of capture metadata (implementation design §5.I.2 pattern) |

**Every row resolves to a Stage-A field, an immutable eligibility-manifest field, a global frozen constant, or a deterministic derivation. No row requires an unregistered implementation choice.**

### 13.2 The confirmatory/descriptive partition is total — no Stage-C latitude

Implementation design §5.A Stage C says only `CONFIRMATORY_ELIGIBLE` strata may appear in the confirmatory matrix, and that "a descriptive-only stratum **may** remain in the broader reporting design." Read as latitude, that permissive "may" would leave a Stage-C choice — precisely the fourth category §3 forbids.

**[SCHEMA — FROZEN]** It is therefore frozen as a **total partition**, which is the only reading consistent with §3 and with Stage C freezing *both* "confirmatory position IDs" *and* "descriptive position IDs":

> Every element of `proposed_strata` lands in exactly one of `confirmatory_strata` (disposition `CONFIRMATORY_ELIGIBLE`) or `descriptive_only_strata` (any `DESCRIPTIVE_ONLY_*` disposition). Every element of `proposed_positions` lands in exactly one of `confirmatory_positions` or `descriptive_positions`, according to its own `(provider, model)` stratum's disposition. No proposed stratum or position is dropped, and none appears in both sets.

This adds no eligibility predicate, changes no disposition, and promotes nothing: it fixes only *where the already-decided dispositions send each already-proposed object*. The eligibility manifest's totality guarantee (implementation design §5.A Stage B and §6: "Refuse to finalize if any of the four predicates is missing a disposition for any proposed stratum") is what makes the partition total.

### 13.3 One noted representation matter, deliberately not opened

`matrix_digest` is named as a field of `registration_manifest.json` (implementation design §5.B.1, §5.B.3) but the frozen design does not enumerate its preimage. That is a **Stage-C** representation matter, outside this addendum's four-gap remit, and it is **not opened here**. It does not affect this section's conclusion: every input to `matrix_digest` is already a registered value (rows 5-13 and 15-17 above), so computing it requires **no unregistered choice of value** — only a preimage enumeration, which is a Stage-C schema question for the Work Unit that owns `freeze_final_registration`. Recording it here neither reopens it nor resolves it.

### 13.4 The `PASS` conclusion

No Stage-C registered value requires an unregistered implementation choice. Every quantity in §10 is classified into exactly one of §3's three categories. Every row of §13.1 traces to exactly one source. The upstream-open readiness tolerances of analysis contract §12.3 / §22 are not registered values and are not carried by any confirmatory artifact (§10.4), so they create no fourth category.

```
ALL_FINAL_REGISTRATION_VALUES_TRACEABLE: YES
REMAINING_STAGE_A_SCHEMA_CHOICES: NONE
```

---

## 14. Adversarial self-check

Each case resolves to exactly one deterministic outcome under §4-§13.

1. **Draft omits `randomization_mc_samples` entirely.** V9 fails; the draft is not written. Absence is never a valid encoding of "not proposed" (§8.1).
2. **Draft sets `randomization_mc_samples = 0`.** Not a positive integer, not `null`; V9 fails; not written.
3. **Draft sets `randomization_mc_samples = "10000"` (string).** Violates §5.B.2's integer rule as restated at §7.4; V9 fails; not written.
4. **Draft proposes `M`; final `K = 12`.** Exact mode. Final registration **refuses that draft** (§8.3); the registered value is neither discarded nor reinterpreted. A new `design_id` is required.
5. **Draft leaves `M = null`; final `K = 20`.** Monte Carlo mode. **FINAL REGISTRATION REFUSES TO FREEZE** (§8.3). Stage C does **not** select `M`. A new Stage-A draft under a new `design_id` must propose it.
6. **Draft leaves `M = null`; final `K = 12`.** Correct exact-mode draft; freeze proceeds. `randomization_mc_provenance.json` is generated in `EXACT_ENUMERATION` shape with **no** seed material and **no** `randomization_mc_samples` field (§8.5; implementation design §5.L.2).
7. **All strata are `DESCRIPTIVE_ONLY_*`, so `K = 0`.** `K` and `randomization_mode` still derive deterministically (`K ≤ 16 → EXACT_ENUMERATION`, `exact_support_size = 2^0 = 1`). No unregistered choice arises. Whether any inferential output exists is governed by the already-frozen estimability floor (analysis contract §9.8, C9), not by this schema.
8. **Someone adds `position_id` to `registration_draft.json`.** Violates §4.2's exact top-level set and §5.2; the draft is not written. `position_id` first exists at Stage C.
9. **Someone adds `baseline_label` to the `position_id` preimage.** Violates §5.1's exactly-six-fields rule; identity would then leak assignment-relevant structure and could not be registered before `b_k`. Rejected.
10. **Someone adds `registration_draft_digest` to the draft as an alias of `self_digest`.** Violates §4.2 and implementation design §5.B.1; not written.
11. **Stage C recomputes `_ordered_treatments` and finds a different label.** Forbidden by §6.3. `baseline_label` is copied, never recomputed. Any inequality between the retained manifest label and the draft label is a hard failure.
12. **A stratum becomes descriptive-only, and someone rebalances the surviving task's OFF/FULL counts.** Impossible and unnecessary: filtering removes whole `{"off","full"}` pairs, so balance is preserved by construction (§6.4). Any rebalancing act is a forbidden alteration of `S_k` (§6.3).
13. **Two positions in one `(task, provider, model, repetition)` group both carry `"off"`.** V7 fails; not written.
14. **A position's `provider_seed` disagrees with `proposed_provider_seeds` for its repetition.** V8 fails; not written.
15. **`baseline_label` written as `"OFF"` (Python attribute name) instead of `"off"`.** Violates §5.3's canonical serialized `QAMode` vocabulary ([OBSERVED] `types.py:22-24`, `runner.py:614`); V7/V9 fail; not written. No new label vocabulary is introduced anywhere.
16. **`baseline_label = "partial"`.** Outside the confirmatory OFF/FULL contrast on which `complement` is defined (implementation design §5.D); V7 fails; not written.
17. **A caller tries to propose `K` or `randomization_mode` in Stage A.** Violates §7.1's exact key set; V9 fails; not written. Both are class-C derivations only.
18. **A caller tries to propose a different `alpha`.** Violates §7.2's stamped literal; V9 fails; not written. `alpha` is frozen upstream at analysis contract §16.3 and is not caller-selectable.
19. **A caller reorders `secondary_endpoint_sequence`.** Violates §7.2's frozen order; V9 fails; not written. Family membership and order are frozen at analysis contract §16.1.
20. **A draft is edited in place after being written.** Forbidden by implementation design §5.A / §6; the edit either breaks `self_digest` verification (§12) or, if `self_digest` is recomputed, breaks every downstream `registration_draft_digest` reference.
21. **Someone reads the exact-mode draft's `randomization_mc_samples: null` and copies it into the exact-mode provenance artifact.** Forbidden: §5.L.2's absent-field rule is unchanged, and §8.5 states the non-copy explicitly.
22. **A reader receives semantically equivalent but noncanonical bytes that parse to the same authenticated object.** Not, by itself, a failure — §5.B.2's verification procedure is unchanged (§12).

---

## 15. Conflict check against the frozen contracts

Each rule this addendum freezes was checked against the frozen upstream text for direct contradiction.

| This addendum | Frozen text checked | Result |
|---|---|---|
| Top-level field set with no `registration_draft_digest` (§4.2) | Implementation design §5.B.1 field inventory | **Agrees verbatim** |
| Canonical JSON / `self_digest` unchanged (§4.4) | Implementation design §5.B.2 | **Restated, unamended** |
| Six-field identity payload (§5.1) | Implementation design §5.C | **Restated, unamended** |
| Seven-field `ProposedPositionV1` (§5.2) | Implementation design §5.A Stage A ("candidate fixed positions"), §5.C | **No conflict** — §5.C constrains the *identity payload* and the *execution-row contract*; it never states that the Stage-A record equals the identity payload |
| `baseline_label` vocabulary `"off"` / `"full"` (§5.3) | `src/iqa_soa/types.py:19-25`, `runner.py:614`; implementation design §5.D | **Agrees** — the existing canonical serialization is reused; none is invented |
| `S_k` bound at Stage A; Stage C may only filter (§6) | Implementation design §5.A Stage C ("baseline schedule" is frozen at Stage C), §5.D item 1 (`_ordered_treatments` unmodified); design decision §10 ("Positions … fixed at freeze, independent of eventual label") | **No conflict** — Stage C freezes the schedule it inherits; it is never said to compute it |
| `randomization_mc_samples` always present, `null` or positive integer (§8.1) | Implementation design §5.B.2 (integer-valued fields stay JSON integers); §5.L.2 (field absent in the exact-mode **provenance** artifact) | **No conflict** — §5.B.2 constrains the representation when a number is present; §5.L.2 governs a different artifact (§8.5) |
| `M` must be proposed at Stage A or the freeze is refused (§8.3) | Implementation design §17 ("`M` … if the registered `K > 16` and `M` is not yet chosen" — a **deferred value**, chosen by a separately authorized act); §5.L.3 ("the **registered** Monte Carlo sample count `M`"; analyzer verifies "`M` equals the **registered** `randomization_mc_samples`"); design decision §7.4.2 conditions E, F, G | **No conflict, and strictly stricter.** Every frozen sentence sources `M` from *registration*; none authorizes Stage C, the provenance generator, the assignment layer, or the analyzer to select it. Freezing it at Stage A satisfies E/F/G *a fortiori* (§8.4) |
| The freeze is refused on a mode/`M` mismatch (§8.3) | Implementation design §6, `ELIGIBILITY_FROZEN → FINAL_REGISTRATION_FROZEN` refusal cell; §5.A abandon-and-recreate rule | **No conflict** — §6 states a refusal condition, never an exhaustive prohibition on other fail-closed refusals; the remedy (a new `design_id`) is the one §5.A already freezes |
| `statistic_spec_id` stamped, not caller-selectable (§9) | Implementation design §5.K, §7 PR-8 | **Agrees verbatim** |
| `alpha = "0.05"` as a canonical decimal string (§7.2, §7.4) | Analysis contract §16.3; implementation design §5.B.2 decimal-string rule | **Agrees** |
| Fixed-sequence family membership and order (§7.2) | Analysis contract §6.2, §16.1 | **Agrees verbatim** |
| Total confirmatory/descriptive partition (§13.2) | Implementation design §5.A Stage C ("a descriptive-only stratum **may** remain"), §6 eligibility-totality refusal | **No conflict** — the permissive "may" is a reporting-scope remark, not a licence to drop a proposed object; totality is the only reading consistent with Stage C freezing descriptive position IDs |
| `RuntimeSnapshotV1` untouched (§11) | Implementation design §5.I | **Not reopened** |
| Reader canonicality unchanged (§12) | Implementation design §5.B.2 | **Restated, unamended** |

**No frozen sentence directly contradicts any rule frozen here.** `CLARIFICATION_BLOCKED_BY_FROZEN_CONTRACT` is therefore not returned.

---

## 16. Authorization boundary

This addendum is binding on repository engineering for the Stage-A artifact schema, and authorizes nothing beyond itself.

- **Code implementation** remains authorized exactly as PR #21 authorized it, under exactly the scope of `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md` §5. This document neither widens nor narrows that scope; it removes an ambiguity a Work Unit 1 implementer would otherwise have had to resolve unilaterally, which that record's §5 binding rule forbids ("A genuine impossibility must be reported and escalated as a separate design decision — never resolved unilaterally inside an implementation commit").
- **No experimental act** is authorized. No registration, no eligibility disposition, no assignment, no Monte Carlo seed, no execution, no candidate.
- **No file other than this document** is created or modified. No `src/` code is written, no test is written, no test is run.

---

## 17. Validation

Documentation-only, static. Performed for this record:

```
git diff --check      -> (empty)
git status --short    -> ?? docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md
git diff --name-only  -> (empty; the new file is untracked and unstaged)
```

No `pytest`. No analyzer, harness, probe, or validator invocation. No provider/model/Ollama call. No staging. No commit. No seed or randomization bit generated. `results/` was not read, written, reset, or staged.

---

## 18. DECISION

## **`REGISTRATION_DRAFT_SCHEMA_CLARIFICATION_DECISION: STAGE_A_SCHEMA_FROZEN`**

Justification: all four representation gaps found by Work Unit 1 are closed without reopening any frozen methodology, randomization design, or implementation architecture. (1) The Stage-A statistical-configuration JSON schema is frozen to an exact eleven-key set, of which exactly one key — `randomization_mc_samples` — is caller-proposed and every other is a stamped global constant traced to its frozen source (§7, §10). (2) `randomization_mc_samples` is always present, typed positive-integer-or-`null`, with `null` meaning "not prospectively proposed," and with a hard bidirectional Stage-C gate that refuses the freeze rather than ever selecting `M` after the draft (§8). (3) `baseline_label` is bound prospectively to every proposed physical position at Stage A, making the complete `(identity, baseline_label)` collection the frozen `S_k`; Stage C may filter by the immutable eligibility disposition and may do nothing else to it (§6). (4) The six `ConfirmatoryPositionV1` identity fields are exhaustive of the **identity payload** only; the Stage-A **record** is `ProposedPositionV1`, exactly those six plus `baseline_label`, with no `position_id` in the draft (§5). Every value `FINAL_REGISTRATION_FROZEN` freezes traces to a Stage-A field, an immutable eligibility-manifest field, a global frozen constant, or a deterministic derivation (§13). No fourth "choose later" category survives anywhere.

```
REGISTRATION_DRAFT_V1_TOP_LEVEL_SCHEMA_FROZEN: YES
PROPOSED_POSITION_SCHEMA_FROZEN: YES
POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES
BASELINE_SCHEDULE_BOUND_AT_STAGE_A: YES
STATISTICAL_CONFIGURATION_KEYSET_FROZEN: YES
M_NULLABILITY_AND_STAGE_C_GATE_FROZEN: YES
ALL_FINAL_REGISTRATION_VALUES_TRACEABLE: YES
REMAINING_STAGE_A_SCHEMA_CHOICES: NONE
```

```
THIS_DOCUMENT_IS_A_BINDING_IMPLEMENTATION_SCHEMA_ADDENDUM: YES

STATISTICAL_METHODOLOGY_CHANGED: NO
RANDOMIZATION_DESIGN_CHANGED: NO
IMPLEMENTATION_ARCHITECTURE_REOPENED_BEYOND_SCHEMA_GAP: NO

CODE_IMPLEMENTATION_AUTHORIZED_UNDER_EXISTING_PR21_DECISION: YES

ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
```

---

## Final report block

```
REGISTRATION_DRAFT_SCHEMA_CLARIFICATION_DECISION:
STAGE_A_SCHEMA_FROZEN

REGISTRATION_DRAFT_V1_TOP_LEVEL_SCHEMA_FROZEN: YES
PROPOSED_POSITION_SCHEMA_FROZEN: YES
POSITION_IDENTITY_PAYLOAD_REMAINS_SIX_FIELDS: YES
BASELINE_SCHEDULE_BOUND_AT_STAGE_A: YES
STATISTICAL_CONFIGURATION_KEYSET_FROZEN: YES
M_NULLABILITY_AND_STAGE_C_GATE_FROZEN: YES
ALL_FINAL_REGISTRATION_VALUES_TRACEABLE: YES
REMAINING_STAGE_A_SCHEMA_CHOICES: NONE

THIS_DOCUMENT_IS_A_BINDING_IMPLEMENTATION_SCHEMA_ADDENDUM: YES

STATISTICAL_METHODOLOGY_CHANGED: NO
RANDOMIZATION_DESIGN_CHANGED: NO
IMPLEMENTATION_ARCHITECTURE_REOPENED_BEYOND_SCHEMA_GAP: NO
RUNTIME_SNAPSHOT_V1_REOPENED: NO
CANONICAL_READER_RULE_CHANGED: NO

CODE_IMPLEMENTATION_AUTHORIZED_UNDER_EXISTING_PR21_DECISION: YES

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
NO TESTS RUN
NO FILES OTHER THAN docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md CREATED
NO EXISTING FILE MODIFIED
```
