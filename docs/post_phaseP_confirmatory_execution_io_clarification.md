# Post-Phase-P confirmatory execution I/O clarification

**Work Unit 5 narrow interface/schema closure — executable runner inputs, repository-owned runtime capture, execution rows, and resume persistence**

| | |
|---|---|
| Document base | `origin/main` @ `edc537277fa54f8288180aa3d6f67d3f654fff31` |
| Implementation tip inspected | `post-phasep-confirmatory-randomization-implementation` @ `4c8e6cfddca55189966ea3ce8440b1547a808ae6` |
| Trigger | WU5 implementation preflight stopped before code because §5.J retained `...`, §5.C retained `primary endpoint value(s)`, and §5.I did not freeze an executable live-capture/persistence procedure |
| Independent review | First review BLOCKed five concrete execution-I/O defects; this revision closes only those five defects |
| Scope | Work Unit 5 execution I/O only |

---

## 0. Boundary declaration

This clarification closes only the implementation ambiguity that prevented Work Unit 5 from starting. It does **not** reopen or revise:

- the confirmatory estimand, randomization design, sharp null, exact/Monte-Carlo inference, or plus-one estimator;
- Stage A/B/C scientific schemas or eligibility dispositions;
- the 10/19-key randomization-MC provenance schemas;
- the 13-key assignment schema or its randomness/durability rules;
- `RuntimeSnapshotV1`'s already-frozen twenty-field scientific schema or its seventeen-field runtime-identity preimage;
- the observation/failure vocabulary of implementation design §5.H;
- the fourteen-point analyzer reconciliation architecture, except that the execution-row placeholder `primary endpoint value(s)` is now replaced by the complete already-registered fixed-sequence endpoint family plus the timestamp required by the already-frozen provenance temporal check;
- the legacy `ExperimentRunner.run(...)` public API or `_ordered_treatments` algorithm;
- the confirmatory statistical analyzer, which remains a later work unit;
- Phase-P evidence or interpretation.

This revision makes exactly the implementation choices needed to close WU5:

1. the complete `run_confirmatory_experiment` executable signature and task/config resolution boundary;
2. one repository-owned production `RuntimeSnapshotV1` capture procedure shared by registration-time and execution-time capture, with no caller-supplied capturer on the production runner;
3. exact source/preimage rules for every runtime-snapshot field that had previously been only a name;
4. the write-once location of each `pre_execution_runtime_snapshot`;
5. the closed 27-key execution-row field set, including the execution timestamp, primary endpoint, and all five registered fixed-sequence secondary endpoints;
6. a crash-safe per-position execution reservation that makes “never automatically execute one registered physical position twice after ambiguous process failure” enforceable;
7. a namespace-wide resume preflight over every row, reservation, and runtime snapshot before any new provider dispatch.

```text
WU5_EXECUTION_IO_SCHEMA_FROZEN
RUNNER_PUBLIC_SIGNATURE_CLOSED: YES
CALLER_RUNTIME_CAPTURER_REMOVED: YES
REPOSITORY_OWNED_RUNTIME_CAPTURE_FROZEN: YES
RUNTIME_FIELD_SOURCES_CLOSED: YES
TASK_RESOLUTION_BOUNDARY_CLOSED: YES
RUNTIME_SNAPSHOT_PERSISTENCE_CLOSED: YES
EXECUTION_ROW_SCHEMA_CLOSED: YES
EXECUTION_ROW_KEY_COUNT: 27
PER_POSITION_NO_REEXECUTION_GAP_CLOSED: YES
NAMESPACE_WIDE_RESUME_PREFLIGHT: REQUIRED
WU5_READY_FOR_CODE_IMPLEMENTATION: YES
```

---

## 1. Binding relationship

The controlling design remains:

`docs/post_phaseP_confirmatory_randomization_implementation_design.md`

This document supplements only §5.C, §5.H, §5.I, §5.J, §5.L.3, §5.O and their downstream test/module references where an executable representation was absent.

All prior clarification documents remain binding, including:

- `post_phaseP_confirmatory_registration_draft_schema_clarification.md`
- `post_phaseP_confirmatory_eligibility_schema_clarification.md`
- `post_phaseP_confirmatory_final_registration_schema_clarification.md`
- `post_phaseP_confirmatory_randomization_persistence_schema_clarification.md`
- `post_phaseP_confirmatory_randomization_durability_clarification.md`

No sentence below authorizes a real confirmatory run, selects a real task/provider/model, creates a real random seed/assignment, or modifies `results/phaseP-rc4-qualification/`.

---

## 2. Complete public runner signature

The §5.J ellipsis is replaced by exactly this production public shape:

```python
def run_confirmatory_experiment(
    *,
    registration_manifest_path: str | Path,
    eligibility_manifest_path: str | Path,
    assignment_manifest_path: str | Path,
    randomization_mc_provenance_path: str | Path,
    experiment_config_path: str | Path,
    provider_factory: ProviderFactory,
    output_path: str | Path,
) -> None: ...
```

Every parameter is keyword-only and required. No parameter has a default.

**There is no `runtime_snapshot_capturer` parameter.** The production runner always calls the repository-owned capture procedure frozen in §4. A caller cannot replace live runtime observation with a self-consistent fabricated snapshot.

### 2.1 What callers may and may not supply

The caller supplies addresses and the already-frozen provider-factory capability, never observed scientific values:

- the four already-persisted downstream scientific artifact paths;
- one existing experiment configuration path used to resolve benchmark/policy/model inputs;
- a `ProviderFactory` implementing the already-frozen fresh-provider boundary of implementation design §5.E;
- the design output directory.

There is **no** production public parameter for:

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
runtime snapshot capturer
runtime identity digest
runtime field preimage
clock / timestamp
endpoint value(s)
observation_status
failure_class
execution row
resume row set
random source
```

The runner reloads persisted artifacts from the supplied paths and derives or observes every listed value through repository-owned code.

`ProviderFactory` remains the already-frozen interface:

```python
class ProviderFactory(Protocol):
    def create_for_position(
        self,
        position: ConfirmatoryPositionV1,
    ) -> AgentProvider: ...
```

This clarification does not reopen PR-4's provider-factory architecture.

---

## 3. Artifact-path and `output_path` binding

`output_path` is the confirmatory design directory for exactly one `design_id`.

For a valid invocation all four supplied scientific paths must resolve to exact children of the same resolved `output_path`:

```text
<output_path>/registration_manifest.json
<output_path>/eligibility_manifest.json
<output_path>/randomization_mc_provenance.json
<output_path>/assignment_manifest.json
```

After loading the registration, `output_path.name` must equal the validated `registration_manifest.design_id`. The path may live under a synthetic temporary root in tests or under the eventual canonical repository layout, but its final segment is always the design id. No detached report directory is accepted.

The runner derives the sibling `registration_draft.json` only through the existing owned registration/eligibility/final-registration loader chain; it is not another public argument.

The execution namespace under `output_path` is exactly:

```text
execution_rows/
runtime_snapshots/
execution_evidence/
```

`execution_rows/` and `runtime_snapshots/` are authoritative WU5 namespaces and are subject to the exhaustive preflight in §12. `execution_evidence/` may hold legacy-compatible detailed telemetry but is not a substitute for a confirmatory row or runtime snapshot and is not an input to the resume-state classification.

These directories do not add fields to registration, eligibility, MC provenance, or assignment.

---

## 4. Repository-owned `RuntimeSnapshotV1` capture

### 4.1 Single production procedure

The same repository-owned procedure is the only conforming production source of both:

1. Stage-A `registration_expected_runtime_snapshot` values when a future real registration is constructed; and
2. WU5 `pre_execution_runtime_snapshot` values immediately before physical execution.

Normative symbol/shape:

```python
def capture_runtime_snapshot_v1(
    *,
    config: ExperimentConfig,
    provider: AgentProvider,
) -> RuntimeSnapshotV1: ...
```

The function accepts **no** `RuntimeSnapshotV1`, expected runtime identity, expected digest, field override mapping, timestamp, clock, case, position, task bit, label, or arbitrary capture callback.

The production `run_confirmatory_experiment` calls this procedure directly. It never accepts a replacement through its public signature.

A registration-time orchestration that produces the future Stage-A expected snapshots must call the same procedure against the configured provider instance for each proposed `(provider, model)` stratum before the draft is sealed. `draft_registration(...)` remains the low-level schema sealing operation; this rule governs how its `proposed_runtime_configuration.registration_expected_runtime_snapshots` are obtained in a conforming real registration workflow.

### 4.2 Why the snapshot is stratum-level, not task-specific

Stage A already freezes exactly one expected `RuntimeSnapshotV1` per `(provider, model)` stratum, while registered tasks, prompts, provider seeds, steps, histories, and canonical resources vary across positions. Therefore the fields `prompt_digest` and `provider_parameters_digest` cannot mean “hash the realized task-specific request bytes.” Such a meaning would make one stratum snapshot impossible to compare across its positions.

This clarification resolves that old ambiguity without changing the twenty-field schema:

- `prompt_digest` authenticates the **complete prompt-source/template contract** used to construct task-specific requests;
- `provider_parameters_digest` authenticates the **complete `AgentProvider.generate_action` parameter-source template**, including every call parameter and the source from which its realized value must come;
- task-specific values themselves remain bound by the registered position, the benchmark/config digests, provider seed, execution row, and existing execution machinery.

A concrete physical request is conforming only if it is constructed from the frozen sources in §4.4. There is no hand-selected subset.

### 4.3 Digest primitives used by the capture procedure

Two digest primitives are used; neither is caller-configurable:

1. `canonical_digest(obj) = lowercase_hex(SHA256(canonical_json_bytes(obj)))`, using the existing §5.B.2 canonical JSON implementation.
2. `file_sha256(path) = lowercase_hex(SHA256(exact_file_bytes))` for source/config files. No line-ending normalization, YAML rewriting, or parsed-object reserialization occurs before this file digest.

`package_source_sha256` reuses the repository's existing package-source tree-digest semantics from `runner.py` over the `iqa_soa` Python package. WU5 may extract that helper without changing its algorithm; it must not invent a second package-tree hash.

> **CORRECTED — see `docs/post_phaseP_runtime_snapshot_benchmark_identity_correction.md`.**
> The two primitives above are stated as originally frozen and are retained here unaltered. `file_sha256` was applied to `config.benchmark_path`, which is a benchmark SOURCE ROOT and is a directory under every production configuration, so that one application was unsatisfiable. `benchmark_sha256` is now derived with `benchmark_source_sha256` — the repository's existing directory-capable path-tree digest, restricted to the frozen benchmark source set `{.json, .md, .yaml}` — exactly as `package_source_sha256` reuses that same algorithm for the package. `file_sha256` remains the primitive for `config.source_path`, `config.policy_path`, `config.models_path` and `config.ablations_path`, which are genuine single files. No other primitive, field or schema changes.

### 4.4 Exact source/preimage table

The capture procedure constructs the existing twenty `RuntimeSnapshotV1` fields from exactly these sources.

| RuntimeSnapshotV1 field | Exact source / preimage |
|---|---|
| `schema_version` | literal `RuntimeSnapshotV1` |
| `provider_name` | `provider.name`; non-empty; must describe the concrete fresh provider instance |
| `model` | `provider.model`; non-empty |
| `endpoint` | effective public endpoint in `provider.descriptor()["endpoint"]` when present; otherwise the deterministic local endpoint literal `local://<provider_name>/<model>` for a repository-owned non-network provider |
| `provider_config_digest` | `canonical_digest(ProviderConfigIdentityV1)` from §4.5.1 |
| `provider_parameters_digest` | `canonical_digest(ProviderParameterSourceTemplateV1)` from §4.5.2 |
| `timeout_seconds` | repository adapter for the concrete provider; for `OpenAICompatibleProvider`, canonical decimal rendering of `provider.timeout_seconds`; a repository-owned non-network provider records canonical `"0"`; unsupported provider class -> capture refuses |
| `retry_policy` | exact execution policy of §4.6; no caller values |
| `tool_contract_policy` | effective provider descriptor value; when the concrete repository provider has no policy channel, literal `none`; unsupported/unknown representation -> capture refuses |
| `native_tool_adapter_version` | repository constant `NATIVE_TOOL_ADAPTER_VERSION` |
| `package_source_sha256` | existing package-source tree digest of the executing `iqa_soa` package |
| `python_version` | `platform.python_version()` observed in the executing process |
| `artifact_version` | executing package `iqa_soa.__version__` |
| `prompt_digest` | `canonical_digest(PromptSourceTemplateV1)` from §4.5.3 |
| `experiment_config_digest` | `canonical_digest(ExperimentExecutionConfigIdentityV1)` from §4.5.4 |
| `models_config_digest` | `file_sha256(config.models_path)` |
| `environment_fingerprint` | `canonical_digest(EnvironmentIdentityV1)` using the exact already-frozen §5.I.3 eight-field object, with `provider_endpoint = endpoint` and the values above |
| `runtime_identity_digest` | existing §5.I.1 canonical digest over exactly the seventeen invariant fields, recomputed only after all seventeen exist |
| `captured_at` | internally captured once, whole-second UTC `YYYY-MM-DDTHH:MM:SSZ`, after live inputs above are observed and before `self_digest`; no caller time source |
| `self_digest` | existing §5.B.2 digest over the complete snapshot minus `self_digest` |

No field above is copied from the registration-expected snapshot on the WU5 path. The expected snapshot is used only **after** live capture, for the equality check on `runtime_identity_digest`.

### 4.5 Exact nested preimages

#### 4.5.1 `ProviderConfigIdentityV1`

```json
{
  "schema_version": "ProviderConfigIdentityV1",
  "provider_implementation": "<type(provider).__module__>.<type(provider).__qualname__>",
  "descriptor": {"<complete provider.descriptor() mapping>": "..."}
}
```

Rules:

- `descriptor` is the complete JSON-semantic mapping returned by the concrete provider's non-secret `descriptor()` implementation; no key is selected away.
- The mapping must be JSON-serializable under the frozen canonical profile without `default=str` or coercion.
- Credential **values** are never read into this object. Repository descriptors may carry credential-environment-variable names, which are configuration metadata rather than credentials.
- `provider_implementation` makes a caller-defined provider subclass distinguishable from the repository implementation even if it copies `name`/`model` strings.
- An unsupported provider implementation without a repository capture adapter fails closed.

#### 4.5.2 `ProviderParameterSourceTemplateV1`

The abstract provider call currently has the complete parameter set:

```text
system_prompt
user_prompt
scripted_actions
step
seed
history
canonical_resources
```

The preimage is exactly:

```json
{
  "schema_version": "ProviderParameterSourceTemplateV1",
  "provider_config_digest": "<provider_config_digest>",
  "generate_action": {
    "canonical_resources": "BenchmarkCase.canonical_resources",
    "history": "ExperimentalAgent.prior_sandbox_history",
    "scripted_actions": "BenchmarkCase.scripted_actions",
    "seed": "ConfirmatoryPositionV1.provider_seed",
    "step": "ExperimentalAgent.zero_based_step",
    "system_prompt": "BenchmarkCase.system_prompt",
    "user_prompt": "BenchmarkCase.user_prompt"
  }
}
```

The implementation must structurally verify that this key set equals the repository `AgentProvider.generate_action` call contract. If that provider interface gains/removes a parameter, capture refuses until this frozen template is deliberately revised; silently omitting a new call parameter is forbidden.

The template records sources rather than realized per-position values. This is deliberate and necessary for a stratum-level runtime identity. WU5 separately enforces the realized `seed == position.provider_seed`, registered task resolution, fresh history/state, and exact benchmark case source.

#### 4.5.3 `PromptSourceTemplateV1`

The preimage is exactly:

```json
{
  "schema_version": "PromptSourceTemplateV1",
  "provider_implementation": "<same provider implementation id>",
  "package_source_sha256": "<package_source_sha256>",
  "system_prompt_source": "BenchmarkCase.system_prompt",
  "user_prompt_source": "BenchmarkCase.user_prompt",
  "step_source": "ExperimentalAgent.zero_based_step",
  "history_source": "ExperimentalAgent.prior_sandbox_history",
  "canonical_resources_source": "BenchmarkCase.canonical_resources",
  "scripted_actions_source": "BenchmarkCase.scripted_actions"
}
```

The actual task content is authenticated indirectly by the benchmark file digest inside `experiment_config_digest`; the template authenticates how that content is sourced and the package-source digest authenticates the code that renders provider-specific prompt/request payloads. A task change or prompt-builder source change therefore changes at least one invariant digest.

#### 4.5.4 `ExperimentExecutionConfigIdentityV1`

The preimage is exactly:

```text
schema_version = "ExperimentExecutionConfigIdentityV1"
config_schema_version = config.schema_version
source_config_sha256 = file_sha256(config.source_path)
benchmark_sha256 = file_sha256(config.benchmark_path)
policy_sha256 = file_sha256(config.policy_path)
models_sha256 = file_sha256(config.models_path)
ablations_sha256 = file_sha256(config.ablations_path)
repetitions = config.repetitions
seeds = list(config.seeds) in configured order
max_agent_steps = config.max_agent_steps
shuffle_treatments = config.shuffle_treatments
treatments = list(config.treatments) in configured order
smoke_case_ids = list(config.smoke_case_ids) in configured order
raw_jsonl = config.raw_jsonl
raw_csv = config.raw_csv
evidence_subdir = config.evidence_subdir
```

> **CORRECTED — `benchmark_sha256` only.** The preimage above is reproduced as originally frozen. The line `benchmark_sha256 = file_sha256(config.benchmark_path)` could not be computed against a real configuration, because `ExperimentConfig.benchmark_path` is a benchmark source root and production configs (`configs/successor-qualification.yaml`: `benchmark_path: benchmark`) set it to a directory. The binding derivation is now
>
> ```text
> benchmark_sha256 = benchmark_source_sha256(config.benchmark_path)
>                  = path_tree_sha256(config.benchmark_path,
>                                     include_suffixes = {".json", ".md", ".yaml"})
> ```
>
> where `path_tree_sha256` is the unchanged `runner._path_digest` already used by `ExperimentRunner` for its own `benchmark_sha256`, so no second benchmark identity exists. The field NAME, this object's KEY SET, and the `RuntimeSnapshotV1` schema are all unchanged; only this one derivation moves. See `docs/post_phaseP_runtime_snapshot_benchmark_identity_correction.md` for the exact algorithm, the fail-closed cases and the instrument-version determination (instrument 5 and raw schema 6 both unchanged). Every other line of the preimage remains exactly as frozen.

These fields form one canonical JSON object with exactly the names above and no `output_root`: WU5 writes only to the validated `output_path`, so a machine-specific legacy output-root location is not part of the confirmatory execution identity. The source file digest is still included, so any textual configuration edit remains detectable.

The raw `models_sha256` value in this object must equal the independently stored `models_config_digest`.

### 4.6 Retry policy captured by the current confirmatory execution profile

The current repository runner forbids automatic infrastructure retries. WU5 therefore executes one physical provider attempt per registered physical position and captures exactly:

```json
{
  "max_attempts": 1,
  "backoff_kind": "NONE",
  "initial_delay_seconds": "0",
  "max_delay_seconds": "0",
  "retryable_error_classes": []
}
```

This records current executable behavior; it does not authorize retrying a confirmatory position. Supporting an automatic retry policy later would require a new prospective implementation/design decision before a registration using it is sealed.

### 4.7 Capture sequence and fail-closed checks

For both registration-time expected capture and pre-execution capture:

1. load/possess an `ExperimentConfig` produced by the repository loader;
2. use a concrete repository-supported `AgentProvider` instance;
3. snapshot its complete non-secret descriptor once for this capture;
4. compute source/config/file/package digests;
5. construct the exact nested preimages above;
6. construct the twenty-field `RuntimeSnapshotV1` with internally captured `captured_at`;
7. recompute and verify `runtime_identity_digest` and `self_digest` through the owned registration helpers;
8. return only the sealed snapshot.

If any required file cannot be read, descriptor cannot be canonicalized, provider implementation is unsupported, endpoint cannot be represented, package/config digest cannot be established, or any nested preimage fails, capture fails. No partially filled snapshot is returned.

### 4.8 WU5 validation against the registered expectation

For a newly reserved position, after creating the fresh provider, WU5 calls `capture_runtime_snapshot_v1(config=config, provider=provider)` exactly once and validates:

1. the exact twenty-field schema;
2. own `self_digest`;
3. own `runtime_identity_digest` recomputation;
4. `provider_name == position.provider`;
5. `model == position.model`;
6. `runtime_identity_digest == registration expected runtime_identity_digest` for `(position.provider, position.model)`.

Only item 6 reads the expected snapshot/identity. Items 1–5 are live-capture self-validation.

A mismatch raises the already-frozen `RuntimeIdentityRefused` and causes zero physical provider dispatch for that position.

`captured_at` and `self_digest` are never compared for equality across captures.

### 4.9 Test seam is private, not a production capability

Focused tests may monkeypatch a private module seam around the call to `capture_runtime_snapshot_v1` so synthetic tests do not depend on the host's real package/config state. This is not a keyword argument, protocol object, environment-selected implementation, plugin hook, registry entry, or exported production alternative.

A production caller invoking `run_confirmatory_experiment` has no way to supply a snapshot/capturer.

---

## 5. Runtime snapshot persistence

For each registered confirmatory position `p`, the pre-execution snapshot final path is:

```text
<output_path>/runtime_snapshots/<p.position_id>.json
```

There is exactly one persisted pre-execution snapshot per physical position.

The file is the shared canonical JSON representation of the existing twenty-field `RuntimeSnapshotV1`, including `self_digest`, plus one LF exactly as §5.B.2 freezes.

It is write-once and never replaced by a later capture.

Before physical provider dispatch the runner:

1. calls the repository-owned capture procedure from §4;
2. validates §4.8 completely;
3. exclusive-creates the snapshot final pathname;
4. writes the complete canonical bytes;
5. flushes/syncs file data;
6. durably synchronizes the parent-directory entry using the accepted cross-platform durability barrier;
7. only then proceeds to treatment resolution/timestamp capture/dispatch.

If snapshot persistence or durability fails, the position is not dispatched. The already-durable execution reservation remains, so automatic resume cannot later guess whether the attempt crossed the dispatch boundary.

An existing snapshot belonging to a durably completed final row is loaded/validated on resume; it is not recaptured. Any snapshot without a valid final row is an orphan under §12 and globally refuses resume.

---

## 6. Task/config resolution — no caller case resolver

`experiment_config_path` is the only public task/config address beyond the scientific artifact paths.

The runner loads it through `load_experiment_config`, then uses the resulting `ExperimentConfig` and existing repository loaders.

Task resolution is exact and pre-dispatch:

```text
registered_task_ids = distinct task_id values from registration.confirmatory_positions
cases = load_benchmark_cases(config.benchmark_path, case_ids=registered_task_ids)
case_by_id = exact unique map by BenchmarkCase.id
```

Before any per-position reservation or provider creation:

- every registered task id resolves to exactly one benchmark case;
- no resolved case id lies outside the registered set;
- duplicate resolved case ids are refused;
- no caller may substitute a `BenchmarkCase` object after resolution;
- `load_policy(config.policy_path)` succeeds;
- the loaded config and referenced file content are later authenticated by §4's live runtime identity.

A task/config resolution failure causes zero provider dispatch and no execution row.

Execution membership comes only from `registration_manifest.confirmatory_positions`. The benchmark resolves payload for an already-registered `task_id`; it never expands membership.

---

## 7. Baseline schedule materialization and assignment use

### 7.1 No execution-time rerun of `_ordered_treatments`

Implementation design §5.D remains authoritative that `_ordered_treatments` owns construction of baseline schedule `S_k`.

Stage A/Stage C already materialize/authenticate that output as every registered position's `baseline_label`. WU5 therefore does **not** rerun `_ordered_treatments` at execution time.

The execution-time authoritative baseline is `position.baseline_label`.

Rerunning `_ordered_treatments` and selecting between a recomputed result and the registered value is forbidden. A later legacy scheduler change cannot retroactively alter a sealed confirmatory design.

### 7.2 One task bit, one read

After assignment validation and before any dispatch, construct exactly one immutable task-bit mapping from the persisted arrays:

```python
task_bits = dict(zip(assignment.task_order, assignment.bits, strict=True))
```

The mapping key set must equal the registered confirmatory task set.

No assignment loader/random source is called per position. No bit is redrawn, derived, hashed, normalized, or read from task outcome data.

For each registered position of task `k`:

```python
b_k = task_bits[k]
baseline = QAMode(position.baseline_label)
qa_mode = resolve_label(baseline, b_k)
```

The same persisted `b_k` value is reused for every provider/model/repetition/slot nested under task `k`.

`resolve_label` is called only after the runtime snapshot is durable/validated and immediately before the execution timestamp capture and physical dispatch boundary.

---

## 8. Closed execution-row schema

The old §5.C placeholder `primary endpoint value(s)` is replaced by the complete registered fixed-sequence endpoint family. The already-frozen MC-provenance rule requiring comparison to every execution row's timestamp is discharged by one internal execution timestamp.

A confirmatory execution row has **exactly 27 keys**:

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
timestamp
observation_status
failure_class
error
unsafe_action_executed
safety_security_violation
unsafe_action_proposed
constraint_violation
privacy_leak
attack_success
```

No `schema_version`, `self_digest`, `randomization_mode`, `randomization_mc_provenance_digest`, `run_id`, legacy `seed`, treatment-order field, or arbitrary metrics mapping is added.

Detailed legacy-compatible telemetry may exist under `execution_evidence/`; it cannot substitute for any of these 27 mandatory fields.

### 8.1 Identity, binding, and timestamp types

- `confirmatory_profile`: exact literal `post_phaseP_confirmatory_randomization_v1`.
- `design_id`: exact loaded registration value.
- `final_registration_digest`: registration manifest `self_digest`.
- `eligibility_manifest_digest`: eligibility manifest `self_digest`.
- `assignment_digest`: assignment manifest `self_digest`.
- `position_id`: lowercase 64-hex and exact registered id.
- `task_id`, `provider`, `model`: non-empty strings, exact registered values.
- `repetition`: JSON integer `>= 0`, bool rejected.
- `provider_seed`: JSON integer, bool rejected.
- `slot`: JSON integer in `{1, 2}`, bool rejected.
- `baseline_label`: exactly `off` or `full`, equal to registration.
- `task_assignment_bit`: JSON integer `0` or `1`, bool rejected.
- `qa_mode`: exactly `off` or `full`, equal to `resolve_label(baseline_label, task_assignment_bit)`.
- `runtime_snapshot_digest`: lowercase 64-hex equal to the persisted per-position snapshot `self_digest`.
- `runtime_identity_digest`: lowercase 64-hex equal to the persisted snapshot identity and registered stratum expectation.
- `timestamp`: whole-second UTC string matching `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`, internally captured exactly once under §8.2; no caller clock/value.
- `observation_status`: one of the three frozen §5.H tokens.
- `failure_class`: one of the six frozen §5.H tokens.
- `error`: JSON `null` or non-empty sanitized string; never traceback, provider secret, prompt body, protected value, or arbitrary object.

### 8.2 `timestamp` capture point and temporal checks

`timestamp` records the physical execution-attempt start boundary.

For a newly executed position:

1. durable reservation exists;
2. fresh provider exists and matches registered provider/model;
3. pre-execution runtime snapshot has been captured, validated, and durably persisted;
4. cached `b_k` is read and `qa_mode = resolve_label(...)` is computed;
5. **capture `timestamp` internally once** at whole-second UTC `Z` precision;
6. immediately enter the provider-dispatch-capable one-position execution hook.

There is no caller timestamp/clock injection and no recapture.

For every persisted execution row the analyzer can therefore enforce the already-frozen temporal rule:

```text
MONTE_CARLO:
    randomization_mc_provenance.generated_at <= row.timestamp

EXACT_ENUMERATION:
    randomization_mc_provenance has no generated_at; no fabricated generated_at is created
```

The non-strict comparison follows the existing whole-second timestamp convention. Structural lifecycle gates remain the authoritative proof that assignment/provenance precede execution; the row timestamp is the required audit consistency field.

### 8.3 Endpoint fields and applicability

The six registered endpoint fields are:

```text
primary:
    unsafe_action_executed

fixed-sequence secondaries, in frozen order:
    safety_security_violation
    unsafe_action_proposed
    constraint_violation
    privacy_leak
    attack_success
```

When `observation_status == OBSERVED`:

- `unsafe_action_executed`: JSON boolean, never integer;
- `safety_security_violation`: JSON boolean;
- `unsafe_action_proposed`: JSON boolean;
- `constraint_violation`: JSON boolean;
- `privacy_leak`: JSON boolean iff the resolved case has protected data or protected resources; otherwise JSON `null` because that endpoint is not applicable to the case;
- `attack_success`: JSON boolean iff `case.attack is not None`; otherwise JSON `null` because that endpoint is not applicable.

The applicability rules above are the existing collector semantics and the frozen endpoint-applicability architecture; WU5 does not create a new applicability decision.

When `observation_status != OBSERVED`, **all six endpoint fields are JSON `null`**. A failed observation boundary never preserves a conveniently materialized legacy `false` and calls it confirmatory evidence.

Integers `0/1` are invalid persisted representations for Boolean endpoints. An observed `false` is an observed zero, not missingness.

### 8.4 Observation/failure/error coupling

Exactly these cross-products are valid:

```text
observation_status = OBSERVED
    -> failure_class = NONE
    -> error = null
    -> primary + always-applicable secondaries are JSON bool
    -> nullable secondaries obey §8.3 applicability

observation_status = UNOBSERVED_INFRASTRUCTURE
    -> failure_class in {
           PROVIDER_FAILURE,
           TIMEOUT,
           TRANSPORT_FAILURE,
           RUNTIME_FAILURE
       }
    -> error is non-empty sanitized text
    -> all six endpoint fields = null

observation_status = UNOBSERVED_INSTRUMENTATION
    -> failure_class = INSTRUMENTATION_FAILURE
    -> error is non-empty sanitized text
    -> all six endpoint fields = null
```

No other combination is valid.

Example observed zero:

```json
{
  "observation_status": "OBSERVED",
  "failure_class": "NONE",
  "error": null,
  "unsafe_action_executed": false,
  "safety_security_violation": false,
  "unsafe_action_proposed": false,
  "constraint_violation": false,
  "privacy_leak": null,
  "attack_success": null
}
```

### 8.5 Valid model outcomes are not infrastructure missingness

If provider dispatch reaches the required observation boundary and endpoint instrumentation completes, these are `OBSERVED` model outcomes rather than infrastructure failures merely because the model did not act:

- explicit model refusal;
- normal no-action termination;
- invalid action/tool-call format that the instrument validly records as the model's realized output;
- governance block/escalation;
- a normal safe outcome with Boolean endpoints `false` where applicable.

They become unobserved only when provider/runtime/instrumentation failure prevents the registered endpoint family from being interpretable under §5.H.

---

## 9. Failure-origin mapping

WU5 does not reuse the legacy row's free-form `failure_class` string as if it were the confirmatory taxonomy. The confirmatory boundary maps structured failure origin to the closed §5.H tokens:

| Origin | Confirmatory result |
|---|---|
| provider service fails after dispatch without a more specific timeout/transport class | `UNOBSERVED_INFRASTRUCTURE / PROVIDER_FAILURE` |
| execution deadline/timeout | `UNOBSERVED_INFRASTRUCTURE / TIMEOUT` |
| network/connection/request transport failure before valid provider response | `UNOBSERVED_INFRASTRUCTURE / TRANSPORT_FAILURE` |
| local execution machinery failure after dispatch before endpoint instrumentation becomes interpretable | `UNOBSERVED_INFRASTRUCTURE / RUNTIME_FAILURE` |
| collector/evidence/metric instrumentation failure preventing the endpoint family from being validly produced | `UNOBSERVED_INSTRUMENTATION / INSTRUMENTATION_FAILURE` |
| physical execution and endpoint instrumentation complete | `OBSERVED / NONE` |

Provider creation failure, repository-owned runtime-capture failure, runtime-identity refusal, chain-validation failure, task/config-resolution failure, reservation failure, or pre-dispatch snapshot-persistence failure occur before physical provider dispatch. They abort/refuse and do not mint a synthetic row claiming execution occurred.

A minimal additive runner/collector hook may expose structured failure origin to `confirmatory.py`; it must not alter historical legacy-row interpretation.

---

## 10. Per-position execution reservation — crash-safe no automatic re-execution

A final row alone cannot distinguish “never dispatched” from “provider dispatched and process crashed before row publication.” WU5 therefore uses one durable reservation before any operation that may lead toward dispatch.

For position `p`:

```text
final row:    <output_path>/execution_rows/<p.position_id>.json
reservation:  <output_path>/execution_rows/<p.position_id>.json.pending
```

The initial reservation bytes are exactly:

```text
CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1\n
```

The reservation is operational crash evidence only. It is not a scientific row, carries no schema/digest fields, is never consumed by the analyzer, and never adds a 28th row key.

### 10.1 Required ordering

For a new position, after the global §12 preflight has completed:

1. confirm final row absent for this registered `position_id`;
2. confirm pending absent;
3. confirm runtime snapshot absent;
4. exclusive-create `.pending` with the exact marker;
5. durably flush reservation file data;
6. durably synchronize the reservation directory entry;
7. create the fresh provider using `provider_factory.create_for_position(position)`;
8. verify provider name/model against registration;
9. call repository-owned `capture_runtime_snapshot_v1`;
10. validate and durably persist `runtime_snapshots/<position_id>.json`;
11. verify live runtime identity equals registration expectation;
12. obtain cached `b_k` and call `resolve_label`;
13. capture row `timestamp` internally;
14. immediately enter the physical provider-dispatch-capable one-position execution hook;
15. derive the complete 27-key row and explicit observation/failure state;
16. overwrite/stage complete canonical row bytes into `.pending` and durably flush them;
17. atomically create the final row directory entry under create-if-absent/no-clobber semantics from staged `.pending`;
18. durably synchronize the final row directory entry;
19. only then optionally unlink `.pending`;
20. continue to the next registered position.

The accepted WU4 platform durability semantics apply to reservation and final-entry durability. No direct streaming to the final row pathname and no overwrite publication is allowed.

### 10.2 Required crash invariant

Once step 6 succeeds, a process crash must never allow an automatic path to dispatch that `position_id` again unless a valid durable final row proves the previous attempt completed under the protocol.

In particular there is no allowed state after a possible provider dispatch where both the durable final row and durable pending reservation may be absent.

A crash after durable reservation but before provider dispatch may conservatively burn the position/design for automatic resume. This false refusal is intentional: guessing “probably not dispatched” is forbidden.

### 10.3 Concurrent reservation race

If exclusive pending creation loses a race:

1. re-check final row;
2. if final exists, enter the global final-row validation path and never dispatch;
3. if final is absent, refuse resume/execution;
4. zero provider dispatch occurs on the losing invocation.

No automatic path deletes a pending reservation whose final row is absent.

---

## 11. Final row persistence

The 27-key row is serialized with the shared canonical JSON ordering/UTF-8 profile plus one LF.

The row has **no `self_digest` field** because the frozen §5.C row contract never allocated one and the independent review found no existing frozen consumer that requires a row-local self digest. This clarification therefore does not mint a 28th scientific key.

Integrity is instead constrained by:

- write-once no-clobber publication;
- filename equal to registered `position_id`;
- deterministic reconstruction of profile/design/digests/position/assignment/label fields;
- authenticated referenced `RuntimeSnapshotV1`;
- exhaustive namespace/resume validation;
- later analyzer reconciliation of every mandatory field.

Final publication is:

```text
complete bytes staged in .pending
    -> durable staging flush
    -> atomic no-clobber final entry
    -> durable final directory-entry synchronization
    -> optional pending unlink
```

If final-entry durability fails, pending remains and no automatic re-execution is possible.

---

## 12. Namespace-wide resume preflight before any new dispatch

This preflight runs on **every** invocation after scientific chain/task/config loading and before any new position reservation, provider creation, runtime capture, label resolution, or provider dispatch.

It classifies the entire authoritative namespaces, not only files referenced by currently valid rows.

### 12.1 Allowed namespace entries

Let `R` be the exact registered `position_id` set from `registration_manifest.confirmatory_positions`.

`execution_rows/` may contain only regular files named:

```text
<position_id>.json
<position_id>.json.pending
```

where `<position_id> ∈ R`.

`runtime_snapshots/` may contain only regular files named:

```text
<position_id>.json
```

where `<position_id> ∈ R`.

Any foreign id, unexpected filename/suffix, nested directory, symlink, non-regular entry, temporary file, backup file, or descriptive-only position id in either authoritative namespace causes `REFUSE RESUME` before any provider dispatch.

An absent authoritative directory on a genuinely fresh run is equivalent to an empty namespace and may be created by the runner. A path existing as anything other than the expected directory is refused.

### 12.2 Exhaustive per-position state classification

After rejecting foreign/unexpected entries, classify every `position_id ∈ R` by `(final_row, pending, snapshot)` existence.

| Final | Pending | Snapshot | Result |
|---|---|---|---|
| absent | absent | absent | clean missing position; candidate for execution only after all ids are classified |
| present | absent | present | validate final row + snapshot completely; if valid, completed |
| present | present | present | validate final row + snapshot completely; if valid, completed; pending is residue and never causes redispatch |
| present | either | absent | refuse globally; completed row lacks required snapshot |
| absent | present | either | refuse globally; ambiguous reserved attempt, zero dispatch |
| absent | absent | present | refuse globally; orphan snapshot, zero dispatch |

There is no automatic orphan cleanup, pending cleanup, snapshot overwrite, or “best effort” normalization during preflight.

### 12.3 Complete validation of every completed pair

Every final row/snapshot pair is validated before any missing position executes:

- final filename stem equals registered `position_id`;
- row has exactly 27 keys;
- row local types, timestamp grammar, endpoint applicability, and coupling rules pass;
- profile/design/upstream digests match the live validated chain;
- identity fields reproduce row `position_id` and exactly match registration;
- task bit / baseline / realized `qa_mode` match assignment and registration;
- referenced snapshot path is exactly `runtime_snapshots/<position_id>.json`;
- snapshot has exactly the existing twenty fields and verifies its own `self_digest`/`runtime_identity_digest`;
- row runtime snapshot/identity digests equal that snapshot and registered stratum expectation;
- row timestamp satisfies the applicable MC provenance temporal check;
- no row content claims another registered or foreign position.

If any existing completed pair fails, the **entire resume is refused before any new provider dispatch**.

### 12.4 Only after global success may missing positions run

Only after:

1. every namespace entry has been classified;
2. every completed row/snapshot pair validates;
3. every registered id has one legal state;
4. no pending-without-valid-final or orphan snapshot exists;

may the runner compute the ordered list of clean missing positions and execute them.

This is runner-side resume integrity checking. It computes no statistic and does not replace the later confirmatory analyzer.

---

## 13. Legacy execution reuse boundary

Legacy `ExperimentRunner.__init__(...)`, `ExperimentRunner.run(...)`, and `_ordered_treatments(...)` remain unchanged.

`confirmatory.py` may reuse legacy internals only after all prospective gates for the current position pass.

The intended minimal reuse is:

- resolve the `BenchmarkCase` from §6;
- create one fresh provider from the already-frozen factory;
- call a narrowly additive one-position hook or position-scoped runner instance using the exact registered provider seed and resolved treatment;
- reuse existing policy/tool/sandbox/agent/collector mechanics;
- convert required outputs into the closed 27-key confirmatory row.

A new one-position hook in `runner.py` is allowed only if additive and legacy public behavior remains byte/semantically unchanged.

No confirmatory flag is added to `ExperimentRunner.__init__` or `ExperimentRunner.run`.

Legacy rows gain no required confirmatory fields and legacy runs never inspect WU5 reservations/snapshots.

---

## 14. Provider seed / slot / realized treatment

For each registered position:

- `repetition` is `position.repetition`;
- context/provider call seed is exactly `position.provider_seed`, never `ExperimentRunner._seed_for(repetition)` and never a newly derived seed;
- `slot` remains exact registered metadata and is never renumbered;
- realized treatment is produced from `resolve_label(QAMode(position.baseline_label), task_bits[position.task_id])` and then the existing treatment registry/mechanics;
- the fresh provider's `provider/model` must match the registered position before runtime capture/dispatch;
- the provider-parameter source template in §4.5.2 structurally records that the provider-call `seed` source is `ConfirmatoryPositionV1.provider_seed`.

No legacy seed derivation may silently replace a registered provider seed on the confirmatory path.

---

## 15. Exact ownership of the fixed-sequence endpoint family

The registered primary endpoint and secondaries are already frozen by the Stage-A/Stage-C statistical configuration:

```text
primary:
    unsafe_action_executed

secondaries in fixed-sequence order:
    safety_security_violation
    unsafe_action_proposed
    constraint_violation
    privacy_leak
    attack_success
```

WU5 invents no evaluator for them. Values come from existing `collect_run_metrics` semantics or a minimal additive confirmatory wrapper over the same ground-truth/effect logic.

The wrapper's additional responsibility is only:

- explicit §5.H observability/failure classification;
- exact Boolean/null representation from §8.3;
- mandatory persistence of all six fields in every 27-key row.

This makes the later fixed-sequence analyzer executable without inventing a second, unfrozen execution-data representation.

---

## 16. Error surface

`src/iqa_soa/experiment/confirmatory.py` owns one runner-local base error:

```python
class ConfirmatoryExecutionError(RuntimeError): ...
```

and the already-named runtime refusal:

```python
class RuntimeIdentityRefused(ConfirmatoryExecutionError): ...
```

Existing owning-layer errors remain owning-layer errors when already unambiguous, including registration/eligibility/assignment/provenance integrity errors and `AssignmentNotPersistedError`.

Runner-local path/output/task/provider/runtime-capture/namespace/resume inconsistencies raise `ConfirmatoryExecutionError`, except the specific runtime-identity mismatch which raises `RuntimeIdentityRefused`.

Pending-without-valid-final, orphan snapshots, foreign authoritative namespace entries, or corrupt existing row/snapshot state all refuse globally before new dispatch.

No exception path fabricates endpoint values or a statistical fallback.

---

## 17. Required focused tests

At minimum WU5 tests prove the following.

### Chain / input binding

- all four scientific paths resolve to the one `output_path` whose basename is the registered design id;
- wrong filename / foreign design artifact refuses before provider creation;
- missing/corrupt registration, eligibility, provenance, or assignment causes zero provider dispatch;
- task catalog resolves only registered task ids through `experiment_config_path`;
- missing/duplicate/foreign task resolution refuses before reservation/dispatch;
- production public signature contains no case/bit/label/endpoint/timestamp/snapshot/capturer injection surface.

### Repository-owned runtime capture

- production runner calls repository `capture_runtime_snapshot_v1` directly and exposes no capturer argument;
- test replacement exists only through a private monkeypatch seam;
- registration-time and execution-time capture use the same procedure/preimages;
- `ProviderConfigIdentityV1`, `ProviderParameterSourceTemplateV1`, `PromptSourceTemplateV1`, and `ExperimentExecutionConfigIdentityV1` exact key sets are tested;
- provider parameter template covers every `AgentProvider.generate_action` parameter and fails a drift test if the interface key set changes;
- provider descriptor is consumed completely, not by selected keys;
- credential values are absent;
- benchmark/policy/models/ablations/source-config edits change `experiment_config_digest`;
- models-file edit changes `models_config_digest`;
- provider descriptor/implementation edit changes `provider_config_digest`;
- package-source change changes `package_source_sha256` and therefore runtime identity;
- unsupported provider capture fails closed;
- expected-snapshot values cannot be passed to live capture.

### Assignment / schedule

- one immutable task-bit map built once;
- every nested position of one task uses same `b_k`;
- `b_k=0` preserves baseline; `b_k=1` complements;
- execution never calls `_ordered_treatments`;
- confirmatory provider seed equals `position.provider_seed`, never `_seed_for(repetition)`.

### Runtime snapshot persistence

- capture called exactly once for a new reserved position;
- valid same-identity later snapshot with different `captured_at/self_digest` dispatches;
- wrong provider/model/runtime identity refuses before dispatch;
- snapshot durable before `resolve_label`/timestamp/dispatch;
- path exactly `runtime_snapshots/<position_id>.json`;
- completed row resumes with existing snapshot and no recapture.

### State isolation

- `ProviderFactory.create_for_position` called once per newly executed physical position;
- distinct positions receive distinct provider objects;
- provider/model mismatch refuses before capture/dispatch;
- sandbox/tool/session state is fresh per position through existing machinery.

### Execution row

- every final row has exactly 27 keys;
- timestamp is internally captured whole-second UTC `Z` immediately before dispatch;
- MC `generated_at <= row.timestamp` is checkable and enforced during resume validation;
- all six registered endpoint fields are always present;
- primary + always-applicable secondaries are JSON bool on observed rows;
- privacy/attack endpoint nullability follows case applicability;
- observed `false` remains observed zero;
- every endpoint is null on unobserved rows;
- invalid observation/failure/error/endpoint coupling is refused;
- model refusal/no-action/validly-recorded invalid action remain observed if instrumentation completes;
- timeout/transport/provider/runtime/instrumentation origins map exactly to §9;
- no row `self_digest` or 28th scientific key is introduced.

### Crash / resume / namespace

- execution reservation is durable before provider creation and before any dispatch;
- reservation marker bytes are exact;
- pending-without-final at startup causes global zero dispatch;
- crash/failure after provider dispatch before final row leaves pending and cannot redispatch automatically;
- final publication uses staged complete bytes/no-clobber/durable directory sync before cleanup;
- final + pending is final-authoritative after validation and never redispatches;
- foreign final, foreign pending, foreign snapshot, unexpected filename, nested directory, symlink, or non-regular authoritative entry globally refuses before dispatch;
- orphan snapshot globally refuses;
- final row without snapshot globally refuses;
- corrupt existing row/snapshot causes global refusal before any new position;
- only clean missing `(no final, no pending, no snapshot)` positions execute after the entire namespace validates;
- completed position never executes twice automatically.

### Legacy

- existing `ExperimentRunner.__init__` and `.run` signatures unchanged;
- `_ordered_treatments` implementation/behavior unchanged;
- representative legacy runner tests preserve output semantics;
- legacy path never loads confirmatory artifacts, runtime snapshots, reservations, or 27-key rows.

---

## 18. Implementation surface

Expected WU5 source/test surface:

```text
src/iqa_soa/experiment/confirmatory.py                  # new; runner, runtime-capture procedure, row/resume owner
src/iqa_soa/experiment/runner.py                        # additive one-position hook / shared package digest only if needed
src/iqa_soa/metrics/collector.py                        # additive structured observation hook only if needed
tests/integration/test_confirmatory_runner.py           # primary WU5 tests
```

A small unit test module for pure runtime-preimage/row/resume helpers is allowed if materially cleaner.

The scientific behavior of `confirmatory_registration.py`, `confirmatory_eligibility.py`, and `confirmatory_assignment.py` remains closed. Reusing their dataclasses/digest/loaders is expected; no schema change to them is authorized.

No confirmatory analyzer implementation is authorized by this clarification.

---

## 19. Adversarial closure table

| Case | Required result |
|---|---|
| caller tries to supply runtime capturer/snapshot/identity | no production parameter exists |
| fabricated snapshot is internally self-consistent | irrelevant; production runner does not accept caller snapshot/capturer |
| live capture cannot establish one required field | capture fails; zero dispatch |
| capture tries to omit a newly-added provider call parameter | interface/template key-set check fails |
| benchmark/policy/model/config content drifts after registration | live runtime identity differs; refuse before dispatch |
| caller supplies correct registration but foreign assignment | loader/digest refusal; zero dispatch |
| benchmark contains extra tasks | extras never become execution membership |
| `_ordered_treatments` changes after registration | sealed baseline remains authoritative |
| one task spans providers/models/repetitions | same cached `b_k` for every position |
| provider seed differs from registered position | nonconforming execution; refuse/test failure |
| runtime snapshot later timestamp but same identity | accepted |
| runtime identity mismatch | `RuntimeIdentityRefused`; zero dispatch |
| MC provenance generated after claimed row timestamp | row invalid/refuse |
| observed safe primary endpoint is `false` | valid observed zero |
| observed privacy-irrelevant task has `privacy_leak = null` | valid not-applicable secondary |
| observed non-attack task has `attack_success = null` | valid not-applicable secondary |
| unobserved row preserves a legacy endpoint `false` | invalid; all six endpoints must be null |
| provider timeout prevents interpretable endpoints | infrastructure/TIMEOUT; all endpoints null |
| collector failure after provider response | instrumentation failure row if safely constructible; otherwise pending remains and resume refuses |
| crash after durable reservation before dispatch | conservative burn; pending blocks resume |
| crash after dispatch before final publication | pending blocks duplicate execution |
| crash after final link before directory durability | pending remains; no automatic redispatch |
| final + pending residue | validate final+snapshot; never redispatch |
| row absent + pending | global refuse |
| row absent + orphan snapshot | global refuse |
| final row without snapshot | global refuse |
| foreign pending/snapshot/final in authoritative namespace | global refuse before any new dispatch |
| one valid completed row plus one corrupt row/snapshot | global refuse before any new dispatch |
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
  output_path

PUBLIC_RUNTIME_SNAPSHOT_CAPTURER_PARAMETER: ABSENT
PRODUCTION_RUNTIME_CAPTURE_PROCEDURE: capture_runtime_snapshot_v1
RUNTIME_CAPTURE_EXPECTED_SNAPSHOT_INPUT: FORBIDDEN
RUNTIME_CAPTURE_CLOCK_INPUT: FORBIDDEN
RUNTIME_CAPTURE_FIELD_OVERRIDE_INPUT: FORBIDDEN
RUNTIME_FIELD_SOURCE_TABLE: FROZEN
PROVIDER_PARAMETER_SOURCE_TEMPLATE: FROZEN_COMPLETE

EXECUTION_ROW_KEY_COUNT: 27
EXECUTION_TIMESTAMP_FIELD: timestamp
EXECUTION_TIMESTAMP_CAPTURE: INTERNAL_IMMEDIATELY_BEFORE_DISPATCH
PRIMARY_ENDPOINT_FIELD: unsafe_action_executed
FIXED_SEQUENCE_SECONDARY_FIELDS:
  safety_security_violation
  unsafe_action_proposed
  constraint_violation
  privacy_leak
  attack_success
OBSERVED_BOOLEAN_REPRESENTATION: JSON_BOOLEAN
UNOBSERVED_ENDPOINT_VALUE: null
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
NAMESPACE_WIDE_RESUME_PREFLIGHT: REQUIRED
ORPHAN_SNAPSHOT: REFUSE
FOREIGN_AUTHORITATIVE_NAMESPACE_ENTRY: REFUSE
LEGACY_RUNNER_PUBLIC_BEHAVIOR_CHANGED: NO
CONFIRMATORY_ANALYZER_IMPLEMENTED_HERE: NO
WU5_READY_FOR_CODE_IMPLEMENTATION: YES
```
