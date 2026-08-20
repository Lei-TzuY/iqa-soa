# Controlled Experiment Protocol

## Research design

The primary independent variable is runtime governance treatment:

- **G0 / Before / `off`**: all syntactically valid proposals reach the sandbox; minimal measurement evidence remains enabled.
- **G1 / `partial`**: permission and budget guards, selected as a transparent conventional-validation baseline because the proposal leaves partial governance unspecified.
- **G2 / After / `full`**: every implemented QA Module is active.
- **Ablation**: FULL with exactly one of injection, privacy, permission, budget, output validation, or detailed evidence disabled by configuration.

The base experimental QA-XML requires confirmation at `critical` severity so a
high-impact action that is otherwise authorized can expose the injection or
privacy module when that module alone is removed. This is a declared
mechanism-isolation choice, not a recommendation for deployment. The runtime
still derives high-risk floors for outbound/destructive tools independently of
the model, and deployments can configure confirmation at `high`.

For each case and repetition, the provider, model parameters, system/user prompts, scripted proposals, initial tool state, attack/fault, benchmark truth, and supported random seed are identical. Each treatment gets a fresh state clone. Where configured, one seed-derived permutation is rotated across each complete repetition block (a deterministic Latin rotation), so every treatment occupies every ordinal position once per full block. The exact order and position remain recorded on every row.

## Execution protocol

1. Validate all policy, model, experiment, and benchmark inputs before creating a run.
2. Create a unique, timestamped experiment directory using exclusive creation; never overwrite a prior run.
3. For each case and repetition, derive and record the seed and treatment order.
4. Reset the sandbox to the case's initial environment for every treatment.
5. Generate proposals from the selected provider.
6. Pass every proposal through the decorator/gateway path. OFF bypasses QA decisions but not observation; governed modes execute only authorized actions.
7. Preserve tool faults and failed runs in raw records.
8. Write append-only evidence and one raw run record with configuration/version provenance. A zero-action/provider-failure run receives a terminal lifecycle fragment.
9. Mark the manifest `complete` only after the exact case x repetition x treatment Cartesian design has been written. Analysis rejects running, truncated, duplicated, error-bearing, or provenance-incomplete runs.
10. Analyze only exact unablated OFF/FULL pairs for the primary before/after result.
11. Analyze ablations as aligned component comparisons, not replacements for the primary paired treatment.

## Repetitions, seeds, and pilots

The deterministic default uses multiple recorded repetitions to exercise the full artifact reproducibly; identical deterministic repetitions are not independent evidence about model stochasticity, so the analyzer suppresses their confidence intervals, hypothesis tests, and replication-dependent effect sizes. For an HTTP model provider, choose repetition count after a registered pilot and power/simulation analysis, record supported seeds, temperature and provider/model versions, and report where the provider cannot guarantee seeded determinism.

Online-provider repetitions are nested within tasks. The automated analysis first averages applicable repetitions within each task, then uses task-cluster bootstrap intervals and a two-sided task-level sign-flip randomization test. Its estimand is the mean treatment effect over this fixed benchmark suite; it does not license generalization to unseen tasks. Metrics applicable to fewer than two task clusters receive no inferential output.

Do not tune case definitions after examining confirmatory outcomes. If a case or policy changes, assign a new benchmark/policy version and rerun both members of every pair.

The Phase 2 real-model pilot uses exactly OFF/FULL, five repetitions, two
configured model slots, deterministic two-arm rotation, and 12 frozen tasks.
For frozen `pilot-v3`, resource semantics are registered before any v3 model
outcome: `max_tokens`, `max_runtime_ms`, and `max_cost` are telemetry-only in
every ordinary non-budget category, while the dedicated `budget` category keeps
all of its strict resource limits. Safety/security violation and resource-budget
violation are reported separately; their union is the explicitly labeled
overall governance constraint metric. This category-wide policy is
model-independent and does not alter a frozen case byte.
Before any 120-run model pilot, a separate four-cell BEN-001/UA-003 smoke must
pass provider, parsing, benign-utility, and OFF-execution/FULL-interception
checks. The pilot command requires that verified smoke directory. No automatic
infrastructure retry is allowed, and the 240-run two-model design must remain
below the configured ceiling of 300. Full real-provider ablations remain gated
until this pilot has credible data.

## Analysis plan

The analysis methods and formulas are fixed in `docs/metrics.md`. Report raw counts with rates, paired effect sizes and uncertainty. Binary and continuous outcomes use different methods. Correct for multiple confirmatory comparisons in a future preregistered study; this prototype intentionally labels generated smoke/pilot tables as artifact validation, not publication conclusions.

Figures are accepted only when sourced from real aggregate run records:

- A: major safety outcomes, OFF versus FULL;
- B: safety–task-success–false-rejection–latency/cost trade-off;
- C: module ablations;
- D: OFF versus FULL by adversarial/fault category.

If required categories or treatment variants are absent, figure generation fails rather than filling gaps.

## Controlled variables and provenance

Raw rows record experiment/run/task identifiers, category, repetition, seed, provider/model, treatment/ablation, timestamp, result/error, all registered metrics, and trace locations. The running/completed manifest records the exact expected/observed design size and SHA-256 digests for the experiment/model/ablation configuration, QA-XML policy and schema, and benchmark tree plus the artifact/Python versions. Derived analyses and figures also hash their raw-record and manifest inputs. API credentials are never serialized.

## Threats to validity

- **Construct validity:** safety, justified refusal, evidence completeness, and task success are explicit proxies, not complete measures of trustworthiness.
- **Internal validity:** exact state reset and paired proposals control the deterministic artifact; remote providers can still drift, ignore seeds, rate-limit, or change versions.
- **Conclusion validity:** the included benchmark is small and hand-authored. Deterministic repeat copies do not enlarge the effective stochastic sample.
- **External validity:** simulated tools and synthetic secrets prevent real harm but cannot establish performance in production, healthcare, robotics, or every agent framework.
- **Benchmark bias:** cases expose mechanisms deliberately. Confirmatory work should freeze them before results and add independent/public benchmarks.
- **Fault validity:** simulated fault intensity and recovery endpoints are simplified and must be calibrated for a target system.
- **Cost validity:** unknown prices remain `null`; time-varying provider prices require dated configuration.
- **Replay leakage:** future adaptive experiments need temporal holdouts and a frozen evaluation window; the current replay does not claim learning or convergence.
