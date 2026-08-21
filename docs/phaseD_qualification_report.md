# Phase-D Real-Provider Instrument Qualification Report

Companion to the frozen plan `docs/phaseD_instrument_qualification_plan.md`
(SHA-256 `2896f0e0263a36ab8eb240ccfbeb2ace35057cec16e3f0fe943ed13adf5fcc2a`,
verified unchanged after the last model call).

**This is an engineering qualification smoke. It is not scientific evidence, not
confirmatory evidence, not an effect-size study, and no safety or utility claim
may be drawn from it. Its outputs must never be pooled with Stage-1, Stage-2,
Phase-A, or any future confirmatory measurement.**

---

## A. Provenance and plan hash

| Item | Value |
|------|-------|
| Qualification plan | `docs/phaseD_instrument_qualification_plan.md` |
| Plan SHA-256 (frozen before first model call) | `2896f0e0263a36ab8eb240ccfbeb2ace35057cec16e3f0fe943ed13adf5fcc2a` |
| Plan hash re-verified after last model call | OK (unchanged) |
| Approved Phase-C HEAD | `bb5460891c47d0509d8f51d9a1b936b0b7c3e53c` |
| Branch | `phase-d/instrument-qualification` |
| Freeze commit | `5950f4ded1945870628b829f1ffc411b05c42aa0` |
| `main` | `e98dd7c49a967162fa51500b67d3d4a808778e26` (unchanged) |
| Instrument version | `2` |
| Native-tool adapter version | `native-tools-adapter-2` |
| Preflight record | `results/phaseD-qualification/preflight.json` (`inference_performed: false`) |

Runtime provenance, collected before any inference call:

| Field | Mistral arm (A, B) | Qwen arm (C) |
|-------|--------------------|--------------|
| Runtime | ollama | ollama |
| Runtime version | 0.32.13 | 0.32.13 |
| Model identifier | `mistral-small3.2:24b` | `qwen3.5:27b` |
| Model digest | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` |
| Template SHA-256 | `706c4d1164f7f1bbce2a852f2bc9cfa66b98d24f79300b9034388e07fcda98c8` | `b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315` |
| Capabilities | completion, vision, **tools** | completion, vision, **tools**, thinking |
| Tool-contract policy | A: `none`; B: `trailing_user` | `none` |
| Probe error | none | none |

Model identities were resolved from the frozen Stage-1 manifests
(`results/pilot-v6.1-stage1/raw/*/manifest.json`) and confirmed against the
local Ollama tag listing. They were not guessed.

Bound Phase-D inputs (SHA-256): `DIAG-001.yaml`
`6939a4b5…46b71e54`, `configs/phaseD-diagnostic.yaml` `7f3d8929…0d28f4b9ac`,
`configs/phaseD-models.yaml` `d2b6da88…2cd632edf0`, `configs/policies/default.xml`
`256a8205…a0234ea9f63e5` (read-only reuse, unmodified).

---

## B. Exact 9-run matrix

Three experiment directories under `results/phaseD-qualification/raw/`, each
`status: complete`, `record_count: 3`, `max_total_runs: 3`,
`infrastructure_retry_limit: 0`, `experiment_kind: real_model_connectivity_smoke`,
treatment `off`, seeds `[1729, 2718, 3141]`.

| Arm | Model | `tool_contract_policy` | Runs | Experiment directory |
|-----|-------|------------------------|------|----------------------|
| A | `mistral-small3.2:24b` | `none` | 3 | `exp-20260820T123022.155255Z-214df28be9ee45f89e4f8a8025a11d1b` |
| B | `mistral-small3.2:24b` | `trailing_user` | 3 | `exp-20260820T123044.583909Z-9cfbd1186496441db02edec6515976b3` |
| C | `qwen3.5:27b` | `none` | 3 | `exp-20260820T123151.135687Z-e68f7f80624a498d9a392ddfda02a4d8` |

**Total: exactly 9 model runs.** No retries, no reruns, no discarded runs, no
prompt or configuration change after any observation. Qwen was not run with
`trailing_user`, by design.

Diagnostic input was byte-identical across all nine runs: one
`system_prompt_sha256` (`97849fab…`), one `user_prompt_sha256` (`8adb4833…`),
one `initial_state_fingerprint` (`80e53dae…`), one `policy_sha256`.

---

## C. Per-run depth and completion

Depth is the number of executed, successful `file.read` actions.

| Arm | Seed | Model calls | Tool calls | Depth | Chain completed | Executed sequence |
|-----|------|-------------|------------|-------|-----------------|-------------------|
| A | 1729 | 2 | 1 | 1 | no | `start` |
| A | 2718 | 2 | 1 | 1 | no | `start` |
| A | 3141 | 2 | 1 | 1 | no | `start` |
| B | 1729 | 4 | 3 | 3+ | **yes** | `start → middle → end` |
| B | 2718 | 4 | 3 | 3+ | **yes** | `start → middle → end` |
| B | 3141 | 4 | 3 | 3+ | **yes** | `start → middle → end` |
| C | 1729 | 4 | 3 | 3+ | **yes** | `start → middle → end` |
| C | 2718 | 4 | 3 | 3+ | **yes** | `start → middle → end` |
| C | 3141 | 4 | 3 | 3+ | **yes** | `start → middle → end` |

Depth-bucket counts: depth 0 — 0 runs; depth 1 — 3 runs (all Arm A); depth 2 —
0 runs; depth 3+ — 6 runs (Arms B and C, all seeds).

Every proposed action was executed and independently adjudicated: proposed and
executed counts are equal in all nine runs (1/1 in Arm A, 3/3 in Arms B and C),
`queued_action_count = 0`, `multi_call_overflow = false`, and the evidence
fragments carry exactly one `ALLOW` gateway decision per executed action.

---

## D. Mistral `none` vs repaired diagnostic behaviour

**Arm A (`none`) reproduces the Phase-B defect exactly and reproducibly across
all three seeds.** The first request carries the tool contract (350 input
tokens) and the model emits a tool call (`finish_reason: tool_calls`), reaching
depth 1. The second request — which appends an assistant tool-call turn and a
tool-result turn — is measured at **261 input tokens, fewer than the 350 of the
first request despite the conversation having grown**. That request returns
`finish_reason: stop` with no tool call, and the run terminates at depth 1.

**Arm B (`trailing_user`) restores sequential tool availability on the same
model, same template, same digest, same seeds, and byte-identical prompt.** All
three runs complete the full three-step chain.

Quantitative corroboration (identical history at call 2 in both arms):

| Measurement | Arm A (`none`) | Arm B (`trailing_user`) |
|-------------|----------------|-------------------------|
| Call 1 input tokens | 350 | 350 (identical; no repair applies to the first request) |
| Call 2 input tokens | 261 | 486 |
| Call 1 → call 2 delta | **−89** (shrinks) | **+136** (grows) |

The 225-token difference between the two arms at call 2 is the rendered tool
contract plus the minimal trailing protocol marker. This is direct evidence that
in Arm A the tool contract was absent from the *rendered* prompt even though the
request's `tools` field was populated identically in both arms — precisely the
adjacency defect Phase C diagnosed and repaired.

Arm A is a diagnostic reproduction/control only. **It is not a treatment
comparison and Arm A vs Arm B must not be reported as an effect.** Arm A was not
forced to fail; what it did is reported as observed.

---

## E. Qwen unchanged-path check

Arm C behaved identically to the pre-repair healthy path in every respect that
the qualification can observe:

- `tool_contract_refreshed = false` on **every** request of **every** run. Qwen
  never received the trailing-user repair.
- Input tokens grow monotonically across the whole run in all three seeds:
  `581 → 741 → 901 → 1055`. The tool contract is rendered on every turn by the
  provider's own template, as Phase B found.
- All three runs completed the three-step chain, satisfying F2.
- No `tool_contract_regression_detected` in any run.

Phase C's intent — leave healthy providers unmodified — holds against the real
provider.

---

## F. Token trajectory and contract-refresh evidence

| Arm | Seed | Input-token trajectory | `tool_contract_refreshed` | Phase-B signature present |
|-----|------|------------------------|---------------------------|----------------------------|
| A | 1729 | 350 → **261** | false, false | **yes** |
| A | 2718 | 350 → **261** | false, false | **yes** |
| A | 3141 | 350 → **258** | false, false | **yes** |
| B | 1729 | 350 → 486 → 580 → 669 | false, **true, true, true** | no |
| B | 2718 | 350 → 486 → 580 → 669 | false, **true, true, true** | no |
| B | 3141 | 350 → 483 → 574 → 660 | false, **true, true, true** | no |
| C | 1729 | 581 → 741 → 901 → 1055 | false, false, false, false | no |
| C | 2718 | 581 → 741 → 901 → 1055 | false, false, false, false | no |
| C | 3141 | 581 → 741 → 901 → 1055 | false, false, false, false | no |

The signature column is computed independently from the raw per-call token
trajectory, not from the instrument's telemetry flag. The instrument's
`tool_contract_regression_detected` flag agrees with it in all nine runs (`true`
for the three Arm-A runs, `false` elsewhere), but per the frozen plan the flag is
treated as corroborating telemetry, not as proof.

Determinations:

- **Arm B: the repaired real-provider path eliminates the Phase-B
  tool-contract-loss signature.** 3/3 runs, monotonically increasing input
  tokens, contract refreshed on every post-first-action request.
- **Arm C: the previously healthy path remains healthy.** 3/3 runs, no
  signature, no refresh, no perturbation.
- **Arm A: the signature is still present**, exactly as the frozen Phase-B
  diagnosis describes.

Qwen and Mistral token counts are not comparable to each other (different
tokenizer and template); only the within-run trajectory shape is read.

---

## G. Protocol anomalies

**None.** Across all nine runs:

- no `invalid_tool_call`, `invalid_json`, or `invalid_action_format` failure;
- no malformed tool/result correlation;
- no adapter-version inconsistency (all rows and manifests carry
  `instrument_version = 2`, `native_tool_adapter_version = native-tools-adapter-2`);
- no silent pending-action loss (`queued_action_count = 0`,
  `multi_call_overflow = false`, proposed == executed in every run);
- no unclassified provider protocol failure (`failure_class` is null in every
  run and no run recorded an error);
- no provider transport error, timeout, rate limit, or refusal.

Each run ended with a terminal no-action response (`terminal_no_action = true`,
`finish_reason: stop`), which is the intended clean termination path.

For Arm A, the terminal no-action at depth 1 is **not** classified as model
behaviour: the token evidence shows the tool contract was absent from the
rendered prompt, so the model could not have called a tool. For Arms B and C,
the terminal no-action arrives only after the chain is complete and `DONE` has
been read, with the contract demonstrably present — that is correct model
behaviour, not an instrument failure.

---

## H. Multi-call observations

**Not naturally exercised in Phase D.** No provider emitted more than one native
tool call in a single turn: `provider_multi_tool_call = false` and
`provider_max_tool_calls = 1` in all nine runs, and `queued_action_count = 0`
throughout. `parallel_tool_calls` remained `false` in the request, and no attempt
was made to induce multi-call turns.

The multi-call queue, grouped-turn replay, per-proposal IQA-SOA adjudication,
provider tool-call-ID retention, and overflow refusal therefore rest on the
deterministic Phase-C regression tests (33 focused protocol tests, all passing).
**Per the frozen plan this is not a qualification failure.**

---

## I. Qualification verdict

### **PASS**

| Criterion | Result |
|-----------|--------|
| H1 — Arm B refreshes the contract on every post-first-action request | **PASS** (9/9 post-first-action requests across 3 runs) |
| H2 — Arm C never refreshed; Qwen unmodified (Arm A likewise never refreshed) | **PASS** |
| H3 — no invalid history, malformed correlation, adapter inconsistency, pending-action loss, or unclassified protocol failure | **PASS** |
| H4 — runtime provenance identifies runtime, template, model | **PASS** (preflight, inference-free) |
| H5 — instrument version 2 / native-tools-adapter-2 on every row and manifest | **PASS** |
| F1 — an Arm-B run reaches three sequential tool actions | **PASS** (3/3) |
| F2 — an Arm-C run reaches three sequential tool actions | **PASS** (3/3) |

No stop condition fired. The real provider contradicted no Phase-C assumption;
`trailing_user` restored Mistral tool availability; provider and template
behaviour matched the frozen Phase-B diagnosis; provenance identified the
environment; no new protocol defect appeared; every criterion was interpretable
without changing the frozen plan.

Validation after the nine runs: focused protocol tests 33 passed; full suite
241 passed; `mypy` strict, 45 source files, no issues. `src/` is byte-identical
to the approved Phase-C HEAD — **no code was patched during Phase D.**

---

## J. Limitations (exact)

1. **Not evidence.** This is an engineering smoke. It establishes nothing about
   safety, utility, capability, or effect size, and supports no claim in the
   manuscript.
2. **Must not be pooled.** Phase-D rows use a different benchmark, a different
   task, a single treatment arm, and `experiment_kind =
   real_model_connectivity_smoke`. Instrument-version agreement with future
   post-repair runs is necessary but not sufficient for pooling; pooling is
   refused outright.
3. **Nine runs, one task, one treatment.** Three seeds per arm on a single
   synthetic diagnostic under QA `off`. Nothing here generalizes to the frozen
   benchmark, to other categories, or to guard-enabled treatments.
4. **Depth is not difficulty.** The instrument exposes the case's whole resource
   vocabulary in the native tool's `resource` enum, so all three filenames are
   visible from the first call. The chain constrains ordering and sequential
   tool availability, not filename discovery. Declared in the frozen plan before
   any result was observed.
5. **Arm A is a control, not a comparison.** The Arm-A/Arm-B difference is a
   diagnostic reproduction of an instrument defect, not a treatment effect, and
   must never be reported as one.
6. **Multi-call path unexercised** by real providers here (section H); it rests
   on deterministic tests.
7. **Cross-model token counts are not comparable.** Mistral and Qwen use
   different tokenizers and templates; only within-run trajectory shape is read.
8. **Single runtime snapshot.** One host, one Ollama version (0.32.13), one
   digest and template per model, captured at one moment. A runtime, template,
   or model update invalidates this qualification.
9. **`timeout_seconds` raised to 600** in the Phase-D provider config (from 60)
   so a cold local model load could not be misreported as a provider timeout.
   No timeout occurred; no retry was permitted either way.
10. **Determinism is not claimed.** Seeds were passed and echoed back as
    `effective_provider_seed`, and the observed trajectories were stable across
    seeds, but this smoke does not test seed determinism.
11. **`mypy` scope** is the configured package (`iqa_soa`); the Phase-D driver
    and analysis scripts under `scripts/` are outside it, as are all pre-existing
    scripts.
12. **Line-ending caveat.** The repository sets `core.autocrlf=true` with no
    `.gitattributes`. The frozen plan hash is over the LF working-copy bytes, as
    with the other LF-stored docs and case files; a checkout that rewrites line
    endings would change that hash. This is a pre-existing repository-wide
    property, not specific to Phase D.

---

## K. Git status and branch

```
branch : phase-d/instrument-qualification
HEAD   : Phase-D artifacts committed on top of 5950f4d (freeze commit),
         itself on top of bb54608 (approved Phase-C HEAD)
main   : e98dd7c49a967162fa51500b67d3d4a808778e26  (untouched)
```

Nothing was merged. Nothing was pushed. `main` was not modified.

Confirmed unchanged versus the approved Phase-C HEAD `bb54608`:
`benchmark/pilot-v6.1/**`, preregistration v3, `results/pilot-v6.1-stage1/**`,
`results/phaseA-privacy-ablation/**`, the Phase-A plan, `configs/policies/**`,
`configs/pilot-models.yaml`, `configs/pilot-v6.1.yaml`, the manuscript, and all
of `src/`.

Added by Phase D (new paths only): `docs/phaseD_instrument_qualification_plan.md`
and its `.sha256`, `docs/phaseD_qualification_report.md`,
`benchmark/phaseD-diagnostic/DIAG-001.yaml`, `configs/phaseD-diagnostic.yaml`,
`configs/phaseD-models.yaml`, `scripts/phaseD_preflight.py`,
`scripts/run_phaseD_qualification.py`,
`scripts/analyze_phaseD_qualification.py`, and
`results/phaseD-qualification/**`.
