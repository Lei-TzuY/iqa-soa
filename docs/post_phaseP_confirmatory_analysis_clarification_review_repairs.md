# Post-Phase-P confirmatory analysis clarification — independent-review repairs

**Record kind:** binding narrow repair addendum to `docs/post_phaseP_confirmatory_analysis_clarification.md`.
**Status:** REVIEW-BLOCKER REPAIR. This document supersedes only the clauses explicitly named below. Every other clause of the WU6 clarification remains unchanged.
**Date:** 2026-08-28
**Base clarification head reviewed:** `a5b054f841181737bd68eb1aa8e9c54920940e91`.
**Independent review verdict:** `BLOCK_WU6_ANALYSIS_CLARIFICATION` with exactly two blockers.

---

## 0. Boundary and precedence

This addendum closes **only**:

1. the task-level nesting error in WU6 clarification §§9.1–9.3 and its consequential restatements; and
2. the analysis-time provider reconstruction defect in WU6 clarification §§8.2/8.4 and its consequential failure mapping.

It does **not** reopen or modify:

- the task-level complement randomization design;
- `FULL_MINUS_OFF` orientation;
- registered global `K`, `K_plus`, exact/MC threshold, PCG64 provenance, or plus-one MC formula;
- endpoint applicability or fixed-sequence order;
- the 27-key WU5 row, 20-key `RuntimeSnapshotV1`, or any WU1–WU5 scientific artifact schema;
- the 19-key `FinalAnalysisManifestV1`, 13-key endpoint-result shape, `execution_rows_digest`, runtime-snapshot digest binding, failure precedence except where explicitly restated below, or crash-safe final publication.

**Precedence rule:** where the base WU6 clarification conflicts with this repair addendum, this addendum controls. All unmentioned text in the base WU6 clarification remains binding.

---

# REPAIR 1 — frozen two-level estimator nesting

## 1.1 Defect closed

The base WU6 clarification incorrectly split provider and model into separate averaging levels. The already-frozen analysis contract does not do that.

For the prospective confirmatory estimator, one **model stratum** is exactly one registered `(provider, model)` configuration. The frozen target then has two levels inside task `k`:

1. equal weight across registered `(provider, model)` strata;
2. within each stratum, equal weight across that stratum's registered repetitions / scheduled matched contrasts.

This is the structure frozen by analysis-contract §5.3:

```text
w_stratum = 1 / |S_k|
w_repetition_within_stratum = 1 / |R(k,s)|
```

No separate provider-average level exists.

## 1.2 Exact WU6 formula — supersedes base clarification §9.1

For endpoint `e`, task `k`, registered stratum `s = (provider, model)`, repetition `r`, and treatment `t`:

```text
S_e(k)    = the endpoint-applicable registered (provider, model) strata for task k
R(k,s)    = the registered repetitions / matched contrasts for cell (k,s)
Y(k,s,r,t,e) = validated binary endpoint value at treatment t

mu(k,s,t,e)
    = (1 / |R(k,s)|) * Σ_{r in R(k,s)} Y(k,s,r,t,e)

D_k(e)
    = (1 / |S_e(k)|) * Σ_{s in S_e(k)} [ mu(k,s,FULL,e) - mu(k,s,OFF,e) ]
```

For the primary endpoint and S-1/S-2/S-3, `S_e(k)` is the full registered confirmatory stratum set for task `k` after the already-frozen task applicability gate. For S-4/S-5, task membership remains endpoint-specific exactly as frozen by the base clarification; within an applicable task, the registered `(provider, model)` stratum set is still weighted equally.

Every membership set and denominator above is fixed from registration before endpoint values are read. No realized child count may change a weight.

## 1.3 Provider/model are one stratum key

The production grouping key for the inner stratum level is exactly:

```text
(provider, model)
```

not `provider` followed by `model`, not model alone, and not provider alone.

A provider hosting two registered models therefore contributes **two equally weighted model strata**, not one provider block whose two models first average to one provider contribution.

## 1.4 Unbalanced example — supersedes base clarification §9.2

Suppose one task has exactly these registered strata and repetitions:

```text
s1 = (A, m1): r0, r1
s2 = (A, m2): r0, r1
s3 = (B, m3): r0
```

Let `d(s,r)` denote the matched `FULL - OFF` endpoint difference.

The frozen task difference is:

```text
D_k = (
    mean(d(s1,r0), d(s1,r1))
  + mean(d(s2,r0), d(s2,r1))
  + d(s3,r0)
) / 3
```

Thus each registered `(provider, model)` stratum has weight `1/3`. Within `s1` and `s2`, each repetition has weight `1/2` of that stratum's `1/3` contribution. `s3` keeps weight `1/3` despite having only one repetition.

The following are forbidden:

```text
flat mean of all five repetition-level differences
mean(models within provider) -> mean(providers)
any weighting proportional to realized or registered repetition count across strata
```

The distinction is material whenever registered repetition counts differ across strata or one provider hosts multiple models.

## 1.5 Legacy helper relationship — supersedes base clarification §9.3 and consequential references

Current legacy `_apply_task_cluster_inference` flat-averages surviving pairs within a task. It is **not** the WU6 production aggregation primitive on an unbalanced confirmatory matrix.

It may be used only as a regression/equivalence oracle on a synthetic design where every registered `(task, provider, model)` stratum has the same repetition count, because only then does the flat arithmetic coincide with the frozen two-level formula.

Consequential references in base clarification §§10.2, 11.2 step 4, 12.4 `task_differences`, and §17 Aggregation tests are read under this repaired definition of `D_k`.

Required focused tests include:

1. one provider, two models, repetition counts `2` and `1`: both model strata have weight `1/2`;
2. two providers with strata `(A,m1)`, `(A,m2)`, `(B,m3)`: all three strata have weight `1/3`, not providers `1/2` each;
3. balanced matrix: repaired nested formula equals the legacy flat mean;
4. zero `D_k` remains in registered `K`; no nesting repair changes `K_plus` semantics.

`NESTED_EQUAL_WEIGHT_FIXED_PRE_RUN` therefore means exactly the two-level structure above.

---

# REPAIR 2 — analysis-time provider reconstruction by registered runtime identity

## 2.1 Defect closed

The base WU6 clarification required visiting every models-config alias and instantiating it through `load_provider`, but did not define behavior when an unrelated alias is disabled/uninstantiable. It also treated `(candidate.name, candidate.model)` as sufficient identity even though `candidate.name` is provider **type**, not alias identity.

That rule is replaced below.

## 2.2 Repository-owned candidate enumeration — supersedes base clarification §8.2 steps 3–6

The analyzer still accepts no provider/factory/capturer from the caller. It still uses only the digest-pinned `ExperimentConfig.models_path` and repository-owned `load_provider` / `capture_runtime_snapshot_v1`.

For each registered confirmatory stratum `(registered_provider, registered_model)`:

1. parse the provider aliases from the already-authenticated `config.models_path` in lexicographic alias order;
2. for each alias, call:

```python
load_provider(config.models_path, provider_name=alias)
```

3. if that alias cannot be instantiated under the frozen configuration — including an explicitly disabled alias, missing environment material, or another `ExperimentConfigError` / provider-construction failure — **skip that alias as a candidate**; the failure of an unrelated alias is not itself an analysis failure;
4. for each successfully instantiated candidate, first retain only candidates satisfying:

```text
candidate.name  == registered_provider
candidate.model == registered_model
```

This pair is a coarse pre-filter only, not final identity;
5. for every pre-filter survivor, immediately call the repository-owned pure/offline capture:

```python
capture_runtime_snapshot_v1(config=config, provider=candidate)
```

without calling `generate_action` and without contacting a provider;
6. validate each captured snapshot's own 20-key schema/self-digest;
7. select by the actual frozen runtime identity:

```text
captured.runtime_identity_digest
    == registration_expected_runtime_identity_digest(registered_provider, registered_model)
```

8. require **exactly one** matching candidate.

Disposition:

```text
zero successfully instantiated coarse (name,model) candidates
    -> ANALYSIS_CONFIGURATION_MISMATCH

one or more coarse candidates exist, but zero reproduce registered runtime_identity_digest
    -> ANALYSIS_RUNTIME_MISMATCH

more than one candidate reproduces the same registered runtime_identity_digest
    -> ANALYSIS_CONFIGURATION_MISMATCH

exactly one digest-matching candidate
    -> use that candidate's captured RuntimeSnapshotV1 as the Stage-A in-memory analysis snapshot
```

A disabled/unusable unrelated alias cannot abort discovery of another valid candidate.

## 2.3 Runtime identity, not alias, is authoritative

No provider alias string becomes a new scientific identity field. Alias is configuration navigation only.

The final cross-capture invariant remains exactly the already-frozen:

```text
runtime_identity_digest
```

The analyzer does not compare aliases, `captured_at`, or snapshot `self_digest` values across capture points.

If two aliases construct byte/semantically identical runtime identities, alias naming alone does not distinguish them; because they are indistinguishable under the frozen scientific identity, the repository must avoid ambiguous multiple reconstructors for one registered stratum. WU6 fails closed with `ANALYSIS_CONFIGURATION_MISMATCH` rather than choosing one by alias order.

## 2.4 Stage-A / Stage-B analysis capture ordering — repairs base clarification §8.4 only as necessary

Stage-A in-memory capture is now the candidate-enumeration procedure of §2.2 above.

Only after **every** registered stratum has exactly one candidate whose captured `runtime_identity_digest` matches registration may WU6:

- trust case/config declarations for endpoint applicability;
- continue whole-analysis gates;
- create/persist Stage-B `analysis_runtime_snapshots/<stratum_id>.json` files under the already-frozen write-once procedure.

The selected Stage-A snapshot object is the object later persisted at Stage B; WU6 does not recapture the same stratum between candidate selection and persistence.

Therefore there is no second opportunity for environment/config drift to be hidden between validation and persistence.

## 2.5 Prospective analyzability obligation — closes the upstream gap without changing scientific schemas

Before any **actual future confirmatory registration** is authorized, every `registration_expected_runtime_snapshot` admitted to Stage A must have been captured from a provider instance reconstructible by the same repository-owned route:

```python
load_provider(config.models_path, provider_name=<one configured alias>)
```

followed by:

```python
capture_runtime_snapshot_v1(config=config, provider=provider)
```

and its persisted `runtime_identity_digest` must equal that capture.

This is an **analyzability precondition**, not a new `RegistrationDraftV1` field and not a new eligibility predicate. It changes no 20-key snapshot, Stage-A/B/C manifest schema, provider eligibility disposition, or WU5 `ProviderFactory` interface.

A `ProviderFactory` used at execution may construct a fresh provider object however its implementation chooses, but each produced provider must already satisfy WU5's frozen `(provider, model)` and `runtime_identity_digest` checks. The analyzability obligation above ensures the same frozen runtime identity has one repository-owned offline reconstruction path at analysis time.

Synthetic unit tests may use private seams/mocks; production callers receive no provider injection surface.

## 2.6 Failure mapping — supersedes only the affected readings of base clarification §13

The failure tokens and their precedence numbers remain unchanged. Their exact meaning for this repair is:

```text
ANALYSIS_CONFIGURATION_MISMATCH
    = no reconstructible coarse (provider.name, model) candidate exists,
      or multiple candidates reproduce the same registered runtime identity,
      or models-config candidate discovery is otherwise structurally ambiguous.

ANALYSIS_RUNTIME_MISMATCH
    = at least one reconstructible coarse (provider.name, model) candidate exists,
      but none reproduces the registration-expected runtime_identity_digest.
```

An unrelated disabled/unconstructible alias is skipped and is neither token by itself.

No statistic, applicability derivation, row reconciliation, or analysis-runtime snapshot persistence begins before all registered strata pass this reconstruction gate.

---

## 3. Closure matrix

The independent review's two blockers are closed as follows:

```text
BLOCKER_1_FROZEN_ESTIMATOR_NESTING: CLOSED
MODEL_STRATUM_KEY: (provider, model)
NESTING_LEVELS_INSIDE_TASK: 2
REPETITION_WEIGHT_WITHIN_STRATUM: EQUAL_FIXED_PRE_RUN
STRATUM_WEIGHT_WITHIN_TASK: EQUAL_FIXED_PRE_RUN
SEPARATE_PROVIDER_AVERAGE_LEVEL: NONE

BLOCKER_2_PROVIDER_RECONSTRUCTION: CLOSED
UNRELATED_UNINSTANTIABLE_ALIAS: SKIP
COARSE_PREFILTER: (candidate.name, candidate.model)
FINAL_IDENTITY_SELECTOR: runtime_identity_digest
ZERO_COARSE_CANDIDATES: ANALYSIS_CONFIGURATION_MISMATCH
COARSE_EXISTS_BUT_NO_DIGEST_MATCH: ANALYSIS_RUNTIME_MISMATCH
MULTIPLE_DIGEST_MATCHES: ANALYSIS_CONFIGURATION_MISMATCH
CALLER_PROVIDER_INJECTION: NONE
NETWORK_INFERENCE_DURING_ANALYSIS_CAPTURE: NONE
PROSPECTIVE_LOAD_PROVIDER_RECONSTRUCTIBILITY_OBLIGATION: REQUIRED
```

`WU6_REVIEW_BLOCKERS_REPAIRED: YES`
