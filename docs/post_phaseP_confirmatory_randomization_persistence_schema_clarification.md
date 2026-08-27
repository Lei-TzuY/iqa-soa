# Post-Phase-P confirmatory randomization persistence schema clarification

**Work Unit 4 persisted representation — `randomization_mc_provenance.json` and `assignment_manifest.json`**

| | |
|---|---|
| Document base | `origin/main` @ `befb7ff5a8e8256ce09b1be6930a8fb38f638ec0` |
| Implementation tip inspected (read-only) | `post-phasep-confirmatory-randomization-implementation` @ `a668d772951597cda5f7bad4d992e35da80b39f6` |
| Closes | `U-D1`–`U-D5`, `U-E1`–`U-E5`, and nothing else |
| Opens | nothing |

---

## 0. Boundary declaration

This document creates exactly one file — itself. It modifies no existing file. It writes no `src/`, no tests, runs no `pytest`, runs no `mypy`, contacts no provider, model, or network, draws no randomness, reads and writes no `results/` tree, stages nothing, and commits nothing.

**Frozen and NOT reopened by anything below:**

- statistical methodology, the analysis contract, every estimand/multiplicity/alpha decision, and the sharp-null semantics;
- the confirmatory randomization design: the randomization unit, `b_k`, the one-bit-per-task rule, the statistic, the `K <= 16` / `K > 16` threshold, and Monte-Carlo plus-one inference;
- provider eligibility semantics: the four predicates, their order, the first-failure rule, and the six disposition tokens;
- the Stage-A `RegistrationDraftV1`, Stage-B `EligibilityManifestV1`, and Stage-C `RegistrationManifestV1` schemas, in every respect;
- the canonical JSON profile and the `self_digest` algorithm (implementation design §5.B.2), which remain owned by Work Unit 1 and are reused here without a second implementation;
- the nine-state machine and the three-stage lifecycle (implementation design §5.A, §6);
- `resolve_label` / `complement` (implementation design §5.D);
- Phase-P interpretation and every Phase-P evidence artifact.

What this document does is strictly narrower: it fixes the **persisted representation** of the two Work Unit 4 artifacts, plus the minimum lifecycle/API binding needed to make that representation reachable exactly one way, and nothing else.

Throughout, unqualified section references are:

- **design decision** — `docs/post_phaseP_confirmatory_randomization_design_decision.md`
- **implementation design** — `docs/post_phaseP_confirmatory_randomization_implementation_design.md`
- **authorization** — `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md`
- **Stage-A clarification** — `docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md`
- **Stage-B clarification** — `docs/post_phaseP_confirmatory_eligibility_schema_clarification.md`
- **Stage-C clarification** — `docs/post_phaseP_confirmatory_final_registration_schema_clarification.md`

```
ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO
ACTUAL_PROVIDER_ELIGIBILITY_ASSESSMENT_AUTHORIZED: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
WU4_CODE_WRITTEN_BY_THIS_DOCUMENT: NO
NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO
HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO
```

---

## 1. Why this document exists

Work Unit 4 (`MC_PROVENANCE_PERSISTED` + `ASSIGNMENT_PERSISTED`, implementation design §16 step 4, authorized by authorization §5.1) stopped **before code** on a completed pre-implementation representation audit that returned `WU4_REPRESENTATION_AUDIT: BLOCK`.

The stop was correct, and it repeats a pattern the chain has now seen three times. Implementation design §5.L and §5.M freeze the *architecture* of both artifacts completely — the tagged union, the entropy source, the draw discipline, the timing, the digest chain, the refusal behavior. What they do not freeze is the *persisted representation* those values take. The clearest single symptom: implementation design §12's audit catalog lists `assignment_manifest.json`'s required fields as "§5.M fields, `bits`, `task_order`", while §5.M — the only section that purports to freeze this artifact — never uses the words `bits` or `task_order` at all.

That is precisely the evidentiary weight Stage-B clarification §5 already ruled insufficient when it retired `assessed_at`: a name in the *Evidence* column of a matrix, or in a *Required fields* cell of a catalog, "describes what the artifact must make auditable, not what its key set is."

| # | Unfrozen WU4 representation item | Closed at |
|---|---|---|
| **U-D1** | exact `randomization_mc_provenance.json` top-level key set per branch; the Monte-Carlo forbidden-key set | §6 |
| **U-D2** | provenance `schema_version` literal | §5 |
| **U-D3** | `created_at` / `generated_at` semantics, grammar, capture contract, and ordering | §8 |
| **U-D4** | `seed_hex` encoding; `numpy_version` source | §9 |
| **U-D5** | provenance generate-persist boundary; error family; loader first-failure order | §10, §11 |
| **U-E1** | exact `assignment_manifest.json` top-level key set | §12 |
| **U-E2** | `bits` / `task_order` JSON representation and their relationship | §14 |
| **U-E3** | bit JSON type; exact task cover; ordering/uniqueness; `K = 0` | §14 |
| **U-E4** | assignment timestamp grammar, capture contract, and ordering | §15 |
| **U-E5** | draw-persist boundary; `python_version`; loader order; provenance-reference mismatch error | §16, §17 |

This document resolves **all and only** `U-D1`–`U-D5` and `U-E1`–`U-E5`.

---

## 2. Binding inputs, and the read-only facts this document is built on

Read in full for this record, read-only, not modified, not reopened, not reinterpreted:

1. `docs/post_phaseP_confirmatory_randomization_design_decision.md` (Revision 4) — §4.D–§4.G, §6, §7.4.2.
2. `docs/post_phaseP_confirmatory_randomization_implementation_design.md` (Revision 3) — §5.A–§5.O, §6, §7, §11, §12, §13, §14, §17.
3. `docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md` — §5, §6, §7.
4. `docs/post_phaseP_confirmatory_final_registration_schema_clarification.md` — §2–§18.
5. `docs/post_phaseP_confirmatory_eligibility_schema_clarification.md` — §3, §5.
6. `docs/post_phaseP_confirmatory_registration_draft_schema_clarification.md` — conventions only.

The implementation design remains authoritative except where this document fills the explicitly unresolved WU4 persisted representation.

**Document-base integrity.** All six documents above are byte-identical between the document base `befb7ff` and the implementation tip `a668d77` (verified by blob-hash comparison). No representation decision below rests on unmerged text.

### 2.1 Interface facts, read from the pushed implementation branch

Inspected with `git show a668d77:<path>` only. Nothing was merged, cherry-picked, or copied.

| # | Fact | Read at |
|---|---|---|
| **H1** | Work Unit 4 is genuinely unimplemented: no `confirmatory_assignment.py`, no `AssignmentRandomSource`, no `persist_assignment`, no `resolve_label`, and no call to `secrets.randbits` or `secrets.token_bytes` exists anywhere under `src/`. The sole textual occurrence of `resolve_label` is a docstring sentence in `confirmatory_registration.py:2331` explaining that no treatment label appears at Stage C. | `git grep` over `src/` |
| **H2** | `canonical_json_bytes`, `compute_self_digest`, `attach_self_digest`, `verify_self_digest`, `serialize_artifact`, `parse_artifact` are implemented and exported from `confirmatory_registration.py` as the single owned realization of implementation design §5.B.2. Work Unit 4 reuses them; it defines no second algorithm. | `confirmatory_registration.py.__all__` |
| **H3** | Both existing artifact writers use an exclusive create (`path.open("xb")`), validate the complete persisted contract *before* path calculation, `mkdir`, and `open`, and convert `FileExistsError` into their own module error. | `confirmatory_registration.py`, `confirmatory_eligibility.py` |
| **H4** | `_require_design_id` enforces a single safe path segment (rejecting `/`, `\`, `:`, NUL, and Windows reserved stems), and every `*_path()` helper requires the resolved path to stay inside `confirmatory_root`. | `confirmatory_registration.py` |
| **H5** | `_require_integer` **deliberately rejects `bool`** — "``bool`` is a subclass of ``int``, and ``True`` would serialize as JSON ``true`` rather than an integer, so it is refused here" — and this is the repository's owned reading of §5.B.2's integer rule. | `confirmatory_registration.py:1693-1706` |
| **H6** | `_capture_created_at()` exists and is exactly `datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`; `freeze_final_registration` calls it internally, exactly once, and exposes no `created_at`, clock, as-of, or override parameter. `_CREATED_AT_PATTERN` is `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`. | `confirmatory_registration.py:220-221, 2424-2434, 3555` |
| **H7** | No literal `RandomizationMcProvenanceV1`, `RandomizationMCProvenanceV1`, or `AssignmentManifestV1` — nor any other candidate WU4 `schema_version` literal — occurs anywhere in `docs/` or `src/`. The two literals minted at §5 and §12 conflict with nothing. | `git grep` over `docs/`, `src/` |
| **H8** | `RegistrationManifest` exposes, as ordinary attributes of the sealed Stage-C record, every value Work Unit 4 needs and no other source provides: `design_id`, `K`, `randomization_mode`, `confirmatory_positions`, `registered_statistical_configuration` (carrying `statistic_spec_id` and `randomization_mc_samples`), and `self_digest`. | `confirmatory_registration.py:2197-2233` |
| **H9** | `load_registration_manifest(path, *, registration_draft, eligibility_manifest)` requires **both** bound upstream artifacts: a Stage-C manifest "may be *parsed* standalone but is never *accepted* without the complete chain it claims." A Work Unit 4 loader that wants an accepted manifest must therefore address the whole chain, not a single path. | `confirmatory_registration.py:3884-3912` |
| **H10** | The repository pins `numpy==2.1.3` and `requires-python = ">=3.11"` in `pyproject.toml`; `[tool.mypy]` sets `python_version = "3.11"`, `strict = true`. **No Stage-A, Stage-B, or Stage-C artifact registers a NumPy version in any field**, at any depth. `RuntimeSnapshotV1` (§5.I.1) and `EnvironmentIdentityV1` (§5.I.3) each carry `python_version` and neither carries a NumPy version. | `pyproject.toml`, `confirmatory_registration.py` |
| **H11** | `REGISTRATION_MANIFEST_FORBIDDEN_KEY_NAMES` already lists `bits`, `b_k`, `task_assignment_bit`, `assignment_digest`, and `randomization_mc_provenance_digest` as names forbidden at Stage C. Stage C therefore already knows these names exist and already binds them to the two downstream artifacts — it simply never gives them a shape. | `confirmatory_registration.py:1930-2000` |

### 2.2 Conventions observed, and applied below without exception

Carried forward verbatim from Stage-B clarification §3 and Stage-C clarification §2.2–§2.3, because a fifth and sixth artifact in one chain must obey one set of rules:

- **C1 — schema-version naming.** PascalCase noun phrase, `V1` suffix, no underscores: `RegistrationDraftV1`, `EligibilityManifestV1`, `RegistrationManifestV1`, `RuntimeSnapshotV1`, `ProposedStatisticalConfigurationV1`, `ConfirmatoryPositionV1`.
- **C2 — which nested objects carry `schema_version`.** A nested object carries one **if and only if** already-frozen upstream text assigns it one. No nested type minted by this document receives one. *(Neither WU4 artifact has any nested object at all — see §7 and §13 — so C2 is satisfied vacuously and no nested-versioning question arises.)*
- **C3 — array ordering is either *sorted* or *semantic*, never "implementation may choose".**
- **C4 — recorded derivations are cross-checked, never trusted.** A derivable value that is nevertheless recorded is recomputed by the loader and compared; a mismatch is refused.
- **C5 — no same-object digest alias, ever** (implementation design §5.B.1).
- **C6 — no field a loader cannot check** offline, from the artifact plus its bound upstream artifacts.
- **C7 — record a derivable value only where a frozen downstream consumer names it.** A derivable value earns a persisted field when some already-frozen consumer reads it *by name*, and not otherwise.

### 2.3 One additional convention, stated because Work Unit 4 is where it first bites

- **C8 — where wall-clock resolution and structural ordering disagree, structure is authoritative and the timestamp is corroborating.** The chain's frozen timestamp grammar is whole-second (H6). Work Unit 4 is the first place in the chain where two artifacts, and two events inside one artifact, are required to be *ordered* rather than merely *recorded* — and where both events routinely occur inside a single UTC second. C8 states the consequence once, so it is not re-decided at each comparison: **every frozen ordering requirement is discharged by call-sequence and state-machine structure, and every persisted timestamp comparison that expresses it is non-strict (`<=`).** A strict `<` anywhere in this contract would fail closed on correct runs, which is a defect, not a safeguard. §8 and §15 apply C8; §24 checks it against every frozen sentence that uses the word "before" or "predates".

---

## 3. Classification principle

**[SCHEMA — FROZEN]** Every persisted Work Unit 4 value falls into exactly one of five classes:

> **A. `REGISTRATION_COPY`** — copied verbatim from the validated, immutable `registration_manifest.json` (directly, or from its nested `registered_statistical_configuration`).
>
> **B. `UPSTREAM_DIGEST_REFERENCE`** — an upstream artifact's own `self_digest`, referenced under the frozen downstream name (§5.B.1).
>
> **C. `DETERMINISTIC_DERIVATION`** — computed with no new choice from A and B under already-frozen rules.
>
> **D. `GLOBAL_FROZEN_LITERAL`** — a constant fixed by the binding methodology/design documents and stamped by implementation.
>
> **E. `OPERATION_CAPTURE`** — a value produced by the generating operation itself: the two entropy-bearing values, the environment values observed at generation, and the timestamps. **Captured internally, never supplied by a caller, unreachable through any parameter of any name.**

**No Work Unit 4 persisted value falls into a sixth class such as "caller chooses."** This is the load-bearing property of the whole record, and §19 makes it structural rather than merely stated: the entire production surface of `confirmatory_assignment.py` accepts **no value input at all** beyond the address of the design (`confirmatory_root`, `design_id`). There is no parameter through which a seed, a seed byte, a bit, a bit vector, a timestamp, a clock, a NumPy version, a Python version, an `M`, or a random source could enter a persisted artifact. A caller cannot inject what it cannot reach.

Class E is larger here than at Stage C (where it had exactly one member, `created_at`) because Work Unit 4 is the first stage that *observes* rather than *derives*: it acquires entropy, it reads the interpreter's environment, and it marks the instants at which it did so. Every class-E member is nevertheless produced by the operation, authenticated by `self_digest`, and — per §8 T7 and §16.4 — is **never** a cross-artifact equality invariant.

---

## 4. §5.L.1 restated exactly as read, with the one reorganization named

**[RESTATEMENT — NOT A CHANGE]** Implementation design §5.L.1 lists seven "common fields, present in both modes":

```
schema_version   confirmatory_profile   design_id   final_registration_digest
randomization_mode   created_at   self_digest
```

and then §5.L.2 lists `K` and `statistic_spec_id` among exact mode's additions, and §5.L.3 lists `K` and `statistic_spec_id` again among Monte-Carlo mode's additions.

`K` and `statistic_spec_id` are therefore **present in both branches** and are common in substance while being written twice in presentation. §6 below presents them once, in the common block. **This is a presentational reorganization of the identical field set, not an amendment**: no field is added, removed, renamed, or moved between branches, and the resulting per-branch key counts reproduce §5.L exactly, as §6.3 confirms arithmetically.

---

## 5. `schema_version` — the provenance literal (closes U-D2)

**[SCHEMA — FROZEN]** The `randomization_mc_provenance.json` `schema_version` literal is exactly:

```
"RandomizationMcProvenanceV1"
```

**One literal, both branches.** The tagged union is one schema with two tagged shapes, not two schemas: implementation design §5.L.1 places `schema_version` in the *common* block precisely so a reader identifies the artifact before it branches on `randomization_mode`. A `RandomizationMcProvenanceExactV1` / `RandomizationMcProvenanceMonteCarloV1` pair is refused — it would make the tag redundant with the version and reintroduce the absent-vs-sentinel non-uniformity Revision 3 closed.

**Justified by C1 and H7:** PascalCase noun phrase, `V1` suffix, no underscores; it names the artifact it versions (`randomization_mc_provenance.json`); and no conflicting literal exists anywhere in `docs/` or `src/`.

**Casing of the initialism.** `Mc`, not `MC`. C1's exemplars contain no internal all-caps run, and the repository's owned convention capitalizes only the leading character of each word (`RegistrationDraftV1`, `EligibilityManifestV1`). `RandomizationMCProvenanceV1` is not this schema's version and is refused by `P4`. There is no alias, no alternative literal, no version negotiation, and no multi-version loader.

`MC_PROVENANCE_SCHEMA_VERSION_FROZEN: YES.`

---

## 6. `RandomizationMcProvenanceV1` — the closed tagged union (closes U-D1)

### 6.1 `EXACT_ENUMERATION` — exactly these ten keys, no more, no fewer

**[SCHEMA — FROZEN]**

```
schema_version
confirmatory_profile
design_id
final_registration_digest
randomization_mode
created_at
K
statistic_spec_id
exact_support_size
self_digest
```

**Exactly ten keys.** A persisted exact-mode artifact with an eleventh key, or missing any one of the ten, is malformed and is refused (`P3`). There are no optional keys and no conditional presence within the branch.

Frozen literals and derivations:

```
schema_version             = "RandomizationMcProvenanceV1"                     (D)
confirmatory_profile       = "post_phaseP_confirmatory_randomization_v1"       (D)
design_id                  = registration_manifest.design_id                   (A)
final_registration_digest  = registration_manifest.self_digest                 (B)
randomization_mode         = "EXACT_ENUMERATION"                               (A)
created_at                 = internally captured sealing instant (§8)          (E)
K                          = registration_manifest.K                           (A)
statistic_spec_id          = "confirmatory_task_sign_flip_v1"                  (D)
exact_support_size         = 2 ** K                                            (C)
self_digest                = §5.B.2 over the other nine keys                    (C)
```

**No entropy API is called on this branch, at all.** Not `secrets.token_bytes`, not `secrets.randbits`, not `os.urandom`, not any NumPy or `random` facility. `exact_support_size` is arithmetic on a registered integer, and `2 ** K` for `K <= 16` is at most `65536` — an ordinary JSON integer under §5.B.2, never a string.

### 6.2 `MONTE_CARLO` — exactly these nineteen keys, no more, no fewer

**[SCHEMA — FROZEN]**

```
schema_version
confirmatory_profile
design_id
final_registration_digest
randomization_mode
created_at
K
statistic_spec_id
source_kind
source_api
entropy_bytes
seed_hex
seed_encoding
rng_library
rng_bit_generator
numpy_version
randomization_mc_samples
generated_at
self_digest
```

**Exactly nineteen keys.** A persisted Monte-Carlo artifact with a twentieth key, or missing any one of the nineteen, is malformed and is refused (`P3`).

Frozen literals and derivations (the nine common entries are exactly as §6.1, with `randomization_mode = "MONTE_CARLO"`):

```
source_kind                = "PYTHON_SECRETS_TOKEN_BYTES"                      (D)
source_api                 = "secrets.token_bytes"                             (D)
entropy_bytes              = 32                                                (D)
seed_hex                   = lowercase hex of the 32 raw bytes (§9)            (E)
seed_encoding              = "uint256_big_endian"                              (D)
rng_library                = "numpy"                                           (D)
rng_bit_generator          = "PCG64"                                           (D)
numpy_version              = internally captured numpy.__version__ (§9)        (E)
randomization_mc_samples   = registration_manifest
                               .registered_statistical_configuration
                               .randomization_mc_samples                       (A)
generated_at               = internally captured entropy instant (§8)          (E)
```

### 6.3 The two forbidden sets are exactly complementary — the arithmetic, confirmed

**[SCHEMA — FROZEN]** Let

```
COMMON      = { schema_version, confirmatory_profile, design_id,
                final_registration_digest, randomization_mode, created_at,
                K, statistic_spec_id, self_digest }              |COMMON| = 9

EXACT_ONLY  = { exact_support_size }                             |EXACT_ONLY| = 1

MC_ONLY     = { source_kind, source_api, entropy_bytes, seed_hex, seed_encoding,
                rng_library, rng_bit_generator, numpy_version,
                randomization_mc_samples, generated_at }         |MC_ONLY| = 10
```

Then:

```
keys(EXACT_ENUMERATION) = COMMON ∪ EXACT_ONLY   →   9 + 1  = 10   ✓ §6.1
keys(MONTE_CARLO)       = COMMON ∪ MC_ONLY      →   9 + 10 = 19   ✓ §6.2

forbidden(EXACT_ENUMERATION) = MC_ONLY          →   10 fields
forbidden(MONTE_CARLO)       = EXACT_ONLY       →    1 field
```

**Reconciliation against implementation design §5.L, confirmed not repaired.** §5.L.1 lists 7 common fields; §5.L.2 adds 3 (`exact_support_size`, `K`, `statistic_spec_id`) giving `7 + 3 = 10`; §5.L.3 adds 12 (`K`, `statistic_spec_id`, and the ten of `MC_ONLY`) giving `7 + 12 = 19`. Both counts reproduce §6.1 and §6.2 exactly. The only difference is presentational, as §4 states: this document counts `K` and `statistic_spec_id` once in `COMMON` rather than twice in the branch blocks.

**`forbidden(EXACT_ENUMERATION)` reproduces §5.L.2's explicit ten-field absent-list verbatim** — `seed_hex`, `entropy_bytes`, `source_kind`, `source_api`, `seed_encoding`, `rng_library`, `rng_bit_generator`, `numpy_version`, `randomization_mc_samples`, `generated_at` — with no field added and none dropped.

**`forbidden(MONTE_CARLO) = { exact_support_size }` is new, and it is the whole of `U-D1`'s second half.** §5.L.3 never stated it, which left `exact_support_size` neither required nor forbidden on the Monte-Carlo branch — the single field in the artifact whose presence two competent implementers could have disagreed about while both satisfying every frozen sentence. It is now forbidden: on the Monte-Carlo branch the exact support is not the object of inference, `2 ** K` for `K > 16` is not a quantity the plus-one estimator consumes, and carrying it would make one artifact assert both a support enumeration and a sampled approximation of it.

**Closure is by the key set, not by the forbidden list.** Because both branches are declared *exact* key sets, any key outside the twenty named in `COMMON ∪ EXACT_ONLY ∪ MC_ONLY` is refused by `P3` without needing to appear on a forbidden list at all. The two forbidden sets above are therefore statements of *which named field belongs to the other branch*, not an open-ended prohibition, and the union of the two branch key sets is exactly the twenty fields the audit enumerated.

### 6.4 No lifecycle/state field — the choice is made, and it is "no"

**[SCHEMA — FROZEN]** `randomization_mc_provenance.json` carries **no** `registration_state`, `provenance_state`, `lifecycle_state`, or field of any other name recording `MC_PROVENANCE_PERSISTED`.

The candidate reason to add one is real and was weighed: all three registration artifacts carry `registration_state` (`"REGISTRATION_DRAFT"`, `"ELIGIBILITY_FROZEN"`, `"FINAL_REGISTRATION_FROZEN"`), and implementation design §6 does name a state `MC_PROVENANCE_PERSISTED`. It is refused on C7:

1. **No frozen consumer reads it by name.** Implementation design §5.L.3's analysis-time list, §5.O's resume checklist, §6's transition row, and §12's catalog entry between them name every field a consumer of this artifact reads. None names a state field. Stage C's `registration_state` earns its place because §5.A, §6, and Stage-C clarification §4.2 all read it by name.
2. **Artifact presence *is* the state.** `MC_PROVENANCE_PERSISTED` is defined by implementation design §6 as the state in which `randomization_mc_provenance.json` exists and digest-validates. A persisted state token would be a second encoding of a fact the file's existence already carries — a redundancy that must then be cross-checked (C4) against a fact that cannot disagree with itself.
3. **The three registration artifacts share one `design_id` directory and one `registration_state` progression precisely because each supersedes the last as the design's current registration record.** These two artifacts do not supersede one another or the registration; they are downstream products of a sealed registration.

The same reasoning, applied identically, yields no state field on `assignment_manifest.json` (§12.2).

`MC_PROVENANCE_TAGGED_UNION_CLOSED: YES.`

---

## 7. Per-field type freeze — `RandomizationMcProvenanceV1`

**[SCHEMA — FROZEN]** No field of this artifact is an object or an array. Every one of the twenty possible fields is a JSON string or a JSON integer, so the artifact has no nested shape, no ordering rule, and no uniqueness rule of its own.

| Field | Branch | JSON type | Content rule | Class |
|---|---|---|---|---|
| `schema_version` | both | string | exactly `"RandomizationMcProvenanceV1"` | D |
| `confirmatory_profile` | both | string | exactly `"post_phaseP_confirmatory_randomization_v1"` | D |
| `design_id` | both | string | non-empty; a single safe path segment (H4); equal as a string value to `registration_manifest.design_id`. **[DEFERRED VALUE SELECTION]** | A |
| `final_registration_digest` | both | string | lowercase 64-character hex SHA-256; equals `registration_manifest.self_digest` | B |
| `randomization_mode` | both | string | exactly `"EXACT_ENUMERATION"` or `"MONTE_CARLO"`; equals `registration_manifest.randomization_mode` | A |
| `created_at` | both | string | `YYYY-MM-DDTHH:MM:SSZ` (§8); internally captured, never a parameter | E |
| `K` | both | JSON integer `>= 0` | equals `registration_manifest.K`; `bool` refused (H5); consistent with the branch: `K <= 16` exact, `K > 16` Monte Carlo | A |
| `statistic_spec_id` | both | string | exactly `"confirmatory_task_sign_flip_v1"` | D |
| `exact_support_size` | exact **only** | JSON integer `>= 1` | exactly `2 ** K`; `bool` refused | C |
| `source_kind` | MC **only** | string | exactly `"PYTHON_SECRETS_TOKEN_BYTES"` | D |
| `source_api` | MC **only** | string | exactly `"secrets.token_bytes"` | D |
| `entropy_bytes` | MC **only** | JSON integer | exactly `32`; never a string; `bool` refused | D |
| `seed_hex` | MC **only** | string | exactly 64 characters matching `^[0-9a-f]{64}$` (§9). **[DEFERRED VALUE SELECTION]** | E |
| `seed_encoding` | MC **only** | string | exactly `"uint256_big_endian"` | D |
| `rng_library` | MC **only** | string | exactly `"numpy"` | D |
| `rng_bit_generator` | MC **only** | string | exactly `"PCG64"` | D |
| `numpy_version` | MC **only** | string | non-empty; verbatim `numpy.__version__` captured at generation (§9) | E |
| `randomization_mc_samples` | MC **only** | JSON integer `>= 1` | equals `registration_manifest.registered_statistical_configuration.randomization_mc_samples`; never `null` on this branch; `bool` refused. **[DEFERRED VALUE SELECTION]** | A |
| `generated_at` | MC **only** | string | `YYYY-MM-DDTHH:MM:SSZ` (§8); internally captured, never a parameter | E |
| `self_digest` | both | string | lowercase 64-character hex SHA-256 per §5.B.2, unchanged | C |

**No numeric representation choice arises.** `K`, `exact_support_size`, `entropy_bytes`, and `randomization_mc_samples` are ordinary JSON integers per §5.B.2; no field of this artifact is a real number, so §5.B.2's canonical-decimal-string rule has no member here.

**`seed_hex` is not a digest.** It matches the same `^[0-9a-f]{64}$` grammar as a SHA-256 lowercase hex digest, because 32 bytes render as 64 hex characters either way. It is nevertheless entropy, never a hash of anything, and it is **never** compared against, substituted for, or validated as a digest field. `P8` validates digest grammar on `final_registration_digest` and `self_digest` only; `P13` validates `seed_hex` under its own rule. An implementation that routes `seed_hex` through a digest validator satisfies the grammar by coincidence and must not do so.

---

## 8. Provenance timestamps — `created_at` and `generated_at` (closes U-D3)

### 8.1 The two fields, distinguished

**[SCHEMA — FROZEN]**

| | `created_at` | `generated_at` |
|---|---|---|
| Present in | **both** branches | `MONTE_CARLO` **only**; forbidden in `EXACT_ENUMERATION` |
| Records | the instant the artifact was **sealed** | the instant the **entropy was acquired** |
| Bound to | the completed construction, immediately before `self_digest` | the one authorized `secrets.token_bytes(32)` call |
| Class | E | E |

The two are distinct fields because they record distinct events, and the whole prospective-freeze claim rests on the second: design decision §7.4.2 conditions **E** and **F** require the draw mechanism to be "frozen prospectively" and "generated and persisted under an auditable procedure before inspection of any confirmatory outcome." `generated_at` is the persisted record of the *generation* event; `created_at` is the persisted record of the *sealing* event, and is the field whose name and grammar the rest of the chain already uses.

### 8.2 Capture contract — frozen

**[SCHEMA — FROZEN]** Both are **not caller-selectable**. They are produced by the provenance operation itself.

| # | Rule |
|---|---|
| **T1** | The provenance operation captures `created_at` internally, **exactly once**, per invocation. On the Monte-Carlo branch it captures `generated_at` internally, **exactly once**, per invocation. There is no second capture, no re-capture, and no recomputation on any later path. |
| **T2** | **The caller must not supply either value.** The operation exposes **no** `created_at` parameter, no `generated_at` parameter, no clock parameter, no "as-of" parameter, no time-source or `now` injection, and no override of any name. There is no interface through which a caller could propose, inject, adjust, or backdate either value. This is the same structural technique Stage-C clarification §4.4.1 T2 uses, and §19 makes it total across the Work Unit 4 surface. |
| **T3** | Each captured value is a **whole-second UTC instant with a mandatory `Z` designator**, rendered under the already-frozen chain grammar `YYYY-MM-DDTHH:MM:SSZ`. Sub-second precision is truncated **by the capture itself**, at the point of capture, exactly as `_capture_created_at()` already does (H6). This is rendering the instant the operation captured, not rewriting a value someone supplied. |
| **T4** | Capture points, ordered: on the Monte-Carlo branch, `generated_at` is captured in immediate association with the single `secrets.token_bytes(32)` call, before the seed is encoded; `created_at` is captured on the successful construction path after every check that does not depend on it, and **strictly before `self_digest` is computed** and **strictly before any byte reaches disk**. A construction that fails never seals an artifact, and a captured instant never exists without a sealed artifact. |
| **T5** | Both captured values **are** fields of `randomization_mc_provenance.json` and are therefore inside the `self_digest` preimage — authenticated like every other field. |
| **T6** | On the exact branch, `generated_at` is **forbidden** (§6.3) because no generation event occurred: no entropy API was called, so there is no acquisition instant to record. Fabricating one would assert an event that did not happen. |
| **T7** | Neither value is a **cross-artifact equality invariant**. Neither need equal, and ordinarily will not equal, `registration_manifest.created_at` or any other artifact's timestamp. No rule in this document compares either for *equality* against any other artifact's timestamp, and none may be added. Ordering relations (§8.3) are not equality invariants. |

### 8.3 Ordering — non-strict, and why (C8)

**[SCHEMA — FROZEN]** The frozen ordering requirements and the persisted relations that corroborate them:

```
Monte-Carlo branch, within the artifact:
    generated_at <= created_at

Both branches, across artifacts:
    randomization_mc_provenance.created_at <= assignment_manifest.generation_started_at
```

**Both relations are non-strict.** Under C8 this is forced, not chosen: the grammar is whole-second (T3, H6), and entropy acquisition, artifact construction, sealing, persistence, and the immediately following assignment generation routinely complete within one UTC second for any realistic `K`. A strict `<` would refuse a correct, honestly generated artifact whenever the machine was fast enough — an intermittent, clock-dependent, load-dependent failure, and the worst possible defect in a contract whose entire purpose is to make prospective ordering auditable.

**What actually proves the ordering.** The authoritative proof is **structural**, in three layers, none of which depends on a timestamp:

1. **State machine.** Implementation design §6 admits no path from `FINAL_REGISTRATION_FROZEN` to `ASSIGNMENT_PERSISTED` that does not pass through `MC_PROVENANCE_PERSISTED`, and no path that re-enters either.
2. **Artifact prerequisite.** The assignment operation refuses to proceed unless `randomization_mc_provenance.json` already exists on disk and validates `P1`–`P24` (§16.1 steps 2–4). An artifact that does not yet exist cannot be loaded, so assignment cannot precede provenance persistence.
3. **Single-operation indivisibility.** §10 and §16 make acquire-and-persist one operation each, so there is no interval during which entropy exists un-persisted and a caller could act on it.

**The timestamp relations are supplemental audit consistency checks.** They detect a grossly inconsistent set of artifacts — a provenance file stamped days after the assignment that references it — and they are worth having for exactly that. They are not, and are not claimed to be, a proof of ordering, and they are stated here as non-strict so they never contradict a structurally correct run.

**No loader can prove historical wall-clock truth, and this document does not claim one can.** No rule here asserts that a loader can establish, from the artifacts alone, that a persisted `generated_at` is the real instant at which `secrets.token_bytes(32)` returned. That guarantee comes from the construction path's structure (T1–T4, §10) plus the `self_digest` and downstream-reference chain that makes any post-hoc edit detectable (§20) — not from `P15`, `P16`, or any other loader rule. Claiming otherwise would be a guarantee the artifact cannot support. §21 documents this separation between writer prerequisites and loader rules explicitly.

### 8.4 The exact-branch temporal role, stated (the second half of U-D3)

**[SCHEMA — FROZEN]** Implementation design §5.L.3's analysis-time rule — "the provenance's `generated_at` predates both assignment generation and every execution row's timestamp" — is written for the Monte-Carlo branch, where `generated_at` exists. On the exact branch that field is forbidden (T6), which left the same check with no field to read.

Resolved: **on the `EXACT_ENUMERATION` branch, `created_at` is the field that carries the provenance-vs-assignment temporal relation**, under the same non-strict comparison of §8.3. One relation therefore serves both branches uniformly:

```
provenance.created_at <= assignment_manifest.generation_started_at        (both branches)
provenance.generated_at <= provenance.created_at                          (MC branch only)
```

On the Monte-Carlo branch the two together give `generated_at <= generation_started_at` transitively, which is exactly what §5.L.3 requires, read non-strictly per C8.

**Why the exact branch has this check at all.** On the exact branch there is no seed whose prospective generation needs proving; the artifact records the *absence* of seed material. The check is retained solely so the six-artifact chain has one uniform temporal contract rather than a mode-conditional one — the same uniformity motive that made the artifact mandatory in both modes in the first place (§5.L.1).

**Execution-row timestamps are out of scope here.** §5.L.3's remaining clause — that provenance predates "every execution row's timestamp" — is discharged against whatever timestamp the already-frozen execution-row contract (§5.C, §5.I) provides. **This document invents no execution-row timestamp field** and adds nothing to the row contract.

`PROVENANCE_TIMESTAMP_CONTRACT_FROZEN: YES.`

---

## 9. `seed_hex` and `numpy_version` (closes U-D4)

### 9.1 `seed_hex` — the exact encoding

**[SCHEMA — FROZEN]** `seed_hex` is:

- the **lowercase hexadecimal encoding of the exact 32 raw bytes** returned by the single `secrets.token_bytes(32)` call;
- **exactly 64 hexadecimal characters**, always, matching `^[0-9a-f]{64}$`;
- with **no `0x` prefix**, no `0X` prefix, no separators, no whitespace, and no uppercase digit;
- with **leading zero bytes preserved** as leading `"00"` pairs — a first byte of `0x00` renders as two leading `0` characters and the string remains 64 characters long;
- in **unchanged byte order**: the first byte returned by `token_bytes` is the first hex pair.

Equivalently, and normatively: `seed_hex == raw_seed_bytes.hex()` for the 32-byte object `raw_seed_bytes`.

The seed integer is then, and only then:

```
seed_int = int.from_bytes(raw_seed_bytes, byteorder="big", signed=False)
generator = numpy.random.Generator(numpy.random.PCG64(seed_int))
```

**This closes the string/int ambiguity precisely.** `seed_encoding = "uint256_big_endian"` describes the *bytes → integer* interpretation and says nothing about the *integer → string* rendering. Rendering `seed_int` instead of the bytes would produce a 62-character string whenever the leading byte is zero — a 1-in-256 event — so two conforming implementations would disagree on roughly 0.4% of seeds, and a reproduction check comparing the two strings would fail for reasons unrelated to the seed. Fixing the encoding on the **bytes** makes the length invariant and the round-trip total:

```
int.from_bytes(bytes.fromhex(seed_hex), byteorder="big", signed=False) == seed_int
```

for every possible draw, including the all-zero one.

**`entropy_bytes = 32` and `len(seed_hex) == 64` are consistent by construction**, and `P13` checks the grammar rather than deriving the length from `entropy_bytes` — a fixed literal check is stricter and cannot be defeated by a tampered `entropy_bytes`.

### 9.2 `numpy_version` — captured, not registered

**[SCHEMA — FROZEN]** `numpy_version` is:

- **captured internally** during Monte-Carlo provenance generation, from `numpy.__version__` as observed in the generating process;
- persisted **verbatim** as a non-empty JSON string, with no parsing, normalization, truncation, or reformatting;
- **never caller-supplied** — no parameter of any name accepts it (T2, §19);
- compared, at analysis time, for **exact string equality** against the NumPy version then loaded, per implementation design §5.L.3.

**This document does not pretend any Stage-A/B/C artifact previously registered a NumPy version.** H10 records the read-only fact: no such field exists anywhere in the three registration artifacts, at any depth. Implementation design §5.L.3's phrase "the registered NumPy version" is therefore satisfied **by this artifact's own field** — `numpy_version` is *the* registration of the NumPy version for this design, made at the moment the generator is constructed, and there is no earlier registration for it to be a copy of. Reading the phrase any other way would require inventing a Stage-A field, which is out of this document's remit and is refused.

**Why capture is the correct class.** The value must describe the interpreter that actually built `PCG64(seed_int)`, because that is what the analysis-time equality check is for: it detects a NumPy upgrade between generation and analysis that could change the bit stream `PCG64` produces for a given seed. A caller-supplied value would describe a claim rather than the generator, and would make the check circular. The repository's `numpy==2.1.3` pin (H10) is corroborating context, not a substitute: the pin makes the captured value stable and reproducible in practice, while the captured field makes a pin change *detectable* rather than silent.

`SEED_ENCODING_AND_NUMPY_VERSION_FROZEN: YES.`

---

## 10. Provenance generate-persist boundary and errors (closes U-D5, first half)

### 10.1 One indivisible public operation

**[SCHEMA — FROZEN]** Production entropy acquisition and immutable artifact persistence form **one public operation**. There is **no** production API — no public function, no public method, no exported helper, and no keyword flag on the persisting operation — that permits:

```
generate seed  →  inspect / discard  →  generate another  →  persist the selected one
```

**Why this is a representation-level requirement and not a style preference.** Design decision §7.4.2 condition **G** requires that the draw mechanism be "never selected, filtered, regenerated, or extended in response to the observed `p_MC`". If a public `generate` returned an inspectable seed that a caller could discard, seed shopping would be possible **and undetectable**: only the persisted artifact is ever audited, and a discarded draw leaves no trace anywhere. No digest, no timestamp, and no duplicate-refusal rule can detect a draw that was never written. The only mechanism that forecloses it is the absence of the interface.

**Frozen operation sequence.** The production operation, given only `(confirmatory_root, design_id)`:

```
 1. Load and revalidate the complete frozen registration chain from disk —
    registration_draft.json, eligibility_manifest.json, registration_manifest.json —
    through the already-owned WU1/WU3 loaders (H9).  Refuse on any failure.
 2. Derive randomization_mode from the loaded registration manifest.  Never from a
    parameter, never from K recomputed locally, never from a caller hint.
 3. Refuse if randomization_mc_provenance.json already exists for this design_id.
    This check precedes every entropy call.
 4. EXACT_ENUMERATION branch: call NO entropy API.  Compute exact_support_size = 2 ** K.
 5. MONTE_CARLO branch: capture generated_at and call secrets.token_bytes(32)
    exactly once.  Never twice, never in a loop, never conditionally on the value drawn.
 6. Construct the complete branch-exact artifact object.
 7. Capture created_at; compute self_digest over the object per §5.B.2.
 8. Exclusive-create the file (§20).
 9. Return only the already-persisted, already-validated artifact.
```

**Failure after entropy acquisition.** If step 8 fails after step 5 has drawn entropy, the operation **does not retry, does not re-draw, and does not acquire new entropy**. It fails. Recovery is the abandon-and-recreate rule already frozen at §5.A — a new `design_id` under explicit human re-authorization — never an automatic retry. This is the same rule §5.M already states for a missing or corrupt assignment, applied to the artifact one state earlier.

**Steps 1 and 2 are why the operation is addressed by `(confirmatory_root, design_id)`.** H9 records that a Stage-C manifest is never *accepted* without both bound upstream artifacts, so an operation that wants an accepted manifest must reach the whole chain. §19 states the resulting API-architecture rule.

### 10.2 Error family — experiment-layer, minimal

**[SCHEMA — FROZEN]** Work Unit 4's module owns one error hierarchy, mirroring the pattern Work Units 1 and 2 already established (one module-scoped base deriving from `ValueError`, per `ConfirmatoryRegistrationError` and `ConfirmatoryEligibilityError`):

```
ConfirmatoryAssignmentError(ValueError)          — module base, owned by
                                                   confirmatory_assignment.py
    McProvenanceIntegrityError                   — provenance malformed, wrong-mode,
                                                   digest-unverifiable, or wrongly bound
    DuplicateMcProvenanceError                   — provenance already persisted for design_id
    AssignmentIntegrityError                     — §11 frozen name; see §16.4
    DuplicateAssignmentError                     — §11 frozen name; duplicate assignment write
    AssignmentNotPersistedError                  — §11 frozen name; raised by the runner,
                                                   type owned here
```

The three assignment names are **already frozen** by implementation design §11 and are adopted unchanged. The two provenance names are **minted here**, by exact analogy, because §6's transition row requires a refusal — "Refuse assignment generation if the provenance artifact is absent, wrong-mode, or contains a forbidden/missing field for its declared mode" — for which §11 assigns no error at all. Two names, chosen to mirror the two assignment names one-for-one, is the smallest family that distinguishes the two refusals a caller must handle differently: *this artifact is wrong* versus *this artifact already exists*.

**Which surface raises which — frozen.** `McProvenanceIntegrityError` and `DuplicateMcProvenanceError` are the public surface of the **provenance** operations (§10.1, §11): a caller invoking the provenance generator or the provenance loader directly may receive either. They are **never** the public surface of an **assignment** entry point: an assignment loader or generation operation that encounters a bad provenance artifact catches the provenance-layer exception and re-raises `AssignmentIntegrityError` `from` it, preserving the cause (§16.4). One layer, one public error type, no transitive leak.

**`CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` is never raised by a production generation path.** §11 scopes that token to "analysis (whole confirmatory experiment)", and it remains analysis-scoped. Generation-time refusals raise the experiment-layer errors above. The analyzer's own routing of a bad provenance artifact to `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (§5.L.3) is unchanged and unaffected.

**No third error is minted for I/O failure.** `FileExistsError` from the exclusive create is converted to the relevant `Duplicate*` error, exactly as H3 records the existing writers doing. Any other `OSError` propagates unchanged — deliberately, because swallowing it is what would enable the silent-retry path §10.1 forbids.

---

## 11. Provenance loader — `P1`–`P24`, first-failure order (closes U-D5, second half)

**[SCHEMA — FROZEN]** A loader applies the rules below **in the numbered order** and aborts on the **first** failure. There is **no normalization, no repair, no sorting on the caller's behalf, no deduplication, no default-filling, no warning-only path, and no partial acceptance.**

**First-failure order is contractually observable**, exactly as Stage-B clarification §14 froze for `E1`–`E26` and Stage-C clarification §16 froze for `F1`–`F39`: for any given malformed artifact, the rule that fires is the lowest-numbered rule it violates, and a conformant implementation may be tested on that.

**Layering rule.** Every local shape/schema/type/constant/grammar check precedes `self_digest` verification, and `self_digest` verification precedes every upstream artifact load and binding check. An upstream loader can therefore never preempt a local schema defect, and a malformed local artifact is never diagnosed as a chain problem.

### 11.1 Tier 1 — local, checkable from the artifact alone

| # | Rule |
|---|---|
| **P1** | File envelope: at most one trailing `\n` stripped; the remaining bytes decode as UTF-8 and parse as a JSON **object**; every key is a string, at every depth. |
| **P2** | `randomization_mode` is present, is a string, and is exactly `"EXACT_ENUMERATION"` or `"MONTE_CARLO"`. **The tag is read first because it selects the branch every later rule is evaluated against.** |
| **P3** | The top-level key set is **exactly** the branch's set: ten keys (§6.1) for `EXACT_ENUMERATION`, nineteen (§6.2) for `MONTE_CARLO`. No missing key, no extra key. This single rule enforces both required-presence and forbidden-absence, including the exact branch's ten forbidden seed fields and the Monte-Carlo branch's forbidden `exact_support_size`. |
| **P4** | `schema_version` is exactly `"RandomizationMcProvenanceV1"`. |
| **P5** | `confirmatory_profile` is exactly `"post_phaseP_confirmatory_randomization_v1"`. |
| **P6** | `design_id` is a non-empty string and a single safe path segment (H4). |
| **P7** | Every field of the branch has the JSON type §7 assigns it. Integer-typed fields are JSON integers and **`bool` is refused** (H5). |
| **P8** | `final_registration_digest` and `self_digest` each match `^[0-9a-f]{64}$`. (`seed_hex` is **not** checked here — §7, `P13`.) |
| **P9** | `K >= 0`, and `K` is consistent with the declared branch: `K <= 16` for `EXACT_ENUMERATION`, `K > 16` for `MONTE_CARLO`. |
| **P10** | `statistic_spec_id` is exactly `"confirmatory_task_sign_flip_v1"`. |
| **P11** | `EXACT_ENUMERATION` only: `exact_support_size == 2 ** K`, recomputed, never trusted (C4). |
| **P12** | `MONTE_CARLO` only: `source_kind`, `source_api`, `entropy_bytes`, `seed_encoding`, `rng_library`, `rng_bit_generator` each equal their frozen literal of §6.2. |
| **P13** | `MONTE_CARLO` only: `seed_hex` matches `^[0-9a-f]{64}$` — exactly 64 characters, lowercase, no prefix (§9.1). |
| **P14** | `MONTE_CARLO` only: `numpy_version` is a non-empty string; `randomization_mc_samples` is a JSON integer `>= 1`. |
| **P15** | Timestamp grammar: `created_at` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` and is a real instant; on `MONTE_CARLO`, `generated_at` likewise. |
| **P16** | `MONTE_CARLO` only: `generated_at <= created_at`, non-strict (§8.3, C8). |
| **P17** | `self_digest` verifies per §5.B.2: remove only `self_digest`, recanonicalize, recompute SHA-256, compare. |

### 11.2 Tier 2 — requires the bound registration chain

| # | Rule |
|---|---|
| **P18** | `registration_manifest.json` for this `design_id` exists, loads, and validates through `F1`–`F37` against its own bound draft and eligibility manifest (H9). A provenance artifact is never accepted against an unvalidated registration. |
| **P19** | `final_registration_digest` equals `registration_manifest.self_digest`. |
| **P20** | `design_id` equals `registration_manifest.design_id`. |
| **P21** | `randomization_mode` equals `registration_manifest.randomization_mode` (implementation design §5.L.1, §6). |
| **P22** | `K` equals `registration_manifest.K`. |
| **P23** | `statistic_spec_id` equals `registration_manifest.registered_statistical_configuration.statistic_spec_id`. |
| **P24** | `MONTE_CARLO` only: `randomization_mc_samples` equals `registration_manifest.registered_statistical_configuration.randomization_mc_samples`. |

### 11.3 Rejection inventory

| Rejected condition | Rule |
|---|---|
| not an object; bad encoding; non-string key | `P1` |
| missing/unknown `randomization_mode` | `P2` |
| any extra or missing key; exact-mode seed field present; MC-mode `exact_support_size` present | `P3` |
| wrong schema version / profile / malformed design id | `P4`, `P5`, `P6` |
| wrong JSON type; `bool` where an integer is required | `P7` |
| malformed digest grammar | `P8` |
| negative `K`; mode/`K` inconsistency | `P9` |
| wrong statistic id | `P10` |
| `exact_support_size != 2 ** K` | `P11` |
| wrong MC constant literal | `P12` |
| malformed `seed_hex` (length, case, prefix, non-hex) | `P13` |
| empty `numpy_version`; non-positive `M` | `P14` |
| malformed timestamp | `P15` |
| `generated_at` after `created_at` | `P16` |
| `self_digest` mismatch | `P17` |
| registration missing/unverifiable | `P18` |
| wrong registration binding, design, mode, `K`, statistic, or `M` | `P19`–`P24` |

Failures raise `McProvenanceIntegrityError` (§10.2); a duplicate **write** raises `DuplicateMcProvenanceError`.

`MC_PROVENANCE_LOADER_ORDER_FROZEN: YES.`

---

## 12. `AssignmentManifestV1` — the closed schema (closes U-E1)

### 12.1 Exactly these thirteen keys, no more, no fewer

**[SCHEMA — FROZEN]** `schema_version` literal:

```
"AssignmentManifestV1"
```

justified by C1 and H7 exactly as §5 justifies the provenance literal. Top-level key set:

```
schema_version
confirmatory_profile
design_id
final_registration_digest
randomization_mc_provenance_digest
task_order
bits
source_kind
source_api
python_version
generation_started_at
generation_completed_at
self_digest
```

**Exactly thirteen keys.** Count confirmed: 5 identity/chain + 2 assignment content + 3 source/environment provenance + 2 timestamps + 1 self digest = 13. A persisted manifest with a fourteenth key, or missing any one of the thirteen, is malformed and is refused (`A2`). Every one of the thirteen is present in every manifest, in every design, **at every `K` including `K = 0`**. The `.pending` crash-safety reservation of §16.1.1 is an operational file outside the scientific artifact catalog and **adds zero fields to this schema**, which remains exactly thirteen keys.

Frozen literals and derivations:

```
schema_version                     = "AssignmentManifestV1"                    (D)
confirmatory_profile               = "post_phaseP_confirmatory_randomization_v1" (D)
design_id                          = registration_manifest.design_id           (A)
final_registration_digest          = registration_manifest.self_digest         (B)
randomization_mc_provenance_digest = randomization_mc_provenance.self_digest   (B)
task_order                         = sorted distinct task ids (§14)            (C)
bits                               = the K drawn bits (§14)                    (E)
source_kind                        = "PYTHON_SECRETS_RANDBITS"                 (D)
source_api                         = "secrets.randbits"                        (D)
python_version                     = internally captured (§16.3)               (E)
generation_started_at              = internally captured (§15)                 (E)
generation_completed_at            = internally captured (§15)                 (E)
self_digest                        = §5.B.2 over the other twelve keys          (C)
```

`self_digest` is the only same-object digest (C5). Downstream meaning is unchanged:

```
assignment_digest := assignment_manifest.json.self_digest
```

and `assignment_digest` is **never** a second field on this artifact (implementation design §5.B.1).

### 12.2 What the manifest deliberately does **not** carry

Named explicitly so no implementer supplies them. Every one is structurally impossible under `A2`'s exact key set.

- **No `assignment_digest`** — a same-object alias of its own `self_digest` (C5).
- **No `created_at`.** The sealing-metadata role `created_at` plays on the three registration artifacts is played here by `generation_completed_at`, which is captured immediately before `self_digest` and persistence (§15.2 T4′). A third timestamp would be a second name for one instant, would need cross-checking against a value that cannot disagree with it (C4), and is named by no frozen consumer (C7). Implementation design §5.M lists exactly two timestamps for this artifact, and §12's catalog lists none beyond "§5.M fields"; neither names `created_at`.
- **No `registration_state`, `assignment_state`, or lifecycle field** — refused on the identical C7 reasoning as §6.4. `ASSIGNMENT_PERSISTED` is defined by this file's existence and validity.
- **No `K`.** `K` is recoverable two ways — `len(bits)` locally and `registration_manifest.K` upstream — and `A12`/`A22` cross-check them against each other. A third persisted copy would add a source of truth without a consumer (C7).
- **No `randomization_mode`, no `statistic_spec_id`, no `eligibility_manifest_digest`.** All three are reachable through the bound registration manifest, and no frozen consumer of *this* artifact reads them from it. `eligibility_manifest_digest` in particular is Stage C's binding, and §5.B.1's inventory for `assignment_manifest.json` lists exactly three digest fields, of which two are upstream references.
- **No Monte Carlo seed material** — no `seed_hex`, `entropy_bytes`, `source_kind` of the token-bytes family, `seed_encoding`, `rng_library`, `rng_bit_generator`, `numpy_version`, `generated_at`, or `exact_support_size`. All are fields of `randomization_mc_provenance.json`, bound here by `randomization_mc_provenance_digest`. **The assignment source and the Monte-Carlo source are different mechanisms and must never share a field.**
- **No realized execution value** — no `qa_mode`, `observation_status`, `failure_class`, endpoint value, `runtime_snapshot_digest`, or row count. Execution begins one state later.
- **No analysis output** — no p-value, `K_plus`, `T_max`, or interval.
- **No resolved treatment label.** `bits` carries `b_k`; the label is computed at dispatch by `resolve_label(baseline_label, b_k)` (§5.D) and is never persisted here. A persisted label would duplicate a pure function of two already-persisted values and could disagree with it.

`ASSIGNMENT_TOP_LEVEL_SCHEMA_FROZEN: YES.`

---

## 13. Per-field type freeze — `AssignmentManifestV1`

**[SCHEMA — FROZEN]** Two fields are arrays of scalars; the remaining eleven are strings. There is no nested object anywhere in this artifact (C2 vacuous).

| Field | JSON type | Content rule | Class |
|---|---|---|---|
| `schema_version` | string | exactly `"AssignmentManifestV1"` | D |
| `confirmatory_profile` | string | exactly `"post_phaseP_confirmatory_randomization_v1"` | D |
| `design_id` | string | non-empty; single safe path segment (H4); equals `registration_manifest.design_id`. **[DEFERRED VALUE SELECTION]** | A |
| `final_registration_digest` | string | lowercase 64-char hex; equals `registration_manifest.self_digest` | B |
| `randomization_mc_provenance_digest` | string | lowercase 64-char hex; equals `randomization_mc_provenance.self_digest` | B |
| `task_order` | array of string | possibly empty; every element non-empty; **strictly ascending** (sorted and unique) under §5.B.2 code-point ordering; equals the recomputed registered task order (§14) | C |
| `bits` | array of JSON integer | possibly empty; every element exactly `0` or `1`; **`bool` refused**; `len(bits) == len(task_order)` (§14) | E |
| `source_kind` | string | exactly `"PYTHON_SECRETS_RANDBITS"` | D |
| `source_api` | string | exactly `"secrets.randbits"` | D |
| `python_version` | string | non-empty; verbatim `platform.python_version()` captured at generation (§16.3) | E |
| `generation_started_at` | string | `YYYY-MM-DDTHH:MM:SSZ` (§15); internally captured, never a parameter | E |
| `generation_completed_at` | string | `YYYY-MM-DDTHH:MM:SSZ` (§15); internally captured, never a parameter | E |
| `self_digest` | string | lowercase 64-char hex per §5.B.2, unchanged | C |

**Array canonicalization.** Both arrays preserve registered order; canonicalization never reorders or deduplicates one (§5.B.2). The sorting and uniqueness rules of §14 are **schema-level preconditions applied before canonicalization**, rejected rather than normalized — never canonicalization-time transformations. `task_order` is a **sorted** array under C3; `bits` is a **semantic** (positional) array under C3, its order fixed by `task_order`'s.

---

## 14. `task_order` and `bits` (closes U-E2 and U-E3)

### 14.1 The representation — parallel arrays, and the choice is made

**[SCHEMA — FROZEN]**

```json
"task_order": ["<task id>", "<task id>", "…"],
"bits":       [0, 1, "…"]
```

`task_order` is a JSON array of strings. `bits` is a JSON array of JSON integers. **`bits[i]` is `b_k` for the task `task_order[i]`.**

The alternatives are named and refused, so no implementer re-opens the question: a `{task_id: bit}` **object** (loses the frozen sorted draw order as a persisted, checkable property, and makes the draw sequence unrecoverable from the artifact); an **array of records** `[{"task_id": …, "bit": …}]` (three keys per task where two parallel scalars suffice, and it invites a per-position variant that §5.M forbids); a **packed bit string** `"0110"` (not a JSON integer per §5.B.2, and it silently admits any character in a position where only `0` and `1` are meaningful).

Parallel arrays are chosen because they persist, in the artifact itself and in checkable form, exactly the two facts implementation design §5.M freezes: *which* tasks were drawn for, and in *what order* `draw_bit()` was called. `task_order[i]` is the `i`-th call; `bits[i]` is its result.

### 14.2 The exact relationship, cover, and ordering

**[SCHEMA — FROZEN]** Let `RTO` (registered task order) be:

```
RTO = sorted( { position.task_id : position ∈ registration_manifest.confirmatory_positions } )
```

ascending under ordinary Unicode code-point ordering, exactly the ordering `sort_keys=True` exercises (§5.B.2), over the **distinct** `task_id` values. Then:

```
task_order == RTO                                          exactly, element for element
len(task_order) == len(bits) == registration_manifest.K
```

Consequences, each individually refused when violated:

- **No missing task.** Every registered confirmatory task appears in `task_order`.
- **No extra task.** No `task_id` appears that is not a registered confirmatory `task_id`. A descriptive-only position's `task_id` does not qualify: `RTO` is built from `confirmatory_positions` only.
- **No duplicate task.** `task_order` is strictly ascending, so uniqueness is implied and separately checked (`A10`).
- **No alternate order.** Any permutation of the correct element set is refused. There is no "implementation may choose" ordering here (C3).

This is the frozen `K` of Stage C — `K = |{ position.task_id : position ∈ confirmatory_positions }|` (Stage-C clarification §15) — reappearing as the cover rule. The two definitions are the same expression, which is why `A21` and `A22` can cross-check a persisted artifact against the registration without a second notion of `K` existing anywhere.

**The loader recomputes `RTO` and compares; it never sorts, repairs, or deduplicates persisted input** (C4, and §5.B.2's rule that ordering is a precondition, not a transformation). A persisted `task_order` that is merely *unsorted* is refused at `A10` before the cover comparison is even reached — the loader does not sort it and then find it correct.

### 14.3 Bit domain — integers, and `bool` is refused

**[SCHEMA — FROZEN]** Every element of `bits` is:

- a **JSON integer**, never a string: `"0"` and `"1"` are refused (§5.B.2: integer-valued fields "remain ordinary JSON integers, never strings");
- exactly `0` or `1`: `2`, `-1`, `0.0`, and `null` are refused;
- **not a `bool`**: `true` and `false` are refused **even though `bool` is a subclass of `int` in Python and `True == 1`**.

The `bool` exclusion is stated explicitly because it is the one case a naive `isinstance(value, int)` check silently admits, and because it is not merely pedantic: `True` serializes as JSON `true`, which changes the canonical bytes and therefore the `self_digest` and the downstream `assignment_digest`. H5 records that Work Unit 1 already reached and implemented this exact reading for its own integer fields; `A11` applies the same rule to `bits`.

`b_k ∈ {0, 1}` is design decision §4.D's own domain, restated in the persisted representation without change: `b_k = 0` means every position in task `k` keeps the label `S_k` gives it; `b_k = 1` means every position takes the complement. The mapping from bit to label remains `resolve_label`'s (§5.D) and is not duplicated here.

### 14.4 `K = 0` — legal, and exactly what it produces

**[SCHEMA — FROZEN]** `K = 0` is legal, exactly to the extent Stage-C clarification §8.3 and §15 already freeze it (`K = 0` yields `randomization_mode = "EXACT_ENUMERATION"` with `randomization_mc_samples = null`, like every other `K <= 16`). Its Work Unit 4 consequences:

```
task_order = []
bits       = []
```

- **`draw_bit()` is called zero times.** `secrets.randbits` is not called at all. §5.M's "exactly once per confirmatory task cluster, `K` total calls" is satisfied by `K = 0` calls; it is not a floor of one.
- **`assignment_manifest.json` is still produced.** `ASSIGNMENT_PERSISTED` remains a required lifecycle state at every `K` (implementation design §6 admits no path around it), so the artifact is written with both arrays empty and all other eleven keys present and populated exactly as at any other `K`.
- **`randomization_mc_provenance.json` is still produced**, on the exact branch, with `exact_support_size = 2 ** 0 = 1` — the value Stage-C clarification §8.3 item 4 already names for this case.
- **Both timestamps still exist** and are captured normally (§15.2).
- The manifest still binds both upstream digests and still validates `A1`–`A23` in full.

**Refusing `K = 0` is not permitted.** A `K = 0` design is a registration with no confirmatory positions — legal at Stage C, and the assignment layer is not the place to re-litigate a matrix Stage C sealed. The artifact records, truthfully, that zero bits were drawn because zero tasks were registered.

`ASSIGNMENT_CONTENT_REPRESENTATION_FROZEN: YES.`
`K_ZERO_BEHAVIOR_FROZEN: YES.`

---

## 15. Assignment timestamps (closes U-E4)

### 15.1 The two fields

**[SCHEMA — FROZEN]** `generation_started_at` and `generation_completed_at` are whole-second UTC instants with a mandatory `Z` designator, rendered under the chain grammar `YYYY-MM-DDTHH:MM:SSZ` — the identical grammar as every other timestamp in the chain, so one rule and one validator serve all six artifacts.

### 15.2 Capture contract — frozen

| # | Rule |
|---|---|
| **T1′** | Both are captured internally by the assignment operation, **exactly once each**, per invocation. |
| **T2′** | **The caller must not supply either.** The operation exposes no timestamp parameter, no clock parameter, no as-of parameter, no time-source injection, and no override of any name (§19). |
| **T3′** | Whole-second UTC-`Z`, truncated by the capture itself at the point of capture (H6's existing `_capture_created_at()` pattern). |
| **T4′** | Capture points, ordered: `generation_started_at` is captured **once, immediately before the draw loop begins** — after every prerequisite check of §16.1 steps 1–7 has passed **and after the durable `.pending` reservation of step 8 exists**, so a refused generation captures nothing. `generation_completed_at` is captured **once, immediately after all `K` bits have been obtained**, and **strictly before `self_digest` is computed** and **strictly before the manifest is published at its final pathname**. |
| **T5′** | Both are fields of `assignment_manifest.json` and are therefore inside the `self_digest` preimage. |
| **T6′** | **At `K = 0` both still exist and are still captured**, bracketing an empty draw loop. They will ordinarily be equal, which T7′ permits. |
| **T7′** | Neither is a cross-artifact **equality** invariant. No rule compares either for equality against any other artifact's timestamp, and none may be added. |

### 15.3 Ordering — non-strict (C8)

**[SCHEMA — FROZEN]**

```
generation_started_at <= generation_completed_at                              (A14)
randomization_mc_provenance.created_at <= generation_started_at               (A23)
```

**Both non-strict, for the reason C8 and §8.3 give.** At whole-second resolution `generation_started_at == generation_completed_at` is the *normal* case, not an anomaly: drawing `K <= 16` bits from `secrets.randbits(1)` completes in microseconds, and at `K = 0` the loop is empty. A strict `<` on `A14` would refuse essentially every honest small-`K` assignment. Likewise the provenance file, persisted moments earlier by the immediately preceding operation, will routinely carry the same UTC second as `generation_started_at`, so `A23` is non-strict too.

**Structure is the ordering proof** (§8.3): the state machine forbids reaching `ASSIGNMENT_PERSISTED` without passing `MC_PROVENANCE_PERSISTED`; §16.1 step 2 refuses to proceed unless the provenance artifact already exists and validates; and the draw is indivisible from publication (§16.1, §16.1.1). The timestamp relations corroborate; they do not carry the guarantee.

**No execution-row timestamp is invented here.** The relation between assignment generation and the first confirmatory execution is enforced structurally by implementation design §6 (`ASSIGNMENT_PERSISTED` precedes `EXECUTION_IN_PROGRESS`) and by `AssignmentNotPersistedError`. Whatever timestamp the already-frozen execution-row contract provides is what any later temporal cross-check uses. **This document adds no field to the row contract and names no row timestamp**, as U-E4's scope requires.

`ASSIGNMENT_TIMESTAMP_CONTRACT_FROZEN: YES.`

---

## 16. Assignment draw-persist boundary, `python_version`, and integrity errors (closes U-E5)

### 16.1 One indivisible public operation

**[SCHEMA — FROZEN]** Production bit drawing and immutable persistence form **one public operation**, in exactly the sense of §10.1. **No production public API returns an inspectable bit vector before the manifest is persisted.**

The threat is the same one §10.1 forecloses, and here it is sharper: `DuplicateAssignmentError` fires only on a *second persisted* manifest, so a caller able to draw `K` bits into memory, look at them, and discard them could redraw indefinitely and persist only the vector it preferred — defeating design decision §4.F's `P(b) = 2^{-K}` uniformity claim while leaving the persisted artifact perfectly well-formed and the duplicate refusal never triggered. Only the absence of the interface prevents it.

**Frozen operation sequence**, given only `(confirmatory_root, design_id)`:

```
 1. Load and revalidate the frozen registration chain from disk (F1-F37).
 2. Load randomization_mc_provenance.json from disk and validate P1-P24.
 3. Verify provenance.final_registration_digest == registration_manifest.self_digest.
 4. Verify provenance mode / K / statistic_spec_id / M against the registration
    manifest (P21-P24).  Absent, corrupt, wrong-mode, or wrongly bound provenance:
    refuse here — before any bit is drawn.
 5. Refuse if assignment_manifest.json already exists for this design_id
    (DuplicateAssignmentError).  This check precedes every draw.
 6. Refuse if assignment_manifest.json.pending exists while the final path does
    NOT (AssignmentIntegrityError, §16.1.1 R1).  This check precedes every draw.
 7. Derive task_order = RTO from registration_manifest.confirmatory_positions (§14.2).
 8. Exclusive-create the .pending reservation and make it DURABLE (§16.1.1 R2, R3).
    Nothing has been drawn yet.  If the platform cannot provide the required
    durable reservation semantics, fail HERE, before any bit exists.
 9. Capture generation_started_at.
10. Call SecretsAssignmentRandomSource.draw_bit() exactly K times, in task_order
    order — once per task, never once per position, model, provider, or repetition.
11. Capture generation_completed_at.
12. Construct the complete thirteen-key manifest.
13. Compute self_digest per §5.B.2, and produce the COMPLETE canonical bytes,
    including self_digest and the one presentation LF, in memory.
14. Write those complete bytes into the .pending staging file and durably flush
    them (§16.1.1 R4).
15. Atomically create the FINAL directory entry under create-if-absent /
    no-clobber semantics (§16.1.1 R5).
16. DURABLY SYNCHRONIZE the filesystem metadata containing that new FINAL
    directory entry (§16.1.1 R5'). The link is NOT durably published merely
    because the create call returned.  If those semantics cannot be
    established, FAIL CLOSED and RETAIN .pending.  Successful durable
    synchronization is the instant ASSIGNMENT_PERSISTED begins.
17. Only now may the .pending name be unlinked (§16.1.1 R6).  Failure here
    never invalidates the already-published artifact.
18. Return only the already-published, already-validated manifest.
```

Steps 2–4 are the concrete realization of implementation design §6's refusal row and of §5.M's "occurs after `randomization_mc_provenance.json` is persisted". Note their position: **the provenance gate closes before step 10 draws anything**, so a bad chain never causes bits to be drawn at all.

**Failure after bits are drawn.** If any step after step 10 fails, the operation **does not redraw, does not retry in a way that acquires new bits, and does not silently regenerate**. It fails. Recovery is §5.M's already-frozen rule verbatim: a missing or corrupt assignment "is a hard refusal, requiring explicit human re-authorization under the abandon-and-recreate rule of §5.A, never an automatic retry."

### 16.1.1 Atomic no-clobber publication and the crash-safety reservation — frozen

**[SCHEMA — FROZEN]** **Exclusive create is not atomic publication, and this document does not claim it is.** `open("xb")` on the final pathname makes the *directory entry* appear before the *content* is written, so a crash mid-write leaves a file that is present at the scientific pathname while holding partial bytes. That satisfies neither half of implementation design §5.M's "writes `assignment_manifest.json` atomically". The correction below is what discharges that frozen requirement; the earlier reliance on exclusive create alone did not, and is superseded.

Two properties are required, and neither implies the other:

> **(A) Atomic, durable publication.** `assignment_manifest.json` becomes visible at its **final** pathname only after the complete canonical bytes have been produced and durably staged; there is no observable instant at which the final pathname exists holding partial content. Publication is complete only once the **new final directory entry is itself durable**, not merely once the create call returned.
>
> **(B) Durable no-redraw evidence, with no gap.** Once a production assignment-generation attempt has been *reserved*, a crash leaves durable on-disk evidence that prevents any later **automatic** redraw — **at every instant**, including the window between creating the final entry and cleaning up the reservation. At no point may a crash leave *neither* the final artifact nor the reservation durable.

**Paths, frozen.**

```
final scientific artifact:    results/confirmatory/<design_id>/assignment_manifest.json
operational reservation:      results/confirmatory/<design_id>/assignment_manifest.json.pending
```

| # | Rule |
|---|---|
| **R1** | **Pre-draw gate.** Before `generation_started_at` and before **any** `secrets.randbits` call: if the final path exists → `DuplicateAssignmentError`; if `.pending` exists while the final path does **not** → hard refusal with `AssignmentIntegrityError`, **no bit is drawn**, and the design requires the already-frozen human re-authorization / new-`design_id` path (§5.A). A stale `.pending` is never cleaned up automatically, never ignored, and never treated as a resumable state. |
| **R2** | **Reserve first.** The `.pending` path is created with an **exclusive create**. Its initial content is the fixed implementation marker `ASSIGNMENT_GENERATION_RESERVED_V1` followed by one LF. The marker carries no scientific data, no digest, and no `self_digest`. |
| **R3** | **Durability before drawing.** The reservation is flushed and synced to durable storage as the platform requires **before** step 9's timestamp capture and step 10's first draw. **If the implementation cannot provide the required durable reservation semantics on its configured filesystem, it fails at this point** — before any bit exists — rather than proceeding with a weaker guarantee. |
| **R4** | **Stage complete bytes.** The complete canonical bytes of the finished manifest (including `self_digest` and the single presentation LF) are written into the `.pending` file and durably flushed. A crash during this staging write leaves `.pending` present and the final path absent; on restart `R1` refuses, and the partial staged content is **never** interpreted as a manifest by anything. |
| **R5** | **Atomic no-clobber creation of the final entry.** The staged, already-complete file is published to the final pathname by an operation that creates the final directory entry **atomically** and **fails if the final path already exists**. The reference primitive is `os.link(pending_path, final_path)` on a same-filesystem path: the new directory entry appears complete or not at all, and it refuses rather than overwrites. **`os.replace()` is forbidden** — replacement/overwrite semantics are exactly what §20.2 prohibits. **Streaming bytes directly into the final pathname is forbidden.** If the platform or filesystem cannot provide an equivalent atomic no-clobber publication primitive, the operation **fails closed** rather than weakening the contract. **A successful return from the create call is *not* durable publication** — `R5′` is what makes it so, and `.pending` may not be touched until `R5′` has succeeded. |
| **R5′** | **Durable publication of the final directory entry — required before any cleanup.** After `R5` creates the final entry and **before** `.pending` may be unlinked, the implementation **must durably synchronize the filesystem metadata containing the newly-created final directory entry**. Until that synchronization succeeds, the final link is **not** considered durably published, and `ASSIGNMENT_PERSISTED` has **not** begun. **If that synchronization is unsupported, cannot be established on the configured filesystem, or fails: fail closed and RETAIN `.pending`** — do not redraw, do not delete `.pending`, do not automatically retry generation (`R7`). This closes the window in which a crash between `R5` and cleanup could otherwise leave **neither** the final entry nor the reservation durable, which would have permitted a redraw. |
| **R6** | **Cleanup is strictly ordered, and non-authoritative.** The ordering is frozen as: **atomic final link (`R5`) → durable final-directory synchronization (`R5′`) → optional `.pending` unlink (`R6`)**. **Unlinking `.pending` before `R5′` has succeeded is forbidden.** Once `R5′` has succeeded, unlinking is optional and its failure **does not invalidate an already-valid final artifact**. If both the final path and `.pending` exist after a crash, **the final artifact is authoritative and no redraw occurs** — `R1`'s first clause fires (`DuplicateAssignmentError`), not its second; `.pending` is then operational residue only, removable solely under this rule's ordering. |
| **R7** | **No automatic recovery after reservation.** Any failure after the durable reservation exists and before **durable** publication has succeeded (`R5′`): **must not** delete the reservation in any way that permits a redraw; **must not** call `secrets.randbits` again; **must not** retry generation. The design is left requiring human re-authorization and a new `design_id`. |

**`R5′` portability — the semantic property is frozen, not one primitive.** Python offers **no single portable directory-metadata-durability call**, and this document does not pretend otherwise. What is frozen is the required **semantic property**:

> *durably synchronize the filesystem metadata containing the newly-created final directory entry, before `.pending` cleanup.*

A **platform-specific implementation may be required**, and that is expected rather than a defect:

- On **POSIX-like** systems this may be realized by opening the parent directory and `fsync`-ing that directory descriptor after the link is created.
- On **Windows/NTFS** the implementation must use an available platform or filesystem mechanism providing the required metadata-durability semantics; the POSIX directory-`fsync` idiom is not assumed to exist or to mean the same thing.

**If the implementation cannot establish those semantics on its configured platform and filesystem, it fails closed and retains `.pending`** (`R5′`, `R7`). **This is not a "best effort" obligation** and must never be weakened into one: an implementation that cannot prove final-entry durability does not proceed to cleanup, and must not silently skip the step and unlink anyway. `R6`'s tolerance of failure applies **only** to the unlink itself, **after** `R5′` has already succeeded — never to `R5′`.

**This is deliberately conservative.** A crash after the reservation but *before the first bit* burns that `design_id` — the reservation cannot distinguish "crashed before drawing" from "crashed after drawing", and it must not guess. Burning a `design_id` is cheap; an undetectable second randomization draw is not. Preventing the latter is the higher-order invariant, and design decision §4.F's `P(b) = 2^{-K}` uniformity claim is what it protects. The same asymmetry governs `R5′`: retaining a `.pending` that a later human must clear is cheap; a crash window that leaves neither name durable, and therefore silently re-arms a redraw, is not.

**What `.pending` is, and is not.**

- It is **operational crash-safety evidence only**, at the implementation layer.
- It is **not a seventh scientific artifact**. It is outside the six-artifact catalog of implementation design §5.B and §12, outside the digest chain of §5.B.1 and §5.B.3, and carries no `self_digest`, no `schema_version`, and no field of `AssignmentManifestV1`.
- Its presence **never** means `ASSIGNMENT_PERSISTED`. **Only a fully validated final `assignment_manifest.json` does** (§6 of the implementation design; `A1`–`A23` here).
- **No loader, analyzer, runner, or resume path ever reads `.pending` as scientific input**, and no digest anywhere is ever computed over it.
- **It adds zero fields to `AssignmentManifestV1`**, which remains exactly thirteen keys (§12.1).

### 16.2 Production provenance literals

```
source_kind = "PYTHON_SECRETS_RANDBITS"
source_api  = "secrets.randbits"
```

These are truth claims about how the persisted bits were obtained, not decorations. §18 makes it structurally impossible for a manifest to carry them while its bits came from anywhere else.

### 16.3 `python_version` — captured, and deliberately not a cross-artifact invariant

**[SCHEMA — FROZEN]** `python_version` is:

- **captured internally** from `platform.python_version()` in the generating process (e.g. `"3.11.9"`);
- persisted **verbatim** as a non-empty JSON string, with no parsing or normalization;
- **never caller-supplied** — no parameter of any name accepts it (T2′, §19).

**It is not required to equal `RuntimeSnapshotV1.python_version`, and no rule compares them.** The two record different things: §5.I.1's `python_version` is part of the **runtime identity** compared across the three execution capture points, describing the interpreter that *executes positions*; this field is **draw provenance**, describing the interpreter that *drew the bits* in the orchestration process. Requiring equality would mint a new cross-artifact equality invariant that no frozen consumer names (C7), and would couple assignment generation to the execution runtime freeze in a way §5.M does not require and §5.I does not contemplate. This is the same deliberate non-invariance Stage-C clarification §4.4.1 T7 establishes for `created_at`, applied to an environment value.

### 16.4 `AssignmentIntegrityError` — the trigger set, stated completely

**[SCHEMA — FROZEN]** Implementation design §11 names `AssignmentIntegrityError` (`ASSIGNMENT_DIGEST_MISMATCH`) and gives it two triggers: the manifest's `self_digest` failing to verify, and its `final_registration_digest` not matching the live final registration's `self_digest`. Implementation design §6's transition row separately **requires** that `randomization_mc_provenance_digest` also be checked against the live upstream `self_digest` — a check with no error assigned to it anywhere.

Resolved by **assigning the existing error**, not by minting a new one.

**The one-surface rule — frozen.** The public assignment entry points have **exactly one** fail-closed exception surface for every non-duplicate assignment-integrity failure:

> **`AssignmentIntegrityError`.** Every rule `A1`–`A23` that fails, at any tier, raises `AssignmentIntegrityError`. There is no second public exception choice, no rule with unspecified public error behavior, and **no dependency-layer exception that escapes the public assignment surface unwrapped.**

`AssignmentIntegrityError` therefore covers, exhaustively:

1. **raw file / JSON / top-level local parsing failure** (`A1`) — bad encoding, unparseable bytes, a non-object payload, or a non-string key;
2. malformed assignment artifact: key set, literals, `design_id` grammar, and JSON types (`A2`–`A6`);
3. malformed digest grammar and wrong production source literals (`A7`, `A8`, `A9`);
4. `task_order` / `bits` domain, ordering, uniqueness, length, and timestamp violations (`A10`–`A14`);
5. the manifest's own `self_digest` failing to verify (`A15`) — §11's first trigger, unchanged;
6. **failure while loading or validating the bound final-registration chain** (`A16`) — the underlying registration-layer exception is **caught and re-raised as `AssignmentIntegrityError` `from` it**;
7. `final_registration_digest` not matching `registration_manifest.self_digest` (`A17`) — §11's second trigger, unchanged — and `design_id` not matching the bound registration manifest (`A18`);
8. **failure while loading or validating the required `randomization_mc_provenance.json`** (`A19`) — the underlying `McProvenanceIntegrityError` is **caught and re-raised as `AssignmentIntegrityError` `from` it**;
9. **`randomization_mc_provenance_digest` not matching `randomization_mc_provenance.self_digest`** (`A20`) — §6's required check, now assigned;
10. task-cover, bit-count, and cross-artifact temporal violations (`A21`–`A23`);
11. **an incomplete prior assignment attempt represented by `.pending` while the final path is absent** (§16.1.1 `R1`, second clause).

**Wrapping, not leaking — and chaining, not erasing.** A caller invoking the **provenance** loader directly may receive `McProvenanceIntegrityError`; that is its own public surface (§11). A caller invoking an **assignment** entry point — the manifest loader, or the generation operation whose steps 1–4 traverse the same dependencies — always receives `AssignmentIntegrityError` for a broken assignment dependency chain. **`McProvenanceIntegrityError` never escapes a public assignment entry point**, and neither does any registration-layer exception. In every wrapping case the original exception is preserved as the cause (`raise AssignmentIntegrityError(...) from error`): the underlying reason is **never silently erased**, only re-surfaced under the one error type an assignment caller must handle.

Why one surface: a caller of the assignment layer holds an assignment-layer contract. Requiring it to also catch every exception type that any upstream layer might raise — now or after a future upstream refactor — would make the fail-closed boundary depend on transitive implementation detail, which is exactly the kind of leak this chain refuses everywhere else.

This is a clarification of an already-frozen error's scope, not an amendment: §11's trigger sentence enumerated the two checks §5.M had spelled out, and §6 required a third that §11 simply did not reach. Nothing in §11 assigns any of these checks to a different error, so no frozen assignment is overridden, and no additional public assignment exception is minted.

`DuplicateAssignmentError` remains, unchanged and reserved for exactly one condition: a second production persistence attempt against a `design_id` whose **final** `assignment_manifest.json` path already exists (§16.1.1 `R1`, first clause). It is never raised for a `.pending` reservation, which is `AssignmentIntegrityError` per trigger 11.

`ASSIGNMENT_RANDOMNESS_PERSISTENCE_BOUNDARY_FROZEN: YES.`

---

## 17. Assignment loader — `A1`–`A23`, first-failure order

**[SCHEMA — FROZEN]** Applied **in the numbered order**, aborting on the **first** failure, with no normalization, repair, sorting, deduplication, default-filling, warning-only path, or partial acceptance. First-failure order is contractually observable. The same layering rule as §11 holds: every local check precedes `self_digest` verification, which precedes every upstream load and binding check.

### 17.1 Tier 1 — local

| # | Rule |
|---|---|
| **A1** | File envelope: at most one trailing `\n` stripped; UTF-8; parses to a JSON **object**; string keys only, at every depth. |
| **A2** | Top-level key set is **exactly** the thirteen of §12.1 — no missing key, no extra key. This is what structurally forbids `created_at`, `assignment_digest`, `K`, `randomization_mode`, every seed field, every execution field, and every analysis field from ever loading. |
| **A3** | `schema_version` is exactly `"AssignmentManifestV1"`. |
| **A4** | `confirmatory_profile` is exactly `"post_phaseP_confirmatory_randomization_v1"`. |
| **A5** | `design_id` is a non-empty string and a single safe path segment (H4). |
| **A6** | Every field has the JSON type §13 assigns it: `task_order` an array, `bits` an array, the other eleven strings. |
| **A7** | `final_registration_digest`, `randomization_mc_provenance_digest`, and `self_digest` each match `^[0-9a-f]{64}$`. |
| **A8** | `source_kind` is exactly `"PYTHON_SECRETS_RANDBITS"`; `source_api` is exactly `"secrets.randbits"`. |
| **A9** | `python_version` is a non-empty string. |
| **A10** | Every element of `task_order` is a non-empty string, and the array is **strictly ascending** under code-point ordering — which refuses an unsorted array and a duplicated task at the same rule. Nothing is sorted or deduplicated on the caller's behalf. |
| **A11** | Every element of `bits` is a **JSON integer** — **`bool` refused** (§14.3, H5) — and is exactly `0` or `1`. |
| **A12** | `len(bits) == len(task_order)`. |
| **A13** | `generation_started_at` and `generation_completed_at` each match `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` and are real instants. |
| **A14** | `generation_started_at <= generation_completed_at`, non-strict (§15.3, C8). |
| **A15** | `self_digest` verifies per §5.B.2. |

### 17.2 Tier 2 — requires the bound registration manifest

| # | Rule |
|---|---|
| **A16** | `registration_manifest.json` for this `design_id` exists, loads, and validates through `F1`–`F37` (H9). **Any registration-layer exception raised here is caught and re-raised as `AssignmentIntegrityError` `from` it** (§16.4). |
| **A17** | `final_registration_digest` equals `registration_manifest.self_digest`. |
| **A18** | `design_id` equals `registration_manifest.design_id`. |

### 17.3 Tier 3 — requires the bound Monte-Carlo provenance artifact

| # | Rule |
|---|---|
| **A19** | `randomization_mc_provenance.json` for this `design_id` exists, loads, and validates through `P1`–`P24` — including its own binding to the same registration manifest. **The `McProvenanceIntegrityError` raised here is caught and re-raised as `AssignmentIntegrityError` `from` it** (§16.4); it never escapes the assignment surface. |
| **A20** | `randomization_mc_provenance_digest` equals `randomization_mc_provenance.self_digest`. |
| **A21** | `task_order` equals the recomputed `RTO` (§14.2) **exactly**, element for element — no missing task, no extra task, no duplicate, no alternate order. |
| **A22** | `len(bits) == registration_manifest.K`. |
| **A23** | `randomization_mc_provenance.created_at <= generation_started_at`, non-strict (§15.3, C8). |

### 17.4 Rejection inventory

| Rejected condition | Rule |
|---|---|
| not an object; bad encoding; unparseable bytes; non-string key | `A1` |
| any extra or missing key; forbidden name present | `A2` |
| wrong schema version / profile / malformed design id | `A3`, `A4`, `A5` |
| wrong JSON type | `A6` |
| malformed digest grammar | `A7` |
| wrong production source literal | `A8` |
| empty `python_version` | `A9` |
| unsorted `task_order`; duplicate task; empty task id | `A10` |
| `bool` bit; bit `2`; string bit; float bit; `null` bit | `A11` |
| `bits` shorter or longer than `task_order` | `A12` |
| malformed timestamp | `A13` |
| `generation_started_at` after `generation_completed_at` | `A14` |
| `self_digest` mismatch | `A15` |
| registration missing / unverifiable / foreign design | `A16`, `A17`, `A18` |
| provenance missing / corrupt / wrongly bound | `A19` |
| wrong `randomization_mc_provenance_digest` | `A20` |
| missing, extra, duplicated, or reordered task vs. the registration | `A21` |
| bit count `!=` registered `K` | `A22` |
| provenance stamped after assignment start | `A23` |
| incomplete prior attempt: `.pending` present, final absent | write-time, §16.1.1 `R1` |
| second production write against an existing **final** assignment path | write-time, §16.1.1 `R1` |

**Public error surface, exact.** Every one of `A1`–`A23` raises **`AssignmentIntegrityError`** — including `A1` (local parse), `A16` (bound registration), and `A19` (bound provenance), the latter two **chained `from`** the underlying registration-layer or `McProvenanceIntegrityError` cause, which is preserved and never erased (§16.4). No other public exception is reachable from the assignment loader, and `McProvenanceIntegrityError` never escapes it. The `.pending`-present-final-absent condition likewise raises `AssignmentIntegrityError`. **`DuplicateAssignmentError` is raised for exactly one condition**: a second production persistence attempt against an existing **final** assignment path (§16.1.1 `R1`, first clause).

`ASSIGNMENT_LOADER_ORDER_FROZEN: YES.`

---

## 18. The deterministic test source — resolved without falsifying production provenance

**[SCHEMA — FROZEN]** This section resolves an explicit tension in the binding text rather than picking a side of it.

**The binding text.** Implementation design §5.M freezes: `DeterministicAssignmentRandomSource` "accepts an explicit, pre-supplied bit sequence for test fixtures only. It is **mandatorily rejected** whenever `confirmatory_profile == "post_phaseP_confirmatory_randomization_v1"` outside of a test context; production assignment generation refuses to proceed if the supplied `AssignmentRandomSource` is a `DeterministicAssignmentRandomSource`." Authorization §7 separately authorizes the deterministic source as a test artifact.

**The tension.** The clause "if the **supplied** `AssignmentRandomSource`" presupposes a parameter through which a source is supplied to production generation. A parameter that exists in order to be refused is still an injection surface: it is exactly the shape that lets a caller reach the randomness of a persisted artifact, and §16.1's whole argument is that such a surface must not exist.

**The resolution — preserve the requirement, remove the surface.**

1. **The public persisting operation accepts no random-source parameter of any kind.** It always constructs `SecretsAssignmentRandomSource` internally (§16.1 step 10, §19).
2. **§5.M's refusal is implemented, not dropped.** The internal draw helper — the function that takes an `AssignmentRandomSource` and returns `K` bits in `task_order` order — performs the isinstance refusal §5.M mandates: presented with a `DeterministicAssignmentRandomSource` on a persisting path under the confirmatory profile, it refuses with `ConfirmatoryAssignmentError`. The check exists and fires exactly as frozen.
3. **The result is strictly stronger than §5.M requires, never weaker.** §5.M demands that a deterministic source *supplied* to production generation be refused. Under this architecture there is no path by which one can be supplied at all, and the refusal remains in place as defence in depth behind that. A requirement of the form "reject X if presented" is satisfied *a fortiori* by an architecture in which X cannot be presented and would be rejected if it were.
4. **`AssignmentRandomSource` keeps its purpose.** The Protocol (§5.M) types the internal draw helper's parameter, and `DeterministicAssignmentRandomSource` is what focused tests pass to that helper — exercising one-bit-per-task, sorted-order, shared-bit, `K = 0`, and exhaustion behavior without touching the persisting operation. This is precisely the scope authorization §7 grants it: a test artifact.
5. **No persisted manifest can misdescribe its source.** Because the persisting operation constructs `SecretsAssignmentRandomSource` itself and accepts no substitute, a persisted `assignment_manifest.json` bearing `source_kind = "PYTHON_SECRETS_RANDBITS"` and `source_api = "secrets.randbits"` is a true claim by construction. There is no path that persists deterministic bits under production provenance literals.
6. **No production-accepted deterministic provenance token is minted.** No `"DETERMINISTIC_TEST_SOURCE"` value of `source_kind`, no test-mode literal, and no alternative production `source_kind` exists. `source_kind` has exactly one legal value on this artifact (§13). A test that wants a persisted artifact uses a synthetic manifest (authorization §7 authorizes synthetic manifests), never a production persistence path fed by a fixture.
7. **Exhaustion is a test-fixture contract.** A `DeterministicAssignmentRandomSource` asked for more bits than its pre-supplied sequence holds raises `ConfirmatoryAssignmentError`. It is test-only, so this needs no further taxonomy.

**Fail-closed for production use, stated once:** if any future code path were to present a non-`SecretsAssignmentRandomSource` to a persisting assignment operation, that path refuses. It does not warn, does not fall back to secrets, and does not persist.

`PRODUCTION_RANDOM_SOURCE_INJECTION_FORBIDDEN: YES.`

---

## 19. Public API architecture — the minimum that must be frozen

**[SCHEMA — FROZEN]** The exact Python spelling of every helper is **not** frozen here, and no implementer is asked to match a name. What is frozen is only what would otherwise be a security-relevant or interoperability-relevant architecture choice:

| # | Frozen |
|---|---|
| **API-1** | The production Monte-Carlo-provenance operation performs **generate + exclusive persistence as one operation** (§10.1). No public API exposes an unpersisted seed. |
| **API-2** | The production assignment operation performs **draw + durably reserved, staged, atomically published, durably linked persistence as one operation** (§16.1, §16.1.1). It returns only after `R5′` has made the final directory entry durable. No public API exposes an unpersisted bit vector, and no public API exposes the `.pending` reservation as a result, a return value, or a resumable handle. |
| **API-3** | **Neither production operation accepts any value input**: no seed, seed byte, `seed_hex`, seed integer, entropy source, bit, bit vector, `M`, NumPy version, Python version, timestamp, clock, time source, as-of value, or random source. Their entire input is the address of the design. This is what makes §3's "no caller-choice class" structural rather than merely asserted. |
| **API-4** | Both operations are addressed by **`(confirmatory_root, design_id)`** and **revalidate the required upstream artifacts from disk**, rather than trusting a caller-constructed record. If a convenience typed parameter is also accepted, it is cross-checked against the on-disk artifact and can never substitute for loading it (H9 makes this necessary in any case: a Stage-C manifest is never *accepted* without its two bound upstream artifacts). |
| **API-5** | Path helpers follow the existing safe-`design_id` / `confirmatory_root` containment discipline of Work Units 1–3 (H4), producing `<confirmatory_root>/<design_id>/randomization_mc_provenance.json` and `<confirmatory_root>/<design_id>/assignment_manifest.json`. The `.pending` reservation path (§16.1.1) is derived from the assignment path under the identical containment discipline, is confined to the same `design_id` directory and the same filesystem, and is **not** a scientific artifact path. |
| **API-6** | Loaders **fail closed and never normalize** (§11, §17). A loader parses, verifies, and rebuilds; it never repairs a malformed artifact, never normalizes an invalid one into validity, and never reserializes around a mismatch. |
| **API-7** | Persisted **semantic** JSON may be recanonicalized under the already-frozen §5.B.2 reader semantics. **No raw-byte equality gate is added** for either artifact: a semantically equivalent noncanonical input that parses to the same authenticated object is not, by itself, a failure condition — exactly as Stage-A clarification §12, Stage-B clarification §16, and Stage-C clarification §17.1 already froze. |
| **API-8** | `resolve_label` and `complement` are unchanged from implementation design §5.D, including the exact signature `resolve_label(baseline_label: QAMode, b_k: int) -> QAMode`. This document restates them for completeness of the module surface and changes nothing about them. |
| **API-9** | The module error hierarchy is §10.2's. No second error taxonomy is minted, and `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` remains analysis-scoped. |

Everything else about the module's Python surface — function names, keyword-only conventions, dataclass versus `TypedDict`, constant spellings, `__all__` ordering — is ordinary local implementation choice, follows the Work Unit 1–3 precedent where a precedent exists, and is deliberately **not** frozen here.

`PUBLIC_API_ARCHITECTURE_COMPLETE: YES.`

---

## 20. Immutability, canonical JSON, and write prerequisites

### 20.1 Canonical JSON and `self_digest` — reused by reference, unamended

**The canonical algorithm is not modified.** Implementation design §5.B.2 applies to both artifacts exactly as written, realized once by Work Unit 1 (H2) and reused here without a second implementation:

- canonical bytes are `json.dumps(object_without_self_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` encoded UTF-8;
- object keys sorted by ordinary Unicode code-point ordering; string keys only;
- arrays preserve registered order — §14's sorting and uniqueness rules are schema-level preconditions applied **before** canonicalization, never canonicalization-time transformations;
- `NaN` / `Infinity` / `-Infinity` forbidden; every integer field is an ordinary JSON integer, never a string; **no field of either artifact is a real number**, so §5.B.2's canonical-decimal-string rule has no member in Work Unit 4;
- `self_digest` is SHA-256, lowercase hex, over the canonical bytes of the object with **only** `self_digest` removed;
- the persisted file is the canonical JSON *including* the computed `self_digest`, reserialized under the identical algorithm, plus exactly one trailing LF that is not part of any digest; a reader strips at most one trailing `\n` first;
- verification: read bytes → strip at most one trailing LF → parse → extract claimed `self_digest` → remove it → recanonicalize → recompute SHA-256 → compare. Mismatch fails closed.

Neither artifact stores a same-object digest alias (C5): `randomization_mc_provenance.json` does not store `randomization_mc_provenance_digest`, and `assignment_manifest.json` does not store `assignment_digest`.

### 20.2 Write-once immutability

**[SCHEMA — FROZEN]** Both artifacts, at

```
results/confirmatory/<design_id>/randomization_mc_provenance.json
results/confirmatory/<design_id>/assignment_manifest.json
```

are:

- written under the existing safe-`design_id` path discipline, with the resolved path required to stay inside `confirmatory_root` (H4);
- **write-once** — `randomization_mc_provenance.json` via an **exclusive create** (H3); `assignment_manifest.json` via the **reserve → stage → atomically publish** protocol of §16.1.1, because §5.M freezes an atomicity requirement for that artifact that exclusive create alone does not satisfy;
- **never overwritten, replaced, truncated, or edited in place**, for any reason, at any later state;
- **never regenerated automatically** — no seed re-draw, no bit re-draw, no automatic retry, ever;
- one per `design_id`, in exactly one shape (`randomization_mc_provenance.json` in exactly one of its two tagged shapes).

A replacement requires the abandon-and-recreate rule of §5.A: the whole design is abandoned as a unit and recreated under a **new** `design_id`, with the abandoned artifacts retained for audit and never reused.

Any attempted in-place edit fails closed by construction: either `self_digest` no longer verifies (`P17` / `A15`), or, if `self_digest` was recomputed, every downstream reference breaks at the referencing artifact — an edited provenance file breaks `assignment_manifest.json`'s `randomization_mc_provenance_digest` (`A20`), and an edited assignment manifest breaks `final_analysis_manifest.json`'s `assignment_digest` (§5.B.3).

### 20.3 Write prerequisites — construction-time, distinct from loader rules

**[SCHEMA — FROZEN]** Stated separately because historical wall-clock truth and random-source provenance **cannot be proven by a loader alone** (§8.3).

| # | Rule |
|---|---|
| **W1** | **Full contract before publication.** The complete `P1`–`P24` (provenance) or `A1`–`A23` (assignment) contract runs against the sealed object *before* the artifact is published at its final pathname — so an invalid artifact is never published, and construction cannot mint anything a load would refuse. For assignment this check precedes staging (§16.1.1 `R4`); the `.pending` reservation of `R2` is created earlier and deliberately, and is not a scientific artifact (§16.1.1). |
| **W2** | **Provenance write — exclusive create.** `randomization_mc_provenance.json` is written with `open("xb")`. An existing artifact for the `design_id` is refused (`DuplicateMcProvenanceError`) — never replaced, truncated, or edited. **This is exclusive creation, not atomic publication**, and nothing in this document claims otherwise: a crash mid-write leaves a present-but-partial file, which fails `P17` and can never be silently consumed, and which blocks any retry at §10.1 step 3 — so no entropy is ever re-drawn. Implementation design §5.L imposes no atomicity requirement on this artifact; §5.M imposes one on the assignment manifest, which `W2′` discharges. |
| **W2′** | **Assignment write — reserve, stage, atomically publish, make durable, then clean up.** `assignment_manifest.json` follows §16.1.1 `R1`–`R7` in full: pre-draw gate on both the final and `.pending` paths; durable exclusive-create reservation *before* the first draw; complete canonical bytes staged and flushed; atomic **no-clobber** creation of the final entry (`os.link`-class primitive, never `os.replace`, never direct streaming into the final path); **durable synchronization of the filesystem metadata holding that new final entry (`R5′`) — a returned create call is not durable publication**; and only then the optional `.pending` unlink. The order `R5` → `R5′` → `R6` is frozen, and cleanup before `R5′` is forbidden. If final-entry durability cannot be established, the write **fails closed and retains `.pending`**; there is no automatic recovery after reservation (`R7`). An existing final artifact is refused (`DuplicateAssignmentError`) — never replaced, truncated, or edited. |
| **W3** | **Upstream prerequisite.** Provenance requires a validated `registration_manifest.json`; assignment requires both a validated `registration_manifest.json` and a validated `randomization_mc_provenance.json`. There is no path that writes either artifact first. |
| **W4** | **Capture prerequisite.** Every class-E value sealed into the object is the value captured internally by *this* invocation, was not supplied by a caller — the operation exposes no parameter through which it could be (T2, T2′, API-3) — conforms to its frozen grammar, and is present in the object **before** `self_digest` is computed and **before** any byte reaches disk. |
| **W5** | **Source prerequisite.** The bits sealed into an assignment manifest came from `SecretsAssignmentRandomSource` constructed by the operation itself (§18). This is a construction-time guarantee, structural in the interface, and no loader rule claims to verify it after the fact. |

**What a loader can and cannot establish.** `P15`/`P16` and `A13`/`A14`/`A23` are **syntax, type, and consistency validations of persisted timestamps** — nothing more. No rule here asserts that a loader can establish, from the artifacts alone, that a persisted timestamp is the real instant, or that persisted bits really came from `secrets.randbits`. Those guarantees come from `W1`–`W5` plus the digest chain that makes any post-hoc edit detectable. Claiming otherwise would be a guarantee the artifacts cannot support.

---

## 21. Complete artifact skeletons

Shape illustration only, over invented placeholders. **No real provider, model, task, design id, digest, seed, bit, or timestamp appears here or anywhere in this document.** Keys are shown in canonical sorted order. `<64-hex>` marks a lowercase 64-character hex digest.

### 21.1 `randomization_mc_provenance.json` — `EXACT_ENUMERATION` (ten keys)

```json
{
  "K": 2,
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "created_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "design_id": "<deferred value selection>",
  "exact_support_size": 4,
  "final_registration_digest": "<64-hex>",
  "randomization_mode": "EXACT_ENUMERATION",
  "schema_version": "RandomizationMcProvenanceV1",
  "self_digest": "<64-hex>",
  "statistic_spec_id": "confirmatory_task_sign_flip_v1"
}
```

`K = 2 <= 16`, so the mode is `EXACT_ENUMERATION` and `exact_support_size = 2 ** 2 = 4`. **No seed field appears, no entropy API was called, and `generated_at` is absent** — the ten forbidden Monte-Carlo fields are structurally excluded by the exact key set.

### 21.2 `randomization_mc_provenance.json` — `MONTE_CARLO` (nineteen keys)

```json
{
  "K": 20,
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "created_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "design_id": "<deferred value selection>",
  "entropy_bytes": 32,
  "final_registration_digest": "<64-hex>",
  "generated_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "numpy_version": "<captured numpy.__version__>",
  "randomization_mc_samples": "<registered M, deferred>",
  "randomization_mode": "MONTE_CARLO",
  "rng_bit_generator": "PCG64",
  "rng_library": "numpy",
  "schema_version": "RandomizationMcProvenanceV1",
  "seed_encoding": "uint256_big_endian",
  "seed_hex": "<64 lowercase hex characters, deferred>",
  "self_digest": "<64-hex>",
  "source_api": "secrets.token_bytes",
  "source_kind": "PYTHON_SECRETS_TOKEN_BYTES",
  "statistic_spec_id": "confirmatory_task_sign_flip_v1"
}
```

`K = 20 > 16`, so the mode is `MONTE_CARLO`, `randomization_mc_samples` is the registered positive integer `M`, and **`exact_support_size` is absent** (§6.3). `generated_at <= created_at` (§8.3). In a real artifact `randomization_mc_samples` is a JSON integer; the quoted placeholder above marks a deferred value, not a string type.

### 21.3 `assignment_manifest.json` (thirteen keys)

```json
{
  "bits": [0, 1],
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "design_id": "<deferred value selection>",
  "final_registration_digest": "<64-hex>",
  "generation_completed_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "generation_started_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "python_version": "<captured platform.python_version()>",
  "randomization_mc_provenance_digest": "<64-hex>",
  "schema_version": "AssignmentManifestV1",
  "self_digest": "<64-hex>",
  "source_api": "secrets.randbits",
  "source_kind": "PYTHON_SECRETS_RANDBITS",
  "task_order": ["<task id A, deferred>", "<task id B, deferred>"]
}
```

`bits[0]` is `b_k` for `task_order[0]`; `bits[1]` for `task_order[1]`. `task_order` is strictly ascending and equals the recomputed `RTO`; `len(bits) == len(task_order) == registration_manifest.K == 2`. **No `created_at`, no `K`, no `randomization_mode`, no seed material, no resolved label.**

### 21.4 `assignment_manifest.json` at `K = 0` (still thirteen keys)

```json
{
  "bits": [],
  "confirmatory_profile": "post_phaseP_confirmatory_randomization_v1",
  "design_id": "<deferred value selection>",
  "final_registration_digest": "<64-hex>",
  "generation_completed_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "generation_started_at": "<YYYY-MM-DDTHH:MM:SSZ>",
  "python_version": "<captured platform.python_version()>",
  "randomization_mc_provenance_digest": "<64-hex>",
  "schema_version": "AssignmentManifestV1",
  "self_digest": "<64-hex>",
  "source_api": "secrets.randbits",
  "source_kind": "PYTHON_SECRETS_RANDBITS",
  "task_order": []
}
```

Zero draws occurred; `secrets.randbits` was never called; both timestamps exist and are ordinarily equal; the artifact is still written, still binds both upstream digests, and still validates `A1`–`A23` in full (§14.4).

These illustrate the schemas; **they register nothing, generate nothing, and decide nothing.**

---

## 22. Cross-artifact derivation table

Every persisted Work Unit 4 value, with its single source. No value has two sources.

| Artifact | Field | Source | Class | Loader cross-check |
|---|---|---|---|---|
| provenance | `schema_version` | frozen literal §5 | D | `P4` |
| provenance | `confirmatory_profile` | frozen literal | D | `P5` |
| provenance | `design_id` | registration manifest | A | `P6`, `P20` |
| provenance | `final_registration_digest` | registration `self_digest` | B | `P8`, `P19` |
| provenance | `randomization_mode` | registration manifest | A | `P2`, `P9`, `P21` |
| provenance | `created_at` | internal capture | E | `P15`, `P16` |
| provenance | `K` | registration manifest | A | `P7`, `P9`, `P22` |
| provenance | `statistic_spec_id` | frozen literal | D | `P10`, `P23` |
| provenance | `exact_support_size` | `2 ** K` | C | `P11` |
| provenance | `source_kind`/`source_api`/`entropy_bytes`/`seed_encoding`/`rng_library`/`rng_bit_generator` | frozen literals | D | `P12` |
| provenance | `seed_hex` | `token_bytes(32).hex()` | E | `P13` |
| provenance | `numpy_version` | `numpy.__version__` capture | E | `P14` |
| provenance | `randomization_mc_samples` | registered `M` | A | `P14`, `P24` |
| provenance | `generated_at` | internal capture | E | `P15`, `P16` |
| provenance | `self_digest` | §5.B.2 | C | `P17` |
| assignment | `schema_version` | frozen literal §12.1 | D | `A3` |
| assignment | `confirmatory_profile` | frozen literal | D | `A4` |
| assignment | `design_id` | registration manifest | A | `A5`, `A18` |
| assignment | `final_registration_digest` | registration `self_digest` | B | `A7`, `A17` |
| assignment | `randomization_mc_provenance_digest` | provenance `self_digest` | B | `A7`, `A20` |
| assignment | `task_order` | `RTO` from registration positions | C | `A10`, `A21` |
| assignment | `bits` | `K` × `secrets.randbits(1)` | E | `A11`, `A12`, `A22` |
| assignment | `source_kind`/`source_api` | frozen literals | D | `A8` |
| assignment | `python_version` | `platform.python_version()` capture | E | `A9` |
| assignment | `generation_started_at` | internal capture | E | `A13`, `A14`, `A23` |
| assignment | `generation_completed_at` | internal capture | E | `A13`, `A14` |
| assignment | `self_digest` | §5.B.2 | C | `A15` |

**Every row answers NO to "may the caller choose it?"** Class E is not a caller-choice class: each member is produced by the operation itself, unreachable through any parameter (API-3), and never an equality invariant across artifacts (T7, T7′, §16.3).

---

## 23. Adversarial self-check

Every case resolves to exactly one deterministic outcome under §5–§22.

### 23.1 Monte-Carlo provenance

| # | Case | Outcome |
|---|---|---|
| 1 | `K = 0`, exact mode | Artifact written: ten keys, `exact_support_size = 2 ** 0 = 1`, no seed field, no `generated_at`. Accepted. |
| 2 | `K = 16`, exact mode | Ten keys, `exact_support_size = 65536`. `P9` accepts `K <= 16` on this branch. Accepted. |
| 3 | `K = 17`, Monte-Carlo mode | Nineteen keys, seed material required, `exact_support_size` absent. `P9` accepts `K > 16` on this branch. Accepted. |
| 4 | `K = 17` but `randomization_mode = "EXACT_ENUMERATION"` | `P9` fails: mode/`K` inconsistency, detected locally before any upstream load. |
| 5 | Exact-mode artifact contains `seed_hex` | `P3` fails: eleventh key, not in the exact ten. Refused. |
| 6 | Monte-Carlo artifact missing `seed_hex` | `P3` fails: eighteen keys, not nineteen. Refused. |
| 7 | Monte-Carlo artifact contains `exact_support_size` | `P3` fails: twentieth key. **This is the case §5.L.3 left open; it is now closed** (§6.3). |
| 8 | `seed_hex` is 62 characters (integer-rendered, leading zero byte lost) | `P13` fails: not 64 characters. **This is why §9.1 fixes the encoding on the bytes.** |
| 9 | `seed_hex` uppercase, or `0x`-prefixed | `P13` fails: does not match `^[0-9a-f]{64}$`. |
| 10 | Seed's first byte is `0x00` | Fully legal. `seed_hex` begins `"00"`, is still exactly 64 characters, and `int.from_bytes` yields the correct `seed_int` (§9.1). Accepted. |
| 11 | All 32 seed bytes are zero | Legal; `seed_hex` is 64 `"0"` characters, `seed_int = 0`. `PCG64(0)` is a valid construction. Accepted — refusing it would bias the draw. |
| 12 | `seed_hex` routed through a digest validator | Grammatically passes by coincidence. Forbidden by §7: `seed_hex` is entropy, never a digest, and is validated at `P13` only. |
| 13 | NumPy differs at analysis time from persisted `numpy_version` | Provenance loads fine; the **analyzer's** §5.L.3 check fails → `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`. Unchanged by this document. |
| 14 | `numpy_version` empty string | `P14` fails. |
| 15 | Wrong `final_registration_digest` | `P19` fails, after `P17` has already confirmed the artifact is internally consistent — so the diagnosis is "wrong chain", not "corrupt file". `McProvenanceIntegrityError`. |
| 16 | Mode disagrees with the registration manifest's frozen mode | `P21` fails (implementation design §5.L.1, §6). |
| 17 | `randomization_mc_samples` differs from registered `M` | `P24` fails. `M` is never re-selected anywhere (Stage-C clarification §15). |
| 18 | Second provenance write for one `design_id` | `W2` refuses: `DuplicateMcProvenanceError`. No entropy is drawn — the existence check (§10.1 step 3) precedes the draw. |
| 19 | Persistence fails after `token_bytes(32)` returned | Operation fails. **No redraw, no retry, no second entropy call** (§10.1). Recovery is a new `design_id` under human re-authorization. |
| 20 | Caller attempts to inject a seed, `seed_hex`, `generated_at`, or a clock | **No surface exists** (API-3). Not a runtime refusal — an absent parameter. |
| 21 | Caller passes a hand-built `RegistrationManifest` object with a forged `self_digest` | API-4: the operation loads and revalidates the chain from disk; a convenience object never substitutes for the on-disk artifact. `P18`/`P19` govern. |
| 22 | Artifact edited in place, `self_digest` not recomputed | `P17` fails. |
| 23 | Artifact edited in place **with** `self_digest` recomputed | `P17` passes; `A20` then fails at the referencing `assignment_manifest.json`, whose `randomization_mc_provenance_digest` no longer matches (§20.2). |
| 24 | A `provenance_state: "MC_PROVENANCE_PERSISTED"` key added | `P3` fails: key not in either branch set (§6.4). |

### 23.2 Assignment

| # | Case | Outcome |
|---|---|---|
| 25 | `K = 0` | Zero `draw_bit()` calls, `task_order = []`, `bits = []`, manifest **still persisted** with all thirteen keys, `A1`–`A23` pass (§14.4). |
| 26 | `bits` contains `true` | `A11` fails: `bool` refused even though `True == 1` in Python (§14.3, H5). |
| 27 | `bits` contains `2` | `A11` fails: not in `{0, 1}`. |
| 28 | `bits` contains `"0"` | `A11` fails: JSON string, not integer (§5.B.2). |
| 29 | `bits` shorter than `task_order` | `A12` fails, locally, before any upstream artifact is loaded. |
| 30 | `bits` longer than `task_order` | `A12` fails. |
| 31 | `bits` length correct locally but `!=` registered `K` | `A12` passes, `A22` fails — the local and upstream checks are distinct rules at distinct tiers. |
| 32 | `task_order` unsorted | `A10` fails. **The loader does not sort it and then accept it** (§14.2). |
| 33 | `task_order` contains a duplicate task | `A10` fails: not strictly ascending. |
| 34 | A registered confirmatory task missing from `task_order` | `A21` fails: cover mismatch against recomputed `RTO`. |
| 35 | A foreign task id present in `task_order` | `A21` fails. |
| 36 | A descriptive-only task's id present in `task_order` | `A21` fails: `RTO` is built from `confirmatory_positions` only (§14.2). |
| 37 | Wrong `final_registration_digest` | `A17` fails → `AssignmentIntegrityError`. |
| 38 | Wrong `randomization_mc_provenance_digest` | `A20` fails → `AssignmentIntegrityError`. **This is the check §11 required but left unassigned; it is now assigned** (§16.4). |
| 39 | Provenance artifact missing or corrupt at generation time | §16.1 steps 2–4 refuse **before step 10 draws anything**. `AssignmentIntegrityError`, chained `from` the underlying `McProvenanceIntegrityError` (§16.4). No bit is drawn, and no `.pending` reservation is created — the gate precedes step 8. |
| 40 | Second `persist_assignment` for one `design_id` | `R1` first clause: `DuplicateAssignmentError`. The existence check precedes both the reservation and the draw, so no bit is drawn. |
| 41 | Publication fails after `K` bits were drawn | Operation fails. **No redraw, no retry acquiring new bits, no automatic deletion of the reservation** (`R7`). `.pending` survives; the final path is absent. Human re-authorization and a new `design_id` under §5.A. |
| 42 | **Crash after the draw, before final atomic publication** | Proof chain: the draw occurred → the durable `.pending` reservation created at step 8 survives the crash (`R3`) → the final pathname was never created, because publication is atomic and no-clobber over already-complete staged bytes (`R5`), so **no partial file ever appears at the scientific pathname** → on restart, `R1`'s second clause sees `.pending` present with the final path absent and **hard-refuses with `AssignmentIntegrityError` before any `randbits` call** → **redraw is impossible**; the design requires human re-authorization and a new `design_id`. |
| 42a | Crash *during* the staging write into `.pending` | Same outcome as case 42 by `R4`: `.pending` is present, the final path is absent, restart refuses at `R1`. The partial staged content is never parsed, never digested, and never interpreted as a manifest by anything. |
| 42b | Crash after the reservation but **before the first bit** | Still refuses on restart (`R1`), burning that `design_id`. Accepted deliberately: the reservation cannot distinguish "crashed before drawing" from "crashed after drawing" and must not guess (§16.1.1). Preventing an undetectable second draw outranks preserving a `design_id`. |
| 42c | Crash after **durable** publication (`R5′`), before `.pending` cleanup | Both paths exist and the final entry is durable. **The final artifact is authoritative and no redraw occurs** (`R6`): `R1`'s *first* clause fires, giving `DuplicateAssignmentError`, not the `.pending` refusal. `.pending` is operational residue, removable only under `R6`'s ordering. Cleanup failure never invalidates a valid published artifact. |
| 42c′ | **Crash after `os.link` returned but before the final directory entry is durable** | The previously unproven window, now closed. `.pending` **cannot have been unlinked**, because `R6` forbids cleanup until `R5′` succeeds. So after the crash either (i) the final entry survived — `R1`'s first clause fires, no redraw; or (ii) it did not — `.pending` is still durably present from `R3`, so `R1`'s second clause fires with `AssignmentIntegrityError`, no redraw. **There is no third outcome, and no interleaving leaves neither name durable.** |
| 42c″ | `R5′` synchronization is unsupported or fails on this filesystem | **Fail closed and retain `.pending`** (`R5′`). No redraw, no `.pending` deletion, no automatic retry (`R7`). If the final entry happens to have survived, restart takes `R1`'s first clause; otherwise `R1`'s second. Either way the design goes to human re-authorization, never to a redraw. |
| 42d | Someone deletes `.pending` by hand to unblock a redraw | Outside the contract's reach — it is a deliberate act against the audit record, not a code path. The document claims no defence against manual filesystem tampering it cannot detect (§20.3), exactly as it claims none against a forged wall-clock. What the protocol guarantees is that **no automatic path** deletes the reservation or retries the draw (`R7`). |
| 42e | Implementation cannot provide durable reservation, atomic no-clobber publication, or final-entry durability on its filesystem | **Fails closed** at whichever rule cannot be satisfied — `R3` before any bit is drawn, `R5` rather than falling back to a weaker primitive, or `R5′` while retaining `.pending`. Direct streaming into the final pathname and `os.replace()` are both forbidden (`R5`), and `R5′` is never downgraded to best-effort (§16.1.1). |
| 42f | Implementation unlinks `.pending` immediately after `os.link` returns | **Forbidden by `R6`.** Cleanup is strictly ordered `R5` → `R5′` → `R6`; an unlink before `R5′` succeeds is a contract violation, and it is the exact sequence that would reopen the neither-name-durable window case 42c′ closes. |
| 43 | `DeterministicAssignmentRandomSource` reaches a persisting path | Impossible: the persisting operation accepts no source parameter, and the internal draw helper refuses the type anyway (§18). Fail-closed, twice. |
| 44 | A manifest claims `source_kind = "PYTHON_SECRETS_RANDBITS"` over fixture bits | Impossible by construction: the persisting operation builds `SecretsAssignmentRandomSource` itself (§18 item 5). |
| 45 | Caller attempts to supply bits, timestamps, a clock, or a random source | **No surface exists** (API-3). |
| 46 | Different bits attempted across models under one task | Impossible: `draw_bit()` is called once per task in `task_order` order, and the schema has no per-position bit slot (§14.1; implementation design §5.M, §5.D). |
| 47 | `generation_started_at == generation_completed_at` | **Accepted** — the normal case at whole-second resolution (`A14` non-strict, C8). Refusing it would fail correct runs. |
| 48 | `provenance.created_at == generation_started_at` | **Accepted** (`A23` non-strict). Structural ordering already proves the sequence (§8.3). |
| 49 | `generation_started_at` after `generation_completed_at` | `A14` fails. |
| 50 | Provenance stamped a day after the assignment | `A23` fails: the supplemental consistency check catching a grossly inconsistent artifact set, which is exactly what it is for. |
| 51 | A `created_at` key added to the assignment manifest | `A2` fails: fourteenth key (§12.2). |
| 52 | A `K` or `randomization_mode` key added | `A2` fails (§12.2). |
| 53 | An `assignment_digest` key added | `A2` fails: same-object alias, forbidden by C5 and structurally excluded by the thirteen-key set. |
| 54 | A resolved `qa_mode` label persisted per task | `A2` fails: labels are computed by `resolve_label` at dispatch, never persisted here (§12.2). |
| 55 | Manifest edited in place, `self_digest` recomputed | `A15` passes; `final_analysis_manifest.json`'s `assignment_digest` reference then breaks downstream (§20.2). |
| 56 | Execution requested with no persisted assignment | `AssignmentNotPersistedError` (implementation design §6, §7 PR-3). Unchanged by this document. |

Every case above resolves to exactly one deterministic outcome; none has a residual "depends on implementation choice" branch.

---

## 24. Conflict check against the binding contracts

Each row is a frozen requirement this document could have contradicted. None is overridden; where the binding text and a preferred representation pulled apart, the binding requirement is preserved and the representation resolved another way.

| Binding requirement | Source | Disposition |
|---|---|---|
| Canonical JSON profile, `self_digest` algorithm, one LF, reader semantics | §5.B.2 | **Reused verbatim.** No second algorithm; no field of either artifact needs the decimal-string rule; no byte-equality gate added (API-7). |
| No same-object digest alias | §5.B.1 | **Held.** Neither artifact stores its own downstream alias name (§12.1, §20.1). |
| Provenance exists in both modes, tagged by `randomization_mode` | §5.L.1 | **Held and tightened**: both branches are now closed key sets, and the tag is read first (`P2`). |
| Exact mode: `exact_support_size = 2 ** K`, `K`, `statistic_spec_id`, no seed material | §5.L.2 | **Reproduced exactly.** The ten forbidden fields are precisely `MC_ONLY` (§6.3). |
| Monte-Carlo mode: full seed provenance, `PCG64`, registered `M`, recorded NumPy version | §5.L.3 | **Reproduced exactly**, with `seed_hex` encoding and `numpy_version` source now determinate (§9). |
| "the **registered** NumPy version" | §5.L.3 | **Conflict, resolved without inventing an upstream field.** H10 shows no Stage-A/B/C artifact registers one. Resolution: this artifact's own `numpy_version` **is** the registration, captured at generation (§9.2). No Stage-A schema is touched. |
| Provenance `generated_at` predates assignment and execution | §5.L.3, §13, §14 case 15 | **Held, read non-strictly (C8)**, with structural ordering as the authoritative proof; and the exact branch's missing `generated_at` is closed by giving `created_at` that role (§8.4). |
| `bootstrap_seed` never reaches the confirmatory MC path | §5.L.3, §14 case 16 | **Held and reinforced**: API-3 gives the production operation no seed-shaped parameter of any kind, so there is no surface through which `bootstrap_seed` could arrive. |
| Assignment provenance fields: `source_kind`, `source_api`, `python_version`, `generation_started_at`, `generation_completed_at` | §5.M | **All five present, unrenamed**, in the thirteen-key set (§12.1). |
| `draw_bit()` once per task, `K` calls, sorted `task_id` order, one bit per task | §5.M | **Held**, and now *persisted checkably*: `task_order` records the call sequence and `A21` verifies it (§14). |
| "writes `assignment_manifest.json` atomically" | §5.M | **Held literally**, and discharged by the reserve → stage → atomic-no-clobber-link → **durable-final-entry** → cleanup protocol of §16.1.1 (`W2′`). **Exclusive create alone does not satisfy it** — `open("xb")` on the final path makes the directory entry visible before the content is complete — so the final pathname is published by an atomic no-clobber primitive over already-complete staged bytes, and **a returned create call is not yet durable publication**: `R5′` must succeed before `.pending` may be cleaned up, closing the window in which a crash could leave neither name durable. |
| "refuses if ... already exists (`DuplicateAssignmentError`)" | §5.M | **Held** (`W2′`, `R1`), and the check is placed **before** the draw (§16.1 step 5), alongside the `.pending` refusal of step 6. |
| "never regenerates ... never an automatic retry" | §5.M | **Held and extended** to the post-draw and post-entropy failure paths explicitly (§10.1, §16.1). |
| "production ... refuses if the **supplied** `AssignmentRandomSource` is a `DeterministicAssignmentRandomSource`" | §5.M | **Conflict, resolved explicitly (§18).** The refusal is implemented on the internal draw helper; the persisting operation has no source parameter at all. Strictly stronger than the requirement, never weaker. |
| `AssignmentIntegrityError` triggers | §11 | **Extended by assignment, not amendment** (§16.4): §6 required a `randomization_mc_provenance_digest` check that §11 left unassigned; the existing error now covers it. No frozen assignment is changed. |
| `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` is analysis-scoped | §11 | **Held.** Generation-time refusals use the experiment-layer family (§10.2). |
| `DuplicateAssignmentError`, `AssignmentNotPersistedError` | §11 | **Adopted unchanged.** |
| State machine order and its refusal rows | §6 | **Held.** No new state, no new transition, no bypass; the artifacts carry no state field (§6.4, §12.2). |
| `resolve_label` / `complement` | §5.D | **Untouched** (API-8). No label is persisted (§12.2). |
| Module ownership: `confirmatory_assignment.py` owns both artifacts | §8 item 3, §11, authorization §5.1 | **Held.** No new module, no alternative layout. |
| `assignment_manifest.json` required fields "§5.M fields, `bits`, `task_order`" | §12 catalog | **Given a shape** (§12.1, §14). Both names survive; neither is renamed. |
| `K = 0` legal at Stage C | Stage-C clarification §8.3, §15 | **Held downstream** (§14.4): both artifacts are still produced, and no draw occurs. |
| `K` is the count of distinct confirmatory `task_id` values | Stage-C clarification §15 | **Reused as the cover rule** (§14.2). No second notion of `K` is created. |
| `M` never re-selected after registration | Stage-C clarification §15 | **Held**: `randomization_mc_samples` is copied and cross-checked (`P24`), never chosen (API-3). |
| Stage C forbids `bits`, `b_k`, `task_order`, and every seed field | Stage-C clarification §4.6, §16.4; H11 | **Consistent**: those names now exist exactly where Stage C said they would, and nowhere else. |
| Timestamp grammar `YYYY-MM-DDTHH:MM:SSZ`, internal capture, never an equality invariant | Stage-C clarification §4.4.1 | **Carried forward** to four new timestamps (§8.2, §15.2), with ordering relations added that are not equality invariants (T7, T7′). |
| No unrelated refactor; `_ordered_treatments` unmodified; legacy paths preserved | authorization §5.2, §5.4 | **Held.** This document names no change to any existing module. |

**No binding requirement is overridden anywhere in this document.** Three genuine tensions were found — the "registered NumPy version" phrase, the "supplied `AssignmentRandomSource`" clause, and the unassigned provenance-digest check — and each is resolved above by preserving the binding requirement and satisfying it through a representation that also satisfies the constraint it collided with.

---

## 25. Boundaries

- **`ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO.`** No seed exists. No entropy API was called. `seed_hex` appears only as a placeholder.
- **`ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO.`** No `b_k` was drawn. `bits` appears only as a placeholder.
- **`ACTUAL_CONFIRMATORY_REGISTRATION_AUTHORIZED: NO.`** No `design_id`, task, provider, model, or `M` is selected here.
- **`WU4_CODE_WRITTEN_BY_THIS_DOCUMENT: NO.`** No `src/` file, no test file, no `pytest`, no `mypy`.
- **`HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO.`** `results/phaseP-rc4-qualification/` was not inspected, hashed, traversed, modified, staged, or regenerated, and has no relationship to any artifact designed here.
- **Still deferred, unchanged:** the confirmatory matrix, provider/model membership and real dispositions, repetitions, ordinary provider seeds, `M`, the actual `b_1..b_K`, the actual seed value, timeout/retry values, the execution window, and the `design_id` value. This document froze representations, not values.

---

## 26. DECISION

## **`CONFIRMATORY_RANDOMIZATION_PERSISTENCE_SCHEMA_CLARIFICATION_DECISION: WU4_PERSISTED_REPRESENTATION_FROZEN`**

Justification: all ten gaps are closed with exactly one representation each. `randomization_mc_provenance.json` is a closed tagged union — ten keys in `EXACT_ENUMERATION`, nineteen in `MONTE_CARLO`, with exactly complementary forbidden sets whose counts reproduce implementation design §5.L arithmetically, and with no lifecycle field invented (§6). Its `schema_version` literal is minted once against a verified absence of any conflicting literal (§5, H7). The `created_at` / `generated_at` ambiguity is resolved into two distinct internally-captured fields with one chain grammar, a seven-rule capture contract, non-strict ordering forced by whole-second resolution, and an explicit statement that structural call ordering — not the timestamp — is the ordering proof; the exact branch's missing `generated_at` is closed by giving `created_at` that role (§8). `seed_hex` is fixed as the 64-character lowercase hex of the exact 32 raw bytes, eliminating the leading-zero-byte divergence, and `numpy_version` is fixed as an internal capture that *is* the registration rather than a copy of a Stage-A field that H10 shows does not exist (§9). Entropy acquisition and persistence are one indivisible operation with a nine-step sequence, a minimal two-name error extension of the already-frozen family, and a twenty-four-rule first-failure loader order (§10, §11). `assignment_manifest.json` is fixed at exactly thirteen keys with `created_at`, `K`, `randomization_mode`, and every state, seed, execution, and analysis field structurally excluded (§12). `bits` and `task_order` — named by implementation design §12's catalog but never shaped by §5.M — are frozen as parallel arrays with an exact element-wise cover of the registered confirmatory task set, strict ascending order, integer bits with `bool` refused, and `K = 0` producing two empty arrays in a manifest that is still persisted (§14). Assignment timestamps are internally captured with non-strict ordering, and no execution-row timestamp is invented (§15). Draw and publication are indivisible; `python_version` is an internal capture deliberately not tied to runtime identity (§16). **§5.M's "writes `assignment_manifest.json` atomically" is discharged literally rather than approximated**: exclusive create is explicitly *not* atomic publication, so the manifest is published by a reserve → stage → atomic-no-clobber-link → **durable-final-entry** → cleanup protocol under which the final scientific pathname never holds partial bytes; a returned `os.link` is not yet durable publication, so `R5′` must durably synchronize the metadata holding the new final entry **before** `.pending` may be unlinked, which closes the window in which a crash could otherwise leave neither name durable and silently re-arm a redraw. The required semantic property — not one falsely-portable primitive — is what is frozen, with platform-specific realization expected and fail-closed retention of `.pending` where it cannot be established. A durable pre-draw `.pending` reservation therefore makes any post-crash automatic redraw structurally impossible at every instant, while remaining outside the six-artifact chain and adding zero schema fields (§16.1.1). **The assignment layer exposes exactly one fail-closed exception surface**: every rule `A1`–`A23` raises `AssignmentIntegrityError`, with `A16`'s registration-layer cause and `A19`'s `McProvenanceIntegrityError` caught and re-raised `from` the original so no dependency-layer exception leaks and no cause is erased (§16.4). A twenty-three-rule first-failure loader order covers the assignment artifact in three tiers (§17). The deterministic test source is resolved by removing the injection surface while implementing §5.M's refusal, which is strictly stronger than the frozen requirement (§18). Sixty-four adversarial cases each resolve to exactly one deterministic outcome, including a nine-case crash-safety family proving that a post-draw crash durably blocks redraw at every instant of the protocol (§23), and every binding contract is checked for contradiction, with three genuine tensions found and each resolved by preserving the binding requirement rather than overriding it (§24).

```
UNRESOLVED_WU4_ITEMS_U_D1_TO_U_D5: NONE
UNRESOLVED_WU4_ITEMS_U_E1_TO_U_E5: NONE
REMAINING_WU4_PERSISTED_SCHEMA_CHOICES: NONE
WU4_CODE_IMPLEMENTATION_UNBLOCKED: YES
```

---

## 27. Validation

| Check | Result |
|---|---|
| Exactly one file created; no existing file modified | YES |
| Document base is canonical `origin/main` (`befb7ff`), not unmerged implementation code | YES |
| Binding docs byte-identical between `befb7ff` and `a668d77` | YES (six blob-hash comparisons) |
| Implementation branch inspected read-only via `git show` only | YES |
| `results/phaseP-rc4-qualification/` untouched | YES |
| No `src/`, no tests, no `pytest`, no `mypy` | YES |
| No entropy, no `secrets.token_bytes`, no `secrets.randbits`, no real artifact | YES |
| Exact-branch key count reproduces §5.L (`7 + 3 = 10`) | YES (§6.3) |
| Monte-Carlo-branch key count reproduces §5.L (`7 + 12 = 19`) | YES (§6.3) |
| Assignment key count internally consistent (`5 + 2 + 3 + 2 + 1 = 13`) | YES (§12.1) |
| Every field of both artifacts classified and sourced exactly once | YES (§22) |
| Every rejection condition has a unique numbered rule | YES (§11.3, §17.4) |
| Assignment final publication is atomic and no-clobber; exclusive create is never equated with it | YES (§16.1.1 `R5`, `W2′`) |
| Final directory entry made durable before any `.pending` cleanup; `R5` → `R5′` → `R6` ordering frozen | YES (§16.1.1 `R5′`, `R6`, `W2′`) |
| Unsupported/failed final-entry durability fails closed and retains `.pending`; never downgraded to best-effort | YES (§16.1.1 `R5′`, `R7`) |
| No crash window can leave neither the final artifact nor the reservation durable | YES (§16.1.1 property (B); §23 cases 42c′, 42c″, 42f) |
| A post-draw crash durably blocks any automatic redraw | YES (§16.1.1 `R1`–`R5′`, `R7`; §23 cases 42, 42a–42f) |
| `.pending` is outside the scientific artifact/digest chain and adds zero schema fields | YES (§16.1.1, §12.1) |
| `AssignmentManifestV1` still exactly thirteen keys | YES (§12.1) |
| Every assignment-loader rule `A1`–`A23` has one exact public exception | YES (§16.4, §17.4) |
| No provenance-layer or registration-layer exception leaks from a public assignment entry point; causes chained, never erased | YES (§10.2, §16.4, `A16`, `A19`) |
| No binding contract overridden | YES (§24) |
| Nothing staged, committed, or pushed | YES |

---

## Final report block

```
WORK_UNIT: WU4_PERSISTENCE_SCHEMA_CLARIFICATION

U_D1: CLOSED    U_E1: CLOSED
U_D2: CLOSED    U_E2: CLOSED
U_D3: CLOSED    U_E3: CLOSED
U_D4: CLOSED    U_E4: CLOSED
U_D5: CLOSED    U_E5: CLOSED

MC_PROVENANCE_EXACT_SCHEMA_FROZEN: YES
MC_PROVENANCE_MC_SCHEMA_FROZEN: YES
ASSIGNMENT_SCHEMA_FROZEN: YES
TIMESTAMP_CONTRACT_FROZEN: YES
RANDOMNESS_PERSISTENCE_BOUNDARY_FROZEN: YES
LOADER_ORDER_FROZEN: YES
K_ZERO_BEHAVIOR_FROZEN: YES
PRODUCTION_RANDOM_SOURCE_INJECTION_FORBIDDEN: YES

WU4_REPRESENTATION_READY_FOR_CODE: YES

CODE_IMPLEMENTATION_PERFORMED_HERE: NO
ACTUAL_MONTE_CARLO_SEED_GENERATION_AUTHORIZED: NO
ACTUAL_RANDOMIZATION_ASSIGNMENT_AUTHORIZED: NO
ACTUAL_CONFIRMATORY_EXECUTION_AUTHORIZED: NO
HISTORICAL_PHASEP_MODIFICATION_AUTHORIZED: NO
```
