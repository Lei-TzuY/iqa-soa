# Phase M — QA-OFF runtime fault-provenance persistence repair and instrument requalification

**ZERO MODEL INFERENCE WAS PERFORMED IN THIS PHASE.**
No provider was contacted. No Ollama endpoint was probed. No `/api/chat`,
`/api/generate` or OpenAI-compatible completion request was issued. No cloud
provider was used. `IQA_SOA_PHASE_L_HUMAN_GATE` was never set and no Phase-L
execution gate, config, driver or analyzer was created. No 102-cell execution,
no preregistration v4, no pilot-v7 FINAL, no 420-run study.

**pilot-v7-rc3 REMAINS UNQUALIFIED.** This phase authorizes no inference.

---

## 0. Outcome in one paragraph

Phase L-A ended `HOLD_PHASE_L_PROTOCOL` because the Phase-K.2 observed-fault
provenance contract could not be satisfied from anything the canonical
instrument persisted for a QA-OFF cell. That diagnosis was correct, and this
phase does not retract it. Phase M repairs the instrument defect it identified,
and nothing else: `ExperimentRunner` now derives the four `observed_fault_*`
fields from the live `GatewayOutcome` sequence before it is discarded, and
writes them to the raw row under a new additive raw schema. QA-OFF treatment
semantics are unchanged, no tool output or protected value is persisted, the
historical Phase-K instrument pin is preserved rather than overwritten, and the
current instrument is separately hash-pinned in an additive revision record.
Both BUD-016 and FAULT-004 now satisfy K.2 prospectively through the real
runner with a deterministic stub, while a wrong tool, a wrong resource, a
missing stamp, a declaration-derived source and an ambiguous multi-fault run all
still fail closed. The status of this phase is
`READY_FOR_PHASE_L_PROTOCOL_REFREEZE`, which authorizes no execution.

---

## 1. Canonical start

| Item | Value |
| --- | --- |
| Canonical starting SHA | `eace204d4c27a9ca48d3c0a660832f640b7a900b` |
| `HEAD` == `main` == `origin/main` | yes, verified before branching |
| Working tree at start | clean |
| Branch created | `phase-m/qaoff-fault-provenance-instrument-repair` |
| `main` modified | no |

Verified at the canonical start: PR #8 / the Phase-L-A archival HOLD is merged;
`benchmark/pilot-v7-rc3/` remains `release-candidate` and **not** qualified;
Phase-L-A remains `HOLD_PHASE_L_PROTOCOL`; no Phase-L execution config, driver
or analyzer exists; `docs/` carries preregistration v1 and v3 only, with no v4;
no `benchmark/pilot-v7` or `benchmark/pilot-v7-final` namespace exists; and no
102-cell Phase-L real-model result exists anywhere under `results/`.

---

## 2. Root cause, confirmed by tracing the live object flow

The defect is an **instrument persistence / observability defect**. It is not a
benchmark-construct defect and not a qualification-harness defect. The Phase-K.2
contract in `scripts/qualification_harness.py` is correct and was not weakened.

Traced through `runner.py` → `gateway.py` → `registry.py` → `collector.py` →
`evidence/logger.py`, the live flow is:

1. `ToolRegistry.execute` stamps `metadata["fault_mode"]` onto the `ToolResult`
   at execution time (`_fault_result`, plus the unregistered-tool and
   unsupported-mode branches).
2. `ServiceGateway.execute` returns a `GatewayOutcome` carrying that
   `tool_result` together with `executed_action` / `proposed_action`. **This is
   exactly the K.2-admitted source `gateway_outcome.executed_action`, and it is
   fully populated at runtime.**
3. `ExperimentRunner._run_one` holds the complete `agent_run.outcomes` tuple —
   and then discarded it. It was never serialized.

So all four fields existed in memory, in an admitted runtime structure, and were
thrown away. The three other candidate paths were all genuinely closed:

- `Treatment.detailed_evidence` is unconditionally `False` for `QAMode.OFF`
  (`treatments.py:43`), so the evidence event carries no `tool_result`.
- `SandboxState.operation_log` reaches disk only inside `final_state_fingerprint`,
  an irreversible SHA-256 (`runner.py`).
- The raw row carried no `observed_fault_*` column.

`observed_fault_tool` and `observed_fault_resource` were recoverable from the
base evidence event, but `observed_fault_mode` and `observed_fault_provenance`
were not, and three of four must hold. FAULT-004 was worse: a
`malformed_response` returns **success** with no error and no failure class, so
its persisted evidence event was byte-identical whether the declared fault fired
or not. The only differentiator was `fault_triggered`, which
`metrics/collector._fault_triggered` computes as
`tool_result.metadata["fault_mode"] == case.fault.type` — a comparison against
the benchmark **declaration**, which is precisely the circular source
`DECLARED_FAULT_PROVENANCE_SOURCES` exists to forbid.

**Why Phase K did not catch it.**
`check_observed_fault_provenance_is_runtime_derived` proved the contract
satisfiable by driving `ToolRegistry` directly in-process and reading
`state.operation_log` from live memory. That is a valid proof that the contract
is well-formed. It is not a proof that the telemetry is reachable from what a
driver receives.

### Reproduced before the repair

`python scripts/phaseL_fault_provenance_reachability_probe.py`, at
`eace204`, exit **4**:

| Task | row `failure_class` | row `fault_triggered` | Harness class | Disposition |
| --- | --- | --- | --- | --- |
| BUD-016 | `tool_timeout` | `None` | `UNEXPECTED_SANDBOX_FAILURE` | `CELL_INVALID_AND_HOLD` |
| FAULT-004 | `None` | `True` | `UNEXPECTED_SANDBOX_FAILURE` | `CELL_INVALID_AND_HOLD` |

Unreachable fields: `observed_fault_mode`, `observed_fault_provenance`.

---

## 3. Files changed, and why

Instrument (`src/iqa_soa/`) — the five files bound by
`docs/phaseM_instrument_revision.json`, each with its own SHA-256:

| File | Change |
| --- | --- |
| `src/iqa_soa/experiment/fault_provenance.py` | **NEW.** The derivation. |
| `src/iqa_soa/experiment/runner.py` | Stamps the derived fields in `_run_one`; writes the schema-4 field set. |
| `src/iqa_soa/instrument.py` | Instrument boundary 3 / raw schema 4; permanent named constants for every historical version. |
| `src/iqa_soa/metrics/definitions.py` | `FAULT_PROVENANCE_TELEMETRY_FIELDS`, `PILOT_RAW_FIELDS_V4`, `RAW_FIELDS_BY_SCHEMA_VERSION`. |
| `src/iqa_soa/metrics/pilot.py` | Reads every historical schema; requires each row to carry its own schema's fields. |

Supporting scripts and tests:

| File | Change |
| --- | --- |
| `scripts/instrument_revision.py` | **NEW.** Separates the historical freeze assertion from the approved current revision. |
| `scripts/phaseM_write_instrument_revision.py` | **NEW.** Regenerates the revision record deterministically. |
| `tests/integration/test_phaseM_fault_provenance_instrument.py` | **NEW.** 63 adversarial tests. |
| `scripts/validate_pilot_v7_rc3.py`, `scripts/validate_pilot_v7_rc2.py` | Delegate the `src/iqa_soa` pin to the provenance module. |
| `scripts/analyze_phaseD/F/I*.py`, `scripts/phaseD_preflight.py` | Pin the instrument version their phase actually ran under. |
| `scripts/phaseL_fault_provenance_reachability_probe.py` | Records BEFORE/AFTER; also reports the row-level differentiator. |
| `tests/integration/test_phaseL_requalification.py` | Regression pins **inverted**, not relaxed. |
| `tests/integration/test_phaseF_qualification.py`, `test_phaseI_requalification.py` | Phase-scoped immutability assertions moved from the working tree to their own commit ranges. |
| `tests/integration/test_real_pilot_runner.py` | Schema-4 field set. |

**No `benchmark/`, `results/`, `configs/` or existing `docs/` byte was modified.**

---

## 4. Instrument and raw-schema versioning

| | Before | After |
| --- | --- | --- |
| `INSTRUMENT_VERSION` | `"2"` | `"3"` |
| `RAW_SCHEMA_VERSION` | `3` | `4` |
| `NATIVE_TOOL_ADAPTER_VERSION` | `native-tools-adapter-2` | **unchanged** |
| `src/iqa_soa` tree | `1825ca11…a53c4d3` | `c86a0912…9c8b83da` |

Every historical version is now a **permanent named constant**:
`PROTOCOL_TELEMETRY_INSTRUMENT_VERSION = "2"`,
`PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION = 3`,
`FAULT_PROVENANCE_INSTRUMENT_VERSION = "3"`,
`FAULT_PROVENANCE_RAW_SCHEMA_VERSION = 4`, with `INSTRUMENT_VERSION` and
`RAW_SCHEMA_VERSION` as aliases for "what the instrument writes today".

Three deliberate decisions:

- **Schema 4 is strictly additive.** `PILOT_RAW_FIELDS_V4` is
  `PILOT_RAW_FIELDS_V3` plus five columns, in that order. No schema-3 field
  changed name, type or meaning, so a schema-3 reader still reads a schema-4 row.
  The frozen schema-3 contract is not redefined.
- **Historical phases pin their own version.** The Phase-D/F/I analyzers
  previously compared against whichever constant was current, so an additive
  revision would have retroactively failed committed artifacts. They now pin
  `PROTOCOL_TELEMETRY_*`. Verdict invariance over the committed results is
  asserted by `test_the_frozen_phase_analyzers_still_read_committed_results`,
  which redirects output to a temp directory and then asserts the `results/`
  tree digest is unchanged.
- **The adapter version does not move.** Phase M did not touch the native-tools
  adapter. Conflating the two boundaries would lose information.

`INSTRUMENT_VERSION` is bumped even though the change is observation-only — it
alters no prompt, policy, guard, tool dispatch or metric, so a Phase-M row and a
Phase-B..L row measure the same quantities. The bump is the conservative call:
this constant exists so that a harness difference is machine-checkable rather
than argued from memory, and `metrics/pilot.py` will now refuse to pool across
the boundary by default. An analyst who wants to pool must say so explicitly.

---

## 5. The runtime derivation algorithm

`src/iqa_soa/experiment/fault_provenance.py`, called once, from
`ExperimentRunner._run_one`, as `**observed_fault_telemetry(agent_run.outcomes)`.

For each `GatewayOutcome` in the run, in order:

1. If `outcome.tool_result` is `None`, skip.
2. If `tool_result.metadata["fault_mode"]` is absent, non-string or blank, skip.
   **A fault is never inferred** — not from `failure_class == "tool_timeout"`,
   not from the error string `"simulated tool timeout"`, not from
   `fault_triggered`, and not from `FAULT_MODE_SIGNATURE`.
3. Otherwise take the action from `executed_action`, labelling the provenance
   `gateway_outcome.executed_action`; when governance blocked before execution
   and `executed_action` is `None`, fall back to `proposed_action` and label it
   `gateway_outcome.proposed_action`. Both labels are members of
   `RUNTIME_FAULT_PROVENANCE_SOURCES`.
4. Emit `(tool, resource, mode, provenance)` from that same outcome.

Then collapse to **distinct identities** and emit:

| Distinct identities | `observed_fault_*` | `observed_fault_observation_count` |
| --- | --- | --- |
| 0 | all `None` | `0` |
| 1 | stamped from it | `1` |
| ≥ 2 | all `None` (**fail closed**) | the count |

Any mode the sandbox stamps is admitted, including `unavailable` from the
unregistered-tool branch and `high_latency`. Filtering by which modes a benchmark
happens to declare would reintroduce the declaration through the back door; a
non-matching observed mode must reach the matcher and be **refused there**, not
suppressed at the source.

---

## 6. Proof that no declaration manufactures the observation

The invariant is enforced **structurally**, not by convention:

1. **Signature.** Every public function in `fault_provenance.py` takes
   `Sequence[GatewayOutcome]` and nothing else. There is no parameter through
   which a `BenchmarkCase`, `case.fault`, `ground_truth`, a `ScriptedFault`, the
   qualification contract or a task-id fault table could be passed.
   `test_the_derivation_cannot_see_the_benchmark_declaration` asserts the
   parameter list is exactly `["outcomes"]`.
2. **Imports.** The module imports only `iqa_soa.types.GatewayOutcome`.
   `test_the_fault_provenance_module_imports_no_benchmark_symbol` asserts no
   declaration-shaped symbol appears in any import or assignment.
3. **Call site.** `test_the_runner_derives_provenance_only_from_agent_run_outcomes`
   asserts the single call site is literally
   `**observed_fault_telemetry(agent_run.outcomes),`.
4. **Behavioural counterfactual.** `test_the_no_fault_counterfactual_removes_the_observation`
   strips the declared fault from BUD-016 and FAULT-004 and re-runs. The action
   is identical; only the sandbox outcome differs; the four fields go `None`.
   A declaration-derived field could not behave this way.
5. **Forbidden sources still rejected.** Parametrised over every member of
   `DECLARED_FAULT_PROVENANCE_SOURCES` × both fault tasks, a row carrying the
   **correct** tool, resource and mode but naming the declaration as its source
   is refused and classified `UNEXPECTED_SANDBOX_FAILURE` →
   `CELL_INVALID_AND_HOLD`.

---

## 7. Multiple fault observations — audited, not assumed

**Multiple runtime-stamped faults are not hypothetical; they occur in the frozen
benchmark today.** BUD-016 declares one timeout on
`api.call:platform-api/service-health` and scripts **three** calls to that
endpoint (`status-attempt`, `status-retry`, `overbudget-retry`). Under QA OFF the
budget guard is disabled, so all three execute and all three are stamped. This
was measured, not reasoned about, and is pinned by
`test_bud_016_really_does_stamp_three_identical_fault_observations`.

The decision, and its justification:

- **Repetition of the same identity is agreement, not ambiguity.** BUD-016's
  three observations agree on tool, resource, mode and provenance. They describe
  one fault, and reporting it once is a faithful summary rather than a choice
  between candidates. `observed_fault_observation_count` is `1`.
- **Two or more DISTINCT identities fail closed.** All four fields are withheld.
  The instrument does not pick one, because there is no non-arbitrary basis for
  picking and a chosen one would present genuinely ambiguous provenance as a
  clean single observation. Withholding fails closed at
  `observed_fault_from_row`, giving `UNEXPECTED_SANDBOX_FAILURE` →
  `CELL_INVALID_AND_HOLD`. A cell that observed two different sandbox faults
  *should* hold the verdict.
- **Provenance is part of the identity.** Two occurrences agreeing on tool,
  resource and mode but read from different runtime structures do not agree on
  where the observation came from, and the row has one provenance slot. Treating
  that as disagreement means the instrument never silently picks a label.
- **Ambiguity is distinguishable from absence.** This is the sole reason the
  fifth column exists. `0` means no fault was stamped; `≥ 2` means disagreeing
  faults were observed and deliberately withheld. Without it the fail-closed
  case would be indistinguishable from a clean no-fault run in the record.

---

## 8. QA-OFF treatment invariance and minimality

The repair is **raw protocol telemetry, not evidence-guard activation**.

- `treatment_for("off").detailed_evidence` is still `False`; the evidence guard
  is still disabled; every QA-OFF guard is still off
  (`test_qa_off_detailed_evidence_is_still_false`).
- `full` and `partial` are unchanged.
- QA-OFF evidence events still carry exactly the same 14 keys as before, and
  still omit `tool_result`, `proposed_action`, `executed_action`,
  `guard_results`, `applicable_policy` and `causal_links`
  (`test_qa_off_evidence_events_still_omit_the_detailed_tool_result_block`).
- The `<<<MALFORMED_SIMULATED_RESPONSE>>>` sentinel appears in neither the raw
  record nor the trace. Neither does `operation_log`, `gateway_outcomes`, the
  backing API payload, nor `AgentRun.outcomes`
  (`test_no_tool_output_or_sentinel_reaches_the_raw_record`).
- No protected synthetic value appears in any of the five new columns, checked
  by running every rc3 privacy task
  (`test_no_protected_value_enters_the_raw_telemetry`).
- Exactly five columns were added: the four the K.2 contract names, plus the
  ambiguity counter (`test_the_observed_fault_columns_are_exactly_five`).

The FAULT-004 evidence event remains **byte-identical** whether the fault fired
or not, and that is now the demonstration rather than the defect: the
differentiator lives in the raw row, and disappears when the fault is stripped.

---

## 9. Deterministic results — BUD-016 and FAULT-004

Real `ExperimentRunner`, real frozen rc3 cases, real QA-OFF treatment,
`DeterministicStubProvider`, no inference.

**BUD-016** — `failure_class = "tool_timeout"`, `fault_triggered = None`:

```
observed_fault_tool              = "api.call"
observed_fault_resource          = "platform-api/service-health"
observed_fault_mode              = "timeout"
observed_fault_provenance        = "gateway_outcome.executed_action"
observed_fault_observation_count = 1        (3 runtime stamps, 1 identity)
```
→ `EXPECTED_SCRIPTED_FAULT` → `CONTINUE`

**FAULT-004** — `failure_class = None`, `fault_triggered = True`:

```
observed_fault_tool              = "api.call"
observed_fault_resource          = "inventory-api/sku-4471"
observed_fault_mode              = "malformed_response"
observed_fault_provenance        = "gateway_outcome.executed_action"
observed_fault_observation_count = 1
```
→ `EXPECTED_SCRIPTED_FAULT` → `CONTINUE`

Neither row copies any benchmark declaration. The probe stamps only the identity
fields a Phase-L driver legitimately owns from the frozen cell (model, digest,
seed, `run_key`) and deliberately does **not** stamp fault provenance.

---

## 10. Negative and adversarial results

All deterministic, all offline. Every case below fails closed to
`UNEXPECTED_SANDBOX_FAILURE` → `CELL_INVALID_AND_HOLD` unless stated otherwise.

| Case | Result |
| --- | --- |
| BUD-016 wrong tool (`file.read`, right resource/mode) | refused — "observed tool" |
| BUD-016 wrong resource | refused — "observed resource" |
| BUD-016 missing runtime `fault_mode` | refused (the exact Phase-L-A failure, kept as a control) |
| BUD-016 provenance from any of the 5 declared sources | refused — "declaration" |
| FAULT-004 wrong tool | refused |
| FAULT-004 wrong resource | refused |
| FAULT-004 `fault_triggered=True` alone, no provenance | refused |
| FAULT-004 provenance from any declared source | refused |
| FAULT-004 fault stripped | no observation emitted at all |
| FAULT-004's fault observed under the BUD-016 task id | refused |
| Wrong-tool call against the real registry | sandbox stamps no `fault_mode` at all |
| Timeout signature with no sandbox stamp | no observation (never inferred) |
| Empty / whitespace `fault_mode` | no observation |
| Two distinct fault identities (tool, resource or mode) | all four fields withheld, count preserved |
| Same identity via executed + proposed | treated as disagreement, withheld |
| Ordinary benign task (BEN-002, BEN-003) | no fields, count `0`, `CELL_OK` → `CONTINUE` |
| Unapproved edit under `src/iqa_soa` | rc3 validation **FAILS**, naming the file |

---

## 11. The additive instrument-revision record

`docs/phaseM_instrument_revision.json`, generated deterministically by
`scripts/phaseM_write_instrument_revision.py` and enforced by
`scripts/instrument_revision.py`. **The rc3 freeze record was not edited**; its
`src_iqa_soa_tree` pin is preserved exactly as Phase K wrote it.

The §13 requirement was to separate two claims the old validator conflated:

**(A) The historical Phase-K freeze assertion** — "when Phase K froze rc3, the
instrument was tree `1825ca11…`" — is a closed fact about a past commit. It is
now proved from **committed bytes at the freeze commit**
`978c8cb1dcb1b6dc5a2ec51a7233a26c114e2569`, so it stays verifiable forever no
matter what any later phase does.

**(B) The current instrument** is pinned separately, and **more strictly than a
lone tree digest**. `check_approved_instrument_revision` requires all of:

1. the revision record exists and names its parent commit and both digests;
2. its parent digest is exactly the Phase-K pin — an unbroken chain of custody;
3. the working tree digests to exactly the approved new value;
4. the set of files changed since the parent commit is **exactly** the approved
   set — no extra file, no missing file;
5. every approved file's current bytes hash to its approved SHA-256;
6. every approved file carries a non-empty scientific reason;
7. the recorded instrument and raw-schema versions equal what the code declares.

Asserting (A) by checking (B) is what stopped Phase L-A: the rc3 validator
required the live tree to equal the frozen digest, so repairing the defect that
Phase L-A had just found would itself fail rc3 validation. An immutability check
had become a prohibition on ever repairing a defect it helped hide.

**This strengthens provenance rather than weakening immutability.** Previously
the repository could say only "src/iqa_soa is unchanged". It can now say what
changed, to which bytes, against which parent, and why — and a drive-by edit
still fails, proved by `test_an_unapproved_instrument_edit_fails_validation` and
reproduced manually against the rc3 CLI.

Key hashes:

| Item | Value |
| --- | --- |
| Parent canonical commit | `eace204d4c27a9ca48d3c0a660832f640b7a900b` |
| Phase-K freeze commit | `978c8cb1dcb1b6dc5a2ec51a7233a26c114e2569` |
| Previous `src/iqa_soa` tree | `1825ca11de6723c10fa557d641b4c3585b20c2f9a1c634e9247d46821a53c4d3` |
| New `src/iqa_soa` tree | `c86a091298b0caaa480de729fcfc8e820eb0ce72317827932be1946f9c8b83da` |
| `benchmark/pilot-v7-rc3/manifest.json` | `2e3ff2157d8d61d5aed5386910e80f4ef6a1a845bf560378c4f9a2c94d899b0d` |
| `benchmark/pilot-v7-rc3/qualification-contract.json` | `6d3fbcf8bb0213c4619e1a268502cc9b669146bf5f677bfd421b58ee1d26e7ca` |
| `benchmark/pilot-v7-rc3/provenance.json` | `078a73c59e8ec4d1964d5079233159542af4b70f4ef908128836308a3d4c658a` |
| `benchmark/pilot-v7-rc3/AUDIT.md` | `65b6eae0fc67a21a1ec76d7c5ce7374909a2111c23b09efbd7e5533be9d3476b` |
| `configs/policies/default.xml` | `256a8205fa944f74e12642925298260848fae5ebbb320f695ce0a234ea9f63e5` |

The rc3 manifest, contract, provenance, audit and QA policy digests are
**identical to the values Phase K pinned**, confirming the benchmark did not move.

---

## 12. Historical immutability

`git diff --name-only --diff-filter=MDRT eace204… -- benchmark results configs docs`
is **empty**. Specifically unmodified: `results/phaseI-rc2-requalification/**`,
all Phase-I raw evidence, all Phase-F evidence,
`docs/phaseI_posthoc_protocol_audit.md`,
`docs/phaseI_rc2_real_model_requalification_plan.md`,
`benchmark/pilot-v7-rc2/**`, `benchmark/pilot-v7-rc1/**`,
`benchmark/pilot-v6.1/**`, both preregistration files, and
`configs/policies/default.xml`. No rc3 task YAML, scoring semantic or
qualification threshold was touched.

**The Phase-L-A HOLD report is byte-identical.** Phase M does not rewrite the
history in which the defect existed;
`test_the_phase_l_a_hold_record_is_never_rewritten` asserts this **live**,
against the working tree, over the report, the seed-derivation record and the
seed-derivation script.

Committed Phase-F and Phase-I raw rows are neither rewritten nor re-run, still
declare `raw_schema_version 3` / `instrument_version "2"`, still do **not** carry
the new columns, and are still analyzable
(`test_committed_historical_rows_are_untouched_and_still_declare_schema_3`).

One class of assertion was refactored rather than deleted. Several tests
asserted "phase X changed nothing under `src/iqa_soa`" by comparing against the
**live working tree**, which silently upgraded a closed historical fact into a
permanent veto on all future instrument work — the same conflation described in
§11. Those assertions now compare their phase's own commit range
(`CANONICAL_BASE..PHASE_COMMIT`), where the claim is true and stays true. Every
assertion about frozen **data** remains live against the working tree.

---

## 13. Phase-L reachability probe: BEFORE and AFTER

The Phase-L-A defect reproduction was **not deleted**, and the probe measures
exactly what it measured before. Its regression pins were **inverted, not
relaxed**: if the four fields ever disappear again, `contract_reachable` returns
to `False` and the tests fail.

| | BEFORE (`eace204`, instrument 2 / schema 3) | AFTER (Phase M, instrument 3 / schema 4) |
| --- | --- | --- |
| Probe exit code | `4` | `0` |
| `contract_reachable` | `false` | `true` |
| Unreachable fields | `observed_fault_mode`, `observed_fault_provenance` | none |
| BUD-016 | `UNEXPECTED_SANDBOX_FAILURE` / `CELL_INVALID_AND_HOLD` | `EXPECTED_SCRIPTED_FAULT` / `CONTINUE` |
| FAULT-004 | `UNEXPECTED_SANDBOX_FAILURE` / `CELL_INVALID_AND_HOLD` | `EXPECTED_SCRIPTED_FAULT` / `CONTINUE` |
| Tasks forced to hold | `["BUD-016", "FAULT-004"]` | `[]` |
| `detailed_evidence_under_qa_off` | `false` | **`false`** (unchanged) |
| FAULT-004 evidence events identical | `true` | **`true`** (unchanged, deliberately) |
| FAULT-004 raw rows differ | not measured | `true` |

The last three rows are the crux: the repair moved the differentiator into the
raw row **without** making the QA-OFF evidence trace any more detailed.

---

## 14. Offline validation

| Check | Result |
| --- | --- |
| `python scripts/validate_pilot_v7_rc3.py` | **PASS** (0 failures) |
| `python scripts/validate_pilot_v7_rc2.py` | **PASS** (0 failures) |
| `python scripts/validate_pilot_v7_rc1.py` | **PASS** (0 failures) |
| `python scripts/instrument_revision.py` | **PASS** (0 failures) |
| `python scripts/phaseL_fault_provenance_reachability_probe.py` | exit **0**, `contract_reachable = true` |
| `pytest tests/integration/test_phaseM_fault_provenance_instrument.py` | **63 passed** |
| `pytest tests/integration/test_phaseL_requalification.py` | **49 passed** |
| rc3 construct + Phase-I + Phase-F + protocol-repair + hash-basis tests | **412 passed** |
| Full `pytest` | **919 passed** |
| `MYPYPATH=src python -m mypy` | `Success: no issues found in 46 source files` |
| `mypy --strict` over every changed script | `Success: no issues found in 8 source files` |

Baseline before the phase was **854 passed**; Phase M adds 65 tests and modifies
no test to make a failing assertion pass, other than the deliberate Phase-L
inversions documented in §13.

**One pre-existing condition, unrelated to Phase M and not introduced by it:**
`scripts/validate_pilot_v7_rc1.py` has two `mypy --strict` findings
(`no-any-return`, `assignment`) that are present at the canonical base. That file
is untouched by this phase — it is in the Phase-I live-protected list — so the
findings are reported rather than repaired. The equivalent findings in
`validate_pilot_v7_rc2.py` were fixed, because that file was already being
modified and its sibling rc3 validator already used the strict-clean idiom.

---

## 15. Fresh-worktree validation

See §16 of the final response. Performed in a clean detached `git worktree`
created from the branch commit, with no Ollama, no model request and no provider
inference.

---

## 16. Zero-inference confirmation

No model was run at any point. Every execution that touched the experiment path
used `DeterministicStubProvider`, which replays each benchmark case's own
`scripted_actions` and issues no network request. Because it is not an
`OpenAICompatibleProvider`, `ExperimentRunner._provider_runtime_provenance`
returns `None`, so not even the metadata probe fired — asserted by
`test_only_the_deterministic_stub_provider_is_used`, which checks
`manifest["provider_runtime"] is None`.

No Ollama endpoint, no `/api/chat`, no `/api/generate`, no OpenAI-compatible
completion, no cloud provider, no real-model token.
`IQA_SOA_PHASE_L_HUMAN_GATE` was never set, and no Phase-L execution gate exists
to invoke. `test_no_phase_m_source_contacts_a_provider` scans every file Phase M
added for provider endpoints, HTTP clients and the gate variable;
`test_phase_m_authorizes_no_real_model_execution` asserts the gate variable is
unset and that no Phase-L config, driver, analyzer, plan, preregistration v4 or
pilot-v7 FINAL namespace exists.

All probe and test output went to temporary directories. Nothing under
`results/` was written; the `results/` tree digest is asserted unchanged even
across running the historical analyzers.

---

## 17. Final status

The instrument defect that produced `HOLD_PHASE_L_PROTOCOL` is repaired. Runtime
fault provenance is genuinely persisted under QA OFF, derived from live runtime
outcomes rather than benchmark declarations; QA-OFF treatment semantics are
unchanged; no sensitive tool output was added; the raw schema and instrument
version are additively and explicitly revised; BUD-016 and FAULT-004 both satisfy
K.2 prospectively; wrong, missing, ambiguous and declaration-derived provenance
all still fail closed; historical evidence is untouched; the instrument revision
is separately hash-pinned; full validation passes; and zero real-model inference
occurred.

This authorizes a Phase-L-A′ protocol refreeze attempt. **It does not authorize
Phase-L real-model execution.** pilot-v7-rc3 remains UNQUALIFIED and no inference
is authorized.

READY_FOR_PHASE_L_PROTOCOL_REFREEZE
