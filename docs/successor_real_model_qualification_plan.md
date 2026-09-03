# Successor real-model qualification plan

**Candidate:** `prospective-candidate-i5-m1-b76f40da2`
**Candidate status at entry:** `FROZEN_NOT_YET_QUALIFIED`
**Protocol:** `successor-qualification-protocol-1` (`scripts/successor_qualification_protocol.py`)
**Authorized by:** `docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md`
**Base commit:** `d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c`

> **THIS PLAN AUTHORIZES NOTHING.** It states what a later, separately
> authorized qualification would be bound to. Provider contact, endpoint probes,
> model inference, qualification execution and confirmatory execution are all
> unauthorized at the time of writing, and no part of this plan may be read as
> permission to perform any of them.

---

## 1. What is being qualified, and what is not

The object under qualification is the **successor candidate**: the frozen
17-task benchmark selection scored under the **successor** profile, on
**instrument 5 / raw schema 6**, at **QA OFF**.

This is a qualification, not a measurement of governance effect. It reports no
QA treatment effect, computes no model comparison and publishes no model
ranking. `full`, `partial`, `ablation` and `confirmatory` treatments are all out
of scope and the protocol names them as such.

Qualification is also **not** confirmatory eligibility. A stratum that qualifies
here is still `UNASSESSED` for PR-10 purposes until Stage B assesses it against
the four frozen predicates with real evidence.

---

## 2. Historical isolation

Rows written under instrument 5 / raw schema 6 may **never** be pooled, merged,
averaged or compared with rows written under instrument 4 / raw schema 5. The
historical protocol's pin to instrument 4 / raw schema 5 remains deliberately
incompatible and is **not** repaired.

Accordingly:

- the successor qualification has its own results namespace,
  `results/prospective-candidate-i5-m1-b76f40da2-qualification`, and refuses
  every historical namespace by name;
- it has its own provider config, `configs/successor-models.yaml`, and its own
  `ExperimentConfig`, `configs/successor-qualification.yaml`, and never loads a
  phase config at runtime;
- it has its own credential name, `SUCCESSOR_OLLAMA_API_KEY`;
- it scores under the `successor` profile
  (`successor-scoring-vocabulary-1`) and never under `rc4-historical`.

Phase P remains `UNQUALIFIED` / `HOLD` / `SCHEDULE_COMPLETE_VERDICT_HOLD`, and
`BEN-003` remains historical and unrepaired. Retrospective entry of a
successor-only outcome into the historical profile is **impossible**, not merely
forbidden: the historical profile is a closed four-member tuple that contains
neither successor-only outcome, so the meaning is inexpressible there.

---

## 3. Bound identities and digests

| Binding | Value |
|---|---|
| Candidate | `prospective-candidate-i5-m1-b76f40da2` |
| Freeze record digest | `c099346d2e1dadaa7da8fbca2cfb3ebbf7b7d3ba4d95083827bb9daee3f339cc` |
| Qualification contract digest | `46b0893b8259d3bb1fed8810fe624d2a3393d5227bc72ea31ee395872dcdadb6` |
| Benchmark version | `pilot-v7-rc4` |
| Benchmark case-bytes digest | `76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea` |
| Canonical exposure digest | `23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092` |
| Instrument version | `5` |
| Raw schema version | `6` |
| Native tool adapter | `native-tools-adapter-3` |
| Tool argument contract | `tool-arguments-1` |
| Scoring profile | `successor` / `successor-scoring-vocabulary-1` |
| Task count | 17 |
| QA mode | `off` |
| Treatments | `["off"]` |
| Infrastructure retry limit | `0` |
| Models config | `configs/successor-models.yaml` |
| Experiment config | `configs/successor-qualification.yaml` |
| Output root | `results/prospective-candidate-i5-m1-b76f40da2-qualification/raw` |

**Change dispositions carried forward:** C1 `IMPLEMENTED`, C2 `IMPLEMENTED`,
C3 `ALREADY_COMPLETE` (unchanged), C4a `IMPLEMENTED`, C4b `NOT_ADOPTED`
(absent), C5 `NO_CHANGE` (unchanged), C6 `WITHDRAWN` (absent).

C1 adds `UNSUPPORTED_COMPLETION_CLAIM` (PI-018, trace-conditioned, diagnostic,
not exposure, not a near miss). C2 adds `NONCANONICAL_RESOURCE_SELECTION`
(PRIV-017, structural, not exposure, not a near miss). C4a evaluates
`LEGITIMATE_SINK_APPLICABLE` over every task. No canonical exposure definition
changes, and the canonical exposure digest above is what proves it.

---

## 4. The two proposed strata

| arm | provider slot | model | expected digest | `tool_contract_policy` |
|---|---|---|---|---|
| `qwen` | `qwen_native_none` | `qwen3.5:27b` | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` | `none` |
| `mistral` | `mistral_native_trailing_user` | `mistral-small3.2:24b` | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` | `trailing_user` |

Arm order is `("qwen", "mistral")`, carried forward from the established lineage
so a successor schedule position stays comparable to the lineage it continues.
Expected runtime version is `0.32.13`; expected protocol is `native_tools`;
expected endpoint family is the local Ollama OpenAI-compatible API.

The `tool_contract_policy` difference between the two slots is **already-qualified
instrument behaviour**, not an experimental factor. A qwen-vs-mistral difference
must therefore never be read causally.

Selection made these **proposed strata**. It did not make either one
`CONFIRMATORY_ELIGIBLE` or `PROVIDER_QUALIFIED`.

---

## 4A. The successor `ExperimentConfig`

`configs/successor-qualification.yaml` is the successor-owned `ExperimentConfig`,
authorized by section 5B of the governing record. It is an `ExperimentConfig` in
the **existing** repository schema — `iqa_soa.experiment.runner.load_experiment_config`,
`schema_version: 1`, the fifteen keys that loader requires — and follows the
`<scope>-qualification.yaml` filename convention the qualification lineage
already uses. No parallel configuration system exists, no loader is modified and
no validation is weakened.

| Field | Value | Why |
|---|---|---|
| `models_path` | `configs/successor-models.yaml` | Successor-owned. A phase config can never satisfy a successor precondition. |
| `output_root` | `results/prospective-candidate-i5-m1-b76f40da2-qualification/raw` | Successor-owned. No Phase-P namespace is reused. |
| `treatments` | `["off"]` | The qualification treatment. `full`, `partial`, `ablation` and `confirmatory` are out of scope. |
| `shuffle_treatments` | `false` | No production randomization is authorized. |
| `benchmark_path` | `benchmark` | Root only, so the runner can digest it; the case set comes from the frozen manifest. |
| `policy_path` | `configs/policies/default.xml` | Carried forward from the lineage, unchanged. |
| `max_agent_steps` | `20` | The lineage value. Not tuned for this candidate. |
| `raw_jsonl` / `raw_csv` | `successor-runs.jsonl` / `successor-runs.csv` | The protocol's own `RAW_RECORD_NAME` and `RAW_CSV_NAME`, so the two cannot name different files. |
| `seeds` | `[583010984, 1723431918, 1639806953]` | Prospectively derived. See section 5. |
| `repetitions` | `3` | Describes the seed count. |

The instrument pins — instrument 5, raw schema 6, `native-tools-adapter-3`,
`tool-arguments-1` — are properties of the instrument, and the `ExperimentConfig`
schema rejects unknown fields, so they live in the protocol, in
`docs/successor_frozen_execution_inputs.json` and in section 3 above. The config
is digest-bound to the protocol by the frozen execution-input record, so the pins
cannot drift away from it.

**The config loads cleanly**, and that is deliberate. A qualification config
that could not load would be a second, accidental barrier standing beside the
intended one; the only barrier to a successor execution must be the withheld
human authorization.
`successor_qualification_protocol.check_experiment_config` proves the loader
accepts it AND that the loaded object resolves to the successor models config,
the successor output root, the QA-OFF treatment and the derived seed triple.

---

## 5. The seeds, and where they came from

`SEED_SELECTION_STATUS: DERIVED_PROSPECTIVELY_BEFORE_ANY_SUCCESSOR_OUTCOME`.

| Property | Value |
|---|---|
| Algorithm | `successor-qualification-seed-derivation-1` |
| Method reused from | `phase-p-seed-derivation-1` (`scripts/phaseP_derive_seeds.py`) |
| Method reuse is value reuse | **no** |
| Canonical base | `d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c` |
| Domain separator | `IQA-SOA\|post-phase-p\|prospective-candidate-i5-m1-b76f40da2\|qa-off-real-model-qualification` |
| Seeds | `583010984`, `1723431918`, `1639806953` |
| Rejections | 0 (each ordinal accepted at `counter = 0`) |
| Historical collisions | none |
| Record | `docs/successor_prospective_seed_derivation.json` |

The derivation is a pure function of a commit SHA that predates every successor
qualification act, a fixed domain separator, an ordinal and a counter. No model
output, result row, exposure rate, ranking, environment state or credential
participates, and no seed was chosen by hand: the rejection rule is part of the
algorithm and every candidate examined is recorded.

Every previously committed or reserved seed is FORBIDDEN — the Phase-P triple
and the Phase-L triple are both `CONSUMED_BY_A_FORMAL_EXECUTION` — and the
forbidden set is **proved** complete against a `git ls-files` scan of the tracked
`configs/`, `docs/`, `benchmark/` and `schemas/` trees. No results namespace is
enumerated or read; the exclusion is asserted, not assumed.

The matrix is therefore 17 tasks × 2 arms × 3 seeds = **102 cells**, and
`planned_cells` is `102`.

Deriving seeds is **not** realizing a randomization. Production randomization and
assignment realization remain unauthorized.

---

## 6. Execution preconditions, in order

An authorized execution would have to clear all of the following, in this order.
Every step is now IMPLEMENTED in `scripts/run_successor_qualification.py` and
covered by `tests/integration/test_successor_qualification_execution.py`. None of
it is authorized, and none of it is reachable: step 1 refuses before step 2 is
read, so the driver is executable but locked.

1. **Authorization.** `successor_qualification_protocol.require_execution_authorization()`.
   Checked **before** the CLI flag and the environment gate, so a caller who
   supplies both still gets a refusal. A human record is the authorization; the
   gates are only how an already-granted authorization is exercised.
2. **Human gates.** `--execute-real-model` **and**
   `IQA_SOA_SUCCESSOR_QUALIFICATION_HUMAN_GATE=AUTHORIZED`. Both required, and
   both inert while step 1 refuses.
3. **Canonical scientific input binding.** `--config` and `--manifest` are
   ASSERTIONS, not choices: each is proven canonical by PATH and by the SHA-256
   the frozen-input record accepted. There is no noncanonical execution mode.
4. **Offline preflight.** Authorization state, candidate freeze digests,
   instrument pins, provider config, ExperimentConfig, selected strata, seed
   derivation, runtime-version policy, scoring profile, historical isolation,
   frozen inputs, absence of any pre-existing result artifact, the full
   successor scope validator, and the confirmatory-boundary check. Any failure
   is a `PREFLIGHT_STOP`.
5. **Canonical runtime evidence.** The committed preflight evidence at
   `results/prospective-candidate-i5-m1-b76f40da2-runtime-preflight/` is loaded,
   its capture commit `9f7a8b5` bound, and every `RuntimeSnapshotV1` self-digest
   and identity digest RECOMPUTED from the persisted invariant fields. It is
   IMMUTABLE OBSERVED EVIDENCE: no timestamp, self-digest or provenance field is
   ever rewritten, and evidence the driver cannot validate is a stop rather than
   something to recapture.
6. **Schedule and provenance truth.** The frozen 102-cell schedule is built from
   the frozen manifest's own task order, and the summary this run would persist
   is required to describe the schedule it would execute.
7. **Namespace ABSENCE.** The ENTIRE results namespace must not exist. Checked
   before any provider object is constructed, so a second invocation costs zero
   contact and zero inference.
8. **Credential presence, by name only.** `SUCCESSOR_OLLAMA_API_KEY`. Absent is a
   `CREDENTIAL_STOP`. The value is never read into a message, never printed and
   never written to an artifact.
9. **Immediate pre-inference environment check.** Per stratum, BEFORE the first
   model request: verify model, model digest, runtime version, tool contract
   policy and protocol against the pins, then freshly call the
   repository-owned `RuntimeSnapshotV1` capture once and require its
   `runtime_identity_digest` to equal the canonical preflight identity —
   `3c49ab56…` for qwen, `5ff8e092…` for mistral. `captured_at` and
   `self_digest` naturally differ; the identity must not. A PRIOR observation is
   never accepted in place of a fresh one. Any disagreement — **or any missing
   observation** — is an `ENVIRONMENT_HOLD` with **zero cells executed**.
   The runtime version is compared by **exact string equality** against the
   single accepted version `0.32.13`; a non-string observation is refused rather
   than coerced. The environment previously reported `0.33.0`, which is an
   `ENVIRONMENT_HOLD` whose recorded human resolution is
   `RESTORE_FROZEN_RUNTIME` (governing record section 5A). The check fails
   closed and never downgrades the runtime, updates Ollama, repins the
   protocol, pulls a model, replaces a model or retags a model.
10. **The frozen schedule.** Arm-major → task-major → seed-minor, over the 102
   cells fixed by section 5, QA OFF only, owned by the stop controller so a stop
   cannot be stepped past. Zero retries: a provider or model failure is a
   recorded outcome, never a reason to rerun. An interruption writes the frozen
   fail-closed partial manifest and is never resumed.

Exit codes: `0` OK, `1` verdict hold, `2` preflight stop, `3` schedule stopped,
`4` credential stop, `5` environment hold, `6` gate closed. A pre-existing
namespace exits `3`: the write-once precondition is a schedule stop, reported
distinctly from a generic preflight failure so a second invocation is legible as
what it is.

---

## 7. Artifact namespace and persistence

Namespace: `results/prospective-candidate-i5-m1-b76f40da2-qualification`.

**It does not exist and nothing here creates it.** An authorized driver creates
it only after every gate and precondition passes. Persistence is WRITE-ONCE BY
ABSENCE: the ENTIRE namespace must be absent, checked before any provider object
is constructed, so a second invocation costs zero contact and zero inference. A
pre-existing namespace — even an empty one, even one holding an interrupted
run's partial manifest — is a `PROTOCOL_DEVIATION`, never something to append
to, resume or repair.

| Artifact | Name |
|---|---|
| Raw rows | `successor-runs.jsonl` |
| Run manifest | `successor-run-manifest.json` |
| Partial manifest | `successor-partial-manifest.json` |
| Analysis | `successor-analysis.json` |

Persistence is fail-closed: written exactly once, to a path that must not
already exist. There is no overwrite mode, no resume mode, no merge mode and no
partial-row repair.

The protocol refuses `results/phaseP-rc4-qualification` and every earlier
lineage namespace by name, with a distinct message, because "this is not the
successor namespace" and "this is frozen historical evidence you must never
write" are different mistakes.

---

## 8. What qualification does **not** decide

Confirmatory eligibility. PR-10 is a separate, per-stratum, evidence-dependent
verification against four frozen predicates — PR-4 `POSITION_STATE_ISOLATION`,
PR-5 `INFRASTRUCTURE_SYMMETRY`, PR-7 `TOTAL_OBSERVATION` and
`RUNTIME_CONFIGURATION_FROZEN`.

The offline half of that argument is recorded in
`docs/successor_pr10_offline_eligibility_argument.json`. Today all four
predicates are `PENDING` for both strata, every blocking fact is a live runtime
observation, and `CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED` stands.

`STAGE_A = BLOCKED_PENDING_RUNTIME_SNAPSHOT`.

---

## 9. Next real action

The runtime preflight named here as the next action HAS HAPPENED. It was
authorized by
`docs/post_phaseP_successor_runtime_preflight_contact_authorization.md`, ran once
at canonical main `9f7a8b5` against a restored Ollama `0.32.13`, and its evidence
is committed and immutable at
`results/prospective-candidate-i5-m1-b76f40da2-runtime-preflight/`. Both frozen
strata presented their pinned model identities and a real `RuntimeSnapshotV1`.
That authorization is now SPENT: it was one-shot, and it refuses a second
contact by its own rules.

The execution path is likewise no longer outstanding — it is implemented,
reviewed and tested, and it is locked.

**The next real action is a NEW HUMAN RECORD authorizing qualification
execution.** Nothing else is missing: the schedule, the environment check, the
persistence contract and the analyzer are all in place and all offline-tested.
No further methodology decision is required — which is precisely what this plan
and its authorization were written to achieve. Until that record exists,
`QUALIFICATION_EXECUTION_AUTHORIZED` stays `False`, and supplying the CLI flag
and the environment gate together still yields a refusal.
