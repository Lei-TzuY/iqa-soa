# Phase P — pilot-v7-rc4 qualification protocol freeze report

**Verdict: `READY_FOR_PHASE_P_ADVERSARIAL_REREVIEW`**

READY does **not** authorize real-model execution. It means only that the Phase-P
implementation may undergo an independent adversarial rereview.

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
| Full `pytest` | **1584 passed** |
| `mypy src` | clean (48 files) |
| `MYPYPATH=src mypy --strict` over the five new Phase-P scripts | clean |
| `qualification_harness_v2.py` self-check | PASS |
| `validate_pilot_v7_rc4.py` | PASS |
| `build_pilot_v7_rc4.py --check` | PASS |
| `phaseO_rc4_construct_probe.py` | PASS |
| `rc4_scoring_vocabulary.py` | PASS |
| `instrument_revision.py` (chain: Phase-K → M → O) | PASS |
| `phaseO_frozen_input_supersession.py` | PASS |
| `phaseM_frozen_input_audit.py` | PASS (12 bound inputs, 6 sidecars) |
| `phaseM_historical_analysis.py` | PASS |
| `phaseN_diagnose_phaseL_hold.py --verify` | PASS |
| `validate_pilot_v7_rc3.py` | PASS |
| `phaseP_derive_seeds.py --check` | PASS |
| `phaseP_write_frozen_inputs.py --check` | PASS |
| `run_phaseP_rc4_qualification.py --verify-frozen-inputs` | PASS |
| `analyze_phaseP_rc4_qualification.py --verify-scoring-plan` | PASS |
| Fresh detached worktree, full battery at the final commit | PASS (and see §9) |

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

