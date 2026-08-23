# Phase O — pilot-v7-rc4 offline redesign report

**OFFLINE REDESIGN ONLY. NO MODEL INFERENCE. NO OLLAMA CONTACT. NO PROVIDER
CONTACT. pilot-v7-rc3 REMAINS UNQUALIFIED. pilot-v7-rc4 IS UNQUALIFIED. NO
EXECUTION AUTHORIZATION.**

| Item | Value |
|---|---|
| Canonical start SHA (`origin/main`) | `0cc3b05ab79559acdd4f50675ed7937199dc4dbe` |
| Branch | `phase-o/pilot-v7-rc4-offline-redesign` |
| Phase-L-B verdict (unchanged) | **`HOLD`** |
| Phase-L-B terminal status (unchanged) | **`SCHEDULE_COMPLETE_VERDICT_HOLD`** |
| pilot-v7-rc3 status | **UNQUALIFIED** |
| pilot-v7-rc4 status | **UNQUALIFIED**, release-candidate, OFFLINE-DESIGNED |
| Model inference in Phase O | **none** |
| Provider / Ollama contact in Phase O | **none** |
| Cells executed, rerun, retried, replaced, resumed | **0** |
| Seeds selected in Phase O | **0** |
| Phase-L seed status | `CONSUMED_BY_FORMAL_PHASE_L_B` |

The design rationale is in [`docs/phaseO_rc4_redesign_spec.md`](phaseO_rc4_redesign_spec.md).
The machine-readable audit is in [`docs/phaseO_rc4_revision_record.json`](phaseO_rc4_revision_record.json).
This document records what was done, what was checked, and what was deliberately
not done.

---

## 1. The 17-task retain / revise audit

Exactly one disposition per rc3 task, from the closed set. Twelve tasks are
carried forward **byte-identically**, three keep their bytes and revise their
contract entry, and exactly two — the only two Phase N found to have failed
benchmark reachability — receive new IDs.

| rc3 | Disposition | rc4 | Bytes |
|---|---|---|---|
| `BEN-002` | `RETAIN_BYTE_IDENTICAL` | `BEN-002` | same |
| `BEN-003` | `RETAIN_BYTE_IDENTICAL` | `BEN-003` | same |
| `PI-015` | `RETAIN_BYTE_IDENTICAL` | `PI-015` | same |
| `PI-018` | `RETAIN_BYTE_IDENTICAL` | `PI-018` | same |
| `PI-019` | `RETAIN_BYTE_IDENTICAL` | `PI-019` | same |
| `PI-020` | `RETAIN_TASK_REVISE_CONTRACT_ONLY` | `PI-020` | same |
| `KP-004` | `RETAIN_BYTE_IDENTICAL` | `KP-004` | same |
| `UA-004` | `RETAIN_BYTE_IDENTICAL` | `UA-004` | same |
| `UA-005` | `RETAIN_BYTE_IDENTICAL` | `UA-005` | same |
| `PRIV-007` | `RETAIN_BYTE_IDENTICAL` | `PRIV-007` | same |
| `PRIV-012` | `RETAIN_BYTE_IDENTICAL` | `PRIV-012` | same |
| `PRIV-016` | `RETAIN_BYTE_IDENTICAL` | `PRIV-016` | same |
| `PRIV-017` | `RETAIN_BYTE_IDENTICAL` | `PRIV-017` | same |
| `BUD-014` | **`REVISE_TASK_NEW_ID`** | **`BUD-017`** | **changed** |
| `BUD-015` | **`REVISE_TASK_NEW_ID`** | **`BUD-018`** | **changed** |
| `BUD-016` | `RETAIN_TASK_REVISE_CONTRACT_ONLY` | `BUD-016` | same |
| `FAULT-004` | `RETAIN_TASK_REVISE_CONTRACT_ONLY` | `FAULT-004` | same |

`RETAIN_BYTE_IDENTICAL` 12 · `RETAIN_TASK_REVISE_CONTRACT_ONLY` 3 ·
`REVISE_TASK_NEW_ID` 2 · `REPLACE_TASK` 0 · `DROP_TASK` 0.

The full scientific reason, the Phase-N evidence, the construct preserved, what
changes and what must not change are recorded per task in
`benchmark/pilot-v7-rc4/AUDIT.md`, in the manifest's `selection_rationale`, in
the provenance's `carried_forward`, and in each contract entry's
`rc4_audit_reason`. Those four are generated from one table, so they cannot
disagree.

**A changed task always receives a new ID.** `check_retained_tasks_are_byte_identical`
fails both ways: a task keeping an rc3 ID whose bytes differ, and a task claiming
a new ID whose bytes are identical.

---

## 2. What was repaired, and where

The most consequential structural fact about this redesign: **eight tasks were
unqualified in Phase L-B, and only two of them were defective as tasks.** Three
of the four instrument findings required no benchmark change at all.

| Finding | Repaired in | Benchmark bytes |
|---|---|---|
| N-1 `TOOL_SCHEMA_PRESENTATION_DEFECT` | instrument | **none** |
| N-2 `HARNESS_FAILURE_ATTRIBUTION_DEFECT` | instrument + harness | FAULT-004 contract only |
| N-3 near miss inexpressible | contract vocabulary | PI-020 contract only |
| N-4 near-miss over-report | contract | BUD-016 contract only |
| reachability (BUD-014, BUD-015) | benchmark | **two new task IDs** |

### 2.1 The truthful tool contract (N-1)

`src/iqa_soa/tools/argument_schema.py` is the one table the sandbox enforces and
the provider advertises. `file.write` requires exactly `content`; the six
undisclosed aliases (`content, body, message, payload, data, value`) are
withdrawn, along with `database.update`'s `values`/`data` aliases and its
undisclosed leftover-arguments fallback, and `robot.move_simulated`'s `position`.

Every scripted action in the entire benchmark corpus already used the canonical
key, so the narrowing changes no benchmark behaviour — it removes only the hidden
acceptance. The contract is disclosed by **two independent channels**
(`parameters.allOf` and prose in both the tool description and the system-prompt
schema instruction), because Phase N showed a contract carried solely by the
`tools` field is not reliably visible to the Mistral path.

`check_tool_contract_conformance` fails if the schema requires something the
sandbox does not, if the sandbox requires something the schema omits, or if any
withdrawn alias remains behaviourally significant.

### 2.2 Event-local ordered attribution (N-2)

`src/iqa_soa/experiment/failure_events.py` derives an ordered per-action failure
list from the live `GatewayOutcome` sequence, under the same structural invariant
as Phase M's fault provenance: it can see nothing but the outcomes, so an event
cannot be manufactured from the declaration it will be compared against.

`scripts/qualification_harness_v2.py` attributes each event and decides by a
precedence stated as data. **Fail-closed stays at the top**: an unbound fault and
an unexplained sandbox failure both outrank a bound fault and both still force
`HOLD`. The only precedence that changed is that a *proved* fault now outranks an
earlier, separately attributable resource miss.

The frozen `scripts/qualification_harness.py` is **byte-identical** to its
committed form and is imported, not copied: `bind_row_to_cell`, `Cell`,
`run_key`, the disposition map, the immediate-stop set and the schedule semantics
are literally the same objects.

### 2.3 Argument-aware near misses (N-3) and the first-attempt exclusion (N-4)

`scripts/rc4_scoring_vocabulary.py` lets a near-miss clause carry an argument
predicate and freezes a four-way payload separation in which exactly one outcome
is exposure. Exposure is decided first and independently, so a near-miss
predicate can neither widen nor shrink it — and `check_vocabulary` refuses a
clause that resolves to the canonical signature at all.

BUD-016 gains a machine-readable `near_miss_exclusions` block naming its intended
first endpoint attempt.

### 2.4 The two reachability repairs

**BUD-017** gives the vendor reports opaque reference identifiers and makes the
register the vendor-to-file index; reading it becomes the ordinary way to find
anything rather than a scoping step a model must think to take. **BUD-018**
replaces the decoy that stated a group total with a movement log that states no
figure at all, so the two-extract route is the only route.

Both preserve their construct, their cap and the unforced character of the risky
action. The validator enforces both repairs rather than trusting them: BUD-017's
canonical enum may contain no vendor name, and BUD-018's third resource may
contain no digits.

---

## 3. Validation

All offline. **No Ollama access. No `/api/chat`, `/api/generate` or
`/v1/chat/completions` request. No provider adapter was invoked.**

| Check | Result |
|---|---|
| `python scripts/validate_pilot_v7_rc4.py` | **PASS** — 0 failures |
| `python scripts/phaseO_rc4_construct_probe.py` | **PASS** — 0 failures |
| `python scripts/rc4_scoring_vocabulary.py` | **PASS** — 0 failures |
| `python scripts/qualification_harness_v2.py` | **PASS** — self-check, 0 failures |
| `python scripts/build_pilot_v7_rc4.py --check` | **PASS** — 0 drifted artifacts |
| `python scripts/phaseO_write_revision_record.py --check` | **PASS** |
| `python scripts/phaseO_write_instrument_revision.py` (regenerate) | reproduces byte-for-byte |
| `python scripts/phaseO_frozen_input_supersession.py` | **PASS** — 0 failures |
| `python scripts/validate_pilot_v7_rc3.py` | **PASS** — 0 failures |
| `python scripts/validate_pilot_v7_rc1.py` | **PASS** — 0 failures |
| `python scripts/validate_pilot_v7_rc2.py` | **FAIL (1)** — the single Phase-M superseded assertion, §4 |
| `python scripts/instrument_revision.py` | **PASS** — chain M → O verified |
| `python scripts/phaseM_frozen_input_audit.py` | **PASS** — 12 bound inputs, 6 sidecars |
| `python scripts/phaseN_diagnose_phaseL_hold.py --verify-offline` | **PASS** |
| `python scripts/phaseN_diagnose_phaseL_hold.py --reconcile` | **PASS** — 0 failures against the archived analysis |
| `python scripts/analyze_phaseL_requalification.py --verify-scoring-plan` | **PASS** |
| `python scripts/run_phaseL_requalification.py --verify-frozen-inputs` | **FAIL (7)** — exactly the superseded set, §4 |
| `mypy src` | **PASS** — no issues in 48 files |
| `mypy --strict` over the 8 new Phase-O scripts | **PASS** — no issues |
| `pytest tests/integration/test_phaseO_rc4_redesign.py` | **PASS** — 60 passed |
| `pytest tests/benchmark/test_pilot_v7_rc4_construct.py` | **PASS** — 31 passed |
| full `pytest`, in a fresh detached worktree at the final commit | see §3.2 |

### 3.1 Zero-inference proof

1. `check_no_provider_execution` scans every Phase-O source for the endpoint
   paths, the provider class, the runtime probe, `urllib.request`,
   `requests.post`, either URL scheme and the human-gate variable. Each forbidden
   token is assembled from fragments inside the validator, so the check cannot be
   satisfied vacuously by its own source.
2. No Phase-O module imports `iqa_soa.agent.providers` for anything but rendering
   a tool definition offline, and none constructs a provider.
3. `scripts/phaseN_diagnose_phaseL_hold.py`'s process-wide audit hook, which
   raises on `socket.connect`, `socket.getaddrinfo` and `urllib.Request`, still
   reports zero refused events.
4. No execution driver, no `results/phaseO-*` tree and no preregistration v4
   exists, asserted by `test_no_execution_driver_was_created`.


### 3.2 The full suite, and the two failures Phase O did not cause

Every check above, and the whole suite, was re-run in a **fresh detached git
worktree checked out at the final commit** with a clean status:

```
2 failed, 1247 passed in 1133.09s
```

Both failures are the same pre-existing test-isolation artifact:

```
tests/integration/test_phaseN_hold_forensics.py::test_offline_verification_passes
tests/integration/test_phaseN_hold_forensics.py::test_no_provider_or_agent_module_is_loaded
```

Phase N's offline invariant is that **no provider or agent module is loaded in
the test process**. That holds when the module runs alone — 44 passed — and fails
whenever any earlier module in the same pytest process has imported
`iqa_soa.agent.providers`, because pytest shares one interpreter. It is a
test-isolation artifact of whole-suite ordering, not a statement about Phase O.

**Reproduced at the canonical base, with Phase O absent.** At
`0cc3b05a…`, running

```
pytest tests/integration/test_phaseL_execution_protocol.py \n       tests/integration/test_phaseN_hold_forensics.py
```

yields exactly these two failures (plus the two stale seed invariants Phase O has
since superseded). Running `test_phaseN_hold_forensics.py` alone at the same
commit passes 44/44. Phase O neither introduces nor worsens this, and the
underlying guarantee is unaffected: `scripts/phaseN_diagnose_phaseL_hold.py
--verify-offline` reports **0 failures** when invoked as a process, which is how
the guarantee is actually made.

**Against the canonical base, the delta is entirely in the right direction.** The
base ran `6 failed, 1150 passed`: four stale Phase-L pre-execution invariants plus
these same two artifacts. The final commit runs `2 failed, 1247 passed` — the four
stale invariants are **repaired** by §4.5, 97 tests are added, and no test that
passed at the base fails now.

---

## 4. Historical immutability, and the one thing Phase O supersedes

### 4.1 Untouched

`git diff --diff-filter=MDRT 0cc3b05a… --` over `benchmark/pilot-v7-rc3`,
`benchmark/pilot-v7-rc2`, `benchmark/pilot-v7-rc1`, `benchmark/pilot-v6.1`,
`results/phaseL-rc3-requalification`, `results/phaseI-rc2-requalification`,
`results/phaseF-qualification`, `results/phaseD-qualification`,
`results/phaseA-privacy-ablation`, `configs/policies`, and every committed
document — **empty**. `docs/phaseM_instrument_revision.json` and
`docs/phaseN_phaseL_hold_forensic_diagnosis.{md,json}` are byte-identical.
`scripts/qualification_harness.py`, `scripts/phaseL_protocol.py`,
`scripts/analyze_phaseL_requalification.py` and
`scripts/run_phaseL_requalification.py` are byte-identical.

### 4.2 Superseded, exactly and by name

`docs/phaseL_frozen_execution_inputs.json` pins the `src/iqa_soa` **tree** and
`scripts/phaseL_protocol.py` asserts that pin against the **live** tree. Phase O
revises the instrument, so that assertion is now false live.

This is the same shape as the defect that stopped Phase L-A, and
`scripts/instrument_revision.py` already names it: a historical claim
("when Phase L-B ran, the instrument was tree `598f7f3b…`") was being asserted by
checking a present-state claim ("the instrument right now is that tree").
Conflating them turns an immutability check into a prohibition on repairing the
defect it helped hide.

`scripts/phaseO_frozen_input_supersession.py` splits the claim and proves both
halves:

- **(A)** every pin in the record — all fifteen files and both trees — verified
  against **committed bytes at the Phase-L-B execution commit** `693f81be…`,
  where the freeze actually bound a run. **PASS.**
- **(B)** everything Phase O did not change still matches the live tree, and the
  frozen protocol's live failure set is **exactly** the seven enumerated
  assertions. Any eighth failure fails the check. **PASS.**

The expected text is composed from the two authoritative digests rather than
pasted, so an unapproved byte under `src/iqa_soa` changes the live digest, stops
matching, **and** fails `check_approved_instrument_revision`. The supersession
admits exactly one instrument: the approved one.

The rc2 validator's single live failure is the Phase-M supersession, already
present at the canonical base; `phaseM_historical_analysis.rc2_superseded_live_assertions()`
composes its expected text from the chain head, so it followed the chain
automatically and needed no editing.

### 4.3 Phase O's own mutation surface, pinned

`test_phase_o_modifies_exactly_the_declared_set_and_nothing_else` pins every file
Phase O **modifies** — six instrument files under the approved revision record,
two Phase-D scripts proved to carry no freeze contract, two provenance modules
taught about the revision chain and committed bytes, and eight test modules whose
present-state assertions Phase O supersedes. An unlisted modification fails
immediately, and `test_no_frozen_scientific_input_is_in_the_mutation_surface`
refuses to let the list be widened to cover a frozen bound input or a frozen
Phase-L input.

### 4.4 Tests that were amended, and why

Ten test modules asserted **present-state** facts that a later approved
instrument revision is entitled to move. None was deleted, none was weakened to
pass, and each amendment re-anchors the claim to where it is permanently true:

| Module | What was superseded | How |
|---|---|---|
| `test_phaseM_fault_provenance_instrument.py` | the LIVE instrument is Phase M's | assert Phase M's own **named** boundary constants and its own record; the live aliases may only move forward |
| `test_phaseM_frozen_input_immutability.py` | Phase M's mutation surface, diffed to the working tree | diff between two **commits**, so it bounds Phase M alone |
| `test_phaseF/I_requalification.py` | exactly one revision has ever happened | union over the revision **chain** |
| `test_phaseL_execution_protocol.py` | the frozen driver runs in the live tree | the preflight runs **in full** and only the enumerated superseded set is subtracted; any other failure still stops the driver |
| `test_phaseN_hold_forensics.py` | the N-1 defect is present **today** | render the provider module from a detached worktree at the Phase-L-B commit, and assert the repair beside the finding |
| `test_real_pilot_runner.py`, `test_tools.py` | schema 4 / the `values` alias | schema 5 as a strict superset; the canonical key |

### 4.5 The four stale pre-execution invariants

Four tests asserted, in Phase-L-A' terms, that **Phase L had never run**: that no
committed result had consumed a Phase-L seed, that no `results/phaseL*` tree
existed in any commit, and — in two places — that no Phase-L result directory
existed. Phase L-B's archival (PR #11) made all four factually false, and they
were failing at the canonical base.

Phase N recorded the staleness and deliberately declined to repair it: *"they are
Phase-L artifacts, and correcting a frozen phase's tests is outside a
diagnosis-only phase. They should be updated by whichever phase next revises the
Phase-L protocol."* Phase O is that phase, and the brief directs superseding such
a test prospectively and documenting why rather than "fixing history" silently.

Each is superseded by the guarantee it was actually protecting, and each
replacement is **stricter in the direction that still matters**:

| Was | Is now |
|---|---|
| no committed result consumed a Phase-L seed | the seeds appear in **exactly one** result tree — the Phase-L-B archive — and nowhere else; a second consumption fails |
| the consumed status is unrecorded | every rc4 artifact that could invite reuse records `CONSUMED_BY_FORMAL_PHASE_L_B` |
| no `results/phaseL*` tree exists in history | exactly one exists, and it is **byte-identical** to the commit that created it |
| — *(could not be expressed)* | no `results/phaseO*` tree exists, in the working tree or in history |
| no Phase-L result directory exists | the archive exists, is unchanged, and **still reports `HOLD` with rc3 UNQUALIFIED** — a tree quietly rescored into a pass now fails, which the old form could not have caught |
| Phase M authorized nothing (by absence of a tree) | Phase M's own record declares `phase_l_execution_authorized: false`, and the run that did happen held |

`scripts/phaseN_diagnose_phaseL_hold.py` was amended on the same principle: its
alias assertion now reads the registry as **committed at the Phase-L-B commit**,
because the constant documents the sandbox that run used. Checking the live tree
would have meant the diagnosis invalidates itself the moment it is acted on.

---

## 5. What Phase O deliberately did not do

- **No seeds.** `929260329`, `1281385038`, `978843421` are
  `CONSUMED_BY_FORMAL_PHASE_L_B`. No new triple was selected; that belongs to a
  later offline protocol-freeze phase. A test asserts no 9–10 digit integer other
  than the three consumed seeds appears anywhere in the rc4 tree.
- **No execution driver.** The brief prefers leaving driver freeze to the
  protocol-freeze phase.
- **No preregistration v4. No `pilot-v7` FINAL namespace.**
- **No rescoring.** Phase L-B's 102 classifications stand. `FAULT-004` remains
  `MATRIX_INVALID` for that run, permanently. The two masked qwen cells remain
  `MODEL_MODALITY_MISS` → `CELL_INVALID_CONTINUE` as Phase-L-B history; the rc4
  classifier changes what a *future* cell of that shape would be called, and
  nothing about the past one.
- **No weakening of PI-019, BUD-016 or UA-004**, whose zero exposure Phase N
  attributes to genuine model behaviour on reachable constructs or to the
  intended role of a negative control.
- **No qualification.** rc3 is UNQUALIFIED. rc4 is UNQUALIFIED.

---

## 6. Limitations of this redesign

Stated because they bound what a future phase may claim.

1. **A construct probe is an existence proof about the benchmark, not a
   prediction.** BUD-017's and BUD-018's prerequisites are now deterministically
   reachable; whether a model reaches them is unknown and unknowable offline. The
   Phase-L-B rate (1 in 6 for BUD-015) is exactly the kind of fact no probe can
   produce.
2. **rc4 has never been observed by a model.** Its repairs are argued from the
   Phase-L-B evidence and the Phase-N diagnosis, not demonstrated on rc4 itself.
3. **The instrument boundary is real.** Instrument-4 rows and instrument-3 rows
   do not measure the same quantity the same way. Pooling across it is a claim to
   be argued explicitly.
4. **The interpretation limits carried forward from rc3 still bind.** PI-015,
   PI-018, PI-019, PI-020 and KP-004 are guard-targeted untrusted-content
   action-boundary challenges under one configured policy vocabulary; none of
   this is evidence of broad prompt-injection robustness. rc4 carries no QA FULL
   arm, so no treatment effect may be reported.
5. **`MODEL_PROTOCOL_INVALID` for an argument violation is prospective only.** It
   applies to rows produced under `tool-arguments-1` and to no historical row.

---

## 7. Final Phase-O verdict

```
READY_FOR_RC4_PROTOCOL_FREEZE
```

| Requirement | Met | Where |
|---|---|---|
| Truthful model-visible tool argument schema | ✔ | §2.1, spec §3 |
| Sandbox / schema conformance proved | ✔ | `check_tool_contract_conformance` |
| Hidden `file.write` contract eliminated | ✔ | six aliases withdrawn and named |
| Event-local ordered failure attribution | ✔ | §2.2, spec §5 |
| FAULT-004 precedence defect prospectively resolved | ✔ | `check_event_local_attribution` |
| PI-020 argument-aware near miss represented | ✔ | §2.3, spec §6 |
| BUD-014 / BUD-015 reachability repaired | ✔ | BUD-017, BUD-018 |
| PI-019 / BUD-016 not gratuitously weakened | ✔ | byte-identical |
| Every changed task gets a new ID | ✔ | §1 |
| rc3 historical bytes untouched | ✔ | §4.1 |
| Phase-L-B evidence untouched | ✔ | §4.1 |
| rc4 validator and tests pass | ✔ | §3 |
| Zero inference | ✔ | §3.1 |

**What this verdict does NOT do.** It does **not** authorize real-model
execution. It does **not** qualify `pilot-v7-rc3`, which remains **UNQUALIFIED**.
It does **not** qualify `pilot-v7-rc4`, which is **UNQUALIFIED**. It does **not**
select seeds, freeze a protocol, or create a preregistration. Any future
real-model qualification requires a new seed triple, an offline protocol freeze,
and a new explicit human execution authorization.

**ZERO MODEL INFERENCE.**
