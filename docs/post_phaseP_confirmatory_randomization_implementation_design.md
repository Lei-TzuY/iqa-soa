# Post-Phase-P confirmatory randomization implementation design

**Record kind:** repository-level ENGINEERING / IMPLEMENTATION DESIGN document.
**Status:** IMPLEMENTATION DESIGN only. This is **not** a methodology document and **not** code. It designs schemas, module boundaries, function signatures, manifests, a state machine, failure tokens, and a future test list that will later realize the statistical methodology already frozen elsewhere. It contains no statistics not already frozen, and it makes no new statistical decision anywhere.
**Date:** 2026-08-26
**Base commit:** `e12865a` (`origin/main`) — merge of PR #19, which carries the frozen confirmatory-randomization design decision.
**Revision:** 3 (supersedes Revision 2 in full for §5.B, §5.C, §5.I, §5.L, and every downstream section that references digest naming, MC provenance, row reconciliation, or runtime snapshots).

**Revision 2 note (carried forward for provenance).** An independent (Codex) closure review accepted the frozen statistical methodology unconditionally but found four genuine implementation-architecture blockers in Revision 1: (1) the lifecycle allowed eligibility to remain `UNASSESSED` at the point the confirmatory matrix was frozen and execution began; (2) the artifact/digest chain left the relationship between registration, eligibility, assignment, Monte Carlo provenance, and analysis manifests only partially specified; (3) the execution-row-to-registered-position binding was too weak; (4) the observation/failure taxonomy could not distinguish a genuine `OBSERVED` endpoint from an endpoint that merely survived as non-`None` after an upstream failure. Revision 2 closed all four and froze the eligibility-before-registration lifecycle, the six-artifact digest chain, `ConfirmatoryPositionV1` row binding, the observation/failure taxonomy, the `secrets`-based RNG sources, and module ownership. Those Revision 2 architectural decisions (`ELIGIBILITY_FREEZE_ORDER`, `OBSERVATION_FAILURE_GATE`, `ASSIGNMENT_RANDOMNESS_ARCHITECTURE`, `MONTE_CARLO_ARCHITECTURE` independence/timing, `STATE_ISOLATION_STRATEGY`, `STATISTIC_SPEC_ID`, `MODULE_OWNERSHIP`) are **not reopened** by this revision.

**Revision 3 note.** A second independent re-review re-checked the Revision 2 closure and PASSed every item listed above, but identified exactly **four residual interface/schema defects** that Revision 2 left underspecified enough to permit an inconsistent implementation:

1. **Self-digest alias recursion.** Revision 2's digest chain allowed an artifact to store both `self_digest` and a same-object alias field (`final_registration_digest` on `registration_manifest.json`, `assignment_digest` on `assignment_manifest.json`) that named the identical value under a second key, while the hashing algorithm only ever omitted `self_digest` from the object being hashed. That is self-referential in the alias name even though the digest math happened to still work, and it left the canonical JSON profile itself (numeric representation, decimal-vs-float handling, key ordering) unfrozen. Revision 3 removes every same-object digest alias field: every artifact stores exactly one `self_digest` of itself, and semantic names such as `final_registration_digest` or `assignment_digest` are downstream-only reference names for an upstream artifact's `self_digest`, never a second field on the artifact that produced it. Revision 3 also freezes the canonical JSON profile completely (§5.B).
2. **Missing exact-mode Monte Carlo provenance sentinel.** Revision 2 froze `randomization_mc_provenance.json` as a K>16-only artifact, which left an absent-vs-sentinel choice live for K≤16 and risked a future implementer fabricating an unnecessary seed for exact enumeration, or omitting the artifact and breaking the six-artifact chain's uniformity. Revision 3 freezes a tagged-union schema so the artifact exists in **both** modes, with mode-conditional required/forbidden fields (§5.L).
3. **Incomplete row profile/design-id validation.** Revision 2's `ConfirmatoryPositionV1` row-binding checklist (§5.C) never explicitly required checking `confirmatory_profile` and `design_id` against the registered values, even though both fields were already part of the row contract. Revision 3 extends the checklist to validate them explicitly, first, before any digest check (§5.C).
4. **Conflated runtime identity vs. capture metadata.** Revision 2 said runtime snapshots must "match" field-by-field, including `captured_at` and `self_digest`, which naturally differ across capture times by design — making the stated equality rule self-contradictory. Revision 3 freezes a two-layer `RuntimeSnapshotV1` contract that separates invariant runtime-identity fields (compared via a dedicated `runtime_identity_digest`) from capture metadata (`captured_at`, `self_digest`), which are never compared for equality across captures (§5.I).

Nothing below authorizes code, execution, staging, or commit. §1-§4 (framing, forensics, frozen methodology axioms, module-naming convention) are unchanged from Revision 2, because none of the four residual defects touches them. §5.B, §5.C, §5.I, §5.L are full replacements; §6-§14 and §18-§19 are updated wherever they reference the changed schemas, and are otherwise unchanged.

**Inputs (read-only, not modified, not reopened, not reinterpreted anywhere below):**

- `docs/post_phaseP_qualification_methodology_decision.md`
- `docs/post_phaseP_analysis_contract_decision.md`
- `docs/post_phaseP_confirmatory_randomization_design_decision.md`
- `docs/metrics.md`

This document does not alter, revise, extend, or reinterpret any sentence in the four files above. Every statistical fact it depends on is treated as an axiom, cited by section number, and never re-derived. Where this document must choose an engineering shape (a module name, a JSON field name, a state-machine token), that choice is marked **[IMPLEMENTATION DESIGN]** and is frozen — Revision 3 permits no alternative shapes to remain live for a future implementer to pick, per the closure review. Where this document reports a fact about the current committed source tree, that fact is marked **[OBSERVED]** and is cited `file:line`. Where a value cannot be fixed without contradicting the "no seed, no bit, no candidate" boundary of the task, it is marked **[DEFERRED VALUE / VERIFICATION]**. Where an action is explicitly out of scope for this document, it is marked **[NOT AUTHORIZED]**.

**Boundary declaration.** Producing this document involved: no model inference, no provider contact, no network call; no modification of anything under `results/phaseP-rc4-qualification/`; no execution of any analyzer, harness, probe, or validator; no `pytest` invocation; no seed derivation; no randomization bit generated; no task/provider/model/repetition value selected; no candidate, version, RC, or named phase created; no `git add`/`commit`/staging. Exactly one file is written: this document.

---

## 1. What this document is, precisely

The three frozen decision records establish, as axioms (restated in full in §3), a position-indexed potential-outcome model, a task-cluster-level fair-bit randomization mechanism `b_k`, an assignment-invariant sign-flip statistic, a total-observation fail-closed rule, and a four-predicate provider/runtime eligibility rule. None of that is re-derived, revised, or extended here. What is missing from the repository is the **engineering** that would let a future, separately authorized implementation PR actually realize that mechanism in code: a place to persist the pre-registration matrix, a place to persist the `b_k` draws, a place to apply them to labels, a fail-closed analyzer path, an eligibility manifest, and tests. This document designs all of that, as schemas and module boundaries only. **No code in this repository is changed by this document. No seed, bit, task, provider, or model is selected by this document.**

---

## 2. Read-only repository forensics — the five facts to verify

All claims below were checked directly against source, independent of what the three frozen decision documents already assert (their own citations of the same lines are consistent with what follows). These are historical observations about the current committed tree; ordinary English "or" describing what the current code already does is not an open architecture choice and is left as-is.

### Fact 1 — `_ordered_treatments` is deterministic counterbalancing, not random assignment

**VERIFIED. [OBSERVED]** `src/iqa_soa/experiment/runner.py:703-722`:

```
def _ordered_treatments(self, arms, case_id, repetition):
    ordered = list(arms)
    if self.config.shuffle_treatments:
        block = repetition // len(ordered)
        rotation = repetition % len(ordered)
        block_seed = self._seed_for(block * len(ordered))
        arm_names = ",".join(item.name for item in ordered)
        material = f"{block_seed}:{case_id}:{block}:{arm_names}".encode("utf-8")
        local_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        random.Random(local_seed).shuffle(ordered)
        ordered = ordered[rotation:] + ordered[:rotation]
    return tuple(ordered)
```

`local_seed` is a SHA-256 digest of `(block_seed, case_id, block, arm_names)` — a pure function of frozen configuration (`self.config.seeds`, the case id, the block index, and the treatment names) — followed by a fixed rotation `repetition % len(ordered)`. No entropy source is consulted; no fair coin is drawn; the same inputs always reproduce the same order. This is a deterministic Latin-style counterbalancing rotation, not a stochastic treatment-assignment draw. It is invoked at `runner.py:381` (`ordered = self._ordered_treatments(arms, case.id, repetition)`) and its output is persisted per row as `treatment_order` / `treatment_index` (`runner.py:616-617`). Confirms the frozen design decision's F5/S13a (`docs/post_phaseP_confirmatory_randomization_design_decision.md` §3, §6 req. 8).

### Fact 2 — `pair_before_after(..., require_complete=True)` rejects incomplete pairs

**VERIFIED. [OBSERVED]** `src/iqa_soa/metrics/statistics.py:391-395` declares `require_complete: bool = True` as the default, and every committed call site (`analyze_before_after` at `statistics.py:681`, `pair_before_after(rows)`) uses that default without overriding it. The enforcement is at `statistics.py:456-460`:

```
if require_complete and incomplete:
    examples = ", ".join(repr(item) for item in incomplete[:3])
    raise AnalysisError(
        f"Unpaired OFF/FULL observations for {len(incomplete)} key(s): {examples}"
    )
```

`incomplete` is built at `statistics.py:416-421`: any `PAIR_KEYS` bucket (`statistics.py:25`, `("task_id","repetition","seed","provider","model")`) missing either an `off` or a `full` row is appended to `incomplete` and excluded from `pairs`, then the whole call raises `AnalysisError` if `require_complete` and `incomplete` is nonempty. An incomplete row-level pair is therefore a **hard error at the row-pairing stage**, not a silent drop.

### Fact 3 — `_apply_task_cluster_inference` silently drops endpoint-missing pairs from the cluster, rather than signaling unavailability

**VERIFIED. [OBSERVED]** `src/iqa_soa/metrics/statistics.py:777-788`:

```
clusters: dict[Any, list[tuple[float, float]]] = {}
for pair in pairs:
    ...
    before = ...
    after = ...
    if before is not None and after is not None:
        clusters.setdefault(pair.key[0], []).append((before, after))
```

A `PairedRows` that survived `pair_before_after` (i.e., both OFF and FULL rows exist and neither carries a disqualifying recorded error, per `statistics.py:444-454`) is **only** added to its task cluster's observation list when **both** the metric's `before` and `after` values are non-`None` after `_binary`/`_number` coercion. A pair whose metric value is `null` on one side is **silently excluded from `clusters`** at line 787-788 — it contributes nothing to `n_tasks`, `task_differences`, or any downstream statistic, and no flag, counter, or exception records that the exclusion happened. This is exactly the gap the frozen methodology's `CONFIRMATORY_OBSERVATION_RULE` (`docs/post_phaseP_confirmatory_randomization_design_decision.md` §8) requires closed: a missing registered position's primary endpoint must trigger `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`, not vanish before inference. No such signal exists today. Revision 2 additionally establishes (§5.H below) that a non-`None` value is *not by itself* sufficient evidence of observation — this document must not use `endpoint is not None` as its fail-closed test, and it does not.

### Fact 4 — `_task_sign_flip_p_value`: exact enumeration for K≤16, Monte Carlo with a generic shared seed for K>16

**VERIFIED. [OBSERVED]** `src/iqa_soa/metrics/statistics.py:854-875`:

```
def _task_sign_flip_p_value(differences, *, samples, seed):
    observed = abs(float(np.mean(differences)))
    if math.isclose(observed, 0.0, abs_tol=1e-15):
        return 1.0
    values = np.asarray(differences, dtype=float)
    if len(values) <= 16:
        total = 1 << len(values)
        ... # exact enumeration over all `total` sign masks
        return extreme / total
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(samples, len(values)))
    simulated = np.abs((signs * values).mean(axis=1))
    return float((np.count_nonzero(simulated >= observed - 1e-15) + 1) / (samples + 1))
```

K≤16 exact enumeration is at `statistics.py:861-871`; K>16 Monte Carlo (`np.random.default_rng(seed)`, `+1/(samples+1)` add-one estimator) is at `statistics.py:872-875`. **The `seed` parameter is not a dedicated Monte Carlo/randomization seed.** Tracing its caller: `_apply_task_cluster_inference` (`statistics.py:766-773`) receives `seed` as a plain parameter and passes the **identical** value both to `_bootstrap_mean_ci` (`statistics.py:839-844`) and to `_task_sign_flip_p_value` (`statistics.py:848-850`). `analyze_before_after` (`statistics.py:667-672`, default `seed: int = 2027`) derives per-metric seeds as `seed + index` / `seed + 100 + index` (`statistics.py:697, 709, 720, 732`) and reports the base value under `"bootstrap_seed": seed` (`statistics.py:743`) — a name that already presumes the seed's only role is the bootstrap, even though the same value silently also drives the sign-flip Monte Carlo. There is no `randomization_mc_seed` field, no distinct RNG-algorithm-id field, and no provenance record anywhere in this path. Revision 2 freezes a wholly separate Monte Carlo seed/provenance channel that never reads, derives from, or feeds `bootstrap_seed`; legacy `bootstrap_seed` behavior in `statistics.py` is unchanged and remains legacy-only. Revision 3 does not reopen this; it only closes the exact-mode sentinel gap in how the provenance artifact's *shape* is frozen (§5.L).

### Fact 5 — no persisted task-level prospective random-assignment artifact exists

**VERIFIED. [OBSERVED]** A repository-wide search (`Grep` over `src/iqa_soa/**/*.py`) for `assignment_manifest`, `RandomSource`, `b_k`, `registration_manifest`, `CONFIRMATORY_ELIGIBLE`, and `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` returned **zero matches** anywhere under `src/`. The complete module inventory under `src/iqa_soa/` (`experiment/{runner,pilot,treatments,ablation,replay,fault_provenance,failure_events}.py`, `metrics/{statistics,collector,definitions,pilot}.py`, `iqa/*`, `tools/*`, `benchmark/*`, `agent/*`) contains no fair-bit generator, no assignment-persistence module, no registration-freeze module, and no eligibility-manifest module. The entire randomization/registration/eligibility layer designed below is **prospective and unimplemented**, exactly as the frozen design decision itself already states (`docs/post_phaseP_confirmatory_randomization_design_decision.md` §3).

---

## 3. Frozen inputs — restated as NOT reconsidered here

The following are treated as axioms throughout this document. None is re-derived, revised, weakened, strengthened, or extended by anything below; every architecture choice in §5 is checked for consistency against them, and any apparent tension is resolved by changing the **code design**, never the methodology.

1. Scheduled position = potential-outcome / treatment-receiving unit (design decision §4.A-4.B).
2. Task cluster `k` = randomization cluster (design decision §4.A).
3. One fair independent random bit `b_k` per confirmatory task, drawn once per task cluster, shared by every nested position/model/provider/repetition under that task (design decision §4.D).
4. `b_k` selects baseline schedule `S_k` versus its exact complement `C(S_k)`; `B = {0,1}^K`, equiprobable, independent of outcomes `Ω` — `B ⊥ Ω` (design decision §4.D-4.G, §5.6).
5. Position-level sharp null hypothesis `H0_sharp` (design decision §5.5).
6. No operational common-random-number replay required between distinct physical executions (design decision §5.3).
7. Full assignment-invariant confirmatory matrix, registered before randomization (design decision §7, §10 as referenced).
8. Task-level relative-sign statistic `T(r) = |(1/K)·Σ r_k D_k^obs|`; zero-difference blocks retained in `K`; only `K_plus` (nonzero) reported for enumeration/MC granularity, structure preserved (design decision §7.1, §7.4.1).
9. K ≤ 16 → exact enumeration of all `2^K` sign masks; K > 16 → frozen Monte Carlo plus-one rule, independent of observed data/outcomes/failures (design decision §7.4, §7.4.2, `MONTE_CARLO_ASSIGNMENT_INDEPENDENCE` A-G, `MONTE_CARLO_PLUS_ONE_VALIDITY`).
10. Total primary-endpoint observation required — no deletion/reweighting/renormalization of missing endpoints; if any registered position's primary endpoint is genuinely unobserved, the confirmatory test must be `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (fail closed), not silently computed on a subset (analysis contract §15.2.5 as inherited by design decision §8).
11. Confirmatory/descriptive matrix split — a provider/runtime/model stratum must be affirmatively judged `CONFIRMATORY_ELIGIBLE` via four predicates (`POSITION_STATE_ISOLATION` = PR-4, `INFRASTRUCTURE_SYMMETRY` = PR-5, `TOTAL_OBSERVATION` prospective eligibility = PR-7, `RUNTIME_CONFIGURATION_FROZEN`) or else it is descriptive-only (design decision §9).
12. `θ_target` / `θ_complete` / bounds separation (analysis contract §5.3-§5.5).
13. Fixed-sequence multiplicity architecture (analysis contract §16, inherited).

Revision 3, like Revision 2, adds no new statistical axiom to this list. It freezes only how the above are realized in artifacts, modules, and state transitions, and (this revision only) closes four residual interface/schema gaps in that realization.

---

## 4. Repository module-naming convention observed

**[OBSERVED]** `src/iqa_soa/experiment/` holds orchestration-lifecycle modules (`runner.py`, `pilot.py`, `treatments.py`, `ablation.py`, `replay.py`, `fault_provenance.py`, `failure_events.py`); `src/iqa_soa/metrics/` holds pure analysis modules (`statistics.py`, `collector.py`, `definitions.py`, `pilot.py`). Each module is single-purpose and named after the concern it owns. The design below follows this convention: the frozen future module list is given in full in §11, and no other module layout is authorized.

---

## 5. Architecture

### 5.A Three-stage registration lifecycle — frozen (Revision 2, not reopened)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze exactly three sequential stages, each with its own immutable artifact, with eligibility evaluated and finalized strictly between the first two. Revision 3 does not reopen this lifecycle; it is restated here only because §5.B's digest-field renaming touches the field names this section refers to.

**Stage A — `REGISTRATION_DRAFT`.** Not the final immutable confirmatory registration. It records the *proposed* design: candidate tasks, candidate provider/model strata, candidate repetitions, candidate ordinary provider seeds, candidate fixed positions, candidate runtime/config values, and candidate statistical configuration. It authorizes nothing: not assignment, not execution, not confirmatory analysis. Its sole role is to be the fixed input that eligibility is assessed against. Producing module: `src/iqa_soa/experiment/confirmatory_registration.py`, function `draft_registration(...) -> RegistrationDraft`, persisted as `registration_draft.json` (§5.B artifact layout).

**Stage B — `ELIGIBILITY_FROZEN`.** Produced by `src/iqa_soa/experiment/confirmatory_eligibility.py`, persisted as `eligibility_manifest.json`, created strictly **after** `registration_draft.json` exists and strictly **before** the final confirmatory registration is produced. It binds to `registration_draft.json`'s `self_digest` (referenced within `eligibility_manifest.json` under the field name `registration_draft_digest`, per §5.B), evaluates every proposed provider/model/runtime stratum named in the draft against the four frozen predicates (`POSITION_STATE_ISOLATION`, `INFRASTRUCTURE_SYMMETRY`, `TOTAL_OBSERVATION` prospective eligibility, `RUNTIME_CONFIGURATION_FROZEN`), and gives each proposed stratum exactly one frozen disposition. It becomes immutable once finalized. Actual provider/model values and their real dispositions remain **[DEFERRED VALUE SELECTION]** — this document assesses no real provider now; it freezes only the schema and the evaluation/immutability rule.

**Stage C — `FINAL_REGISTRATION_FROZEN`.** Produced by `confirmatory_registration.py`, function `freeze_final_registration(...) -> RegistrationManifest`, persisted as `registration_manifest.json`. Only after `ELIGIBILITY_FROZEN` may this stage occur. The final registration binds to both `registration_draft.json.self_digest` (as `registration_draft_digest`) and `eligibility_manifest.json.self_digest` (as `eligibility_manifest_digest`), and explicitly freezes: confirmatory strata, descriptive-only strata, confirmatory position IDs, descriptive position IDs, task membership, provider/model membership, repetitions, ordinary seeds, baseline schedule, statistic version, registered `K`, the derived `randomization_mode` (§5.L), and every other registered value. It includes the final confirmatory matrix digest (`matrix_digest`) and its own `self_digest` — which every downstream artifact references under the name `final_registration_digest` (§5.B) — and carries `registration_state: FINAL_REGISTRATION_FROZEN`. **Only `CONFIRMATORY_ELIGIBLE` strata (per the immutable eligibility manifest from Stage B) may appear in the confirmatory matrix.** A descriptive-only stratum may remain in the broader reporting design, but its role is already frozen as descriptive before final registration — it can never later enter the confirmatory matrix.

**Post-freeze invariant.** After `FINAL_REGISTRATION_FROZEN`, no task/provider/model/position may move into or out of the confirmatory matrix, for any reason, ever. Eligibility re-assessment in place is **not permitted** under any circumstance — not before assignment, not after assignment, not after execution, not after analysis. If a future pre-execution need for re-assessment arises, the entire registration (draft, eligibility manifest, final registration) is abandoned as a unit and a **new** `registration_draft.json` / `eligibility_manifest.json` / `registration_manifest.json` triple is created under a **new** `design_id`. An existing frozen eligibility manifest is never mutated or versioned in place; it is either the immutable record it always was, or it belongs to an abandoned `design_id` that is retained for audit but never reused.

### 5.B Artifact / digest chain, canonical JSON profile — frozen (Revision 3 replacement)

**[IMPLEMENTATION DESIGN — FROZEN]** One concrete artifact layout, and no alternative, is frozen for future implementation:

```
results/confirmatory/<design_id>/
    registration_draft.json
    eligibility_manifest.json
    registration_manifest.json
    randomization_mc_provenance.json
    assignment_manifest.json
    final_analysis_manifest.json
```

This document creates none of those files now; it freezes their names, location, digest relationships, and the canonicalization/hashing algorithm only.

#### 5.B.1 No same-object digest alias — frozen (closure defect 1)

**Rule.** Every immutable artifact stores **exactly one** digest of itself: `self_digest`. No artifact stores a second field that is merely an alias of its own `self_digest` under a different name. Semantic names such as `registration_draft_digest`, `eligibility_manifest_digest`, `final_registration_digest`, `randomization_mc_provenance_digest`, and `assignment_digest` are names used **only by downstream artifacts** when referencing an *upstream* artifact's `self_digest`. They are never a same-object second field on the artifact that produced the value.

Frozen field inventory, per artifact (no artifact contains a same-object alias of its own `self_digest`):

```
registration_draft.json:
    stores: self_digest
    does NOT store: registration_draft_digest

eligibility_manifest.json:
    stores: registration_draft_digest  (= registration_draft.json.self_digest)
    stores: self_digest
    does NOT store: eligibility_manifest_digest

registration_manifest.json:
    stores: registration_draft_digest
    stores: eligibility_manifest_digest
    stores: matrix_digest
    stores: self_digest
    does NOT store: final_registration_digest

    Downstream meaning: final_registration_digest := registration_manifest.json.self_digest

randomization_mc_provenance.json:
    stores: final_registration_digest
    stores: self_digest
    does NOT store: randomization_mc_provenance_digest

    Downstream meaning: randomization_mc_provenance_digest := randomization_mc_provenance.json.self_digest

assignment_manifest.json:
    stores: final_registration_digest
    stores: randomization_mc_provenance_digest
    stores: self_digest
    does NOT store: assignment_digest

    Downstream meaning: assignment_digest := assignment_manifest.json.self_digest

final_analysis_manifest.json:
    stores: final_registration_digest
    stores: eligibility_manifest_digest
    stores: randomization_mc_provenance_digest
    stores: assignment_digest
    stores: runtime_snapshot_digests
    stores: statistic_spec_id
    stores: self_digest
```

`final_analysis_manifest.json` is itself terminal — nothing downstream references its `self_digest` by a semantic alias name in this design, so no alias-naming question arises for it.

#### 5.B.2 Canonical JSON profile — frozen, complete, no alternative

**Canonicalization algorithm (frozen, one algorithm, applies to every artifact above).** The canonical bytes of an artifact object (with `self_digest` already removed, per §5.B.3) are produced by exactly:

```python
json.dumps(
    object_without_self_digest,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
)
```

encoded as UTF-8. No other serializer, library, or option set is authorized.

Additional frozen rules, all mandatory:

- JSON objects only use string keys.
- Schema numeric fields that require exact decimal representation (e.g. `timeout_seconds`, every `*_delay_seconds` field in `retry_policy`) **must** be represented as canonical decimal strings (base-10, no exponent form, e.g. `"30"`, `"30.5"`) rather than binary floating-point JSON numbers. A canonical decimal string never carries leading zeros (other than a single `"0"` before a decimal point), never carries a trailing decimal point with no digits after it, and never carries a `+` sign.
- Integer-valued fields (e.g. `K`, `max_attempts`, `entropy_bytes`, `randomization_mc_samples`) remain ordinary JSON integers, never strings.
- `NaN`, `Infinity`, and `-Infinity` are forbidden anywhere in a canonical payload; `allow_nan=False` enforces this at serialization time, and any upstream value that would require one of these is a hard construction error, not a representable field.
- Arrays preserve registered order; arrays are never reordered or deduplicated by the canonicalization step itself (deduplication, where required — e.g. `retryable_error_classes`, §5.I — is a schema-level rule applied before canonicalization, not a canonicalization-time transformation).
- Object keys are sorted by Python's deterministic Unicode string ordering, exactly as exercised by `sort_keys=True` (i.e., ordinary code-point ordering of the key strings).
- Hash algorithm: SHA-256, applied once over the canonical UTF-8 byte sequence.
- Digest representation: lowercase 64-character hexadecimal string.

**Self-digest construction (frozen, one procedure, applies to every `self_digest` field on every artifact).**

1. Parse or construct the artifact object in memory.
2. Remove **only** its own `self_digest` field from the object (no other field is removed; in particular, no field named after a *different* alias is removed, since — per §5.B.1 — no such alias field exists on the artifact in the first place).
3. Canonicalize the remaining object exactly per the algorithm above.
4. UTF-8 encode the canonical string.
5. Compute SHA-256 over those bytes.
6. Lowercase-hex-encode the digest.
7. Persist the result as the artifact's `self_digest` field.

**Persisted artifact bytes (frozen).** The bytes written to disk are: the canonical JSON **including** the now-computed `self_digest` field, reserialized under the identical canonicalization algorithm (so the on-disk object, with `self_digest` present, is itself still sorted-key/no-whitespace/UTF-8 canonical JSON), followed by exactly one LF byte (`\n`). This presentation LF is a pure file-formatting convenience and is **not** part of any digest computation — it is appended only after every digest that will ever be computed for that write has already been computed, and a reader strips at most one trailing `\n` before doing anything else with the bytes.

**Verification (frozen, one procedure, used by every consumer).**

1. Read the persisted file bytes; strip at most one trailing `\n`.
2. Parse the remaining bytes as JSON.
3. Extract the claimed `self_digest` field.
4. Remove `self_digest` from the parsed object.
5. Recanonicalize the remaining object per the algorithm above.
6. Recompute SHA-256 over the recanonicalized UTF-8 bytes.
7. Constant-time/equality-compare the recomputed digest against the claimed `self_digest`.

Any mismatch at step 7, for any artifact, at any point: **fail closed**. No consumer proceeds on mismatch; every consumer fails closed to the token family named in §11.

#### 5.B.3 Frozen digest relationships (restated under the no-alias rule)

```
eligibility_manifest.json:
    registration_draft_digest   (reference to registration_draft.json.self_digest)
    self_digest

registration_manifest.json:
    registration_draft_digest   (reference to registration_draft.json.self_digest)
    eligibility_manifest_digest (reference to eligibility_manifest.json.self_digest)
    matrix_digest
    self_digest                 (referenced downstream as final_registration_digest)

randomization_mc_provenance.json:
    final_registration_digest   (reference to registration_manifest.json.self_digest)
    self_digest                 (referenced downstream as randomization_mc_provenance_digest)

assignment_manifest.json:
    final_registration_digest   (reference to registration_manifest.json.self_digest)
    randomization_mc_provenance_digest (reference to randomization_mc_provenance.json.self_digest)
    self_digest                 (referenced downstream as assignment_digest)

final_analysis_manifest.json:
    final_registration_digest
    eligibility_manifest_digest
    randomization_mc_provenance_digest
    assignment_digest
    runtime_snapshot_digests
    statistic_spec_id
    self_digest
```

**Fail-closed rule (restated):** any digest mismatch — a manifest's declared upstream reference field (e.g. `assignment_manifest.json.final_registration_digest`) not matching the live upstream artifact's own `self_digest`, or a manifest's own `self_digest` not verifying per §5.B.2's verification procedure — is a hard failure. No consumer proceeds on mismatch; every consumer fails closed to the same family of tokens named in §11.

### 5.C Execution row ↔ registered position binding — frozen (Revision 3 replacement: profile/design-id checks added)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze a canonical identity and a row-binding contract but omitted `confirmatory_profile`/`design_id` from the explicit reconciliation checklist even though both fields were already part of the row contract. Revision 3 closes that gap; the identity construction and digest-field names below are otherwise Revision 2's, restated under the §5.B.1 no-alias field names.

**`ConfirmatoryPositionV1` identity.** Each final registered position has a deterministic `position_id`, defined as the SHA-256 (lowercase hex, canonicalization algorithm of §5.B.2) over a canonical JSON object containing **exactly** these fields, no more, no fewer:

```
task_id
provider
model
repetition
provider_seed
slot
```

The treatment label is deliberately **excluded** from `position_id` because treatment assignment (`b_k`) is applied prospectively to a fixed position — the position's identity must not depend on which label it ends up receiving, or the identity itself would leak assignment information and could not be registered before `b_k` is drawn.

**Confirmatory execution-row contract (frozen).** Every confirmatory execution row must persist exactly these fields:

```
confirmatory_profile
design_id
final_registration_digest
eligibility_manifest_digest
assignment_digest
position_id
task_id
provider
model
repetition
provider_seed
slot
baseline_label
task_assignment_bit
qa_mode
runtime_snapshot_digest
runtime_identity_digest
observation_status
failure_class
error
primary endpoint value(s)
```

`confirmatory_profile` is frozen as the literal string:

```
"post_phaseP_confirmatory_randomization_v1"
```

**Frozen analyzer verification checklist (fourteen points, extended from Revision 2's twelve).** For every row, the analyzer (§5.G) must verify, **in the order given**, and fail closed on the first failure:

1. `confirmatory_profile` on the row exactly equals `"post_phaseP_confirmatory_randomization_v1"`.
2. `design_id` on the row exactly equals the loaded registration manifest's `design_id`.
3. `final_registration_digest` matches the loaded final registration's `self_digest`.
4. `eligibility_manifest_digest` matches the loaded eligibility manifest's `self_digest`.
5. `assignment_digest` matches the loaded assignment manifest's `self_digest`.
6. `position_id` is a member of the registered position set.
7. All identity fields on the row (`task_id`, `provider`, `model`, `repetition`, `provider_seed`, `slot`) independently reproduce the claimed `position_id` under the §5.C hash construction (a row cannot merely *claim* a `position_id`; the analyzer recomputes it), and independently reproduce the registered `ConfirmatoryPositionV1` identity for that `position_id` (task_id/provider/model/repetition/provider_seed/slot exactly match the registered values, not merely hash to the same digest).
8. Exactly one row exists for every expected physical execution.
9. No duplicate confirmatory position execution exists.
10. No extra row claiming confirmatory membership exists under this `confirmatory_profile`/`design_id` (a row's `position_id` must be in the registered confirmatory set of *this* design, not merely well-formed, and a row carrying the correct `confirmatory_profile` string but a foreign `design_id` is rejected by check 2 above, never silently accepted as belonging to this design).
11. `task_assignment_bit` on the row equals the persisted task bit for that `task_id` in the assignment manifest.
12. `baseline_label` equals the registered `S_k(position)`.
13. `qa_mode` equals the realized label produced from `S_k(position)` and `b_k` (i.e. `resolve_label(baseline_label, b_k)`, §5.D).
14. Runtime identity binding passes the `RuntimeSnapshotV1` contract (§5.I): the referenced `runtime_snapshot_digest` verifies as a valid snapshot `self_digest`, and the row's `runtime_identity_digest` equals the frozen registration-expected `runtime_identity_digest`.

Any mismatch at any of the fourteen checks: the analyzer returns `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`. There is no statistical fallback, no partial computation, and no warning-only path. A row bearing a legacy (absent or different) `confirmatory_profile` is never routed through this checklist at all — it is not a confirmatory row and stays on the legacy analysis path (§9).

### 5.D S_k / C(S_k) label application — frozen (Revision 2, not reopened)

**[IMPLEMENTATION DESIGN — FROZEN]** Exact code boundary, expressed as three owned responsibilities that must never merge:

1. **Existing deterministic schedule `S_k`** — owned by `_ordered_treatments` (`runner.py:703-722`, Fact 1), **left unmodified**. It continues to decide, per position, which physical call slot gets which label under `b_k = 0`.
2. **The random bit `b_k`** — owned exclusively by `assignment_manifest.json` (§5.M), read once per task at the start of confirmatory execution for that task, cached per task, never re-read per position.
3. **Final treatment label** — computed by a pure function in `src/iqa_soa/experiment/confirmatory_assignment.py`:

```
def resolve_label(baseline_label: QAMode, b_k: int) -> QAMode:
    return baseline_label if b_k == 0 else complement(baseline_label)
```

`complement(OFF) = FULL`, `complement(FULL) = OFF`. `resolve_label` is called once per scheduled position, taking `baseline_label` from the existing `_ordered_treatments` output (unmodified) and `b_k` from the assignment manifest. The confirmatory runner (§5.J) calls `resolve_label` immediately before dispatching a confirmatory-mode execution; non-confirmatory runs never call it and are byte-for-byte unaffected (§9).

Invariants: `resolve_label` is total, pure, and involutive in `b_k`: `resolve_label(resolve_label(x, b), b) == x`. Balance invariant: because `complement` is applied uniformly to every position nested in task `k`, the OFF/FULL count within task `k` is preserved exactly under either bit value — matches design decision §6 requirement 2 verbatim. Single-`b_k`-shared invariant: enforced structurally because `resolve_label` is invoked with the **same** `b_k` value, read once per task and cached, for every model/provider/repetition/slot under that task.

### 5.E State isolation strategy — frozen (Revision 2, not reopened; PR-4)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze one strategy: **every registered physical confirmatory position receives a fresh local provider/client execution context.** No mutable provider object, session, conversation, tool state, or sandbox state is reused across positions, without exception.

Frozen interface:

```
class ProviderFactory(Protocol):
    def create_for_position(self, position: ConfirmatoryPositionV1) -> AgentProvider: ...
```

The confirmatory runner (§5.J) obtains exactly one new `AgentProvider` instance per position via `ProviderFactory.create_for_position(position)`; it never reuses a provider instance across two distinct `position_id` values. This closes the local half of `POSITION_STATE_ISOLATION`: locally recreatable state (sandbox instance, tool registry instance, conversation/session object) is mandatorily fresh per position, by construction, not by argument.

Provider-side infrastructure that cannot be locally recreated — routing, rate-limit buckets, shared serving infrastructure on the provider's own side — remains outside what a fresh local context can prove, and is assessed instead under `INFRASTRUCTURE_SYMMETRY` (§5.F, PR-5) together with the PR-4 evidence record this design still requires per position. This document still does not claim that any real provider passes PR-4; that remains **[DEFERRED VERIFICATION]**.

### 5.F Infrastructure symmetry (PR-5)

**[IMPLEMENTATION DESIGN]** Candidate leak paths where OFF vs FULL could be distinguished by infrastructure outside the intended treatment channel, enumerated for future audit (not resolved here — this is evidence-gathering, not architecture, and remains open by design):

1. **Prompt/system-message content**: does the OFF/FULL label change anything about the prompt sent to the provider beyond the intended `qa_mode` semantics.
2. **Gateway-path latency signature**: `QAMode.OFF` deterministically short-circuits to `ALLOW` without invoking the QA chain (`src/iqa_soa/iqa/gateway.py:49-53, 63-71`) — an intended behavioral difference, but a candidate infrastructure leak if it also crosses a provider-side rate-limit/cache-tier boundary.
3. **Evidence volume**: FULL emits richer evidence; if evidence writing shares I/O capacity with the provider call path, a volume-dependent side channel is possible.
4. **Provider/model selection**: any code path that picks a different provider endpoint, connection pool, or hardware pool conditional on `qa_mode` rather than solely on `(provider, model)` stratum.

Frozen artifact: an `infrastructure_symmetry_audit` record, embedded inside `eligibility_manifest.json` (§5.A Stage B), listing each candidate channel above with a `CHECKED`/`NOT_CHECKED` status and an evidence reference. `INFRASTRUCTURE_SYMMETRY` may only `PASS` when every channel is `CHECKED` with no asymmetry found. This predicate, like the others, is evaluated once, in Stage B, before `FINAL_REGISTRATION_FROZEN`, and never re-evaluated in place afterward (§5.A).

### 5.G Total observation / fail-closed analyzer, module ownership — frozen (PR-7 core; row-checklist reference updated)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze a dedicated module: `src/iqa_soa/metrics/confirmatory.py`, with a single public entry point:

```
def analyze_confirmatory_randomization(...) -> ConfirmatoryResult: ...
```

This wrapper performs, in this fixed order:

1. Loads and validates all bound manifests (`registration_manifest.json`, `eligibility_manifest.json`, `assignment_manifest.json`, `randomization_mc_provenance.json` — which **always** exists per §5.L, in both `EXACT_ENUMERATION` and `MONTE_CARLO` mode), verifying every digest binding in §5.B and that the provenance artifact's `randomization_mode` equals the registration manifest's frozen `randomization_mode`.
2. Reconciles registered positions and observed rows per the fourteen-point checklist of §5.C, including the `confirmatory_profile`/`design_id` checks.
3. Validates observation status / failure taxonomy per §5.H.
4. Validates runtime/assignment/label identity per §5.C checks 11-14 and §5.I.
5. Only after steps 1-4 all pass does it invoke the frozen task-statistic computation (§5.K equivalence design), reusing `statistics.py`'s pure aggregation as a **computation**, never by falling through `_apply_task_cluster_inference`'s own clustering/dropping behavior (Fact 3).

Legacy `analyze_before_after(...)` remains completely unchanged and is never called through, or from within, the confirmatory path; it is called only through its own existing call sites unless a caller explicitly and separately invokes `analyze_confirmatory_randomization`. Confirmatory mode is strictly opt-in: a caller must possess a `registration_manifest`, `eligibility_manifest`, `assignment_manifest`, and `randomization_mc_provenance` to invoke it at all.

The critical structural property, and the fix for Fact 3: missingness is checked by iterating the **registered** position list from `registration_manifest.json`, independent of whatever rows happen to exist, rather than iterating whatever survived pairing. If even one registered confirmatory position's primary endpoint fails the observation check (§5.H), `analyze_confirmatory_randomization` returns `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` and computes no statistic on any subset.

### 5.H Observation / failure taxonomy — frozen (Revision 2, not reopened)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze an explicit taxonomy so confirmatory analysis never infers observability from `endpoint is None` / `endpoint is not None` alone.

```
observation_status ∈ {
    OBSERVED,
    UNOBSERVED_INFRASTRUCTURE,
    UNOBSERVED_INSTRUMENTATION
}

failure_class ∈ {
    NONE,
    PROVIDER_FAILURE,
    TIMEOUT,
    TRANSPORT_FAILURE,
    RUNTIME_FAILURE,
    INSTRUMENTATION_FAILURE
}
```

The confirmatory collection boundary — `src/iqa_soa/metrics/collector.py`, extended additively (§11) — must explicitly produce both fields from live runner/failure telemetry for every confirmatory row; it never leaves them to be inferred later from the endpoint value.

`observation_status = OBSERVED` is permitted only if all three hold: (a) the scheduled position actually executed through the required observation boundary; (b) the primary endpoint's generating instrumentation completed; (c) no fatal provider/runtime/instrumentation failure makes the endpoint uninterpretable.

**Observed zero.** An endpoint value of `0`, `False`, or `0.0` together with `observation_status = OBSERVED` is an **OBSERVED ZERO** and remains in analysis exactly as any other observed value would.

**Fail-closed rule.** Any `observation_status != OBSERVED` for any registered applicable confirmatory primary endpoint causes `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`, even if the legacy collector happened to materialize a non-null `False`/`0` value for that same row under its own (unchanged) historical interpretation. This reconciliation gate is frozen to run strictly **before** any code path resembling `_apply_task_cluster_inference` is reached inside the confirmatory analyzer — `analyze_confirmatory_randomization` (§5.G) performs it as step 3, before step 5's statistic computation, never after.

### 5.I Runtime-configuration snapshot — frozen (Revision 3 replacement: identity vs. capture metadata)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 said runtime snapshots must "match" while its own schema contained naturally varying fields (`captured_at`, `self_digest`), which is self-contradictory. Revision 3 freezes a **two-layer** `RuntimeSnapshotV1` contract that separates invariant runtime identity from capture metadata.

**`RuntimeSnapshotV1` contains exactly these fields, no more, no fewer:**

```
schema_version
provider_name
model
endpoint
provider_config_digest
provider_parameters_digest
timeout_seconds
retry_policy
tool_contract_policy
native_tool_adapter_version
package_source_sha256
python_version
artifact_version
prompt_digest
experiment_config_digest
models_config_digest
environment_fingerprint
runtime_identity_digest
captured_at
self_digest
```

#### 5.I.1 Runtime identity payload

`runtime_identity_digest` is SHA-256 (canonicalization algorithm of §5.B.2, lowercase hex) over a canonical JSON object containing **exactly** these invariant fields:

```
schema_version
provider_name
model
endpoint
provider_config_digest
provider_parameters_digest
timeout_seconds
retry_policy
tool_contract_policy
native_tool_adapter_version
package_source_sha256
python_version
artifact_version
prompt_digest
experiment_config_digest
models_config_digest
environment_fingerprint
```

It **excludes**: `runtime_identity_digest` (itself), `captured_at`, `self_digest`.

`provider_parameters_digest` hashes the **complete** serialized provider parameter mapping used for execution (every key the provider call actually receives), never a hand-selected subset. `retry_policy` records the complete retry configuration verbatim, including the case of zero configured retries — it is never omitted or left implicit when retries are disabled.

#### 5.I.2 Capture metadata — never an equality invariant

`captured_at` and `self_digest` are **metadata**, not equality invariants. Each snapshot has its own `captured_at` and therefore, ordinarily, its own distinct `self_digest`, because `self_digest` is computed over the entire object (§5.B.2) including `captured_at` and `runtime_identity_digest`. **The runtime identity comparison never compares snapshot `self_digest` equality across different capture times.** It compares `runtime_identity_digest` exactly, and only that field, across captures.

#### 5.I.3 Environment fingerprint — `EnvironmentIdentityV1`, frozen field set

`environment_fingerprint` is SHA-256 (§5.B.2 canonicalization) over a canonical JSON object containing **exactly** these fields, no more, no fewer, with no "at minimum," "for example," or future field-selection choice remaining:

```
platform_system
platform_release
platform_machine
python_implementation
python_version
package_source_sha256
provider_endpoint
native_tool_adapter_version
```

#### 5.I.4 Timeout / retry representation — frozen schema (values remain deferred)

`timeout_seconds` is a canonical decimal string in base-10, with no exponent form (§5.B.2). Examples of valid schema shape: `"30"`, `"30.5"`. The architecture does not select the future timeout *value*.

`retry_policy` is a structured object with exactly:

```
max_attempts
backoff_kind
initial_delay_seconds
max_delay_seconds
retryable_error_classes
```

Rules: `max_attempts` is an integer ≥ 1; `backoff_kind` is one of `"NONE"`, `"FIXED"`, `"EXPONENTIAL"`; `initial_delay_seconds` and `max_delay_seconds` are canonical decimal strings (§5.B.2); `retryable_error_classes` is a sorted, unique array of frozen error-class strings. Actual retry values remain deferred registered values; the schema itself is not deferred.

#### 5.I.5 Three capture points — frozen

```
1. registration_expected_runtime_snapshot
   captured before eligibility/final registration and bound into the proposed
   runtime configuration.

2. pre_execution_runtime_snapshot
   captured immediately before each physical execution.

3. analysis_runtime_snapshot
   captured when confirmatory analysis validates the environment.
```

**Required invariant:** all relevant `runtime_identity_digest` values equal the registration-expected `runtime_identity_digest`. Their `captured_at` and `self_digest` are *expected to differ* and are **not compared**.

Every execution row stores:

```
runtime_snapshot_digest   = that position's pre_execution_runtime_snapshot.self_digest
runtime_identity_digest   = that snapshot's runtime_identity_digest
```

The analyzer verifies **both**: (a) the referenced snapshot artifact's `self_digest` verifies per §5.B.2's verification procedure; (b) the row's/snapshot's `runtime_identity_digest` equals the frozen registration-expected `runtime_identity_digest`.

#### 5.I.6 Frozen failure tokens

A runtime-identity mismatch discovered during eligibility/pre-registration assessment yields `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` for that stratum (it simply never becomes `CONFIRMATORY_ELIGIBLE`).

After final registration: a `runtime_identity_digest` mismatch, wherever detectable before execution (pre-execution snapshot vs. registration-expected snapshot, checked before the execution is dispatched), causes the runner to **refuse** that execution/resume outright. If a `runtime_identity_digest` mismatch is instead only discovered during analysis (e.g. because the analysis-time recorded snapshot was never checked pre-execution), the outcome is `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`. There is no third outcome and no silent acceptance of a partial-match or capture-metadata-only mismatch — a `captured_at` or `self_digest` difference alone, with `runtime_identity_digest` equal, is never a failure of any kind.

### 5.J Confirmatory runner entry point — frozen (Revision 2, not reopened)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze a dedicated, wholly new module: `src/iqa_soa/experiment/confirmatory.py`, with a single public entry point:

```
def run_confirmatory_experiment(
    registration_manifest_path,
    eligibility_manifest_path,
    assignment_manifest_path,
    randomization_mc_provenance_path,
    provider_factory,
    output_path,
    ...
) -> None: ...
```

It requires all five named artifact/config arguments; none is optional, none has a default that silently skips a gate (`randomization_mc_provenance_path` is always required — per §5.L the provenance artifact always exists, in both randomization modes). It enforces the state machine (§6): it refuses to begin any execution unless `assignment_manifest.json` and `randomization_mc_provenance.json` already exist and digest-validate against `registration_manifest.json`. It reads `b_k` once per task (§5.D), caches it, and calls `resolve_label` per position. It obtains one fresh `AgentProvider` per position via `provider_factory.create_for_position(position)` (§5.E) — no other code path in this module constructs a provider. Before dispatching each position's execution, it captures `pre_execution_runtime_snapshot` and refuses the execution if that snapshot's `runtime_identity_digest` does not equal the registration-expected `runtime_identity_digest` (§5.I.6). It may reuse existing `ExperimentRunner` internals **only after** all prospective confirmatory gates (state machine, digest checks, eligibility check, runtime-identity check) pass; it never bypasses `ExperimentRunner`'s existing non-confirmatory machinery when doing so. Legacy `ExperimentRunner` behavior, including its existing constructor and existing call sites, is completely unmodified by the existence of this module; `run_confirmatory_experiment` is the only entry point into confirmatory execution, and there is no constructor flag on `ExperimentRunner` that does the same thing.

### 5.K Statistic implementation equivalence (PR-8)

**[IMPLEMENTATION DESIGN — FROZEN]** `statistic_spec_id` is frozen as the literal string:

```
"confirmatory_task_sign_flip_v1"
```

No `<semver>` placeholder is used anywhere in this document or in any future artifact schema derived from it; `statistic_spec_id` is the single opaque versioned identifier, and a change to the statistic's implementation requires minting a new literal id, never bumping a semver field.

The statistic computation itself: registered `K` (from `len(registration_manifest.confirmatory_positions)` grouped by task, never from however many task differences happen to be nonzero at analysis time); nested equal-weight mean over model strata, then repetitions/seeds, then providers, within each task cluster — structurally identical to `_apply_task_cluster_inference`'s existing nesting (`statistics.py:790-796`), reused as a **computation**, never by falling through the function's own clustering/dropping behavior (Fact 3); `FULL − OFF` orientation for `D_k`; relative sign `r_k(b) = 1 - 2*(b_k XOR b_obs_k)` (design decision §7.1); zero-difference blocks retained in `K`, only `K_plus` used for enumeration/MC granularity reporting, never for matrix membership; no data-dependent membership changes — the position set comes from `registration_manifest.json` only, frozen at Stage C, never adjusted after observing `D_k^obs`.

Equivalence-proof approach: a future property-based test (§10) asserting that, on a fully-observed synthetic matrix, `analyze_confirmatory_randomization`'s per-task differences numerically equal what `_apply_task_cluster_inference` would compute over the same rows.

### 5.L Exact / Monte Carlo randomization and MC provenance — frozen (Revision 3 replacement: tagged-union sentinel)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 left `randomization_mc_provenance.json` as a K>16-only artifact, which is an absent-vs-sentinel choice the closure review flagged as unresolved. Revision 3 freezes one tagged-union schema so the six-artifact chain remains uniform: **`randomization_mc_provenance.json` exists in both exact and Monte Carlo modes.** No MC seed is ever generated for exact mode.

#### 5.L.1 Tagged-union schema

```
randomization_mode ∈ {
    "EXACT_ENUMERATION",
    "MONTE_CARLO"
}
```

**Common fields, present in both modes:**

```
schema_version
confirmatory_profile
design_id
final_registration_digest
randomization_mode
created_at
self_digest
```

**Mode consistency (frozen).** `registration_manifest.json` freezes `randomization_mode`, derived deterministically from registered `K`:

```
K <= 16  →  EXACT_ENUMERATION
K > 16   →  MONTE_CARLO
```

The provenance artifact's `randomization_mode` **must equal** the registration manifest's frozen `randomization_mode`. Wrong mode, a missing provenance artifact, forbidden fields present, or required fields missing: `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`. There is no remaining absent-vs-sentinel choice: the artifact is mandatory in every design, in exactly one of the two tagged shapes below.

#### 5.L.2 Exact mode: `K <= 16`

For `randomization_mode = "EXACT_ENUMERATION"`, the artifact additionally contains:

```
exact_support_size = 2^K
K
statistic_spec_id = "confirmatory_task_sign_flip_v1"
```

and **must contain no seed material**. These fields **must be absent**:

```
seed_hex
entropy_bytes
source_kind
source_api
seed_encoding
rng_library
rng_bit_generator
numpy_version
randomization_mc_samples
generated_at
```

No entropy API is called. No seed is generated. `_task_sign_flip_p_value`'s existing exact-enumeration branch (`statistics.py:861-871`) is reused verbatim as a computation called from `confirmatory.py` (metrics), because design decision §7.4 already accepts this branch prospectively unchanged. Its `self_digest` is still computed normally, per §5.B.2, over the fields it actually contains. `assignment_manifest.json` **always** stores `randomization_mc_provenance_digest` — a reference to this artifact's `self_digest` — even in exact mode (§5.B.1, §5.B.3), so the artifact/digest/state-machine shape is identical across exact and Monte Carlo designs without fabricating an unnecessary seed.

#### 5.L.3 Monte Carlo mode: `K > 16`

For `randomization_mode = "MONTE_CARLO"`, the already-frozen architecture (Revision 2, not reopened — independence and timing unchanged) applies: `secrets.token_bytes(32)`, interpreted as an unsigned 256-bit big-endian integer (`seed_int`), feeding `numpy.random.Generator(numpy.random.PCG64(seed_int))`, with the registered Monte Carlo sample count `M` and the registered NumPy version.

The artifact additionally contains, plus the common fields of §5.L.1:

```
K
statistic_spec_id = "confirmatory_task_sign_flip_v1"
source_kind = "PYTHON_SECRETS_TOKEN_BYTES"
source_api = "secrets.token_bytes"
entropy_bytes = 32
seed_hex
seed_encoding = "uint256_big_endian"
rng_library = "numpy"
rng_bit_generator = "PCG64"
numpy_version
randomization_mc_samples
generated_at
```

It is generated **after** `FINAL_REGISTRATION_FROZEN`, **before** assignment generation, **before** any confirmatory execution — and therefore necessarily exists before `B_obs` is realized, before any endpoint exists, and before any failure/loss information exists.

`bootstrap_seed` (existing field, `statistics.py:743`) continues to govern only `_bootstrap_mean_ci` and is **never** read by, derived from, or fed into the confirmatory Monte Carlo path. The architecture and public API of `confirmatory.py` (metrics) does not accept a `bootstrap_seed`-shaped argument at all for the MC draw — there is no parameter through which a caller could pass it.

**At analysis time**, for `MONTE_CARLO` mode the analyzer verifies: loaded NumPy version equals the persisted registered `numpy_version`; the bit generator equals `PCG64`; `M` equals the registered `randomization_mc_samples`; the provenance file's `self_digest` verifies (§5.B.2); and the provenance's `generated_at` predates both assignment generation and every execution row's timestamp. For `EXACT_ENUMERATION` mode the analyzer verifies instead that none of the forbidden seed-material fields (§5.L.2) is present, and that `exact_support_size == 2^K`. Any mismatch, forbidden field, missing required field, or missing provenance in either mode: `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`.

Plus-one formula, reused verbatim (MC mode only): `(count_at_least_as_extreme + 1) / (samples + 1)` (`statistics.py:875` pattern) — design decision §7.4.2 already determines this formula implements `MONTE_CARLO_PLUS_ONE_VALIDITY` exactly, conditional only on provenance discipline. `p_MC` is always reported together with `randomization_mc_samples` (`M`), never presented as an exact-enumeration result.

Legacy callers of `_task_sign_flip_p_value`/`bootstrap_seed` outside the confirmatory path may retain their existing behavior unchanged.

### 5.M Production assignment randomness — frozen (Revision 2, not reopened; PR-1/PR-6)

**[IMPLEMENTATION DESIGN — FROZEN]** Revision 2 froze the production assignment source as Python `secrets.randbits(1)`, called **exactly once per confirmatory task cluster**, in canonical sorted `task_id` order.

Frozen interface, `src/iqa_soa/experiment/confirmatory_assignment.py`:

```
class AssignmentRandomSource(Protocol):
    def draw_bit(self) -> int: ...
```

Production implementation:

```
class SecretsAssignmentRandomSource:
    def draw_bit(self) -> int:
        return secrets.randbits(1)
```

Test-only implementation: `DeterministicAssignmentRandomSource` — accepts an explicit, pre-supplied bit sequence for test fixtures only. It is **mandatorily rejected** whenever `confirmatory_profile == "post_phaseP_confirmatory_randomization_v1"` outside of a test context; production assignment generation refuses to proceed if the supplied `AssignmentRandomSource` is a `DeterministicAssignmentRandomSource`.

Persisted provenance fields (frozen, exact):

```
source_kind = "PYTHON_SECRETS_RANDBITS"
source_api = "secrets.randbits"
python_version
generation_started_at
generation_completed_at
```

**Frozen generation ordering.** Assignment generation: occurs only after `FINAL_REGISTRATION_FROZEN`; occurs after `randomization_mc_provenance.json` is persisted (§5.L, in either mode); occurs strictly before any confirmatory execution; writes `assignment_manifest.json` atomically; refuses if `assignment_manifest.json` already exists for the `design_id` (`DuplicateAssignmentError`); never regenerates a missing or corrupt assignment automatically — a missing/corrupt assignment is a hard refusal, requiring explicit human re-authorization under the abandon-and-recreate rule of §5.A, never an automatic retry.

**One bit per task, shared by every nested position.** `draw_bit()` is called once per task cluster (`K` total calls, in sorted `task_id` order), never once per position, model, provider, or repetition. Every nested position under a given task loads that task's single persisted bit; there is no per-position bit lookup path in the schema or the interface.

### 5.N File / module ownership — frozen (see §11 for the authoritative list)

The full future module list, with no alternative layout, is given in §11. §8 (file plan) and §11 must be read together; §11 is authoritative wherever the two could be read as disagreeing, since §11 is the closure-mandated frozen list.

### 5.O Resume behavior — frozen (Revision 3: digest/runtime references updated)

**[IMPLEMENTATION DESIGN — FROZEN]** A confirmatory run may resume only if every one of the following holds:

- `final_registration_digest` matches (against `registration_manifest.json.self_digest`);
- `eligibility_manifest_digest` matches;
- `assignment_digest` matches;
- `randomization_mc_provenance_digest` matches;
- `randomization_mode` on the loaded provenance artifact equals the registration manifest's frozen `randomization_mode`;
- every existing execution row's `runtime_identity_digest` equals the registration-expected `runtime_identity_digest` (§5.I.5-5.I.6) — a later `captured_at`/`self_digest` on a fresh `pre_execution_runtime_snapshot` taken for the resumed positions is expected and is not compared;
- `statistic_spec_id` matches;
- existing execution rows reconcile exactly with the registered positions already marked complete (§5.C fourteen-point checklist, applied to every existing row);
- no duplicate row exists.

Resume may execute **only** the still-missing registered positions. Resume must never: redraw assignment; regenerate the MC seed; reclassify provider eligibility; alter matrix membership; or rerun an already-persisted, already-completed position. Any mismatch in the checklist above — including a `runtime_identity_digest` mismatch, which is refused immediately as it is detectable before execution — routes to: `REFUSE RESUME` where the mismatch is detected before any execution is dispatched, and no confirmatory p-value is produced from the partial or resumed run under that mismatch.

---

## 6. State machine — frozen

**[IMPLEMENTATION DESIGN — FROZEN]** The live lifecycle is exactly:

```
REGISTRATION_DRAFT
    ↓
ELIGIBILITY_FROZEN
    ↓
FINAL_REGISTRATION_FROZEN
    ↓
MC_PROVENANCE_PERSISTED
    ↓
ASSIGNMENT_PERSISTED
    ↓
EXECUTION_IN_PROGRESS
    ↓
EXECUTION_COMPLETE
    ↓
CONFIRMATORY_ANALYSIS_COMPLETE
```

with one alternative terminal path, reachable from execution validation or from analysis validation (never bypassed, never silently skipped):

```
* --(any validation failure)--> CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE
```

For each transition, the required artifact, digest verification, mutation permitted, mutation forbidden, and refusal behavior are frozen as follows:

| Transition | Required artifact(s) | Digest verification | Mutation permitted | Mutation forbidden | Refusal behavior |
|---|---|---|---|---|---|
| `→ REGISTRATION_DRAFT` | `registration_draft.json` written | `self_digest` computed and stored | Draft may be superseded by a **new** draft under a new `design_id`; never edited in place once written | Editing an existing `registration_draft.json` in place | N/A (first stage; malformed draft simply is not written) |
| `REGISTRATION_DRAFT → ELIGIBILITY_FROZEN` | `eligibility_manifest.json`, referencing `registration_draft.json.self_digest` as `registration_draft_digest` | `eligibility_manifest.registration_draft_digest == registration_draft.json.self_digest` (verified per §5.B.2) | None once finalized — the eligibility manifest becomes immutable at write time | Any later edit, re-assessment, or promotion of any stratum's disposition | Refuse to finalize if any of the four predicates is missing a disposition for any proposed stratum |
| `ELIGIBILITY_FROZEN → FINAL_REGISTRATION_FROZEN` | `registration_manifest.json`, referencing `registration_draft.json.self_digest` and `eligibility_manifest.json.self_digest` | Both reference digests checked against the live upstream artifacts' `self_digest` (§5.B.2) | None — immutable once `registration_state: FINAL_REGISTRATION_FROZEN` is set | Adding/removing any task, provider, model, or position from the confirmatory matrix; including any non-`CONFIRMATORY_ELIGIBLE` stratum in the confirmatory matrix | Refuse to freeze if any confirmatory-matrix stratum's eligibility disposition is not `CONFIRMATORY_ELIGIBLE` |
| `FINAL_REGISTRATION_FROZEN → MC_PROVENANCE_PERSISTED` | `randomization_mc_provenance.json` (always required, in either tagged-union mode, §5.L) | `randomization_mc_provenance.final_registration_digest == registration_manifest.json.self_digest`; `randomization_mc_provenance.randomization_mode == registration_manifest.randomization_mode` | None — immutable once written | Regenerating the seed (MC mode) or fabricating seed material (exact mode) for the same `design_id` | Refuse assignment generation if the provenance artifact is absent, wrong-mode, or contains a forbidden/missing field for its declared mode |
| `MC_PROVENANCE_PERSISTED → ASSIGNMENT_PERSISTED` | `assignment_manifest.json` | `assignment_manifest.final_registration_digest` and `.randomization_mc_provenance_digest` both checked against live upstream `self_digest` values | None — immutable once written | Any second `persist_assignment` call for the same `design_id` | `DuplicateAssignmentError` |
| `ASSIGNMENT_PERSISTED → EXECUTION_IN_PROGRESS` | none new; reads all prior artifacts | All prior digests re-verified at the start of execution; registration-expected `runtime_identity_digest` established | Execution rows are appended, never edited after being written | Editing/removing an already-written execution row | `AssignmentNotPersistedError` if entered without a valid assignment manifest |
| `EXECUTION_IN_PROGRESS → EXECUTION_COMPLETE` | none new | Row-set reconciled against registered positions (§5.C, fourteen-point checklist); each row's `runtime_identity_digest` checked against the registration-expected value (§5.I) | None to prior artifacts | Any mutation of `registration_manifest.json`, `eligibility_manifest.json`, or `assignment_manifest.json` | Incomplete row set keeps the run in `EXECUTION_IN_PROGRESS` (or, on resume failure, routes to `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`, §5.O) |
| `EXECUTION_COMPLETE → CONFIRMATORY_ANALYSIS_COMPLETE` \| `→ CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` | `final_analysis_manifest.json` | Every digest in §5.B.3's `final_analysis_manifest.json` block checked | None — `final_analysis_manifest.json` is immutable once written | Recomputing/overwriting an existing `final_analysis_manifest.json` for the same `design_id` | Any of §5.C/§5.H/§5.I/§5.L checks failing routes to `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` instead of `CONFIRMATORY_ANALYSIS_COMPLETE` |

**Critical invariant, restated:** `FINAL_REGISTRATION_FROZEN` is the **first** state in which the final confirmatory matrix exists. Eligibility assessment occurs strictly before it (`ELIGIBILITY_FROZEN` precedes `FINAL_REGISTRATION_FROZEN` in the ordering above). No confirmatory membership change is possible afterward, under any transition in this table. `randomization_mc_provenance.json` is required in **every** design, regardless of `K` (§5.L) — there is no state-machine path that skips `MC_PROVENANCE_PERSISTED`.

---

## 7. PR-1 .. PR-10 implementation matrix — frozen, all rows Class A

**[IMPLEMENTATION DESIGN — FROZEN]** Every row below names a single concrete implementation surface. No row leaves an architecture choice open for a future engineer. Revision 3 repairs PR-1, PR-3, PR-5, PR-7, PR-9, and PR-10 to reference the corrected digest-alias-free schema, the mandatory tagged-union MC provenance artifact, the extended row checklist, and the two-layer runtime-identity contract; PR-2, PR-4, PR-6, PR-8 are unchanged from Revision 2.

| PR | Frozen requirement | Frozen implementation | Files/symbols | Evidence | Tests | Failure token |
|---|---|---|---|---|---|---|
| PR-1 | One independent fair bit per task cluster, drawn after final freeze; assignment self-digest persistence unambiguous | `SecretsAssignmentRandomSource.draw_bit()` (`secrets.randbits(1)`), called once per task, sorted `task_id` order; final-registration prerequisite; atomic assignment persistence with single `self_digest` field (no `assignment_digest` alias on the artifact itself, §5.B.1); duplicate refusal | `src/iqa_soa/experiment/confirmatory_assignment.py: AssignmentRandomSource, SecretsAssignmentRandomSource, persist_assignment` | `assignment_manifest.json` provenance fields (§5.M) | one-bit-per-task test, duplicate-refusal test, self-digest-round-trip test | `DuplicateAssignmentError` |
| PR-2 | `S_k`/`C(S_k)` exact label complements, both balanced | `resolve_label(baseline_label, b_k)` pure function | `src/iqa_soa/experiment/confirmatory_assignment.py: resolve_label, complement` | involution + balance tests | complement involution test, balance test | n/a (pure function) |
| PR-3 | Assignment persisted before first treatment-level execution, immutable after; one persisted task bit shared across all nested positions; `confirmatory_profile`/`design_id` bound concretely to every row | `run_confirmatory_experiment(...)` (§5.J); state machine (§6): `ASSIGNMENT_PERSISTED` precedes `EXECUTION_IN_PROGRESS`; row writer stamps `confirmatory_profile`/`design_id` on every row from the loaded registration manifest, never from caller input | `src/iqa_soa/experiment/confirmatory.py: run_confirmatory_experiment` | state-machine transition log; row `confirmatory_profile`/`design_id` fields | no-execution-before-assignment-persistence test, shared-bit test, profile/design-id stamping test | `AssignmentNotPersistedError` |
| PR-4 | `POSITION_STATE_ISOLATION` | `ProviderFactory.create_for_position(position)`; fresh local provider/session/sandbox/tool state mandatorily constructed per position; actual provider evidence remains deferred | `src/iqa_soa/experiment/confirmatory.py` (call site), `ProviderFactory` interface | `isolation_evidence` per position | fresh-instance-per-position structural test | `DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED` |
| PR-5 | `INFRASTRUCTURE_SYMMETRY`; runtime identity comparison fully frozen | `RuntimeSnapshotV1` two-layer contract (§5.I: `runtime_identity_digest` over invariant fields, `captured_at`/`self_digest` as non-compared metadata) + `infrastructure_symmetry_audit` record, complete symmetry evidence schema | `src/iqa_soa/experiment/confirmatory_eligibility.py` | audit record, four candidate channels checked; registration-expected `runtime_identity_digest` recorded | routing-asymmetry probe tests (future); runtime-identity-vs-capture-metadata unit tests | `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY`, `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` |
| PR-6 | `B ⊥ Ω` assignment exogeneity | `secrets.randbits` assignment generation with no experimental-data input; frozen pre-execution artifact timing (§5.M, §6) | `confirmatory_assignment.py` | draw timestamp precedes first execution timestamp | timing-order test | n/a — enforced by state machine (§6) |
| PR-7 | `TOTAL_OBSERVATION` prospective + realized fail-closed check; row reconciliation includes profile/design and runtime identity | Strict `confirmatory.py` (metrics) gate: fourteen-point position/label/digest/profile/design-id/runtime-identity/failure reconciliation (§5.C, §5.G, §5.H, §5.I) | `src/iqa_soa/metrics/confirmatory.py` | `missing_positions` / observation-status report in `ConfirmatoryResult` | missing-position, missing-endpoint, non-OBSERVED, wrong-profile, foreign-design-id, runtime-identity-mismatch tests | `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`; prospective-only: `DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL` |
| PR-8 | Statistic implementation equivalence | `statistic_spec_id = "confirmatory_task_sign_flip_v1"` | `src/iqa_soa/metrics/confirmatory.py`, `statistics.py` (read-only reuse) | `statistic_spec_id` in registration manifest | statistic-equivalence property test | `STATISTIC_VERSION_MISMATCH` |
| PR-9 | Exact K≤16 sentinel / Monte Carlo K>16, assignment independence, exact-mode and MC-mode completely frozen | Mandatory tagged-union `randomization_mc_provenance.json` in both modes (§5.L); exact mode: no seed fields, `exact_support_size = 2^K`; MC mode: `secrets.token_bytes(32)`, NumPy `PCG64`, pinned recorded NumPy version; pre-assignment/pre-execution generation | `src/iqa_soa/metrics/confirmatory.py`, `src/iqa_soa/experiment/confirmatory_assignment.py` (MC provenance generation, both modes) | `randomization_mc_provenance.json` (both modes) | exact-equivalence test, exact-mode-no-seed-fields test, MC-mode-seed-fields-required test, MC-seed-not-conflated test, invalid/wrong-mode-provenance test | `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` |
| PR-10 | `RUNTIME_CONFIGURATION_FROZEN` + eligibility manifest frozen before final registration, no post-freeze promotion/reassessment; runtime identity/eligibility digest chain completely frozen | `eligibility_manifest.json` (§5.A Stage B), `RuntimeSnapshotV1` two-layer contract (§5.I) | `src/iqa_soa/experiment/confirmatory_eligibility.py` | per-stratum evidence refs, `assessed_at`, registration-expected `runtime_identity_digest` | eligibility-immutability test, no-reassessment test, runtime-identity-digest-chain test | `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN`, `DESCRIPTIVE_ONLY_UNASSESSED` |

No row above requires a future engineer to choose between architectures; every "implementation" column names one frozen mechanism. `ALL_PR1_TO_PR10_CLASS_A: YES` (§18).

---

## 8. Exact file-level change plan (future, not made now)

This section names concrete future edits consistent with the frozen module list of §11; where Revision 1 named a different module (`registration.py`, `assignment.py`, `isolation.py`, `eligibility.py`), that layout is superseded by §11 below and is not used.

1. **`src/iqa_soa/experiment/confirmatory_registration.py`** (new). Owns registration draft/final schemas, canonical JSON/digest helpers (§5.B.2), matrix freeze validation (§5.A Stages A and C). Tests: draft immutability, final-registration digest binding, no-freeze-before-eligibility, no-same-object-digest-alias-present test.
2. **`src/iqa_soa/experiment/confirmatory_eligibility.py`** (new). Owns the eligibility schema, four-predicate disposition, immutable eligibility validation (§5.A Stage B, §5.F, §5.I evidence embedding). Tests: total-disposition-over-four-predicates, default-`UNASSESSED`, immutability, no-reassessment.
3. **`src/iqa_soa/experiment/confirmatory_assignment.py`** (new). Owns `AssignmentRandomSource`, `SecretsAssignmentRandomSource`, assignment persistence/load/refusal, MC provenance generation/load in both tagged-union modes (§5.L, §5.M). Tests: one-bit-per-task, complement involution, balance preservation, duplicate refusal, MC-seed-timing, exact-mode-no-seed-fields, MC-mode-seed-fields-required, digest mismatch.
4. **`src/iqa_soa/experiment/confirmatory.py`** (new). Owns `run_confirmatory_experiment`, state-machine enforcement, position label application, fresh provider per position, pre-execution runtime-identity check, execution/resume gates (§5.J, §5.O). Tests: confirmatory-mode-off-byte-identical-to-today (via the untouched `ExperimentRunner`), task-bit-governs-all-nested-positions, resume-refusal-on-mismatch, runtime-identity-refusal-before-dispatch.
5. **`src/iqa_soa/metrics/confirmatory.py`** (new). Owns strict manifest/row reconciliation (fourteen-point checklist), observation/failure validation, runtime-identity validation, confirmatory randomization analysis (§5.G, §5.H, §5.I, §5.K, §5.L). Public entry point `analyze_confirmatory_randomization(...)`. Tests: see §10 — the largest test surface.
6. **`src/iqa_soa/experiment/runner.py`** (modified later, additive only). Only minimal reusable hooks / row provenance plumbing needed by `confirmatory.py` (item 4) — no confirmatory-specific logic lives here. `_ordered_treatments` is not modified. Existing constructor and existing tests unaffected.
7. **`src/iqa_soa/metrics/statistics.py`** (modified later, minimal). Only extract/reuse pure statistic primitives as required by `confirmatory.py` (item 5); legacy behavior of `_apply_task_cluster_inference`, `_task_sign_flip_p_value`, `pair_before_after`, `analyze_before_after` is preserved unchanged.
8. **`src/iqa_soa/metrics/collector.py`** (modified later, additive only). Emits explicit `observation_status`/`failure_class` (§5.H) and `runtime_identity_digest`/`runtime_snapshot_digest` (§5.I) for confirmatory rows, without changing historical interpretation of existing non-confirmatory rows.

Frozen future test modules (no alternative layout):

```
tests/unit/test_confirmatory_registration.py
tests/unit/test_confirmatory_eligibility.py
tests/unit/test_confirmatory_assignment.py
tests/integration/test_confirmatory_runner.py
tests/unit/test_confirmatory_statistics.py
```

No file above is created, and no test above is written or run, by this document.

---

## 9. Backward compatibility strategy

Confirmatory mode is explicit opt-in at every layer and lives entirely in new modules: `run_confirmatory_experiment` (§5.J) is the sole confirmatory entry point and is never reachable through `ExperimentRunner`'s existing constructor or existing call sites; `analyze_confirmatory_randomization` (§5.G) is a new function nobody calls implicitly; `resolve_label` (§5.D) is only invoked from the new confirmatory runner, never from the existing `_ordered_treatments` call site. A row without `confirmatory_profile == "post_phaseP_confirmatory_randomization_v1"` (or without one at all) never enters the fourteen-point checklist of §5.C and stays on the legacy analysis path. Historical Phase-P and ordinary analyses are byte-for-byte unaffected: `statistics.py`, `collector.py`'s existing fields, `definitions.py`, `pilot.py` retain their current behavior; the only new call sites are in wholly new modules (§8, §11) or minimal additive hooks. No retroactive migration of Phase-P evidence is designed, needed, or authorized — `results/phaseP-rc4-qualification/` has no relationship to any artifact designed above, and nothing here reads or writes it.

---

## 10. Test design (future files, not written here)

Proposed new test files, each with concrete assertions, aligned to the frozen module list of §8/§11:

- **`tests/unit/test_confirmatory_registration.py`**: `test_draft_immutable_after_write`; `test_no_final_registration_before_eligibility_frozen`; `test_final_registration_binds_draft_and_eligibility_digests`; `test_matrix_digest_stable_under_reserialization`; `test_only_confirmatory_eligible_strata_enter_matrix`; `test_no_artifact_stores_a_same_object_digest_alias_field`; `test_registration_manifest_freezes_randomization_mode_from_k`.
- **`tests/unit/test_confirmatory_eligibility.py`**: `test_total_disposition_over_four_predicates`; `test_first_failing_predicate_is_reported_reason`; `test_default_disposition_is_unassessed`; `test_confirmatory_eligible_requires_all_four_pass`; `test_eligibility_manifest_immutable_after_finalize`; `test_no_reassessment_after_final_freeze_raises`.
- **`tests/unit/test_confirmatory_assignment.py`**: `test_complement_is_involutive`; `test_balance_preserved_under_complement`; `test_one_task_bit_governs_all_nested_positions`; `test_bit_persisted_before_first_read_by_execution`; `test_duplicate_assignment_refused`; `test_assignment_digest_mismatch_detected`; `test_deterministic_source_rejected_for_confirmatory_profile`; `test_mc_seed_generated_secrets_token_bytes_32_when_k_gt_16`; `test_mc_seed_timing_precedes_assignment_and_execution`; `test_exact_mode_provenance_contains_no_seed_fields`; `test_exact_mode_provenance_contains_exact_support_size_and_k`; `test_mc_mode_provenance_missing_seed_hex_rejected`; `test_exact_mode_provenance_with_seed_hex_rejected`; `test_provenance_mode_mismatch_with_registration_rejected`.
- **`tests/unit/test_confirmatory_statistics.py`**: `test_missing_registered_position_yields_unavailable`; `test_missing_endpoint_on_one_position_yields_unavailable`; `test_non_observed_status_yields_unavailable_even_if_endpoint_nonnull` (directly targets Revision 2 closure blocker 4); `test_observed_zero_stays_observed`; `test_no_complete_case_deletion`; `test_zero_difference_task_retained_in_K`; `test_k_plus_used_only_for_reporting_not_membership`; `test_exact_k_leq_16_matches_statistics_module`; `test_monte_carlo_plus_one_formula`; `test_invalid_mc_provenance_yields_unavailable`; `test_mc_seed_field_never_conflated_with_bootstrap_seed`; `test_statistic_equivalence_with_apply_task_cluster_inference`; `test_position_id_excludes_treatment_label`; `test_row_identity_fields_reproduce_position_id`; `test_duplicate_confirmatory_row_detected`; `test_extra_unregistered_confirmatory_row_detected`; `test_row_wrong_confirmatory_profile_rejected`; `test_row_correct_profile_foreign_design_id_rejected`; `test_runtime_identity_digest_mismatch_yields_unavailable`; `test_runtime_identity_digest_match_with_different_captured_at_allowed`; `test_runtime_identity_digest_match_with_different_self_digest_allowed`; `test_self_digest_recomputation_fails_on_manual_edit`; `test_content_edit_without_self_digest_recomputation_detected`.
- **`tests/integration/test_confirmatory_runner.py`**: `test_no_execution_before_assignment_persistence`; `test_matrix_reconciliation`; `test_fresh_provider_instance_per_position`; `test_resume_refuses_on_any_digest_or_runtime_identity_mismatch`; `test_resume_allowed_under_same_runtime_identity_later_captured_at`; `test_resume_only_runs_missing_positions`; `test_historical_phaseP_analysis_unchanged` (presence of the new modules changes nothing about the legacy path); `test_pre_execution_runtime_identity_mismatch_refuses_before_dispatch`.

No test above is written or run by this document; this is the list of future test files and their assertions only.

---

## 11. Canonical failure-token table

| Token | Scope | Trigger condition |
|---|---|---|
| `DESCRIPTIVE_ONLY_NO_CONFIRMATORY_RANDOMIZATION` | provider-stratum | No assignment mechanism exists/was invoked for this stratum at all — the pre-implementation default for every provider today |
| `DESCRIPTIVE_ONLY_STATE_NOT_ISOLATED` | provider-stratum | `POSITION_STATE_ISOLATION` predicate `FAIL` (§5.E, §5.A Stage B) |
| `DESCRIPTIVE_ONLY_ROUTING_ASYMMETRY` | provider-stratum | `INFRASTRUCTURE_SYMMETRY` predicate `FAIL` (§5.F, §5.A Stage B) |
| `DESCRIPTIVE_ONLY_OBSERVABILITY_NOT_TOTAL` | provider-stratum | `TOTAL_OBSERVATION` (prospective) predicate `FAIL` (§5.G, §5.A Stage B) |
| `DESCRIPTIVE_ONLY_RUNTIME_NOT_FROZEN` | provider-stratum | `RUNTIME_CONFIGURATION_FROZEN` predicate `FAIL`, pre-freeze — including a `runtime_identity_digest` mismatch discovered during eligibility assessment (§5.I.6, §5.A Stage B) |
| `DESCRIPTIVE_ONLY_UNASSESSED` | provider-stratum | No predicate has yet been evaluated; the default for every currently configured provider |
| `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` | analysis (whole confirmatory experiment) | Any registered confirmatory position's primary endpoint has `observation_status != OBSERVED` (§5.H); or any §5.C fourteen-point row-binding check fails (including wrong `confirmatory_profile`, foreign `design_id`, or duplicate/extra row); or absent, wrong-mode, or malformed Monte Carlo provenance in either randomization mode (§5.L); or any digest mismatch anywhere in the §5.B chain at analysis time; or a `runtime_identity_digest` mismatch discovered during analysis on an already-registered confirmatory execution (§5.I.6); or a resume mismatch (§5.O) |
| `AssignmentIntegrityError` (`ASSIGNMENT_DIGEST_MISMATCH`) | experiment (assignment layer) | Persisted assignment file's `self_digest` does not verify per §5.B.2, or its `final_registration_digest` reference does not match the live final registration's `self_digest` (§5.M, §6) |
| `DuplicateAssignmentError` (`DUPLICATE_ASSIGNMENT_REFUSED`) | experiment (assignment layer) | `persist_assignment` called against a `design_id` that already has a persisted assignment manifest (§5.M) |
| `AssignmentNotPersistedError` (`NO_ASSIGNMENT_BEFORE_EXECUTION`) | experiment (runner) | Confirmatory execution requested before `assignment_manifest.json` exists for the active `design_id` (§6, §7 PR-3) |
| `STATISTIC_VERSION_MISMATCH` | analysis | The `statistic_spec_id` recorded at registration does not match `"confirmatory_task_sign_flip_v1"` as implemented at analysis time (§5.K, §7 PR-8) |
| `RuntimeIdentityRefused` (pre-execution/resume refusal) | experiment (runner) | A `pre_execution_runtime_snapshot`'s `runtime_identity_digest` does not equal the registration-expected `runtime_identity_digest`, detected before execution is dispatched (§5.I.6, §5.O) |

No statistical fallback is permitted when any of the above fires: every trigger above produces exactly the named token and no computed p-value, no partial statistic, and no silent subset analysis.

---

## 12. Audit/proof artifact catalog

| Artifact | Producer | Consumer | Generation point | Required fields | Digest/binding | Retention |
|---|---|---|---|---|---|---|
| `registration_draft.json` | `confirmatory_registration.py: draft_registration` | eligibility layer, final registration | Stage A, before any eligibility assessment | proposed matrix, `self_digest` | self-contained (no upstream reference) | Permanent; superseded only by a new `design_id`'s draft |
| `eligibility_manifest.json` | `confirmatory_eligibility.py` | final registration (Stage C gate) | Stage B, after draft, before final registration | §5.A Stage B fields, four predicates per stratum, `created_at`, `schema_version`, `self_digest` | `registration_draft_digest` reference to `registration_draft.json.self_digest` | Permanent, immutable, never versioned in place |
| `registration_manifest.json` | `confirmatory_registration.py: freeze_final_registration` | assignment layer, confirmatory analyzer | Stage C, after `ELIGIBILITY_FROZEN` | §5.A Stage C fields, `randomization_mode` | `registration_draft_digest`, `eligibility_manifest_digest`, `matrix_digest`, `self_digest` (referenced downstream as `final_registration_digest`) | Permanent; new `design_id` on any correction, never overwritten |
| `randomization_mc_provenance.json` | `confirmatory_assignment.py` (MC provenance generator) | confirmatory analyzer (metrics) | After `FINAL_REGISTRATION_FROZEN`, before assignment, before execution — always generated, in either tagged-union mode (§5.L) | §5.L.1 common fields + mode-specific §5.L.2/§5.L.3 fields | `final_registration_digest` reference, `self_digest` (referenced downstream as `randomization_mc_provenance_digest`) | Permanent, one per `design_id`, in exactly one of the two tagged shapes |
| `assignment_manifest.json` | `confirmatory_assignment.py: persist_assignment` | confirmatory runner (label resolution), confirmatory analyzer | After MC provenance, before first confirmatory execution | §5.M fields, `bits`, `task_order` | `final_registration_digest`, `randomization_mc_provenance_digest`, `self_digest` (referenced downstream as `assignment_digest`) | Permanent, one per `design_id` |
| Confirmatory execution rows | `confirmatory.py` (experiment runner) via `collector.py` extension | confirmatory analyzer | Per position, during `EXECUTION_IN_PROGRESS` | §5.C row-contract fields, including `runtime_identity_digest` | `position_id`, all bound digest references | Permanent, one row per registered position |
| `final_analysis_manifest.json` | `metrics/confirmatory.py: analyze_confirmatory_randomization` (output) | end reader / report | After analysis completes (or fails closed) | §5.B.3 `final_analysis_manifest.json` field block | binds registration + eligibility + MC provenance + assignment digest references, plus `runtime_snapshot_digests`, `statistic_spec_id`, `self_digest` | Permanent, immutable once produced |

---

## 13. Security/integrity threat model

| Threat | Preventive / fail-closed mechanism |
|---|---|
| Eligibility re-assessed or promoted after final freeze | `ELIGIBILITY_FROZEN` is immutable (§5.A Stage B); `FINAL_REGISTRATION_FROZEN` reads its digest once and never re-reads a mutated eligibility manifest; any attempted post-freeze re-assessment requires a brand-new `design_id` and is otherwise structurally impossible |
| Assignment regenerated after seeing outcomes | `DuplicateAssignmentError` refuses any second `persist_assignment` call for a given `design_id` (§5.M); state machine (§6) forbids re-entering `ASSIGNMENT_PERSISTED` |
| Assignment manifest edited | `self_digest` verification on every read (§5.B.2, §5.M); any content edit without recomputing `self_digest` fails verification; any edit including a recomputed `self_digest` still changes every downstream reference and is caught at the referencing artifact |
| Matrix changed post-assignment | Membership-immutability rule (§6): once `FINAL_REGISTRATION_FROZEN`, `registration_manifest.json` is never re-written; any attempted edit is caught by digest recomputation mismatching every downstream reference |
| MC seed chosen after seeing outcomes | `randomization_mc_provenance.json` must exist (in MC mode, with seed material) and be timestamped before assignment and execution (§5.L.3, §6); analyzer refuses (`CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`) if generation time postdates outcome availability |
| Seed fabricated for exact-mode design | Exact mode (§5.L.2) forbids all seed-material fields; their presence is a hard rejection, not a warning |
| MC-mode provenance missing seed material | MC mode (§5.L.3) requires `seed_hex` and every companion field; absence is a hard rejection |
| Descriptive provider promoted to confirmatory after outcomes | Eligibility disposition (§5.A Stage B) is fixed before `FINAL_REGISTRATION_FROZEN`; a stratum's confirmatory-matrix membership is fixed at Stage C and never revisited (§5.A post-freeze invariant) |
| Runtime changes mid-run | `runtime_identity_digest` field-exact match check (§5.I) run at every comparison point; any mismatch fails the predicate pre-freeze or refuses execution/resume post-freeze, or fails analysis if only discovered then; `captured_at`/`self_digest` differences alone never trigger a failure |
| Labels influencing routing outside treatment channel | `INFRASTRUCTURE_SYMMETRY` audit (§5.F) enumerates candidate leak channels; any unaudited or asymmetric channel blocks `CONFIRMATORY_ELIGIBLE` |
| Task bit accidentally drawn per-model instead of per-task | `draw_bit()` is called exactly once per task, in sorted `task_id` order, never per model/provider/repetition (§5.M); `resolve_label` caches `b_k` per task |
| Missing or falsely-observed outcome silently accepted | `analyze_confirmatory_randomization` iterates the registered position list and checks `observation_status`, never `endpoint is not None` alone (§5.G, §5.H) |
| Row claims a position it does not match | Fourteen-point row-binding checklist (§5.C) recomputes `position_id` from a row's own identity fields and rejects any row that does not reproduce it |
| Row claims the wrong confirmatory design | `confirmatory_profile`/`design_id` checks (§5.C, checks 1-2) run first, before any digest check; a foreign-`design_id` row is rejected even if `confirmatory_profile` is correct |
| Registration/eligibility/assignment/MC manifest mismatch | Every digest reference in §5.B.3 checked on every read; mismatch raises and blocks the entire chain |
| Stale/mismatched statistic version | `statistic_spec_id` recorded at registration and checked against the implemented `"confirmatory_task_sign_flip_v1"` at analysis time; mismatch raises `STATISTIC_VERSION_MISMATCH` |
| Interrupted run resumed under changed config/digests | Resume contract (§5.O) requires every digest reference and the `runtime_identity_digest` to match; any mismatch is `REFUSE RESUME`, no confirmatory p-value |

---

## 14. Adversarial self-check

Each case below has exactly one deterministic result under the frozen architecture of §5-§13.

1. **Provider fails eligibility during pre-registration assessment.** Placed into the descriptive-only set before `FINAL_REGISTRATION_FROZEN` (§5.A Stage B/C); it can never later enter the confirmatory matrix for this `design_id`.
2. **Someone tries eligibility re-assessment after final freeze.** Refused; a new `design_id`/new registration triple is required (§5.A post-freeze invariant, §13).
3. **Assignment belongs to another registration digest.** `final_registration_digest` reference mismatch (§5.B.3, §5.M); refuse execution/analysis.
4. **No persisted assignment.** `AssignmentNotPersistedError`; execution refused (§6, §7 PR-3).
5. **Manually edit `assignment_manifest.json`'s `self_digest`.** Deterministic recomputation (§5.B.2 verification) fails; every reader that verifies `self_digest` refuses.
6. **Manually edit assignment content but do not recompute any digest.** `self_digest` mismatch on read (§5.B.2 step 7); refuse.
7. **Different bits attempted across models under same task.** Impossible by construction — `draw_bit()` yields one bit per task, cached and shared, with no per-model/per-position lookup path (§5.D, §5.M); any attempt is a programming error caught by the shared-bit test, not a runtime state.
8. **Entire registered position missing.** `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (§5.G, §5.C check 6).
9. **Row exists, endpoint `False`, but provider failed before observation boundary.** `observation_status != OBSERVED`; `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (§5.H) — the endpoint's non-null value is not sufficient evidence of observation.
10. **Row exists, endpoint `False` and `observation_status = OBSERVED`.** Observed zero retained in analysis unchanged (§5.H).
11. **`K = 10`.** Exact-mode `randomization_mc_provenance.json` exists (§5.L.2), contains no entropy/seed fields, contains `exact_support_size = 2^10` and `K = 10`; `assignment_manifest.json` still binds `randomization_mc_provenance_digest` to it.
12. **`K = 20`.** MC-mode provenance (§5.L.3) requires a `secrets.token_bytes`-derived `seed_hex`, `rng_bit_generator = "PCG64"`, and registered `randomization_mc_samples` (`M`); absence of any required field is rejected.
13. **Exact-mode provenance unexpectedly contains `seed_hex`.** Rejected — forbidden field present for `EXACT_ENUMERATION` mode (§5.L.2).
14. **MC-mode provenance missing `seed_hex`.** Rejected — required field absent for `MONTE_CARLO` mode (§5.L.3).
15. **MC seed generated after assignment or execution begins.** Provenance invalid (generation timestamp check, §5.L.3); `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`.
16. **`bootstrap_seed` passed to confirmatory MC.** Architecture/API does not accept it — `confirmatory.py` (metrics) has no parameter through which `bootstrap_seed` could reach the MC draw (§5.L.3).
17. **Row `confirmatory_profile` is wrong.** Row never enters the confirmatory reconciliation path for this design; `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` / not accepted as belonging to this confirmatory design (§5.C check 1).
18. **Row `confirmatory_profile` correct but `design_id` foreign.** Rejected at check 2, before any digest is even compared; `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` (§5.C).
19. **Pre-execution `RuntimeSnapshotV1.captured_at` differs from the registration-expected snapshot's `captured_at`.** Allowed, unconditionally, provided `runtime_identity_digest` matches (§5.I.2, §5.I.5).
20. **Runtime snapshot `self_digest` differs solely because `captured_at` differs.** Allowed, provided each snapshot's own `self_digest` individually verifies (§5.B.2) and `runtime_identity_digest` matches across snapshots (§5.I.2).
21. **Endpoint/runtime config actually changed (e.g. a different provider endpoint).** `runtime_identity_digest` mismatch; refuse execution/resume if detected before dispatch, else `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE` at analysis (§5.I.6).
22. **Resume under the same `runtime_identity_digest` but a later `captured_at`.** Allowed (§5.I.5, §5.O).
23. **Resume under a different `runtime_identity_digest`.** Refused — `REFUSE RESUME` (§5.O, §5.I.6).
24. **Descriptive-only provider promoted after outcomes.** Impossible without a new registration/`design_id` (§5.A post-freeze invariant).
25. **Statistic version differs.** `STATISTIC_VERSION_MISMATCH`; `CONFIRMATORY_RANDOMIZATION_TEST_UNAVAILABLE`-family refusal (§5.K, §11).
26. **Legacy analysis without confirmatory profile.** Unchanged legacy behavior — `analyze_before_after`/`_apply_task_cluster_inference` are untouched and are the only path reached when no `confirmatory_profile` and no confirmatory manifests are supplied (§5.G, §9).

Every case above resolves to exactly one deterministic outcome; none has a residual "depends on implementation choice" branch.

---

## 15. Consistency sweep

A full-document sweep was performed for every term the Revision 3 closure spec named for review: `assignment_digest`, `final_registration_digest`, `registration_draft_digest`, `eligibility_manifest_digest`, `self_digest`, `randomization_mc_provenance`, `K <= 16`, `EXACT_ENUMERATION`, `MONTE_CARLO`, `confirmatory_profile`, `design_id`, `RuntimeSnapshotV1`, `captured_at`, `runtime_identity_digest`, `environment_fingerprint`, "snapshot matches", "versionable", "absent", "optional".

Findings and disposition:

- Every prior occurrence of a same-object digest alias field (`registration_manifest.self_digest == registration_manifest.final_registration_digest`, `assignment_manifest.self_digest == assignment_digest`, and the analogous phrasing in §5.B, §6, §11, §12, §13) has been rewritten so the artifact stores only `self_digest`, and downstream references use the semantic name only when pointing at an upstream artifact's `self_digest` (§5.B.1, §5.B.3).
- Every prior occurrence of `randomization_mc_provenance.json` scoped as "K>16 only" (§5.B's old artifact-relationship block, §5.L's old heading, §6's old MC-provenance transition row, §7 PR-9's old requirement text, §12's old generation-point cell) has been rewritten to state the artifact is mandatory in both modes (§5.L.1), tagged by `randomization_mode`.
- Every prior occurrence of the twelve-point row checklist (§5.C, §5.G step 2, §7 PR-7, §9) has been rewritten to the fourteen-point checklist that validates `confirmatory_profile` and `design_id` first (§5.C).
- Every prior occurrence of "runtime snapshot(s) match" without qualification (old §5.I's "Frozen comparison points" paragraph, old §5.J, old §6's `EXECUTION_IN_PROGRESS → EXECUTION_COMPLETE` row, old §13, old §14 case 5) has been rewritten to compare `runtime_identity_digest` only, with `captured_at`/`self_digest` explicitly excluded from comparison (§5.I.2, §5.I.5-5.I.6).
- `environment_fingerprint`'s field list is restated once, completely, in §5.I.3, with `platform_machine` added to close the "for example"/incompleteness gap the closure spec flagged; no other section restates a competing field list.
- No remaining sentence anywhere in §5-§14 uses "absent" or "optional" to describe `randomization_mc_provenance.json`'s existence — its existence is now mandatory in both modes; "absent" is used only, precisely, to describe which *fields* must be absent within the exact-mode tagged shape (§5.L.2), which is a schema rule, not an existence choice.
- Historical observations in §2 (Facts 1-5) retain ordinary descriptive "or" where they describe what the *current, unmodified* code already does; nothing in §2 was touched by any of the four Revision 3 defects, and no rewording was needed there.
- Revision 2's own consistency-sweep language (previously §15, now superseded by this section) is not reproduced verbatim below it; this section replaces it in full, since re-asserting stale claims about "twelve-point checklist" or "K>16-only provenance" would itself reintroduce the defects just closed.

No remaining sentence in §5-§14 offers a future implementer more than one way to realize a frozen mechanism, and no remaining sentence asserts an equality rule (digest or runtime) that is self-contradictory against the schema it references.

---

## 16. Dependency-ordered implementation sequence (not implemented here)

1. **Registration draft schema.** `confirmatory_registration.py` draft path (§8 item 1). Exit criterion: `RegistrationDraft` round-trips through canonical serialization with a stable `self_digest`, with no same-object alias field present.
2. **Eligibility schema and immutability.** `confirmatory_eligibility.py` (§8 item 2), depends on step 1. Exit criterion: four-predicate disposition computed exhaustively; immutability and no-reassessment enforced; unit tests pass.
3. **Final registration freeze.** `confirmatory_registration.py` final path (§8 item 1), depends on steps 1-2. Exit criterion: `registration_manifest.json` references both upstream `self_digest` values under `registration_draft_digest`/`eligibility_manifest_digest`; freezes `randomization_mode` from `K`; only `CONFIRMATORY_ELIGIBLE` strata admitted to the confirmatory matrix.
4. **MC provenance and assignment.** `confirmatory_assignment.py` (§8 item 3), depends on step 3. Exit criterion: tagged-union provenance generated in both modes before assignment; exact mode contains no seed fields, MC mode contains all required seed fields; `secrets.randbits`/`secrets.token_bytes` paths tested, duplicate/digest-mismatch refusals pass.
5. **Confirmatory runner.** `confirmatory.py` (experiment) (§8 item 4), depends on steps 1-4. Exit criterion: state machine (§6) enforced end to end against synthetic fixtures, including mandatory `MC_PROVENANCE_PERSISTED` in both modes and pre-execution runtime-identity refusal; legacy `ExperimentRunner` regression suite unchanged.
6. **Fail-closed confirmatory analyzer.** `confirmatory.py` (metrics) (§8 item 5), depends on steps 1-4 (readable manifests) but can be developed and tested against synthetic fixtures independent of step 5. Exit criterion: §5.C (fourteen-point), §5.H, §5.I, §5.K, §5.L checks all pass on synthetic fixtures; statistic-equivalence test against `_apply_task_cluster_inference` passes.
7. **Minimal runner/collector hooks.** `runner.py`, `collector.py` additive changes (§8 items 6, 8), depends on steps 5-6. Exit criterion: existing non-confirmatory test suites unchanged; new `observation_status`/`failure_class`/`runtime_identity_digest` fields populated only for confirmatory rows.
8. **Focused tests, full suite.** All files in §10, depends on the corresponding implementation step having landed.
9. **Final verification.** Historical-behavior-unchanged regression pass (§9); no candidate/version/RC created at any point in this sequence.

No step in this sequence is executed by this document.

---

## 17. Values intentionally left unselected

**DEFERRED VALUE SELECTION** (values, not architecture — will be chosen later, by a separately authorized act, never by this document):

- The actual confirmatory task matrix (which task clusters are registered).
- Provider/model stratum membership for the confirmatory experiment, and the real eligibility disposition of any real provider/model.
- Repetition counts per task/stratum.
- Ordinary provider seeds (the pre-existing per-repetition seed values, distinct from any randomization bit).
- `M` (Monte Carlo sample count) if the registered `K > 16` and `M` is not yet chosen.
- The actual `b_1, ..., b_K` assignment bits.
- The actual `randomization_mc_seed` value / `seed_hex` (Monte Carlo mode only; exact mode has no such value).
- The actual `timeout_seconds` and `retry_policy` values (their schema shapes are frozen in §5.I.4; their values are not).
- Execution time/window for the confirmatory run.
- The `design_id` value for any future actual registration.

**REMAINING_IMPLEMENTATION_ARCHITECTURE_CHOICES: NONE.** Every architectural choice this document is responsible for (§5.A-§5.O, §6, §7, §8, §11) is fully specified: schema field names and types are concrete and exhaustive, the canonical JSON profile is fully frozen (serializer, options, decimal-string rule, key ordering, hash algorithm, digest encoding), module boundaries and function signatures are named exactly once each, the state machine's transitions and refusal conditions are enumerated, the PR-1..PR-10 mapping has exactly one concrete target per row, and the file-level change plan names exact new files and their contents with no alternative layout. The two items still marked **[DEFERRED VERIFICATION]** (§5.E's real-provider PR-4 evidence, §5.A Stage B's `CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED`) are future *evidence-gathering* procedures against an already-frozen schema and evaluation rule, not open design questions about how the code should be shaped.

---

## 18. DECISION

## **CONFIRMATORY_RANDOMIZATION_IMPLEMENTATION_DESIGN_DECISION: IMPLEMENTATION_ARCHITECTURE_FROZEN**

Justification: all four residual interface/schema defects identified by the independent re-review are closed in this revision, without reopening any Revision 2 architecture. (1) Self-digest alias recursion is removed: every artifact stores exactly one `self_digest` of itself; semantic names like `final_registration_digest` and `assignment_digest` are downstream-only reference names, never a same-object second field; the canonical JSON profile (Python `json.dumps` with `sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False`, decimal-string numeric fields, SHA-256, lowercase hex) is now completely frozen with no remaining ambiguity (§5.B). (2) `randomization_mc_provenance.json` is now a mandatory tagged-union artifact in both `EXACT_ENUMERATION` (K≤16, no seed fields) and `MONTE_CARLO` (K>16, full seed provenance) modes, with `registration_manifest.json` freezing `randomization_mode` deterministically from registered `K` and the provenance artifact's mode required to match — closing the absent-vs-sentinel gap (§5.L). (3) The row-binding checklist is extended from twelve to fourteen points, validating `confirmatory_profile` and `design_id` first, before any digest check, and explicitly rejecting a row with the correct profile but a foreign `design_id` (§5.C). (4) `RuntimeSnapshotV1` is now a two-layer contract: a `runtime_identity_digest` computed over exactly the invariant fields, compared exactly across all three capture points, versus `captured_at`/`self_digest` capture metadata that is never compared for equality — removing the prior self-contradiction between "snapshots must match" and a schema that necessarily varies by capture time (§5.I). Every Revision 2 architectural decision this task was instructed not to reopen (`ELIGIBILITY_FREEZE_ORDER`, `OBSERVATION_FAILURE_GATE`, `ASSIGNMENT_RANDOMNESS_ARCHITECTURE`, `MONTE_CARLO_ARCHITECTURE` independence/timing, `STATE_ISOLATION_STRATEGY`, `STATISTIC_SPEC_ID`, `MODULE_OWNERSHIP`) is restated unchanged (§5.A, §5.D, §5.E, §5.G, §5.H, §5.J, §5.K, §5.M). No point in this revision leaves a future implementer a choice among architectures.

---

## 19. Authorization boundary

**IMPLEMENTATION_DESIGN_READY_FOR_CODE_IMPLEMENTATION: YES**
**CODE_IMPLEMENTATION_AUTHORIZED: NO**
**NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO**

This document authorizes nothing beyond itself. No file other than this one was created or modified in producing it. No code was written, edited, or executed. No test was run. No seed, bit, task, provider, or model was selected or generated.

---

## Final report block

```
REVISION: 3

SELF_DIGEST_ALIAS_RECURSION_REMOVED: YES
CANONICAL_JSON_PROFILE_FULLY_FROZEN: YES
EXACT_MODE_MC_PROVENANCE_SENTINEL_FROZEN: YES
ROW_PROFILE_AND_DESIGN_ID_VALIDATION_FROZEN: YES
RUNTIME_IDENTITY_VS_CAPTURE_METADATA_FROZEN: YES
ENVIRONMENT_FINGERPRINT_FIELD_SET_FROZEN: YES
TIMEOUT_RETRY_SCHEMA_FROZEN: YES
ALL_PR1_TO_PR10_CLASS_A: YES

REMAINING_IMPLEMENTATION_ARCHITECTURE_CHOICES:
NONE

CONFIRMATORY_RANDOMIZATION_IMPLEMENTATION_DESIGN_DECISION:
IMPLEMENTATION_ARCHITECTURE_FROZEN

IMPLEMENTATION_DESIGN_READY_FOR_CODE_IMPLEMENTATION: YES

CODE_IMPLEMENTATION_AUTHORIZED: NO
NEW_CANDIDATE_IMPLEMENTATION_AUTHORIZED: NO

ZERO MODEL INFERENCE
NO PHASE-P EVIDENCE MODIFIED
NO RC4 MODIFICATION
NO HISTORICAL PHASE-P REINTERPRETATION
NO RANDOMIZATION BIT GENERATED
NO SEED GENERATED
NO PROVIDER ELIGIBILITY ASSIGNED
NO CANDIDATE CREATED
NO FILES OTHER THAN THE IMPLEMENTATION-DESIGN DOCUMENT MODIFIED
```
