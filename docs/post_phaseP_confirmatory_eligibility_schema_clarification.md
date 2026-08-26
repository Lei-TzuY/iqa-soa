# Post-Phase-P confirmatory `ELIGIBILITY_FROZEN` schema clarification

**Record kind:** binding implementation-schema addendum — cross-stage (Stage B schema + the minimum Stage-A runtime-cardinality repair Stage B requires to be well-defined)
**Status:** SCHEMA CLARIFICATION. Not a statistical-methodology redesign. Not a confirmatory-randomization redesign. Not code implementation.
**Date:** 2026-08-26
**Branch:** `post-phasep-confirmatory-eligibility-schema-clarification`
**Base commit:** `f9666b0` (`origin/main`) — verified ancestor of this branch's `HEAD`; includes `c60883c` (`REGISTRATION_DRAFT_SCHEMA_CLARIFICATION_DECISION: STAGE_A_SCHEMA_FROZEN`)
**Work Unit 1 inspected read-only:** `8110c009c4e15fd7d59c28da1c553396923b8ac8` (`feat: add confirmatory registration draft infrastructure`) — inspected with `git show` only. Not merged, not copied, not modified by this document.
**Subject:** the seven unfrozen-representation gaps `U1`-`U7` returned by `WORK_UNIT_2_SCHEMA_SUFFICIENCY: BLOCKED_BY_UNFROZEN_REPRESENTATION`

---

## 0. Boundary declaration

This document creates exactly one file — itself. It modifies no existing file. It writes no `src/`, no tests, runs no pytest, contacts no provider, model, or network, draws no randomness, stages nothing, and commits nothing.

**Frozen and NOT reopened by anything below:**

- the four eligibility predicates and their identities;
- predicate order;
- the first-failure disposition rule;
- the six disposition tokens;
- confirmatory / descriptive methodology;
- the canonical JSON profile and the `self_digest` algorithm (implementation design §5.B.2);
- the three-stage registration lifecycle and its ordering (implementation design §5.A, §6);
- randomization design;
- statistical analysis;
- provider eligibility methodology, and the `RuntimeSnapshotV1` two-layer contract (implementation design §5.I).

What this document does is strictly narrower: it fixes **representation** for the Stage-B artifact, and it repairs exactly one **cardinality** defect in the Stage-A nested runtime shape without which Stage B is not well-defined.

Throughout, unqualified section references are:

- **design decision** — `docs/post_phaseP_confirmatory_randomization_design_decision.md`
- **implementation design** — `docs/post_phaseP_confirmatory_randomization_implementation_design.md`
- **authorization** — `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md`
- **Stage-A clarification** — `docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md`

---

## 1. Why this document exists

Work Unit 2 (`src/iqa_soa/experiment/confirmatory_eligibility.py` + `tests/unit/test_confirmatory_eligibility.py`) stopped **before code** because the frozen stack does not uniquely determine `eligibility_manifest.json`. The schema-sufficiency review returned exactly seven gaps:

| # | Gap | Closed at |
|---|---|---|
| **U1** | `eligibility_manifest.json` top-level key set not frozen | §4 |
| **U2** | `schema_version` literal not frozen | §4.1 |
| **U3** | `created_at` versus `assessed_at` semantics/placement not frozen | §5 |
| **U4** | per-stratum eligibility-record shape and predicate-status vocabulary not frozen | §6, §7 |
| **U5** | evidence-reference representation/granularity not frozen | §9 |
| **U6** | `infrastructure_symmetry_audit` nested representation not frozen | §10 |
| **U7** | Stage A permits multiple `proposed_strata` but binds one `registration_expected_runtime_snapshot`; the stratum→runtime-identity mapping is not frozen | §12, §13 |

Every other Work Unit 2 input is already frozen and is referenced, never restated in a form that could drift.

---

## 2. Read-only forensics — the exact facts this document is built on

Each fact was read directly, either from the working tree or from commit `8110c00` via `git show`. Nothing below is inferred.

**F1 — Stage A binds exactly one runtime snapshot.** `git show 8110c00:src/iqa_soa/experiment/confirmatory_registration.py` defines

```
_RUNTIME_KEYS = frozenset({
    "registration_expected_runtime_snapshot",   # singular
    "retry_policy",
    "timeout_seconds",
})
```

and `ProposedRuntimeConfigurationV1` holds exactly one `RuntimeSnapshotV1` in the field `registration_expected_runtime_snapshot`.

**F2 — `RuntimeSnapshotV1` is provider/model-specific.** Its frozen field set (implementation design §5.I, realized verbatim in `_RUNTIME_SNAPSHOT_KEYS`) includes `provider_name`, `model`, and `endpoint`, and all three are inside the `runtime_identity_digest` preimage (§5.I.1). A single snapshot therefore *names one provider/model runtime*, not a family of them.

**F3 — `proposed_strata` may hold more than one stratum.** Stage-A clarification §4.3: "array of `ProposedStratumV1`, non-empty, sorted ascending by `(provider, model)`, unique." Nothing bounds it at one. Design decision §9 and §10 explicitly contemplate multiple declared strata, each carrying its own disposition.

**F4 — nothing binds F1 to F3.** `_validate_proposed_matrix` in `8110c00` enforces V3-V8 over `proposed_tasks`, `proposed_strata`, `proposed_repetitions`, `proposed_provider_seeds`, `proposed_positions`. It never receives `proposed_runtime_configuration`, and no other code path compares the snapshot's `(provider_name, model)` against any element of `proposed_strata`. The mapping does not merely lack a *cardinality*; it lacks an *existence check* even at cardinality one.

**F5 — the Stage-A clarification deliberately left this open.** Its §11 states: "It also makes no statement about the cardinality relationship between `proposed_strata` and runtime snapshots; that relationship is governed by §5.I and is not opened here." Implementation design §5.I, however, governs *one snapshot's own shape and comparison rules* and never speaks to how many snapshots a draft binds. The gap fell between two documents, each correctly deferring to the other.

**F6 — the eligibility unit is the provider/model stratum.** Design decision §9: "every proposed `model_stratum`/`provider_runtime` receives **exactly one** of the dispositions below." Implementation design §5.A Stage B: eligibility "evaluates every proposed provider/model/runtime stratum named in the draft against the four frozen predicates … and gives each proposed stratum exactly one frozen disposition."

**F7 — `position_id` does not exist at Stage B.** Stage-A clarification §5.2: "`position_id` first exists at Stage C." Implementation design §6: "`FINAL_REGISTRATION_FROZEN` is the **first** state in which the final confirmatory matrix exists," and `ELIGIBILITY_FROZEN` strictly precedes it.

**F8 — the two competing timestamp names.** Implementation design §12's audit catalog lists `eligibility_manifest.json`'s required fields as "§5.A Stage B fields, four predicates per stratum, `created_at`, `schema_version`, `self_digest`". Implementation design §7's PR-10 row lists, in its *Evidence* column, "per-stratum evidence refs, `assessed_at`, registration-expected `runtime_identity_digest`". No document places `assessed_at` in a schema enumeration.

**F9 — no conflicting frozen literal exists.** `grep` over `docs/*.md` finds no occurrence of `EligibilityManifestV1`, `eligibility_state`, or any other candidate Stage-B `schema_version` literal. The literal minted at §4.1 conflicts with nothing.

**F10 — the digest inventory is already frozen.** Implementation design §5.B.1: `eligibility_manifest.json` "stores: `registration_draft_digest` (= `registration_draft.json.self_digest`); stores: `self_digest`; does NOT store: `eligibility_manifest_digest`."

---

## 3. Conventions observed, and applied without exception below

**C1 — schema-version naming.** The repository's frozen literals are `RegistrationDraftV1`, `RuntimeSnapshotV1`, `ProposedStatisticalConfigurationV1`, `ConfirmatoryPositionV1`. Pattern: PascalCase noun phrase, `V1` suffix, no underscores. §4.1's literal follows it exactly.

**C2 — which nested objects carry `schema_version`.** In the entire Stage-A chain, exactly two nested objects carry one: `RuntimeSnapshotV1` (implementation design §5.I) and `ProposedStatisticalConfigurationV1` (Stage-A clarification §7.1). `ProposedStratumV1`, `ProposedPositionV1`, `ProposedRepetitionsEntryV1`, `ProposedProviderSeedEntryV1`, `RetryPolicyV1`, and `proposed_runtime_configuration` carry none. **Rule applied here:** a nested object carries `schema_version` if and only if already-frozen upstream text assigns it one. No nested type minted by this document receives one; the manifest's single top-level `schema_version` versions the whole `EligibilityManifestV1` payload including every nested shape.

**C3 — array ordering is either *sorted* or *semantic*, never "implementation may choose".** Sorted arrays (`proposed_tasks`, `proposed_strata`, `retryable_error_classes`) are ascending by an explicitly named key under ordinary Unicode code-point ordering, and are schema-level preconditions rejected rather than normalized (implementation design §5.B.2; Stage-A clarification §4.4). Semantic arrays (`secondary_endpoint_sequence`) are positional and carry a frozen order (Stage-A clarification §7.4). Every array below is declared as exactly one of the two.

**C4 — recorded derivations are cross-checked, never trusted.** Stage-A clarification §7.3: a value that is derivable is nevertheless *recorded* so a mismatch is detectable, and the loader recomputes and compares rather than assuming agreement. Applied below to `disposition` (§8) and to `INFRASTRUCTURE_SYMMETRY.status` (§10.4).

**C5 — no same-object digest alias, ever** (implementation design §5.B.1, F10).

**C6 — no field a loader cannot check.** Every field frozen below is checkable offline, from the manifest plus the bound draft, with no network access and no dereferencing of any locator.

---

## 4. `EligibilityManifestV1` — top-level schema frozen (closes U1, U2)

### 4.1 Artifact schema version literal — frozen

**[SCHEMA — FROZEN]** The Stage-B artifact's `schema_version` literal is exactly:

```
"EligibilityManifestV1"
```

Justified by C1 and F9: it matches the repository naming convention exactly, and no conflicting frozen literal exists anywhere in the frozen stack. There is no alternative literal and no version negotiation.

`ELIGIBILITY_SCHEMA_VERSION_FROZEN: YES.`

### 4.2 Lifecycle-state representation — frozen

**[SCHEMA — FROZEN]** The lifecycle state is carried by the field name

```
registration_state
```

with the literal value

```
"ELIGIBILITY_FROZEN"
```

**`eligibility_state` is retired and is not a field of this artifact, or of any artifact in this chain.** Reason: implementation design §6's state machine is *one* lifecycle over *one* registration, and the two sibling artifacts already carry that lifecycle under the field name `registration_state` — `registration_draft.json` with `"REGISTRATION_DRAFT"` (Stage-A clarification §4.2, realized as `REGISTRATION_STATE_DRAFT` in `8110c00`) and `registration_manifest.json` with `"FINAL_REGISTRATION_FROZEN"` (implementation design §5.A). Introducing a differently-named state field for the middle stage of the same lifecycle would make the three artifacts unreadable by one uniform check. The state token `ELIGIBILITY_FROZEN` is itself unchanged — it is implementation design §6's own state name, verbatim.

### 4.3 Top-level field set — exactly these eight fields, no more, no fewer

**[SCHEMA — FROZEN]** `eligibility_manifest.json` contains exactly:

```
schema_version
registration_state
confirmatory_profile
design_id
created_at
registration_draft_digest
eligibility_records
self_digest
```

**Exactly eight keys.** A persisted manifest with a ninth key, or missing any one of the eight, is malformed and is refused (§14 E1).

Frozen literal values:

```
schema_version        = "EligibilityManifestV1"                       (§4.1)
registration_state    = "ELIGIBILITY_FROZEN"                          (§4.2)
confirmatory_profile  = "post_phaseP_confirmatory_randomization_v1"   (implementation design §5.C)
```

### 4.4 Per-field type freeze

**[SCHEMA — FROZEN]**

| Field | JSON type | Content rule |
|---|---|---|
| `schema_version` | string | exactly `"EligibilityManifestV1"` |
| `registration_state` | string | exactly `"ELIGIBILITY_FROZEN"` |
| `confirmatory_profile` | string | exactly `"post_phaseP_confirmatory_randomization_v1"` |
| `design_id` | string | non-empty; byte-identical to the bound draft's `design_id`. **[DEFERRED VALUE SELECTION]** — no value is chosen here |
| `created_at` | string | RFC 3339 UTC instant, `Z` designator mandatory, whole-second precision, no fractional seconds, no non-`Z` offset: `YYYY-MM-DDTHH:MM:SSZ` (§5) |
| `registration_draft_digest` | string | lowercase 64-character hex SHA-256; equals `registration_draft.json`'s `self_digest` |
| `eligibility_records` | array of `EligibilityStratumRecordV1` | non-empty; sorted ascending by `(provider, model)`; unique on `(provider, model)`; an exact element-wise cover of the draft's `proposed_strata` (§6) |
| `self_digest` | string | lowercase 64-character hex SHA-256, computed per implementation design §5.B.2, unchanged |

### 4.5 Digest inventory — restated, unamended

```
eligibility_manifest.json:
    stores:        registration_draft_digest   (= registration_draft.json.self_digest)
    stores:        self_digest
    does NOT store: eligibility_manifest_digest
```

`eligibility_manifest_digest` is a **downstream-only** reference name, used by `registration_manifest.json` and `final_analysis_manifest.json` when pointing at this artifact's `self_digest` (implementation design §5.B.1, §5.B.3). It is never a same-object second field here, and a manifest carrying it is refused by the exact-key-set rule (§14 E1).

### 4.6 What the manifest deliberately does **not** carry

Named explicitly so no implementer supplies them:

- **No `confirmatory_strata` / `descriptive_only_strata` lists.** The confirmatory/descriptive partition is a Stage-C deterministic derivation over this manifest's dispositions (Stage-A clarification §13.1 rows 6-7, §13.2). Recording it here would create a second source of truth for a value Stage C must derive.
- **No `position_id`, and no per-position record of any kind** (F7, §9.4).
- **No `matrix_digest`, `final_registration_digest`, `assignment_digest`, or `randomization_mc_provenance_digest`.** All are downstream of Stage B and do not exist yet.
- **No execution-derived field** — no `observation_status`, `failure_class`, `qa_mode`, `baseline_label`, `task_assignment_bit`, `bits`, `b_k`, or endpoint value (§11).
- **No `assessed_at`** (§5).
- **No `eligibility_predicate_sequence` or channel-order constant.** The frozen predicate order and channel order are carried *in band*, positionally, by every record (§7.2, §10.2); a second copy could disagree with the first.

`ELIGIBILITY_MANIFEST_TOP_LEVEL_SCHEMA_FROZEN: YES.`

---

## 5. Timestamp semantics — frozen (closes U3)

**The ambiguity.** F8: the audit catalog says `created_at`; PR-10's evidence column says `assessed_at`. Neither document states whether there are one or two timestamps, or where a second would sit.

**[SCHEMA — FROZEN]** There is **exactly one timestamp in `eligibility_manifest.json`**: a single manifest-level field named

```
created_at
```

**There is no per-stratum assessment timestamp. There is no per-predicate timestamp. There is no per-channel timestamp. `assessed_at` is retired for this artifact and is not a field of it at any depth.**

**Representation** — identical to the Stage-A convention (Stage-A clarification §4.3), so one rule serves the whole artifact chain:

```
RFC 3339 UTC instant, mandatory Z designator, whole-second precision:
    YYYY-MM-DDTHH:MM:SSZ
    ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$
```

A non-UTC offset, a fractional-second component, or any other form is **refused**, never converted and never truncated — `created_at` is a digest-authenticated registered value, so silently rewriting what the caller supplied would register something they did not propose.

**Semantics.** `created_at` is the instant at which the eligibility assessment was **finalized and sealed** — the single moment the manifest became immutable. Because the manifest is written exactly once, atomically, and can never be edited, re-assessed, or versioned in place (§15), there is exactly one such instant per manifest, and it answers "when was this stratum assessed" for every stratum in it.

**Why `created_at` and not `assessed_at`.**

1. `created_at` is the name used by the only frozen text that *enumerates this artifact's fields* — implementation design §12's audit catalog. `assessed_at` appears solely in PR-10's *Evidence* column, which describes what the artifact must make auditable, not what its key set is.
2. `created_at` is already the artifact-chain convention (`registration_draft.json.created_at`, Stage-A clarification §4.3; §13.1 row 27 names the analogous final-registration field the "`created_at`-class field on the manifest"). One name, one grammar, one validator across three artifacts.
3. PR-10's audit obligation is satisfied extensionally: it requires a "recorded disposition log, timestamped before execution, showing which of the four predicates were checked and their individual pass/fail results". The manifest's per-predicate `status` values supply the *which and what*; the manifest-level `created_at` supplies the *when*; the state machine's ordering (implementation design §6) supplies *before execution*. Nothing in the obligation requires per-stratum timestamps.
4. A per-stratum timestamp would be an unverifiable free value that no invariant consumes, and would immediately raise questions this document would then have to answer with no frozen basis: must it precede `created_at`, must the array be sorted by it, may two strata share one. Adding validation surface with no consumer is the opposite of what closing a schema gap means.
5. There can never be two assessment instants that matter inside one manifest, because in-place reassessment is permanently forbidden (§15): a second assessment is a different `design_id` with a different manifest and a different `created_at`.

`RuntimeSnapshotV1.captured_at` is untouched: it is a field of `RuntimeSnapshotV1`, governed by implementation design §5.I.2 as capture metadata that is never an equality invariant, and it keeps its own frozen representation. It is not a Stage-B timestamp and is not renamed, re-grammared, or compared here.

`TIMESTAMP_SEMANTICS_FROZEN: YES.`

---

## 6. `EligibilityStratumRecordV1` — exact shape (closes U4, part 1)

### 6.1 The exact key set — six keys, no more, no fewer

**[SCHEMA — FROZEN]** Every element of `eligibility_records` contains exactly:

```
provider                        string, non-empty
model                           string, non-empty
predicates                      array of exactly 4 EligibilityPredicateRecordV1   (§7)
infrastructure_symmetry_audit   InfrastructureSymmetryAuditV1                     (§10)
runtime_identity_digest         string, lowercase 64-character hex                (§13)
disposition                     string, one of exactly six frozen tokens          (§8)
```

Per C2, the record carries no `schema_version`.

### 6.2 Provider/model representation — the existing Stage-A vocabulary, unchanged

**[SCHEMA — FROZEN]** The stratum is identified by exactly the two fields `provider` and `model`, with exactly the key names, types, and content rules `ProposedStratumV1` already uses (Stage-A clarification §4.3; `_STRATUM_KEYS = {"model", "provider"}` in `8110c00`). **No new stratum-identifier vocabulary is invented**, no composite `stratum_id` string is minted, and no digest of the pair is introduced. The eligibility unit is the provider/model stratum (F6), and it is named the way Stage A already names it.

Note the deliberate asymmetry with `RuntimeSnapshotV1`, which spells the same concept `provider_name`/`model` (implementation design §5.I). That naming is frozen inside the snapshot and is not changed; the stratum record uses the *stratum* vocabulary `provider`/`model` because that is what it is a record about. §12.3 freezes the exact join between the two spellings.

### 6.3 Ordering, uniqueness, coverage

**[SCHEMA — FROZEN]**

- **Ordering:** `eligibility_records` is a **sorted** array (C3), ascending by the tuple `(provider, model)` under ordinary Unicode code-point ordering — the identical key and ordering rule `proposed_strata` already uses.
- **Uniqueness:** unique on `(provider, model)`.
- **Coverage — exact, element-wise:** letting `D = registration_draft.json`,

```
len(eligibility_records) == len(D.proposed_strata)
and for every index i:
    eligibility_records[i].provider == D.proposed_strata[i].provider
    eligibility_records[i].model    == D.proposed_strata[i].model
```

Because both arrays are sorted ascending by the same key and are unique on it, element-wise positional equality is exactly the statement "same set, same order". Every proposed stratum therefore maps to **exactly one** eligibility record: **no missing, no duplicate, no extra, no foreign stratum.** A record for a `(provider, model)` not in `proposed_strata` is a foreign stratum and the manifest is refused (§14 E24).

This is what makes implementation design §6's transition refusal — "Refuse to finalize if any of the four predicates is missing a disposition for any proposed stratum" — a structurally checkable rule rather than a prose aspiration.

`PER_STRATUM_RECORD_SCHEMA_FROZEN: YES.`

---

## 7. The four predicate records (closes U4, part 2)

### 7.1 Representation choice — an ordered array, frozen

**[SCHEMA — FROZEN]** Predicate states are represented as **one ordered array of exact predicate records**, not as four named sibling fields.

The choice is made, not offered. Reasons: (a) the frozen disposition rule is defined over an *order* ("the **first** predicate that fails in the order above", design decision §9) — an array makes that order structural and machine-checkable rather than a convention a reader must remember; (b) each predicate carries a status *and* an evidence collection, so a four-named-fields shape would need four parallel sibling objects anyway, at which point the names duplicate the `predicate_id` values; (c) the same shape is used for the symmetry channels (§10), so one validation idiom covers both.

### 7.2 `EligibilityPredicateRecordV1` — three keys, no more, no fewer

**[SCHEMA — FROZEN]**

```
predicate_id     string, one of the four frozen predicate tokens
status           string, one of the three frozen status tokens          (§7.3)
evidence_refs    array of EvidenceReferenceV1                           (§9)
```

**`predicates` is a semantic array (C3), positional, not sorted.** It has exactly four elements and

```
predicates[0].predicate_id == "POSITION_STATE_ISOLATION"
predicates[1].predicate_id == "INFRASTRUCTURE_SYMMETRY"
predicates[2].predicate_id == "TOTAL_OBSERVATION"
predicates[3].predicate_id == "RUNTIME_CONFIGURATION_FROZEN"
```

exactly and always. This is design decision §9's frozen order, verbatim and unchanged. A missing, duplicated, reordered, or unknown `predicate_id` is refused (§14 E10). The four tokens are quoted from the frozen design; none is minted here.

### 7.3 Predicate-status vocabulary — exactly three tokens

**[SCHEMA — FROZEN]**

```
status ∈ { "PASS", "FAIL", "UNASSESSED" }
```

- `PASS` — the predicate was assessed and holds for this stratum.
- `FAIL` — the predicate was assessed and does not hold for this stratum.
- `UNASSESSED` — no assessment of this predicate has been performed for this stratum.

`UNASSESSED` is the stem of design decision §9's frozen `DESCRIPTIVE_ONLY_UNASSESSED`, so no new stem is introduced. There is no fourth token: no `SKIPPED`, no `NOT_APPLICABLE`, no `PENDING`, no `null`, and absence of the field is not an encoding of anything — it is malformed.

`UNASSESSED` is a **recorded** status, never a structurally missing one. Implementation design §6's "Refuse to finalize if any of the four predicates is missing a disposition" means *structurally absent*; a recorded `UNASSESSED` satisfies it, which is required, because design decision §9 makes `DESCRIPTIVE_ONLY_UNASSESSED` "the default disposition for every provider/runtime today".

`PREDICATE_STATUS_VOCABULARY_FROZEN: YES.`

### 7.4 Status combinations — no short-circuit constraint

**[SCHEMA — FROZEN]** The four statuses are **mutually unconstrained**. Every one of the `3⁴ = 81` combinations of `PASS` / `FAIL` / `UNASSESSED` over the four frozen positions is an admissible assessment record. In particular, and stated positively so no validator re-derives a stricter rule:

- **A recorded `FAIL` does not terminate the record.** Later predicates may carry `PASS`, `FAIL`, or `UNASSESSED` freely.
- **Multiple `FAIL` values are legal.** A stratum may fail two, three, or all four predicates, and each individual result is retained.
- **A `PASS` or `FAIL` may follow an `UNASSESSED`.** A predicate left unassessed does not invalidate a later predicate's recorded result.
- **The stored order is semantic, not chronological.** `predicates` is stored in the frozen order of §7.2 for disposition precedence and machine-checkability. **Assessment order is never inferred from storage order**, and no field records when any individual predicate was assessed (§5).

**Why the frozen upstream contract requires exactly this.** Design decision §9's disposition rule reads, verbatim: "never more than one `DESCRIPTIVE_ONLY_*` token (the **first** predicate that fails in the order above is recorded as the reason; **a configuration failing multiple predicates** is still `DESCRIPTIVE_ONLY_<reason>` for exactly one stated reason, not multiply classified)". The frozen text therefore *explicitly contemplates a configuration failing multiple predicates*, and constrains only the **disposition** to a single token — never the **record** to a single `FAIL`. "First" selects which failure supplies the reason; it does not license discarding the others, and it does not mandate short-circuit evaluation. No frozen text anywhere requires assessment to stop after a failure.

**Where the single-disposition guarantee comes from.** It is supplied entirely by the deterministic precedence of §8.2, which returns exactly one token for every one of the 81 combinations. No stratum can receive two dispositions, because §8.2 is a function. Constraining the *record* was never necessary to obtain that guarantee, and doing so would have destroyed recorded findings the frozen design expects to be kept.

**`UNASSESSED` semantics remain fail-closed and deterministic.** `UNASSESSED` means the predicate was not assessed. By §8.2, any record containing an `UNASSESSED` and no `FAIL` yields `DESCRIPTIVE_ONLY_UNASSESSED`; a record containing a `FAIL` yields that failure's reason regardless of how many `UNASSESSED` entries accompany it. `UNASSESSED` never contributes to eligibility, and no combination containing one can reach `CONFIRMATORY_ELIGIBLE` (§8.2 step 3).

All four `UNASSESSED` is the frozen default state of every provider/runtime today (design decision §9; implementation design §11) and remains legal, as it always was.

`FIRST_FAILURE_AND_UNASSESSED_RULE_FROZEN: YES.`

---

## 8. Disposition derivation — exact, total, and cross-checked

**The methodology is unchanged.** This section freezes only the deterministic function from recorded predicate states to a recorded token.

### 8.1 The disposition vocabulary — exactly six tokens

**[SCHEMA — FROZEN]**

```
disposition ∈ {
    "CONFIRMATORY_ELIGIBLE",
    "DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED",
    "DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY",
    "DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL",
    "DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN",
    "DESCRIPTIVE_ONLY_UNASSESSED"
}
```

Quoted verbatim from design decision §9. **`DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION` is explicitly NOT an admissible value of `disposition`.** It exists in implementation design §11's failure-token table, but it is an assignment/randomization-layer token (PR-1, PR-3, PR-6, PR-8), not one of the four eligibility predicates' failure tokens, and design decision §9's total rule enumerates exactly the six above. A manifest recording it is refused (§14 E19).

### 8.2 The derivation rule — three-step precedence, total over all 81 combinations

**[SCHEMA — FROZEN]** Exactly one rule, applied in exactly this order:

| Step | Condition | `disposition` |
|---|---|---|
| **1** | At least one predicate has `status == "FAIL"`. Take the **earliest such predicate in the frozen order of §7.2** and use its corresponding reason (table below). | the earliest failing predicate's `DESCRIPTIVE_ONLY_*` reason |
| **2** | No predicate has `status == "FAIL"`, **and** at least one has `status == "UNASSESSED"`. | `DESCRIPTIVE_ONLY_UNASSESSED` |
| **3** | Otherwise — all four have `status == "PASS"`. | `CONFIRMATORY_ELIGIBLE` |

The step-1 reason mapping, quoted unchanged from design decision §9:

| Earliest failing predicate | `disposition` |
|---|---|
| `predicates[0]` `POSITION_STATE_ISOLATION` | `DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED` |
| `predicates[1]` `INFRASTRUCTURE_SYMMETRY` | `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY` |
| `predicates[2]` `TOTAL_OBSERVATION` | `DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL` |
| `predicates[3]` `RUNTIME_CONFIGURATION_FROZEN` | `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` |

**`FAIL` outranks `UNASSESSED` at every position.** A record whose first predicate is `UNASSESSED` and whose second is `FAIL` yields `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY` — the discovered failure, not the weaker `DESCRIPTIVE_ONLY_UNASSESSED`. A *discovered* defect is never buried behind an *un-looked-at* one. Step 1's "earliest" ranges over failing predicates only; unassessed positions do not consume precedence.

**Totality and single-valuedness.** The three steps are mutually exclusive and jointly exhaustive over all `3⁴ = 81` status combinations: step 1 fires iff the set of `FAIL` positions is non-empty, and its `min` is then unique; step 2 fires iff that set is empty and some position is `UNASSESSED`; step 3 fires iff neither. **Every combination receives exactly one disposition — never zero, never two.** No stratum can be multiply classified, which is precisely design decision §9's requirement, delivered by the derivation rather than by constraining what may be recorded (§7.4).

Mechanical completeness proof over the 81 combinations, by disposition:

| `disposition` | Combinations | Count |
|---|---|---|
| `DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED` | `s_0 = FAIL`; `s_1, s_2, s_3` free | `3³ = 27` |
| `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY` | `s_0 ∈ {PASS, UNASSESSED}`, `s_1 = FAIL`; `s_2, s_3` free | `2·3² = 18` |
| `DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL` | `s_0, s_1 ∈ {PASS, UNASSESSED}`, `s_2 = FAIL`; `s_3` free | `2²·3 = 12` |
| `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` | `s_0, s_1, s_2 ∈ {PASS, UNASSESSED}`, `s_3 = FAIL` | `2³ = 8` |
| `DESCRIPTIVE_ONLY_UNASSESSED` | no `FAIL`, at least one `UNASSESSED` | `2⁴ − 1 = 15` |
| `CONFIRMATORY_ELIGIBLE` | all four `PASS` | `1` |
| **Total** | | **`27 + 18 + 12 + 8 + 15 + 1 = 81`** |

The partition sums to exactly 81 with no overlap and no remainder — the derivation is total, and no combination anywhere has an undefined or ambiguous disposition.

`CONFIRMATORY_ELIGIBLE` requires all four `PASS` and nothing weaker — the conjunction design decision §9 already froze. It is unreachable from any combination containing a `FAIL` or an `UNASSESSED`, as the table's single-count row shows.

### 8.3 `disposition` is recorded **and** recomputed

**[SCHEMA — FROZEN]** `disposition` is a stored field (Stage C reads it directly, implementation design §5.A) **and** the loader recomputes it from `predicates` by §8.2 and refuses any manifest where the stored and recomputed values differ (§14 E19). This is C4's already-frozen pattern — record the derivation so a mismatch is detectable rather than silently assumed — applied here, not a new idea.

---

## 9. Evidence references — exact representation (closes U5)

### 9.1 `EvidenceReferenceV1` — three keys, no more, no fewer

**[SCHEMA — FROZEN]** Evidence references are **exact structured records**, never bare strings. A bare string would leave "what kind of thing is this string" open — a path, a URL, a digest, free prose — which is precisely the class of open choice this document exists to remove.

```
evidence_kind     string, one of exactly three frozen kinds
locator           string, non-empty, grammar fixed per kind
content_digest    string, lowercase 64-character hex SHA-256
```

There is no `note`, `summary`, `author`, or `assessed_at` field: every field of this record is checkable offline (C6), and free prose is not.

### 9.2 `evidence_kind` — exactly three kinds, each with one locator grammar

**[SCHEMA — FROZEN]**

| `evidence_kind` | `locator` grammar | `content_digest` is |
|---|---|---|
| `"REPOSITORY_PATH"` | a repository-relative POSIX path: `^(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`, with no segment equal to `.` or `..`, no leading `/`, no empty segment, no backslash | SHA-256 over the referenced file's bytes exactly as committed |
| `"DESIGN_ARTIFACT_FIELD"` | `registration_draft.json#<json_pointer>`, where `<json_pointer>` is an RFC 6901 pointer with at least one segment: `^registration_draft\.json#(?:/[^/]*)+$` | the referenced artifact's `self_digest` — and therefore **must equal this manifest's `registration_draft_digest`** |
| `"EXTERNAL_ATTESTATION"` | an absolute HTTPS URL: `^https://[^\s]+$` | SHA-256 over the bytes retrieved at assessment time |

`REPOSITORY_PATH` covers everything committed: the offline design reviews PR-4 and PR-5 require, PR-7's prospective observability argument, code-inspection notes, probe transcripts. `DESIGN_ARTIFACT_FIELD` covers the case where the registered draft itself *is* the evidence — most importantly the registration-expected runtime identity for `RUNTIME_CONFIGURATION_FROZEN`. `EXTERNAL_ATTESTATION` covers a provider's published infrastructure statement.

`registration_draft.json` is the **only** admissible artifact filename in a `DESIGN_ARTIFACT_FIELD` locator: at Stage B it is the only artifact of the chain that exists besides the manifest being written (implementation design §6). A reference to `registration_manifest.json`, `assignment_manifest.json`, or any other downstream artifact names something that does not yet exist and is refused (§14 E14).

**No loader ever dereferences a locator.** Validation is purely structural and offline: `evidence_kind` is in the vocabulary, `locator` matches that kind's grammar, `content_digest` is 64 lowercase hex, and — for `DESIGN_ARTIFACT_FIELD` only — `content_digest` equals `registration_draft_digest`. No file is opened, no URL is fetched, no digest is recomputed from remote bytes. This keeps Stage-B validation deterministic, offline, and reproducible forever, including after an external URL has rotted.

### 9.3 Cardinality, ordering, and empty/non-empty semantics — frozen

**[SCHEMA — FROZEN]** `evidence_refs` is always present and always an array (never `null`, never absent). It is a **sorted** array (C3), ascending by the tuple `(evidence_kind, locator, content_digest)` under ordinary Unicode code-point ordering, and unique on that tuple. Out-of-order or duplicated entries are refused, never re-sorted or deduplicated on the caller's behalf.

Its cardinality is fixed by the status it accompanies — this is the answer to "empty/non-empty semantics", and it is exhaustive:

**On a predicate record (§7.2):**

| `predicate_id` | `status` | required `evidence_refs` |
|---|---|---|
| `POSITION_STATE_ISOLATION`, `TOTAL_OBSERVATION`, `RUNTIME_CONFIGURATION_FROZEN` | `PASS` or `FAIL` | length ≥ 1 |
| `POSITION_STATE_ISOLATION`, `TOTAL_OBSERVATION`, `RUNTIME_CONFIGURATION_FROZEN` | `UNASSESSED` | exactly `[]` |
| `INFRASTRUCTURE_SYMMETRY` | any status | exactly `[]` — **always** (§9.5) |

**On a symmetry channel record (§10.3):**

| `check_status` | required `evidence_refs` |
|---|---|
| `CHECKED` | length ≥ 1 |
| `NOT_CHECKED` | exactly `[]` |

A recorded `PASS`/`FAIL` or `CHECKED` with no evidence is an unsupported assertion and is refused; a recorded `UNASSESSED` or `NOT_CHECKED` carrying evidence contradicts its own status and is refused. No upper bound on length is imposed — that would be inventing a scientific evidence requirement, which is outside this document's remit.

### 9.4 PR-4's "`isolation_evidence` per position" — the only consistent interpretation

Implementation design §7's PR-4 row names, in its *Evidence* column, "`isolation_evidence` per position", while eligibility is provider/model-stratum scoped (F6). These are reconciled, not both adopted.

**[SCHEMA — FROZEN] "Per position" is evidence-*generation* granularity, not manifest-*membership* granularity.**

This is the only interpretation consistent with the frozen design, for three independent reasons:

1. **No position identity exists at Stage B.** `position_id` first exists at Stage C (F7). A per-position record inside `eligibility_manifest.json` would have to reference positions that have no identities yet.
2. **Binding eligibility to positions would invert the frozen lifecycle.** `ELIGIBILITY_FROZEN` strictly precedes `FINAL_REGISTRATION_FROZEN`, which is "the **first** state in which the final confirmatory matrix exists" (implementation design §6). Per-position eligibility would make the Stage-B artifact depend on the matrix its own output is required to determine.
3. **The frozen eligibility unit is the stratum**, receiving "exactly one" disposition (design decision §9), and only `CONFIRMATORY_ELIGIBLE` *strata* may enter the confirmatory matrix (implementation design §5.A Stage C).

**[SCHEMA — FROZEN] How the Stage-B stratum record references that evidence.** The position-granular isolation argument — the `ProviderFactory.create_for_position(position)` contract of implementation design §5.E, under which every registered physical position mandatorily receives a fresh local provider/session/sandbox/tool context — is **aggregated into the stratum's `POSITION_STATE_ISOLATION` predicate record** and referenced there through ordinary `EvidenceReferenceV1` entries in its `evidence_refs`, exactly as in §9.1-§9.3. There is **no** `isolation_evidence` field, at any depth, in `eligibility_manifest.json`; the name is not part of this schema.

The predicate holds for the stratum if and only if the isolation argument holds for **every** position that stratum could contribute — which is precisely the structural, once-per-stratum argument §5.E already makes, since the freshness guarantee is a property of the provider factory contract for that provider/model runtime, not of any individual position. **The predicate's meaning is unchanged; only its representation is frozen.**

### 9.5 Where evidence attaches — per predicate, per channel, never both for one fact

**[SCHEMA — FROZEN]** Evidence attaches in exactly two places, with a clean partition and no overlap:

- **Per predicate**, for `POSITION_STATE_ISOLATION`, `TOTAL_OBSERVATION`, and `RUNTIME_CONFIGURATION_FROZEN`.
- **Per audit channel**, for `INFRASTRUCTURE_SYMMETRY`, whose evidence is carried **in full and exclusively** by `infrastructure_symmetry_audit.channels[*].evidence_refs`. Its predicate-level `evidence_refs` is therefore **always exactly `[]`**, in every status.

The exclusivity is deliberate. Implementation design §5.F already requires a per-channel evidence reference; if the predicate level also carried evidence, the same facts would live in two places and could disagree, and an implementer would have to choose which one to write. One fact, one location, no choice.

`EVIDENCE_REFERENCE_SCHEMA_FROZEN: YES.`

---

## 10. `infrastructure_symmetry_audit` — exact nested schema (closes U6)

### 10.1 `InfrastructureSymmetryAuditV1` — one key

**[SCHEMA — FROZEN]** `infrastructure_symmetry_audit` is an **object** with exactly one key:

```
channels    array of exactly 4 InfrastructureSymmetryChannelV1
```

It remains an object, not a bare array, because implementation design §5.F freezes it as "an `infrastructure_symmetry_audit` **record** … listing each candidate channel". Per C2 it carries no `schema_version`.

### 10.2 The four channel tokens — minted here, stable

Implementation design §5.F enumerates four candidate leak paths in prose with no machine tokens. `grep` confirms no token for any of them exists anywhere in the frozen stack, so exactly four are minted, once, here:

**[SCHEMA — FROZEN]**

| # | §5.F candidate channel | `channel_id` |
|---|---|---|
| 1 | prompt/system-message content | `"PROMPT_SYSTEM_MESSAGE_CONTENT"` |
| 2 | gateway-path latency signature | `"GATEWAY_PATH_LATENCY_SIGNATURE"` |
| 3 | evidence volume | `"EVIDENCE_VOLUME"` |
| 4 | provider/model selection | `"PROVIDER_MODEL_SELECTION"` |

**`channels` is a semantic array (C3), positional, not sorted**, carrying exactly four elements in exactly the §5.F enumeration order:

```
channels[0].channel_id == "PROMPT_SYSTEM_MESSAGE_CONTENT"
channels[1].channel_id == "GATEWAY_PATH_LATENCY_SIGNATURE"
channels[2].channel_id == "EVIDENCE_VOLUME"
channels[3].channel_id == "PROVIDER_MODEL_SELECTION"
```

**No channel may be absent, duplicated, reordered, or unknown**, and no fifth channel may be added — implementation design §5.F froze the candidate set at exactly these four. Violations are refused (§14 E15).

### 10.3 `InfrastructureSymmetryChannelV1` — four keys, no more, no fewer

**[SCHEMA — FROZEN]**

```
channel_id         string, the frozen token for this positional index
check_status       string ∈ { "CHECKED", "NOT_CHECKED" }
symmetry_result    string ∈ { "NO_ASYMMETRY_FOUND", "ASYMMETRY_FOUND", "SYMMETRY_NOT_ASSESSED" }
evidence_refs      array of EvidenceReferenceV1                              (§9.3)
```

`CHECKED` / `NOT_CHECKED` are implementation design §5.F's own tokens, kept verbatim in their own field. `symmetry_result` is the separate field that supplies the distinction §5.F also requires but never named — **checked-and-no-asymmetry versus checked-and-asymmetry-found**. Two fields rather than one collapsed three-token field, so that §5.F's frozen `CHECKED`/`NOT_CHECKED` vocabulary survives literally rather than being absorbed into new compound tokens.

`SYMMETRY_NOT_ASSESSED` is deliberately distinct from the predicate-status token `UNASSESSED` (§7.3): the two vocabularies live in different fields, and a distinct spelling means any token identifies its own field unambiguously.

**Coherence rule — frozen, refused rather than repaired:**

| `check_status` | required `symmetry_result` | required `evidence_refs` |
|---|---|---|
| `"CHECKED"` | `"NO_ASYMMETRY_FOUND"` or `"ASYMMETRY_FOUND"` | length ≥ 1 |
| `"NOT_CHECKED"` | `"SYMMETRY_NOT_ASSESSED"` | exactly `[]` |

A `CHECKED` channel without a symmetry result — i.e. carrying `SYMMETRY_NOT_ASSESSED` — is refused (§14 E16), as is a `NOT_CHECKED` channel claiming a result. There is no `null` and no absent field in either direction.

### 10.4 `INFRASTRUCTURE_SYMMETRY.status` is derived from `channels`, and cross-checked

**[SCHEMA — FROZEN]** `predicates[1].status` is a deterministic function of the four channel records:

```
if any channel has symmetry_result == "ASYMMETRY_FOUND":      FAIL
elif all four channels have check_status == "CHECKED":        PASS
else:                                                          UNASSESSED
```

Total over every channel configuration admitted by §10.3, with no undefined case. Note that the second branch, reached only when no channel found an asymmetry, is exactly implementation design §5.F's frozen rule: "`INFRASTRUCTURE_SYMMETRY` may only `PASS` when every channel is `CHECKED` with no asymmetry found." A partially-audited stratum that has found nothing wrong yet is `UNASSESSED`, never `PASS` — it can never reach `CONFIRMATORY_ELIGIBLE`.

Per C4 the value is both **recorded** in `predicates[1].status` and **recomputed** by the loader, which refuses any manifest where the two differ (§14 E17). The recorded status must additionally be one of the three frozen tokens of §7.3. No positional or ordering constraint applies to it — §7.4 imposes none on any predicate — so a derived `FAIL` here is legal whatever the other three predicates record.

`INFRASTRUCTURE_SYMMETRY_AUDIT_SCHEMA_FROZEN: YES.`

---

## 11. `TOTAL_OBSERVATION` — prospective only

**[SCHEMA — FROZEN]** `TOTAL_OBSERVATION` is represented by exactly one ordinary `EligibilityPredicateRecordV1` at `predicates[2]`, with the §7.3 status vocabulary and the §9.3 evidence rule, and nothing else. Its `status` records whether the **prospective** total-observation argument passes, fails, or is unassessed; its `evidence_refs` reference the offline observability design argument PR-7 requires ("Offline observability design argument per provider/runtime, prior to execution", design decision §12 PR-7).

It remains prospective. Explicitly, and refused by §14 E1/E8/E21 if attempted:

- **no execution-row field** may appear anywhere in `eligibility_manifest.json` — no `observation_status`, no `failure_class`, no `position_id`, no endpoint value, no row count;
- **no realized endpoint is inspected** at Stage B, and none exists to inspect (implementation design §6: execution begins four states later);
- **the later analyzer is not designed here.** `src/iqa_soa/metrics/confirmatory.py`, its fourteen-point row checklist (implementation design §5.C), and the realized fail-closed observation gate (§5.G, §5.H) are untouched by this document and are the subject of their own work unit.

The prospective/realized distinction is design decision §9's, unchanged: PR-7 as an *eligibility predicate* is "the prospective observability condition … not a realized-data check", while `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` remains the separate realized-data outcome emitted much later.

---

## 12. Runtime cardinality — resolved (closes U7)

This is the cross-stage defect. Stage B cannot be well-defined without it: `RUNTIME_CONFIGURATION_FROZEN` is a **per-stratum** predicate (design decision §9, F6) that must be evaluated against a **per-stratum** registration-expected runtime identity, and Stage A currently binds one runtime identity for the whole draft (F1, F2, F3, F4).

### 12.1 The defect, stated exactly

- `proposed_strata` is a non-empty array of `(provider, model)` pairs with no upper bound (F3).
- `proposed_runtime_configuration.registration_expected_runtime_snapshot` is exactly one `RuntimeSnapshotV1` (F1), which names one `provider_name`, one `model`, one `endpoint`, all inside its `runtime_identity_digest` preimage (F2).
- For `len(proposed_strata) > 1` there is **no defined mapping** from a stratum to a runtime identity, so `RUNTIME_CONFIGURATION_FROZEN` has nothing well-defined to be evaluated against for any stratum but (at most) one.
- For `len(proposed_strata) == 1` there is not even an existence check: no code path compares the snapshot's `(provider_name, model)` to the single stratum (F4), so a draft may bind a runtime identity for a provider/model it never proposed.

### 12.2 Repair options evaluated against the frozen design

| Repair | Description | Verdict |
|---|---|---|
| **R0 — none** | Leave the mapping undefined | **REJECTED.** Stage B is then not well-defined; Work Unit 2 stays blocked, which is the condition this document exists to lift. |
| **R1 — restrict confirmatory designs to one proposed stratum** | Require `len(proposed_strata) == 1` | **REJECTED.** No upstream frozen rule requires it, and the frozen design explicitly contemplates multiple provider/model strata: design decision §10 registers "Providers / models — Declared strata, each carrying a `CONFIRMATORY_ELIGIBLE` / `DESCRIPTIVE_ONLY_<reason>` disposition"; §9's disposition rules are stated per-stratum; Stage-A clarification §13.2 partitions `proposed_strata` into two possibly-non-empty sets. Restricting to one stratum would be a methodology change, which is out of scope and forbidden. |
| **R2 — create runtime identity at Stage B or later** | Capture a snapshot per stratum during eligibility | **REJECTED.** Runtime/config values are required to be *proposed and frozen before* eligibility: implementation design §5.I.5 capture point 1 is "captured **before** eligibility/final registration and bound into the proposed runtime configuration". Stage B evaluates against an already-registered expected identity; it never mints one. |
| **R3 — derive per-stratum identity from the one snapshot** | Overwrite `provider_name`/`model` per stratum, rehash | **REJECTED.** `runtime_identity_digest` is frozen as SHA-256 over exactly the §5.I.1 invariant field set of an **actually captured** snapshot. Synthesizing snapshots that were never captured would fabricate registered evidence, and the remaining fields (`endpoint`, `provider_config_digest`, `provider_parameters_digest`, `environment_fingerprint`) are genuinely provider-specific and cannot be carried across strata. |
| **R4 — per-stratum runtime-configuration collection** | `proposed_runtime_configuration` binds exactly one complete `RuntimeSnapshotV1` per proposed stratum, exactly covering `proposed_strata` | **ADOPTED.** §12.3. |

R4 is the *minimum* repair: it changes one nested field's shape, introduces no new record type, amends no methodology, leaves `RuntimeSnapshotV1` byte-identical, and preserves the `RegistrationDraftV1` top-level thirteen-key set unchanged.

### 12.3 The Stage-A amendment — frozen, minimal

**[SCHEMA — FROZEN — AMENDS STAGE A]** `proposed_runtime_configuration` remains the top-level key of `registration_draft.json`, remains a JSON **object**, and remains the eleventh of the frozen thirteen keys. Its nested shape becomes exactly one key:

```
proposed_runtime_configuration : object, exactly one key

    registration_expected_runtime_snapshots
        array of RuntimeSnapshotV1
```

**Rules on `registration_expected_runtime_snapshots`:**

| # | Rule |
|---|---|
| **RC-1** | Non-empty. |
| **RC-2** | Every element is a complete `RuntimeSnapshotV1` with exactly the twenty frozen fields of implementation design §5.I, whose `runtime_identity_digest` (§5.I.1) and `self_digest` (§5.B.2) both verify. **`RuntimeSnapshotV1` itself is not amended in any way.** |
| **RC-3** | **Sorted** array (C3): ascending by the tuple `(provider_name, model)` under ordinary Unicode code-point ordering. |
| **RC-4** | Unique on `(provider_name, model)`. |
| **RC-5** | **Exact element-wise cover of `proposed_strata`:** `len(registration_expected_runtime_snapshots) == len(proposed_strata)`, and for every index `i`, `registration_expected_runtime_snapshots[i].provider_name == proposed_strata[i].provider` **and** `registration_expected_runtime_snapshots[i].model == proposed_strata[i].model`. |

Because `proposed_strata` is itself sorted ascending by `(provider, model)` and unique (Stage-A clarification §4.3), RC-3 + RC-4 + RC-5 together mean exactly: **every proposed stratum has exactly one registration-expected runtime snapshot; no stratum is unbound; no snapshot is foreign; no stratum is bound twice.** The two arrays are index-aligned, which is also what makes `eligibility_records` a third parallel array (§6.3, §13.1).

RC-5 is also the join between the two spellings of the same concept: the stratum vocabulary `(provider, model)` and the snapshot vocabulary `(provider_name, model)` (§6.2). Neither field is renamed; the equality above is the whole of the mapping.

**`runtime_identity_digest` derivation is unchanged.** It is derived inside each `RuntimeSnapshotV1` per implementation design §5.I.1 — SHA-256, §5.B.2 canonicalization, lowercase hex, over exactly the seventeen invariant fields, excluding `runtime_identity_digest`, `captured_at`, and `self_digest` — and is never free-standing caller input. The registration-expected runtime identity **for stratum `(p, m)`** is, by definition, the `runtime_identity_digest` of the unique snapshot with `provider_name == p` and `model == m`.

### 12.4 Retired: the configuration-level `timeout_seconds` and `retry_policy`

**[SCHEMA — FROZEN — AMENDS STAGE A]** The keys `timeout_seconds` and `retry_policy` are removed from `proposed_runtime_configuration`. It has exactly one key (§12.3).

**No registered value is lost.** Both survive verbatim, per stratum, inside each `RuntimeSnapshotV1`, where implementation design §5.I already freezes them as required snapshot fields, §5.I.4 freezes their representation (canonical decimal string; the five-key `retry_policy` object), and §5.I.1 includes both in the `runtime_identity_digest` preimage. They remain registered, digest-authenticated, and immutable. This is de-duplication, not removal.

Their removal is *necessary*, not merely tidy: as configuration-level scalars they carry an implicit claim that one timeout and one retry policy govern the whole draft. Under a per-stratum collection that claim is false in general — heterogeneous provider runtimes legitimately carry different timeouts — and forcing them equal across strata would be a methodology change this document is not authorized to make. The Work Unit 1 equality check they existed to support (`proposed_runtime_configuration.timeout_seconds` must equal the snapshot's) becomes vacuous once each stratum's values live in exactly one place.

### 12.5 `schema_version` literals — unchanged, with the reason stated

**[SCHEMA — FROZEN]**

- `registration_draft.json`'s `schema_version` stays exactly `"RegistrationDraftV1"` (Stage-A clarification §4.1).
- No `schema_version` is added to `proposed_runtime_configuration` (C2; and none was there before).
- The Python class name `ProposedRuntimeConfigurationV1` is unchanged. It is not a persisted literal — `_RUNTIME_KEYS` contains no `schema_version` — so renaming it would widen the patch surface with no artifact-visible effect.

The literal is kept rather than bumped because a `schema_version` exists to disambiguate **persisted bytes**, and no `registration_draft.json` has ever been written: the `design_id` value is `[DEFERRED VALUE SELECTION]` (implementation design §17), no real registration exists, and every Work Unit 1 test constructs synthetic drafts in `tmp_path`. There is therefore no artifact anywhere whose interpretation could change under the amendment, and nothing to version around. Detection is exact regardless: the amended `_RUNTIME_KEYS` rejects the old three-key nested shape outright as having unknown and missing keys, so an old-shape draft cannot load silently — it fails closed.

**Were any real draft ever to have been persisted, this amendment would instead require a `RegistrationDraftV2` literal.** Recorded here so the reasoning is auditable rather than assumed.

### 12.6 Superseded clauses — stated exactly

The following clauses of the Stage-A schema clarification are **superseded, for `proposed_runtime_configuration` only**:

| Clause | Text superseded | Replacement |
|---|---|---|
| **§4.3, `proposed_runtime_configuration` row** | "the complete registration-expected `RuntimeSnapshotV1` (implementation design §5.I), bound as already implemented under Work Unit 1" | "an object with exactly one key, `registration_expected_runtime_snapshots`: the complete registration-expected `RuntimeSnapshotV1` **for every proposed stratum**, sorted, unique, and an exact element-wise cover of `proposed_strata` (§12.3 RC-1…RC-5)". The field's top-level JSON type (`object`) and its position in the thirteen-key set are unchanged. |
| **§4.5, V10** | "`proposed_runtime_configuration` is a complete `RuntimeSnapshotV1` whose `runtime_identity_digest` and `self_digest` both verify per implementation design §5.I and §5.B.2." | **V10′:** "`proposed_runtime_configuration` has exactly the key `registration_expected_runtime_snapshots`. That array satisfies RC-1…RC-5 of §12.3: non-empty; every element a complete `RuntimeSnapshotV1` whose `runtime_identity_digest` and `self_digest` both verify per implementation design §5.I and §5.B.2; sorted ascending by `(provider_name, model)`; unique on that key; and an exact element-wise cover of `proposed_strata`." |
| **§11, final paragraph, second sentence** | "It also makes no statement about the cardinality relationship between `proposed_strata` and runtime snapshots; that relationship is governed by §5.I and is not opened here." | **Superseded.** The cardinality relationship is frozen at §12.3 RC-5. The deferral was to implementation design §5.I, but §5.I governs one snapshot's own shape and comparison rules and never spoke to how many snapshots a draft binds (F5) — which is exactly why the gap survived both documents. |
| **§13.1, row 21** | "Registration-expected `RuntimeSnapshotV1` and its `runtime_identity_digest` — `proposed_runtime_configuration` (§4.3, V10)" | "Registration-expected `RuntimeSnapshotV1` **and its `runtime_identity_digest`, one per proposed stratum** — `proposed_runtime_configuration.registration_expected_runtime_snapshots` (§12.3, V10′)". Its source class is unchanged: Stage-A field plus deterministic digest. |

**Explicitly NOT superseded, and unchanged in every respect:**

- Stage-A clarification §4.1 (`"RegistrationDraftV1"`), §4.2 (the thirteen top-level keys), §4.4 (canonical JSON / `self_digest`), §4.5 V1-V9 and V11, §5 (position record and identity payload), §6 (`S_k` binding), §7 (`ProposedStatisticalConfigurationV1`, eleven keys), §8 (`randomization_mc_samples` and the Stage-C gate), §9, §10, §12, §13.2, §13.3.
- Implementation design §5.I in its entirety — §5.I, §5.I.1, §5.I.2, §5.I.3, §5.I.4, §5.I.5, §5.I.6. `RuntimeSnapshotV1`'s field set, its identity payload, `EnvironmentIdentityV1`, the timeout/retry representation, the three capture points, and the failure tokens are all untouched. **No other Stage-A field is modified by this document.**

`RUNTIME_CARDINALITY_RESOLVED: YES.`

---

## 13. Runtime eligibility binding — frozen

### 13.1 What the eligibility record stores, and where it comes from

**[SCHEMA — FROZEN]** Each `EligibilityStratumRecordV1` stores `runtime_identity_digest`: a lowercase 64-character hex string, **copied verbatim** from the bound draft. For the record at index `i`:

```
eligibility_records[i].runtime_identity_digest
    == registration_draft.json
         .proposed_runtime_configuration
         .registration_expected_runtime_snapshots[i]
         .runtime_identity_digest
```

The index is meaningful because §12.3 RC-3/RC-5 and §6.3 make the three arrays — `proposed_strata`, `registration_expected_runtime_snapshots`, and `eligibility_records` — element-wise aligned by `(provider, model)`. Equivalently and identically: the digest is that of the unique registration-expected snapshot whose `(provider_name, model)` equals this record's `(provider, model)`.

It is **copied, never recomputed, and never recaptured.** Stage B does not construct a `RuntimeSnapshotV1`, does not hash one, and does not read a live runtime.

### 13.2 No live runtime recapture at Stage B

**[SCHEMA — FROZEN]** No live runtime capture occurs at Stage B in this work unit. Capture point 1 (`registration_expected_runtime_snapshot`) already happened, at Stage A. Capture points 2 and 3 (`pre_execution_runtime_snapshot`, `analysis_runtime_snapshot`, implementation design §5.I.5) belong to execution and analysis, states that do not exist yet. Eligibility evaluates **prospective evidence against the already-registered expected identity**, and nothing else.

### 13.3 Equality rule and mismatch consequence

**[SCHEMA — FROZEN]** The equality rule is exact byte-for-byte string equality of the two 64-hex values named in §13.1. There is no partial match, no prefix comparison, and no normalization.

Two distinct failure situations exist, and they have deliberately different consequences:

1. **Copy mismatch — an integrity failure.** The manifest's stored `runtime_identity_digest` does not equal the bound draft's value for that stratum. The **whole manifest is refused** (§14 E25); no disposition is produced for any stratum. This is not an eligibility finding: it means the manifest was assembled against a different runtime binding than the draft its own `registration_draft_digest` names, which is a corruption of the artifact chain, and silently downgrading a corrupt manifest to `DESCRIPTIVE_ONLY_*` would let a broken chain produce a usable-looking record.

2. **Assessment failure — an eligibility finding.** The assessor determines that the runtime/model/configuration cannot be held fixed for the confirmatory execution window, or discovers a runtime-identity problem during assessment. This is recorded as `predicates[3].status = "FAIL"` with supporting evidence, yielding `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` by §8.2 — exactly implementation design §5.I.6's frozen pre-freeze token, unchanged.

**A runtime identity mismatch, or an inability to defend runtime freeze, can never produce `CONFIRMATORY_ELIGIBLE`.** Proof, exhaustive over the schema: `CONFIRMATORY_ELIGIBLE` requires all four `PASS` (§8.2), so it requires `predicates[3].status == "PASS"`, which by §9.3 requires at least one evidence reference. Case 1 refuses the manifest before any disposition is derived. Case 2 sets that status to `FAIL`. An assessor who simply cannot defend runtime freeze — no argument, no evidence — cannot record `PASS`, because `PASS` with `evidence_refs == []` is refused (§14 E13); the only legal record is `UNASSESSED` with empty evidence, giving `DESCRIPTIVE_ONLY_UNASSESSED`. There is no fourth path.

`PER_STRATUM_RUNTIME_BINDING_FROZEN: YES.`

---

## 14. Fail-closed validation contract

**[SCHEMA — FROZEN]** A loader applies the rules below **in the numbered order** and aborts on the **first** failure. There is **no normalization, no repair, no sorting on the caller's behalf, no deduplication, no default-filling, no warning-only path, and no partial acceptance.** A manifest that fails any rule is not a valid `EligibilityManifestV1` and no consumer proceeds with it.

Failures are raised as `ConfirmatoryEligibilityError`, a `ValueError` subclass — named by direct analogy with the module-scoped `ConfirmatoryRegistrationError` observed in `8110c00`, so the implementer mints no new error taxonomy.

### 14.1 Tier 1 — checkable from the manifest alone

| # | Rule |
|---|---|
| **E1** | Top-level object has exactly the eight keys of §4.3 — no missing key, no extra key. (This is what structurally forbids `eligibility_manifest_digest`, `assessed_at`, and every other retired or foreign name from ever loading.) |
| **E2** | `schema_version` equals `"EligibilityManifestV1"`. |
| **E3** | `registration_state` equals `"ELIGIBILITY_FROZEN"`. |
| **E4** | `confirmatory_profile` equals `"post_phaseP_confirmatory_randomization_v1"`. |
| **E5** | `design_id` is a non-empty string. |
| **E6** | `created_at` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` exactly (§5). |
| **E7** | `registration_draft_digest` matches `^[0-9a-f]{64}$`. |
| **E8** | `eligibility_records` is a non-empty array; every element is an object with exactly the six keys of §6.1. |
| **E9** | Every record's `provider` and `model` are non-empty strings; the array is sorted ascending by `(provider, model)` and unique on it (§6.3). |
| **E10** | Every record's `predicates` is an array of exactly four elements, and `predicates[i].predicate_id` equals the `i`-th frozen predicate token, positionally, for `i = 0,1,2,3` (§7.2). |
| **E11** | Every predicate record is an object with exactly the three keys of §7.2; `status` is one of `PASS`, `FAIL`, `UNASSESSED`. |
| **E12** | Every record's four statuses are independently admissible: **all `3⁴` combinations of the §7.3 tokens are legal (§7.4)**. The loader MUST NOT reject a record because it carries more than one `FAIL`, because a `PASS`/`FAIL` follows a `FAIL`, or because a `PASS`/`FAIL` follows an `UNASSESSED`. Status legality is constrained only by E11 (vocabulary), E13 (evidence coherence), E17 (symmetry derivation), and E19 (disposition derivation). |
| **E13** | Every predicate record satisfies the evidence-attachment rule of §9.3 — including `INFRASTRUCTURE_SYMMETRY.evidence_refs == []` in every status (§9.5). |
| **E14** | Every `EvidenceReferenceV1` is an object with exactly the three keys of §9.1; `evidence_kind` is one of the three frozen kinds; `locator` matches that kind's frozen grammar (§9.2); `content_digest` matches `^[0-9a-f]{64}$`; for `DESIGN_ARTIFACT_FIELD`, `content_digest` equals the manifest's `registration_draft_digest`. Every `evidence_refs` array is sorted ascending by `(evidence_kind, locator, content_digest)` and unique on that tuple. |
| **E15** | Every record's `infrastructure_symmetry_audit` is an object with exactly the one key `channels`; `channels` is an array of exactly four elements; `channels[i].channel_id` equals the `i`-th frozen channel token, positionally (§10.2). |
| **E16** | Every channel record is an object with exactly the four keys of §10.3; `check_status` and `symmetry_result` are in their frozen vocabularies; the coherence rule holds — a `CHECKED` channel carries a real symmetry result and ≥ 1 evidence reference, a `NOT_CHECKED` channel carries `SYMMETRY_NOT_ASSESSED` and exactly `[]`. |
| **E17** | Every record's recorded `predicates[1].status` equals the value derived from its `channels` by §10.4. |
| **E18** | Every record's `runtime_identity_digest` matches `^[0-9a-f]{64}$`. |
| **E19** | Every record's `disposition` is one of the six frozen tokens of §8.1 — and in particular is **not** `DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION` — and equals the value derived from its `predicates` by §8.2. |
| **E20** | `self_digest` matches `^[0-9a-f]{64}$` and verifies per implementation design §5.B.2's unchanged verification procedure (§16). |
| **E21** | No JSON object key anywhere in the artifact, at any depth, is one of the forbidden names of §14.3. |

### 14.2 Tier 2 — requires the bound `registration_draft.json`

A manifest may be *parsed* standalone, but it is never *accepted* — and never consumed by Stage C — without the bound draft. These rules run only after every Tier-1 rule has passed.

| # | Rule |
|---|---|
| **E22** | The bound `registration_draft.json` loads and its own `self_digest` verifies per §5.B.2; the manifest's `registration_draft_digest` equals that verified `self_digest`. |
| **E23** | The manifest's `design_id` equals the draft's `design_id`, byte-for-byte, and the manifest's `confirmatory_profile` equals the draft's. |
| **E24** | `eligibility_records` is an exact element-wise cover of the draft's `proposed_strata` per §6.3 — equal lengths and index-wise `(provider, model)` equality. This is the single rule that rejects a missing, duplicate, or foreign stratum record. |
| **E25** | For every index `i`, `eligibility_records[i].runtime_identity_digest` equals `draft.proposed_runtime_configuration.registration_expected_runtime_snapshots[i].runtime_identity_digest` (§13.1). |
| **E26** | The draft's `registration_state` equals `"REGISTRATION_DRAFT"` — the manifest is bound to a Stage-A artifact, not to some other stage's. |

### 14.3 Forbidden key names

**[SCHEMA — FROZEN]** No JSON object key at any depth of `eligibility_manifest.json` may be any of:

```
assessed_at                  (retired; §5)
eligibility_manifest_digest  (same-object alias; §4.5)
isolation_evidence           (not part of this schema; §9.4)
position_id                  (Stage C only; F7)
baseline_label  qa_mode  task_assignment_bit  bits  b_k     (assignment material)
observation_status  failure_class                            (execution rows; §11)
matrix_digest  final_registration_digest  assignment_digest
randomization_mc_provenance_digest                           (downstream artifacts)
confirmatory_strata  descriptive_only_strata  descriptive_positions
                                                             (Stage-C derivations; §4.6)
```

This is a **key-name** prohibition, not a raw-substring search: it is exactly checkable and cannot false-positive on a legitimate `locator` string that happens to contain one of these words. E1, E8, E11, E14, E15, and E16 already make every one of them structurally impossible by exhausting the key set at every depth; E21 restates the prohibition so an auditor can check it directly.

### 14.4 The complete rejection inventory

Each item the fail-closed contract requires a loader to reject deterministically, mapped to the rule that rejects it:

| Rejected condition | Rule |
|---|---|
| malformed top-level shape | E1 |
| wrong schema / state / profile / design id | E2, E3, E4, E5, E23 |
| wrong `registration_draft_digest` | E7, E22 |
| missing / extra / duplicate stratum record | E8, E9, E24 |
| illegal predicate token or status | E10, E11 |
| incoherent predicate ordering (`predicate_id` positions) | E10 |
| illegal disposition | E19 |
| disposition inconsistent with predicate states | E19 |
| malformed evidence refs | E13, E14 |
| incomplete / duplicate / unknown infrastructure audit channel | E15 |
| checked channel without a symmetry result | E16 |
| symmetry predicate status inconsistent with its channels | E17 |
| runtime mapping mismatch | E18, E25 |
| malformed timestamp | E6 |
| malformed `self_digest` | E20 |
| `self_digest` mismatch | E20 |
| manifest bound to a non-draft upstream artifact | E26 |

**One rule in this contract forbids a rejection rather than requiring one.** E12 is stated negatively on purpose: a status combination is never itself a rejection ground. A loader that refuses `PASS FAIL FAIL PASS`, or any other multi-`FAIL` or non-short-circuit record, is **non-conformant** — the single-disposition guarantee comes from §8.2's precedence, never from narrowing what may be recorded (§7.4). Every genuine rejection ground is in the table above.

`FAIL_CLOSED_VALIDATION_SCHEMA_COMPLETE: YES.`

---

## 15. Immutability and reassessment — restated, unchanged

Restated in substance from implementation design §5.A, §6, and §12; **not reopened, not amended, not softened.**

`eligibility_manifest.json` is **immutable once finalized**. There is no overwrite, no in-place reassessment, no versioning in place, and no post-freeze promotion of any stratum's disposition — not before assignment, not after assignment, not after execution, not after analysis, not for any reason, ever.

Any reassessment requires **abandon-and-recreate under a new `design_id`**: the entire registration triple (`registration_draft.json`, `eligibility_manifest.json`, `registration_manifest.json`) is abandoned as a unit and a new triple is created under a new `design_id`. The abandoned artifacts are retained for audit and never reused.

A stratum whose disposition is any `DESCRIPTIVE_ONLY_*` token — including `DESCRIPTIVE_ONLY_UNASSESSED` — can never later enter the confirmatory matrix of this `design_id`. Only `CONFIRMATORY_ELIGIBLE` strata may (implementation design §5.A Stage C).

Nothing in this section is opened by this document.

---

## 16. Canonical JSON and digest — unchanged

**The canonical algorithm is not modified.** Implementation design §5.B.2 applies to `eligibility_manifest.json` exactly as written, and is restated here only for the avoidance of doubt:

- Canonical bytes are `json.dumps(object_without_self_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` encoded UTF-8.
- Object keys sorted by ordinary Unicode code-point ordering via `sort_keys=True`; objects use string keys only.
- Arrays preserve registered order; the sorting and uniqueness rules of §4.4, §6.3, §9.3, §12.3 are **schema-level preconditions applied before canonicalization**, never canonicalization-time transformations.
- `NaN` / `Infinity` / `-Infinity` forbidden. This manifest contains **no** JSON numbers at all — every field frozen above is a string, an array, or an object — so the canonical-decimal-string rule has no subject here and no numeric representation choice arises.
- `self_digest` is SHA-256, lowercase hex, over the canonical bytes of the object with **only** `self_digest` removed.
- The persisted file is the canonical JSON *including* the computed `self_digest`, reserialized under the identical algorithm, plus exactly one trailing LF that is not part of any digest; a reader strips at most one trailing `\n` first.
- Verification: read bytes → strip at most one trailing LF → parse → extract claimed `self_digest` → remove it → recanonicalize → recompute SHA-256 → compare. Mismatch fails closed.

**Reader semantic recanonicalization is unchanged, and no byte-for-byte input canonicality gate is added.** A semantically equivalent noncanonical input that parses to the same authenticated object is not, by itself, a failure condition — exactly as Stage-A clarification §12 already froze. This document adds no reader-side canonicality check and no new failure token.

---

## 17. Complete artifact skeleton

Shape illustration only, over invented placeholders. **No real provider, model, task, design id, digest, or eligibility decision appears here or anywhere in this document.** Keys are shown in canonical sorted order; `<64-hex>` marks a lowercase 64-character hex digest.

```json
{
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "created_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "design_id": "<deferred value selection>",
  "eligibility_records": [
    {
      "disposition": "DESCRIPTIVE_ONLY_UNASSESSED",
      "infrastructure_symmetry_audit": {
        "channels": [
          {
            "channel_id": "PROMPT_SYSTEM_MESSAGE_CONTENT",
            "check_status": "NOT_CHECKED",
            "evidence_refs": [],
            "symmetry_result": "SYMMETRY_NOT_ASSESSED"
          },
          {
            "channel_id": "GATEWAY_PATH_LATENCY_SIGNATURE",
            "check_status": "NOT_CHECKED",
            "evidence_refs": [],
            "symmetry_result": "SYMMETRY_NOT_ASSESSED"
          },
          {
            "channel_id": "EVIDENCE_VOLUME",
            "check_status": "NOT_CHECKED",
            "evidence_refs": [],
            "symmetry_result": "SYMMETRY_NOT_ASSESSED"
          },
          {
            "channel_id": "PROVIDER_MODEL_SELECTION",
            "check_status": "NOT_CHECKED",
            "evidence_refs": [],
            "symmetry_result": "SYMMETRY_NOT_ASSESSED"
          }
        ]
      },
      "model": "<proposed model, deferred>",
      "predicates": [
        {
          "evidence_refs": [
            {
              "content_digest": "<64-hex>",
              "evidence_kind": "REPOSITORY_PATH",
              "locator": "<repo-relative path to the offline isolation review>"
            }
          ],
          "predicate_id": "POSITION_STATE_ISOLATION",
          "status": "PASS"
        },
        {
          "evidence_refs": [],
          "predicate_id": "INFRASTRUCTURE_SYMMETRY",
          "status": "UNASSESSED"
        },
        {
          "evidence_refs": [],
          "predicate_id": "TOTAL_OBSERVATION",
          "status": "UNASSESSED"
        },
        {
          "evidence_refs": [],
          "predicate_id": "RUNTIME_CONFIGURATION_FROZEN",
          "status": "UNASSESSED"
        }
      ],
      "provider": "<proposed provider, deferred>",
      "runtime_identity_digest": "<64-hex, copied from the draft>"
    }
  ],
  "registration_draft_digest": "<64-hex>",
  "registration_state": "ELIGIBILITY_FROZEN",
  "schema_version": "EligibilityManifestV1",
  "self_digest": "<64-hex>"
}
```

The record shown carries statuses `PASS UNASSESSED UNASSESSED UNASSESSED` — admissible by §7.4, and since it holds no `FAIL` but at least one `UNASSESSED`, §8.2 step 2 gives `DESCRIPTIVE_ONLY_UNASSESSED`, with `predicates[1].status == "UNASSESSED"` correctly derived from four `NOT_CHECKED` channels by §10.4. It illustrates the schema; it decides nothing.

And the amended Stage-A nested shape (§12.3), for the same one-stratum illustration:

```json
"proposed_runtime_configuration": {
  "registration_expected_runtime_snapshots": [
    { "...": "one complete unmodified RuntimeSnapshotV1 per proposed stratum, sorted by (provider_name, model)" }
  ]
}
```

---

## 18. Implementation impact table

**[FUTURE CODE — NOT WRITTEN HERE]** Precise classification of every code surface this document affects. No file below is created or modified by this document.

| Surface | Class | Exact impact |
|---|---|---|
| `src/iqa_soa/experiment/confirmatory_eligibility.py` | **NEW — Work Unit 2** | Owns `EligibilityManifestV1` and every nested type frozen at §4-§13, the §8.2 disposition derivation, the §10.4 symmetry derivation, the §14 fail-closed loader, `ConfirmatoryEligibilityError`, and immutable persistence/load reusing the unchanged §5.B.2 canonical/digest procedure. Already authorized (authorization §5.1). |
| `tests/unit/test_confirmatory_eligibility.py` | **NEW — Work Unit 2** | Frozen assertions from implementation design §10 (`test_total_disposition_over_four_predicates`, `test_first_failing_predicate_is_reported_reason`, `test_default_disposition_is_unassessed`, `test_confirmatory_eligible_requires_all_four_pass`, `test_eligibility_manifest_immutable_after_finalize`, `test_no_reassessment_after_final_freeze_raises`), plus coverage of every §14 rule E1-E26, the §8.2 precedence over representative combinations — including multi-`FAIL` records such as `PASS FAIL FAIL PASS`, a `FAIL` following an `UNASSESSED`, and the all-`UNASSESSED` default — together with an explicit test that no admissible status combination is rejected (§7.4, E12), the four channel tokens and the coherence rule (§10.3), and the three evidence kinds and their grammars (§9.2). Already authorized (authorization §5.3). |
| `src/iqa_soa/experiment/confirmatory_registration.py` | **PATCH REQUIRED — narrow** | §18.1 |
| `tests/unit/test_confirmatory_registration.py` | **PATCH REQUIRED — narrow** | §18.2 |

```
WORK_UNIT_1_RUNTIME_CARDINALITY_PATCH_REQUIRED: YES
```

### 18.1 The only affected Work Unit 1 source surfaces

Exactly five, all inside `src/iqa_soa/experiment/confirmatory_registration.py`:

| Symbol (as committed at `8110c00`) | Required change |
|---|---|
| `_RUNTIME_KEYS` | Becomes `frozenset({"registration_expected_runtime_snapshots"})` — one key, plural (§12.3, §12.4). |
| `ProposedRuntimeConfigurationV1` | Field set becomes the single `registration_expected_runtime_snapshots: tuple[RuntimeSnapshotV1, ...]`; the `timeout_seconds` and `retry_policy` fields are removed (§12.4). `__post_init__` validates RC-1, RC-2 (delegated to each `RuntimeSnapshotV1.__post_init__`, unchanged), RC-3, RC-4; the two former snapshot-equality checks are removed as vacuous. `to_dict` emits the one key. |
| `ProposedRuntimeConfigurationV1.registration_expected_runtime_identity_digest` | Property becomes a method taking `(provider, model)` and returning that stratum's `runtime_identity_digest`, raising `ConfirmatoryRegistrationError` for an unbound stratum. Name unchanged. |
| `_runtime_from_mapping` | Parses the one-key shape and builds the snapshot tuple via the **unchanged** `_runtime_snapshot_from_mapping`. |
| **new** `_validate_stratum_runtime_cover(proposed_strata, proposed_runtime_configuration)` | Enforces RC-5, the cross-check that needs both objects. Called from exactly two sites: `draft_registration`, immediately after `_validate_proposed_matrix`; and `_draft_from_artifact`, immediately after `_runtime_from_mapping`. A separate helper rather than a new parameter on `_validate_proposed_matrix`, because on the load path the runtime object is parsed *after* that call and reordering existing checks is a wider change than the repair needs. |

`draft_registration`'s signature is unchanged: it still takes `proposed_runtime_configuration: ProposedRuntimeConfigurationV1`. `RegistrationDraft`, its `canonical_payload`, `to_artifact`, `write_registration_draft`, `load_registration_draft`, `registration_draft_path`, and `__all__` are unchanged.

### 18.2 The only affected Work Unit 1 test surfaces

This inventory is **exhaustive**: every symbol in `tests/unit/test_confirmatory_registration.py` at `8110c00` that reads, constructs, or asserts on `proposed_runtime_configuration` is listed. Impacts are of exactly two kinds — **repathed** (the assertion's meaning is unchanged; only the access path moves into the snapshot collection) and **superseded** (the assertion tested an equality between a configuration-level scalar and the snapshot, and that equality ceases to exist because the scalar does, §12.4).

| Test symbol (as committed at `8110c00`) | Kind | Required change |
|---|---|---|
| `_synthetic_runtime` | fixture | Builds the one-key collection from a tuple of snapshots. Its `timeout_seconds` and `retry_policy` keyword parameters are **removed** — there is no configuration-level value left for a caller to vary, which is exactly why the two tests below are superseded rather than repathed. |
| `test_synthetic_draft_construction_succeeds` | repathed | Its two runtime assertions become `draft.proposed_runtime_configuration.registration_expected_runtime_snapshots[0].timeout_seconds == "30.5"` and `…[0].retry_policy.max_attempts == 1`. Every other assertion in the test — schema version, registration state, profile, `design_id`, `created_at`, statistical configuration, position count, `verify_self_digest` — is **unchanged**. |
| `test_integer_schema_fields_stay_json_integers` | repathed | Its final three assertions read `persisted["proposed_runtime_configuration"]["registration_expected_runtime_snapshots"][0]["retry_policy"]` and `…[0]["timeout_seconds"]`. The discipline being asserted — `max_attempts` a JSON integer, `initial_delay_seconds` and `timeout_seconds` canonical decimal **strings** — is **unchanged**, because §5.I.4 is not amended (§12.6). Its `proposed_repetitions`, `proposed_provider_seeds`, and `proposed_positions` assertions are untouched. |
| `test_registration_expected_runtime_snapshot_is_bound_in_full` | repathed | Asserts against `to_dict()["registration_expected_runtime_snapshots"][0]`. The twenty-field `RuntimeSnapshotV1` key-set assertion inside it is **unchanged** — §5.I is not amended. |
| `test_load_rejects_snapshot_content_mismatched_to_its_identity_digest` | repathed | Same assertion; the mutation path becomes `…["registration_expected_runtime_snapshots"][0]["endpoint"]`. |
| `test_digest_valid_direct_runtime_bypass_cannot_create_a_file` | repathed | Same assertion; forged object rebuilt in the amended shape. |
| `test_proposed_timeout_must_match_registration_expected_snapshot` | **superseded** | The old assertion — `_synthetic_runtime(timeout_seconds="31")` raises on disagreement with the snapshot — is **retired**, because the configuration-level `timeout_seconds` it varied no longer exists (§12.4) and the equality check it exercised is vacuous. **Replacement obligation:** assert that `timeout_seconds` is present, non-empty, and a canonical decimal string on **every** element of `registration_expected_runtime_snapshots`, and that a draft carrying a configuration-level `timeout_seconds` key fails to load under the amended one-key check (§12.5). |
| `test_proposed_retry_policy_must_match_registration_expected_snapshot` | **superseded** | The old assertion — `_synthetic_runtime(retry_policy=other)` raises on disagreement — is **retired**, for the identical reason. **Replacement obligation:** assert that `retry_policy` is present on **every** element of `registration_expected_runtime_snapshots` and satisfies the unchanged five-key `RetryPolicyV1` schema of §5.I.4, and that a draft carrying a configuration-level `retry_policy` key fails to load. |
| **new tests** | added | Multi-stratum cover (RC-5 satisfied for `len(proposed_strata) > 1`); missing snapshot for a proposed stratum rejected; foreign snapshot for an unproposed stratum rejected; duplicate `(provider_name, model)` rejected; unsorted collection rejected, not re-sorted; per-stratum `runtime_identity_digest` lookup returns the right stratum's digest; the old three-key nested shape fails to load. |

**The two superseded assertions lose no coverage of a real invariant.** They existed to stop a caller pairing one proposed configuration with an unrelated runtime identity. Under the amendment that pairing is unrepresentable: each stratum's `timeout_seconds` and `retry_policy` live in exactly one place, inside its own `RuntimeSnapshotV1`, already bound into its `runtime_identity_digest` preimage (§5.I.1). The invariant is now structural rather than checked, which is why the replacement obligations assert *presence and schema validity per snapshot* rather than *cross-field agreement*.

### 18.3 What is explicitly NOT reopened in Work Unit 1

**The entire Work Unit 1 commit outside §18.1 and §18.2 remains accepted.** Specifically unaffected and not re-litigated: the canonical JSON profile helpers (`canonical_json_bytes`, `compute_self_digest`, `attach_self_digest`, `verify_self_digest`, `serialize_artifact`, `parse_artifact`); the whole digest chain; `ProposedStratumV1`, `ProposedRepetitionsEntryV1`, `ProposedProviderSeedEntryV1`, `ProposedPositionV1` and the six-field identity payload; `RetryPolicyV1`; `RuntimeSnapshotV1` in every respect; `ProposedStatisticalConfigurationV1` and its eleven keys and stamped literals; `_validate_proposed_matrix`'s V3-V8 logic; `_DRAFT_KEYS` and the thirteen top-level keys; `design_id` path safety; the `created_at` timestamp helpers; write/load/immutability behavior; and every test not named in §18.2.

**This is a nested-shape cardinality repair on one field, not a reopening of Work Unit 1.** No statistical, baseline, canonical, digest, or path functionality is touched.

The independent closure review's findings on the runtime repair are recorded here unchanged, and nothing in this document's revision alters the surface they were made about — the source patch is **not** expanded beyond the already-frozen runtime-cardinality surface of §18.1:

```
PER_STRATUM_RUNTIME_REPAIR: PASS
MINIMUM_CROSS_STAGE_CHANGE: PASS
RUNTIME_OUTER_FIELD_REMOVAL: PASS
NO_RUNTIME_POLICY_SEMANTIC_CHANGE: PASS
```

`NO_RUNTIME_POLICY_SEMANTIC_CHANGE` is what the two superseded tests above turn on: removing the configuration-level `timeout_seconds` and `retry_policy` removes a **duplicate location**, never a policy value or a policy meaning (§12.4).

---

## 19. Adversarial self-check

Every case resolves to exactly one deterministic outcome under §4-§16.

1. **Manifest omits `created_at`.** E1 fails — eight keys exactly. Refused. Absence encodes nothing.
2. **Manifest carries both `created_at` and `assessed_at`.** E1 fails (ninth key); E21 restates it. Refused.
3. **`created_at` written as `2026-08-26T12:00:00+00:00`.** E6 fails: the `Z` designator is mandatory, and the value is not converted on the caller's behalf. Refused.
4. **`created_at` written with fractional seconds.** E6 fails; never truncated. Refused.
5. **Manifest carries `eligibility_manifest_digest` as a copy of its own `self_digest`.** E1 fails; implementation design §5.B.1 agrees. Refused.
6. **`registration_state` written as `"eligibility_frozen"`.** E3 fails — exact literal. Refused.
7. **A record uses `stratum_id: "provider/model"` instead of two fields.** E8 fails — the six-key set is exact and no composite identifier exists (§6.2). Refused.
8. **`eligibility_records` sorted by `model` then `provider`.** E9 fails — the ordering key is `(provider, model)`, and the array is not re-sorted. Refused.
9. **A proposed stratum has no eligibility record.** E24 fails (length mismatch). Refused. This is implementation design §6's "refuse to finalize if any of the four predicates is missing a disposition for any proposed stratum", made structural.
10. **Two records for the same `(provider, model)`.** E9 (uniqueness) fails, and E24 would too. Refused.
11. **A record for a `(provider, model)` absent from `proposed_strata`.** E24 fails — a foreign stratum. Refused.
12. **`predicates` holds three elements.** E10 fails — exactly four, positionally. Refused.
13. **`predicates` holds all four tokens in alphabetical order.** E10 fails — the array is semantic and positional, in design decision §9's frozen order (§7.2). Refused; never re-sorted.
14. **Status recorded as `"pass"` (lowercase).** E11 fails — exact tokens. Refused.
15. **Status recorded as `null`, or the `status` key omitted.** E11 / E8 fail. Neither is an encoding of `UNASSESSED` (§7.3). Refused.
16. **`PASS FAIL FAIL PASS`.** **Legal** — multiple `FAIL` values are admissible and each individual result is retained (§7.4). Assessment continued past the first failure, which the frozen contract permits. §8.2 step 1 takes the earliest `FAIL`, at index 1, giving `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY` — one disposition, not two. The same holds for `PASS FAIL FAIL UNASSESSED` and every other multi-failure combination.
17. **`PASS FAIL PASS UNASSESSED`.** **Legal** — a `PASS` may follow a `FAIL` (§7.4). Earliest `FAIL` is at index 1 → `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY`. E12 explicitly forbids the loader from rejecting this.
18. **`UNASSESSED PASS PASS PASS`.** **Legal** — a `PASS` may follow an `UNASSESSED`, and out-of-order assessment is never inferred from storage order (§7.4). No `FAIL`, at least one `UNASSESSED` → §8.2 step 2 → `DESCRIPTIVE_ONLY_UNASSESSED`. The three recorded `PASS` results are retained in full.
19. **`UNASSESSED FAIL UNASSESSED UNASSESSED`.** **Legal**, and the disposition is `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY`, not `DESCRIPTIVE_ONLY_UNASSESSED`: §8.2 step 1 runs before step 2, so `FAIL` outranks `UNASSESSED` at every position. The discovered defect is reported as itself and is never buried behind an un-looked-at predicate.
20. **All four `UNASSESSED`.** Legal. No `FAIL`, some `UNASSESSED` → §8.2 step 2 → `DESCRIPTIVE_ONLY_UNASSESSED`. This is the frozen default for every provider/runtime today (design decision §9).
21. **All four `PASS`, but `disposition` written as `DESCRIPTIVE_ONLY_UNASSESSED`.** E19 fails — recorded and recomputed values differ. Refused; the recorded value is never trusted (C4).
22. **`disposition` written as `DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION`.** E19 fails — not one of the six eligibility tokens (§8.1). Refused.
23. **A `PASS` predicate with `evidence_refs: []`.** E13 fails — an unsupported assertion (§9.3). Refused.
24. **An `UNASSESSED` predicate carrying evidence.** E13 fails — contradicts its own status. Refused.
25. **`INFRASTRUCTURE_SYMMETRY` carrying predicate-level evidence while `PASS`.** E13 fails — its `evidence_refs` is always `[]`; its evidence lives exclusively on the channels (§9.5). Refused.
26. **An evidence reference written as the bare string `"docs/review.md"`.** E14 fails — evidence references are structured records (§9.1). Refused.
27. **`evidence_kind: "SCREENSHOT"`.** E14 fails — closed three-kind vocabulary. Refused.
28. **`REPOSITORY_PATH` locator `"../secrets/x"` or `"/etc/passwd"`.** E14 fails — no `..` segment, no leading `/`. Refused.
29. **`DESIGN_ARTIFACT_FIELD` locator naming `registration_manifest.json`.** E14 fails — only `registration_draft.json` exists at Stage B (§9.2). Refused.
30. **`DESIGN_ARTIFACT_FIELD` whose `content_digest` differs from `registration_draft_digest`.** E14 fails. Refused.
31. **`EXTERNAL_ATTESTATION` whose URL later 404s.** Not a failure at any time: no loader ever dereferences a locator (§9.2). The recorded `content_digest` remains the authenticated fact.
32. **`evidence_refs` listing the same reference twice.** E14 fails (uniqueness); never deduplicated on the caller's behalf.
33. **`infrastructure_symmetry_audit` written as a bare array.** E15 fails — it is an object with exactly the key `channels` (§10.1). Refused.
34. **`channels` holding three entries, or five.** E15 fails — exactly four, positionally. Refused.
35. **A fifth channel token invented, e.g. `TOKENIZER_VERSION`.** E15 fails — §5.F froze the candidate set at four. Refused.
36. **A channel `CHECKED` with `symmetry_result: "SYMMETRY_NOT_ASSESSED"`.** E16 fails — a checked channel without a symmetry result (§10.3). Refused.
37. **A channel `NOT_CHECKED` claiming `NO_ASYMMETRY_FOUND`.** E16 fails. Refused.
38. **Three channels `CHECKED` with no asymmetry, one `NOT_CHECKED`, and `predicates[1].status = "PASS"`.** E17 fails: §10.4 derives `UNASSESSED`, because §5.F permits `PASS` only when **every** channel is checked. Refused. The stratum can never be `CONFIRMATORY_ELIGIBLE` on this evidence.
39. **One channel `ASYMMETRY_FOUND`, three `NOT_CHECKED`, `predicates[1].status = "FAIL"`.** Legal: §10.4 derives `FAIL`. With `predicates[0] = PASS` and `predicates[2..3] = UNASSESSED`, §8.2 step 1 takes the earliest `FAIL`, at index 1 → `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY`. §10.4's `FAIL` branch is unconditional on the other channels' `check_status`, so an audit that found an asymmetry need not also complete the remaining channels — though it may, and those results would be retained.
40. **A per-position `isolation_evidence` array added to a stratum record.** E8 and E21 fail. "Per position" is evidence-generation granularity, aggregated into the `POSITION_STATE_ISOLATION` predicate's `evidence_refs` (§9.4). Refused.
41. **A `position_id` added anywhere.** E21 fails; `position_id` first exists at Stage C (F7). Refused.
42. **An `observation_status` field added to a record.** E8 / E21 fail — Stage B is prospective only (§11). Refused.
43. **A `confirmatory_strata` summary list added at top level.** E1 fails — that partition is a Stage-C derivation (§4.6). Refused.
44. **`runtime_identity_digest` copied from the wrong stratum's snapshot.** E25 fails — index-aligned equality (§13.1). Refused; no disposition is produced for any stratum.
45. **A manifest whose `registration_draft_digest` names a different draft than the one supplied.** E22 fails. Refused.
46. **A manifest bound to a `registration_manifest.json` instead of a draft.** E26 fails. Refused.
47. **A manifest edited in place after being written.** Either E20 fails (`self_digest` no longer verifies) or, if `self_digest` was recomputed, every downstream `eligibility_manifest_digest` reference breaks (implementation design §5.B.3). Either way the chain fails closed, and the edit was forbidden regardless (§15).
48. **A stratum recorded `DESCRIPTIVE_ONLY_UNASSESSED`, later promoted to `CONFIRMATORY_ELIGIBLE` in place.** Forbidden absolutely (§15). Requires abandon-and-recreate under a new `design_id`.
49. **A draft binds one snapshot for two proposed strata.** RC-5 fails (§12.3) — length mismatch. The draft is not written and does not load.
50. **A draft binds a snapshot for a `(provider_name, model)` not in `proposed_strata`.** RC-5 fails element-wise. Refused — closing the gap F4 left even at cardinality one.
51. **A draft binds two snapshots for the same `(provider_name, model)`.** RC-4 fails. Refused.
52. **A draft binds snapshots correctly but unsorted.** RC-3 fails; never re-sorted on the caller's behalf. Refused.
53. **A draft persisted in the old three-key nested shape.** The amended `_RUNTIME_KEYS` exact-key check fails on load: two unknown keys and one missing (§12.5). Refused — never silently accepted, never migrated.
54. **Someone re-adds `timeout_seconds` to `proposed_runtime_configuration` "for convenience".** The one-key check fails. Both values remain registered per stratum inside each `RuntimeSnapshotV1` (§12.4). Refused.
55. **Someone proposes amending `RuntimeSnapshotV1` to carry a list of models instead.** Out of scope and refused: §5.I is not reopened (§12.6), and the two-layer identity contract depends on one snapshot naming one runtime identity (F2).
56. **A reader receives semantically equivalent but noncanonical bytes that parse to the same authenticated object.** Not a failure — §5.B.2's verification procedure is unchanged and no byte-for-byte input gate is added (§16).

---

## 20. Conflict check against the frozen contracts

Every rule frozen above, checked against the frozen upstream text for direct contradiction.

| This addendum | Frozen text checked | Result |
|---|---|---|
| `schema_version = "EligibilityManifestV1"` (§4.1) | Stage-A clarification §4.1; implementation design §5.I; §7.1 naming pattern | **Consistent**; no conflicting literal exists (F9) |
| `registration_state = "ELIGIBILITY_FROZEN"` (§4.2) | Implementation design §5.A, §6 state machine | **Uses the frozen state name verbatim**, under the field name the sibling artifacts already use |
| Top-level eight-key set (§4.3) | Implementation design §5.B.1 field inventory; §12 audit catalog row | **Agrees**: `registration_draft_digest` present, `self_digest` present, `eligibility_manifest_digest` absent, `created_at`/`schema_version` present |
| One `created_at`, `assessed_at` retired (§5) | Implementation design §12 audit catalog; §7 PR-10 evidence column | **No contradiction**: PR-10's audit obligation is satisfied extensionally (§5, reason 3) |
| Four predicates, this order (§7.2) | Design decision §9; §12 PR-10 | **Quoted verbatim, unchanged** |
| Three-token status vocabulary (§7.3) | Design decision §9 `DESCRIPTIVE_ONLY_UNASSESSED`; implementation design §6 refusal | **Consistent**: `UNASSESSED` is recorded, never structurally missing |
| No short-circuit constraint on statuses (§7.4) | Design decision §9: "the **first** predicate that fails in the order above is recorded as the reason; **a configuration failing multiple predicates** is still `DESCRIPTIVE_ONLY_<reason>` for exactly one stated reason, not multiply classified" | **Consistent, and required by that text**: §9 explicitly contemplates a configuration failing multiple predicates, and constrains the *disposition* to one token, never the *record* to one `FAIL`. No frozen text mandates short-circuit evaluation. |
| Disposition derivation (§8.2) | Design decision §9's disposition table and its single-token rule | **Reproduces it exactly**: the earliest failing predicate in the frozen order supplies the one reason; extends only to make the `UNASSESSED` interaction explicit and total over all 81 combinations |
| Six-token disposition vocabulary (§8.1) | Design decision §9; implementation design §11 | **Agrees**; `DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION` correctly excluded as a non-eligibility token |
| Evidence as structured records (§9) | Implementation design §5.F "evidence reference"; §7 PR-4/PR-5/PR-10 evidence columns | **Representation only**; no scientific evidence requirement added or removed |
| "Per position" is generation granularity (§9.4) | Design decision §9 (stratum-scoped); implementation design §5.E, §6 (`position_id` at Stage C) | **The only consistent reading** (F6, F7) |
| Four channels, frozen order, minted tokens (§10.2) | Implementation design §5.F's four candidate channels | **Same four, same order**; tokens minted because none existed |
| `INFRASTRUCTURE_SYMMETRY` PASS condition (§10.4) | Implementation design §5.F "may only `PASS` when every channel is `CHECKED` with no asymmetry found" | **Reproduces it exactly** |
| `TOTAL_OBSERVATION` prospective only (§11) | Design decision §9 item 3; §12 PR-7 | **Prospective/realized split preserved unchanged** |
| Per-stratum runtime collection (§12.3) | Implementation design §5.I (snapshot shape), §5.I.5 (capture point 1 timing); design decision §10 (multiple declared strata) | **No conflict**: §5.I never stated a cardinality (F5); capture still precedes eligibility; multiple strata remain permitted |
| Retiring configuration-level `timeout_seconds`/`retry_policy` (§12.4) | Implementation design §5.I, §5.I.4 | **No value lost** — both remain required, per stratum, inside `RuntimeSnapshotV1` |
| Thirteen-key Stage-A top level preserved (§12.5, §12.6) | Stage-A clarification §4.2 | **Unchanged** |
| Copy-not-recapture runtime binding (§13) | Implementation design §5.I.5, §5.I.6 | **Consistent**: capture points 2 and 3 belong to later states; §5.I.6's pre-freeze token is used unchanged |
| Fail-closed contract (§14) | Implementation design §5.B.2, §6, §11 | **Consistent**: no normalization, no repair, no warning-only path |
| Immutability (§15) | Implementation design §5.A, §6, §12 | **Restated, unamended** |
| Canonical JSON / digest (§16) | Implementation design §5.B.2; Stage-A clarification §12 | **Restated, unamended**; no reader canonicality gate added |

No rule above contradicts any frozen text. The one place where frozen text is **superseded** rather than merely restated is enumerated exhaustively at §12.6, and it concerns exactly one Stage-A nested field.

---

## 21. Boundaries

**[NOT AUTHORIZED, and not done by this document]**

- No actual provider or model eligibility is assessed or assigned. `CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED` remains true for every provider/runtime configured in the repository (design decision §9), unchanged.
- No `design_id` is selected.
- No task matrix, no `M`, no assignment, no Monte Carlo seed, no randomization bit.
- No execution, no provider contact, no network access, no model inference.
- No results or confirmatory artifacts are created. `results/confirmatory/` is not written to.
- No Phase-P evidence is read, modified, reinterpreted, or migrated. `results/phaseP-rc4-qualification/` has no relationship to anything above.
- No randomization design change. No statistical methodology change. No analysis-contract change.
- No candidate, version, RC, or named phase is created.
- No `src/` file, no test file, and no existing document is modified. No pytest is run. Nothing is staged or committed.

---

## 22. DECISION

## **`CONFIRMATORY_ELIGIBILITY_SCHEMA_CLARIFICATION_DECISION: ELIGIBILITY_SCHEMA_AND_RUNTIME_CARDINALITY_FROZEN`**

Justification: all seven gaps `U1`-`U7` are closed with exactly one representation each. The `EligibilityManifestV1` top-level key set is fixed at exactly eight keys with exact JSON types and frozen literals (§4); the schema-version literal is minted once against a verified absence of any conflicting literal (§4.1, F9); the `created_at`/`assessed_at` ambiguity is resolved to a single manifest-level `created_at` with the artifact chain's existing grammar, and `assessed_at` is explicitly retired for this artifact (§5); the per-stratum record is fixed at exactly six keys using the existing Stage-A `provider`/`model` vocabulary, with a sorted, unique, exact element-wise cover of `proposed_strata` (§6); predicate states are one positional four-element array with a three-token vocabulary and **no short-circuit constraint** — every one of the eighty-one status combinations is an admissible record, multiple `FAIL` values are retained individually, and the single disposition is supplied instead by §8.2's three-step precedence (earliest `FAIL` wins; else any `UNASSESSED`; else all-`PASS`), which is proved total and single-valued over all eighty-one by an exhaustive partition (§7, §8); evidence references are structured three-key records with three closed kinds, one locator grammar each, exact cardinality rules, and a non-overlapping attachment partition, with PR-4's "per position" wording resolved as evidence-generation granularity aggregated into the stratum's isolation predicate (§9); `infrastructure_symmetry_audit` is a one-key record over exactly four positionally-ordered channels with newly minted stable tokens, a two-field checked/result representation preserving §5.F's own `CHECKED`/`NOT_CHECKED` vocabulary, and a derived-and-cross-checked predicate status that reproduces §5.F's PASS condition exactly (§10); `TOTAL_OBSERVATION` stays prospective with no execution-row field admitted (§11); and the runtime cardinality defect is repaired at its only coherent point — Stage A — by the minimum nested-shape amendment, one complete unmodified `RuntimeSnapshotV1` per proposed stratum, exactly covering `proposed_strata`, with the four rejected alternatives and their reasons recorded, the thirteen-key top level preserved, `RuntimeSnapshotV1` untouched, and every superseded Stage-A clause named individually (§12, §12.6). Each eligibility record binds to its stratum's already-registered expected runtime identity by copy, never by recapture, and neither a copy mismatch nor an undefendable runtime freeze can reach `CONFIRMATORY_ELIGIBLE` (§13). Twenty-six numbered fail-closed rules cover every rejection the contract requires, with no normalization and no repair path (§14). Immutability, the canonical JSON profile, and the `self_digest` algorithm are restated unamended (§15, §16). Fifty-six adversarial cases each resolve to exactly one deterministic outcome (§19), and every frozen contract is checked for contradiction with none found (§20).

```
ELIGIBILITY_MANIFEST_TOP_LEVEL_SCHEMA_FROZEN: YES
ELIGIBILITY_SCHEMA_VERSION_FROZEN: YES
TIMESTAMP_SEMANTICS_FROZEN: YES
PER_STRATUM_RECORD_SCHEMA_FROZEN: YES
PREDICATE_STATUS_VOCABULARY_FROZEN: YES
FIRST_FAILURE_AND_UNASSESSED_RULE_FROZEN: YES
EVIDENCE_REFERENCE_SCHEMA_FROZEN: YES
INFRASTRUCTURE_SYMMETRY_AUDIT_SCHEMA_FROZEN: YES
RUNTIME_CARDINALITY_RESOLVED: YES
PER_STRATUM_RUNTIME_BINDING_FROZEN: YES
FAIL_CLOSED_VALIDATION_SCHEMA_COMPLETE: YES

REMAINING_WORK_UNIT_2_SCHEMA_CHOICES:
NONE

THIS_DOCUMENT_IS_A_BINDING_IMPLEMENTATION_SCHEMA_ADDENDUM: YES

WORK_UNIT_1_RUNTIME_CARDINALITY_PATCH_REQUIRED: YES

STATISTICAL_METHODOLOGY_CHANGED: NO
RANDOMIZATION_DESIGN_CHANGED: NO

ACTUAL_PROVIDER_ELIGIBILITY_ASSIGNED: NO
ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
```

---

## 23. Validation

Commands run in producing this record, and nothing else:

```
git diff --check
git status --short
git diff --name-only
```

Expected and observed:

```
?? docs/post_phaseP_confirmatory_eligibility_schema_clarification.md
```

No `src/` change. No test change. No pytest. No staging. No commit.

```
ZERO MODEL INFERENCE
NO PHASE-P EVIDENCE MODIFIED
NO RC4 MODIFICATION
NO HISTORICAL PHASE-P REINTERPRETATION
NO RANDOMIZATION BIT GENERATED
NO SEED GENERATED
NO PROVIDER ELIGIBILITY ASSIGNED
NO CANDIDATE CREATED
NO WORK UNIT 1 IMPLEMENTATION COMMIT MERGED OR COPIED
NO FILES OTHER THAN THIS CLARIFICATION DOCUMENT CREATED OR MODIFIED
```
