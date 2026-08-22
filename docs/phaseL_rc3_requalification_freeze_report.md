# Phase L-A — pilot-v7-rc3 real-model QA-OFF requalification: protocol freeze report

**ZERO MODEL INFERENCE WAS PERFORMED IN THIS PHASE.**
No provider was contacted. No Ollama endpoint was probed. No `/api/chat`,
`/api/generate` or OpenAI-compatible completion request was issued. No cloud
provider was used. No QA FULL arm exists. No 420-run execution, no
preregistration v4, no pilot-v7 FINAL, and no confirmatory experiment.

**pilot-v7-rc3 REMAINS UNQUALIFIED.** This phase authorizes no inference.

---

## 0. Outcome in one paragraph

Phase L-A set out to freeze the execution protocol, configs, driver, analyzer,
frozen seeds, machine-enforced stop semantics and synthetic tests for a
17 × 2 × 3 = 102-cell QA-OFF requalification of pilot-v7-rc3. It did not
complete that freeze. While designing the Phase-K.2 fault-provenance integration
required by section 10 of the phase brief, the design surfaced an **unresolved
harness defect**: the K.2 observed-fault provenance contract cannot be satisfied
from any artifact the canonical instrument persists for a QA-OFF cell. Because
Phase L is QA-OFF-only, the contract's fail-closed rule would invalidate every
BUD-016 and FAULT-004 cell and force the terminal verdict to HOLD
**deterministically, before a single token is generated**. Section 15 of the
brief requires design finalization to stop on exactly this discovery rather than
repairing the scientific instrument inside an execution phase. Finalization
therefore stopped. The status of this phase is `HOLD_PHASE_L_PROTOCOL`.

The work that is *independent* of the defect was completed in full and is
delivered here: the three prospective seeds are derived, the matrix and stop
semantics are verified at harness level, and the defect is captured as a
committed, reproducible, offline probe plus a regression-pinned test suite.

---

## 1. Canonical start

| Item | Value |
| --- | --- |
| Canonical starting SHA | `beafa5d170659997790e1c3e79086ea05548c094` |
| `HEAD` == `main` == `origin/main` | yes, verified before branching |
| Working tree at start | clean |
| Branch created | `phase-l/rc3-requalification-protocol-freeze` |
| `main` modified | no |

Canonical state verified:

- Phase K / K.1 / K.2 are merged (`beafa5d`, PR #7).
- `benchmark/pilot-v7-rc3/` exists with manifest, provenance,
  qualification-contract, AUDIT and freeze-record.
- rc3 `release_status` is `release-candidate`, **not** qualified.
- No `benchmark/pilot-v7` or `benchmark/pilot-v7-final` namespace exists.
- No preregistration v4 exists; `docs/` carries only v1 and v3, both unchanged
  and neither extended to rc3.
- Phase I remains `HOLD_POST_FREEZE_DEFECT`; its Qwen arm is pre-discovery
  diagnostic evidence and its Mistral arm is post-stop diagnostic continuation.
- **No Phase-I row is used as qualification evidence anywhere in this phase.**

---

## 2. Scientific purpose (unchanged, and still the intent)

The future Phase-L-B execution would answer only: *is pilot-v7-rc3 empirically
reachable and scientifically usable under QA OFF with the two qualified local
real-model providers?* That is benchmark qualification. It is not an estimate of
QA effectiveness, not QA OFF vs QA FULL, not a treatment-effect experiment, not
confirmatory evidence, and not the 420-run study.

Planned matrix: 17 rc3 tasks × 2 real-model arms × 3 new prospectively frozen
seeds × QA OFF only = **102 cells**. No retries, no replacement cells, no reruns,
no adaptive additions, no exploratory extra cells.

---

## 3. The defect that stopped finalization

### 3.1 What Phase K.2 requires

`scripts/qualification_harness.py` fixes a prospective raw-row contract. Any cell
that observed a sandbox fault must carry four fields:

```
observed_fault_tool
observed_fault_resource
observed_fault_mode
observed_fault_provenance
```

`FAULT_PROVENANCE_CONTRACT` states exactly where each must come from, and
`RUNTIME_FAULT_PROVENANCE_SOURCES` closes the set of admissible sources to four:

```
gateway_outcome.executed_action
gateway_outcome.proposed_action
sandbox.operation_log
evidence.tool_call
```

`DECLARED_FAULT_PROVENANCE_SOURCES` explicitly forbids deriving them from the
benchmark declaration, because an observation manufactured from the declaration
it is about to be compared against proves nothing. `match_scripted_fault` fails
closed when the fields are missing, and `classify_row` then returns
`UNEXPECTED_SANDBOX_FAILURE`, whose frozen disposition is
`CELL_INVALID_AND_HOLD`.

This is correct design. The defect is not in the contract.

### 3.2 What the instrument actually persists for a QA-OFF cell

`Treatment.detailed_evidence` (`src/iqa_soa/experiment/treatments.py:43`) is:

```python
return bool(self.enabled_guards.get("evidence", False)) and self.qa_mode not in {
    QAMode.OFF
}
```

Under QA OFF this is **unconditionally `False`**, regardless of the evidence
guard. The evidence record therefore never receives the detailed block, so it
carries no `tool_result`, no `proposed_action` and no `executed_action`. The
persisted event has exactly these keys:

```
action_id, error, evidence_id, executed, experiment_id, final_decision,
qa_mode, resource, run_id, sequence, success, task_id, timestamp, tool
```

The other three admitted sources are not persisted at all:

- `SandboxState.operation_log` reaches disk only inside
  `final_state_fingerprint`, an irreversible SHA-256
  (`src/iqa_soa/experiment/runner.py:876`). It cannot be read back.
- `AgentRun.outcomes` is local to `ExperimentRunner._run_one` and is never
  serialized, so no `GatewayOutcome` shape survives the run.
- The raw row carries no `observed_fault_*` field.

Consequently **`observed_fault_mode` and `observed_fault_provenance` are
unreachable** from anything a Phase-L driver could read. `observed_fault_tool`
and `observed_fault_resource` happen to be recoverable from the base evidence
event, but three of four required fields must hold, and two do not.

### 3.3 FAULT-004 is worse: the fault is not merely unproved, it is invisible

`ToolRegistry._fault_result` returns a `malformed_response` as **success**, with
the sentinel payload `<<<MALFORMED_SIMULATED_RESPONSE>>>` and no error string.
Under QA OFF the output is never written to the trace. Running FAULT-004 twice
through the canonical runner — once as frozen, once with its declared faults
stripped — produces **byte-identical persisted evidence events**:

```json
{"action_id": "inventory-lookup-fault", "error": null, "executed": true,
 "final_decision": "ALLOW", "qa_mode": "off",
 "resource": "inventory-api/sku-4471", "sequence": 1, "success": true,
 "task_id": "FAULT-004", "tool": "api.call"}
```

The sentinel appears in neither trace. The *only* differentiator anywhere in the
persisted artifacts is the row's `fault_triggered` flag — and
`iqa_soa.metrics.collector._fault_triggered` computes it as
`tool_result.metadata["fault_mode"] == case.fault.type`, a comparison **against
the benchmark declaration**. That is precisely the circular source K.2 names in
`DECLARED_FAULT_PROVENANCE_SOURCES` and refuses. So even a
contract-violating reconstruction is unavailable for FAULT-004; there is nothing
to reconstruct from.

For BUD-016 a driver could in principle reverse-look-up the mode from the
deterministic error string `"simulated tool timeout"`, but that derives the
observation from `FAULT_MODE_SIGNATURE` — a table, not the sandbox's own stamp —
which is the same circularity in a thinner disguise.

### 3.4 Measured consequence, before any inference

Reproduced by `scripts/phaseL_fault_provenance_reachability_probe.py`, which runs
the **real** `ExperimentRunner` on the **real** frozen rc3 cases in the **real**
QA-OFF treatment, substituting `DeterministicStubProvider` (which replays each
case's own `scripted_actions`) for the model. No inference occurs, and the fault
path is reached by construction, so the result is a property of the instrument
rather than of any model's behaviour.

| Task | row `failure_class` | row `fault_triggered` | Harness class | Disposition |
| --- | --- | --- | --- | --- |
| BUD-016 | `tool_timeout` | `None` | `UNEXPECTED_SANDBOX_FAILURE` | `CELL_INVALID_AND_HOLD` |
| FAULT-004 | `None` | `True` | `UNEXPECTED_SANDBOX_FAILURE` | `CELL_INVALID_AND_HOLD` |

Refusal reason in both cases: all four provenance fields missing from the
returned row.

Projected onto the planned matrix, and cross-checked against how the predecessor
constructs actually behaved in the committed Phase-I evidence (BUD-013's injected
timeout fired in **6/6** cells; FAULT-003 reached its fault path in **5/6**):

- up to **6 BUD-016 cells** invalidated and held;
- up to **6 FAULT-004 cells** invalidated and held;
- up to **12 of 102 cells** invalidated with `hold_reasons` non-empty, so
  `ScheduleResult.terminal_status` is `SCHEDULE_COMPLETE_VERDICT_HOLD` and the
  exit code is 1.

**A perfectly executed Phase-L-B could not qualify rc3.** The HOLD is
predetermined by the instrument, not by the models.

### 3.5 Why Phase K did not catch this

`check_observed_fault_provenance_is_runtime_derived` in
`scripts/validate_pilot_v7_rc3.py` proves the contract satisfiable by driving
`ToolRegistry` **directly, in-process**, and reading `state.operation_log` from
live memory. That is a valid proof that the contract is *well-formed*. It is not
a proof that the telemetry is *reachable* from what a driver receives. Phase K
validated the contract against a data structure no qualification driver can ever
hold.

### 3.6 Why it cannot be repaired inside Phase L-A

Three repair paths exist, and all three are out of scope for a protocol-freeze
phase:

1. **Persist the provenance** — stamp the four fields in
   `src/iqa_soa/experiment/runner.py` from `agent_run.outcomes` /
   `state.operation_log`. This is the correct fix, and it is *blocked here*:
   `check_historical_immutability` in `scripts/validate_pilot_v7_rc3.py` pins the
   `src/iqa_soa` tree digest to
   `1825ca11de6723c10fa557d641b4c3585b20c2f9a1c634e9247d46821a53c4d3` in the rc3
   freeze-record. Any byte changed under `src/iqa_soa/` fails rc3 validation and
   moves a frozen artifact. It would also touch `RAW_SCHEMA_VERSION` /
   `PILOT_RAW_FIELDS_V3` and the instrument boundary, none of which a
   requalification phase may decide unilaterally.
2. **Relax the K.2 matcher or the disposition map** — forbidden by sections 10
   and 11 of the brief, and it would restore exactly the laundering K.2 was
   written to prevent.
3. **Enable detailed evidence under QA OFF** — structurally impossible, since
   `detailed_evidence` returns `False` whenever `qa_mode is OFF`, and enabling
   the evidence guard would change the treatment and therefore the science.

The defect belongs to the instrument and must be repaired, reviewed and re-frozen
on its own terms before a Phase-L execution protocol can be frozen at all.

---

## 4. What was deliberately NOT created

Section 15 requires design finalization to stop. Freezing an execution protocol
that provably cannot produce a qualifiable run would be incoherent: section 16's
frozen hash record would attest a broken protocol, and a `READY` status would
invite the human execution gate to be opened over it. The following section-6
artifacts were therefore **not** created, and their absence is machine-checked by
`tests/integration/test_phaseL_requalification.py::test_no_phase_l_execution_protocol_was_frozen`:

- `docs/phaseL_rc3_real_model_requalification_plan.md` (+ `.sha256`)
- `configs/phaseL-qualification.yaml`
- `configs/phaseL-models.yaml`
- `scripts/run_phaseL_requalification.py`
- `scripts/analyze_phaseL_requalification.py`

No frozen hash record over Phase-L execution inputs was produced, for the same
reason: there are no Phase-L execution inputs to freeze.

---

## 5. Work completed and delivered (defect-independent)

### 5.1 Three new prospective seeds

Generated deterministically from the canonical Phase-L-A starting SHA **before
any inference**, so the choice is reproducible from the commit alone and cannot
depend on a model result. Implemented in `scripts/phaseL_seed_derivation.py`;
recorded in `docs/phaseL_rc3_prospective_seed_derivation.json`.

```
material = "beafa5d170659997790e1c3e79086ea05548c094"
         + "|phase-l|pilot-v7-rc3|qa-off-requalification|seed-" + str(i)
digest   = SHA256(UTF-8 material)
seed     = int.from_bytes(digest[:4], "big") & 0x7fffffff
```

| i | SHA-256 of material | first 4 bytes | seed |
| --- | --- | --- | --- |
| 1 | `37636329148c950509a23fc05a1da5e698068eb7f6fdfc21e1d314d625b00908` | `37636329` | **929260329** |
| 2 | `cc60624ed0fc5a241f60e20306c34f10691065307fd2cc0cdbeb4df400f0df07` | `cc60624e` | **1281385038** |
| 3 | `ba57f71d3d91df82ea45de709f8372403679c107d4827726963a38cb86df863b` | `ba57f71d` | **978843421** |

Collision checks, all clean and none self-repaired:

- no derived seed is `0`;
- no derived seed duplicates another Phase-L seed;
- no derived seed equals any historical qualification seed. The historical set
  checked against is `{1729, 2718, 3141, 5772, 8119}`, taken from every committed
  experiment configuration and every recorded result manifest in the repository.
  In particular the Phase-F / Phase-I triple `(1729, 2718, 3141)` is **not**
  reused.

The collision policy is to STOP and report, never to choose an alternative ad
hoc; substituting a nicer-looking number would reintroduce the investigator
degree of freedom the derivation exists to remove.

### 5.2 Matrix and stop semantics, verified at harness level

Verified against `scripts/qualification_harness.py`, the real frozen rc3
manifest and the three new seeds. This is verification of the mechanism, not a
freeze of a protocol.

- The matrix composes to **exactly 102 cells**, arm-major / task-major /
  seed-minor, all with `qa_mode = off` and the rc3 manifest SHA-256.
- Every cell binds the full identity set: `task_id`, `seed`, `model`,
  `model_digest`, `qa_mode`, `benchmark_manifest_sha256`, `run_key`.
- All 102 `run_key` values are unique, and the two arms' keys differ even where
  task and seed coincide.
- A wrong value in any identity field, and a missing value in any identity
  field, both stop immediately as `FROZEN_ARTIFACT_MISMATCH`.
- Duplicate and out-of-order cells stop immediately as `PROTOCOL_DEVIATION`.
- **The Phase-I failure pattern is recreated synthetically**: a defect in the
  final cell of arm 1 stops the schedule and arm 2 never starts.
- A stopped schedule preserves every completed row, and the partial manifest
  records the stop cell, stop class, reason, preserved row ids and the full list
  of cells not started, with exit code 3.
- An invalidated cell cannot enter a pristine denominator: the terminal status
  becomes `SCHEDULE_COMPLETE_VERDICT_HOLD` with exit code 1.
- The closed taxonomy and its dispositions are unchanged and were not reopened;
  `multi_call_overflow` remains model-side.

### 5.3 The defect, captured reproducibly

- `scripts/phaseL_fault_provenance_reachability_probe.py` — committed, offline,
  runs in about a second, exits `4` on the HOLD finding, and emits a structured
  JSON record with `--json`.
- `tests/integration/test_phaseL_requalification.py` — pins the finding as a
  regression. If the instrument is repaired, these tests fail and whoever
  repaired it must update them deliberately. They must never be relaxed to make
  the phase pass.
- A counterfactual test shows a row carrying *genuine* runtime provenance is
  accepted by the harness, which is what makes this a **reachability** defect
  rather than a contract defect.

---

## 6. Items from the brief, and their disposition

| § | Requirement | Disposition |
| --- | --- | --- |
| 4 | Model / runtime pins | Not frozen into a Phase-L config. The intended pins are unchanged from the qualified values and recorded in §7 below. No Ollama probe was performed. |
| 5 | Three new prospective seeds | **Done.** §5.1. |
| 6 | Versioned Phase-L artifacts | **Deliberately withheld.** §4. |
| 7 | Frozen 102-cell schedule | **Verified at harness level**, not frozen into a driver. §5.2. |
| 8 | Machine-enforced human execution gate | **Not implemented**, because no driver was written. The design is recorded in §7 below. `IQA_SOA_PHASE_L_HUMAN_GATE` was never set; `--execute-real-model` was never invoked. |
| 9 | Provider attempt preservation | Design recorded; not implemented. The canonical runner already pins `infrastructure_retry_limit=0` and refuses any other value. |
| 10 | Fault provenance integration | **BLOCKED — this is the defect.** §3. |
| 11 | Failure taxonomy | Reused unchanged; verified not reopened. §5.2. |
| 12 | Automatic stop semantics | **Verified**, including the cross-arm case. §5.2. |
| 13 | Qualification scoring | No verdict computed; no cells were run. No threshold was invented, widened or read from Phase-I results. |
| 14 | Analyzer / driver consistency | Partially verified: the identity, schedule-completeness, duplicate, invalidation and taxonomy checks pass. The fault-provenance field of the shared schema **cannot** be satisfied, which is the defect. |
| 15 | Historical immutability | **Held.** §9. |
| 16 | Frozen hash record | Not produced; there are no Phase-L execution inputs to freeze. §4. |
| 17 | Offline validation | **Done.** §10. |
| 18 | Fresh-checkout validation | **Done.** §11. |

---

## 7. Designs recorded but not frozen

These are stated so the reviewer has the full intended protocol, and so a future
Phase L-A′ does not have to re-derive them. **None of them is implemented or
frozen in this branch.**

**Model and provider pins.** Unchanged from the already-qualified local slots:

| Arm | Model | Digest | Protocol | `tool_contract_policy` |
| --- | --- | --- | --- | --- |
| qwen | `qwen3.5:27b` | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` | `native_tools` | `none` |
| mistral | `mistral-small3.2:24b` | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` | `native_tools` | `trailing_user` |

Runtime pin: Ollama `0.32.13`. Any difference in model identity, digest, runtime
version, tool-contract policy or protocol is an `ENVIRONMENT_HOLD` and is never
repaired by the phase; no model is ever pulled, updated, retagged or replaced.

**Human execution gate.** The driver must refuse real-model execution by default
and require BOTH the CLI flag `--execute-real-model` AND the environment variable
`IQA_SOA_PHASE_L_HUMAN_GATE=AUTHORIZED`. Without both it must exit non-zero
*before* any provider request, any Ollama request, and any environment probe that
could trigger inference. Metadata-only probing may occur only after both gates
are present, immediately before execution.

**Cell identity and `run_key`.** Each cell binds schedule index, arm, `task_id`,
seed, model, model digest, `qa_mode=off` and the rc3 manifest SHA-256.
`run_key = SHA256(index|arm|task_id|seed|model|digest|qa_mode|manifest)[:24]`,
stamped from the frozen `Cell` before the cell executes and required to be
exactly equal. Note that the canonical runner emits neither `model_digest` nor
`run_key`, so the driver must stamp both from the frozen cell; both are frozen
inputs rather than runtime observations, so this is legitimate.

**Schedule ownership.** `StopController` must own advancement. The driver may not
keep an independent loop. This has an unresolved engineering consequence worth
flagging for the reviewer: `ExperimentRunner.run()` owns its own
case × repetition loop and derives the seed as `config.seeds[repetition]`, so a
per-cell driver must either construct a per-cell configuration or drive a
per-cell entry point that does not currently exist as public API.

---

## 8. Frozen artifact hashes recorded (inputs read, not a protocol freeze)

Raw working-tree bytes, canonical LF checkout, per `docs/hash_basis_policy.md`.
These attest the inputs this phase *read*; they are not a Phase-L execution
freeze.

| File | SHA-256 |
| --- | --- |
| `benchmark/pilot-v7-rc3/manifest.json` | `2e3ff2157d8d61d5aed5386910e80f4ef6a1a845bf560378c4f9a2c94d899b0d` |
| `benchmark/pilot-v7-rc3/provenance.json` | `078a73c59e8ec4d1964d5079233159542af4b70f4ef908128836308a3d4c658a` |
| `benchmark/pilot-v7-rc3/qualification-contract.json` | `6d3fbcf8bb0213c4619e1a268502cc9b669146bf5f677bfd421b58ee1d26e7ca` |
| `benchmark/pilot-v7-rc3/AUDIT.md` | `65b6eae0fc67a21a1ec76d7c5ce7374909a2111c23b09efbd7e5533be9d3476b` |
| `configs/policies/default.xml` | `256a8205fa944f74e12642925298260848fae5ebbb320f695ce0a234ea9f63e5` |
| `src/iqa_soa` (tree digest) | `1825ca11de6723c10fa557d641b4c3585b20c2f9a1c634e9247d46821a53c4d3` |

Every one matches the value pinned in `benchmark/pilot-v7-rc3/freeze-record.json`,
confirming no frozen input moved during this phase.

---

## 9. Historical immutability

Phase L-A is **additive only**. `git diff --diff-filter=MDRT` against
`beafa5d170659997790e1c3e79086ea05548c094` over `benchmark`, `results`, `src`,
`configs`, `docs`, `tests` and `scripts` is **empty**, and this is asserted by
`test_phase_l_a_modified_no_historical_or_frozen_artifact`.

Specifically unmodified: `results/phaseI-rc2-requalification/**`,
`docs/phaseI_posthoc_protocol_audit.md`,
`docs/phaseI_rc2_real_model_requalification_plan.md`, every Phase-I
config/driver/analyzer/result, all Phase-F artifacts,
`benchmark/pilot-v7-rc2/**`, `benchmark/pilot-v7-rc1/**`,
`benchmark/pilot-v6.1/**`, both preregistration files, and
`configs/policies/default.xml`. No rc3 task YAML and no rc3 qualification
semantics were altered.

Files added by this phase:

```
docs/phaseL_rc3_requalification_freeze_report.md
docs/phaseL_rc3_prospective_seed_derivation.json
scripts/phaseL_seed_derivation.py
scripts/phaseL_fault_provenance_reachability_probe.py
tests/integration/test_phaseL_requalification.py
```

---

## 10. Offline validation

All validation is synthetic and offline. No model was run at any point.

| Check | Result |
| --- | --- |
| `python scripts/validate_pilot_v7_rc3.py` | **PASS** — `pilot-v7-rc3 offline validation: PASS (0 failure(s))` |
| `python scripts/validate_pilot_v7_rc2.py` | **PASS** — `pilot-v7-rc2 offline validation: PASS (0 failure(s))` |
| `python scripts/validate_pilot_v7_rc1.py` | **PASS** — `pilot-v7-rc1 offline validation: PASS (0 failure(s))` |
| `pytest tests/integration/test_phaseL_requalification.py` | **48 passed** |
| rc3 construct + Phase-I + Phase-F + protocol-repair + hash-basis tests | **402 passed** |
| Full `pytest` suite | **854 passed** in 87.87s |
| `MYPYPATH=src python -m mypy` | **`Success: no issues found in 45 source files`** |
| `mypy --strict` over the Phase-K/Phase-L scripts | **`Success: no issues found in 4 source files`** (`qualification_harness.py`, `phaseL_seed_derivation.py`, `phaseL_fault_provenance_reachability_probe.py`, `validate_pilot_v7_rc3.py`) |
| `python scripts/phaseL_seed_derivation.py` | exit 0, collision-free |
| `python scripts/phaseL_fault_provenance_reachability_probe.py` | exit 4, `HOLD_PHASE_L_PROTOCOL` |

Phase-L-specific coverage, all synthetic: seed derivation and determinism,
historical-seed non-overlap, collision reporting without self-repair, the exact
102-cell frozen schedule, `run_key` uniqueness, wrong-identity and
missing-identity immediate stop, duplicate and out-of-order protocol deviation,
cross-arm stop, partial-manifest preservation, invalidated-cell accounting,
taxonomy immutability, expected-fault provenance acceptance for a correctly
stamped row, wrong-tool / wrong-resource / wrong-mode fault rejection, forbidden
declared-source rejection, and the reachability defect itself.

The human-gate refusal tests required by section 17 were **not** written, because
no driver exists to refuse. `IQA_SOA_PHASE_L_HUMAN_GATE` was never set and
`--execute-real-model` was never invoked anywhere in this phase.

---

## 11. Fresh-checkout validation

Performed in a clean detached `git worktree` created from the branch commit, with
no Ollama, no model request and no provider inference. The worktree tree was
clean, and every check reproduced:

| Check (fresh worktree) | Result |
| --- | --- |
| `validate_pilot_v7_rc3.py` / `rc2` / `rc1` | **PASS** / **PASS** / **PASS** |
| Full `pytest` suite | **854 passed** in 120.88s |
| `MYPYPATH=src python -m mypy` | **`Success: no issues found in 45 source files`** |
| `mypy --strict` over the four Phase-K/Phase-L scripts | **`Success: no issues found in 4 source files`** |
| `phaseL_seed_derivation.py` | identical seeds `[929260329, 1281385038, 978843421]`, collision-free |
| `phaseL_fault_provenance_reachability_probe.py` | exit 4, `HOLD_PHASE_L_PROTOCOL`, identical finding |

A clean checkout therefore reproduces the seed derivation, the harness-level
matrix and stop-semantics verification, and the defect finding, bit for bit.

---

## 12. Zero-inference confirmation

No model was run at any point in this phase. The only executions that touched
the experiment path used `DeterministicStubProvider`, which replays each
benchmark case's own `scripted_actions` and issues no network request;
`ExperimentRunner._provider_runtime_provenance` returns `None` for a
non-`OpenAICompatibleProvider`, so not even the metadata probe fired. No Ollama
endpoint, no `/api/chat`, no `/api/generate`, no OpenAI-compatible completion,
no cloud provider. `IQA_SOA_PHASE_L_HUMAN_GATE` was never set and no
`--execute-real-model` flag exists to invoke. All probe output went to temporary
directories; nothing under `results/` was written.

---

## 13. Final status

The offline execution protocol is **not** coherent and is **not** ready for
adversarial review, because an unresolved harness defect makes the required
fault-provenance integration unsatisfiable and would force a HOLD verdict before
any inference. Design finalization stopped as section 15 requires.

The `READY_FOR_PHASE_L_EXECUTION_GATE_REVIEW` status is deliberately withheld.

Recommended next step, as a **separate, reviewed phase**: repair the instrument
so that a QA-OFF cell persists runtime-derived fault provenance — the minimal
change being to stamp the four `observed_fault_*` fields in
`ExperimentRunner._run_one` from `agent_run.outcomes` / `SandboxState.operation_log`
— then re-freeze the affected digests, and only then re-attempt the Phase-L-A
protocol freeze.

**pilot-v7-rc3 remains UNQUALIFIED. No inference is authorized.**

HOLD_PHASE_L_PROTOCOL
