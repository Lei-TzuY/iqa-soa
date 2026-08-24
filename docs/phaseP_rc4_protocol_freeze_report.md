# Phase P — pilot-v7-rc4 qualification protocol freeze report

**Verdict: `READY_FOR_PHASE_P_R2_ADVERSARIAL_REREVIEW`**

READY does **not** authorize real-model execution. It means only that the Phase-P
implementation may undergo an independent adversarial rereview.

Audit history: first rereview **PASS** -> P-R1 frozen-input bypass found ->
P-R1 repair -> P-R2 residual authorization / evidence-root blockers found ->
P-R2 repair (§11).

| | |
|---|---|
| Canonical start | `f65ee4980813b465431c5f7d75a0d00db87785b6` (`HEAD == main == origin/main`, clean tree) |
| Branch | `phase-p/rc4-qualification-protocol-freeze` |
| Predecessor | Phase O / O-R1, PR #13, MERGED |
| Benchmark | `pilot-v7-rc4` — release-candidate, **UNQUALIFIED**, OFFLINE-DESIGNED, **NOT FINAL** |
| Model inference performed | **none** |
| Ollama contact | **none** |
| Provider contact | **none** |
| rc4 bytes changed | **none** |
| Execution authorized | **none** |

This phase is additive. It adds a protocol, a driver that refuses to run, an
analyzer, a seed derivation, a hash record and a test suite. It changes no
accepted artifact.

---

## 1. What was frozen

| Item | Value |
|---|---|
| Matrix | 17 tasks × 2 arms × 3 seeds × QA OFF = **102 cells** |
| Task order | the accepted rc4 manifest's own `selected_task_ids` order |
| Arm order | `(qwen, mistral)` |
| Seed order | `(1197050110, 1904689056, 1133353488)` |
| Schedule ordering | arm-major → task-major → seed-minor |
| Schedule digest | `26b9b65bda1f580088a407ff03cae7ca9fe8d1d8c0a46f4e674dfdbaa8f4d130` |
| Benchmark manifest | `e8904b213cc4ffe814604ac10ec623596147f1ad4020c66e49e7f35a1e782a14` |
| Instrument | version `4`, raw schema `5` |
| Argument contract | `tool-arguments-1`, digest `eedff86135a533a21e19caef4ba9b05334bf54040aa38486e706e28716bd4634` |
| Native tool adapter | `native-tools-adapter-3` |
| Harness | `rc4-harness-2` |
| Scoring vocabulary | `rc4-scoring-vocabulary-1` |
| Analyzer | `phase-p-rc4-analyzer-1` |
| Runtime | Ollama `0.32.13` |
| Retries | `0` |
| Results namespace | `results/phaseP-rc4-qualification/` (**not created**) |
| Human gate | `--execute-real-model` **AND** `IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED` |

## 2. Seed derivation

`scripts/phaseP_derive_seeds.py`, algorithm `phase-p-seed-derivation-1`:

```
material  = <canonical base SHA> + "|" + <domain separator>
          + "|seed-" + str(ordinal) + "|counter-" + str(counter)
digest    = SHA256(material encoded UTF-8)
candidate = int.from_bytes(digest[:4], "big") & 0x7fffffff
```

Domain separator: `IQA-SOA|phase-p|pilot-v7-rc4|qa-off-real-model-qualification`

Deterministic rejection rule: accept the first candidate that is non-zero, is not
a forbidden historical seed and does not duplicate a seed already accepted for a
lower ordinal; otherwise record the rejection and increment the counter. All
three ordinals were accepted at `counter-0`; no rejection occurred.

| Ordinal | Counter | SHA-256 | Seed |
|---|---|---|---|
| 1 | 0 | `c75988fe1f36486a636538b80cfbaa7db953c6485187aee8b7f20067af3d33f4` | `1197050110` |
| 2 | 0 | `71873fa01d97fcb25ad210d41ae5387dabf64f80bd5bd9d28e8d379e4cd46d9b` | `1904689056` |
| 3 | 0 | `c38d9a109944cd2016720388485f2456d4947ddf3f372f6a79f0c4ed8cffe757` | `1133353488` |

**Proof the triple is new.** `scan_committed_seeds` reads every git-TRACKED file
under `configs/`, `results/`, `docs/`, `benchmark/` and `schemas/`: the committed
configurations, the committed `*.jsonl` raw rows and the committed `*.json`
artifacts. The file set is enumerated with `git ls-files`, not by walking the
filesystem — see §9. It finds exactly eight prior seeds —
`1729, 2718, 3141, 5772, 8119, 929260329, 1281385038, 978843421` — all covered by
the forbidden set, and none of them equal to a Phase-P seed. The scan is scoped
to sources OUTSIDE Phase P's own three declared artifacts, and the exclusion cuts
both ways: a Phase-P seed appearing anywhere else is reported as a leak.

The Phase-L triple's status remains `CONSUMED_BY_FORMAL_PHASE_L_B`.

## 3. Model / provider / runtime pins, from committed evidence

Every pin is quoted from committed artifacts and required to be **unanimous**
across five independent sources (§8 of the plan). Verified agreement:

- `qwen3.5:27b` → `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`, policy `none`
- `mistral-small3.2:24b` → `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b`, policy `trailing_user`
- protocol `native_tools`, runtime `0.32.13`

Phase D is recorded as an authority on digest, runtime and protocol but
explicitly **excluded** as an authority on arm policy, because it deliberately ran
the same model under both policies in order to qualify the policy repair itself.
The exclusion is machine-readable (`ARM_POLICY_EVIDENCE_PATHS`) and a test asserts
the premise that justifies it.

No live metadata request was made by Phase P.

## 4. Fail-closed properties, each with a behavioural test

| Property | Enforced by |
|---|---|
| Both gates required; neither alone suffices; exact case | `human_gate_refusal` |
| Gate evaluated before preflight, config, provider, probe, directory | `driver.main` ordering |
| Contract drift refused per row, ahead of every scientific branch | `protocol.contract_drift` → `FROZEN_ARTIFACT_MISMATCH`/`IMMEDIATE_STOP` |
| Identity drift, missing or `None` refused | `harness.bind_row_to_cell` |
| Driver never overwrites a conflicting identity value | `setdefault` in `stamp_frozen_identity` |
| Transported observations are never stamped as constants | `MANIFEST_TRANSPORTED_FIELDS` |
| Both arms probed before either runs; 0 cells on `ENVIRONMENT_HOLD` | `metadata_preflight` |
| No pull/download/update/retag/repair/substitute | absence of any write endpoint, asserted statically |
| Malformed schema-5 telemetry → `INSTRUMENT_DEFECT` | Phase-O-R1 strict reader |
| Stop at final cell of arm 1 → arm 2 executes zero cells | `StopController.cells()` |
| Offending row preserved; no resume, replace or delete | append-before-classify |
| Pre-existing output → `PROTOCOL_DEVIATION`, before the probe | `check_output_namespace` |
| Lost evidence never scored as zero exposure | `_trace_events` |
| Driver/analyzer disagreement → blocking `INSTRUMENT_DEFECT` | `check_classification_ledger` |
| No confirmatory quantity may be emitted | `check_reporting_scope` |

## 5. Validation

| Check | Result |
|---|---|
| Phase-P focused suite (`tests/integration/test_phaseP_execution_protocol.py`) | **200 passed** |
| Full `pytest` | **1585 passed** (fresh worktree at `89c056e`, 18m02s) |
| `mypy src` | clean (48 files) |
| `MYPYPATH=src mypy --strict` over the five new Phase-P scripts | clean |
| `qualification_harness_v2.py` self-check | PASS |
| `validate_pilot_v7_rc4.py` | PASS |
| `build_pilot_v7_rc4.py --check` | PASS |
| `phaseO_rc4_construct_probe.py` | PASS |
| `rc4_scoring_vocabulary.py` | PASS |
| `instrument_revision.py` (chain: Phase-K → M → O) | PASS |
| `phaseO_frozen_input_supersession.py` | PASS |
| `phaseM_frozen_input_audit.py` | PASS (12 bound inputs, 7 sidecars — the Phase-P plan sidecar included) |
| `phaseM_historical_analysis.py` | PASS |
| `phaseN_diagnose_phaseL_hold.py --verify` | PASS |
| `validate_pilot_v7_rc3.py` | PASS |
| `phaseP_derive_seeds.py --check` | PASS |
| `phaseP_write_frozen_inputs.py --check` | PASS |
| `run_phaseP_rc4_qualification.py --verify-frozen-inputs` | PASS |
| `analyze_phaseP_rc4_qualification.py --verify-scoring-plan` | PASS |
| Fresh detached worktree at `89c056e`, full battery | PASS — 1585 passed, every script above green, `mypy` clean, and `results/phaseP-rc4-qualification/` absent (see §9) |

## 6. Zero-inference / zero-Ollama / zero-provider proof

The claim is made precisely, not by asserting that one hook wraps everything.

**Runtime guard, for the code paths it actually covers.** `no_network()` replaces
`socket.socket.connect` and `socket.create_connection` for the duration of a
block and records every attempt. It is applied to the offline preflight, the
analyzer's scoring-plan derivation, the seed derivation, every closed-gate
refusal, and a complete 102-cell gated run with injected seams. **Zero attempts
recorded in all of them.**

**Anti-vacuity.** `test_the_network_guard_is_not_vacuous` deliberately attempts
two connections — to `127.0.0.1:9`, a closed loopback port — and asserts the guard
refuses and records both. This is a **loopback anti-vacuity probe**, reported here
separately from real contact: it reaches no provider, no Ollama runtime and no
model, and the guard refuses before any packet is sent. Without it, "zero events"
would be unfalsifiable.

**Static inspection, for the paths a socket guard does not cover.**
`scripts/phaseP_protocol.py`, `scripts/phaseP_derive_seeds.py`,
`scripts/phaseP_write_frozen_inputs.py` and
`scripts/analyze_phaseP_rc4_qualification.py` contain no `urlopen`, no
`requests.`, no `httpx.`, no `socket.`, and no generation endpoint. The driver
alone may name a runtime endpoint; its executable string constants (docstrings
excluded by AST) contain `/api/version` and `/api/tags` and contain none of
`/api/chat`, `/api/generate`, `chat/completions`, `/api/pull`, `/api/create`,
`/api/copy`, `/api/delete` or `/api/push`.

**Summary.** Excluding the two deliberate loopback anti-vacuity probes above,
Phase-P validation caused **zero model inference, zero Ollama contact and zero
provider contact.**

## 7. Historical immutability

`git diff f65ee4980813b465431c5f7d75a0d00db87785b6 -- benchmark/` is **empty**.
No file under `results/`, `src/`, `benchmark/`, `docs/phaseL_*`, `docs/phaseM_*`,
`docs/phaseN_*`, `docs/phaseO_*`, `scripts/qualification_harness.py`,
`scripts/qualification_harness_v2.py`, `scripts/rc4_scoring_vocabulary.py`,
`scripts/analyze_phaseL_requalification.py` or `scripts/phaseL_protocol.py` was
modified. Both facts are asserted by tests, not only by inspection.

No historical verdict was reinterpreted. `pilot-v7-rc3` remains `UNQUALIFIED`,
Phase L-B remains `HOLD`, and all 102 of its classifications remain binding.

## 8. What Phase P did not do

No model inference. No Ollama contact. No provider contact. No rc4 cell executed.
No empirical qualification result created. rc4 not marked qualified. pilot-v7 not
made final. No confirmatory result, no QA FULL, no PARTIAL, no ablation, no
confirmatory matrix. The human gate was never set. The results namespace was never
created.

`pilot-v7-rc4` remains **UNQUALIFIED**, **release-candidate**,
**OFFLINE-DESIGNED** and **NOT FINAL**.

## 9. A defect the fresh-worktree run caught, and its repair

The first fresh detached-worktree run **failed**, on
`test_the_derivation_is_a_pure_function_of_the_base_commit`. That is what the run
is for, and the failure is recorded here rather than quietly fixed.

**Cause.** `scan_committed_seeds` enumerated files by walking the filesystem.
This repository gitignores several large local result directories —
`results/raw/`, `results/real-pilot/`, `results/processed/`,
`results/phaseA-privacy-ablation/` and `results/pilot-v6.1-stage1/` — so the
development tree contained hundreds of untracked run artifacts that a clean
checkout does not. The derivation record's `committed_seeds_discovered` therefore
listed 111 sources for seed `1729` in the development tree and 34 in a clean
checkout of the same commit.

**Why it mattered.** Two claims were false as written. The record was not
reproducible from the base SHA, and the completeness proof for the forbidden
seed set was a statement about one machine's disk rather than about committed
history — exactly the class of defect this repository's provenance machinery
exists to prevent.

**What it did not affect.** The seed triple itself is a pure function of the base
SHA and the domain separator and never depended on the scan. The *set* of
discovered seeds was identical either way — the same eight — because the
committed Phase-D, Phase-F, Phase-I and Phase-L results carry all of them. No
scientific conclusion changes.

**Repair.** `tracked_files` enumerates the file set with `git ls-files`, and
`scan_committed_seeds` reads only what git tracks. Git is required: a tree in
which git cannot be consulted cannot support a claim about committed history at
all, so the failure is raised rather than degraded into a partial scan. Two
regression tests were added — one asserting every scanned source is tracked and
that an untracked file naming a seed changes nothing, one asserting two scans of
the same commit agree.

The final battery was then re-run in a fresh detached worktree at the head
commit.

## 10. P-R1 — the frozen-input binding blocker, found after a PASS rereview

The first independent adversarial rereview of this phase returned **PASS**. A
later, independent look found a blocker it had missed, and the phase was
reopened rather than merged. This section records that sequence, because the
sequence is part of the evidence.

### 10.1 The blocker

Pinning a file by SHA-256 proves the canonical **tree** is intact. It does not
prove a given **invocation** was pointed at that tree.

The driver accepted `--config`, `--manifest` and `--output-root`; the analyzer
accepted `--manifest` and `--contract`. After the canonical
`offline_preflight()` succeeded, `protocol.load_benchmark(manifest_path)`
verified only `benchmark_version == pilot-v7-rc4` and `len(cases) == 17`, and
`check_experiment_configuration` verified only that a config declared the frozen
seeds, treatment and repetitions. Those are properties, not identity.

Consequently a caller could pass every canonical check and then execute or score
a **different experiment**:

* a copied manifest with the task order changed, or with one case binding
  changed, or claiming a different byte digest for a case — all structurally
  valid, all 17 tasks, all `pilot-v7-rc4`;
* a copied `phaseP-qualification.yaml` with `max_agent_steps` doubled — a runtime
  setting rc4's budget tasks depend on for over-budget proposals to remain
  observable;
* an arbitrary `--output-root`, producing an "official" run in a namespace no
  downstream reader knows, whose append-only precondition was checked against the
  wrong directory;
* an alternate qualification contract — including one that would make
  qualification **easier**.

And the emitted provenance would still have described the canonical artifacts:
`_write_run_manifest` recorded `protocol.protocol_summary()`, which is derived
from the canonical manifest, and the analyzer payload recorded
`qualification_contract_sha256` by hashing the **canonical** contract path
regardless of which contract it had scored. That is a provenance falsehood, and
it violates frozen-input closure, prospective integrity and reproducibility.

Nothing was executed under the defect: Phase P has never run a cell.

### 10.2 The repair

Scientific-input binding only. rc4 was not redesigned, no seed changed, no model
ran and no provider was contacted. See
`docs/phaseP_rc4_real_model_qualification_plan.md` §24b for the full statement.

Every input a caller can name is proven twice — resolved canonical **path**
equality and SHA-256 equality with the digest the frozen-input record accepted —
in three independent places: the driver CLI (immediately after the human gate,
before the preflight), `phaseP_protocol.load_benchmark` (on its own argument),
and all three analyzer entry points. `--output-root` is bound to
`results/phaseP-rc4-qualification/`. The four bound artifacts are
`configs/phaseP-qualification.yaml`, `configs/phaseP-models.yaml`,
`benchmark/pilot-v7-rc4/manifest.json` and
`benchmark/pilot-v7-rc4/qualification-contract.json`.

Provenance is now derived from what was read: the run manifest carries an
`execution_inputs` block hashing each input as read with a per-input
`is_canonical` verdict and a single `official_phase_p_execution` boolean; the
driver refuses to proceed unless `protocol_summary()` agrees with the schedule it
would execute on manifest digest, task order, cell count and schedule digest; and
the analyzer hashes the contract it bound rather than a hard-coded path.

### 10.3 The adversarial regressions added

| # | Adversarial case | Refusal |
|---|---|---|
| A | alternate manifest, same `benchmark_version`, same 17 tasks | `FROZEN_ARTIFACT_MISMATCH`; 0 probes, 0 cells, no result directory |
| B | alternate manifest, only the task **order** changed | same |
| C | alternate manifest, one case **binding** changed | same |
| D | alternate contract with a scoring clause changed | analyzer refuses before any plan is derived or row read |
| E | alternate contract that would make qualification **easier** | same — and no `PASS_RC4_QUALIFIED_FOR_QA_OFF_USE` is emitted |
| F | Phase-P-looking config, frozen seeds/treatment, changed runtime setting | `FROZEN_ARTIFACT_MISMATCH` before any probe |
| G | alternate `--output-root` on the production CLI | `PROTOCOL_DEVIATION`; refused as a noncanonical Phase-P execution |
| H | the canonical paths | continue to pass every offline check |

The internal seam the offline suite drives, `execute_bound_run`, leaves
**`output_root` alone** unbound: it binds the execution config on entry, the
manifest through `load_benchmark` and the model config through
`check_experiment_configuration`, none of which depends on `main()` having
checked first. A test hands it a byte-identical copy of the frozen config and of
the frozen manifest and requires both to be refused.

Two further separations are tested in isolation so neither half of the binding
can silently stop working: a **byte-identical copy** placed elsewhere is refused
by the path proof, and **edited bytes at the canonical relative path** are
refused by the digest proof. E carries an explicit anti-vacuity test proving the
"easier" contract would in fact have flipped the clean synthetic matrix's `HOLD`
— it reclassifies exactly the tasks that hold it — so the refusal is not merely a
rejection of a malformed file.

### 10.4 Non-blocking rereview findings, also closed

**Causal-effect key forms.** `FORBIDDEN_REPORT_TERMS` matches token runs, so
`qa_effect` did not cover `qa_full_effect` and nothing covered
`confirmatory_result`. Added: `qa_full_effect`, `qa_full_effectiveness`,
`qa_full_vs_off`, `full_vs_off`, `causal_effect`, `treatment_estimate`,
`confirmatory_result`, `confirmatory_effect`, `confirmatory_finding` and
`confirmatory_verdict`. Each is a multi-token run on purpose: the bare tokens
`confirmatory` and `causal` appear in keys this phase **must** emit
(`authorizes_confirmatory_execution`, the contract's causal-prerequisite
vocabulary), and the declaration-of-absence exemption
(`reports_no_qa_treatment_effect`, `no_qa_effect_claim`) is asserted to survive.

**Seed-scan docstring scope.** `scripts/phaseP_derive_seeds.py` claimed
`scan_committed_seeds` reports "every seed the repository has ever recorded". The
mechanism is `git ls-files` at the current commit, so the accurate claim is the
current committed tree. The docstring now says so, and a test asserts the old
wording is gone.

The residual gap was closed **independently** rather than by weakening the claim.
A full-history scan read every blob ever committed under the scan roots —
`configs/`, `results/`, `docs/`, `benchmark/`, `schemas/` — via
`git rev-list --objects --all` and `git cat-file`, applying the same extraction
the module uses:

| Full-history seed scan | Figure |
|---|---|
| historical blobs examined | **686** |
| distinct seed values found | **11** |
| values outside `FORBIDDEN_SEEDS` ∪ the Phase-P triple | **0** |

The eight forbidden seeds and the three Phase-P seeds account for all eleven. The
scan reads git object bytes only; it ran no model and contacted nothing.

### 10.5 P-R1 validation

Strictly offline. Zero model inference, zero Ollama contact, zero provider
contact.

| Check | Result |
|---|---|
| Phase-P focused suite | **229 passed** (200 before P-R1; +29 binding regressions) |
| Full `pytest` | **1614 passed** (1585 before P-R1) |
| `mypy src` | clean (48 files) |
| `MYPYPATH=src mypy --strict` over all five Phase-P scripts | clean |
| every validator listed in §5 | PASS |
| `run_phaseP_rc4_qualification.py --verify-frozen-inputs` | PASS |
| `analyze_phaseP_rc4_qualification.py --verify-scoring-plan` | PASS |
| `phaseP_write_frozen_inputs.py --check` | PASS |
| Fresh detached worktree at the P-R1 commit, full battery | see §10.6 |

### 10.6 Fresh detached-worktree battery at the P-R1 commit

Run at `68283af3227c08d192526b2a2eba2f0a2247c3cb`, in a worktree checked out
clean (`0 modified/untracked` at start), and recorded in the immediately
following commit — exactly as the §9 battery was, and for the same reason: a
report cannot contain the results of a run performed at a commit that already
contains those results. The freeze report is not itself a frozen input, so
recording the figures changes no hash the driver asserts.

| Check | Result |
|---|---|
| Phase-P focused suite | **229 passed** (3m25s) |
| Full `pytest` | **1614 passed** (18m20s) |
| `mypy src` | clean (48 files) |
| `mypy --strict` over the five Phase-P scripts | clean (5 files) |
| all 15 validator / `--check` / `--verify` invocations | **PASS** |

Immutability vs the Phase-P canonical base `f65ee49`, files changed:

| Path | Changed |
|---|---|
| `benchmark/` | **0** |
| `src/` | **0** |
| `results/` | **0** |
| `docs/phaseL_*`, `docs/phaseM_*`, `docs/phaseN_*`, `docs/phaseO_*` | **0** |
| `scripts/qualification_harness.py`, `scripts/qualification_harness_v2.py` | **0** |
| `scripts/rc4_scoring_vocabulary.py` | **0** |
| `scripts/analyze_phaseL_requalification.py`, `scripts/phaseL_protocol.py` | **0** |

Frozen quantities, recomputed from the clean checkout:

| | |
|---|---|
| seeds | `[1197050110, 1904689056, 1133353488]` |
| planned cells | `102` |
| schedule digest | `26b9b65bda1f580088a407ff03cae7ca9fe8d1d8c0a46f4e674dfdbaa8f4d130` |
| rc4 manifest sha256 | `e8904b213cc4ffe814604ac10ec623596147f1ad4020c66e49e7f35a1e782a14` |

All four are byte-identical to the original freeze: P-R1 changed no seed, no
schedule and no benchmark byte.

`results/phaseP-rc4-qualification/`: **ABSENT**. The tree was still clean after
the entire battery — the run created no results namespace and left no artifact
behind. Zero model inference, zero Ollama contact, zero provider contact.

### 10.7 Status

P-R1 authorizes another independent adversarial rereview and nothing else.
`pilot-v7-rc4` remains **UNQUALIFIED**, **release-candidate**,
**OFFLINE-DESIGNED** and **NOT FINAL**. No cell has been executed, the human gate
has never been set, and `results/phaseP-rc4-qualification/` does not exist.

---

## 11. P-R2 — two residual blockers, found after the P-R1 repair

The P-R1 repair was itself rereviewed, and a further independent look found two
blockers it had not closed. The phase was reopened again rather than merged. The
audit history now reads:

```
Phase P
  -> first independent rereview: PASS
  -> P-R1 frozen-input bypass found (the PASS had missed it)
  -> P-R1 repair
  -> P-R2 residual authorization / evidence-root blockers found
  -> P-R2 repair                                   <- this section
```

Both blockers have the same shape, and it is worth naming: **P-R1 bound what a
caller could NAME and left unbound what a caller could BE.** The scientific
inputs were proved by path and digest, and the two things that decide whether a
run is an official Phase-P run at all — the authority to execute it, and the
namespace its evidence lives in — were left to caller discipline and to a
reported boolean.

### 11.1 Blocker 1 — the internal real-model path bypassed the human gate

`execute_bound_run` was real-model capable, and it machine-enforced no gate:

```python
def execute_bound_run(*, config_path, manifest_path, output_root, env,
                      probe=None, execute_cell=None) -> int:
    ...
    environment_failures, runtime_metadata = metadata_preflight(
        probe or probe_ollama_metadata)          # <- contacts the live runtime
    ...
    execute_cell=execute_cell or make_cell_executor(...)   # <- real inference
```

`probe=None` resolved to `probe_ollama_metadata`, which issues `/api/version` and
`/api/tags` against the local runtime. `execute_cell=None` resolved to the real
runner-backed executor, which spends inference on all 102 cells. The function
required `--execute-real-model` nowhere, required
`IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED` nowhere, and read the environment only to
check that a provider credential was present. Its docstring said `main()` was its
only production caller.

**A docstring is not a control.** Any Python caller that skipped `main()` —
`import run_phaseP_rc4_qualification as d; d.execute_bound_run(...)` — reached the
live runtime and the real frozen schedule having proved neither half of the dual
gate. The invariant *real-model execution requires both human gates* was a
property of one caller, not of the execution path.

### 11.2 Repair 1 — the authority is an object

```
NO DUAL GATE      -> NO CAPABILITY
NO CAPABILITY     -> NO REAL METADATA PROBE
                  -> NO REAL PROVIDER CREATION
                  -> NO REAL MODEL EXECUTION
```

**`RealExecutionAuthorization`** is a capability, and it cannot be forged at the
call site. Its constructor demands a module-private sentinel **by identity** — so
passing `True`, `None`, `"AUTHORIZED"` or a fresh `object()` as the token raises
— **and** independently re-evaluates
`human_gate_refusal` against the environment it is handed — so even a caller
holding the token cannot mint one for an environment without
`IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED`. `verify()` re-proves both halves at USE
time, so a grant cannot be minted under an open gate and carried into a context
that no longer authorizes anything. Its `repr` renders no environment, because
the environment carries the provider credential.

**`grant_real_execution_authorization(...)`** is the only thing that mints one,
and it mints one only through that constructor. The sentinel is module-private
and absent from `__all__`.

**`execute_authorized_real_run(*, authorization)`** is the **only** function in
the module that may select `probe_ollama_metadata` or construct the real
executor. It requires the capability, re-verifies it, and takes **nothing else**:
it binds the frozen config, the frozen benchmark manifest and the frozen
`results/phaseP-rc4-qualification` namespace itself, from `phaseP_protocol`, so
it depends on nothing a caller passes. An unauthorized call **raises**
`UnauthorizedRealExecution` — it does not return an exit code, because no run
happened and an exit code is a result.

**`execute_offline_bound_run(...)`** is a different function, and it is what the
offline suite drives. It is structurally incapable of a real run:

| Guard | Refuses |
|---|---|
| `probe` and `execute_cell` are required, no defaults | a missing injection resolving into a real one |
| `probe is _REAL_METADATA_PROBE` (bound at import) | the real probe laundered in through the injection point |
| the `REAL_EXECUTOR_MARKER` every `make_cell_executor` product carries | the real executor, likewise |
| `protocol.is_canonical_results_root(output_root)` | synthetic evidence occupying the official namespace |

**`main()`** lost its injection seam entirely: `probe` and `execute_cell` are gone
from its signature. It proves both gates, mints the capability, and hands it on.

The shared core `_drive_bound_run` takes `probe` and a `make_executor` **factory**
as required arguments, so there is no `None` anywhere for it to resolve into a
real-model default.

### 11.3 Blocker 2 — a noncanonical evidence root could receive a qualified verdict

P-R1 bound the two **scientific inputs**. The **evidence root** was not an input —
it is the run being read — so it was not bound. `analyze(root, ...)` read whatever
directory it was handed and merely *reported*:

```json
"analyzed_canonical_results_namespace": false
```

That flag took no part in `blocking_failures` and no part in the verdict. A
complete synthetic 102-cell matrix in a temporary directory that satisfied every
scientific gate could therefore be handed
`PASS_RC4_QUALIFIED_FOR_QA_OFF_USE` and `EXIT_OK`, with the warning printed
harmlessly beside it. **A warning that coexists with a PASS is not a control.**

This was not hypothetical: the P-R2 fixture `qualifying_phase_p_run` is exactly
such a matrix, and under the pre-repair analyzer it produced that verdict.

### 11.4 Repair 2 — two functions, two disjoint verdict vocabularies

**`analyze_official_qualification(root=None, ...)`** — the only path that can emit
`PASS_RC4_QUALIFIED_FOR_QA_OFF_USE`.

1. `root` is bound to `results/phaseP-rc4-qualification` by resolved canonical
   path. Anything else raises before a row is read: no payload, no verdict.
2. The path is necessary and **not sufficient**. `check_execution_provenance`
   requires the run to have recorded, in its own P-R1 `execution_inputs` block,
   that it read the frozen config, the frozen model config and the frozen
   benchmark manifest and wrote the frozen namespace.
3. That claim is **independently recomputed**, never believed. Each recorded
   `sha256` is compared against `protocol.accepted_frozen_digest(...)` — the
   digest `docs/phaseP_frozen_execution_inputs.json` accepted — each recorded
   `repository_relative_path` against the canonical relative path, and the
   recorded `output_root` against `protocol.canonical_results_root()`. The run's
   own `official_phase_p_execution` boolean is checked **last** and is never
   load-bearing: a manifest claiming it while recording one wrong digest is
   refused by the digest.
4. Any mismatch is `FROZEN_ARTIFACT_MISMATCH` or `INSTRUMENT_DEFECT`, is
   **blocking**, and the verdict is `HOLD`.

**`analyze_synthetic_evidence(root, ...)`** refuses the official namespace
outright and reports `TEST_ANALYSIS_PASS` / `TEST_ANALYSIS_HOLD` under
`record_kind: phase_p_synthetic_analysis`, with an explicit disclaimer. The
official verdict string appears in a synthetic payload in exactly one place: the
disclaimer that exists to say it can never be reported, and a test asserts it
appears nowhere else.

There is no third function and no flag that turns one into the other. The
producing side matches: `execute_offline_bound_run` refuses to write the official
namespace, so synthetic evidence cannot occupy the one directory an official
qualification may read.

The CLI default is unchanged — no `--root` still means the frozen namespace and
the official mode. What changed is that a noncanonical `--root` produces no
payload at all rather than an official payload with a warning inside it; scoring
one requires `--synthetic-analysis`.

### 11.5 The adversarial regressions added

33 new regressions, all offline. The unauthorized-path ones do **not** hand in a
stand-in and find it unused — they monkeypatch `probe_ollama_metadata` and
`make_cell_executor` themselves to raise if touched, so "the real seams were
never reached" is asserted against the real names.

| Brief | Regression | Asserts |
|---|---|---|
| A | `test_the_real_model_path_refuses_everything_that_is_not_the_capability` (7 forgeries, `True` first) | raises; 0 real probes; 0 cells; no namespace |
| A | `test_the_capability_cannot_be_constructed_without_the_private_token` | 4 token shapes refused |
| A | `test_a_forged_subclass_is_still_refused` | subclassing reaches the type check and stops at the token |
| B | every unauthorized path above, with the real probe/executor patched to explode | never reached |
| C | `test_the_credential_is_not_authorization` | the credential opens nothing |
| D | `test_the_human_environment_alone_is_not_authorization` | env without flag mints nothing |
| E | `test_the_cli_flag_alone_is_not_authorization` | flag without env mints nothing |
| F | `test_both_gates_mint_the_capability_and_nothing_else_happens` | a real capability is produced; the offline seam is injected at exactly that boundary; no runtime contact; credential never in `repr` |
| G | `test_the_offline_seam_works_without_authorization_and_cannot_fall_back` | 102 cells with no authorization; missing injection, real probe and real executor each refused |
| G | `test_the_offline_seam_never_writes_the_official_namespace` | the producer-side half |
| G | `test_no_offline_test_path_can_select_a_real_seam_by_default` | asserted on the **signatures** |
| G | `test_only_the_authorized_path_can_name_the_real_seams` | asserted on the **AST**: exactly one function may load each real seam's name, so no future edit can quietly add a second selector |
| — | `test_the_capability_is_reverified_at_use_and_not_merely_at_mint` | the grant carries its proof and the proof is re-checked where it is used |
| — | `test_the_grant_token_is_not_exported` | the capability is reachable; the thing that mints one is not |
| H | `test_a_noncanonical_evidence_root_never_receives_the_qualification_verdict` | see anti-vacuity below |
| I | `test_a_run_that_does_not_claim_to_be_official_is_held` | `HOLD` |
| J | `test_a_wrong_recorded_input_digest_is_held_despite_the_official_claim` (×3 inputs) | `HOLD` on the digest while the boolean still claims official |
| J | `test_a_wrong_recorded_input_path_is_held` (×3 inputs) | both halves of the binding re-proved |
| K | `test_a_noncanonical_recorded_output_namespace_is_held` (×2 shapes) | `HOLD` |
| K | `test_a_run_manifest_with_no_provenance_block_is_held` | `HOLD` |
| L | `test_a_truthful_official_run_is_eligible_for_the_normal_scientific_logic` | `PASS` on qualifying evidence, `HOLD` on zero-exposure evidence, both for scientific reasons |
| — | `test_the_synthetic_mode_can_never_read_the_official_namespace` | the modes are disjoint from both sides |
| — | `test_the_two_verdict_vocabularies_share_no_string` | a synthetic PASS is not greppable as a qualification |

**Test H is anti-vacuous, and this is the load-bearing part.** A new fixture,
`qualifying_phase_p_run`, is a complete 102-cell matrix in which **every task
qualifies**: each challenge walks its ordered prerequisite chain and then its
canonical exposure signature with a payload that satisfies its declared argument
predicate, the two count-threshold tasks cross their caps, BUD-016's exposure
witness is a proposal its own near-miss exclusion does **not** remove, both benign
controls walk their safe route, the fault opportunity binds its declared fault,
and the deliberate negative control stays at zero exposure. Each route is read off
the plan `build_scoring_plans` derives from the frozen rc4 contract; none is
invented.

The test then proves, in order:

1. the synthetic analysis of that root has **zero** blocking failures, **zero**
   unqualified tasks and verdict `TEST_ANALYSIS_PASS` — the evidence is
   scientifically complete;
2. `analyze_official_qualification` **refuses** the same root outright;
3. the CLI's official mode exits non-`EXIT_OK` and emits no `"verdict"` key at
   all;
4. the **same rows**, copied into a canonical namespace with truthful official
   provenance, produce `PASS_RC4_QUALIFIED_FOR_QA_OFF_USE`.

Step 4 is what makes step 2 mean something: what the evidence-root binding refused
was a genuine qualification, not a foregone `HOLD`.

**No official evidence was manufactured.** Tests I–L need a run that IS in the
canonical namespace, and this repository must never contain
`results/phaseP-rc4-qualification/`. Rather than write into the repository, the
*notion* of the canonical namespace is relocated to a temporary directory:
`protocol.canonical_results_root()` is the single source of that notion —
`is_canonical_results_root`, `require_canonical_results_root`, the driver's
`describe_execution_inputs` and the analyzer's `check_execution_provenance` all
reach it — so patching it moves the whole binding coherently and every assertion
under it exercises the real code path. The truthful `execution_inputs` block is
produced by the **driver's own** `describe_execution_inputs` under that relocated
namespace, not hand-written; each of tests I / J / K then introduces exactly one
lie into it.

### 11.6 Documentation cleanup

The stale `execute_bound_run` docstring — which simultaneously said "THIS
FUNCTION BINDS NOTHING" and then described the config binding it performed — is
gone with the function. Its two successors each say what they actually do, and
the plan document gained §14b and §20b.

### 11.7 P-R2 validation

Strictly offline. Zero model inference, zero Ollama contact, zero provider
contact.

| Check | Result |
|---|---|
| Phase-P focused suite | **262 passed** (229 before P-R2; +33 P-R2 regressions) |
| Full `pytest` | **1647 passed** (1614 before P-R2, 18m55s) |
| `mypy src` | clean (48 files) |
| `MYPYPATH=src mypy --strict` over all five Phase-P scripts | clean (5 files) |
| every validator listed in §5 | PASS |
| `run_phaseP_rc4_qualification.py --verify-frozen-inputs` | PASS |
| `analyze_phaseP_rc4_qualification.py --verify-scoring-plan` | PASS |
| `phaseP_write_frozen_inputs.py --check` | PASS |
| Fresh detached worktree at the P-R2 commit, full battery | see §11.8 |

### 11.8 Fresh detached-worktree battery at the P-R2 commit

To be run in a worktree checked out clean at the P-R2 implementation commit and
recorded in the immediately following commit — exactly as the §9 and §10.6
batteries were, and for the same reason: a report cannot contain the results of a
run performed at a commit that already contains those results. The freeze report
is not itself a frozen input, so recording the figures changes no hash the driver
asserts.

### 11.9 Status

P-R2 authorizes another independent adversarial rereview and nothing else.
`pilot-v7-rc4` remains **UNQUALIFIED**, **release-candidate**,
**OFFLINE-DESIGNED** and **NOT FINAL**. No cell has been executed, the human gate
has never been set, and `results/phaseP-rc4-qualification/` does not exist.
