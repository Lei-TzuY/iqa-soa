# Phase-D Real-Provider Instrument Qualification Plan

Status: FROZEN before the first Phase-D model inference call.
Approved Phase-C HEAD: `bb5460891c47d0509d8f51d9a1b936b0b7c3e53c`
Branch: `phase-d/instrument-qualification`
Instrument: `instrument_version = 2`, `native_tool_adapter_version = native-tools-adapter-2`

---

## 1. What this document is, and what it is not

This is a **post-Phase-B / post-Phase-C engineering qualification smoke** of the
repaired native-tools instrument against the real local provider runtime.

It is explicitly **NOT**:

- **not** preregistration v3, nor an amendment, extension, or successor to it;
- **not** scientific evidence, and nothing in it may be cited in the manuscript
  as a result;
- **not** confirmatory evidence for any hypothesis;
- **not** an effect-size, power, or comparative-performance study;
- **not** a treatment comparison between models, and **not** a safety or
  utility measurement of any kind.

Its only question is an engineering one:

> After the Class-P repair, does the real provider path keep the native tool
> contract available across sequential tool results, and does the repaired path
> remain protocol-correct, without perturbing the provider that was already
> healthy?

### 1.1 Non-pooling rule (binding)

Phase-D outputs **MUST NEVER** be pooled, merged, averaged, compared, or
reported together with:

- pilot-v6.1 Stage-1 results,
- pilot-v6.1 Stage-2 results,
- Phase-A privacy-ablation results,
- any future confirmatory measurement.

This holds regardless of `instrument_version` agreement. Phase-D uses a
different benchmark (`benchmark/phaseD-diagnostic`), a different task, a single
treatment arm, and a non-scientific purpose, so instrument-version compatibility
is necessary but not sufficient for pooling, and pooling is refused outright.

Phase-D artifacts are written under `results/phaseD-qualification/` and are
recorded with `experiment_kind = real_model_connectivity_smoke`, never
`real_model_pilot`.

### 1.2 No effect claim (binding)

**No safety claim, no utility claim, no quality claim, and no effect-size claim
may be made from these runs.** Task success, token counts, and completion depth
are read here only as evidence about *instrument availability and protocol
correctness*, never as evidence about model capability, safety, or benefit.

---

## 2. Frozen scientific artifacts (untouched)

Phase D does not create, modify, delete, or re-run any of:

- `benchmark/pilot-v6.1/**`
- preregistration v3 (`docs/preregistration_coverage_extension_v3.md`)
- Stage-1 / Stage-2 results (`results/pilot-v6.1-stage1/**`)
- Phase-A plan and results (`docs/phaseA_privacy_ablation_plan.md`,
  `results/phaseA-privacy-ablation/**`)
- QA policies used by frozen experiments (read-only reuse of
  `configs/policies/default.xml`; not modified)
- the manuscript
- frozen model/config artifacts (`configs/pilot-models.yaml`,
  `configs/pilot-v6.1.yaml`)

No pilot-v6.1 task is redesigned, reworded, reselected, or reused for the core
qualification.

---

## 3. Diagnostic task (Phase-D only, non-scientific)

A single dedicated synthetic sandbox case, `DIAG-001`, in the Phase-D-only
benchmark directory `benchmark/phaseD-diagnostic/`.

Three-step pointer chain:

```
public/start.txt   ->  "Next file: public/middle.txt"
public/middle.txt  ->  "Next file: public/end.txt"
public/end.txt     ->  "DONE"
```

User task: *"Read public/start.txt. Each file names the next file to read.
Follow the chain until you reach a file whose contents are DONE."*

Properties, by construction:

- Requires **three sequential `file.read` decisions**. The identity of the
  second and third resource is revealed only by the preceding tool result;
  neither the user prompt nor any earlier file names them.
- Contains **no** privacy, injection, permission, budget, safety, adversarial,
  or fault construct. Category is `benign`; `protected_data`,
  `protected_resources`, `forbidden_actions`, `forbidden_resources` are all
  empty; there is no `attack` and no `fault` block.
- The system prompt is reused verbatim from the existing benign case wording
  and contains no provider-specific hinting. **No wording was added, tuned, or
  selected to make any particular model behave better**, and no wording will be
  changed after observing results.
- The prompt bytes and initial sandbox state are **identical across all three
  arms** because all arms load the same single case file. This is verifiable
  post hoc via `system_prompt_sha256`, `user_prompt_sha256`, and
  `initial_state_fingerprint`, which must agree across all nine runs.

### 3.1 Known, pre-declared limitation of the task

The instrument derives the native tool's `resource` enum from the case's
declared resource vocabulary (`BenchmarkCase.canonical_resources`), so all three
filenames are visible in the tool schema from the first call onward. The chain
therefore constrains *ordering* and *sequential tool availability*, not
*discoverability of the filenames*. This is a property of the existing
instrument, is identical across all arms, and is recorded here **before** any
result is observed so it cannot be introduced later as an explanation.

---

## 4. Qualification matrix (frozen)

Seeds, fixed and identical for every arm: **1729, 2718, 3141**.
Single treatment arm: **`off`** (QA guards disabled), chosen so that no
privacy/injection/permission/budget guard construct can confound a measurement
about tool-contract availability. Every executed action still passes through the
IQA-SOA gateway individually and is adjudicated and logged.

| Arm | Provider slot | Model | `tool_contract_policy` | Runs |
|-----|---------------|-------|------------------------|------|
| A | `mistral_none` | `mistral-small3.2:24b` | `none` | 3 |
| B | `mistral_trailing_user` | `mistral-small3.2:24b` | `trailing_user` | 3 |
| C | `qwen_none` | `qwen3.5:27b` | `none` | 3 |

**Total: exactly 9 diagnostic model runs.**

- No retries. `max_infrastructure_retries` is 0 and no run is repeated for any
  reason, including provider error, timeout, or an unexpected outcome.
- No silent reruns. Every produced experiment directory is reported.
- No prompt tuning, seed change, config change, or case change after observing
  any result.
- **Arm A is a diagnostic reproduction/control for the Phase-B instrument
  defect only.** It is *not* a scientific treatment comparison, and Arm A vs
  Arm B must never be reported as an effect.
- **Qwen is deliberately NOT run with `trailing_user`.** Phase C intentionally
  leaves healthy providers unmodified, and running the repair against a healthy
  provider is out of scope for this qualification.

---

## 5. Recorded evidence (per run and per model call)

Written by the existing post-repair instrument to
`results/phaseD-qualification/raw/<experiment-id>/`:

- `manifest.json` — provider descriptor, `provider_runtime` provenance,
  `instrument_version`, `native_tool_adapter_version`, input digests, seeds.
- `runs.jsonl` — one complete row per run, including `provider_attempts`, the
  full per-model-call provenance list.
- `runs.csv` — the stable column subset.
- `evidence/<run-id>.jsonl` — QA-IUM evidence events per adjudicated action.

Per model call (`provider_attempts[i]`): provider/model, effective model, seed,
`tool_contract_refreshed`, `input_tokens`, `output_tokens`, `finish_reason`,
`tool_call_count`, `multi_tool_call`, `additional_action_count`,
`emitted_action_ids`, `emitted_resources`, `emitted_proposals`,
`emitted_actions`, `emitted_tool_call_ids` (original provider tool-call IDs when
present), `outcome`, `failure_class`, request/response IDs, latency.

Per run: seed, `tool_contract_policy`, `instrument_version`,
`native_tool_adapter_version`, `terminal_no_action`,
`terminal_no_action_attempts`, `no_action_after_actions`,
`provider_multi_tool_call`, `provider_max_tool_calls`, `queued_action_count`,
`multi_call_overflow`, `tool_contract_regression_detected`, `model_calls`,
`tool_calls`, proposed vs executed action counts, evidence trace path.

Depth is derived and reported as the number of **executed** `file.read` actions:

- depth 0 — run started, no tool action executed
- depth 1 — one executed read
- depth 2 — two executed reads
- depth 3+ — three or more executed reads
- `chain_completed` — `public/start.txt`, `public/middle.txt`, and
  `public/end.txt` were each read successfully, in that order.

**No safety or quality metric is inferred from this diagnostic.** Metric columns
the shared runner emits (e.g. `task_success`, `constraint_violation`) are
recorded because the row schema is shared, and are read only as instrument
telemetry.

---

## 6. Hard qualification criteria (frozen, pre-observation)

**H1.** Arm B (Mistral `trailing_user`): every post-first-action provider
request records `tool_contract_refreshed = true`. Equivalently: in each Arm-B
run, every attempt after the first executed action has
`tool_contract_refreshed = true`, and the first request has it `false`.

**H2.** Arm C (Qwen `none`): `tool_contract_refreshed` is `false` on every
request in every run. Qwen never receives the trailing-user repair.
(Arm A, Mistral `none`, must likewise never record a refresh.)

**H3.** No run fails because of: invalid native history construction; malformed
tool/result correlation; adapter-version inconsistency; silent pending-action
loss (`multi_call_overflow` with unconsumed queued actions); or an unclassified
provider protocol failure (a failure with no `failure_class`).

**H4.** Runtime provenance is complete enough to identify the actual runtime,
template, and model used: `runtime`, `runtime_version`, `model_identifier`,
`model_digest`, `template_sha256`, and `capabilities` are all non-null for both
models, with `probe_error` null.

**H5.** Every Phase-D row and manifest records `instrument_version = 2` and
`native_tool_adapter_version = native-tools-adapter-2`.

**Functional smoke (F1, F2).**

- **F1.** At least one Arm-B run reaches three sequential executed tool actions.
- **F2.** At least one Arm-C run reaches three sequential executed tool actions.

**Interpretation rule (frozen).** If the tool contract is demonstrably available
on a request (the request carried `tools`, and for Arm B
`tool_contract_refreshed = true`) but the model returns a terminal no-action
response, that is classified as **model behaviour**, not an instrument failure.
Arm A is **not** forced to fail; whatever it actually does is reported as
observed.

### 6.1 Phase-B signature check

For every arm, the per-call `input_tokens` trajectory is reported. The Phase-B
tool-contract-loss signature is:

> a later model call carries **strictly fewer** input tokens than an earlier
> call in the same run, despite the conversation history having grown.

`tool_contract_regression_detected` is treated as **diagnostic telemetry only**,
never as proof by itself; the raw per-call token trajectory is reported
alongside it and is the primary evidence.

Determinations to be made (descriptively, not inferentially):

- Arm B: whether the repaired real-provider path eliminates the signature.
- Arm C: whether the previously healthy path remains free of the signature.
- Arm A: reported as observed, with no requirement that it reproduce.

### 6.2 Multi-call path

No attempt is made to induce multiple tool calls per turn. `parallel_tool_calls`
remains `false` in the request, as in the frozen configuration.

If a provider naturally emits a multi-call turn, verify: all proposals recorded
(`proposed_action_count` equals total emitted); grouping preserved (shared turn
index in replayed history); each executed action independently adjudicated by
IQA-SOA (one evidence decision per action); no proposal lost; original provider
tool-call IDs retained in `emitted_tool_call_ids`.

If no run emits a multi-call turn, the report states **"not naturally exercised
in Phase D"** and relies on the deterministic Phase-C regression tests. **That is
not a qualification failure.**

---

## 7. Verdict rule (frozen)

- **PASS** — H1-H5 all hold, and F1 and F2 both hold.
- **FAIL** — any of H1-H5 is violated, or a stop condition in section 8 fires.
- **INCONCLUSIVE** — H1-H5 hold but F1 or F2 does not (the instrument is
  protocol-correct but the functional smoke did not demonstrate a three-step
  chain in the arm concerned), or the evidence cannot decide a criterion without
  changing this plan.

Arm A's outcome does **not** enter the verdict. It is reported descriptively.

---

## 8. Stop conditions (frozen)

Execution stops immediately, **without repairing code**, if:

1. the real provider contradicts an assumption made in Phase C;
2. `trailing_user` does not restore Mistral tool availability;
3. provider/template behaviour differs materially from the frozen Phase-B
   diagnosis;
4. runtime provenance cannot identify the environment (H4 fails at preflight —
   in that case, stop *before* any inference call);
5. a new protocol defect appears;
6. a qualification criterion cannot be interpreted without changing this plan.

**No code is patched after observing a real-model outcome within Phase D.** If a
repair is indicated, the failure is reported and the phase stops so it can be
reviewed as a new engineering phase.

---

## 9. Validation and output (frozen)

After exactly nine model runs: focused protocol tests, full `pytest`, `mypy`.

Explicitly not run: pilot-v6.1, Phase A, any 420-run experiment, any statistical
significance test, any manuscript edit.

---

## 10. Bound inputs (SHA-256)

| Input | SHA-256 |
|-------|---------|
| `benchmark/phaseD-diagnostic/DIAG-001.yaml` | `6939a4b50a74f8ed091dd6b38ee6e320eb479da3cb3290e32f24f65746b71e54` |
| `configs/phaseD-diagnostic.yaml` | `7f3d8929b0aae03f7c638c1cfc5bbf7159303081bcf5f3f7df07fc0d28f4b9ac` |
| `configs/phaseD-models.yaml` | `d2b6da887bfaa363d4c3dfc3235148cabd62f012e8313bd5aadc252cd632edf0` |
| `configs/policies/default.xml` (read-only reuse) | `256a8205fa944f74e12642925298260848fae5ebbb320f695ce0a234ea9f63e5` |

This plan is frozen at the SHA-256 recorded in
`docs/phaseD_instrument_qualification_plan.sha256`. It is not modified after the
first model call, and not modified after observing any qualification result. If
an unexpected condition would require a changed plan, execution STOPS instead.
