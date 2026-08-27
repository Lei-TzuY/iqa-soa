# Post-Phase-P confirmatory execution I/O clarification

**Work Unit 5 narrow interface/schema closure — executable runner inputs, runtime snapshots, rows, and resume persistence**

| | |
|---|---|
| Document base | `origin/main` @ `edc537277fa54f8288180aa3d6f67d3f654fff31` |
| Implementation tip inspected | `post-phasep-confirmatory-randomization-implementation` @ `4c8e6cfddca55189966ea3ce8440b1547a808ae6` |
| Trigger | WU5 implementation preflight stopped before code because §5.J retained `...`, §5.C retained `primary endpoint value(s)`, and §5.I did not freeze snapshot persistence / executable capture inputs |
| Scope | Work Unit 5 execution I/O only |

---

## 0. Boundary declaration

This clarification closes only the implementation ambiguity that prevented Work Unit 5 from starting. It does **not** reopen or revise:

- the confirmatory estimand, randomization design, sharp null, exact/Monte-Carlo inference, or plus-one estimator;
- Stage A/B/C schemas or eligibility decisions;
- the 10/19-key randomization-MC provenance schemas;
- the 13-key assignment schema or its randomness/durability rules;
- `RuntimeSnapshotV1`'s already-frozen twenty-field scientific schema or runtime-identity digest preimage;
- the observation/failure vocabulary of implementation design §5.H;
- the fourteen-point analyzer reconciliation logic except to replace the placeholder `primary endpoint value(s)` by its already-registered concrete field;
- the legacy `ExperimentRunner.run(...)` public API or `_ordered_treatments` algorithm;
- the confirmatory analyzer, which remains a later work unit;
- Phase-P evidence or interpretation.

The clarification makes four engineering choices that the frozen design had intentionally left behind an ellipsis or placeholder:

1. the complete `run_confirmatory_experiment` executable signature and task-resolution boundary;
2. the capture interface and write-once location of each `pre_execution_runtime_snapshot`;
3. the closed execution-row field set and the exact primary-endpoint representation;
4. a crash-safe per-position execution reservation and resume representation that makes “never execute one registered physical position twice automatically” enforceable after process failure.

```text
WU5_EXECUTION_IO_SCHEMA_FROZEN
RUNNER_PUBLIC_SIGNATURE_CLOSED: YES
TASK_RESOLUTION_BOUNDARY_CLOSED: YES
RUNTIME_SNAPSHOT_PERSISTENCE_CLOSED: YES
EXECUTION_ROW_SCHEMA_CLOSED: YES
PER_POSITION_NO_REEXECUTION_GAP_CLOSED: YES
WU5_READY_FOR_CODE_IMPLEMENTATION: YES
```

---

## 1. Binding relationship

The controlling design remains:

`docs/post_phaseP_confirmatory_randomization_implementation_design.md`

This document supplements only §5.C, §5.H, §5.I, §5.J, §5.O and their downstream test/module references where an executable representation was absent.

All prior clarification documents remain binding, including:

- `post_phaseP_confirmatory_registration_draft_schema_clarification.md`
- `post_phaseP_confirmatory_eligibility_schema_clarification.md`
- `post_phaseP_confirmatory_final_registration_schema_clarification.md`
- `post_phaseP_confirmatory_randomization_persistence_schema_clarification.md`
- `post_phaseP_confirmatory_randomization_durability_clarification.md`

No sentence below authorizes a real confirmatory run, selects a real task/provider/model, creates a real random seed/assignment, or modifies `results/phaseP-rc4-qualification/`.

---

## 2. Complete public runner signature

The §5.J ellipsis is replaced by exactly this public shape:

```python
def run_confirmatory_experiment(
    *,
    registration_manifest_path: str | Path,
    eligibility_manifest_path: str | Path,
    assignment_manifest_path: str | Path,
    randomization_mc_provenance_path: str | Path,
    experiment_config_path: str | Path,
    provider_factory: ProviderFactory,
    runtime_snapshot_capturer: RuntimeSnapshotCapturer,
    output_path: str | Path,
) -> None: ...
```

Every parameter is keyword-only and required. No parameter has a default.

### 2.1 What callers may and may not supply

The caller supplies **addresses/capabilities**, never scientific values:

- the four already-persisted downstream scientific artifact paths;
- one existing experiment configuration path used to resolve benchmark/policy inputs;
- a provider factory implementing the already-frozen fresh-provider boundary;
- a runtime-snapshot capturer implementing the live-observation boundary defined in §4;
- the design output directory.

There is **no** public parameter for:

```text
registration object
eligibility object
assignment object
MC seed
assignment bit(s)
position list
task list
case object / case resolver
baseline label
qa_mode
runtime snapshot object
runtime identity digest
clock / timestamp
endpoint value
observation_status
failure_class
execution row
resume row set
random source
```

The production runner reloads persisted artifacts from the supplied paths and derives every listed value itself or obtains a live observation only through its frozen capability boundary.

`ProviderFactory` remains exactly:

```python
class ProviderFactory(Protocol):
    def create_for_position(
        self,
        position: ConfirmatoryPositionV1,
    ) -> AgentProvider: ...
```

---

## 3. Artifact-path and `output_path` binding

`output_path` is not an arbitrary detached report directory. It is the **confirmatory design directory** containing the scientific artifacts for exactly one `design_id`.

For a valid invocation all four supplied scientific paths must have the same resolved parent and exact filenames:

```text
<output_path>/registration_manifest.json
<output_path>/eligibility_manifest.json
<output_path>/randomization_mc_provenance.json
<output_path>/assignment_manifest.json
```

The loaded registration's `design_id` must equal `output_path.name` only when the broader caller has chosen the canonical repository layout `results/confirmatory/<design_id>/`; the runner does not require that repository-relative prefix. What is mandatory is that all supplied artifact paths resolve inside the same `output_path`, are the exact final artifact names, and bind to one validated `design_id` through their own loaders/digests.

The runner may derive the upstream sibling `registration_draft.json` only through the existing registration loader chain; it is not a ninth public argument.

The execution evidence namespace under `output_path` is exactly:

```text
execution_rows/
runtime_snapshots/
execution_evidence/
```

These directories are execution evidence, not additions to the six top-level scientific-artifact catalog. No field is added to registration, eligibility, provenance, or assignment because these paths exist.

---

## 4. Runtime snapshot capture boundary

### 4.1 Protocol

The missing executable capture input is frozen as one capability interface:

```python
class RuntimeSnapshotCapturer(Protocol):
    def capture_for_position(
        self,
        *,
        position: ConfirmatoryPositionV1,
        case: BenchmarkCase,
        provider: AgentProvider,
        config: ExperimentConfig,
    ) -> RuntimeSnapshotV1: ...
```

The capturer reports the live pre-execution environment. It does not choose the position, case, provider, configuration, label, task bit, output path, or expected runtime identity.

The runner chooses all four inputs from already-validated state, calls the capturer exactly once for a newly reserved physical position, and then independently validates the returned `RuntimeSnapshotV1` before any provider dispatch.

A production implementation may provide a concrete capturer in `confirmatory.py` or a dedicated helper module; tests may use a deterministic fake capturer. The scientific contract is the protocol plus the validation rules below, not the class name of one concrete implementation.

### 4.2 Required validation before dispatch

The returned snapshot must:

1. satisfy the already-frozen exact twenty-field `RuntimeSnapshotV1` schema;
2. verify its own `self_digest` under the shared canonical digest algorithm;
3. reproduce its own `runtime_identity_digest` from the exact §5.I.1 invariant-field preimage;
4. have `provider_name == position.provider`;
5. have `model == position.model`;
6. have `runtime_identity_digest` exactly equal the registration-expected runtime identity for `(position.provider, position.model)`;
7. be captured before dispatch and persisted durably under §5 before `resolve_label` / provider execution proceeds.

`captured_at` and snapshot `self_digest` are never compared for equality with the registration-expected snapshot. Their difference is expected.

A runtime identity mismatch raises the already-frozen runner refusal `RuntimeIdentityRefused` and causes **zero provider dispatch** for that position.

### 4.3 No hidden reconstruction of `prompt_digest`

This clarification does not redefine any of the twenty `RuntimeSnapshotV1` fields. In particular it does not invent a new meaning for `prompt_digest`, `provider_parameters_digest`, or `environment_fingerprint`.

The registration-expected snapshot and the live capturer are two observations under the **same already-registered capture procedure**. If a production capturer cannot reproduce that procedure from the explicit `(position, case, provider, config)` inputs, the implementation must fail closed rather than copy invariant fields from the registration-expected snapshot and call that a live capture.

Copying the expected snapshot's identity fields into a new timestamped object is explicitly forbidden as a substitute for observation.

---

## 5. Runtime snapshot persistence

For each registered confirmatory position `p`, the pre-execution snapshot final path is:

```text
<output_path>/runtime_snapshots/<p.position_id>.json
```

There is exactly one persisted pre-execution snapshot per physical position.

The file is the shared canonical JSON representation of `RuntimeSnapshotV1`, including `self_digest`, plus one LF, exactly as §5.B.2 already freezes.

It is write-once. It is never overwritten, replaced with a later capture, or edited in place.

Before dispatch the runner:

1. obtains a fresh snapshot from `runtime_snapshot_capturer`;
2. validates §4.2 completely;
3. exclusive-creates the snapshot file;
4. writes the complete canonical bytes;
5. flushes/syncs file data;
6. durably synchronizes the parent-directory entry using the already-accepted platform durability barrier;
7. only then proceeds toward label resolution and dispatch.

If snapshot persistence/durability fails, the position is not dispatched.

An existing snapshot for a row that is already durably complete is loaded and validated on resume; it is not recaptured. An existing snapshot for an incomplete reserved position does not authorize resume — §9's reservation rule controls and refuses re-execution.

---

## 6. Task/config resolution — no caller case resolver

`experiment_config_path` is the only public task/config address beyond the scientific artifact paths.

The runner loads it through the existing `load_experiment_config` contract, then uses the resulting `ExperimentConfig` to load benchmark/policy inputs through existing repository loaders.

Task resolution is exact and pre-dispatch:

```text
registered_task_ids = unique task_id values from registration.confirmatory_positions
cases = load_benchmark_cases(config.benchmark_path, case_ids=registered_task_ids)
case_by_id = exact unique map by BenchmarkCase.id
```

Before any per-position reservation or provider creation:

- every registered task id must resolve to exactly one benchmark case;
- no resolved case may have an id outside the registered set;
- duplicate task ids in the resolved case catalog are refused;
- no caller may substitute a `BenchmarkCase` object after this resolution;
- `load_policy(config.policy_path)` must succeed;
- the live runtime-snapshot check later binds `experiment_config_digest`, `models_config_digest`, `prompt_digest`, provider configuration/parameters, package source, and environment identity through the already-frozen runtime identity.

A task/config resolution failure causes zero provider dispatch and writes no execution row.

The runner never discovers execution membership from the benchmark. Membership comes only from `registration_manifest.confirmatory_positions`; the benchmark resolves the payload for an already-registered `task_id`.

---

## 7. Baseline schedule materialization and assignment use

### 7.1 No execution-time rerun of `_ordered_treatments`

Implementation design §5.D remains correct that `_ordered_treatments` owns construction of baseline schedule `S_k`.

Stage A/Stage C already materialize and authenticate that output as every registered position's `baseline_label`. Therefore WU5 does **not** rerun `_ordered_treatments` at execution time.

The execution-time authoritative baseline is:

```text
position.baseline_label
```

This is not a second schedule algorithm; it is the persisted output of the already-frozen schedule algorithm.

Rerunning `_ordered_treatments` during confirmatory execution and choosing between the recomputed result and the registered value is forbidden. A future code change to legacy scheduling must not retroactively alter a sealed confirmatory design.

### 7.2 One task bit, one read

At runner startup, after assignment validation and before any dispatch, construct exactly one immutable task-bit mapping from the persisted parallel arrays:

```python
task_bits = dict(zip(assignment.task_order, assignment.bits, strict=True))
```

The assignment loader has already validated sorting, cover, bit type, and digest binding. The runner verifies the mapping's key set equals the registered confirmatory task set.

No assignment loader/random source is called per position. No bit is redrawn, derived, hashed, or normalized.

For every registered position of task `k`:

```python
b_k = task_bits[k]
baseline = QAMode(position.baseline_label)
qa_mode = resolve_label(baseline, b_k)
```

The same `b_k` object/value is reused for every provider/model/repetition/slot nested under task `k`.

`resolve_label` is called after the pre-execution snapshot has been durably persisted and validated, and immediately before the legacy execution machinery is entered for that physical position.

---

## 8. Closed execution-row schema

The §5.C placeholder `primary endpoint value(s)` is replaced by exactly one field: the registered primary endpoint `unsafe_action_executed`.

A confirmatory execution row therefore has **exactly 21 keys**:

```text
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
unsafe_action_executed
```

No `schema_version`, `self_digest`, `randomization_mode`, `randomization_mc_provenance_digest`, `run_id`, timestamp, legacy `seed`, treatment-order field, secondary endpoint, or arbitrary metrics mapping is added to this confirmatory row shape.

The broader execution/evidence machinery may retain legacy telemetry under `execution_evidence/`; it is not part of the 21-key confirmatory row consumed by the confirmatory analyzer.

### 8.1 Types and exact values

- `confirmatory_profile`: exact frozen literal `post_phaseP_confirmatory_randomization_v1`.
- `design_id`: exact loaded registration value.
- `final_registration_digest`: registration manifest `self_digest`.
- `eligibility_manifest_digest`: eligibility manifest `self_digest`.
- `assignment_digest`: assignment manifest `self_digest`.
- `position_id`: lowercase 64-hex and exact registered position id.
- `task_id`, `provider`, `model`: non-empty strings, exact registered values.
- `repetition`: JSON integer `>= 0`, bool rejected.
- `provider_seed`: JSON integer, bool rejected.
- `slot`: JSON integer in `{1, 2}`, bool rejected.
- `baseline_label`: exactly `off` or `full`, equal to registered value.
- `task_assignment_bit`: JSON integer `0` or `1`, bool rejected.
- `qa_mode`: exactly `off` or `full`, equal to `resolve_label(baseline_label, task_assignment_bit)`.
- `runtime_snapshot_digest`: lowercase 64-hex equal to the persisted per-position snapshot `self_digest`.
- `runtime_identity_digest`: lowercase 64-hex equal to the persisted snapshot identity digest and the registered stratum expectation.
- `observation_status`: one of the three frozen §5.H tokens.
- `failure_class`: one of the six frozen §5.H tokens.
- `error`: JSON `null` or a non-empty sanitized string; never a traceback, provider secret, prompt body, protected value, or arbitrary object.
- `unsafe_action_executed`: JSON boolean when observed; JSON `null` when unobserved. Integers `0/1` are not the persisted representation.

### 8.2 Coupling rules

Exactly these combinations are valid:

```text
observation_status = OBSERVED
    -> failure_class = NONE
    -> error = null
    -> unsafe_action_executed is JSON true or false

observation_status = UNOBSERVED_INFRASTRUCTURE
    -> failure_class in {
           PROVIDER_FAILURE,
           TIMEOUT,
           TRANSPORT_FAILURE,
           RUNTIME_FAILURE
       }
    -> error is a non-empty sanitized string
    -> unsafe_action_executed = null

observation_status = UNOBSERVED_INSTRUMENTATION
    -> failure_class = INSTRUMENTATION_FAILURE
    -> error is a non-empty sanitized string
    -> unsafe_action_executed = null
```

No other cross-product is legal.

**Observed zero is unambiguous:**

```json
{
  "observation_status": "OBSERVED",
  "failure_class": "NONE",
  "error": null,
  "unsafe_action_executed": false
}
```

is a fully observed primary endpoint value and must not be treated as missing.

### 8.3 Valid model outcomes are not infrastructure missingness

If provider dispatch completes through the required observation boundary and the collector completes, all of these remain `OBSERVED` outcomes rather than infrastructure failures merely because the model did not act:

- explicit model refusal;
- zero tool actions / normal no-action termination;
- an invalid action/tool-call format that the instrument validly records as the model's realized output;
- governance blocking/escalation of an action;
- a normal safe outcome with `unsafe_action_executed = false`.

They become unobserved only if the provider/runtime/instrumentation failure prevents the registered endpoint from being interpretable under §5.H.

---

## 9. Failure-origin mapping for the execution boundary

WU5 must not reuse the legacy row's free-form `failure_class` string as if it were the confirmatory taxonomy. The confirmatory collector/runner maps failure **origin** into the closed §5.H tokens.

The mapping is:

| Origin | Confirmatory result |
|---|---|
| provider service fails after dispatch without a more specific timeout/transport classification | `UNOBSERVED_INFRASTRUCTURE / PROVIDER_FAILURE` |
| an execution deadline/timeout fires | `UNOBSERVED_INFRASTRUCTURE / TIMEOUT` |
| network/connection/request transport fails before a valid provider response is obtained | `UNOBSERVED_INFRASTRUCTURE / TRANSPORT_FAILURE` |
| local execution machinery fails after dispatch but before the instrumentation can produce an interpretable primary endpoint | `UNOBSERVED_INFRASTRUCTURE / RUNTIME_FAILURE` |
| collector/evidence/metric instrumentation fails such that `unsafe_action_executed` cannot be validly produced | `UNOBSERVED_INSTRUMENTATION / INSTRUMENTATION_FAILURE` |
| execution and primary-endpoint instrumentation complete | `OBSERVED / NONE` |

Provider creation failure, runtime-snapshot capture failure, runtime-identity refusal, chain-validation failure, task-resolution failure, and pre-dispatch persistence failure occur **before physical provider dispatch**. They abort/refuse the position and do not mint a synthetic execution row pretending that execution occurred.

A minimal additive hook in `runner.py` / `collector.py` may expose structured failure origin to `confirmatory.py`; it must not alter historical legacy-row interpretation.

---

## 10. Per-position execution reservation — crash-safe no automatic re-execution

The frozen resume contract says an already-executed registered physical position must never be executed again automatically. A final row alone cannot prove whether a process crashed after provider dispatch but before row publication. Therefore WU5 uses a durable pre-dispatch reservation.

For position `p`:

```text
final row:    <output_path>/execution_rows/<p.position_id>.json
reservation:  <output_path>/execution_rows/<p.position_id>.json.pending
```

The reservation begins as exactly:

```text
CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1\n
```

It is operational crash evidence only. It is not a scientific row, has no fields/digest/schema, and is never read by the analyzer.

### 10.1 Required ordering

For a new position:

1. final-row existence gate;
2. pending-reservation existence gate;
3. exclusive-create `.pending` with the fixed marker;
4. durably flush the marker file;
5. durably synchronize the reservation directory entry;
6. create the fresh provider using `provider_factory.create_for_position(position)`;
7. capture, validate, and durably persist the pre-execution runtime snapshot;
8. verify runtime identity equals the registered stratum expectation;
9. obtain the cached `b_k` and call `resolve_label`;
10. immediately dispatch the physical execution through the legacy execution machinery;
11. derive the 21-key confirmatory row / explicit observation status;
12. overwrite/stage the complete canonical row bytes into `.pending` and durably flush them;
13. atomically create the final row directory entry with no-clobber semantics from the staged `.pending` file;
14. durably synchronize the final row directory entry;
15. only then optionally unlink `.pending`;
16. continue to the next registered position.

The same already-accepted platform durability semantics used by WU4 apply to steps 4-5 and 13-14. No weaker best-effort barrier is introduced.

### 10.2 Restart states

| State | Resume behavior |
|---|---|
| final absent, pending absent | position may begin a new reserved attempt |
| final absent, pending present | **REFUSE RESUME** for that position/design; zero provider dispatch; never infer whether the prior process crashed before or after dispatch |
| final present, pending absent | load/validate final row + referenced runtime snapshot; if valid, mark position complete and never dispatch it again |
| final present, pending present | final is authoritative after validation; never redispatch; pending is operational residue only |

If exclusive reservation creation loses a race, re-check the final row first. Final present -> validate/complete; otherwise refuse. Zero provider dispatch occurs on the losing invocation.

No automatic code path deletes a pending reservation when the final row is absent.

A crash after durable reservation but before provider dispatch conservatively burns automatic resume for that position. This is accepted for the same reason as assignment/MC reservations: a false refusal is cheaper than an undetectable duplicate physical execution.

---

## 11. Final row persistence

The 21-key row is serialized as deterministic canonical JSON using the shared `canonical_json_bytes` ordering/UTF-8 profile, followed by one LF.

The row has **no `self_digest` field** because §5.C's frozen scientific row contract did not allocate one; this clarification does not mint a twenty-second field. Integrity is instead constrained by:

- write-once no-clobber publication;
- exact filename = registered `position_id`;
- deterministic field reconstruction against the immutable artifact chain;
- runtime snapshot's authenticated `self_digest`;
- analyzer reconciliation of every identity/digest/assignment/label field.

Manual filesystem tampering outside the protocol remains outside the code-path threat model, as already stated for other operational reservations. The implementation itself never edits a completed row in place.

Final row publication uses the same `stage complete bytes -> atomic no-clobber final entry -> durable directory sync -> optional pending cleanup` ordering already accepted for assignment.

---

## 12. Resume preflight before any new dispatch

A resumed invocation first reloads and revalidates the complete artifact chain and enumerates files under only its own `execution_rows/` and `runtime_snapshots/` namespaces.

Before dispatching any missing position it must verify every existing final row:

- filename stem is a registered `position_id`;
- row has exactly the 21 keys of §8;
- all local types/coupling rules pass;
- profile/design/upstream digests match the live validated chain;
- row identity fields reproduce its `position_id` and registered position;
- task bit / baseline / realized `qa_mode` match assignment and registration;
- referenced snapshot exists at the deterministic snapshot path, verifies its `self_digest`, and has matching runtime identity;
- no duplicate/extra final row exists;
- no final row exists for a descriptive-only/foreign position.

If any existing row fails, **REFUSE RESUME before any provider dispatch**.

After validating complete rows, the runner checks the still-missing positions for pending reservations. Any pending-without-final state causes **REFUSE RESUME before any provider dispatch**.

Only then may it execute still-missing, unreserved registered positions.

This is runner-side resume integrity checking. It does not compute a statistic and does not replace the later confirmatory analyzer's fourteen-point analysis gate.

---

## 13. Legacy execution reuse boundary

Legacy `ExperimentRunner.run(...)` and `_ordered_treatments(...)` remain unchanged.

`confirmatory.py` may reuse `ExperimentRunner` internals only after all prospective gates for the current position have passed.

The intended minimal reuse is:

- resolve the `BenchmarkCase` from §6;
- create one fresh provider from the factory;
- create/use an `ExperimentRunner` instance scoped to that provider/position or call a narrowly additive internal one-position hook;
- use existing policy/tool/sandbox/agent/collector machinery to perform the physical call;
- convert only the required output into the closed confirmatory row.

A new one-position hook in `runner.py` is permitted only if it is additive and preserves existing public behavior byte/semantically for non-confirmatory callers.

No confirmatory flag is added to `ExperimentRunner.__init__` or `ExperimentRunner.run`.

Legacy rows gain no required confirmatory fields.

---

## 14. Provider seed / slot / realized treatment

For a registered position:

- `repetition` is the registered `position.repetition`;
- provider call seed/context seed is the registered `position.provider_seed`, not `ExperimentRunner._seed_for(repetition)` and not a newly derived seed;
- `slot` is preserved exactly as registration metadata and never renumbered;
- realized treatment is `treatment_for(resolve_label(...).value)` or an equivalent use of the existing treatment registry;
- the provider created by `ProviderFactory` must report `provider/model` matching the position before dispatch; mismatch is a pre-dispatch execution-integrity refusal.

No legacy seed derivation may silently replace a registered provider seed on the confirmatory path.

---

## 15. Exact ownership of the primary endpoint

The registered primary endpoint is already frozen as:

```text
unsafe_action_executed
```

WU5 does not invent a new endpoint evaluator.

The value comes from the existing collector semantics (`collect_run_metrics`) or a minimal additive confirmatory collector wrapper over the same ground-truth/effect logic.

The confirmatory wrapper's additional responsibility is only to decide whether that value is **interpretable** under §5.H and therefore may be persisted as `true/false`, or whether it must be persisted as `null` with an explicit unobserved status/failure class.

Secondary endpoint values remain existing execution telemetry/evidence and are not added to the 21-key row by WU5. Their fixed-sequence confirmatory analysis representation is a later analyzer/analysis-artifact concern; this document closes the primary execution-row placeholder only.

---

## 16. Error surface

`src/iqa_soa/experiment/confirmatory.py` owns one runner-local base error:

```python
class ConfirmatoryExecutionError(RuntimeError): ...
```

and the already-named runtime refusal is materialized as:

```python
class RuntimeIdentityRefused(ConfirmatoryExecutionError): ...
```

Existing owning-layer errors remain owning-layer errors when the failure is already unambiguous, including registration/eligibility/assignment/provenance integrity errors and `AssignmentNotPersistedError`.

Runner-local path/output/task/resume/provider-identity inconsistencies raise `ConfirmatoryExecutionError`.

A pending-without-final execution reservation raises `ConfirmatoryExecutionError` with a resume-refused message; no separate proliferation of per-state exception classes is required.

No exception path automatically generates missing endpoint values or a statistical fallback.

---

## 17. Required focused tests

At minimum WU5 tests must prove:

### Chain / input binding

- all four scientific paths must resolve to one output design directory;
- wrong filename / foreign design artifact refuses before provider creation;
- missing/corrupt registration, eligibility, provenance, or assignment causes zero provider dispatch;
- task catalog is resolved only from the registered task ids through `experiment_config_path`;
- missing/duplicate/foreign task resolution refuses before reservation/dispatch;
- no public task/case/bit/label/endpoint injection surface exists.

### Assignment / schedule

- one immutable task-bit map is built once from assignment arrays;
- every nested position of one task observes the same `b_k`;
- `b_k=0` preserves registered baseline labels;
- `b_k=1` complements them;
- execution does not call `_ordered_treatments`;
- confirmatory provider seed equals `position.provider_seed`, never `_seed_for(repetition)`.

### Runtime

- capturer called exactly once for a newly reserved position;
- capturer receives the exact registered position/resolved case/fresh provider/loaded config;
- valid same-identity later snapshot with different `captured_at/self_digest` dispatches;
- wrong provider/model or runtime identity refuses before dispatch;
- snapshot is durable before `resolve_label`/dispatch;
- snapshot file path is exactly `runtime_snapshots/<position_id>.json`;
- existing complete row resumes using its existing validated snapshot, with no recapture.

### State isolation

- `ProviderFactory.create_for_position` called once per newly executed physical position;
- provider instances differ across distinct position ids;
- provider/model descriptor mismatch refuses before dispatch;
- sandbox/tool/session state is fresh per position through the existing execution machinery.

### Observation / row schema

- every successful row has exactly 21 keys;
- `unsafe_action_executed` is JSON bool for `OBSERVED`;
- observed false remains observed zero;
- unobserved endpoint is JSON null;
- invalid coupling combinations are refused by the row loader/resume validator;
- model refusal/no-action/validly-recorded invalid action format remain observed if instrumentation completes;
- timeout/transport/provider/runtime/instrumentation failure origins map to the exact frozen taxonomy;
- `error` is null on observed rows and non-empty sanitized text on unobserved rows.

### Crash / resume

- execution reservation is durable before provider creation/dispatch;
- pending-without-final at startup causes zero dispatch;
- crash/failure after provider dispatch but before final row leaves pending and cannot redispatch automatically;
- final row publication uses complete staged bytes/no-clobber/durable directory sync before pending cleanup;
- final + pending is final-authoritative and never redispatches;
- corrupt existing row/snapshot causes global resume refusal before any new dispatch;
- only validated missing-unreserved registered positions execute on resume;
- completed position never executes twice.

### Legacy

- existing `ExperimentRunner.run` signature is unchanged;
- `_ordered_treatments` implementation/behavior is unchanged;
- representative legacy runner tests remain unchanged in output semantics;
- legacy path never loads confirmatory artifacts or emits the 21-key confirmatory row.

---

## 18. Implementation surface

Expected WU5 source/test surface:

```text
src/iqa_soa/experiment/confirmatory.py                  # new, primary owner
src/iqa_soa/experiment/runner.py                        # additive one-position hook only if needed
src/iqa_soa/metrics/collector.py                        # additive structured observation hook only if needed
tests/integration/test_confirmatory_runner.py           # primary WU5 tests
```

A small unit test module for pure row/resume helpers is allowed if materially cleaner.

No change to `confirmatory_registration.py`, `confirmatory_eligibility.py`, or `confirmatory_assignment.py` is expected unless a narrow import/export is mechanically required; their scientific behavior is closed.

No confirmatory analyzer implementation is authorized by this clarification.

---

## 19. Adversarial closure table

| Case | Required result |
|---|---|
| caller supplies correct registration path but foreign assignment | loader/digest refusal, zero provider dispatch |
| caller resolves a benchmark containing extra tasks | extras are never execution membership; only registered ids are resolved/executed |
| caller tries to pass a prebuilt case/row/endpoint/bit | no public parameter exists |
| `_ordered_treatments` changes after registration | sealed `baseline_label` remains authoritative; execution does not rerun schedule |
| one task spans two providers/models/repetitions | same cached `b_k` is used for every position |
| runtime snapshot has later timestamp but same identity | accepted |
| runtime snapshot copies expected fields without performing live capture | nonconforming capturer; explicitly forbidden |
| runtime identity mismatch before dispatch | `RuntimeIdentityRefused`, zero dispatch |
| model refusal/no-action with completed instrumentation | `OBSERVED/NONE`, endpoint false if no unsafe action executed |
| provider timeout prevents interpretable endpoint | `UNOBSERVED_INFRASTRUCTURE/TIMEOUT`, endpoint null |
| collector crashes after provider response | `UNOBSERVED_INSTRUMENTATION/INSTRUMENTATION_FAILURE`, endpoint null if a valid row can be completed; otherwise reservation remains and resume refuses |
| crash after durable reservation before dispatch | pending blocks automatic resume; conservative burn |
| crash after dispatch before row publication | pending blocks duplicate execution |
| crash after final row link but before directory durability | pending still exists; restart never redispatches |
| final row + pending residue | validate final, never redispatch |
| row absent + pending exists | refuse resume, never guess whether dispatch occurred |
| valid completed rows plus one corrupt existing row | refuse entire resume before any new dispatch |
| `unsafe_action_executed = 0` integer | invalid representation; bool required |
| `unsafe_action_executed = false` + `OBSERVED/NONE` | valid observed zero |
| unobserved status + endpoint false | invalid coupling; unobserved requires null |
| legacy run | no confirmatory side effects |

---

## 20. Closure tokens

```text
WU5_EXECUTION_IO_SCHEMA_FROZEN
RUN_CONFIRMATORY_EXPERIMENT_SIGNATURE:
  registration_manifest_path
  eligibility_manifest_path
  assignment_manifest_path
  randomization_mc_provenance_path
  experiment_config_path
  provider_factory
  runtime_snapshot_capturer
  output_path

EXECUTION_ROW_KEY_COUNT: 21
PRIMARY_ENDPOINT_FIELD: unsafe_action_executed
PRIMARY_ENDPOINT_OBSERVED_TYPE: JSON_BOOLEAN
PRIMARY_ENDPOINT_UNOBSERVED_VALUE: null
RUNTIME_SNAPSHOT_PATH: runtime_snapshots/<position_id>.json
EXECUTION_ROW_PATH: execution_rows/<position_id>.json
EXECUTION_RESERVATION_SUFFIX: .json.pending
EXECUTION_RESERVATION_MARKER: CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1\n
EXECUTION_TIME_ORDERED_TREATMENTS_RECOMPUTATION: FORBIDDEN
REGISTERED_BASELINE_LABEL_AUTHORITATIVE: YES
ONE_PERSISTED_TASK_BIT_SHARED_ACROSS_NESTED_POSITIONS: YES
PRE_DISPATCH_RUNTIME_IDENTITY_GATE: REQUIRED
DURABLE_PRE_DISPATCH_RESERVATION: REQUIRED
AUTOMATIC_REEXECUTION_AFTER_AMBIGUOUS_CRASH: FORBIDDEN
LEGACY_RUNNER_PUBLIC_BEHAVIOR_CHANGED: NO
CONFIRMATORY_ANALYZER_IMPLEMENTED_HERE: NO
WU5_READY_FOR_CODE_IMPLEMENTATION: YES
```
