# Post-Phase-P successor provider selection and qualification-protocol authorization

**Record kind:** human prospective decision and scope authorization
**Candidate:** `prospective-candidate-i5-m1-b76f40da2`
**Candidate status at entry:** `FROZEN_NOT_YET_QUALIFIED`
**Base commit:** `d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c`
**Discharges:** the provider/model selection and qualification-protocol blocker
raised by the preceding `REAL_EXECUTION_GATE` gate, and nothing else.

---

## 0. Boundary declaration

This record is the **human** half of a decision the frozen candidate freeze
record already demanded of it. `candidates/prospective-candidate-i5-m1-b76f40da2/freeze-record.json`
states its own `next_decision`:

> A separate human decision on real provider/model eligibility, registration,
> randomization, qualification and confirmatory execution. Freeze confers none of
> them.

This record supplies the **provider/model selection** part of that decision and
authorizes the engineering that selection makes possible. It supplies none of
the rest. Registration, randomization, qualification execution and confirmatory
execution remain undecided and unauthorized.

**Phase P is untouched.** Phase P remains `UNQUALIFIED`, `HOLD`,
`SCHEDULE_COMPLETE_VERDICT_HOLD`. `BEN-003` remains historical and unrepaired,
its cell `MODEL_PROTOCOL_INVALID`, its matrix `MATRIX_INVALID`, its attribution
`MODEL_PROTOCOL_FAILURE`. No realized Phase-P row was read, re-run, re-scored,
reclassified or used in any way while producing this record or the work it
authorizes, and no Phase-P outcome contributed to the selection below.

---

## 1. The decision

### `HUMAN_PROSPECTIVE_PROVIDER_SELECTION: AUTHORIZED`

**Selected proposed strata — exactly two, no more, no fewer:**

| # | `provider_slot` | `model` | `provider_type` | endpoint family | `protocol` | `tool_contract_policy` |
|---|---|---|---|---|---|---|
| 1 | `qwen_native_none` | `qwen3.5:27b` | `openai_compatible` | local Ollama OpenAI-compatible API | `native_tools` | `none` |
| 2 | `mistral_native_trailing_user` | `mistral-small3.2:24b` | `openai_compatible` | local Ollama OpenAI-compatible API | `native_tools` | `trailing_user` |

Both are selected **together**. Neither may be selected alone, no third
provider or model may be added, and neither model may be replaced by a newer
one.

### `SELECTION_BASIS: PROSPECTIVE_LINEAGE_CONTINUITY`

These two strata are the repository's long-standing real-model qualification
slots, carried through the predecessor qualification lineage: qualified in Phase
C/D, used by Phase F against rc1, by Phase I against rc2 and by Phase L-B
against rc3. Continuity of that lineage is the **entire** stated ground.

### The selection was NOT based on

- any Phase-P outcome, and no Phase-P result was consulted;
- Phase-P qualification status;
- any benchmark result, historical exposure rate or observed performance;
- model ranking or any inference of superiority;
- API-key presence, `OLLAMA_HOST` presence, or any environment-variable state;
- current availability or convenience;
- any seed;
- any expected result or confirmatory outcome.

### What the selection establishes, and what it does not

The selection establishes **`PROPOSED_STRATUM`** status for each of the two
strata. That is its whole effect.

It does **not** assign either stratum `CONFIRMATORY_ELIGIBLE`, and it does
**not** assign either stratum `PROVIDER_QUALIFIED`. Actual eligibility remains a
later PR-10 **evidence and verification** question, exactly as
`docs/post_phaseP_confirmatory_randomization_design_decision.md` section 12
already froze it, and
`CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED` continues to hold for every provider
and runtime configured in this repository.

**Actual PR-10 eligibility: `EVIDENCE_DEPENDENT`.**

---

## 2. Scope authorization

### Authorized by this record

| # | Scope | Status |
|---|---|---|
| 1 | A successor-owned provider configuration | `SUCCESSOR_PROVIDER_CONFIG_CREATION: AUTHORIZED` |
| 2 | A successor real-model qualification protocol | `SUCCESSOR_QUALIFICATION_PROTOCOL_CREATION: AUTHORIZED` |
| 3 | Successor frozen execution-input bindings | `AUTHORIZED` |
| 4 | Successor provider/runtime eligibility-preflight machinery | `AUTHORIZED` |
| 5 | Offline PR-10 evidence/argument artifacts, where they can be honestly established without provider contact | `AUTHORIZED` |
| 6 | Focused tests and validators for the above | `AUTHORIZED` |
| 7 | This decision/authorization record | `AUTHORIZED` |
| 8 | A successor-owned `ExperimentConfig` | `SUCCESSOR_EXPERIMENT_CONFIG_CREATION: AUTHORIZED` |
| 9 | Freezing that `ExperimentConfig` into the execution-input bindings | `SUCCESSOR_EXPERIMENT_CONFIG_FREEZE: AUTHORIZED` |
| 10 | One prospective successor seed derivation | `SUCCESSOR_PROSPECTIVE_SEED_DERIVATION: AUTHORIZED` |

### Withheld by this record

| Scope | Status |
|---|---|
| `PROVIDER_CONTACT` | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| Endpoint probes (including metadata-only probes) | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| `MODEL_INFERENCE` | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| `QUALIFICATION_EXECUTION` | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| `CONFIRMATORY_EXECUTION` | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| Stage-C final confirmatory registration | `NOT_AUTHORIZED_BY_THIS_RECORD` |
| Production randomization / assignment realization | `NOT_AUTHORIZED_BY_THIS_RECORD` |

Production randomization stays withheld and is **not** the same act as seed
derivation. Deriving a reproducible seed triple fixes which cells exist; it
realizes no assignment, draws no random bits and selects no position. Section 5C
authorizes the first and nothing more.

---

## 3. What was created under this authorization

| Artifact | Role |
|---|---|
| `configs/successor-models.yaml` | The successor-owned provider config. Exactly the two selected strata. |
| `configs/successor-qualification.yaml` | The successor-owned `ExperimentConfig`. Binds the successor models config, the successor output root and the derived seed triple. |
| `scripts/successor_derive_seeds.py` | The successor prospective seed derivation. Recomputes the whole search from the base commit alone. |
| `docs/successor_prospective_seed_derivation.json` | The seed derivation record: algorithm, base, domain, every candidate, every rejection, accepted seeds, derivation digest. |
| `scripts/successor_qualification_protocol.py` | The frozen successor qualification protocol. |
| `scripts/run_successor_qualification.py` | The driver. Its execution path is refused by construction. |
| `scripts/successor_eligibility_preflight.py` | The offline PR-10 eligibility argument machinery. |
| `docs/successor_frozen_execution_inputs.json` | The frozen execution-input bindings. |
| `docs/successor_real_model_qualification_plan.md` | The successor real-model qualification plan. |
| `docs/successor_pr10_offline_eligibility_argument.json` | The offline PR-10 argument for both proposed strata. |
| `tests/unit/test_successor_provider_selection.py` | Selection, config and identity tests. |
| `tests/integration/test_successor_qualification_protocol.py` | Protocol, isolation, PR-10 and Stage-A boundary tests. |

**Nothing historical was modified.** `configs/phaseP-models.yaml` and every other
phase configuration are byte-identical. No benchmark byte changed, and no
model-visible input changed.

---

## 4. Credential naming

The successor credential environment variable is **`SUCCESSOR_OLLAMA_API_KEY`**.

No historical phase credential name is reused. `PHASEP_OLLAMA_API_KEY`,
`PHASEL_OLLAMA_API_KEY`, `PHASEI_OLLAMA_API_KEY`, `PHASEF_OLLAMA_API_KEY` and
`OPENAI_API_KEY` are each explicitly refused by the protocol, so a historical
credential can never silently satisfy a successor precondition.

The name is checked by **name only**. Its value is never read, never printed and
never written to any artifact by any code authorized here. The config authorizes
no endpoint contact, and loading it performs none.

---

## 5. Model digest and runtime identity policy

The expected local-model digests and the expected runtime version are **carried
forward prospectively** as runtime identity pins:

| model | expected digest |
|---|---|
| `qwen3.5:27b` | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` |
| `mistral-small3.2:24b` | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` |

Expected runtime version: `0.32.13`.

**They are justified from committed NON-OUTCOME history.** Each is stated
identically by four committed protocol and plan records of the established
qualification lineage — `scripts/phaseL_protocol.py`,
`docs/phaseD_qualification_report.md`,
`docs/phaseI_rc2_real_model_requalification_plan.md` and
`docs/phaseL_rc3_real_model_requalification_plan_v2.md`. A model digest is a
property of the local model artifact the lineage qualified, not of any phase's
outcome. No realized Phase-P row was consulted to obtain them, and none is
needed.

**They are pins, not instructions.** A later live-runtime disagreement is an
`ENVIRONMENT_HOLD`, never a repair. The protocol never pulls, updates, retags or
replaces a model. `successor_qualification_protocol.verify_runtime_identity`
fixes that rule offline, now, before any probe is authorized to exist; a missing
observation is an `ENVIRONMENT_HOLD` too, so "the preflight did not look" can
never read as "the preflight found agreement".

---

## 5A. `RUNTIME_VERSION_RESOLUTION: RESTORE_FROZEN_RUNTIME`

The execution environment reported a live Ollama runtime of **`0.33.0`**. The
frozen required runtime is **`0.32.13`**. That disagreement is an
**`ENVIRONMENT_HOLD`**, and this section records the human resolution of it.

| Decision | Value |
|---|---|
| `RUNTIME_VERSION_RESOLUTION` | `RESTORE_FROZEN_RUNTIME` |
| `EXPECTED_RUNTIME_VERSION` | `0.32.13` |
| `RUNTIME_REPIN` | `NOT_AUTHORIZED` |
| `RUNTIME_VERSION_EQUIVALENCE_EXCEPTION` | `NOT_AUTHORIZED` |
| `RUNTIME_RESTORE_REQUIRED` | `YES` |
| `ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION` | `0.33.0` (recorded, refused, never accepted) |

**The resolution is to restore the execution environment to `0.32.13` before any
real runtime capture.** It is not to move the pin.

The reason is not fastidiousness. The runtime version is carried forward on
exactly the same prospective footing as the model digests: it is a property of
the local artifact the established qualification lineage qualified, taken from
committed non-outcome records, and fixed **before** any successor observation
existed. Repinning it to whatever the environment happens to be running would
let environment drift silently redefine the qualified instrument — the pin would
then record the environment rather than constrain it, and every later claim that
the successor ran on the qualified runtime would be unfalsifiable.

Accordingly, and bindingly:

- the protocol pin is **not** changed to `0.33.0`;
- version equality is **not** weakened — `RUNTIME_VERSION_COMPARISON` is
  `EXACT_STRING_EQUALITY`, `ACCEPTED_RUNTIME_VERSIONS` has exactly one member,
  and a non-string observation is refused rather than coerced;
- **no** equivalence exception, allowlist, range or prefix match is created;
- `0.33.0` is recorded **only** so the hold is citable. It is not in the accepted
  set, no code path compares against it, and `check_runtime_version_policy`
  fails if it ever equals the pin.

An `ENVIRONMENT_HOLD` authorizes **no** remedy. The preflight must fail closed
and must never automatically downgrade the runtime, update Ollama, repin the
protocol, pull a model, replace a model or retag a model. The expected model
digests are unchanged:

| model | expected digest |
|---|---|
| `qwen3.5:27b` | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` |
| `mistral-small3.2:24b` | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` |

**No runtime was probed to write this section.** `0.33.0` is a human-reported
environment observation carried into this record; nothing authorized here
contacted a runtime, and nothing may.

---

## 5B. `SUCCESSOR_EXPERIMENT_CONFIG_CREATION: AUTHORIZED`

The successor candidate had a provider config and a protocol but no
`ExperimentConfig` of its own. This section authorizes creating and freezing
one, and exactly one:

`configs/successor-qualification.yaml`

The filename follows the repository's existing convention for this artifact —
`<scope>-qualification.yaml`, as `configs/phaseD-diagnostic.yaml`,
`configs/phaseF-qualification.yaml`, `configs/phaseI-qualification.yaml`,
`configs/phaseL-qualification.yaml` and `configs/phaseP-qualification.yaml`
already do — so no more specific successor-owned filename is required.

| Decision | Value |
|---|---|
| `SUCCESSOR_EXPERIMENT_CONFIG_CREATION` | `AUTHORIZED` |
| `SUCCESSOR_EXPERIMENT_CONFIG_FREEZE` | `AUTHORIZED` |

It is an `ExperimentConfig` in the **existing** schema
(`iqa_soa.experiment.runner.load_experiment_config`, `schema_version: 1`,
fifteen keys). No parallel configuration system is introduced, no loader is
modified and no validation is weakened. It binds:

| Binding | Value |
|---|---|
| Candidate | `prospective-candidate-i5-m1-b76f40da2` |
| Models config | `configs/successor-models.yaml` |
| Treatment | `off` — the qualification treatment; `full`, `partial`, `ablation` and `confirmatory` are out of scope |
| Output root | `results/prospective-candidate-i5-m1-b76f40da2-qualification/raw` |
| Instrument version | `5` |
| Raw schema version | `6` |
| Native tool adapter | `native-tools-adapter-3` |
| Tool argument contract | `tool-arguments-1` |
| Infrastructure retry limit | `0` |

The instrument, schema, adapter and tool-contract pins are properties of the
instrument and the `ExperimentConfig` schema rejects unknown fields, so they are
pinned in `scripts/successor_qualification_protocol.py`,
`docs/successor_frozen_execution_inputs.json` and
`docs/successor_real_model_qualification_plan.md`. The config is digest-bound to
that protocol, so the pins cannot drift away from it.

**It reuses no Phase-P namespace**, assigns nothing confirmatory, and realizes no
randomization: `shuffle_treatments` is `false` and no seed exists.

### The one deliberately empty field

Seed derivation remains a **withheld** scope (section 2). The config therefore
carries `seeds: []` and `repetitions: 0`, and the repository's own loader
**refuses** it as written.

That is the intended consequence and it is a safety property, not an oversight:
the successor `ExperimentConfig` is frozen, complete in every field this record
has settled, and **structurally non-executable** until a separately authorized
seed derivation supplies the one field nobody has been authorized to supply.
Writing a placeholder seed to make the file load would have fabricated a
scientific input — the exact failure this freeze exists to prevent. An honest
gap is preferable to a fabricated constant, here as in section 2.

### Not an execution authorization

Creating and freezing this config authorizes **no** execution of any kind. It
does not authorize confirmatory execution, and it is not a confirmatory design:
it is suitable for the successor **real qualification** protocol only.

---

## 5C. `SUCCESSOR_PROSPECTIVE_SEED_DERIVATION: AUTHORIZED`

| Decision | Value |
|---|---|
| `SUCCESSOR_PROSPECTIVE_SEED_DERIVATION` | `AUTHORIZED` |
| `SEED_DERIVATION_ALGORITHM` | `successor-qualification-seed-derivation-1` |
| `SEED_COUNT` | `3` |
| `SEEDS_DERIVED_BEFORE_ANY_SUCCESSOR_QUALIFICATION_OUTCOME` | `YES` |
| `HISTORICAL_SEED_VALUE_REUSE` | `NO` |
| `OUTCOME_INFORMED_SEED_SELECTION` | `NO` |
| Canonical derivation base | `d5b5537a84cc8b57bca2195c3b3bb4cfdb857e5c` |
| Domain separator | `IQA-SOA\|post-phase-p\|prospective-candidate-i5-m1-b76f40da2\|qa-off-real-model-qualification` |
| Production randomization | still `NOT_AUTHORIZED` |

### Why this is now authorized

Section 5B froze a successor `ExperimentConfig` whose `seeds` field was
deliberately empty, which made the config **unloadable**. That was the honest
intermediate state, but it is the wrong terminal one: the next authorized
lifecycle step requires this config to become executable once runtime identity
and execution authorization are satisfied, and a configuration that cannot load
would be a **second, accidental** barrier standing alongside the intended one.
The only barrier to a successor execution must be the withheld human
authorization.

### What is reused, and what is not

The **method** is reused from the historical `phase-p-seed-derivation-1`
algorithm (`scripts/phaseP_derive_seeds.py`):

```
material  = <canonical base SHA> + "|" + <domain separator>
          + "|seed-" + ordinal + "|counter-" + counter
digest    = SHA256(UTF-8(material))
candidate = int.from_bytes(digest[:4], "big") & 0x7fffffff
```

For each ordinal 1..3, starting at `counter = 0`, accept the first candidate
that is non-zero, is not a forbidden historical or reserved seed, and does not
duplicate a seed already accepted for a lower ordinal; otherwise record the
rejection and increment the counter.

**No historical seed VALUE is reused.** The Phase-P triple
(`1197050110`, `1904689056`, `1133353488`) and the Phase-L triple
(`929260329`, `1281385038`, `978843421`) are both `CONSUMED_BY_A_FORMAL_EXECUTION`
and are FORBIDDEN inputs to this search, along with `1729`, `2718`, `3141`,
`5772` and `8119`. Method reuse is not value reuse: two derivations sharing a
formula but differing in base commit and domain separator cannot collide by
construction.

### Why no outcome could have informed it

The derivation base is the successor candidate freeze commit. It **predates**
every successor qualification act, and zero successor result rows exist at it.
The inputs are a commit SHA, a fixed string, an ordinal and a counter — no model
output, no result row, no exposure rate, no ranking, no environment state and no
credential participates.

### The forbidden set is proved, not asserted

`scripts/successor_derive_seeds.py` enumerates the **git-tracked** files under
`configs/`, `docs/`, `benchmark/` and `schemas/` and reports every seed they
record. The derivation **fails closed** if that scan finds a seed the reserved
set does not cover, so a seed introduced by a phase this work did not anticipate
breaks the derivation rather than silently passing it.

**No results namespace is read.** `results/` is named only in
`EXCLUDED_SCAN_ROOTS`, and the exclusion is asserted rather than assumed:
`tracked_files` raises if the enumeration ever returns a path under it. This is
narrower than the Phase-P scan by deliberate choice — the successor boundary
forbids reading historical evidence rows — and it costs the proof nothing,
because every seed any phase has run on is declared in that phase's committed
config and derivation artifact, both of which **are** scanned. The enumeration
is `git ls-files`, never a filesystem walk, so no untracked local evidence
directory can influence the record.

The scan found **11** committed seeds and the reserved set covers all of them.

### The result

Three seeds, each accepted at `counter = 0`, zero rejections, no collision:

| ordinal | seed | `sha256(material)` |
|---|---|---|
| 1 | `583010984` | `22c00aa8dfb773b705f73e7be44db5503a845916eeaa78191c641f72eaf245db` |
| 2 | `1723431918` | `66b97beee9158b7d65d4b2e8b47c37e1476b68ed77c0eab8c051f6f47eef35b3` |
| 3 | `1639806953` | `e1bd77e926102bb4f8af6cfd3138e687311cad5ae812da6ceeff867c392bfc69` |

The prospective matrix is therefore 17 tasks x 2 arms x 3 seeds = **102 cells**.
`docs/successor_prospective_seed_derivation.json` records the algorithm, the
base, the domain separator, every candidate examined with its material and
digest, every rejection (there are none), the accepted triple and the derivation
digest. The protocol does not re-spell the seeds: it recomputes them from the
derivation module, so it cannot claim a seed the algorithm does not produce.

### Still not an execution authorization

The `ExperimentConfig` now loads. **Nothing else changed.** Provider contact,
endpoint probes, model inference, qualification execution and confirmatory
execution all remain `NOT_AUTHORIZED`, and the runtime restore of section 5A
remains required before any capture.

---

## 6. What is still blocked, and why

`STAGE_A = BLOCKED_PENDING_RUNTIME_SNAPSHOT`.

A valid Stage-A `RegistrationDraftV1` must satisfy V10′: `proposed_runtime_configuration`
holds one complete, digest-verifying `RuntimeSnapshotV1` **per proposed
stratum**, an exact element-wise cover of `proposed_strata` (eligibility
clarification section 12.3, RC-1…RC-5). There are two proposed strata and zero
captured snapshots.

The snapshot cannot be manufactured offline. Implementation design section 5.I.5
makes the registration-expected snapshot a **capture point**, and section 5.I.3
places live host facts and the provider endpoint inside its
`environment_fingerprint` preimage. `successor_eligibility_preflight.accept_captured_runtime_snapshot`
therefore refuses **every** snapshot offered to it, including a structurally
perfect one built by the frozen dataclass: shape is not provenance.

This is an acceptable terminal state for this record. Forcing Stage A
prematurely was never the goal. The goal was to remove the provider-selection,
configuration and protocol blocker so that the next action is a **narrowly
defined runtime preflight** rather than another methodology decision — and that
is what the next action now is.

---

## 7. One thing this record deliberately does not do

It does not record a Stage-B disposition for either stratum.

If the four predicates were assessed today they would all be `UNASSESSED`, and
the frozen derivation (eligibility clarification section 8.2 step 2) would yield
`DESCRIPTIVE_ONLY_UNASSESSED`. The offline PR-10 artifact computes exactly that
and labels it a **projection**.

Recording it as an actual disposition would be destructive. Section 15 forbids
promoting a recorded `DESCRIPTIVE_ONLY_*` stratum to `CONFIRMATORY_ELIGIBLE` in
place, and refused case 48 states the consequence: the stratum could then only be
rescued by abandoning the `design_id` and recreating it. Writing down today's
unavoidable ignorance as a disposition would permanently exclude both selected
strata from the confirmatory matrix on the strength of evidence nobody has yet
been authorized to gather.

Stage B is entered later, **once**, with real evidence.

---

## 8. Standing status after this record

| Property | Value |
|---|---|
| Candidate | `prospective-candidate-i5-m1-b76f40da2` |
| Candidate status | `FROZEN_NOT_YET_QUALIFIED` |
| Qualification status | `NOT_YET_QUALIFIED` |
| Selected proposed strata | 2 |
| `CONFIRMATORY_ELIGIBLE` strata | 0 |
| `PROVIDER_QUALIFIED` strata | 0 |
| Provider contacted | no |
| Endpoint probed | no |
| Model inference performed | no |
| Rows written | 0 |
| Runtime snapshots captured | 0 |
| Runtime snapshots synthesized | 0 |
| Randomization realized | no |
| Seeds derived | 3 (prospectively, before any successor outcome) |
| Historical seed values reused | 0 |
| Planned cells | 102 (17 tasks x 2 arms x 3 seeds) |
| Successor `ExperimentConfig` | frozen, digest-bound, non-executable |
| Expected runtime version | `0.32.13` |
| Runtime repin | `NOT_AUTHORIZED` |
| Runtime restore required | yes |
| Runtime probed by this record | no |
| Phase P | `UNQUALIFIED` / `HOLD` / `SCHEDULE_COMPLETE_VERDICT_HOLD` |
| BEN-003 | historical, unrepaired |
| Benchmark bytes | unchanged |
| Model-visible input | unchanged |

### Standing refusals — unchanged by anything in this record

| Scope | Status |
|---|---|
| `PROVIDER_CONTACT` | `NOT_AUTHORIZED` |
| `MODEL_INFERENCE` | `NOT_AUTHORIZED` |
| `QUALIFICATION_EXECUTION` | `NOT_AUTHORIZED` |
| `CONFIRMATORY_EXECUTION` | `NOT_AUTHORIZED` |
| `RUNTIME_REPIN` | `NOT_AUTHORIZED` |

Sections 5A and 5B add a runtime-version **resolution** and an
`ExperimentConfig` **authorization**. Neither adds an execution authorization,
and neither may be read as one.

**Next real action:** restore the execution environment to Ollama `0.32.13`, then
a separately authorized runtime preflight that, per proposed stratum, verifies
the model digest, runtime version, tool contract policy and protocol against the
pins above, and captures one real `RuntimeSnapshotV1`. It requires provider
contact and therefore a new human record. It requires no further methodology
decision.
